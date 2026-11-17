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
 *   becomeClub(id) - your team becomes that club, live (per-club saves, native save/reload)
 *   currentClub() - the club the Dream FC currently is ("" if none), lastError()
 * A small "Manager" button brings the menus back while they are hidden.
 */
public final class Overlay {
    private static WebView web;
    private static View reopen;
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

        WebView w = new WebView(activity);
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
    }

    static void show() {
        if (web == null) {
            return;
        }
        web.setVisibility(View.VISIBLE);
        web.bringToFront();
        reopen.setVisibility(View.GONE);
    }

    static void hide() {
        if (web == null) {
            return;
        }
        web.setVisibility(View.GONE);
        reopen.setVisibility(View.VISIBLE);
        reopen.bringToFront();
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
            // A club switch that did not survive its reload (app died within 8 s): go back to
            // the previous club's save.
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
                    lastError = "The club switch failed, so your previous team was restored.";
                }
                switching.delete();
            }
        } catch (Throwable t) {
            lastError = String.valueOf(t);
        }
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

    /**
     * Live club switch, no restart. Each club keeps its own save in DOCS/dlsmgr_saves/<club>.dat
     * (the player's original team is "original"):
     *   1. ask the game to save (native hook, see patch_apk.py) and wait for profile.dat to change
     *   2. file profile.dat under the current club
     *   3. load the target club's save, or create it from the original save (Profile.becomeClub)
     *   4. copy the club's kits/badge to the player team, ask the game to reload the profile
     * Runs on a worker thread; the native work happens on the game thread at the next frame.
     */
    static void becomeClub(String cid) {
        try {
            Context ctx = activity;
            File dir = ctx.getExternalFilesDir(null);
            File prof = new File(dir, "profile.dat");
            File saves = new File(dir, "dlsmgr_saves");
            saves.mkdirs();
            File currentF = new File(dir, "dlsmgr_club.txt");
            String cur = currentF.exists() ? readText(new FileInputStream(currentF)).trim() : "original";
            if (cur.length() == 0) {
                cur = "original";
            }
            if (cur.equals(cid)) {
                return;
            }
            long before = prof.lastModified();
            nativeRequest(0x5A5E0001);
            for (int i = 0; i < 40 && prof.lastModified() == before; i++) {
                Thread.sleep(100);
            }
            Thread.sleep(300);  // let the write finish
            byte[] now = readBytes(new FileInputStream(prof));
            Profile.decode(now);  // only file a save that reads back
            writeBytes(new File(saves, cur + ".dat"), now);

            File target = new File(saves, cid + ".dat");
            byte[] out;
            if (target.exists()) {
                out = readBytes(new FileInputStream(target));
            } else {
                File orig = new File(saves, "original.dat");
                byte[] base = orig.exists() ? readBytes(new FileInputStream(orig)) : now;
                JSONObject clubs = new JSONObject(readText(ctx.getAssets().open("dlsmgr/clubs.json")));
                out = Profile.encode(Profile.becomeClub(Profile.decode(base), clubs.getJSONObject(cid)));
            }
            Profile.decode(out);
            writeBytes(prof, out);
            new File(dir, "profile_temp.dat").delete();
            writeBytes(currentF, cid.getBytes("UTF-8"));
            copyClubLooks(ctx, dir);
            File switching = new File(dir, "dlsmgr_switching.txt");
            writeBytes(switching, cur.getBytes("UTF-8"));  // removed once the reload has survived
            nativeRequest(0x5A5E0002);
            activity.runOnUiThread(new ToastTask("You are now " + clubName(ctx, cid)));
            Thread.sleep(8000);
            switching.delete();
        } catch (Throwable t) {
            lastError = String.valueOf(t);
            activity.runOnUiThread(new ToastTask("Could not switch club: " + t));
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

    private static void copy(InputStream in, File to) throws java.io.IOException {
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
                    if (f.isFile() && name.endsWith(".dat")) {
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
                nativeRequest(0x5A5E0000 | (userHome ? 0x4000 : 0x8000) | (tid & 0x3FF));
                String name = clubs.getJSONObject(opponent).getString("name");
                activity.runOnUiThread(new HideTask());
                activity.runOnUiThread(new ToastTask("Next match set: " + (userHome ? "vs " : "at ") + name
                        + ". Tap Play in DLS to kick off."));
                return "";
            } catch (Throwable t) {
                return String.valueOf(t);
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
