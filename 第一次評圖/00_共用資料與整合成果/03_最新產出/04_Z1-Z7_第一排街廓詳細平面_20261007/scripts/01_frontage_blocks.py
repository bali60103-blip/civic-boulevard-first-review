# 市民大道兩側第一排街廓（Z1–Z7 詳細平面用）
# 街廓＝圖框扣除道路閉合面（02_南京至仁愛擴幅 road_surfaces 經 00_integrate_sidewalk.py 與官方人行道整合）後之連通面；
# 第一排＝自市民大道中心線每 STEP m 向南北打垂直射線，第一個碰到的「實體街廓」（排除分隔島、細長綠帶）。
# 射線落在橫向街道上會穿到第二排：以同側鄰近射線的路緣距離（滾動低分位數）＋容差篩掉，並要求最少命中數。
# 大型街廓（華山、臺北車站、北科大、河堤）於距中心線 D_MAX m 處截斷，以免單一街廓撐大圖幅。
import json
from pathlib import Path
import numpy as np
from shapely.geometry import shape, mapping, LineString, Polygon, Point, box
from shapely.ops import unary_union, transform
from shapely.strtree import STRtree
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
ROOT = H.parents[1]
BASE = ROOT / '03_最新產出/02_南京至仁愛擴幅_20261005'
LU = ROOT / '03_最新產出/03_南京至仁愛_沿線土地使用分析_20261006'
OUT = H / 'data'; OUT.mkdir(exist_ok=True)
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform

STEP = 4            # 射線間距 m
RAY = 420           # 射線長 m（大型街廓如華山、臺北車站）
TOL = 14            # 超過同側路緣距離多少 m 視為穿進橫街
MIN_HITS = 3        # 第一排至少被幾條射線命中（≈ 12 m 臨街面）
INNER = 16          # 形心距中心線 < INNER m 者視為大道內分隔島
THIN = 7            # 2A/P < THIN m 視為細長帶（分隔島、綠帶）
STRIP = 22          # 無建物且短邊 < STRIP m、長寬比 > 3：橫街中央綠帶（敦化路等）
D_MAX = 150         # 距中心線截斷深度 m
FULL_ZONES = ('Z4', 'Z6', 'Z7', 'Z8')   # 分頁圖：這些單元不截斷，且跨界街廓整塊畫出（2026-10-07／08 使用者指示）
# Z8：光復南路以東高架與地面市民大道五段分離（地面路往東北），高架下無公共道路，松山文創＋大巨蛋（南）與臺北機廠（北）
#     在線稿中為同一街廓；Z8 以高架軸線為準（2026-10-08），此大街廓即南北兩側第一排。

frame = box(300935, 2770000, 307545, 2771910)
road = shape(json.load(open(H / 'data/road_surfaces_integrated_EPSG3826.geojson'))['features'][0]['geometry'])   # 已與官方人行道整合（00_integrate_sidewalk.py）
blocks = [g for g in frame.difference(road).geoms if g.area > 30]
bld = shape(json.load(open(BASE / 'building_outlines_TWD97.geojson'))['features'][0]['geometry'])
btree = STRtree(list(bld.geoms))
bgeoms = list(bld.geoms)

# 1. 市民大道中心線：以高架主線＋平面市民大道兩向車道之垂直剖面中點求得，再平滑
ax_ = json.load(open(ROOT / '01_輸入資料/前處理資料/axis.json'))
civic = unary_union([transform(tf, LineString(l)) for k in ('elevated_ll', 'atgrade_ll') for l in ax_[k] if len(l) > 1])
axis0 = transform(tf, LineString(ax_['axis_ll']))

def smooth(pts, win):
    k = max(1, int(win / 10)); out = pts.copy()
    for i in range(len(pts)):
        a, b = max(0, i - k), min(len(pts), i + k + 1)
        out[i] = pts[a:b].mean(axis=0)
    return out

def resample(line, step=10):
    return np.array([line.interpolate(t).coords[0] for t in np.arange(0, line.length, step)] + [line.coords[-1]])

pts = smooth(resample(axis0), 250)
for it in range(3):
    cl = LineString(pts); new = pts.copy()
    for i, p in enumerate(pts):
        t = cl.project(Point(p)); a = np.array(cl.interpolate(max(0, t - 15)).coords[0]); b = np.array(cl.interpolate(min(cl.length, t + 15)).coords[0])
        d = (b - a) / (np.linalg.norm(b - a) or 1); n = np.array([-d[1], d[0]])
        seg = LineString([p - n * 60, p + n * 60])
        hit = seg.intersection(civic)
        q = [np.array(g.coords[0]) for g in getattr(hit, 'geoms', [hit]) if g.geom_type == 'Point']
        if len(q) >= 2:
            s = [float(np.dot(x - p, n)) for x in q]
            new[i] = p + n * (min(s) + max(s)) / 2
    pts = smooth(new, 120 if it < 2 else 60)
