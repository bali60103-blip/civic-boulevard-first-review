# 純綠地＋公園步道（Z4 起；使用者 2026-10-12：「在圖上加標純綠地的範圍」「地圖上的公園如果有步道要加上步道」）
#   純綠地＝公園綠地（03_南京至仁愛 04_green 之 PARK＋GRASS：OSM leisure=park／garden／common、landuse=recreation_ground／grass、natural=wood 等）內，
#     臺北市 Ortho_2025 空照（0.6 m/px）判讀為植栽之範圍，扣除建物、運動設施（球場、跑道、體健設施、兒童遊戲場）與公園步道。
#     植栽：G > R+6 且 G > B+2（草地、樹冠），或公園綠地內之暗部（max < 70，樹冠陰影）；裸土、鋪面、水泥廣場、停車不計。
#     去雜點：閉運算、開運算各 2 像素（約 1.2 m），向量化（contourpy）後小於 10 m² 者捨去。
#   公園步道＝OSM（expanded_osm）highway＝footway／path／pedestrian／steps／cycleway／service／living_street 落在公園綠地（外擴 2 m）內之段，
#     依 width 標籤展寬；無標籤者 footway 2.5 m、path 1.5 m、pedestrian 4 m、steps 2 m、cycleway 2.5 m、service 3 m、living_street 4 m。
#   範圍：20 之地圖視窗（含前後段，與 26 同框）；統計：本單元多邊形內。
#   輸出：data/{Z}_green_paths_EPSG3826.geojson（kind＝green／parkpath）、data/{Z}_green_paths_summary.json（20、21 讀）
import json, sys, importlib.util, collections
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from contourpy import contour_generator, FillType
from shapely import affinity
from shapely.geometry import shape, mapping, box, Polygon, MultiPolygon
from shapely.ops import transform, unary_union
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
ZONE = sys.argv[1] if len(sys.argv) > 1 else 'Z4'
_argv = sys.argv; sys.argv = [_argv[0], ZONE]
spec = importlib.util.spec_from_file_location('ns', H / 'scripts/20_ns_factors_sheet.py')
N = importlib.util.module_from_spec(spec); spec.loader.exec_module(N)
sys.argv = _argv
S = N.S
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform
IMG = H.parents[0] / '02_南京至仁愛擴幅_20261005'; MAN = json.load(open(IMG / 'imagery_manifest.json'))['images']
LU = H.parents[0] / '03_南京至仁愛_沿線土地使用分析_20261006/data'
PX = 0.6
PATH_W = {'footway': 2.5, 'path': 1.5, 'pedestrian': 4.0, 'steps': 2.0, 'cycleway': 2.5, 'service': 3.0, 'living_street': 4.0}

# ---------- 範圍：地圖視窗（與 26 view_world 相同）----------
d = S.PZ(ZONE)
xc, xlim, ylim, y_ax, H_AX = N.map_frame(ZONE)
o = d['R'].centroid
VIEW = affinity.rotate(affinity.translate(box(xlim[0], ylim[0], xlim[1], ylim[1]), o.x, o.y), d['ang'], origin=(o.x, o.y))
WB = VIEW.buffer(20)

# ---------- 公園綠地（候選）----------
GJ = json.load(open(LU / 'green_EPSG3826.geojson'))['features']
CAND = unary_union([shape(f['geometry']) for f in GJ if f['properties']['kind'] in ('PARK', 'GRASS')]).buffer(0).intersection(WB)
PARKS = []   # 具名公園（OSM 運動設施快取中之 leisure=park）
for f in json.load(open(H / 'data/osm_sports_4326.geojson'))['features']:
    p = f['properties']
    if p.get('leisure') in ('park', 'garden') and p.get('name'):
        g = transform(tf, shape(f['geometry'])).buffer(0)
        if g.intersects(WB): PARKS.append((g, p['name']))
