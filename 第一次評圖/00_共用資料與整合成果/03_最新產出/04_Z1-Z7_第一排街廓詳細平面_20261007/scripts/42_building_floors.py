# 建物樓高分級（2026-10-15 使用者：「把建物輪廓圖色套疊樓高參數進去調深淺；0–5 層一種深淺、6–11 層一種，級距隨樓高變大」）
#   級距（層）：0–5｜6–11｜12–19｜20–29｜30 以上（級寬 6、6、8、10、開放）；層數＝高度 ÷ 3.3 m（同 17 SRC_RULE、07 簡報 P15）。
#   樓高來源：臺北三維模型（2017，tpe3d 圖磚 3847／4347；approximate）——07_簡報_斷裂與揭露_20261014/data/臺北三維模型2017_圖幅_EPSG3826.geojson
#     （與簡報 P15 v6 樓高灰階同源）。方法同 07 04_slides.py height_layers：量體與線稿建物之交集逐一分級（裙樓、塔樓分開）；
#     建物未被量體覆蓋之部分取重疊最大量體之高度；完全無量體者以土地使用判讀樓層（03 landuse_pieces levels）；再無者列最低級（src＝無資料）。
#   輸出 data/building_floors_EPSG3826.geojson（全線圖框內之線稿建物切片：floors 估計層數、cls 0–4、src）；20 G_BLD0–4、21、36 圖例讀取。
import json, collections, importlib.util
from pathlib import Path
from shapely.geometry import shape, mapping, box
from shapely.ops import unary_union
from shapely.strtree import STRtree

H = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sheet', H / 'scripts/02_sheet.py')
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
V3F = H.parents[0] / '07_簡報_斷裂與揭露_20261014/data/臺北三維模型2017_圖幅_EPSG3826.geojson'
LUF = H.parents[0] / '03_南京至仁愛_沿線土地使用分析_20261006/data/landuse_pieces_EPSG3826.geojson'
FLOOR_M = 3.3
BINS = [5, 11, 19, 29]                                   # 各級上限（層）；第 5 級＝30 層以上
LABELS = ['0–5 層', '6–11 層', '12–19 層', '20–29 層', '30 層以上']
def cls_of(fl): return sum(fl > t for t in BINS)
def floors_of(h): return int(round(h / FLOOR_M))

FRAME = box(300935, 2770000, 307545, 2771910)            # 全線圖框（同 20 map_frame TF）
V3 = [(shape(f['geometry']).buffer(0), float(f['properties']['height'])) for f in json.load(open(V3F))['features'] if f['properties'].get('height')]
t3 = STRtree([g for g, _ in V3])
LU = [(shape(f['geometry']), f['properties']['levels']) for f in json.load(open(LUF))['features'] if f['properties'].get('levels')]
tl = STRtree([g for g, _ in LU])
feats, n = [], collections.Counter()
def add(g, fl, src):
    for q in getattr(g, 'geoms', [g]):
        if q.geom_type == 'Polygon' and q.area >= .5:
            feats.append({'type': 'Feature', 'geometry': mapping(q), 'properties': {'floors': fl, 'cls': cls_of(fl), 'label': LABELS[cls_of(fl)], 'src': src}})
for b in S.polys(S.bld.intersection(FRAME)):
    parts = [(V3[i][0].intersection(b), V3[i][1]) for i in t3.query(b) if V3[i][0].intersects(b)]
    parts = [(x, h) for x, h in parts if x.area >= 1]
    if parts:
        n['三維模型'] += 1
        rest = b.difference(unary_union([x for x, _ in parts]))
        if rest.area >= 1: add(rest, floors_of(max(parts, key=lambda t: t[0].area)[1]), '三維模型（未覆蓋部分取重疊最大量體）')
        for x, h in parts: add(x, floors_of(h), '三維模型')
        continue
    lv = [LU[i][1] for i in tl.query(b) if LU[i][0].intersects(b)]
    if lv: n['土地使用樓層'] += 1; add(b, int(max(lv)), '土地使用樓層')
    else: n['無資料'] += 1; add(b, 0, '無資料（列最低級）')
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': feats,
           'bins': BINS, 'labels': LABELS, 'floor_m': FLOOR_M, 'source': '臺北三維模型（2017，approximate）＋03 土地使用樓層', 'date': '2026-10-15'},
          open(H / 'data/building_floors_EPSG3826.geojson', 'w'), ensure_ascii=False)
a = collections.Counter()
for f in feats: a[f['properties']['cls']] += shape(f['geometry']).area
tot = sum(a.values())
print('建物', dict(n), '｜切片', len(feats))
for i, lab in enumerate(LABELS): print(f'{lab}: {a[i] / 1e4:.1f} ha（{a[i] / tot:.0%}）')
