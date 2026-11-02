# 穿越需求點與供給點（單元主題圖資料；先做 Z1）
#   需求點分三類（2026-10-09 使用者指示）：大量體（大型商辦、高樓）／捷運・地下街出入口／巷道出入口；公車站、YouBike、公園等不列入
#   需求點＝想穿越市民大道的人從哪裡出來：
#     街口／巷口／步道口：步行可通行之道路或步道穿過大道兩側「第一排街廓邊線」並通往後方街區者（同處 10 m 內合併）
#     捷運／地下街出入口、公車站、YouBike（OSM 節點，2026-09-09 擷取；距大道中心線 80 m 內）
#     設施：公園、醫院、學校、博物館／園區（OSM 面），標於設施最靠近大道之處；有 OSM 入口節點者優先
#   供給點＝現在能穿越的地方：
#     平面：交工處行人穿越線中位於大道路面且橫越大道者（同路口 45 m 內合併），附須跨車道段數與南北總寬
#     立體：地下街、人行天橋（2026-09-09 a1_crossings 清單）
import json, sys, math, collections
from pathlib import Path
import numpy as np
from shapely.geometry import shape, mapping, Point, LineString, Polygon
from shapely.ops import unary_union, transform
from shapely.strtree import STRtree
from pyproj import Transformer
import importlib.util

H = Path(__file__).resolve().parents[1]
PRE = H.parents[1] / '01_輸入資料/前處理資料'
spec = importlib.util.spec_from_file_location('sheet', H / 'scripts/02_sheet.py')
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
S.VARIANT['full'] = True
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform
ZONE = sys.argv[1] if len(sys.argv) > 1 else 'Z1'
C = S.center
d = S.PZ(ZONE); R = d['R']
cuts = [shape(f['geometry']) for f in S.ZF if 'cut' in f['properties']]
def station(g):
    x = g.intersection(C); return C.project(x.centroid if not x.is_empty else g.centroid)
k = int(ZONE[1:])
s0 = station(cuts[k - 1]); s1 = station(cuts[k]) if k < len(cuts) else C.length
def normal(t):
    a = np.array(C.interpolate(max(0, t - 15)).coords[0]); b = np.array(C.interpolate(min(C.length, t + 15)).coords[0])
    v = (b - a) / np.linalg.norm(b - a); return v, np.array([-v[1], v[0]])
def side_of(pt):
    t = C.project(pt); p = np.array(C.interpolate(t).coords[0]); _, n = normal(t)
    return 'N' if float(np.dot(np.array(pt.coords[0]) - p, n)) > 0 else 'S'
OUT = []
def add(g, **p):
    OUT.append({'type': 'Feature', 'geometry': mapping(g), 'properties': p})

# ---------- 1. 大道兩側第一排街廓邊線 ----------
FB = [shape(f['geometry']) for f in json.load(open(H / 'data/frontage_blocks_full_EPSG3826.geojson'))['features']] + \
     [shape(f['geometry']) for f in json.load(open(H / 'data/frontage_blocks_EPSG3826.geojson'))['features']]
blocks = unary_union(FB)
btree = STRtree(FB)
ts = np.arange(max(0, s0 - 60), min(C.length, s1 + 60), 3.0)
edge = {+1: [], -1: []}
for t in ts:
    p = np.array(C.interpolate(t).coords[0]); _, n = normal(t)
    for sd in (+1, -1):
        ray = LineString([p, p + sd * n * 140])
        hit = [ray.intersection(FB[i]) for i in btree.query(ray, predicate='intersects')]
        ds = [float(np.linalg.norm(np.array(c) - p)) for h in hit for q in getattr(h, 'geoms', [h]) if not q.is_empty for c in q.coords]
        edge[sd].append(min(ds) if ds else np.nan)
EDGE = {}
for sd in (+1, -1):
    e = np.array(edge[sd]); m = int(60 / 3)
    med = np.array([np.nanmedian(e[max(0, i - m): i + m + 1]) if np.isfinite(e[max(0, i - m): i + m + 1]).any() else np.nan for i in range(len(e))])
    ok = np.isfinite(med); med = np.interp(np.arange(len(med)), np.where(ok)[0], med[ok])
    EDGE[sd] = LineString([tuple(np.array(C.interpolate(t).coords[0]) + sd * normal(t)[1] * e_) for t, e_ in zip(ts, med)])
    add(EDGE[sd], kind='edge', side='N' if sd > 0 else 'S')
    # 匯聚流線用之臨街線：±75 m 滾動最小值（沿最貼近大道之建物線，不繞進街廓凹口），再 ±30 m 平滑
    e2 = np.where(np.isfinite(e), e, np.nan); m2 = int(75 / 3)
    lo = np.array([np.nanmin(e2[max(0, i - m2): i + m2 + 1]) if np.isfinite(e2[max(0, i - m2): i + m2 + 1]).any() else np.nan
                   for i in range(len(e2))])
    ok = np.isfinite(lo); lo = np.interp(np.arange(len(lo)), np.where(ok)[0], lo[ok])
    m3 = int(30 / 3); lo = np.array([lo[max(0, i - m3): i + m3 + 1].mean() for i in range(len(lo))])
    FLOW = LineString([tuple(np.array(C.interpolate(t).coords[0]) + sd * normal(t)[1] * e_) for t, e_ in zip(ts, lo)])
    add(FLOW, kind='flow_edge', side='N' if sd > 0 else 'S')