SPORTS = []  # 運動設施（扣除用）
for f in json.load(open(H / 'data/osm_sports_4326.geojson'))['features']:
    p = f['properties']
    if p.get('leisure') in ('pitch', 'track', 'fitness_station', 'playground', 'sports_centre', 'stadium', 'swimming_pool') or ('sport' in p and p.get('leisure') not in ('park', 'garden')):
        g = transform(tf, shape(f['geometry']))
        g = g.buffer(3.0) if g.area == 0 else g.buffer(0)
        if g.intersects(WB): SPORTS.append(g)
SPORTU = unary_union(SPORTS) if SPORTS else Polygon()

# ---------- 公園步道（OSM 線 → 依寬度展成面）----------
osm = json.load(open(S.BASE / 'source/expanded_osm.geojson'))['features']
CAND_B = CAND.buffer(2)
pp = []
for f in osm:
    p = f['properties']; hw = p.get('highway')
    if hw not in PATH_W or f['geometry']['type'] not in ('LineString', 'MultiLineString'): continue
    g = transform(tf, shape(f['geometry']))
    if not g.intersects(CAND_B): continue
    seg = g.intersection(CAND_B)
    if seg.is_empty or seg.length < 3: continue
    try: w = float(str(p.get('width', '')).replace('m', '').strip())
    except ValueError: w = PATH_W[hw]
    pp.append((seg.buffer(w / 2, cap_style='flat'), seg, hw, w, p.get('name', ''), p.get('@id', p.get('id', ''))))
PPATH = unary_union([q for q, *_ in pp]).intersection(CAND_B) if pp else Polygon()

# ---------- 空照植栽判讀（0.6 m 格網）----------
x0, y0, x1, y1 = [round(v) for v in WB.bounds]
Wpx, Hpx = int((x1 - x0) / PX), int((y1 - y0) / PX)
mos = Image.new('RGB', (Wpx, Hpx), 'white')
for m in MAN:
    bx = m['bbox']; cx0, cx1 = max(x0, bx[0]), min(x1, bx[2]); cy0, cy1 = max(y0, bx[1]), min(y1, bx[3])
    if cx0 >= cx1 or cy0 >= cy1: continue
    t = Image.open(IMG / 'imagery' / m['file']).convert('RGB'); sx = t.width / (bx[2] - bx[0]); sy = t.height / (bx[3] - bx[1])
    c = t.crop((int((cx0 - bx[0]) * sx), int((bx[3] - cy1) * sy), int((cx1 - bx[0]) * sx), int((bx[3] - cy0) * sy))).resize((int((cx1 - cx0) / PX), int((cy1 - cy0) / PX)))
    mos.paste(c, (int((cx0 - x0) / PX), int((y1 - cy1) / PX)))
A = np.asarray(mos).astype(int); R, G, B = A[..., 0], A[..., 1], A[..., 2]
cm = Image.new('L', (Wpx, Hpx), 0); dr = ImageDraw.Draw(cm)
to = lambda c: ((c[0] - x0) / PX, (y1 - c[1]) / PX)
for pg in getattr(CAND, 'geoms', [CAND]):
    if pg.geom_type != 'Polygon': continue
    dr.polygon([to(c) for c in pg.exterior.coords], fill=255)
    for r in pg.interiors: dr.polygon([to(c) for c in r.coords], fill=0)
