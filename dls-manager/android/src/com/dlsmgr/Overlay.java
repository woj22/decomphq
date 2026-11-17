package com.dlsmgr;

import android.app.Activity;
import android.content.Context;
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
        public boolean isApp() {
            return true;
        }
    }
}
