package com.dlsmgr;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.TextView;
import android.widget.Toast;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import org.json.JSONObject;

/**
 * DLS Manager menus shown on top of DLS19.
 *
 * Called once from SavesRestoring.DoSmth (start of MainActivity.onCreate). The menus are a
 * WebView added straight to the window's decor view, so they survive the game's own
 * setContentView and need no manifest changes. The page is assets/dlsmgr/index.html.
 *
 * JavaScript sees window.DLSManager with:
 *   hide()   - hide the menus and show the DLS game (Play Match until the engine link exists)
 *   isApp()  - true, so the page knows it runs inside the game
 *   exportSave() - zip the game's save (profile.dat etc.) and open the share sheet
 *   becomeClub(id) - your team becomes that club when the game is next opened (per-club saves)
 *   saveState(json)/loadState() - menu career backup file
 *   currentClub() - the club the Dream FC currently is ("" if none), lastError()
 * A small "Manager" button brings the menus back while they are hidden.
 */
public final class Overlay {
    private static WebView web;
    private static View reopen;
    /** Our in-match pause button (DLS's is switched off natively). */
    private static View pauseBtn;
    /** A match is being played: the menus page stays up as a transparent HUD. */
    static volatile boolean inMatch;
    static volatile boolean cutActive;
    private static Activity activity;

    private Overlay() {}

    public static void attach(Context context) {
        if (!(context instanceof Activity) || web != null) {
            return;
        }
        applyClub(context);
        activity = (Activity) context;
        final View decor = activity.getWindow().getDecorView();
        decor.post(new Runnable() {
            @Override
            public void run() {
                create();
            }
        });
    }

