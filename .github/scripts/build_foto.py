"""Prepara le foto del portfolio e scrive foto.js.

1. Ogni foto caricata in foto/ (jpg, png, tif, webp...) viene convertita in WebP,
   lato lungo massimo 2400 px, senza ritagli; l'originale viene sostituito.
2. Per ogni progetto crea la miniatura in miniature/ dalla prima foto.
3. Scrive foto.js con l'elenco delle foto di ogni progetto, in ordine di nome.
"""
import hashlib, json, os, re, sys
from PIL import Image, ImageOps

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
FOTO, MINI = 'foto', 'miniature'
MAX_SIDE, THUMB_W = 2400, 800
EXT = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.webp', '.bmp', '.gif'}
SEC = {'00_home': 'home', '01_studio': 'studio', '02_urban': 'urban', '03_interior': 'interior', '04_art': 'art'}
os.chdir(ROOT)

natkey = lambda s: [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', s)]

def rgb(im):
    im = ImageOps.exif_transpose(im)
    if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
        return im.convert('RGBA')
    return im.convert('RGB')

def fit(im, side):
    w, h = im.size
    s = side / max(w, h)
    return im.resize((round(w * s), round(h * s)), Image.LANCZOS) if s < 1 else im

# 1. conversione
for dp, _, files in os.walk(FOTO):
    for f in sorted(files):
        stem, ext = os.path.splitext(f)
        ext = ext.lower()
        if ext not in EXT:
            continue
        src = os.path.join(dp, f)
        dst = os.path.join(dp, stem + '.webp')
        with Image.open(src) as im0:
            big = max(im0.size) > MAX_SIDE
            if ext == '.webp' and not big:
                continue
            im = fit(rgb(im0), MAX_SIDE)
        im.save(dst + '.tmp', 'WEBP', quality=90, method=6)
        os.replace(dst + '.tmp', dst)
        if src != dst:
            os.remove(src)
        print('foto pronta:', dst)

def photos(folder):
    return sorted([f for f in os.listdir(folder) if f.lower().endswith('.webp')], key=natkey)

def url(path):
    h = hashlib.md5(open(path, 'rb').read()).hexdigest()[:8]
    return f'{path}?v={h}'

data = {'home': [], 'p': {}, 's': {}}
for secdir in sorted(os.listdir(FOTO), key=natkey):
    sec = SEC.get(secdir)
    base = os.path.join(FOTO, secdir)
    if not sec or not os.path.isdir(base):
        continue
    if sec == 'home':
        data['home'] = [url(os.path.join(base, f)) for f in photos(base)]
        continue
    for pdir in sorted(os.listdir(base), key=natkey):
        folder = os.path.join(base, pdir)
        if not os.path.isdir(folder):
            continue
        entity = sec + '/' + re.sub(r'^\d+[_-]', '', pdir)
        lst = [url(os.path.join(folder, f)) for f in photos(folder)]
        if sec == 'studio':
            data['s'][entity] = lst
            continue
        entry = {'f': lst}
        if lst:  # 2. miniatura
            first = os.path.join(folder, photos(folder)[0])
            tdir = os.path.join(MINI, secdir)
            os.makedirs(tdir, exist_ok=True)
            tpath = os.path.join(tdir, pdir + '.webp')
            with Image.open(first) as im:
                im = rgb(im)
                w, h = im.size
                if w > THUMB_W:
                    im = im.resize((THUMB_W, round(h * THUMB_W / w)), Image.LANCZOS)
                im.save(tpath, 'WEBP', quality=85, method=6)
            entry['t'] = url(tpath)
        data['p'][entity] = entry

# miniature di progetti che non esistono più
if os.path.isdir(MINI):
    keep = {os.path.join(MINI, sd, pd + '.webp') for sd in os.listdir(FOTO) if os.path.isdir(os.path.join(FOTO, sd))
            for pd in os.listdir(os.path.join(FOTO, sd)) if os.path.isdir(os.path.join(FOTO, sd, pd))}
    for dp, _, files in os.walk(MINI):
        for f in files:
            p = os.path.join(dp, f)
            if p not in keep:
                os.remove(p)

# 3. elenco per il sito
with open('foto.js', 'w') as fh:
    fh.write('// Generato automaticamente da .github/scripts/build_foto.py: non modificare a mano.\n')
    fh.write('window.ERFOTO = ' + json.dumps(data, ensure_ascii=False, indent=0) + ';\n')
print('foto.js aggiornato:', len(data['p']), 'progetti')
