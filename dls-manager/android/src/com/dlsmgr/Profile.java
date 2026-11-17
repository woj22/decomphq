package com.dlsmgr;

import java.io.ByteArrayOutputStream;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.zip.Inflater;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * DLS19 profile.dat: decode, turn the Dream FC into a club, encode.
 * Same format and logic as tools/save/dls_save.py and make_fuzinar_profile.py:
 *   16-byte header (u16 1, u16 flags, u32 length, u32 Adler-32 seeded 0xabc30526 over the
 *   encrypted payload, u32 raw size if zlib-compressed), payload XXTEA-encrypted as words.
 */
final class Profile {
    private static final int[] KEY = {0x5035EE21, 0xB329A046, 0xBCDF1389, 0x08BA8AF1};
    private static final int DELTA = 0x9E3779B9;
    private static final int REC = 0xAE;
    private static final int STADIUM_AFTER_LINEUP = 0xF4;   // stadium name, 24 UTF-16 chars
    private static final int TEAM_AFTER_LINEUP = 0x11F5;    // team name, 33 chars; short name 4 chars after it

    private Profile() {}

    // ------------------------------------------------------------------ file wrapper
    static byte[] decode(byte[] file) throws Exception {
        int flags = u16(file, 2);
        int length = i32(file, 4);
        int raw = i32(file, 12);
        int n = (file.length - 16) / 4;
        byte[] body = new byte[n * 4];
        System.arraycopy(file, 16, body, 0, n * 4);
        if ((flags & 1) != 0) {
            int[] v = new int[n];
            for (int i = 0; i < n; i++) {
                v[i] = i32(body, i * 4);
            }
            xxteaDecrypt(v);
            for (int i = 0; i < n; i++) {
                put32(body, i * 4, v[i]);
            }
        }
        byte[] data = new byte[length];
        System.arraycopy(body, 0, data, 0, length);
        if (raw != 0) {
            Inflater inf = new Inflater();
            inf.setInput(data);
            byte[] outb = new byte[raw];
            inf.inflate(outb);
            inf.end();
            data = outb;
        }
        return data;
    }

    static byte[] encode(byte[] data) {
        int pad = (4 - data.length % 4) % 4;
        int n = (data.length + pad) / 4;
        int[] v = new int[n];
        byte[] body = new byte[n * 4];
        System.arraycopy(data, 0, body, 0, data.length);
        for (int i = 0; i < n; i++) {
            v[i] = i32(body, i * 4);
        }
        xxteaEncrypt(v);
        for (int i = 0; i < n; i++) {
            put32(body, i * 4, v[i]);
        }
        byte[] out = new byte[16 + body.length];
        put16(out, 0, 1);
        put16(out, 2, 1 | (pad << 1));
        put32(out, 4, data.length);
        put32(out, 8, adler(body, 0xABC30526));
        put32(out, 12, 0);
        System.arraycopy(body, 0, out, 16, body.length);
        return out;
    }

    // ------------------------------------------------------------------ Dream FC -> club
    /**
     * The development list stores the ratings in a different order from players.dat
     * (database: speed, acceleration, stamina, strength, tackling, control, shooting,
     * passing, crossing, heading, 3 x goalkeeping). Development slot k holds database
     * attribute DEV_ORDER[k]: strength, stamina, speed, acceleration, control, crossing,
     * passing, shooting, heading, tackling, then the goalkeeping three. Found from an in-game
     * card (Gabriel): every value matched this order exactly.
     */
    static final int[] DEV_ORDER = {3, 2, 0, 1, 5, 8, 7, 6, 9, 4, 10, 11, 12};

