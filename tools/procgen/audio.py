"""Synthesised SFX and ambience loops (22.05 kHz mono 16-bit WAV, deterministic)."""
import os, wave
import numpy as np

SR = 22050


def _t(sec):
    return np.arange(int(SR * sec)) / SR


def env(n, a=0.005, d=0.2):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)
    return e


def lp(x, k):
    """one-pole low-pass, k in (0,1]; smaller = darker."""
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc += k * (x[i] - acc); y[i] = acc
    return y


def lp_fast(x, width):
    if width <= 1: return x
    ker = np.ones(width) / width
    return np.convolve(x, ker, mode='same')


def noise(n, seed):
    return np.random.RandomState(seed).uniform(-1, 1, n)


def tone(f, sec, harm=(1,), decay=.5):
    t = _t(sec)
    s = sum(np.sin(2 * np.pi * f * h * t) / (i + 1) for i, h in enumerate(harm))
    return s * env(len(t), .002, decay)


def sfx_tap():
    t = _t(.07); return np.sin(2 * np.pi * 1400 * t) * env(len(t), .001, .012) * .6 + lp_fast(noise(len(t), 1), 3) * env(len(t), .001, .006) * .3


def sfx_page():
    n = int(SR * .35); x = noise(n, 2)
    sweep = np.linspace(0, 1, n)
    e = np.sin(np.pi * sweep) ** 2 * (1 + .5 * np.sin(sweep * 40))
    return (x - lp_fast(x, 6)) * e * .45


def sfx_quill():
    n = int(SR * .18); x = noise(n, 3)
    e = np.zeros(n)
    for s in (0, .05, .1):
        i = int(s * SR); m = min(n - i, int(.04 * SR)); e[i:i + m] += np.exp(-np.arange(m) / (SR * .01))
    return (x - lp_fast(x, 3)) * e * .5


def sfx_door():
    t = _t(.9)
    creak = np.sin(2 * np.pi * (180 + 60 * np.sin(2 * np.pi * 3 * t)) * t) * np.exp(-t / .4) * .25
    thud = lp_fast(noise(len(t), 4), 40) * 6 * np.exp(-np.maximum(t - .55, 0) / .12) * (t > .55)
    thud += np.sin(2 * np.pi * 60 * t) * np.exp(-np.maximum(t - .55, 0) / .15) * (t > .55) * .6
    return creak + thud


def sfx_stamp():
    t = _t(.45)
    body = np.sin(2 * np.pi * 85 * t * (1 - .3 * t)) * np.exp(-t / .09)
    click = lp_fast(noise(len(t), 5), 8) * 4 * np.exp(-t / .015)
    return (body * .8 + click * .5)


def sfx_bell():
    t = _t(2.2)
    s = sum(a * np.sin(2 * np.pi * 523 * r * t) * np.exp(-t / d) for r, a, d in
            ((1, .5, 1.2), (2.0, .25, .7), (2.76, .2, .5), (5.4, .1, .25), (.5, .2, 1.6)))
    return s * np.minimum(1, t / .002)


def sfx_link():
    t = _t(.5)
    a = np.sin(2 * np.pi * 660 * t) * np.exp(-t / .15) * (t < .25)
    b = np.sin(2 * np.pi * 990 * t) * np.exp(-np.maximum(t - .12, 0) / .2) * (t > .12)
    return (a + b) * .4


def loop_bed(sec, seed, drone, hiss, extra=None):
    n = int(SR * sec); t = np.arange(n) / SR
    x = lp_fast(noise(n, seed), 60) * hiss
    for f, a in drone:
        # integer cycles per loop so it wraps seamlessly
        f2 = round(f * sec) / sec
        x += a * np.sin(2 * np.pi * f2 * t) * (0.8 + 0.2 * np.sin(2 * np.pi * t / sec))
    if extra:
        x += extra(t, n)
    # crossfade tail into head for a seamless loop
    k = int(SR * .25)
    x[:k] = x[:k] * np.linspace(0, 1, k) + x[-k:] * np.linspace(1, 0, k)
    return x[:-k] if False else x


def ticks(t, n, rate, seed, freq=2000, amp=.05, dec=.004):
    rng = np.random.RandomState(seed); out = np.zeros(n)
    for _ in range(int(t[-1] * rate)):
        i = rng.randint(0, n - 400); m = 300
        out[i:i + m] += np.sin(2 * np.pi * freq * np.arange(m) / SR) * np.exp(-np.arange(m) / (SR * dec)) * amp * rng.uniform(.4, 1)
    return out


AMB = {
    'amb_court': lambda: loop_bed(8, 11, [(55, .08), (82.5, .05)], .5,
                                  lambda t, n: lp_fast(noise(n, 12), 300) * 3 * (.5 + .5 * np.sin(2 * np.pi * t / 8))),
    'amb_hall': lambda: loop_bed(8, 13, [(65, .05), (97.5, .03)], .7,
                                 lambda t, n: ticks(t, n, 3, 14, 900, .04, .02) + lp_fast(noise(n, 15), 20) * .15),
    'amb_records': lambda: loop_bed(8, 16, [(48, .04)], .25, lambda t, n: ticks(t, n, 2, 17, 2400, .05, .003)),
    'amb_booths': lambda: loop_bed(8, 18, [(60, .05), (90, .03)], .4, lambda t, n: ticks(t, n, 1.5, 19, 3000, .04, .002)),
    'amb_chamber': lambda: loop_bed(8, 20, [(41, .07), (61.5, .05), (123, .02)], .3),
}
SFX = {'sfx_tap': sfx_tap, 'sfx_page': sfx_page, 'sfx_quill': sfx_quill, 'sfx_door': sfx_door, 'sfx_stamp': sfx_stamp,
       'sfx_bell': sfx_bell, 'sfx_link': sfx_link}


def write(path, x, peak=.7):
    x = np.asarray(x, float)
    m = np.abs(x).max() or 1
    x = (x / m * peak * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(x.tobytes())


def build(outdir):
    os.makedirs(outdir, exist_ok=True)
    for k, f in SFX.items():
        write(os.path.join(outdir, k + '.wav'), f(), .8)
    for k, f in AMB.items():
        write(os.path.join(outdir, k + '.wav'), f(), .35)
    return sorted(list(SFX) + list(AMB))
