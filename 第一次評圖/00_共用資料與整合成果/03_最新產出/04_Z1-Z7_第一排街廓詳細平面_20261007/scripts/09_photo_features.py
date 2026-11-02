# 照片判讀補繪（2026-10-07）：依 ~/Desktop/civic photo 現場照片判讀，補平面圖缺漏之現況元素
#   1. 橋墩：柱型依各單元照片判讀；柱位依官方平均跨距（D028 市民大道主橋 5,802.5 m／160 孔 ≈ 36.3 m）
#      沿橋面中軸配置，並限制落在分隔島（非車道面）、不壓建物／行穿線；跨路口處跨距自動放長。非實測柱位。
#   2. 分隔島植栽：照片確認高架下分隔島多為綠籬／灌木植栽（Z2 為石砌擋牆坡道上植栽）
#   3. OSM 既有點位經照片核實者：候車亭、YouBike、公共藝術、地下化引道遺構、地面樓梯、停車場出入口
#   4. 照片定位之機車停車列（iPhone GPS ＋畫面判讀）
import json, csv, collections
from pathlib import Path
import numpy as np
from shapely.geometry import shape, mapping, Point, LineString, Polygon, box
from shapely.ops import unary_union, transform
from shapely.strtree import STRtree
from shapely import affinity
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
ROOT = H.parents[1]
BASE = ROOT / '03_最新產出/02_南京至仁愛擴幅_20261005'
LU = ROOT / '03_最新產出/03_南京至仁愛_沿線土地使用分析_20261006'
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform

SPAN = 5802.5 / 160          # 官方平均跨距
SPAN_MIN, SPAN_MAX = 26.0, 52.0
ZONES = ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'Z7', 'Z8']   # Z8 僅作 Z7 前後段

RG = json.load(open(H / 'data/frontage_region_EPSG3826.geojson'))['features']
REG = {f['properties']['zone']: shape(f['geometry']) for f in RG if f['properties']['kind'] == 'region'}
# 完整版範圍（Z4、Z6、Z7 不截斷、跨界街廓整塊）一併處理
for f in RG:
    if f['properties']['kind'] == 'region_full':
        REG[f['properties']['zone']] = unary_union([REG.get(f['properties']['zone'], shape(f['geometry'])), shape(f['geometry'])])
center = next(shape(f['geometry']) for f in RG if f['properties']['kind'] == 'centerline')
RU = unary_union([REG[z] for z in ZONES])
road = shape(json.load(open(H / 'data/road_surfaces_integrated_EPSG3826.geojson'))['features'][0]['geometry'])   # 已與官方人行道整合（00_integrate_sidewalk.py）
bld = shape(json.load(open(BASE / 'building_outlines_TWD97.geojson'))['features'][0]['geometry'])
civ = json.load(open(LU / 'data/civic_elevated_EPSG3826.json'))
elev = shape(civ['elevated'])
SD = json.load(open(H / 'data/street_detail_EPSG3826.geojson'))['features']
cw = unary_union([shape(f['geometry']) for f in SD if f['properties']['kind'] == 'crosswalk'])
frame = box(300935, 2770000, 307545, 2771910)
islands_all = frame.difference(road)

# ---------- 照片判讀：各單元柱型（依照片編號；見 data/photos/photo_reading.csv） ----------
# single_round：單柱圓形（Z6 彩虹柱、Z7）；single_rect：單柱矩形（Z2、Z5）；portal：雙柱＋帽梁（Z3–Z4）
PIER_TYPE = {
    'Z1': ('single_rect', '無照片，柱型未核'),
    'Z2': ('single_rect', 'IMG_4585、4586、4591、4592：大型單柱（錐形帽梁），分隔島為石砌坡道擋牆'),
    'Z3': ('portal', 'IMG_4594–4596：雙柱門形墩；與 Z4 西段連續'),
    'Z4': ('portal', 'DSC08745–08774、IMG_4597–4599：雙柱＋帽梁門形墩，柱間為植栽分隔島'),
    'Z5': ('single_rect', 'DSC08703–08715（市民大道三段5號、八德路二段路牌）、DSC08441–08457：大型矩形單柱'),
    'Z6': ('single_round', 'IMG_4675–4680、DSC08524–08533：圓形單柱，彩虹漆'),
    'Z7': ('single_round', 'DSC08574–08700：圓形單柱，淡粉色漆'),
    'Z8': ('single_round', '無照片，柱型未核（沿用 Z7）'),
}
PIER_DIM = {'single_round': {'d': 2.4}, 'single_rect': {'a': 2.4, 'b': 3.6}, 'portal': {'d': 1.8, 'half': 5.5}}

# ---------- 橋面中軸：沿市民大道中心線之垂直剖面，取高架雙向車道中心線交點之中點 ----------
def normal_at(line, t):
    a = np.array(line.interpolate(max(0, t - 8)).coords[0]); b = np.array(line.interpolate(min(line.length, t + 8)).coords[0])
    d = (b - a) / np.linalg.norm(b - a); return d, np.array([-d[1], d[0]])