    static byte[] becomeClub(byte[] d, JSONObject club) throws Exception {
        JSONArray ps = club.getJSONArray("players");
        // starting XI first (link flag 1), then by DLS slot
        List<JSONObject> order = new ArrayList<JSONObject>();
        for (int i = 0; i < ps.length() && i < 32; i++) {
            order.add(ps.getJSONObject(i));
        }
        // starting XI first (link flag 1), then by DLS slot (stable insertion sort; no
        // Comparator class, which trips d8 - see Overlay build notes)
        for (int i = 1; i < order.size(); i++) {
            JSONObject x = order.get(i);
            int j = i - 1;
            while (j >= 0 && rank(order.get(j)) > rank(x)) {
                order.set(j + 1, order.get(j));
                j--;
            }
            order.set(j + 1, x);
        }
        // old layout
        int nOld = d[0x20] & 0xFF;
        int p = 0x21 + nOld * REC;
        int sOld = i32(d, p + 4);
        int infoO = p + 8;
        int idsO = infoO + 128;
        int devO = idsO + 128;
        int devCnt = i32(d, devO);
        int devEnd = devO + 8 + devCnt * 31;
        Set<Integer> oldIds = new HashSet<Integer>();
        for (int i = 0; i < sOld; i++) {
            oldIds.add(i32(d, idsO + 4 * i) & 0xFFFF);
        }
        int lu = findLineup(d, devEnd, oldIds);
        int luN = d[lu] & 0xFF;
        int afterLu = lu + 1 + 2 * luN;
        int takersO = afterLu + 3;

        // Squad and development list: all the club's players (up to the 32 slots the squad
        // table has; both are read by their counts - FUN_000adfb8 / FUN_000b7308).
        // Line-up: keeps its current length (the save's XI + subs, 18 here). It sits inside
        // the season data and lengthening it shifted the competitions after it (the v42 crash).
        // Players in the squad but not in the line-up are the reserves.
        int n = Math.min(order.size(), 32);
        if (devCnt != sOld || order.size() < luN) {
            throw new Exception("unexpected save layout: squad " + sOld + ", development " + devCnt
                    + ", line-up " + luN + ", club players " + order.size());
        }
        int[] ids = new int[n];
        for (int i = 0; i < n; i++) {
            ids[i] = order.get(i).getInt("id");
        }
        ByteArrayOutputStream o = new ByteArrayOutputStream(d.length + 8192);
        o.write(d, 0, p);  // header + custom players unchanged
        byte[] info = new byte[128];
        byte[] dev = new byte[n * 31];
        for (int i = 0; i < n; i++) {
            JSONObject g = order.get(i);
            JSONArray at = g.getJSONArray("attr");
            put32(dev, i * 31, ids[i]);
            for (int k = 0; k < 13; k++) {
                put16(dev, i * 31 + 4 + 2 * k, Math.min(10000, at.getInt(DEV_ORDER[k]) * 10));
            }
            info[i * 4] = (byte) g.optInt("shirt");
            info[i * 4 + 1] = (byte) g.optInt("pos");
        }
        byte[] sect = new byte[8];
        System.arraycopy(d, p, sect, 0, 8);
        put32(sect, 4, n);
        o.write(sect, 0, 8);
        o.write(info, 0, 128);
        byte[] idArr = new byte[128];
        for (int i = 0; i < 32; i++) {
            put32(idArr, i * 4, i < n ? ids[i] : -1);
        }
        o.write(idArr, 0, 128);
        byte[] devHdr = new byte[8];
        put32(devHdr, 0, n);
        System.arraycopy(d, devO + 4, devHdr, 4, 4);
        o.write(devHdr, 0, 8);
        o.write(dev, 0, dev.length);
        o.write(d, devEnd, lu - devEnd);
        int lineupStart = o.size();
        o.write(luN);
        byte[] lineup = new byte[2 * luN];
        for (int i = 0; i < luN; i++) {
            put16(lineup, 2 * i, ids[i]);
        }
        o.write(lineup, 0, lineup.length);
        int lineupEnd = lineupStart + 1 + 2 * luN;
        o.write(d, afterLu, takersO - afterLu);
        byte[] takers = new byte[10];
        int[] bits = {2, 4, 8, 0x10, 0x20};
        for (int k = 0; k < 5; k++) {
            int t = ids[Math.min(n - 1, 10)];
            for (int i = 0; i < Math.min(n, 11); i++) {
                if ((order.get(i).optInt("flags") & bits[k]) != 0) {
                    t = ids[i];
                    break;
                }
            }
            put16(takers, 2 * k, t);
        }
        o.write(takers, 0, 10);
        o.write(d, takersO + 10, d.length - (takersO + 10));
        byte[] out = o.toByteArray();

        // names: fixed buffers at fixed distances after the line-up; only write if they hold text
        writeName(out, lineupEnd + STADIUM_AFTER_LINEUP, club.optString("stadium"), 24);
        int team = lineupEnd + TEAM_AFTER_LINEUP;
        if (writeName(out, team, club.optString("name"), 33)) {
            writeName(out, team + 66, club.optString("short"), 4);
        }
        return out;
    }

    private static int rank(JSONObject g) {
        return ((g.optInt("flags") & 1) != 0 ? 0 : 1000) + g.optInt("slot");
    }

