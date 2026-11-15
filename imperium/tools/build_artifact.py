"""Package web/ as a self-contained static bundle (dist_artifact/): rewrites bare 'three' imports to relative
paths (no import map needed) and copies only the three.js addon files the game actually imports."""
import os, re, shutil, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, 'web')
OUT = os.environ.get('OUT', os.path.join(ROOT, 'dist_artifact'))
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)
IMP = re.compile(r"""((?:import|export)[^'"]*?from\s*|import\s*\(?\s*)(['"])([^'"]+)\2""")
done, todo = set(), ['src/main.js']
def resolve(src, spec):
    if spec == 'three':
        return 'vendor/three.module.js'
    if spec.startswith('three/addons/'):
        return 'vendor/jsm/' + spec[len('three/addons/'):]
    return os.path.normpath(os.path.join(os.path.dirname(src), spec))
while todo:
    f = todo.pop()
    if f in done:
        continue
    done.add(f)
    text = open(os.path.join(WEB, f)).read()
    if f != 'vendor/three.module.js':
        def sub(m):
            tgt = resolve(f, m.group(3))
            todo.append(tgt)
            rel = os.path.relpath(tgt, os.path.dirname(f))
            if not rel.startswith('.'):
                rel = './' + rel
            return m.group(1) + m.group(2) + rel + m.group(2)
        text = IMP.sub(sub, text)
    os.makedirs(os.path.join(OUT, os.path.dirname(f)), exist_ok=True)
    open(os.path.join(OUT, f), 'w').write(text)
os.makedirs(os.path.join(OUT, 'data'), exist_ok=True)
shutil.copy(os.path.join(WEB, 'data', 'citymap.json'), os.path.join(OUT, 'data'))
shutil.copy(os.path.join(WEB, 'style.css'), OUT)
html = open(os.path.join(WEB, 'index.html')).read()
body = html[html.index('<body>') + 6:html.index('</body>')]
head = html[html.index('<head>') + 6:html.index('</head>')]
head = re.sub(r'<script type="importmap">.*?</script>', '', head, flags=re.S)
head = re.sub(r'<meta charset[^>]*>\s*|<meta name="viewport"[^>]*>\s*', '', head)
css = open(os.path.join(WEB, 'style.css')).read()
head = head.replace('<link rel="stylesheet" href="style.css">', '<style>\n:root { color-scheme: dark; }\n' + css + '</style>')
open(os.path.join(OUT, 'index.html'), 'w').write((head.strip() + '\n' + body.strip() + '\n').encode('ascii', 'xmlcharrefreplace').decode())
print(json.dumps(sorted(done)))
