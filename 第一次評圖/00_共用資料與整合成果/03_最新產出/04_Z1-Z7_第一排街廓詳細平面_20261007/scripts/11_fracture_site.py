# 南北斷裂證據＋操作基地（單元主題圖資料；先做 Z1）
#   斷裂：沿市民大道中心線每 50 m，於南北各 150 m 取一對點，在 OSM 步行路網上求最短路徑
#         （方法同 2026-09-09 E2 繞路係數：offset 150 m、直線需求 300 m；控制組為五條平行東西向幹道）；
#         記錄路徑幾何、繞路係數、實際穿越位置。
#         平面穿越點：交工處行人穿越線中，位於大道路面、且行走方向與大道垂直者（依里程 25 m 群聚）；
#         立體穿越：OSM footway bridge／地下街（2026-09-09 a1 清單）。
#   操作基地：橋下空間（橋面投影 ∩ 本段）分「橋下分隔島／空地」「橋下車道」；
#         高架兩側閒置：OSM 平面停車場、施工中／待開發、空地（brownfield 等）、零星草地；
#         第一排街廓內未建築且無標記之空地（≥ 300 m²，待現勘）；高架旁交通島／畸零地（道路範圍內之非街廓空地）。
import json, sys, math, collections
from pathlib import Path
import numpy as np
import networkx as nx
from scipy.spatial import cKDTree
from shapely.geometry import shape, mapping, Point, LineString, Polygon, box
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
STEP, OFFSET = 50.0, 150.0
C = S.center
d = S.PZ(ZONE); R = d['R']
cuts = [shape(f['geometry']) for f in S.ZF if 'cut' in f['properties']]
def station(g):
    x = g.intersection(C); return C.project(x.centroid if not x.is_empty else g.centroid)
k = int(ZONE[1:])
s0 = station(cuts[k - 1]); s1 = station(cuts[k]) if k < len(cuts) else C.length
OUT = []
def add(g, **p):
    if g is not None and not g.is_empty: OUT.append({'type': 'Feature', 'geometry': mapping(g), 'properties': p})

# ---------- 1. 步行路網（2026-09-09 擷取之 OSM ways；同 pedgraph.walkable 規則）----------
WALK_NO = {'no', 'private', 'discouraged'}
PED_HW = {'footway', 'path', 'pedestrian', 'steps', 'living_street', 'residential', 'service', 'unclassified', 'tertiary', 'secondary',
          'primary', 'cycleway', 'corridor', 'track', 'road', 'tertiary_link', 'secondary_link', 'primary_link'}
def walkable(t):
    if t.get('foot') in WALK_NO: return False
    if t.get('access') in WALK_NO and t.get('foot') not in ('yes', 'designated', 'permissive'): return False
    hw = t.get('highway')
    if hw is None: return False
    if hw in ('motorway', 'motorway_link', 'trunk', 'trunk_link', 'construction', 'proposed'):
        return t.get('foot') in ('yes', 'designated', 'permissive')
    return hw in PED_HW
bb = R.buffer(900).bounds
G = nx.Graph(); coord = {}; wtag = {}
for w in json.load(open(PRE / 'osm_ways.json')):
    if not walkable(w['t']): continue
    xy = [tf(lon, lat) for lon, lat in w['c']]
    if not any(bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3] for x, y in xy): continue
    for r, p in zip(w['n'], xy): coord[r] = p
    for i in range(len(w['n']) - 1):
        a, b = w['n'][i], w['n'][i + 1]
        if a == b: continue
        dd = math.dist(xy[i], xy[i + 1])
        if not G.has_edge(a, b) or G[a][b]['w'] > dd:
            G.add_edge(a, b, w=dd, way=w['id']); wtag[w['id']] = w['t']
giant = max(nx.connected_components(G), key=len)
ids = np.array([n for n in coord if n in giant]); pts = np.array([coord[n] for n in ids]); tree = cKDTree(pts)
def snap(p, maxd=90):
    dd, i = tree.query(p, distance_upper_bound=maxd)
    return (int(ids[i]), float(dd)) if np.isfinite(dd) else (None, None)