cand = np.asarray(cm) > 0
mx_ = np.maximum(np.maximum(R, G), B); mn_ = np.minimum(np.minimum(R, G), B)
paved_px = ((mx_ - mn_) < 22) & (mx_ > 80)      # 灰色硬鋪面（低彩度、亮）；草、樹冠、陰影、裸土（黃褐）皆非鋪面
# 純綠地＝公園綠地扣除硬鋪面、步道、運動設施、建物（使用者 2026-10-12 兩度指出中央藝文公園綠地破碎）：
#   裸土、踩禿草地、枯草、樹冠縫、樹蔭屬公園軟質開放地，一律算綠地；只扣除成片之灰色硬鋪面（廣場、停車），
#   且鋪面改繪淡灰（同公園步道），公園內只剩「綠」與「灰」兩種，不留白洞。
#   鋪面判讀：開運算 2 像素（去除寬 < 約 2.4 m 之零星灰點），連通 ≥ PAVE_MIN m² 者，閉運算 2 像素補齊邊緣、外擴 1 像素。
PAVE_MIN = 40          # m²
pav = ndimage.binary_opening(cand & paved_px, iterations=2)
lab, nlab = ndimage.label(pav)
sizes = ndimage.sum(pav, lab, range(1, nlab + 1)) * PX * PX if nlab else np.array([])
big = np.isin(lab, np.nonzero(sizes >= PAVE_MIN)[0] + 1) if nlab else np.zeros_like(pav)
big = ndimage.binary_dilation(ndimage.binary_closing(big, iterations=2), iterations=1) & cand
# 向量化：格點中心座標，取 0.5 等值之填色面
gx = x0 + (np.arange(Wpx) + .5) * PX; gy = y1 - (np.arange(Hpx) + .5) * PX
def vec(m):
    cg = contour_generator(x=gx, y=gy, z=m.astype(float), fill_type=FillType.OuterOffset)
    out = []
    for pts, offs in zip(*cg.filled(0.5, 1.5)):
        rings = [pts[offs[i]:offs[i + 1]] for i in range(len(offs) - 1)]
        if not rings or len(rings[0]) < 4: continue
        pg = Polygon(rings[0], [r for r in rings[1:] if len(r) >= 4]).buffer(0)
        if not pg.is_empty: out.append(pg)
    return unary_union(out) if out else Polygon()
HARD = unary_union([S.bld.intersection(WB.buffer(5)), SPORTU, PPATH])
PAVE = vec(big).simplify(.3).buffer(.6, join_style='round').buffer(-.6, join_style='round').intersection(CAND).difference(HARD)
# 鋪面須與動線相連：廣場、停車必接公園步道或公園邊界（人行道）；孤立於草地中之灰塊多為空照浮水印（臺北市政府／都發局字樣）、
#   碎石或陰影，不計為鋪面（算綠地）
_conn = unary_union([PPATH.buffer(2.0), CAND.boundary.buffer(2.0)])
PAVE = unary_union([q for q in getattr(PAVE, 'geoms', [PAVE]) if q.geom_type == 'Polygon' and q.area >= 25 and q.intersects(_conn)])
# 平滑（使用者 2026-10-12：步道鋪面鋸齒太多，不必貼近現實，表達大概形狀即可）：
#   閉運算＋開運算（外擴 R_SM → 內縮 2R_SM → 外擴 R_SM，圓角）去除鋸齒與寬 < 2R_SM 之尖刺，再簡化約 1 m
R_SM = 3.5
PAVE = PAVE.buffer(R_SM, join_style='round').buffer(-2 * R_SM, join_style='round').buffer(R_SM, join_style='round').simplify(1.5)
PAVE = PAVE.buffer(1.0, join_style='round').buffer(-1.0, join_style='round')     # 簡化後再圓角
PAVE = PAVE.intersection(CAND).difference(S.bld.intersection(WB.buffer(5))).difference(SPORTU)
PAVE = unary_union([q for q in getattr(PAVE, 'geoms', [PAVE]) if q.geom_type == 'Polygon' and q.area >= 25])
GREEN = CAND.difference(HARD).difference(PAVE)          # 其餘皆綠地：不留白洞
_sliver = [q for q in getattr(GREEN, 'geoms', [GREEN]) if q.geom_type == 'Polygon' and q.area < 15]
if _sliver: PAVE = unary_union([PAVE] + _sliver)           # 鋪面與步道間之細縫併入鋪面（淡灰），不留白點
GREEN = unary_union([q for q in getattr(GREEN, 'geoms', [GREEN]) if q.geom_type == 'Polygon' and q.area >= 15])
# 草地中孤立之小灰點（< 60 m² 且不接步道、公園邊界）改回綠地
_spk = [q for q in getattr(PAVE, 'geoms', [PAVE]) if q.geom_type == 'Polygon' and q.area < 60 and not q.intersects(PPATH.buffer(1.0)) and not q.intersects(CAND.boundary.buffer(1.0))]
if _spk:
    PAVE = PAVE.difference(unary_union(_spk)); GREEN = unary_union([GREEN] + _spk)
    PAVE = unary_union([q for q in getattr(PAVE, 'geoms', [PAVE]) if q.geom_type == 'Polygon' and q.area >= 1])