axis_pts = []
for t in np.arange(0, center.length, 3):
    p = np.array(center.interpolate(t).coords[0]); d, n = normal_at(center, t)
    hit = LineString([p - n * 30, p + n * 30]).intersection(elev)
    s = [float(np.dot(np.array(q.coords[0]) - p, n)) for q in getattr(hit, 'geoms', [hit]) if not hit.is_empty and q.geom_type == 'Point']
    if len(s) >= 2 and max(s) - min(s) < 30: axis_pts.append((t, p + n * (min(s) + max(s)) / 2, max(s) - min(s)))
    elif len(s) == 1: axis_pts.append((t, p + n * s[0], 0.0))
# 平滑並切成連續段（缺口 > 30 m 斷開）
segs, cur = [], []
for t, q, w in axis_pts:
    if cur and t - cur[-1][0] > 30: segs.append(cur); cur = []
    cur.append((t, q, w))
if cur: segs.append(cur)
axes = []
for sg in segs:
    if len(sg) < 5: continue
    q = np.array([x[1] for x in sg]); k = 4
    qs = np.array([q[max(0, i - k): i + k + 1].mean(axis=0) for i in range(len(q))])
    axes.append(LineString(qs))

# ---------- 柱位配置 ----------
# 每 1 m 沿橋面中軸打 ±15 m 垂直線，找其下之分隔島（非車道、非建物、非行穿線）；柱心置於分隔島寬度中點，
# 柱徑／門形墩柱距依分隔島寬度縮放（線稿車道寬為估算，分隔島常較實際窄，縮放以免柱壓車道）
from shapely.prepared import prep
free = islands_all.intersection(RU.buffer(40)).difference(bld).difference(cw.buffer(1.5))
free_p = prep(free)
REGB = {z: prep(REG[z].buffer(25)) for z in ZONES}
def zone_of_fast(p):
    return next((z for z in ZONES if REGB[z].contains(Point(p))), None)
MARGIN = 0.4
def fit(typ, w):
    # 依分隔島寬 w 回傳實際繪製尺寸；放不下回傳 None
    if typ == 'portal':
        r = 0.9; half = min(5.5, w / 2 - r - MARGIN)
        if half >= 2.0: return ('portal', {'d': 2 * r, 'half': half})
        typ = 'single_round'
    if typ == 'single_round':
        dd = min(2.4, w - 2 * MARGIN)
        return ('single_round', {'d': dd}) if dd >= 1.4 else None
    b = min(3.6, w - 2 * MARGIN)
    return ('single_rect', {'a': 2.4, 'b': b}) if b >= 1.6 else None
def footprint(p, d, typ, dim):
    n = np.array([-d[1], d[0]])
    if typ == 'single_round': return Point(p).buffer(dim['d'] / 2, 16)
    if typ == 'single_rect':
        a, b = dim['a'] / 2, dim['b'] / 2
        return Polygon([p + d * a + n * b, p - d * a + n * b, p - d * a - n * b, p + d * a - n * b])
    h, r = dim['half'], dim['d'] / 2
    return unary_union([Point(p + n * h).buffer(r, 16), Point(p - n * h).buffer(r, 16)])