# 西端（淡水河堤）高架轉入匝道，中心線依末段方向外延至河堤界線以西
d0 = pts[0] - pts[8]; d0 /= np.linalg.norm(d0)
while pts[0][0] > 300990: pts = np.vstack([pts[0] + d0 * 10, pts])
center = LineString(pts)

# 2. 街廓屬性
ZF = json.load(open(LU / 'data/zones_EPSG3826.geojson'))['features']
cuts = [shape(f['geometry']) for f in ZF if 'cut' in f['properties']]
cut_in = unary_union([c.intersection(center.buffer(D_MAX)) for c in cuts])
def width(g): return 2 * g.area / g.length
def sides(g):
    c = np.asarray(g.minimum_rotated_rectangle.exterior.coords)
    a, b = np.linalg.norm(c[1] - c[0]), np.linalg.norm(c[2] - c[1]); return min(a, b), max(a, b)
binfo = []
for g in blocks:
    bf = sum(bgeoms[i].intersection(g).area for i in btree.query(g, predicate='intersects'))
    s, l = sides(g)
    real = width(g) >= THIN and center.distance(g.centroid) >= INNER and (g.area >= 250 or bf > 40)
    if bf < 50 and s < STRIP and l / s > 3: real = False                      # 橫街中央綠帶
    if bf < 50 and g.intersection(cut_in).length > 30: real = False           # 橫街（建國高架等）橋下分隔帶
    binfo.append({'real': real, 'bfoot': bf})
tree = STRtree(blocks)

# 3. 射線
S = np.arange(0, center.length, STEP)
rec = {+1: [], -1: []}  # 每站：(block index or -1, 入點距離, 出點距離)
normals = []
for t in S:
    p = np.array(center.interpolate(t).coords[0])
    a = np.array(center.interpolate(max(0, t - 12)).coords[0]); b = np.array(center.interpolate(min(center.length, t + 12)).coords[0])
    d = (b - a) / np.linalg.norm(b - a); n = np.array([-d[1], d[0]])  # +n = 左側（行進往東時為北側）
    normals.append((p, n))
    for side in (+1, -1):
        ray = LineString([p, p + side * n * RAY])
        best = None
        for i in tree.query(ray, predicate='intersects'):
            if not binfo[i]['real']: continue
            seg = ray.intersection(blocks[i])
            ds = [float(np.linalg.norm(np.array(c) - p)) for g in getattr(seg, 'geoms', [seg]) if not g.is_empty for c in g.coords]
            if not ds: continue
            if best is None or min(ds) < best[1]:
                # 出點：同一街廓沿射線的第一段連續交段之末端
                first = min((g for g in getattr(seg, 'geoms', [seg]) if not g.is_empty),
                            key=lambda g: min(np.linalg.norm(np.array(c) - p) for c in g.coords))
                best = (i, min(ds), max(np.linalg.norm(np.array(c) - p) for c in first.coords))
        rec[side].append(best if best else (-1, np.inf, np.inf))

# 4. 篩掉穿進橫街的射線
acc = {}
for side in (+1, -1):
    d = np.array([r[1] for r in rec[side]])
    k = int(50 / STEP); ok = np.zeros(len(d), bool)
    for j in range(len(d)):
        w = d[max(0, j - k): j + k + 1]; w = w[np.isfinite(w)]
        if not len(w): continue
        edge = np.percentile(w, 25)
        ok[j] = np.isfinite(d[j]) and d[j] <= edge + TOL
    acc[side] = ok
hits = {}
for side in (+1, -1):
    for j, r in enumerate(rec[side]):
        if acc[side][j]: hits.setdefault(r[0], []).append((side, j))
first = {i: v for i, v in hits.items() if len(v) >= MIN_HITS}

# 5. 分區（沿用 03_南京至仁愛 zones_EPSG3826 之路口中心線界線，界線延伸至圖框上下緣）
zprops = [f['properties'] for f in ZF if 'id' in f['properties']]
end_x = center.coords[-1][0]
def slab(k):
    L = list(cuts[k].coords)
    R = list(cuts[k + 1].coords)[::-1] if k + 1 < len(cuts) else [(end_x + 600, 2771910), (end_x + 600, 2770000)]
    return Polygon([(L[0][0], 2769000)] + L + [(L[-1][0], 2773000), (R[0][0], 2773000)] + R + [(R[-1][0], 2769000)]).buffer(0)
slabs = {zp['id']: slab(k) for k, zp in enumerate(zprops)}