# ---------- 2. 需求點：街口／巷口／步道口 ----------
WALK_NO = {'no', 'private'}
ROADS = {'primary', 'secondary', 'tertiary', 'unclassified', 'residential', 'living_street', 'service', 'primary_link', 'secondary_link',
         'tertiary_link', 'road', 'pedestrian'}
PATHS = {'footway', 'path', 'steps', 'cycleway', 'corridor'}
cand = []
bb = R.buffer(250).bounds
for w in json.load(open(PRE / 'osm_ways.json')):
    t = w['t']; hw = t.get('highway')
    if hw not in ROADS | PATHS: continue
    if t.get('foot') in WALK_NO or (t.get('access') in WALK_NO and t.get('foot') not in ('yes', 'designated')): continue
    if t.get('footway') in ('crossing', 'sidewalk') or t.get('bridge') == 'yes' or t.get('tunnel') in ('yes', 'building_passage'): continue
    if str(t.get('layer', '0')) not in ('0', ''): continue
    nm = t.get('name', '')
    if nm.startswith('市民大道') and not any(x in nm for x in ('巷', '弄')): continue
    xy = [tf(lo, la) for lo, la in w['c']]
    if not any(bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3] for x, y in xy) or len(xy) < 2: continue
    g = LineString(xy)
    for sd in (+1, -1):
        x = g.intersection(EDGE[sd])
        for q in getattr(x, 'geoms', [x]):
            if x.is_empty or q.geom_type != 'Point': continue
            tq = C.project(q)
            if not (s0 - 5 <= tq <= s1 + 5): continue
            if blocks.buffer(-0.8).contains(q): continue            # 落在街廓內（非街廓之間的開口）
            # 走向與大道夾角 > 40°，且通往後方（離中心線更遠處仍有路段）
            loc = g.intersection(q.buffer(15))
            segs = [np.asarray(s_.coords) for s_ in getattr(loc, 'geoms', [loc]) if s_.geom_type == 'LineString' and s_.length > 3]
            if not segs: continue
            v = np.vstack(segs); v = v - v.mean(axis=0); dv = np.linalg.svd(v, full_matrices=False)[2][0]
            u, _ = normal(tq)
            if abs(float(np.dot(dv, u))) > .77: continue
            dq = C.distance(q)
            if max(C.distance(Point(c)) for c in xy) < dq + 12: continue
            if hw in PATHS or hw == 'pedestrian': typ = 'path_mouth'
            elif nm and not any(x_ in nm for x_ in ('巷', '弄')) and hw not in ('service',): typ = 'street'
            else: typ = 'lane'
            cand.append((tq, sd, typ, nm, q))
RANK = {'street': 0, 'lane': 1, 'path_mouth': 2}
cand.sort(key=lambda c: (c[1], c[0]))
mouths = []
for c in cand:
    # 同側 10 m 內，或同名道路 25 m 內（雙向分隔車道、無名巷併入相鄰具名街）視為同一街口
    if mouths and mouths[-1][1] == c[1] and (c[0] - mouths[-1][0] <= 10 or
                                             (c[0] - mouths[-1][0] <= 25 and (c[3] == mouths[-1][3] or not c[3] or not mouths[-1][3]))):
        if RANK[c[2]] < RANK[mouths[-1][2]] or (not mouths[-1][3] and c[3]): mouths[-1] = c
        continue
    mouths.append(c)
for tq, sd, typ, nm, q in mouths:
    add(q, kind='demand', type=typ, name=nm, side='N' if sd > 0 else 'S', s=round(tq, 1))

# ---------- 3. 需求點：捷運／地下街出入口、公車站、YouBike ----------
RB = R.buffer(25)
NEAR = 80
seen = []
for n in json.load(open(PRE / 'osm_nodes.json')):
    t = n['t']
    if not t: continue
    typ = None
    if t.get('railway') in ('subway_entrance', 'train_station_entrance'): typ = 'mrt'
    elif t.get('highway') == 'bus_stop' or (t.get('public_transport') == 'platform' and t.get('bus') == 'yes'): typ = 'bus'
    elif t.get('amenity') == 'bicycle_rental': typ = 'bike'
    if not typ: continue
    if '緊急' in t.get('name', ''): continue          # 緊急出口非一般出入口
    p = Point(tf(n['lon'], n['lat']))
    if not RB.contains(p) or C.distance(p) > NEAR: continue     # 只取大道旁（距中心線 80 m 內）
    tq = C.project(p)
    if not (s0 - 5 <= tq <= s1 + 5): continue
    if typ == 'bus' and any(o[0] == 'bus' and o[1].distance(p) < 12 for o in seen): continue   # 同站重複節點
    seen.append((typ, p))
    add(p, kind='demand', type=typ, name=t.get('name', ''), ref=t.get('ref', ''), side=side_of(p), s=round(tq, 1))

