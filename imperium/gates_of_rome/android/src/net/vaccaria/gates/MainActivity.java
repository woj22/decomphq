package net.vaccaria.gates;

import android.app.Activity;
import android.graphics.Color;
import android.os.Bundle;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/** The Caldera Council: the game page in a WebView, plus a small bridge so it can call the OpenAI API. */
public class MainActivity extends Activity {
    private WebView web;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        int basalt = Color.parseColor("#14100e");
        getWindow().setStatusBarColor(basalt);
        getWindow().setNavigationBarColor(basalt);
        web = new WebView(this);
        web.setBackgroundColor(basalt);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);          // the saved reign and settings live in local storage
        s.setAllowFileAccess(true);
        web.setWebChromeClient(new WebChromeClient());
        web.addJavascriptInterface(new Http(), "NativeHttp");
        setContentView(web);
        if (state != null) web.restoreState(state);
        else web.loadUrl("file:///android_asset/index.html");
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    /** HTTP POST for the page, so API calls don't depend on the browser's cross-origin rules. */
    private class Http {
        @JavascriptInterface
        public void post(String id, String url, String key, String body) {
            new Thread(new Request(id, url, key, body)).start();
        }
    }

    private class Request implements Runnable {
        private final String id, url, key, body;

        Request(String id, String url, String key, String body) {
            this.id = id; this.url = url; this.key = key; this.body = body;
        }

        public void run() {
            boolean ok = true;
            String text;
            try {
                HttpURLConnection c = (HttpURLConnection) new URL(url).openConnection();
                c.setRequestMethod("POST");
                c.setDoOutput(true);
                c.setConnectTimeout(20000);
                c.setReadTimeout(120000);
                c.setRequestProperty("Content-Type", "application/json");
                c.setRequestProperty("Authorization", "Bearer " + key);
                OutputStream o = c.getOutputStream();
                o.write(body.getBytes("UTF-8"));
                o.close();
                int code = c.getResponseCode();
                InputStream in = code >= 400 ? c.getErrorStream() : c.getInputStream();
                ByteArrayOutputStream buf = new ByteArrayOutputStream();
                byte[] chunk = new byte[8192];
                int n;
                while (in != null && (n = in.read(chunk)) > 0) buf.write(chunk, 0, n);
                text = buf.toString("UTF-8");
            } catch (Exception e) {
                ok = false;
                text = String.valueOf(e.getMessage());
            }
            runOnUiThread(new Deliver("window.__nativeDone(" + JSONObject.quote(id) + "," + ok + "," + JSONObject.quote(text) + ")"));
        }
    }

    private class Deliver implements Runnable {
        private final String js;

        Deliver(String js) { this.js = js; }

        public void run() { web.evaluateJavascript(js, null); }
    }
}