# 6. 平面範圍：第一排街廓＋其間之大道路面與橫街口（以射線出點包絡補齊）
def envelope(side):
    dep = np.array([r[2] if acc[side][j] else np.nan for j, r in enumerate(rec[side])])
    idx = np.where(np.isfinite(dep))[0]
    if not len(idx): return None
    dd = np.interp(np.arange(len(dep)), idx, dep[idx])
    # 長距離無第一排（河堤、空地）：只到路緣
    gap = np.zeros(len(dep))
    for j in range(len(dep)):
        prv = idx[idx <= j]; nxt = idx[idx >= j]
        gap[j] = (nxt[0] - prv[-1]) * STEP if len(prv) and len(nxt) else 1e9
    edge = np.array([r[1] if np.isfinite(r[1]) else 30 for r in rec[side]])
    dd = np.where(gap > 90, np.minimum(edge, 40), dd)
    ring = [tuple(p) for p, n in normals] + [tuple(p + side * n * dd[j]) for j, (p, n) in enumerate(normals)][::-1]
    return Polygon(ring).buffer(0)
env = unary_union([e for e in (envelope(+1), envelope(-1)) if e is not None])
fb = unary_union([blocks[i] for i in first])
region = unary_union([env.buffer(0.5), fb]).buffer(1).buffer(-1)
region = Polygon(region.exterior) if region.geom_type == 'Polygon' else unary_union([Polygon(p.exterior) for p in region.geoms])
band = center.buffer(D_MAX, cap_style='flat')
region_unclipped = region
region = region.intersection(band)
clipped_edge = region.boundary.intersection(band.boundary.buffer(.05))   # 截斷處（出圖畫截斷線）

feats = []
for i, v in first.items():
    g = blocks[i]
    ov = sorted(((g.intersection(s).area, z) for z, s in slabs.items()), reverse=True)
    z = ov[0][1]
    side = 'N' if np.mean([s for s, _ in v]) > 0 else 'S'
    feats.append({'type': 'Feature', 'geometry': mapping(g.intersection(band)),
                  'properties': {'zone': z, 'side': side, 'hits': len(v), 'frontage_m': len(v) * STEP,
                                 'area_m2': round(g.area), 'bfoot_m2': round(binfo[i]['bfoot']),
                                 'clipped': bool(g.difference(band).area > 1)}})
zreg = []
for z, s in slabs.items():
    r = region.intersection(s)
    if not r.is_empty:
        zreg.append({'type': 'Feature', 'geometry': mapping(r), 'properties': {'zone': z, 'kind': 'region'}})
# 完整版（FULL_ZONES）：不截斷之範圍 ∩ 分段，再併入與本段重疊 > 20 m² 之第一排街廓整塊（跨分段界線者不切）
feats_full = []
for z in FULL_ZONES:
    s = slabs[z]
    whole = [i for i in first if blocks[i].intersection(s).area > 20]
    r = unary_union([region_unclipped.intersection(s)] + [blocks[i] for i in whole]).buffer(.5).buffer(-.5)
    r = Polygon(r.exterior) if r.geom_type == 'Polygon' else unary_union([Polygon(q.exterior) for q in r.geoms if q.area > 50])
    zreg.append({'type': 'Feature', 'geometry': mapping(r), 'properties': {'zone': z, 'kind': 'region_full'}})
    for i in whole:
        v = first[i]; side = 'N' if np.mean([q for q, _ in v]) > 0 else 'S'
        own = max(((blocks[i].intersection(s2).area, z2) for z2, s2 in slabs.items()))[1]
        feats_full.append({'type': 'Feature', 'geometry': mapping(blocks[i]),
                           'properties': {'zone': z, 'owner_zone': own, 'side': side, 'hits': len(v), 'area_m2': round(blocks[i].area),
                                          'restored_m2': round(blocks[i].difference(band).area + blocks[i].difference(s).area)}})
crs = {'type': 'name', 'properties': {'name': 'EPSG:3826'}}
json.dump({'type': 'FeatureCollection', 'crs': crs, 'features': feats}, open(OUT / 'frontage_blocks_EPSG3826.geojson', 'w'), ensure_ascii=False)
json.dump({'type': 'FeatureCollection', 'crs': crs, 'features': feats_full}, open(OUT / 'frontage_blocks_full_EPSG3826.geojson', 'w'),
          ensure_ascii=False)
json.dump({'type': 'FeatureCollection', 'crs': crs, 'features': zreg + [
    {'type': 'Feature', 'geometry': mapping(center), 'properties': {'kind': 'centerline'}},
    {'type': 'Feature', 'geometry': mapping(clipped_edge), 'properties': {'kind': 'clipped_edge', 'd_max': D_MAX}}]},
    open(OUT / 'frontage_region_EPSG3826.geojson', 'w'), ensure_ascii=False)

import collections
cnt = collections.Counter((f['properties']['zone'], f['properties']['side']) for f in feats)
for z in slabs:
    print(z, 'N', cnt[(z, 'N')], 'S', cnt[(z, 'S')])
print('blocks', len(blocks), 'first-row', len(first), 'centerline', round(center.length))
for z in FULL_ZONES:
    rr = [f['properties'] for f in feats_full if f['properties']['zone'] == z]
    print(z, 'full blocks', len(rr), 'restored m2', sum(r['restored_m2'] for r in rr))
