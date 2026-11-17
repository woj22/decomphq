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
 *   becomeClub(id) - make the Dream FC that club (applied on restart, before the save loads)
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
        decor.postDelayed(new BootOk(), 30000);

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
     * Dream FC = the club picked in the manager menus.
     *
     * becomeClub(id) (from the menus) writes DOCS/dlsmgr_pending_club.txt and restarts the app.
     * On the next start, before the game reads the save, applyClub() backs up profile.dat
     * (profile_backup_before_<club>.dat), rewrites the Dream FC as that club (squad from
     * assets/dlsmgr/clubs.json, see Profile.becomeClub) and records it in dlsmgr_club.txt.
     * On every start it then copies the club's kit and badge files to the Dream FC's (258).
     */
    static void applyClub(Context ctx) {
        File dir = ctx.getExternalFilesDir(null);
        if (dir == null) {
            return;
        }
        File pending = new File(dir, "dlsmgr_pending_club.txt");
        File current = new File(dir, "dlsmgr_club.txt");
        File prof0 = new File(dir, "profile.dat");
        File last = new File(dir, "profile_backup_last.dat");
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
            // Crash guard: starts are counted and the count is cleared after 30 s of normal
            // running (see create()). Two failed starts in a row after a club switch -> the
            // save from just before the switch is restored.
            File boots = new File(dir, "dlsmgr_boot.txt");
            int n = 0;
            if (boots.exists()) {
                try {
                    n = Integer.parseInt(readText(new FileInputStream(boots)).trim());
                } catch (Throwable t) {
                    n = 0;
                }
            }
            if (n >= 2 && last.exists() && current.exists()) {
                copy(new FileInputStream(last), prof0);
                new File(dir, "profile_temp.dat").delete();
                current.delete();
                lastError = "The game failed to start after the club switch, so your previous save was restored.";
                n = 0;
            }
            writeBytes(boots, String.valueOf(n + 1).getBytes("UTF-8"));
        } catch (Throwable t) {
            lastError = String.valueOf(t);
        }
        try {
            if (pending.exists()) {
                String cid = readText(new FileInputStream(pending)).trim();
                JSONObject clubs = new JSONObject(readText(ctx.getAssets().open("dlsmgr/clubs.json")));
                JSONObject club = clubs.getJSONObject(cid);
                File prof = new File(dir, "profile.dat");
                byte[] file = readBytes(new FileInputStream(prof));
                File backup = new File(dir, "profile_backup_before_" + cid + ".dat");
                if (!backup.exists()) {
                    writeBytes(backup, file);
                }
                writeBytes(last, file);
                byte[] out = Profile.encode(Profile.becomeClub(Profile.decode(file), club));
                Profile.decode(out);  // must read back cleanly before it replaces the save
                writeBytes(prof, out);
                new File(dir, "profile_temp.dat").delete();
                writeBytes(current, cid.getBytes("UTF-8"));
                pending.delete();
            }
        } catch (Throwable t) {
            pending.delete();  // never retry a failing conversion on every start
            lastError = String.valueOf(t);
        }
        try {
            if (current.exists()) {
                String cid = readText(new FileInputStream(current)).trim();
                JSONObject clubs = new JSONObject(readText(ctx.getAssets().open("dlsmgr/clubs.json")));
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

    /** Called from the menus: remember the club and restart so applyClub runs before the save loads. */
    static void becomeClub(String cid) {
        try {
            File dir = activity.getExternalFilesDir(null);
            writeBytes(new File(dir, "dlsmgr_pending_club.txt"), cid.getBytes("UTF-8"));
            Intent launch = activity.getPackageManager().getLaunchIntentForPackage(activity.getPackageName());
            if (launch != null) {
                launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
                android.app.PendingIntent pi = android.app.PendingIntent.getActivity(activity, 1937, launch,
                        android.app.PendingIntent.FLAG_CANCEL_CURRENT | 0x04000000 /* FLAG_IMMUTABLE */);
                android.app.AlarmManager am = (android.app.AlarmManager) activity.getSystemService(Context.ALARM_SERVICE);
                am.set(android.app.AlarmManager.RTC, System.currentTimeMillis() + 1000, pi);
            }
            Toast.makeText(activity, "Setting up your club - the game restarts", Toast.LENGTH_LONG).show();
            activity.finishAffinity();
            android.os.Process.killProcess(android.os.Process.myPid());
        } catch (Throwable t) {
            Toast.makeText(activity, "Could not switch club: " + t, Toast.LENGTH_LONG).show();
        }
    }

    /** 30 s after the menus appear the game is clearly running: clear the crash-guard count. */
    static final class BootOk implements Runnable {
        @Override
        public void run() {
            try {
                writeBytes(new File(activity.getExternalFilesDir(null), "dlsmgr_boot.txt"), "0".getBytes("UTF-8"));
            } catch (Throwable t) {
                // ignore
            }
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
            activity.runOnUiThread(new BecomeTask(cid));
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
