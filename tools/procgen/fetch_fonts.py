#!/usr/bin/env python3
"""Fetch the bundled UI fonts (PROJECT §9.6) into game/assets/fonts/ with their licence files.

Run once (network needed); results are committed. Any font that fails is skipped (Engine falls back to the
default font). Not part of build_assets.py so the art build stays offline and deterministic.
"""
import io, os, sys, urllib.request, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'game', 'assets', 'fonts')
GF = 'https://raw.githubusercontent.com/google/fonts/main/ofl'

# (name, [(url, member-in-zip-or-None, out-filename)])
FONTS = [
    ('Jacquard 24', [(f'{GF}/jacquard24/Jacquard24-Regular.ttf', None, 'Jacquard24-Regular.ttf'),
                     (f'{GF}/jacquard24/OFL.txt', None, 'Jacquard24-OFL.txt')]),
    ('Jersey 20', [(f'{GF}/jersey20/Jersey20-Regular.ttf', None, 'Jersey20-Regular.ttf'),
                   (f'{GF}/jersey20/OFL.txt', None, 'Jersey20-OFL.txt')]),
    ('Departure Mono', [
        ('https://github.com/rektdeckard/departure-mono/releases/download/v1.500/DepartureMono-1.500.zip',
         'DepartureMono-1.500/DepartureMono-Regular.otf', 'DepartureMono-Regular.otf'),
        ('https://github.com/rektdeckard/departure-mono/releases/download/v1.500/DepartureMono-1.500.zip',
         'DepartureMono-1.500/LICENSE', 'DepartureMono-OFL.txt')]),
    ('Pixel Operator', [
        ('https://dl.dafont.com/dl/?f=pixel_operator', 'PixelOperator.ttf', 'PixelOperator.ttf'),
        ('https://dl.dafont.com/dl/?f=pixel_operator', 'PixelOperator-Bold.ttf', 'PixelOperator-Bold.ttf'),
        ('https://dl.dafont.com/dl/?f=pixel_operator', 'LICENSE.txt', 'PixelOperator-CC0.txt')]),
]

_cache = {}


def get(url):
    if url not in _cache:
        req = urllib.request.Request(url, headers={'User-Agent': 'asset-build/1.0'})
        with urllib.request.urlopen(req, timeout=30) as r:
            _cache[url] = r.read()
    return _cache[url]


def main():
    os.makedirs(OUT, exist_ok=True)
    ok = []
    for name, files in FONTS:
        try:
            blobs = []
            for url, member, fn in files:
                data = get(url)
                if member:
                    data = zipfile.ZipFile(io.BytesIO(data)).read(member)
                blobs.append((fn, data))
            for fn, data in blobs:
                with open(os.path.join(OUT, fn), 'wb') as f:
                    f.write(data)
            ok.append(name)
            print('ok  ', name)
        except Exception as e:  # skip any font that cannot be fetched
            print('skip', name, '-', e, file=sys.stderr)
    print(f'{len(ok)}/{len(FONTS)} fonts vendored into {OUT}')


if __name__ == '__main__':
    main()