# ---------- 4. 需求點：設施（公園、醫院、學校、博物館／園區）----------
FAC = {'school': '學校', 'university': '學校', 'college': '學校', 'kindergarten': '學校', 'hospital': '醫院', 'museum': '博物館',
       'attraction': '園區', 'gallery': '博物館', 'park': '公園', 'library': '圖書館', 'community_centre': '社區中心', 'marketplace': '市場'}
ent_nodes = [(Point(tf(n['lon'], n['lat'])), n['t']) for n in json.load(open(PRE / 'osm_nodes.json'))
             if n['t'] and n['t'].get('entrance') in ('main', 'yes', 'entrance')]
for w in json.load(open(PRE / 'osm_areas.json')):
    t = w['t']; key = t.get('amenity') or t.get('tourism') or t.get('leisure')
    if key not in FAC or len(w['c']) < 4: continue
    g = Polygon([tf(*q) for q in w['c']]).buffer(0)
    if not g.intersects(R.buffer(40)) or (key == 'park' and g.area < 3000): continue
    near = [p for p, tt in ent_nodes if g.buffer(3).contains(p) and R.buffer(60).contains(p)]
    if near: p = min(near, key=lambda p: C.distance(p)); src = 'OSM 入口'
    else:
        gi = g.intersection(R.buffer(5))
        if gi.is_empty: continue
        from shapely.ops import nearest_points
        p = nearest_points(gi.boundary, C)[0]; src = '設施臨大道處'
    tq = C.project(p)
    if not (s0 - 30 <= tq <= s1 + 30): continue
    add(p, kind='demand', type='facility', fac=FAC[key], name=t.get('name', ''), src=src, side=side_of(p), s=round(tq, 1))

# ---------- 4b. 需求點：大量體（大型商辦、高樓）----------
#   第一排街廓內之線稿建物；高樓＝臺北三維模型（2017）高度 ≥ 36 m 或 OSM ≥ 12 層；大型商辦／公共量體＝建築面積 ≥ 2,000 m²（住宅、學校除外）
#   需求點位置＝建物之 OSM 入口（3 m 內），否則建物外輪廓上最靠近大道之點
H_MIN, LV_MIN, A_MIN = 36.0, 12, 2000.0
USE_FIX = {'主廳舍': '博物館・鐵道部園區'}
T3 = []
for f_ in json.load(open(H.parents[1] / '02_調整過程/歷次處理與版本紀錄/過程_臺北三維參照/civic_approximate_buildings_wgs84.geojson'))['features']:
    g_ = transform(tf, shape(f_['geometry'])).buffer(0)
    if not g_.is_empty and f_['properties'].get('height'): T3.append((g_, float(f_['properties']['height'])))
t3tree = STRtree([g_ for g_, _ in T3])
PCS = json.load(open(H.parents[0] / '03_南京至仁愛_沿線土地使用分析_20261006/data/landuse_pieces_EPSG3826.geojson'))['features']
bagg = collections.defaultdict(lambda: {'lv': 0, 'names': collections.Counter(), 'cls': collections.Counter()})
for f_ in PCS:
    pr_ = f_['properties']
    if not shape(f_['geometry']).intersects(R): continue
    b_ = bagg[pr_['bid']]
    if pr_['levels']: b_['lv'] = max(b_['lv'], pr_['levels'])
    if pr_['name']: b_['names'][pr_['name']] += pr_['area']
    b_['cls'][pr_['cls_bld']] += pr_['area']
named_areas = []
for w in json.load(open(PRE / 'osm_areas.json')):
    if w['t'].get('name') and len(w['c']) >= 4:
        xy = [tf(*q) for q in w['c']]
        if any(abs(x - R.centroid.x) < 1500 and abs(y - R.centroid.y) < 800 for x, y in xy):
            g_ = Polygon(xy).buffer(0)
            if not g_.is_empty: named_areas.append((g_, w['t']['name']))
