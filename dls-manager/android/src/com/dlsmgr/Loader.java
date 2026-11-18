package com.dlsmgr;

import android.app.Activity;
import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.LinearGradient;
import android.graphics.Paint;
import android.graphics.RectF;
import android.graphics.Shader;
import android.os.SystemClock;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.FrameLayout;
import android.widget.ImageView;

import java.io.InputStream;

/**
 * Assistant Manager 27 loading screen, over everything while the game starts (DLS's own First
 * Touch splash and loading screens are drawn underneath and never seen).
 *
 * The owner's paintings (assets/dlsmgr/bg/load_N.jpg) fade into one another with a slow zoom,
 * under the AM27 logo and a spinning ring. It goes when the menus page says it has drawn
 * (DLSManager.loaded()), but not before MIN_MS, and in any case after MAX_MS.
 */
final class Loader {
    private static final int PICTURES = 4;
    private static final long SHOW_MS = 2800, FADE_MS = 1000, MIN_MS = 3500, MAX_MS = 30000;
    private static FrameLayout root;
    private static ImageView[] img = new ImageView[2];
    private static int front, next;
    private static long shownAt;
    private static boolean leaving;

    private Loader() {}

    static void show(Activity a) {
        if (root != null) {
            return;
        }
        ViewGroup decor = (ViewGroup) a.getWindow().getDecorView();
        float dp = a.getResources().getDisplayMetrics().density;
        FrameLayout f = new FrameLayout(a);
        f.setBackgroundColor(Color.rgb(8, 12, 11));
        f.setClickable(true);  // nothing underneath gets touches while loading
        for (int i = 0; i < 2; i++) {
            ImageView v = new ImageView(a);
            v.setScaleType(ImageView.ScaleType.CENTER_CROP);
            v.setAlpha(0f);
            f.addView(v, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
            img[i] = v;
        }
        f.addView(new Shade(a), new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        ImageView logo = new ImageView(a);
        logo.setImageBitmap(load(a, "dlsmgr/bg/am27_logo.png", 1));
        logo.setAdjustViewBounds(true);
        FrameLayout.LayoutParams llp = new FrameLayout.LayoutParams((int) (190 * dp), ViewGroup.LayoutParams.WRAP_CONTENT, Gravity.BOTTOM | Gravity.START);
        llp.setMargins((int) (28 * dp), 0, 0, (int) (26 * dp));
        f.addView(logo, llp);
        FrameLayout.LayoutParams slp = new FrameLayout.LayoutParams((int) (34 * dp), (int) (34 * dp), Gravity.BOTTOM | Gravity.END);
        slp.setMargins(0, 0, (int) (30 * dp), (int) (32 * dp));
        f.addView(new Spinner(a, dp), slp);
        decor.addView(f, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        root = f;
        shownAt = SystemClock.uptimeMillis();
        front = 0;
        next = (int) (System.currentTimeMillis() / 1000 % PICTURES);
        step(a);
        f.postDelayed(new Runnable() {
            @Override
            public void run() {
                done();
            }
        }, MAX_MS);
    }

    /** Keep the loading screen above views the overlay adds or raises while it is up. */
    static void top() {
        if (root != null) {
            root.bringToFront();
        }
    }

    /** The menus have drawn: go once the minimum time has passed. */
    static void done() {
        if (root == null || leaving) {
            return;
        }
        long wait = MIN_MS - (SystemClock.uptimeMillis() - shownAt);
        if (wait > 0) {
            root.postDelayed(new Runnable() {
                @Override
                public void run() {
                    done();
                }
            }, wait);
            return;
        }
        leaving = true;
        final FrameLayout f = root;
        f.animate().alpha(0f).setDuration(600).withEndAction(new Runnable() {
            @Override
            public void run() {
                ViewGroup p = (ViewGroup) f.getParent();
                if (p != null) {
                    p.removeView(f);
                }
                for (int i = 0; i < 2; i++) {
                    img[i].setImageDrawable(null);
                    img[i] = null;
                }
                root = null;
            }
        }).start();
    }

    // the next picture fades in over the current one, zooming slowly
    private static void step(final Activity a) {
        if (root == null || leaving) {
            return;
        }
        Bitmap b = load(a, "dlsmgr/bg/load_" + (next % PICTURES + 1) + ".jpg", 0);
        next++;
        final ImageView in = img[front], out = img[1 - front];
        front = 1 - front;
        if (b != null) {
            in.setImageBitmap(b);
        }
        in.setAlpha(0f);
        in.setScaleX(1.0f);
        in.setScaleY(1.0f);
        // cross-fade (the two pictures stay below the shade, logo and spinner)
        in.animate().scaleX(1.07f).scaleY(1.07f).setDuration(SHOW_MS + FADE_MS * 2).start();
        in.animate().setDuration(FADE_MS).alpha(1f).start();
        out.animate().alpha(0f).setDuration(FADE_MS).start();
        in.postDelayed(new Runnable() {
            @Override
            public void run() {
                step(a);
            }
        }, SHOW_MS + FADE_MS);
    }

    /** Asset bitmap, scaled down when far bigger than the screen. */
    private static Bitmap load(Context c, String path, int sample) {
        try {
            BitmapFactory.Options o = new BitmapFactory.Options();
            o.inSampleSize = sample <= 0 ? (c.getResources().getDisplayMetrics().widthPixels < 1100 ? 2 : 1) : sample;
            InputStream in = c.getAssets().open(path);
            try {
                return BitmapFactory.decodeStream(in, null, o);
            } finally {
                in.close();
            }
        } catch (Throwable t) {
            return null;
        }
    }

    /** Darkening along the bottom (under the logo) and a soft vignette at the top. */
    static final class Shade extends View {
        private final Paint p = new Paint();

        Shade(Context c) {
            super(c);
        }

        @Override
        protected void onDraw(Canvas cv) {
            int w = getWidth(), h = getHeight();
            p.setShader(new LinearGradient(0, 0, 0, h, new int[] {Color.argb(90, 0, 0, 0), Color.argb(0, 0, 0, 0), Color.argb(0, 0, 0, 0), Color.argb(200, 4, 8, 7)},
                    new float[] {0f, 0.25f, 0.55f, 1f}, Shader.TileMode.CLAMP));
            cv.drawRect(0, 0, w, h, p);
        }
    }

    /** A ring with a green arc chasing round it. */
    static final class Spinner extends View {
        private final Paint ring = new Paint(Paint.ANTI_ALIAS_FLAG), arc = new Paint(Paint.ANTI_ALIAS_FLAG);
        private final RectF r = new RectF();
        private final long t0 = SystemClock.uptimeMillis();

        Spinner(Context c, float dp) {
            super(c);
            ring.setStyle(Paint.Style.STROKE);
            ring.setStrokeWidth(3.5f * dp);
            ring.setColor(Color.argb(70, 255, 255, 255));
            arc.setStyle(Paint.Style.STROKE);
            arc.setStrokeWidth(3.5f * dp);
            arc.setStrokeCap(Paint.Cap.ROUND);
            arc.setColor(Color.rgb(76, 200, 106));
        }

        @Override
        protected void onDraw(Canvas cv) {
            float s = ring.getStrokeWidth();
            r.set(s, s, getWidth() - s, getHeight() - s);
            cv.drawOval(r, ring);
            long t = SystemClock.uptimeMillis() - t0;
            float start = (t % 1100) * 360f / 1100f;
            float sweep = 70f + 110f * (float) Math.abs(Math.sin(t / 700.0));
            cv.drawArc(r, start, sweep, false, arc);
            if (root != null) {
                postInvalidateOnAnimation();
            }
        }
    }
}