# ---------- 統計（本單元內）----------
ZP_ = {f['properties']['id']: shape(f['geometry']) for f in S.ZF if 'id' in f['properties']}
ZPOLY = ZP_[ZONE]
g_in = GREEN.intersection(ZPOLY); c_in = CAND.intersection(ZPOLY)
by_park = []
for pg, nm in sorted(PARKS, key=lambda t: -t[0].intersection(ZPOLY).area):
    a = pg.intersection(ZPOLY).area
    if a < 100: continue
    ln = sum(s.intersection(pg.buffer(2)).intersection(ZPOLY).length for _, s, *_ in pp)
    by_park.append({'name': nm, 'park_m2': round(a), 'green_m2': round(GREEN.intersection(pg).intersection(ZPOLY).area),
                    'path_m': round(ln), 'path_m2': round(PPATH.intersection(pg).intersection(ZPOLY).area),
                    'pave_m2': round(PAVE.intersection(pg).intersection(ZPOLY).area)})
summ = {'zone': ZONE, 'green_m2': round(g_in.area), 'cand_m2': round(c_in.area), 'green_share_of_cand': round(g_in.area / max(c_in.area, 1), 3),
        'path_m': round(sum(s.intersection(ZPOLY).length for _, s, *_ in pp)), 'path_m2': round(PPATH.intersection(ZPOLY).area),
        'parks': by_park, 'path_types': dict(collections.Counter(hw for _, s, hw, *_ in pp if s.intersects(ZPOLY))),
        'pave_m2': round(PAVE.intersection(ZPOLY).area),
        'method': '公園綠地（04_green PARK＋GRASS）扣除 Ortho_2025 成片灰色硬鋪面（≥ 40 m²）、公園步道、運動設施、建物；裸土、枯草、樹冠皆算綠地'}
feats = [{'type': 'Feature', 'geometry': mapping(q), 'properties': {'kind': 'green', 'area': round(q.area)}} for q in getattr(GREEN, 'geoms', [GREEN]) if not q.is_empty]
feats += [{'type': 'Feature', 'geometry': mapping(q), 'properties': {'kind': 'parkpave', 'area': round(q.area)}} for q in getattr(PAVE, 'geoms', [PAVE]) if not q.is_empty]
feats += [{'type': 'Feature', 'geometry': mapping(q.intersection(CAND_B)), 'properties': {'kind': 'parkpath', 'highway': hw, 'width_m': w, 'name': nm, 'osm': oid}}
          for q, s, hw, w, nm, oid in pp if not q.intersection(CAND_B).is_empty]
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': feats,
           'source': 'Ortho_2025（臺北市都發局 historygis）＋OSM 2026-09-08', 'date': '2026-10-12'},
          open(H / f'data/{ZONE}_green_paths_EPSG3826.geojson', 'w'), ensure_ascii=False)
json.dump(summ, open(H / f'data/{ZONE}_green_paths_summary.json', 'w'), ensure_ascii=False, indent=1)
print('green in zone m2', summ['green_m2'], 'of cand', summ['cand_m2'], summ['green_share_of_cand'], '| paths m', summ['path_m'], summ['path_types'])
for p in by_park: print(' ', p)
