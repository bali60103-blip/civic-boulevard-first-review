# 各單元圖頁引用之現場照片（2026-10-09）：依 09_photo_features.py（柱型、分隔島植栽、OSM 核實、機車格）與
# 10_photo_reading.py 之判讀依據整理，逐張列出用途標籤 → data/photos/photo_refs_by_zone.json（05 出圖時放入該頁）
import json, re, collections
from pathlib import Path
H = Path(__file__).resolve().parents[1]
rows = {r['id']: r for r in json.load(open(H / 'data/photos/photo_index.json'))}

# (單元, 用途, 照片)：照片可為單張 'IMG_4585'、區間 'IMG_4594-4596'，或限定資料夾 'C:DSC08574-08700'
REFS = [
    ('Z2', '柱型', 'IMG_4585 IMG_4586 IMG_4591 IMG_4592'), ('Z2', '分隔島植栽', 'IMG_4585'), ('Z2', '候車亭', 'IMG_4585 IMG_4586'),
    ('Z2', '地下街出入口', 'IMG_4589'),
    ('Z3', '柱型', 'IMG_4594-4596'), ('Z3', '分隔島植栽', 'IMG_4594'),
    ('Z4', '柱型', 'A/D:DSC08745-08774 IMG_4597-4599'), ('Z4', '分隔島植栽', 'A/D:DSC08745-08774'), ('Z4', '公共藝術', 'DSC08752'),
    ('Z4', '停車場出入口', 'DSC08757 DSC08763'), ('Z4', '候車亭', 'DSC08763 DSC08773'), ('Z4', '地下停車場4號樓梯', 'DSC08765'),
    ('Z4', '舊鐵道引道', 'IMG_4634-4637'),
    ('Z4', '公共藝術（Z4–Z5 交界）', 'DSC08460 DSC08461'), ('Z4', 'YouBike（Z4–Z5 交界）', 'DSC08471 DSC08473'),
    ('Z5', '柱型', 'B/D:DSC08703-08715 B/D:DSC08441-08457'), ('Z5', '分隔島植栽', 'DSC08447 DSC08707'), ('Z5', 'YouBike', 'DSC08706'),
    ('Z5', '公共藝術（Z4–Z5 交界）', 'DSC08460 DSC08461'), ('Z5', 'YouBike（Z4–Z5 交界）', 'DSC08471 DSC08473'),
    ('Z6', '柱型', 'IMG_4675-4680 C:DSC08524-08533'), ('Z6', '分隔島植栽', 'IMG_4678-4680'), ('Z6', '機車格', 'IMG_4676 IMG_4680'),
    ('Z6', 'YouBike', 'IMG_4677 DSC08568'),
    ('Z7', '柱型', 'C:DSC08574-08700'), ('Z7', '分隔島植栽', 'C:DSC08640-08668'), ('Z7', '公共藝術', 'C:DSC08603-08628'),
    ('Z7', '候車亭', 'DSC08688'),
]
def expand(tok):
    fold = None
    if ':' in tok: fold, tok = tok.split(':')
    m = re.match(r'([A-Z]+_?)(\d+)(?:-(\d+))?$', tok)
    pre, a, b = m.group(1), int(m.group(2)), int(m.group(3) or m.group(2))
    out = []
    for pid, r in rows.items():
        if not pid.startswith(pre): continue
        try: n = int(pid[len(pre):])
        except ValueError: continue
        if a <= n <= b and (fold is None or ('/' + fold + '/') in ('/' + r['file'])): out.append(pid)
    return out
by_zone = collections.defaultdict(lambda: collections.defaultdict(list))
for z, tag, toks in REFS:
    for t in toks.split():
        for pid in expand(t):
            if tag not in by_zone[z][pid]: by_zone[z][pid].append(tag)
res = {}
for z in ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'Z7', 'Z8']:
    items = []
    for pid, tags in by_zone.get(z, {}).items():
        r = rows[pid]
        items.append({'id': pid, 'file': r['file'], 'tags': tags, 'gps': 'x' in r,
                      'x': r.get('x'), 'y': r.get('y'), 'heading': r.get('heading'), 'time': r.get('time')})
    items.sort(key=lambda it: (not it['gps'], it['file']))
    res[z] = items
json.dump(res, open(H / 'data/photos/photo_refs_by_zone.json', 'w'), ensure_ascii=False, indent=1)
for z, it in res.items():
    print(z, len(it), 'GPS', sum(i['gps'] for i in it))
