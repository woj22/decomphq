package com.dlsmgr;

import android.content.Context;

import java.io.File;
import java.io.FileInputStream;

/**
 * libdlsmgr.so (android/native/dlsmgr.c): our own native code next to libDLS19.so. It is
 * bundled as assets/dlsmgr/native/libdlsmgr.so, copied to the app's files and loaded once
 * libDLS19.so is in memory; init() gives it the game library's load address.
 */
final class Native {
    static boolean ready;

    static native int probe(long start);

    static native void init(long libBase, Class<?> overlay);

    static native void pauseAction(int id);

    /** The user's live sheet: side, formation, mentality, subs left, count, then id / flags pairs. */
    static native int[] getSheet();

    /** Queue a swap (kind 1) or tactics change (kind 2) for the game thread; 0 if one is pending. */
    static native int sheetOp(int kind, int a, int b);

    /** Team stats, events and player counters of the match so far (see dlsmgr.c). */
    static native int[] stats();

    /** Queue a team's squad (DLS player ids, 11-32) to be written into DLS's team record. */
    static native int setRoster(int team, int[] ids);

    /** Queue players (DLS ids) whose in-game face DLS should render (event 20 / 21 per player). */
    static native int renderFaces(int[] ids);

    /** Our pause button: opens DLS's pause screen (FUN_0018fdf0) on the next game frame. */
    static native void pause();

    /** Load and initialise; safe to call repeatedly (does nothing once ready). */
    static void start(Context ctx) {
        if (ready) {
            return;
        }
        try {
            File so = new File(ctx.getFilesDir(), "libdlsmgr.so");
            Overlay.copy(ctx.getAssets().open("dlsmgr/native/libdlsmgr.so"), so);
            System.load(so.getAbsolutePath());
            long base = findBase();
            if (base == 0) {
                Overlay.lastError = "libDLS19.so not found in memory";
                return;
            }
            init(base, Overlay.class);
            ready = true;
            Overlay.log(ctx.getExternalFilesDir(null), "native library ready, game at 0x" + Long.toHexString(base));
        } catch (Throwable t) {
            Overlay.lastError = "native library: " + t;
            Overlay.log(ctx.getExternalFilesDir(null), "native library failed: " + t);
        }
    }

    /** Candidate mappings from /proc/self/maps, confirmed by the library itself. */
    static long findBase() throws Exception {
        java.io.BufferedReader br = new java.io.BufferedReader(new java.io.FileReader("/proc/self/maps"));
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
                long end = Long.parseLong(f[0].substring(f[0].indexOf('-') + 1), 16);
                if (end - start > 0x3ee120 && probe(start) != 0) {
                    return start;
                }
            }
        } finally {
            br.close();
        }
        return 0;
    }
}