BL = list(S.bld.geoms)
inR = R.buffer(-1)
for bid, b_ in bagg.items():
    g = BL[bid]
    if g.intersection(R).area < .5 * g.area: continue
    hs = [h for i_ in t3tree.query(g) for gg, h in [T3[i_]] if gg.intersects(g) and gg.intersection(g).area > .2 * min(g.area, 400)]
    hmax = max(hs, default=0); cls = b_['cls'].most_common(1)[0][0]
    tall = hmax >= H_MIN or b_['lv'] >= LV_MIN
    big = g.area >= A_MIN and cls not in ('RES', 'EDU')
    if not (tall or big): continue
    nm = b_['names'].most_common(1)[0][0] if b_['names'] else ''
    if not nm:
        c_ = g.representative_point()
        cands = [(a_.area, n_) for a_, n_ in named_areas if a_.contains(c_) and a_.area < 20 * g.area]
        nm = min(cands)[1] if cands else ''
    ents = [p_ for p_, tt in ent_nodes if g.buffer(3).contains(p_)]
    if ents: pt = min(ents, key=lambda q: C.distance(q)); src = 'OSM 入口'
    else:
        from shapely.ops import nearest_points
        pt = nearest_points(g.exterior, C)[0]; src = '面向大道之外牆'
    tq = C.project(pt)
    if not (s0 - 10 <= tq <= s1 + 10): continue
    use = {'COM': '商業', 'OFF': '辦公', 'GOV': '機關', 'MED': '醫療', 'TRN': '交通', 'HER': '文化', 'RES': '住宅', 'UNK': '', 'IND': '', 'MIX': '商住'}.get(cls, '')
    if '雙星' in nm or '雙子星' in nm: use = '興建中'
    lv = max(b_['lv'] or 0, round(hmax / 3.3) if hmax else 0)          # OSM 層數與三維高度換算取大者
    use = USE_FIX.get(nm, use)
    add(pt, kind='demand', type='bulk', name=nm, use=use, levels=int(lv) if lv else None, height=round(hmax, 1) if hmax else None,
        footprint=round(g.area), tall=bool(tall), big=bool(big), bid=bid, src=src, side=side_of(pt), s=round(tq, 1))
    add(g, kind='bulk_bld', bid=bid, side=side_of(pt))

# 三類以外之需求點（公車站、YouBike、設施）不列入
OUT[:] = [f for f in OUT if not (f['properties']['kind'] == 'demand' and f['properties']['type'] in ('bus', 'bike', 'facility'))]
CAT = {'street': 'alley', 'lane': 'alley', 'path_mouth': 'alley', 'mrt': 'transit', 'bulk': 'bulk'}
for f in OUT:
    if f['properties']['kind'] == 'demand': f['properties']['cat'] = CAT[f['properties']['type']]

# ---------- 5. 供給點 ----------
road = S.road
cw = [shape(f['geometry']) for f in json.load(open(H / 'data/street_detail_EPSG3826.geojson'))['features'] if f['properties']['kind'] == 'crosswalk']
corr = R.intersection(C.buffer(45)).intersection(road.buffer(1))
at = []
for g in cw:
    if not g.intersects(corr): continue
    c = g.centroid; t = C.project(c)
    if not (s0 - 20 <= t <= s1 + 20): continue
    r = np.asarray(g.minimum_rotated_rectangle.exterior.coords)
    e = max((r[1] - r[0], r[2] - r[1]), key=np.linalg.norm); e = e / np.linalg.norm(e)
    u, _ = normal(t)
    if abs(float(np.dot(e, u))) < 0.55: at.append((t, g))
at.sort(key=lambda x: x[0])
groups = []
for t, g in at:
    if groups and t - groups[-1][-1][0] <= 45: groups[-1].append((t, g))
    else: groups.append([(t, g)])