print('graph', G.number_of_nodes(), 'nodes; giant', len(giant))

# ---------- 2. 取樣：南北各 150 m 之最短路徑 ----------
def normal(t):
    a = np.array(C.interpolate(max(0, t - 15)).coords[0]); b = np.array(C.interpolate(min(C.length, t + 15)).coords[0])
    v = (b - a) / np.linalg.norm(b - a); return np.array([-v[1], v[0]])
probes = []
for t in np.arange(s0 + STEP / 2, s1, STEP):
    p = np.array(C.interpolate(t).coords[0]); n = normal(t)
    A, B = p + n * OFFSET, p - n * OFFSET
    na, da = snap(A); nb, db = snap(B)
    if na is None or nb is None or na == nb: continue
    try: path = nx.dijkstra_path(G, na, nb, weight='w')
    except nx.NetworkXNoPath: continue
    line = LineString([coord[q] for q in path])
    net = line.length + da + db
    x = line.intersection(C)
    xs = sorted(C.project(q) for q in getattr(x, 'geoms', [x]) if not x.is_empty and q.geom_type == 'Point')
    cross = min(xs, key=lambda v: abs(v - t)) if xs else None
    pr = {'kind': 'probe', 's': round(float(t), 1), 'net_m': round(net, 1), 'detour': round(net / (2 * OFFSET), 3),
          'extra_m': round(net - 2 * OFFSET, 1), 'cross_s': round(cross, 1) if cross is not None else None,
          'A': [round(v, 2) for v in A], 'B': [round(v, 2) for v in B]}
    probes.append(pr)
    add(LineString([tuple(A)] + list(line.coords) + [tuple(B)]), **pr)
det = np.array([q['detour'] for q in probes])
ctrl = json.load(open(PRE / 'b_detour.json'))['controls']
ctrl_mean = float(np.mean([c['detour_mean'] for c in ctrl])); ctrl_extra = float(np.mean([c['extra_walk_mean_m'] for c in ctrl]))
stats = {'zone': ZONE, 's0': round(s0), 's1': round(s1), 'len_m': round(s1 - s0), 'n_probes': len(probes),
         'detour_mean': round(float(det.mean()), 2), 'detour_median': round(float(np.median(det)), 2), 'detour_max': round(float(det.max()), 2),
         'extra_mean_m': round(float(np.mean([q['extra_m'] for q in probes]))),
         'share_over_1_8': round(float((det >= 1.8).mean()), 2), 'share_over_2': round(float((det >= 2).mean()), 2),
         'control_detour_mean': round(ctrl_mean, 2), 'control_extra_mean_m': round(ctrl_extra),
         'controls': {c['label']: c['detour_mean'] for c in ctrl}}

# ---------- 3. 穿越點 ----------
road = S.road
cw = [shape(f['geometry']) for f in json.load(open(H / 'data/street_detail_EPSG3826.geojson'))['features'] if f['properties']['kind'] == 'crosswalk']
corr = R.intersection(C.buffer(45)).intersection(road.buffer(1))      # 大道路面帶
at = []
for g in cw:
    if not g.intersects(corr): continue
    c = g.centroid; t = C.project(c)
    if not (s0 - 20 <= t <= s1 + 20): continue
    r = np.asarray(g.minimum_rotated_rectangle.exterior.coords)
    e = max((r[1] - r[0], r[2] - r[1]), key=np.linalg.norm); e = e / np.linalg.norm(e)
    a2 = np.array(C.interpolate(min(C.length, t + 10)).coords[0]) - np.array(C.interpolate(max(0, t - 10)).coords[0]); a2 /= np.linalg.norm(a2)
    if abs(float(np.dot(e, a2))) < 0.55:     # 行走方向與大道夾角 > 約 57°：橫越大道
        at.append((t, g))
at.sort(key=lambda x: x[0])
groups = []
for t, g in at:
    if groups and t - groups[-1][-1][0] <= 45: groups[-1].append((t, g))   # 同一路口之多組行穿線合併
    else: groups.append([(t, g)])