    private static void create() {
        if (web != null) {
            return;
        }
        ViewGroup decor = (ViewGroup) activity.getWindow().getDecorView();

        WebView w = new PassWebView(activity);
        WebSettings s = w.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setAllowFileAccess(true);
        s.setMediaPlaybackRequiresUserGesture(true);
        w.setBackgroundColor(Color.rgb(11, 14, 13));
        w.setWebViewClient(new WebViewClient());
        w.setWebChromeClient(new WebChromeClient());
        w.addJavascriptInterface(new Bridge(), "DLSManager");
        w.loadUrl("file:///android_asset/dlsmgr/index.html");
        decor.addView(w, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        web = w;

        TextView b = new TextView(activity);
        b.setText("Manager");
        b.setTextColor(Color.WHITE);
        b.setTextSize(14);
        b.setPadding(36, 18, 36, 18);
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(Color.argb(220, 76, 200, 106));
        bg.setCornerRadius(48);
        b.setBackground(bg);
        b.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                show();
            }
        });
        FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT,
                Gravity.BOTTOM | Gravity.START);
        lp.setMargins(32, 0, 0, 32);
        b.setVisibility(View.GONE);
        decor.addView(b, lp);
        reopen = b;

        TextView pb = new TextView(activity);
        pb.setText("❚❚");
        pb.setTextColor(Color.WHITE);
        pb.setTextSize(13);
        pb.setGravity(Gravity.CENTER);
        GradientDrawable pbg = new GradientDrawable();
        pbg.setColor(Color.argb(215, 11, 14, 13));
        pbg.setCornerRadius(18);
        pbg.setStroke(2, Color.argb(120, 255, 255, 255));
        pb.setBackground(pbg);
        pb.setOnClickListener(new PauseClick());
        float dp = activity.getResources().getDisplayMetrics().density;
        FrameLayout.LayoutParams plp = new FrameLayout.LayoutParams((int) (40 * dp), (int) (34 * dp), Gravity.TOP | Gravity.START);
        plp.setMargins((int) (14 * dp), (int) (8 * dp), 0, 0);
        pb.setVisibility(View.GONE);
        decor.addView(pb, plp);
        pauseBtn = pb;
    }

    static void show() {
        if (web == null) {
            return;
        }
        web.setVisibility(View.VISIBLE);
        web.bringToFront();
        reopen.setVisibility(View.GONE);
        frontEnd(false);
        web.evaluateJavascript("window.dlsOnShow && window.dlsOnShow()", null);
    }

    static void hide() {
        if (web == null) {
            return;
        }
        web.setVisibility(View.GONE);
        reopen.setVisibility(View.VISIBLE);
        reopen.bringToFront();
        frontEnd(true);  // the player asked to see DLS itself
    }

    /**
     * DLS's own menus are not drawn at all (exhibition.c, render_screens_gate) unless the player
     * deliberately opens DLS; matches always draw.
     */
    static void frontEnd(boolean visible) {
        try {
            nativeRequest(visible ? 0x5A5E0011 : 0x5A5E0010);
        } catch (Throwable t) {
            lastError = String.valueOf(t);
        }
    }

    /**
     * Zip the save files (the same set as the game's own Safe Mode "send profile") into
     * DOCS/Attachments/dlsmgr_save.zip and offer it through the share sheet, using the game's
     * existing file provider (<package>.licensefileprovider). Nothing is sent anywhere unless
     * the player picks a destination.
     */
    /**
     * Start-up (before the game reads the save): one-off restores, then the current club's
     * kit/badge files are copied to the player team. Club switches happen live, see becomeClub.
     */
    static void applyClub(Context ctx) {
        File dir = ctx.getExternalFilesDir(null);
        if (dir == null) {
            return;
        }
        File current = new File(dir, "dlsmgr_club.txt");
        File prof0 = new File(dir, "profile.dat");
        saveLogcat(dir);
        // DLS keeps a "match in progress" file and resumes that match at start-up; a match
        // interrupted by a crash then crashed every launch (v56). Matches are only ever started
        // from the menus, so it's always removed.
        for (String nm : new String[]{"CurrentMatch.dat", "currentmatch.dat"}) {
            File cm = new File(dir, nm);
            if (cm.exists() && cm.delete()) {
                log(dir, "removed DLS's interrupted-match file " + nm);
            }
        }
        recover(ctx, dir);
        try {
            // One-off: the player's own save (exported before v33) bundled as
            // assets/dlsmgr/profile_restore_<tag>.dat is put back once; the current
            // profile is kept as profile_backup_restore_<tag>.dat.
            String[] names = ctx.getAssets().list("dlsmgr");
            for (String nm : names == null ? new String[0] : names) {
                if (!nm.startsWith("profile_restore_") || !nm.endsWith(".dat")) {
                    continue;
                }
                String tag = nm.substring("profile_restore_".length(), nm.length() - 4);
                File mark = new File(dir, "dlsmgr_restored_" + tag + ".done");
                if (mark.exists()) {
                    continue;
                }
                if (prof0.exists()) {
                    copy(new FileInputStream(prof0), new File(dir, "profile_backup_restore_" + tag + ".dat"));
                }
                copy(ctx.getAssets().open("dlsmgr/" + nm), prof0);
                new File(dir, "profile_temp.dat").delete();
                current.delete();
                new FileOutputStream(mark).close();
            }
            // v33's one-off Fužinar import crashed the game: put its backup back, once.
            File b33 = new File(dir, "profile_backup_fuz1.dat");
            File r33 = new File(dir, "dlsmgr_restored_fuz1.done");
            if (b33.exists() && new File(dir, "dlsmgr_import_fuz1.done").exists() && !r33.exists()) {
                copy(new FileInputStream(b33), prof0);
                new File(dir, "profile_temp.dat").delete();
                current.delete();
                new FileOutputStream(r33).close();
            }
            // v37's live switch could crash mid-way: its marker names the club to go back to.
            File switching = new File(dir, "dlsmgr_switching.txt");
            if (switching.exists()) {
                String prev = readText(new FileInputStream(switching)).trim();
                File prevSave = new File(new File(dir, "dlsmgr_saves"), prev + ".dat");
                if (prevSave.exists()) {
                    copy(new FileInputStream(prevSave), prof0);
                    new File(dir, "profile_temp.dat").delete();
                    if (prev.equals("original")) {
                        current.delete();
                    } else {
                        writeBytes(current, prev.getBytes("UTF-8"));
                    }
                    log(dir, "rolled back a crashed live switch to " + prev);
                }
                switching.delete();
            }
        } catch (Throwable t) {
            lastError = String.valueOf(t);
        }
        applyPendingSwitch(ctx, dir);
        copyClubLooks(ctx, dir);
    }

    /** The chosen club's kit and badge files become the player team's (DLS team 258). */
    static void copyClubLooks(Context ctx, File dir) {
        File current = new File(dir, "dlsmgr_club.txt");
        try {
            if (current.exists()) {
                String cid = readText(new FileInputStream(current)).trim();
                JSONObject clubs = new JSONObject(readText(ctx.getAssets().open("dlsmgr/clubs.json")));
                if (!clubs.has(cid)) {
                    return;
                }
                int tid = clubs.getJSONObject(cid).getInt("tid");
                String[] kits = {"home", "away", "third", "home_gk", "away_gk", "third_gk"};
                for (String k : kits) {
                    File src = new File(dir, tid + "_" + k + ".png");
                    File dst = new File(dir, "258_" + k + ".png");
                    if (src.exists()) {
                        copy(new FileInputStream(src), dst);
                    } else {
                        dst.delete();
                    }
                }
                String[][] logos = {{"teamlogo_" + tid + ".png", "teamlogo_258.png"},
                        {"teamlogo_" + tid + "_thumb.png", "teamlogo_258_thumb.png"},
                        {"teamlogo_" + tid + ".png", "t258.png"},
                        {"teamlogo_" + tid + "_thumb.png", "t258_thumb.png"}};
                for (String[] l : logos) {
                    File src = new File(dir, l[0]);
                    if (src.exists()) {
                        copy(new FileInputStream(src), new File(dir, l[1]));
                    }
                }
            }
        } catch (Throwable t) {
            lastError = String.valueOf(t);
        }
    }

    static String lastError = "";
    private static long libBaseCache = 0;

    /** Load address of libDLS19.so: the mapping start where "DOCS:profile.dat" sits at +0x3ee100. */
    static long libBase() throws Exception {
        if (libBaseCache != 0) {
            return libBaseCache;
        }
        java.io.BufferedReader br = new java.io.BufferedReader(new java.io.FileReader("/proc/self/maps"));
        java.io.RandomAccessFile mem = new java.io.RandomAccessFile("/proc/self/mem", "r");
        byte[] want = "DOCS:profile.dat".getBytes("US-ASCII");
        try {
            String line;
            while ((line = br.readLine()) != null) {
                if (!(line.contains("libDLS19") || line.contains(".apk"))) {
                    continue;
                }
                String[] f = line.split("\\s+");
                if (f.length < 2 || f[1].charAt(0) != 'r') {
                    continue;
                }
                long start = Long.parseLong(f[0].substring(0, f[0].indexOf('-')), 16);
                try {
                    byte[] got = new byte[want.length];
                    mem.seek(start + 0x3ee100);
                    mem.readFully(got);
                    if (java.util.Arrays.equals(got, want)) {
                        libBaseCache = start;
                        return start;
                    }
                } catch (Throwable t) {
                    // not readable there, keep looking
                }
            }
        } finally {
            br.close();
            mem.close();
        }
        return 0;
    }

    static long readLong(java.io.RandomAccessFile mem, long addr) throws java.io.IOException {
        byte[] b = new byte[8];
        mem.seek(addr);
        mem.readFully(b);
        long v = 0;
        for (int i = 7; i >= 0; i--) {
            v = (v << 8) | (b[i] & 0xFF);
        }
        return v;
    }

    static int readInt(java.io.RandomAccessFile mem, long addr) throws java.io.IOException {
        byte[] b = new byte[4];
        mem.seek(addr);
        mem.readFully(b);
        return (b[0] & 0xFF) | ((b[1] & 0xFF) << 8) | ((b[2] & 0xFF) << 16) | ((b[3] & 0xFF) << 24);
    }

    /**
     * Club switch. The live version (native save + reload while running) crashed the game, so
     * the switch is applied at start-up instead, before the game reads the save:
     * becomeClub() records the request and asks the player to reopen the game; applyClub()
     * then files the current save under the current club (DOCS/dlsmgr_saves/<club>.dat) and
     * loads the target club's save, or creates it from the original save. Steps are logged to
     * DOCS/dlsmgr_log.txt.
     */
    static void becomeClub(String cid) {
        try {
            // Re-enabled in v42: an exported save showed the converted Fužinar save loads, plays and
            // autosaves; the Play-match crash was the fixture override (still off).
            File dir = activity.getExternalFilesDir(null);
            writeBytes(new File(dir, "dlsmgr_pending_club.txt"), cid.getBytes("UTF-8"));
            log(dir, "switch requested: " + cid);
            activity.runOnUiThread(new ToastTask(clubName(activity, cid)
                    + " is ready - close the game and open it again to start."));
        } catch (Throwable t) {
            lastError = String.valueOf(t);
        }
    }

    static void log(File dir, String msg) {
        try {
            FileOutputStream o = new FileOutputStream(new File(dir, "dlsmgr_log.txt"), true);
            o.write((new java.util.Date() + "  " + msg + "\n").getBytes("UTF-8"));
            o.close();
        } catch (Throwable t) {
            // ignore
        }
    }

    /**
     * Recovery (v40): club switching left saves the game crashes on. Once, restore the
     * player's own exported save (assets/dlsmgr/profile_restore_orig1.dat) and remove every
     * club-switch file, keeping the current profile as profile_backup_recover1.dat.
     */
    static void recover(Context ctx, File dir) {
        // v45: third recovery. Every club save made on the phone (v37-v44) left the season's
        // competition stats out of step with the squad and crashed the loader; club saves now
        // come pre-built and checked (assets/dlsmgr/clubsaves). The current club is switched
        // back in straight away from its new save.
        // v56: fourth run - club saves from v45-v55 had the development ratings in the
        // database order (stats scrambled on cards, e.g. Gabriel); the rebuilt club saves
        // use DLS's own order and ratings calibrated to the menus.
        File mark = new File(dir, "dlsmgr_recovered4.done");
        if (mark.exists()) {
            return;
        }
        try {
            File prof = new File(dir, "profile.dat");
            File curF = new File(dir, "dlsmgr_club.txt");
            String keep = "";
            File pendF = new File(dir, "dlsmgr_pending_club.txt");
            if (pendF.exists()) {
                keep = readText(new FileInputStream(pendF)).trim();
            } else if (curF.exists()) {
                keep = readText(new FileInputStream(curF)).trim();
            }
            if (prof.exists()) {
                copy(new FileInputStream(prof), new File(dir, "profile_backup_recover4.dat"));
            }
            copy(ctx.getAssets().open("dlsmgr/profile_restore_orig1.dat"), prof);
            String[] gone = {"profile_temp.dat", "dlsmgr_club.txt", "dlsmgr_pending_club.txt", "dlsmgr_switching.txt",
                    "258_home.png", "258_away.png", "258_third.png", "t258.png", "t258_thumb.png",
                    "teamlogo_258.png", "teamlogo_258_thumb.png"};
            for (String g : gone) {
                new File(dir, g).delete();
            }
            File saves = new File(dir, "dlsmgr_saves");
            File[] fs = saves.listFiles();
            if (fs != null) {
                for (File f : fs) {
                    f.renameTo(new File(dir, "old4_" + f.getName()));
                }
            }
            new File(dir, "dlsmgr_restored_orig1.done").createNewFile();
            new File(dir, "dlsmgr_recovered2.done").createNewFile();
            new File(dir, "dlsmgr_fullsquad1.done").createNewFile();
            new File(dir, "dlsmgr_recovered3.done").createNewFile();
            if (keep.length() > 0 && !keep.equals("original")) {
                writeBytes(pendF, keep.getBytes("UTF-8"));
            }
            new FileOutputStream(mark).close();
            log(dir, "recovery 4: original save restored, club-switch files removed; club to restore: " + keep);
        } catch (Throwable t) {
            log(dir, "recovery failed: " + t);
        }
    }

    /** Keep this app's log lines from the previous run (they include a crash's "Fatal signal" line). */
    static void saveLogcat(File dir) {
        try {
            Process pr = Runtime.getRuntime().exec(new String[]{"logcat", "-d", "-t", "600"});
            byte[] b = readBytes(pr.getInputStream());
            writeBytes(new File(dir, "dlsmgr_logcat.txt"), b);
        } catch (Throwable t) {
            // ignore
        }
    }

    /** Start-up half of a club switch (see becomeClub). Runs before the game reads the save. */
    static void applyPendingSwitch(Context ctx, File dir) {
        File pending = new File(dir, "dlsmgr_pending_club.txt");
        if (!pending.exists()) {
            return;
        }
        String cid = "";
        try {
            cid = readText(new FileInputStream(pending)).trim();
            pending.delete();  // never retried on every start
            File prof = new File(dir, "profile.dat");
            File saves = new File(dir, "dlsmgr_saves");
            saves.mkdirs();
            File currentF = new File(dir, "dlsmgr_club.txt");
            String cur = currentF.exists() ? readText(new FileInputStream(currentF)).trim() : "original";
            if (cur.length() == 0) {
                cur = "original";
            }
            log(dir, "applying switch " + cur + " -> " + cid);
            if (cur.equals(cid)) {
                return;
            }
            byte[] now = readBytes(new FileInputStream(prof));
            Profile.decode(now);
            writeBytes(new File(saves, cur + ".dat"), now);
            log(dir, "filed current save as " + cur);
            File target = new File(saves, cid + ".dat");
            byte[] out;
            if (target.exists()) {
                out = readBytes(new FileInputStream(target));
                log(dir, "loading saved " + cid);
            } else {
                // Pre-built by tools/save/make_club_saves.py: converted, then rewritten by the
                // game's own save code (run under emulation) so the competition stats match
                // the new squad, and test-loaded the same way.
                out = readBytes(ctx.getAssets().open("dlsmgr/clubsaves/" + cid + ".dat"));
                log(dir, "new save for " + cid + " from the pre-built club save");
            }
            Profile.decode(out);
            writeBytes(prof, out);
            new File(dir, "profile_temp.dat").delete();
            writeBytes(currentF, cid.getBytes("UTF-8"));
            log(dir, "switch done: " + cid);
        } catch (Throwable t) {
            lastError = "Club switch failed: " + t;
            log(dir, "switch FAILED " + cid + ": " + t);
        }
    }

    private static String clubName(Context ctx, String cid) {
        try {
            return new JSONObject(readText(ctx.getAssets().open("dlsmgr/clubs.json"))).getJSONObject(cid).getString("name");
        } catch (Throwable t) {
            return cid;
        }
    }

    /** Hooked FTTJNI.NativeDialogButton: 0x5A5E0001 = save the profile, 0x5A5E0002 = reload it. */
    static void nativeRequest(int code) throws Exception {
        Class<?> jni = Class.forName("com.firsttouchgames.ftt.FTTJNI");
        jni.getMethod("NativeDialogButton", int.class).invoke(null, code);
    }

    static final class ToastTask implements Runnable {
        private final String msg;

        ToastTask(String msg) {
            this.msg = msg;
        }

        @Override
        public void run() {
            Toast.makeText(activity, msg, Toast.LENGTH_LONG).show();
        }
    }

    static final class BecomeTask implements Runnable {
        private final String cid;

        BecomeTask(String cid) {
            this.cid = cid;
        }

        @Override
        public void run() {
            Overlay.becomeClub(cid);
        }
    }

    private static String readText(InputStream in) throws java.io.IOException {
        return new String(readBytes(in), "UTF-8");
    }

    private static byte[] readBytes(InputStream in) throws java.io.IOException {
        java.io.ByteArrayOutputStream bo = new java.io.ByteArrayOutputStream();
        byte[] buf = new byte[65536];
        int r;
        while ((r = in.read(buf)) > 0) {
            bo.write(buf, 0, r);
        }
        in.close();
        return bo.toByteArray();
    }

    private static void writeBytes(File f, byte[] b) throws java.io.IOException {
        FileOutputStream out = new FileOutputStream(f);
        out.write(b);
        out.close();
    }

    static void copy(InputStream in, File to) throws java.io.IOException {
        FileOutputStream out = new FileOutputStream(to);
        byte[] buf = new byte[65536];
        int r;
        while ((r = in.read(buf)) > 0) {
            out.write(buf, 0, r);
        }
        in.close();
        out.close();
    }

    static void exportSave() {
        try {
            File dir = activity.getExternalFilesDir(null);
            if (dir == null) {
                dir = activity.getFilesDir();
            }
            File out = new File(dir, "Attachments");
            out.mkdirs();
            File zip = new File(out, "dlsmgr_save.zip");
            ZipOutputStream zos = new ZipOutputStream(new FileOutputStream(zip));
            File[] files = dir.listFiles();
            int n = 0;
            if (files != null) {
                for (File f : files) {
                    String name = f.getName();
                    if (f.isFile() && (name.endsWith(".dat") || name.startsWith("dlsmgr_log"))) {
                        zos.putNextEntry(new ZipEntry(name));
                        InputStream in = new FileInputStream(f);
                        byte[] buf = new byte[65536];
                        int r;
                        while ((r = in.read(buf)) > 0) {
                            zos.write(buf, 0, r);
                        }
                        in.close();
                        zos.closeEntry();
                        n++;
                    }
                }
            }
            zos.close();
            // androidx FileProvider via reflection (no compile-time dependency)
            Class<?> fp = Class.forName("androidx.core.content.FileProvider");
            Uri uri = (Uri) fp.getMethod("getUriForFile", Context.class, String.class, File.class)
                    .invoke(null, activity, activity.getPackageName() + ".licensefileprovider", zip);
            Intent send = new Intent(Intent.ACTION_SEND);
            send.setType("application/zip");
            send.putExtra(Intent.EXTRA_STREAM, uri);
            send.putExtra(Intent.EXTRA_SUBJECT, "DLS Manager save");
            send.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            activity.startActivity(Intent.createChooser(send, "Export save (" + n + " files)"));
        } catch (Throwable t) {
            Toast.makeText(activity, "Export failed: " + t, Toast.LENGTH_LONG).show();
        }
    }

    static final class ExportTask implements Runnable {
        @Override
        public void run() {
            Overlay.exportSave();
        }
    }

    /** One team sheet block: u8 valid, u8 formation, u8 count, u8 0, 32 x u16 ids. */
    static byte[] sheetBytes(JSONObject side) throws Exception {
        byte[] b = new byte[4 + 64];
        if (side != null) {
            org.json.JSONArray ids = side.getJSONArray("ids");
            int n = Math.min(32, ids.length());
            if (n >= 11) {
                b[0] = 1;
                b[1] = (byte) side.getInt("f");
                b[2] = (byte) n;
                for (int i = 0; i < n; i++) {
                    int id = ids.getInt(i);
                    b[4 + 2 * i] = (byte) id;
                    b[5 + 2 * i] = (byte) (id >> 8);
                }
            }
        }
        return b;
    }

    /**
     * The last exhibition result, written by the match's full-time handler (exhibition.c) to
     * files/dlsmgr_result.txt: "home,away,homeGoals,awayGoals,sequence", or "".
     */
    static String resultLine() {
        try {
            File f = new File(activity.getFilesDir(), "dlsmgr_result.txt");
            return f.exists() ? readText(new FileInputStream(f)).trim() : "";
        } catch (Throwable t) {
            return "";
        }
    }

    /** Changes whenever a new result is written. */
    static String resultSeq() {
        return resultLine() + "|" + new File(activity.getFilesDir(), "dlsmgr_result.txt").lastModified();
    }

    /** Shows the menus again once the match's full-time handler has written a new result. */
    static final class ResultWatch implements Runnable {
        private final String before;

        ResultWatch(String before) {
            this.before = before;
        }

        @Override
        public void run() {
            for (int i = 0; i < 10 * 4 * 3600; i++) {
                try {
                    Thread.sleep(100);
                } catch (InterruptedException e) {
                    return;
                }
                if (!resultSeq().equals(before)) {
                    // straight back: the menus cover DLS before its hub is drawn
                    activity.runOnUiThread(new ShowTask());
                    return;
                }
            }
        }
    }

    static volatile boolean matchShown;

    /**
     * Called by the game thread through FTTMainActivity.DlsmgrEvent (tools/apk_patch/exhibition.c):
     * 1 = the match has loaded and is on screen, 2 = full time (before DLS shows its own screens).
     */
    public static void nativeEvent(int code) {
        try {
            log(activity.getExternalFilesDir(null), "game event 0x" + Integer.toHexString(code));
        } catch (Throwable t) {
            // ignore
        }
        if ((code & 0xff) == 3) {
            introWeather = (code >> 8) & 0xff;
            introTime = (code >> 16) & 0xff;
            return;  // DLS's intro check is only true for an instant at load; timed below instead
        }
        if (code == 1) {
            matchShown = true;
            introDone = false;
            activity.runOnUiThread(new MatchTask());
            if (!Native.ready) {
                // no cutscene events without the library: time the intro from the match appearing
                startIntro(900);
            } else if (cutActive) {
                // the build-up cutscene started while the match was still loading
                startIntro(400);
            }
        } else if ((code & 0xff) == 16) {
            activity.runOnUiThread(new JsTask("window.dlsAdded && window.dlsAdded(" + ((code >> 8) & 0xff) + ")"));
        } else if ((code & 0xff) == 14) {
            // scoreboard: home goals, away goals, clock (libdlsmgr, on change)
            activity.runOnUiThread(new JsTask("window.dlsHud && window.dlsHud(" + ((code >> 8) & 31) + "," + ((code >> 13) & 31)
                    + "," + ((code >> 24) & 0xff) + "," + ((code >> 18) & 63) + ")"));
        } else if ((code & 0xff) == 11) {
            // cutscene started / ended (libdlsmgr): our intro runs during the build-up cutscene
            // and slides away as soon as it ends, so skipping the cutscene skips it too
            boolean active = ((code >> 16) & 1) != 0;
            cutActive = active;
            if (active && matchShown && !introDone) {
                startIntro(250);
            } else if (!active && introRunning) {
                activity.getWindow().getDecorView().post(new IntroStep(introSeq, 3));
            }
        } else if (code == 12) {
            // replay wipe: the league's logo flashes instead of DLS's
            int seq = ++flashSeq;
            activity.runOnUiThread(new OverlayJsTask("window.dlsReplayFlash && window.dlsReplayFlash()", true, true));
            activity.getWindow().getDecorView().postDelayed(new FlashEnd(seq), 1500);
        } else if (code == 2) {
            introSeq++;
            activity.runOnUiThread(new ShowTask());
        } else if ((code & 0xff) == 9) {
            // DLS opened its pause / half-time screen: ours is drawn instead (DLS's is hidden;
            // the choices run DLS's own resume / team / quit code through Native.pauseAction)
            introSeq++;
            introRunning = false;
            activity.runOnUiThread(new PauseBtnTask(false));
            activity.runOnUiThread(new OverlayJsTask("window.dlsPause && window.dlsPause(" + ((code >> 8) & 0xff) + ","
                    + ((code >> 16) & 0xff) + "," + ((code >> 24) & 0xff) + ")", true, false));
        } else if (code == 15) {
            // full time: DLS's full-time menu is skipped natively; hide our pause button and wait
            // for the result (event 2)
            introSeq++;
            activity.runOnUiThread(new PauseBtnTask(false));
        } else if (code == 10) {
            activity.runOnUiThread(new OverlayJsTask("window.dlsIntroEnd && window.dlsIntroEnd()", false, false));
        }
    }

    /** While our intro plays over the match, touches go through to the game. */
    static volatile boolean touchThrough;

    static final class PassWebView extends WebView {
        PassWebView(Context ctx) {
            super(ctx);
        }

        @Override
        public boolean dispatchTouchEvent(android.view.MotionEvent ev) {
            return !touchThrough && super.dispatchTouchEvent(ev);
        }
    }

    static final class JsTask implements Runnable {
        private final String js;

        JsTask(String js) {
            this.js = js;
        }

        @Override
        public void run() {
            if (web != null) {
                web.evaluateJavascript(js, null);
            }
        }
    }

    static final class PauseBtnTask implements Runnable {
        private final boolean show;

        PauseBtnTask(boolean show) {
            this.show = show;
        }

        @Override
        public void run() {
            if (pauseBtn != null) {
                pauseBtn.setVisibility(show && inMatch ? View.VISIBLE : View.GONE);
            }
        }
    }

    static volatile boolean introDone;
    static volatile boolean introRunning;
    static volatile int flashSeq;

    static void startIntro(long delay) {
        introDone = true;
        introRunning = true;
        int seq = ++introSeq;
        View v = activity.getWindow().getDecorView();
        v.postDelayed(new IntroStep(seq, 1), delay);
        v.postDelayed(new IntroStep(seq, 2), delay + 4000);
        v.postDelayed(new IntroStep(seq, 3), delay + 10000);
    }

    static final class FlashEnd implements Runnable {
        private final int seq;

        FlashEnd(int seq) {
            this.seq = seq;
        }

        @Override
        public void run() {
            if (seq == flashSeq && !introRunning) {
                new OverlayJsTask("window.dlsIntroEnd && window.dlsIntroEnd()", false, true).run();
            }
        }
    }

    static volatile int introSeq;
    static volatile int introWeather;
    static volatile int introTime;

    /** One step of our match intro: 1 team bar, 2 line-ups, 3 slide out, 4 done (dropped if superseded). */
    static final class IntroStep implements Runnable {
        private final int seq;
        private final int step;

        IntroStep(int seq, int step) {
            this.seq = seq;
            this.step = step;
        }

        @Override
        public void run() {
            if (seq != introSeq) {
                return;
            }
            if (step == 1) {
                new OverlayJsTask("window.dlsIntro && window.dlsIntro(" + introWeather + "," + introTime + ")", true, true).run();
            } else if (step == 2) {
                new OverlayJsTask("window.dlsLineups && window.dlsLineups()", true, true).run();
            } else if (step == 3) {
                introSeq++;  // later steps of this intro are dropped
                if (web != null) {
                    final int done = introSeq;
                    web.evaluateJavascript("window.dlsIntroOut && window.dlsIntroOut()", null);
                    web.postDelayed(new IntroStep(done, 4), 550);
                }
            } else {
                introRunning = false;
                new OverlayJsTask("window.dlsIntroEnd && window.dlsIntroEnd()", false, true).run();
            }
        }
    }

    /**
     * Our team intro over DLS's build-up cutscene (DLS's own card is switched off natively):
     * the menus page goes transparent and plays its intro animation, then steps aside.
     */
    static final class IntroTask implements Runnable {
        private final int weather;
        private final int timeOfDay;
        private final boolean start;

        IntroTask(int weather, int timeOfDay, boolean start) {
            this.weather = weather;
            this.timeOfDay = timeOfDay;
            this.start = start;
        }

        @Override
        public void run() {
            if (web == null) {
                return;
            }
            if (start) {
                web.setBackgroundColor(Color.TRANSPARENT);
                web.evaluateJavascript("window.dlsIntro && window.dlsIntro(" + weather + "," + timeOfDay + ")", null);
                web.setVisibility(View.VISIBLE);
                web.bringToFront();
            } else {
                web.evaluateJavascript("window.dlsIntroEnd && window.dlsIntroEnd()", null);
                web.setVisibility(View.GONE);
                web.setBackgroundColor(Color.rgb(11, 14, 13));
            }
        }
    }

    /** If the match-loaded call never arrives within 30 s, the menus report it instead of waiting. */
    static final class LoadTimeout implements Runnable {
        @Override
        public void run() {
            try {
                Thread.sleep(30000);
            } catch (InterruptedException e) {
                return;
            }
            if (!matchShown) {
                activity.runOnUiThread(new KickoffFailedTask());
            }
        }
    }

    /** The match didn't come up: stay in the menus and say so (no DLS screens are drawn now). */
    static final class KickoffFailedTask implements Runnable {
        @Override
        public void run() {
            if (web != null) {
                web.evaluateJavascript("window.dlsKickoffFailed && window.dlsKickoffFailed()", null);
            }
        }
    }

    /** A transparent menus page over the match (line-ups), or back out of it. */
    static final class OverlayJsTask implements Runnable {
        private final String js;
        private final boolean show;
        private final boolean passThrough;

        OverlayJsTask(String js, boolean show, boolean passThrough) {
            this.js = js;
            this.show = show;
            this.passThrough = passThrough;
        }

        @Override
        public void run() {
            if (web == null) {
                return;
            }
            touchThrough = show && passThrough;
            if (show) {
                web.setBackgroundColor(Color.TRANSPARENT);
                web.setVisibility(View.VISIBLE);
                web.bringToFront();
                web.evaluateJavascript(js, null);
            } else if (inMatch) {
                web.evaluateJavascript(js, null);   // back to the plain HUD
                touchThrough = true;
                if (pauseBtn != null) {
                    pauseBtn.setVisibility(View.VISIBLE);
                    pauseBtn.bringToFront();
                }
            } else {
                web.evaluateJavascript(js, null);
                web.setVisibility(View.GONE);
                web.setBackgroundColor(Color.rgb(11, 14, 13));
            }
        }
    }

    /** During a match nothing of ours is on screen (not even the Manager button). */
    /** The match is on screen: the menus page becomes our transparent HUD (scoreboard). */
    static final class MatchTask implements Runnable {
        @Override
        public void run() {
            if (web != null) {
                inMatch = true;
                touchThrough = true;
                reopen.setVisibility(View.GONE);
                web.setBackgroundColor(Color.TRANSPARENT);
                web.setVisibility(View.VISIBLE);
                web.bringToFront();
                web.evaluateJavascript("window.dlsHudMode && window.dlsHudMode()", null);
                pauseBtn.setVisibility(View.VISIBLE);
                pauseBtn.bringToFront();
            }
        }
    }

    static final class PauseClick implements View.OnClickListener {
        @Override
        public void onClick(View v) {
            try {
                if (Native.ready) {
                    Native.pause();
                }
            } catch (Throwable t) {
                lastError = String.valueOf(t);
            }
        }
    }

    /** Leave match mode (full time): hide the HUD pieces. */
    static void endMatchMode() {
        inMatch = false;
        touchThrough = false;
        if (pauseBtn != null) {
            pauseBtn.setVisibility(View.GONE);
        }
        if (web != null) {
            web.setBackgroundColor(Color.rgb(11, 14, 13));   // dlsOnShow ends the HUD and renders the result
        }
    }

    static final class ShowTask implements Runnable {
        @Override
        public void run() {
            endMatchMode();
            Overlay.show();
        }
    }

    /** Named (not anonymous) so d8 handles it; see build notes. */
    static final class HideTask implements Runnable {
        @Override
        public void run() {
            Overlay.hide();
        }
    }

    public static final class Bridge {
        @JavascriptInterface
        public void hide() {
            activity.runOnUiThread(new HideTask());
        }

        @JavascriptInterface
        public void becomeClub(String cid) {
            new Thread(new BecomeTask(cid), "dlsmgr-club").start();
        }

        /**
         * Make DLS's next fixture "player team vs opponent" (home or away), then show DLS so
         * the match is played there. Native side: NativeDialogButton 0x5A5E4000/0x8000 | team.
         */
        @JavascriptInterface
        public String playFixture(String opponent, boolean userHome) {
            try {
                JSONObject clubs = new JSONObject(readText(activity.getAssets().open("dlsmgr/clubs.json")));
                int tid = clubs.getJSONObject(opponent).getInt("tid");
                // v47: an exhibition (tools/apk_patch/exhibition.c) that kicks off straight away:
                // opponent first, then 0x5A5E0004 = start it on the next game frame. The menus
                // come back by themselves at full time (ResultWatch).
                Native.start(activity);
                String before = resultSeq();
                matchShown = false;
                nativeRequest(0x5A5E0000 | (userHome ? 0x4000 : 0x8000) | (tid & 0x3ff));
                nativeRequest(0x5A5E0004);
                // The menus stay up (showing their kick-off screen) while DLS loads the match;
                // the game calls nativeEvent(1) once the match is on screen and nativeEvent(2) at
                // full time. ResultWatch / LoadTimeout are fallbacks if those calls never come.
                new Thread(new ResultWatch(before), "dlsmgr-result").start();
                new Thread(new LoadTimeout(), "dlsmgr-load").start();
                return "";
            } catch (Throwable t) {
                return String.valueOf(t);
            }
        }

        /**
         * Kick off from the menus' pre-match screen with both team sheets. sheets is JSON
         * {"home": {"f": DLS formation 0-11, "ids": [DLS player ids: XI in slot order, then
         * subs and reserves]}, "away": {...}}; they are written to lib+0x7c3f40 / +0x7c3f84
         * for the native kick-off (tools/apk_patch/exhibition.c, make_sheet). A side without a
         * usable sheet plays DLS's own line-up.
         */
        @JavascriptInterface
        public String kickOff(String opponent, boolean userHome, String sheets) {
            try {
                JSONObject clubs = new JSONObject(readText(activity.getAssets().open("dlsmgr/clubs.json")));
                int tid = clubs.getJSONObject(opponent).getInt("tid");
                JSONObject sh = new JSONObject(sheets);
                // v52: /proc/self/mem can't be written on every phone, so the sheets go through
                // the native request channel one byte at a time (0x5A5E3000 = position 0,
                // 0x5A5E2000|b = next byte), into lib+0x7c3f40 (home) and +0x7c3f84 (away).
                byte[] home = sheetBytes(sh.optJSONObject("home"));
                byte[] away = sheetBytes(sh.optJSONObject("away"));
                nativeRequest(0x5A5E0100 | Math.max(1, Math.min(5, sh.optInt("difficulty", 3))));
                nativeRequest(0x5A5E3000);
                for (byte b : home) {
                    nativeRequest(0x5A5E2000 | (b & 0xff));
                }
                for (byte b : away) {
                    nativeRequest(0x5A5E2000 | (b & 0xff));
                }
                Native.start(activity);
                String before = resultSeq();
                matchShown = false;
                nativeRequest(0x5A5E0000 | (userHome ? 0x4000 : 0x8000) | (tid & 0x3ff));
                nativeRequest(0x5A5E0004);
                // The menus stay up (showing their kick-off screen) while DLS loads the match;
                // the game calls nativeEvent(1) once the match is on screen and nativeEvent(2) at
                // full time. ResultWatch / LoadTimeout are fallbacks if those calls never come.
                new Thread(new ResultWatch(before), "dlsmgr-result").start();
                new Thread(new LoadTimeout(), "dlsmgr-load").start();
                return "";
            } catch (Throwable t) {
                lastError = String.valueOf(t);
                return String.valueOf(t);
            }
        }

        /**
         * The last exhibition match, from the file its full-time handler writes
         * (files/dlsmgr_result.txt, see tools/apk_patch/exhibition.c):
         * "home,away,homeGoals,awayGoals,sequence" with DLS team ids (258 = the player's team),
         * or "" before the first one.
         */
        /** Our pause menu's choice: 8 resume, 7 quit, 1 team management (DLS's own buttons). */
        @JavascriptInterface
        public void pauseAction(int id) {
            try {
                if (Native.ready) {
                    Native.pauseAction(id);
                }
            } catch (Throwable t) {
                lastError = String.valueOf(t);
            }
        }

        @JavascriptInterface
        public String lastMatch() {
            return resultLine();
        }

        @JavascriptInterface
        public int clubTid(String cid) {
            try {
                return new JSONObject(readText(activity.getAssets().open("dlsmgr/clubs.json"))).getJSONObject(cid).getInt("tid");
            } catch (Throwable t) {
                return -1;
            }
        }

        @JavascriptInterface
        public void clearFixture() {
            try {
                nativeRequest(0x5A5E0003);
            } catch (Throwable t) {
                lastError = String.valueOf(t);
            }
        }

        @JavascriptInterface
        public String currentClub() {
            try {
                File f = new File(activity.getExternalFilesDir(null), "dlsmgr_club.txt");
                return f.exists() ? readText(new FileInputStream(f)).trim() : "";
            } catch (Throwable t) {
                return "";
            }
        }

        /** Menu career kept in a file as well as WebView storage (survives the app being closed). */
        @JavascriptInterface
        public void saveState(String json) {
            try {
                writeBytes(new File(activity.getExternalFilesDir(null), "dlsmgr_menu_state.json"), json.getBytes("UTF-8"));
            } catch (Throwable t) {
                lastError = String.valueOf(t);
            }
        }

        @JavascriptInterface
        public String loadState() {
            try {
                File f = new File(activity.getExternalFilesDir(null), "dlsmgr_menu_state.json");
                return f.exists() ? readText(new FileInputStream(f)) : "";
            } catch (Throwable t) {
                return "";
            }
        }

        @JavascriptInterface
        public String lastError() {
            return lastError;
        }

        @JavascriptInterface
        public void exportSave() {
            activity.runOnUiThread(new ExportTask());
        }

        @JavascriptInterface
        public boolean isApp() {
            return true;
        }
    }
}