street = R.difference(unary_union(d['blocks']).buffer(-0.5))
def cross_width(t):
    res = []
    for dt in (-30, -20, 20, 30):
        tt = t + dt
        if not (0 < tt < C.length): continue
        p = np.array(C.interpolate(tt).coords[0]); _, n = normal(tt)
        ln = LineString([p - n * 70, p + n * 70]).intersection(street).intersection(road)
        segs = [q for q in getattr(ln, 'geoms', [ln]) if q.geom_type == 'LineString' and q.length > 2.5]
        if not segs: continue
        ss = sorted(float(np.dot(np.array(c) - p, n)) for q in segs for c in q.coords)
        res.append((ss[-1] - ss[0], len(segs)))
    if not res: return 0, 0
    res.sort(); return round(res[len(res) // 2][0], 1), res[len(res) // 2][1]
for gr in groups:
    t = float(np.mean([x[0] for x in gr]))
    span, nseg = cross_width(t)
    for _, g in gr: add(g, kind='supply_stripe')
    add(Point(C.interpolate(t).coords[0]), kind='supply', type='at_grade', s=round(t, 1), n_crosswalks=len(gr), span_m=span, n_stages=nseg)
for L in json.load(open(PRE / 'a1_crossings.json'))['civic']['locations']:
    p = Point(tf(*L['ll'])); t = C.project(p)
    if not (s0 - 20 <= t <= s1 + 20): continue
    kinds = set(L['kinds'])
    if 'footbridge' in kinds or ('tunnel' in kinds and any('地下街' in n for n in L['names'])):
        typ = 'footbridge' if 'footbridge' in kinds else 'underground'
        add(Point(C.interpolate(t).coords[0]), kind='supply', type=typ, s=round(t, 1), name='、'.join(L['names'][:3]))

# ---------- 6. 每個需求點：原因與匯聚路口 ----------
#   原因＝該點之類型與名稱；匯聚路口＝沿大道距離最近之平面穿越路口（十字路口），距離＝里程差（沿人行道），不做路網推算
def street_name(pt):
    t = C.project(pt); u, _ = normal(t)
    best = None
    for nm_, g in S.streets.items():
        if nm_.startswith('市民大道'): continue
        d_ = g.distance(pt)
        if d_ >= 45: continue
        loc = g.intersection(pt.buffer(60))
        segs = [np.asarray(q.coords) for q in getattr(loc, 'geoms', [loc]) if q.geom_type == 'LineString' and q.length > 5]
        if not segs: continue
        v = np.vstack(segs); v = v - v.mean(axis=0); dv = np.linalg.svd(v, full_matrices=False)[2][0]
        if abs(float(np.dot(dv, u))) > .7: continue
        if best is None or d_ < best[0]: best = (d_, nm_)
    return best[1] if best else ''
XING = []
for f in OUT:
    pr = f['properties']
    if pr['kind'] == 'supply' and pr['type'] == 'at_grade':
        pr['name'] = street_name(shape(f['geometry'])) or f"里程 {pr['s']:.0f} m"
        XING.append((pr['s'], pr['name']))
STATIONS = []
for n in json.load(open(PRE / 'osm_nodes.json')):
    t = n['t']
    if t and t.get('railway') == 'station' and t.get('station') == 'subway':
        STATIONS.append((Point(tf(n['lon'], n['lat'])), t.get('name', '')))
def reason(pr, g):
    typ, nm = pr['type'], pr.get('name', '') or ''
    if typ == 'street': return f'{nm} 街口'
    if typ == 'lane': return f'{nm} 巷口' if nm else '無名巷口'
    if typ == 'path_mouth': return f'{nm} 步道口' if nm else '步道口'
    if typ == 'mrt':
        ref = (pr.get('ref') or '').strip()
        if ref.startswith('Y') or nm.startswith('Y'): return f"台北地下街 {(ref or nm).strip()} 出口"
        stn = min(STATIONS, key=lambda q: q[0].distance(g))[1] if STATIONS else ''
        no = (nm or ref).replace('號出入口', '').strip()
        stn = stn if stn.endswith('站') else stn + '站'
        return f'{stn} {no}號出口' if no else f'{stn} 出入口'
    if typ == 'bus': return f'公車站 {nm}'.strip()
    if typ == 'bike': return f"YouBike {nm.replace('YouBike2.0_', '').replace('YouBike1.0_', '')}".strip()
    if typ == 'facility': return f"{nm}（{pr.get('fac', '')}）"
    if typ == 'bulk':
        d_ = []
        if pr.get('levels'): d_.append(f"{pr['levels']} 層")
        if pr.get('big') and not pr.get('tall'): d_.append(f"{pr['footprint']:,} m2")
        if pr.get('use'): d_.insert(0, pr['use'])
        return f"{nm or '大樓'}（{'・'.join(d_)}）"
    return nm
# ---------- 7. 同側步行路網：需求點沿人可走之路線到路口角落 ----------
#   路網＝OSM 可步行路段（2026-09-09 osm_ways.json；同 pedgraph 規則）；排除：跨越大道之路段（與中心線相交、或大道走廊內垂直大道之行穿線）、
#   市民大道本身之車道中心線（人走人行道）、地下／隧道／室內路段。只計算同側，不跨大道。
import networkx as nx
from scipy.spatial import cKDTree
WALK_NO2 = {'no', 'private', 'discouraged'}
PED_HW = {'footway', 'path', 'pedestrian', 'steps', 'living_street', 'residential', 'service', 'unclassified', 'tertiary', 'secondary',
          'primary', 'cycleway', 'corridor', 'track', 'road', 'tertiary_link', 'secondary_link', 'primary_link'}
def walkable(t):
    if t.get('foot') in WALK_NO2: return False
    if t.get('access') in WALK_NO2 and t.get('foot') not in ('yes', 'designated', 'permissive'): return False
    hw = t.get('highway')
    if hw is None: return False
    if hw in ('motorway', 'motorway_link', 'trunk', 'trunk_link', 'construction', 'proposed'): return t.get('foot') in ('yes', 'designated', 'permissive')
    return hw in PED_HW
def lvl(t):
    for k_ in ('layer', 'level'):
        try:
            if float(str(t.get(k_, '0')).split(';')[0]) < 0: return True
        except ValueError: pass
    return t.get('tunnel') in ('yes',) or t.get('indoor') == 'yes'
Cz = LineString([C.interpolate(v).coords[0] for v in np.arange(max(0, s0 - 400), min(C.length, s1 + 400), 3)])
# 人行道主線（每側一條，連續、與路緣平行、置於人行道中央）：
#   路緣距離＝沿垂直線第一排街廓前最後一段道路面之外緣；人行道寬＝路緣外官方人行道範圍之連續寬度（無資料取 3 m）
#   兩者各以 ±40 m 滾動中位數（跨過橫街口）後 ±15 m 平滑；主線＝路緣 + 人行道寬／2
SWP = unary_union([shape(f['geometry']) for f in
                  json.load(open(H / 'data/street_detail_EPSG3826.geojson'))['features'] if f['properties']['kind'] in ('sw', 'sw_setback', 'sw_marked')])
def roll(a, half, fn):
    m_ = int(half / 3)
    return np.array([fn(a[max(0, i - m_): i + m_ + 1]) if np.isfinite(a[max(0, i - m_): i + m_ + 1]).any() else np.nan for i in range(len(a))])
def fill(a, default):
    ok = np.isfinite(a)
    return np.interp(np.arange(len(a)), np.where(ok)[0], a[ok]) if ok.any() else np.full(len(a), default)
SPINE = {}
for sd in (+1, -1):
    curb_l, sw_l = [], []
    for t, e_ in zip(ts, edge[sd]):
        p = np.array(C.interpolate(t).coords[0]); _, n = normal(t)
        lim = e_ if np.isfinite(e_) else 90
        ray = LineString([p, p + sd * n * (lim + 2)])
        rx = ray.intersection(road)
        ds = [float(np.linalg.norm(np.array(c) - p)) for q in getattr(rx, 'geoms', [rx]) if not rx.is_empty for c in q.coords]
        curb = max([v for v in ds if v <= lim + .5], default=np.nan)
        w_ = np.nan
        if np.isfinite(curb):
            sx = LineString([p + sd * n * (curb - .5), p + sd * n * (curb + 15)]).intersection(SWP)
            segs_ = [q for q in getattr(sx, 'geoms', [sx]) if not sx.is_empty and q.geom_type == 'LineString']
            if segs_:
                q0 = min(segs_, key=lambda q: min(np.linalg.norm(np.array(c) - p) for c in q.coords))
                if min(np.linalg.norm(np.array(c) - p) for c in q0.coords) <= curb + 2: w_ = q0.length
        curb_l.append(curb); sw_l.append(w_)
    curb_a = fill(roll(np.array(curb_l), 40, np.nanmedian), 20)
    sw_a = fill(roll(np.array(sw_l), 40, np.nanmedian), 3.0)
    sw_a = np.clip(sw_a, 1.5, 10)
    off = curb_a + sw_a / 2
    off = np.array([off[max(0, i - 5): i + 6].mean() for i in range(len(off))])        # ±15 m 平滑
    keep = [(float(t), tuple(np.array(C.interpolate(t).coords[0]) + sd * normal(t)[1] * o)) for t, o in zip(ts, off)
            if s0 - 15 <= t <= s1 + 15]                      # 只在本段範圍內（河堤端外不延伸）
    SPINE['N' if sd > 0 else 'S'] = keep
    add(LineString([q for _, q in keep]), kind='spine', side='N' if sd > 0 else 'S')
corr45 = C.buffer(45)
bb2 = R.buffer(500).bounds
# 沿大道之行走一律走人行道中線（主線）：移除落在主線 12 m 帶內、且與大道平行之 OSM 路段（避免路線在人行道上歪斜）
SPL = {sd: LineString([q for _, q in SPINE[sd]]) for sd in SPINE}
SPB = unary_union([SPL[sd].buffer(12) for sd in SPL])
G = nx.Graph(); coord = {}
for w in json.load(open(PRE / 'osm_ways.json')):
    t = w['t']
    if not walkable(t) or lvl(t): continue
    nm = t.get('name', '')
    if nm.startswith('市民大道') and not any(x_ in nm for x_ in ('巷', '弄')): continue
    xy = [tf(lo, la) for lo, la in w['c']]
    if not any(bb2[0] <= x <= bb2[2] and bb2[1] <= y <= bb2[3] for x, y in xy): continue
    for i in range(len(w['n']) - 1):
        a_, b_ = w['n'][i], w['n'][i + 1]
        if a_ == b_: continue
        seg = LineString([xy[i], xy[i + 1]])
        if seg.intersects(Cz): continue                                   # 跨越大道中心線
        if SPB.contains(seg):                                             # 人行道帶內與大道平行之路段 → 由主線取代
            v = np.array(xy[i + 1]) - np.array(xy[i]); L = np.linalg.norm(v)
            if L > 0:
                u_, _ = normal(C.project(seg.centroid))
                if abs(float(np.dot(v / L, u_))) > .8: continue
        if t.get('footway') == 'crossing' and seg.intersects(corr45):     # 大道走廊內垂直大道之行穿線（橫越大道車道）
            v = np.array(xy[i + 1]) - np.array(xy[i]); L = np.linalg.norm(v)
            if L > 0:
                u_, _ = normal(C.project(seg.centroid))
                if abs(float(np.dot(v / L, u_))) < .5: continue
        coord[a_] = xy[i]; coord[b_] = xy[i + 1]
        dd = seg.length
        if not G.has_edge(a_, b_) or G[a_][b_]['w'] > dd: G.add_edge(a_, b_, w=dd)
osm_nodes_ = list(coord)
for sd in ('N', 'S'):
    sp = SPINE[sd]
    for i, (t, q) in enumerate(sp):
        coord[('sp', sd, i)] = q
        if i: G.add_edge(('sp', sd, i - 1), ('sp', sd, i), w=float(np.linalg.norm(np.array(q) - np.array(sp[i - 1][1]))))
# OSM 節點 8 m 內接到同側主線（人行道與巷道在大道邊的交會）
sp_pts = {sd: np.array([q for _, q in SPINE[sd]]) for sd in SPINE}
sp_tree = {sd: cKDTree(sp_pts[sd]) for sd in SPINE}
for n in osm_nodes_:
    sd = side_of(Point(coord[n]))
    d_, i_ = sp_tree[sd].query(coord[n])
    if d_ <= 8: G.add_edge(n, ('sp', sd, int(i_)), w=float(d_))
# 與人行道主線交叉之步行路段（橫街人行道、巷道）：交叉處兩端都接到主線（避免路口未接上而繞街廓）
for a_, b_ in list(G.edges()):
    if isinstance(a_, tuple) or isinstance(b_, tuple): continue
    seg = LineString([coord[a_], coord[b_]])
    for sd in SPL:
        x = seg.intersection(SPL[sd])
        if x.is_empty: continue
        q = x if x.geom_type == 'Point' else x.centroid
        d_, i_ = sp_tree[sd].query(q.coords[0])
        if d_ > 6: continue
        for n in (a_, b_):
            w_ = float(np.linalg.norm(np.array(coord[n]) - np.array(SPINE[sd][int(i_)][1])))
            if not G.has_edge(n, ('sp', sd, int(i_))) or G[n][('sp', sd, int(i_))]['w'] > w_:
                G.add_edge(n, ('sp', sd, int(i_)), w=w_)
nid = list(coord); npt = np.array([coord[n] for n in nid]); ktree = cKDTree(npt)
nside = {n: (n[1] if isinstance(n, tuple) else side_of(Point(coord[n]))) for n in nid}
def snap_side(pt, sd, maxd=25):
    dd, ii = ktree.query(pt.coords[0], k=40, distance_upper_bound=maxd)
    for d_, i_ in zip(np.atleast_1d(dd), np.atleast_1d(ii)):
        if np.isfinite(d_) and i_ < len(nid) and nside[nid[i_]] == sd and nid[i_] in G: return nid[i_], float(d_)
    return None, None
# 路口角落節點＝人行道主線上該路口里程處（行穿線在該側之落點）
corner_node = {}
for cs_, cn in XING:
    for sd in ('N', 'S'):
        i_ = int(np.argmin([abs(t - cs_) for t, _ in SPINE[sd]]))
        corner_node[(cn, sd)] = (('sp', sd, i_), Point(SPINE[sd][i_][1]))
print('walk graph', G.number_of_nodes(), 'nodes; corners', len(corner_node), '/', 2 * len(XING))
dem = [f for f in OUT if f['properties']['kind'] == 'demand']
routes = []
for sd in ('N', 'S'):
    targets = {corner_node[(cn, sd)][0]: cn for cs_, cn in XING if (cn, sd) in corner_node}
    for i, f in enumerate(sorted([f for f in dem if f['properties']['side'] == sd], key=lambda f: f['properties']['s'])):
        pr = f['properties']; g = shape(f['geometry'])
        pr['id'] = f'{sd}{i + 1:02d}'
        pr['reason'] = reason(pr, g)
        # 吸附：同側 25 m 內（無則 45 m）之路網節點；吸附段權重 ×3，優先接最近之步道（避免長直線）
        # 大量體：建物外牆 15 m 內（無則 60 m）之同側路網節點皆可為入口，由步行距離決定；入口點＝外牆上最靠近該節點處
        best = None
        bg = None
        if pr['type'] == 'bulk' and pr.get('src') != 'OSM 入口':
            bg = next(shape(ff['geometry']) for ff in OUT if ff['properties']['kind'] == 'bulk_bld' and ff['properties']['bid'] == pr['bid'])
        for rad in ((15, 30, 60) if bg is not None else (25, 45)):
            if bg is not None:
                idx = ktree.query_ball_point(bg.centroid.coords[0], r=rad + np.sqrt(bg.area))
                cand = [(bg.exterior.distance(Point(coord[nid[i_]])), nid[i_]) for i_ in idx if nside[nid[i_]] == sd and nid[i_] in G]
                cand = [(d_, n_) for d_, n_ in cand if d_ <= rad]
                # 入口限面向大道之一側：節點距大道中心線不超過建物最近距離 + 25 m
                front = C.distance(bg) + 25
                fc_ = [(d_, n_) for d_, n_ in cand if C.distance(Point(coord[n_])) <= front]
                cand = fc_ if (fc_ or rad < 60) else cand        # 前側找不到時先放大半徑，最後才接受背面
            else:
                dd, ii = ktree.query(g.coords[0], k=60, distance_upper_bound=rad)
                cand = [(float(d_), nid[i_]) for d_, i_ in zip(np.atleast_1d(dd), np.atleast_1d(ii))
                        if np.isfinite(d_) and i_ < len(nid) and nside[nid[i_]] == sd and nid[i_] in G]
            if not cand: continue
            G.add_node('SRC')
            for d_, n_ in cand: G.add_edge('SRC', n_, w=d_ * 3)
            dist, path = nx.single_source_dijkstra(G, 'SRC', cutoff=1000, weight='w')
            G.remove_node('SRC')
            for tn, cn in targets.items():
                if tn in dist and (best is None or dist[tn] < best[0]): best = (dist[tn], cn, path[tn][1:])
            if best: break
        d0 = 0.0
        if best and bg is not None:     # 大量體入口點落在外牆上最靠近起始節點處
            from shapely.ops import nearest_points
            g = nearest_points(bg.exterior, Point(coord[best[2][0]]))[0]
            f['geometry'] = mapping(g); pr['s'] = round(C.project(g), 1); pr['src'] = '外牆最近步行路網處'
        if best:
            snap_len = float(np.linalg.norm(np.array(coord[best[2][0]]) - np.array(g.coords[0])))
            best = (best[0] - 2 * snap_len, best[1], best[2])           # 扣回 ×3 權重，距離以實際步行長度計
            line = [g.coords[0]] + [coord[n] for n in best[2]]
            # 去除主線上之重複折點
            line = [q for k_, q in enumerate(line) if k_ == 0 or q != line[k_ - 1]]
            pr['conv'] = best[1]; pr['conv_dist'] = round(best[0] + d0); pr['route'] = 'network'
            pr['conv_s'] = next(cs_ for cs_, cn in XING if cn == best[1])
            routes.append((LineString(line), pr['id'], sd, best[1]))
        elif XING:   # 路網無法連通：沿大道里程最近路口（標註）
            cs_, cn = min(XING, key=lambda x: abs(x[0] - pr['s']))
            pr['conv'] = cn; pr['conv_s'] = cs_; pr['conv_dist'] = round(abs(cs_ - pr['s'])); pr['route'] = 'fallback'
for ln, did, sd, cn in routes:
    add(ln, kind='route', id=did, side=sd, conv=cn)
conv_cnt = collections.Counter((f['properties']['conv'], f['properties']['side']) for f in dem if 'conv' in f['properties'])
for cs_, cn in XING:
    for sd in ('N', 'S'):
        if (cn, sd) in corner_node:
            add(corner_node[(cn, sd)][1], kind='conv_corner', conv=cn, side=sd, s=cs_, count=conv_cnt.get((cn, sd), 0))
print('fallback', [f['properties']['id'] for f in dem if f['properties'].get('route') == 'fallback'])

cnt = collections.Counter((f['properties']['kind'], f['properties'].get('type'), f['properties'].get('side')) for f in OUT
                          if f['properties']['kind'] in ('demand', 'supply'))
stats = {'zone': ZONE, 's0': round(s0), 's1': round(s1), 'len_m': round(s1 - s0),
         'counts': {f'{a}|{b}|{c}': v for (a, b, c), v in sorted(cnt.items(), key=lambda x: str(x[0]))}}
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': OUT, 'stats': stats},
          open(H / f'data/{ZONE}_demand_supply_EPSG3826.geojson', 'w'), ensure_ascii=False)
for k_, v in sorted(cnt.items(), key=lambda x: str(x[0])): print(k_, v)
for f in sorted(dem, key=lambda f: f['properties']['id']):
    pr = f['properties']; print(pr['id'], pr['reason'], '→', pr.get('conv'), pr.get('conv_dist'), 'm')
print({f'{k[0]}|{k[1]}': v for k, v in conv_cnt.items()})