crossings = []
street = R.difference(unary_union(d['blocks']).buffer(-0.5))    # 第一排街廓之間的公共道路空間
def cross_width(t):
    # 穿越大道需走過之車道：於路口前後 20–30 m（避開橫街本身）沿垂直線量測，取中位數
    #   車道段＝線稿道路面（分隔島為孔洞）∩ 第一排街廓間之道路空間；span＝南北最外側車道緣距離（含分隔島）
    res = []
    for dt in (-30, -20, 20, 30):
        tt = t + dt
        if not (0 < tt < C.length): continue
        p = np.array(C.interpolate(tt).coords[0]); n = normal(tt)
        ln = LineString([p - n * 70, p + n * 70]).intersection(street).intersection(road)
        segs = [q for q in getattr(ln, 'geoms', [ln]) if q.geom_type == 'LineString' and q.length > 2.5]
        if not segs: continue
        ss = sorted(float(np.dot(np.array(c) - p, n)) for q in segs for c in q.coords)
        res.append((ss[-1] - ss[0], sum(q.length for q in segs), len(segs)))
    if not res: return 0, 0, 0
    res.sort(); span, lane, nseg = res[len(res) // 2]
    return round(lane, 1), nseg, round(span, 1)
for gr in groups:
    t = float(np.mean([x[0] for x in gr])); u = unary_union([x[1] for x in gr])
    used = sum(1 for q in probes if q['cross_s'] is not None and abs(q['cross_s'] - t) < 30)
    lane_m, n_seg, span_m = cross_width(t)
    crossings.append({'s': round(t, 1), 'kind': 'at_grade', 'n_crosswalks': len(gr), 'n_probe_routes': used,
                      'carriageway_m': lane_m, 'n_carriageways': n_seg, 'span_m': span_m})
    add(Point(C.interpolate(t).coords[0]), kind='crossing', s=round(t, 1), type='at_grade', n_crosswalks=len(gr), n_probe_routes=used,
        carriageway_m=lane_m, n_carriageways=n_seg, span_m=span_m)
for L in json.load(open(PRE / 'a1_crossings.json'))['civic']['locations']:
    p = Point(tf(*L['ll'])); t = C.project(p)
    if not (s0 - 20 <= t <= s1 + 20): continue
    kinds = set(L['kinds'])
    if 'footbridge' in kinds or ('tunnel' in kinds and any('地下街' in n for n in L['names'])):
        typ = 'footbridge' if 'footbridge' in kinds else 'underground'
        if any(abs(c['s'] - t) < 15 and c['kind'] == typ for c in crossings): continue
        crossings.append({'s': round(t, 1), 'kind': typ, 'names': L['names'][:3]})
        add(Point(C.interpolate(t).coords[0]), kind='crossing', s=round(t, 1), type=typ, names='、'.join(L['names'][:3]))
crossings.sort(key=lambda c: c['s'])
ag = [c['s'] for c in crossings if c['kind'] == 'at_grade']
gaps = []
edges = [s0] + ag + [s1]
for a_, b_ in zip(edges, edges[1:]):
    if b_ - a_ < 5: continue
    gaps.append({'from': round(a_), 'to': round(b_), 'len_m': round(b_ - a_), 'end': a_ == s0 or b_ == s1})
    add(LineString([C.interpolate(v).coords[0] for v in np.linspace(a_, b_, 20)]), kind='gap', len_m=round(b_ - a_),
        open_end=(a_ == s0 or b_ == s1))
stats |= {'n_at_grade': len(ag), 'n_grade_sep': sum(1 for c in crossings if c['kind'] != 'at_grade'),
          'gap_max_m': max(g['len_m'] for g in gaps if not g['end']) if any(not g['end'] for g in gaps) else None,
          'gaps': gaps}

# ---------- 4. 操作基地 ----------
deck = S.deck.intersection(R)
islands = box(*R.buffer(50).bounds).difference(road)
deck_free = deck.intersection(islands).buffer(0)
deck_road = deck.difference(islands).buffer(0)
add(deck_free, kind='site', cat='under_island', area=round(deck_free.area))
add(deck_road, kind='site', cat='under_road', area=round(deck_road.area))
# OSM 用地標籤
CAT = {}
def cat_of(t):
    if t.get('amenity') == 'parking' and t.get('parking') in (None, 'surface', 'street_side') and t.get('access') != 'private': return 'parking'
    if t.get('landuse') == 'construction' or 'construction' in t: return 'construction'
    if t.get('landuse') in ('brownfield', 'greenfield', 'vacant'): return 'vacant'
    if t.get('landuse') == 'grass' and not t.get('leisure'): return 'grass'
    return None
osm_cat = collections.defaultdict(list)
for w in json.load(open(PRE / 'osm_areas.json')):
    c_ = cat_of(w.get('t', {}))
    if not c_ or len(w['c']) < 4: continue
    g = Polygon([tf(*q) for q in w['c']]).buffer(0)
    if g.intersects(R): osm_cat[c_].append(g)
bld = S.bld.intersection(R.buffer(5))
sw = unary_union([shape(f['geometry']) for f in json.load(open(H / 'data/street_detail_EPSG3826.geojson'))['features']
                  if f['properties']['kind'] in ('sw', 'sw_setback', 'sw_marked')])
green = S.green
taken = deck
idle = {}
for c_ in ('construction', 'vacant', 'parking', 'grass'):
    g = unary_union(osm_cat[c_]).intersection(R).difference(taken).difference(bld) if osm_cat[c_] else Polygon()
    g = unary_union([p for p in S.polys(g) if p.area >= 60])
    idle[c_] = g; taken = unary_union([taken, g])
blocks = unary_union(d['blocks']).intersection(R)
rest = blocks.difference(bld.buffer(1)).difference(sw).difference(green).difference(taken)
idle['open_unlabeled'] = unary_union([p for p in S.polys(rest.buffer(-1.5).buffer(1.5)) if p.area >= 300])
taken = unary_union([taken, idle['open_unlabeled']])
# 高架旁交通島／畸零地：道路範圍內、非第一排街廓、非人行道、離高架 60 m 內之空地
leftover = islands.intersection(R).difference(blocks).difference(sw).difference(taken).difference(bld)
idle['leftover'] = unary_union([p for p in S.polys(leftover) if p.area >= 40 and p.distance(S.elev) < 60])
# 2025 航照（臺北市 Ortho_2025，02_南京至仁愛擴幅 images）逐塊判讀覆寫：(E, N, 判定類別, 說明)；以形心 40 m 內比對
AERIAL = {'Z1': [
    (301366, 2771364, 'vacant_wooded', '樹林覆蓋之未開發空地，零星棚架（OSM 標 residential，線稿無建物；權屬待查）'),
    (301391, 2771408, 'vacant_wooded', '同上，北緣'),
    (301078, 2771408, 'ramp_leftover', '河堤匝道群間之綠地'),
    (301049, 2771316, 'ramp_leftover', '匝道間交通島'),
    (301561, 2771341, 'exclude', '鐵道部園區（國立臺灣博物館）庭園與北門站出入口'),
    (301596, 2771523, 'exclude', '財政部關務署／海關大樓院區'),
    (301357, 2771530, 'exclude', '臺北市立聯合醫院中興院區'),
    (301234, 2771563, 'exclude', '學校操場'),
    (301435, 2771562, 'exclude', '醫院旁通道'),
    (301702, 2771467, 'exclude', '住宅社區中庭'),
    (301896, 2771262, 'developing', '台北雙子星 C1 施工中（航照可見吊車）'),
    (301713, 2771293, 'developing', '台北雙子星 D1 施工中（航照可見吊車）'),
    (301773, 2771426, 'developing', '國王雙子星 施工中'),
    (302089, 2771351, 'exclude', '皇翔臺北廣場：航照已為完工建物（OSM construction 標記過時）'),
    (301977, 2771339, 'small_lot', '小型空地（待現勘）'),
]}
def aerial(p):
    c = p.centroid
    for e, n, cat, note in AERIAL.get(ZONE, []):
        if math.hypot(c.x - e, c.y - n) < 40: return cat, note
    return None, None
for c_, g in idle.items():
    for p in S.polys(g):
        cat, note = aerial(p)
        if cat is None:
            cat, note = {'construction': ('developing', 'OSM 施工中'), 'parking': ('parking', 'OSM 平面停車場'),
                         'vacant': ('vacant', 'OSM 空地'), 'grass': ('leftover', 'OSM 草地'),
                         'open_unlabeled': ('small_lot', '未建築且無標記（待現勘）'),
                         'leftover': ('elev_island', '高架旁分隔島／交通島')}[c_]
        if c_ == 'parking': cat, note = 'parking', note or 'OSM 平面停車場'
        add(p, kind='site', cat=cat, src=c_, area=round(p.area), note=note)
tot = collections.Counter()
for f in OUT:
    if f['properties']['kind'] == 'site': tot[f['properties']['cat']] += f['properties']['area']
stats['site_m2'] = dict(tot)

# ---------- 5. 臨街商業凹陷（E1 方法；店家 POI 沿本段之南北剖面）----------
sys.path.insert(0, str(H.parents[1] / '01_輸入資料/資料處理程式'))
from sectors import classify
ACTIVE = {'餐飲', '零售', '便利超市', '夜生活', '商辦', '金融', '旅宿', '醫療'}
seg = LineString([C.interpolate(v).coords[0] for v in np.arange(s0, s1, 5)])
P_ = []
for n in json.load(open(PRE / 'osm_nodes.json')):
    if classify(n['t']) in ACTIVE: P_.append(tf(n['lon'], n['lat']))
for w in json.load(open(PRE / 'osm_areas.json')):
    if classify(w['t']) in ACTIVE:
        xy = [tf(*q) for q in w['c']]; P_.append((sum(q[0] for q in xy) / len(xy), sum(q[1] for q in xy) / len(xy)))
sd = []
for x, y in P_:
    pt = Point(x, y); dd = seg.distance(pt)
    if dd > 400: continue
    t = seg.project(pt)
    if t <= 5 or t >= seg.length - 5: continue
    a_ = np.array(seg.interpolate(max(0, t - 15)).coords[0]); b_ = np.array(seg.interpolate(min(seg.length, t + 15)).coords[0])
    side = 1 if ((b_[0] - a_[0]) * (y - a_[1]) - (b_[1] - a_[1]) * (x - a_[0])) > 0 else -1
    sd.append(side * dd)
sd = np.array(sd)
inner = (np.abs(sd) <= 50).sum() / (seg.length * 100 / 1e4)
ref = ((np.abs(sd) >= 200) & (np.abs(sd) <= 400)).sum() / (seg.length * 400 / 1e4)
gg = json.load(open(PRE / 'g_gradient.json'))
ctrl_tr = {k: v['active']['trough_depth'] for k, v in gg.items() if isinstance(v, dict) and 'active' in v and k != '市民大道'}
stats['frontage'] = {'inner_per_ha': round(inner, 2), 'ref_per_ha': round(ref, 2), 'trough': round(1 - inner / ref, 3) if ref else None,
                     'civic_all_trough': gg.get('市民大道', {}).get('active', {}).get('trough_depth'), 'controls': ctrl_tr}

json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': OUT, 'stats': stats},
          open(H / f'data/{ZONE}_fracture_site_EPSG3826.geojson', 'w'), ensure_ascii=False)
print(json.dumps({k: v for k, v in stats.items() if k not in ('gaps',)}, ensure_ascii=False, indent=1))
print('gaps', [(g['from'], g['to'], g['len_m']) for g in gaps])
print('crossings', [(c['s'], c['kind'], c.get('n_probe_routes'), c.get('carriageway_m'), c.get('n_carriageways'), c.get('span_m')) for c in crossings])