piers = []
for ax in axes:
    L = int(ax.length); cand = {}
    for i in range(L + 1):
        p = np.array(ax.interpolate(i).coords[0]); z = zone_of_fast(p)
        if z is None: continue
        d, n = normal_at(ax, i)
        ray = LineString([p - n * 15, p + n * 15])
        x = ray.intersection(free)
        best = None
        for q in getattr(x, 'geoms', [x]):
            if q.is_empty or q.geom_type != 'LineString': continue
            ss = sorted(float(np.dot(np.array(c) - p, n)) for c in q.coords)
            lo, hi = ss[0], ss[-1]; mid = (lo + hi) / 2
            if abs(mid) > 12: continue
            if best is None or hi - lo > best[1] - best[0]: best = (lo, hi)
        if not best: continue
        typ0 = PIER_TYPE[z][0]; f = fit(typ0, best[1] - best[0])
        if not f: continue
        c = p + n * (best[0] + best[1]) / 2
        fp = footprint(c, d, *f)
        if not free_p.contains(fp): continue
        cand[i] = (c, d, z, f, best[1] - best[0])
    feas = np.array(sorted(cand))
    if not len(feas): continue
    i = feas[0]; chosen = [i]
    while True:
        nx = feas[(feas >= i + SPAN_MIN) & (feas <= i + SPAN_MAX)]
        if not len(nx):
            nx2 = feas[feas > i + SPAN_MAX]
            if not len(nx2): break
            i = nx2[0]; chosen.append(i); continue
        # 最接近官方平均跨距者；同距時取分隔島較寬處
        i = min(nx, key=lambda j: (abs(j - i - SPAN) // 3, -cand[j][4])); chosen.append(i)
    for i in chosen:
        c, d, z, (typ, dim), w = cand[i]
        piers.append({'geom': footprint(c, d, typ, dim), 'p': c, 'd': d, 'zone': z, 'type': typ, 'dim': dim, 'median_w': round(w, 1)})
# 門形墩帽梁（示意外框）
feats = []
def add(g, **pr):
    if g is not None and not g.is_empty: feats.append({'type': 'Feature', 'geometry': mapping(g), 'properties': pr})
for k, pr in enumerate(piers):
    if pr['zone'] not in ZONES: continue
    add(pr['geom'], kind='pier', pier_type=pr['type'], pier_type_photo=PIER_TYPE[pr['zone']][0], zone=pr['zone'],
        median_w=pr['median_w'], evidence=PIER_TYPE[pr['zone']][1], unverified=pr['zone'] in ('Z1', 'Z8'))
    if pr['type'] == 'portal':
        p, d = pr['p'], pr['d']; n = np.array([-d[1], d[0]]); h = pr['dim']['half'] + 1.2; a = 1.1
        add(Polygon([p + d * a + n * h, p - d * a + n * h, p - d * a - n * h, p + d * a - n * h]), kind='pier_cap', zone=pr['zone'])
spans = collections.Counter(pr['zone'] for pr in piers if pr['zone'] in ZONES)
print('piers', dict(sorted(spans.items())))

# ---------- 分隔島植栽：高架下（橋面中軸 18 m 內）之分隔島，照片確認為植栽 ----------
axis_u = unary_union(axes)
MEDIAN_ZONES = {'Z2': '石砌坡道擋牆上植栽（IMG_4585）', 'Z3': '綠籬（IMG_4594）', 'Z4': '綠籬＋喬木（DSC08745–08774）',
                'Z5': '綠籬（DSC08447、08707）', 'Z6': '綠籬（IMG_4678–4680）', 'Z7': '綠籬（DSC08640–08668）'}
for g in getattr(islands_all, 'geoms', [islands_all]):
    if g.area < 25 or g.area > 6000: continue
    if axis_u.distance(g.representative_point()) > 18: continue
    z = next((zz for zz in MEDIAN_ZONES if REG[zz].intersects(g)), None)
    if not z: continue
    gi = g.difference(bld)
    if gi.area < 20: continue
    add(gi, kind='median_planting', zone=z, evidence=MEDIAN_ZONES[z])

# ---------- OSM 點位經照片核實 ----------
VERIFIED = {   # kind: 照片依據
    'shelter': 'IMG_4585、4586（Z2 國光客運候車棚）、DSC08763、08773、08688（候車亭）',
    'bike_rental': 'IMG_4677、DSC08471、08473、08568、08706（YouBike 站）',
    'artwork': 'DSC08752（石雕）、08460–08461（葫蘆雕塑）、08603–08628（Z7 分隔島雕塑）',
    'rail_disused': 'IMG_4634–4637（圍籬後之舊鐵道引道）',
    'parking_entrance': 'DSC08757、08763（停車場入口標誌）',
}
for f in json.load(open(H / 'data/osm_furniture_4326.geojson'))['features']:
    k = f['properties']['kind']
    if k not in VERIFIED and k != 'steps': continue
    tg = f['properties']['tags']
    if k == 'steps' and (str(tg.get('level', '0')).startswith('-') or str(tg.get('layer', '0')).startswith('-')): continue
    g = transform(tf, shape(f['geometry']))
    if not RU.intersects(g): continue
    add(g.intersection(RU.buffer(3)) if g.geom_type != 'Point' else g, kind='osm_' + k, name=f['properties']['name'],
        osm=f['properties']['osm'], evidence=VERIFIED.get(k, '照片未逐一核對（OSM 地面樓梯）'))

# ---------- 照片定位：機車停車列（iPhone GPS ＋畫面）----------
# 以照片位置向拍攝方向，沿最近人行道路緣取一段（長度依畫面可見範圍判讀）
rows = {r['id']: r for r in json.load(open(H / 'data/photos/photo_index.json'))}
sw = unary_union([shape(f['geometry']) for f in SD if f['properties']['kind'] == 'sw'])
MOTO = [  # (照片, 沿拍攝方向長度 m, 說明)
    ('IMG_4676', 120, 'Z6 南側人行道路緣，高架下機車格整排'),
    ('IMG_4680', 90, 'Z6 南側人行道路緣，彩虹柱段'),
]
curb = sw.boundary.intersection(road.buffer(0.6))
for pid, Lm, note in MOTO:
    r = rows[pid]; c = Point(r['x'], r['y'])
    h = np.radians(r['heading']); d = np.array([np.sin(h), np.cos(h)])
    probe = LineString([(r['x'], r['y']), (r['x'] + d[0] * Lm, r['y'] + d[1] * Lm)]).buffer(18, cap_style='flat')
    seg = curb.intersection(probe)
    segs_ = [s for s in getattr(seg, 'geoms', [seg]) if s.geom_type == 'LineString' and s.length > 8]
    if not segs_: continue
    s = max(segs_, key=lambda x: x.length)
    # 機車格帶：路緣內側 2 m（人行道側）
    band = s.buffer(2.0, cap_style='flat').intersection(sw)
    add(band, kind='moto_row', photo=pid, evidence=note)

json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': feats},
          open(H / 'data/photo_features_EPSG3826.geojson', 'w'), ensure_ascii=False)
print(collections.Counter(f['properties']['kind'] for f in feats))