    private static int findLineup(byte[] d, int start, Set<Integer> want) throws Exception {
        int n = want.size();
        for (int o = start; o < d.length - 1 - 2 * n; o++) {
            if ((d[o] & 0xFF) != n) {
                continue;
            }
            Set<Integer> got = new HashSet<Integer>();
            for (int i = 0; i < n; i++) {
                got.add(u16(d, o + 1 + 2 * i));
            }
            if (got.equals(want)) {
                return o;
            }
        }
        throw new Exception("line-up block not found");
    }

    private static boolean writeName(byte[] b, int off, String s, int nchars) {
        if (off < 0 || off + nchars * 2 > b.length) {
            return false;
        }
        // sanity: the buffer must currently hold UTF-16 text (printable chars or zeros)
        for (int i = 0; i < nchars; i++) {
            int c = u16(b, off + 2 * i);
            if (c != 0 && (c < 0x20 || c > 0x24F)) {
                return false;
            }
        }
        putStr(b, off, s, nchars);
        return true;
    }

    private static int birthDays(int y, int m, int d) {
        if (y <= 1900) {
            return 0x927C;
        }
        Calendar c0 = Calendar.getInstance(java.util.TimeZone.getTimeZone("UTC"));
        c0.clear();
        c0.set(1900, 0, 1);
        Calendar c1 = Calendar.getInstance(java.util.TimeZone.getTimeZone("UTC"));
        c1.clear();
        c1.set(y, Math.max(1, m) - 1, Math.max(1, d));
        return (int) ((c1.getTimeInMillis() - c0.getTimeInMillis()) / 86400000L);
    }

    // ------------------------------------------------------------------ primitives
    private static int mx(int z, int y, int sum, int p, int e, int[] k) {
        return (((z >>> 5) ^ (y << 2)) + ((y >>> 3) ^ (z << 4))) ^ ((sum ^ y) + (k[(p & 3) ^ e] ^ z));
    }

    static void xxteaEncrypt(int[] v) {
        int n = v.length;
        if (n < 2) {
            return;
        }
        int rounds = 6 + 52 / n;
        int sum = 0;
        int z = v[n - 1];
        while (rounds-- > 0) {
            sum += DELTA;
            int e = (sum >>> 2) & 3;
            for (int p = 0; p < n; p++) {
                int y = v[(p + 1) % n];
                v[p] += mx(z, y, sum, p, e, KEY);
                z = v[p];
            }
        }
    }

    static void xxteaDecrypt(int[] v) {
        int n = v.length;
        if (n < 2) {
            return;
        }
        int rounds = 6 + 52 / n;
        int sum = rounds * DELTA;
        int y = v[0];
        while (rounds-- > 0) {
            int e = (sum >>> 2) & 3;
            for (int p = n - 1; p >= 0; p--) {
                int z = v[(p - 1 + n) % n];
                v[p] -= mx(z, y, sum, p, e, KEY);
                y = v[p];
            }
            sum -= DELTA;
        }
    }

    static int adler(byte[] b, int seed) {
        long a = seed & 0xFFFF;
        long s = (seed >>> 16) & 0xFFFF;
        for (byte x : b) {
            a = (a + (x & 0xFF)) % 65521;
            s = (s + a) % 65521;
        }
        return (int) ((s << 16) | a);
    }

    static int u16(byte[] b, int o) {
        return (b[o] & 0xFF) | ((b[o + 1] & 0xFF) << 8);
    }

    static int i32(byte[] b, int o) {
        return (b[o] & 0xFF) | ((b[o + 1] & 0xFF) << 8) | ((b[o + 2] & 0xFF) << 16) | ((b[o + 3] & 0xFF) << 24);
    }

    static void put16(byte[] b, int o, int v) {
        b[o] = (byte) v;
        b[o + 1] = (byte) (v >> 8);
    }

    static void put32(byte[] b, int o, int v) {
        b[o] = (byte) v;
        b[o + 1] = (byte) (v >> 8);
        b[o + 2] = (byte) (v >> 16);
        b[o + 3] = (byte) (v >> 24);
    }

    static void putStr(byte[] b, int o, String s, int nchars) {
        for (int i = 0; i < nchars; i++) {
            int c = i < Math.min(s.length(), nchars - 1) ? s.charAt(i) : 0;
            put16(b, o + 2 * i, c);
        }
    }
}
