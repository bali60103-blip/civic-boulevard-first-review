# 街道細部：人行道、騎樓、車道線、行人穿越線（Z1–Z7 第一排街廓範圍）
# 人行道：臺北市新工處人行道範圍（code 退縮地＝無遮簷人行道另列）＋交工處標線型人行道
# 行穿線：交工處行人穿越線圖資（斑馬紋／枕木紋）
# 騎樓：臨路建物沿道路境界線向內 3.64 m（臺北市建築管理自治條例第 7 條）；
#       停管處「機車退出騎樓路段」路段名稱含「騎樓」者為官方路段，標「僅人行道」者不畫，其餘依規則推估
# 車道線：OSM lanes／oneway＋車道面（線稿道路面扣除人行道）逐 3 m 垂直剖面等分；為推估，非標線測量
# 樹穴／花圃：新工處人行道固定設施物_樹穴（TP_TREE.json）；通風井：OSM man_made=ventilation_shaft；捷運出入口：OSM（06_extract_osm_points.py）
import json, re, glob, collections
from pathlib import Path
import numpy as np
import shapefile
from shapely.geometry import shape, mapping, LineString, Point, MultiLineString
from shapely.ops import unary_union, transform, linemerge
from shapely.strtree import STRtree
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
ROOT = H.parents[1]
BASE = ROOT / '03_最新產出/02_南京至仁愛擴幅_20261005'
LU = ROOT / '03_最新產出/03_南京至仁愛_沿線土地使用分析_20261006'
REB = Path.home() / 'Desktop/Civic_Rebuild_20260909_201934/data'   # 2026-09-09 下載之市府人行道範圍
SRC = H / 'data/source_taipei'
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform

ARC_W = 3.64        # 騎樓寬（自道路境界線起算）
TOUCH = 1.5         # 建物邊距道路境界 ≤ TOUCH m 視為臨路貼齊
LANE_MIN, LANE_MAX = 2.6, 5.2
STEP = 3

RG = json.load(open(H / 'data/frontage_region_EPSG3826.geojson'))['features']
REG = {f['properties']['zone']: shape(f['geometry']) for f in RG if f['properties']['kind'] == 'region'}
# 完整版範圍（Z4、Z6、Z7 不截斷、跨界街廓整塊）一併處理
for f in RG:
    if f['properties']['kind'] == 'region_full':
        REG[f['properties']['zone']] = unary_union([REG.get(f['properties']['zone'], shape(f['geometry'])), shape(f['geometry'])])
ZONES = ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'Z7', 'Z8']   # Z8 僅作 Z7 東側前後段（淡化）
RU = unary_union([REG[z] for z in ZONES])
WORK = RU.buffer(40)
clip_e = next(shape(f['geometry']) for f in RG if f['properties']['kind'] == 'clipped_edge')
FB = [f for f in json.load(open(H / 'data/frontage_blocks_EPSG3826.geojson'))['features'] if f['properties']['zone'] in ZONES]
_fbf = H / 'data/frontage_blocks_full_EPSG3826.geojson'
if _fbf.exists():   # 完整版單元以未截斷之整塊街廓取代
    FULLZ = {f['properties']['zone'] for f in json.load(open(_fbf))['features']}
    FB = [f for f in FB if f['properties']['zone'] not in FULLZ] + \
         [f for f in json.load(open(_fbf))['features'] if f['properties']['owner_zone'] == f['properties']['zone']]
ROAD_ALL = shape(json.load(open(H / 'data/road_surfaces_integrated_EPSG3826.geojson'))['features'][0]['geometry'])   # 已與官方人行道整合
road = ROAD_ALL.intersection(WORK)
bld = list(shape(json.load(open(BASE / 'building_outlines_TWD97.geojson'))['features'][0]['geometry']).geoms)
btree = STRtree(bld)
OUT = []
def add(g, **p):
    if g is None or g.is_empty: return
    OUT.append({'type': 'Feature', 'geometry': mapping(g), 'properties': p})

def read_shp(pat):
    out = []
    for fn in sorted(glob.glob(str(SRC / pat), recursive=True)):
        r = shapefile.Reader(fn)
        for s, rec in zip(r.shapes(), r.records()):
            g = shape(s.__geo_interface__)
            if g.is_valid is False: g = g.buffer(0)
            if g.intersects(WORK): out.append((g, rec.as_dict(), fn))
    return out

# ---------- 1. 人行道 ----------
SW = []
for f in json.load(open(REB / 'taipei-sidewalks.geojson'))['features']:
    g = shape(f['geometry'])
    if not g.intersects(WORK): continue
    p = f['properties']; g = g.buffer(0)
    kind = 'sw_setback' if p['code'] == '退縮地' else 'sw'
    g = g.difference(ROAD_ALL)          # 以整合後路緣裁切（跨巷口、漂浮於車道之片段不畫）
    if g.is_empty: continue
    SW.append((g, kind, p))
    add(g.intersection(WORK), kind=kind, road=p['NAME_Road'], side=p['SW_DIRECT'], width=p['SW_WTH_ItemValue'],
        clear_w=round(p['SWW_WTH'] or 0, 2), code=p['code'], seg=f"{p['PSTART']}—{p['PEND']}")
MS = read_shp('marked_sidewalk_*/**/*.shp')
for g, rec, fn in MS:
    add(g.intersection(WORK), kind='sw_marked', width=rec.get('rdlbwt'))
sw_all = unary_union([g for g, _, _ in SW] + [g for g, _, _ in MS])
sw_side = unary_union([g for g, _, _ in SW])               # 路側人行道（新工處，不含標線型）
face = unary_union([sw_side, road])
setback = unary_union([g for g, k, _ in SW if k == 'sw_setback'])

# ---------- 2. 行人穿越線 ----------
CW = read_shp('crosswalk_*/**/*.shp')
for g, rec, fn in CW:
    pat = 'zebra' if '斑馬紋' in fn else 'ladder'
    add(g.intersection(WORK.buffer(10)), kind='crosswalk', pattern=pat, licode=rec.get('licode'))
cw_all = unary_union([g for g, _, _ in CW])

# ---------- 3. 騎樓 ----------
SEC = []
for g, rec, fn in read_shp('arcade_*/*.shp'):
    n = rec['rname'] or ''
    if '騎樓' in n: has = True
    elif '人行道' in n: has = False
    else: has = rec['motype'] == '01'
    SEC.append((g.buffer(0), has, n))
stree = STRtree([s[0] for s in SEC])
# 建物原用途（大型公共設施少設騎樓，推估時排除）
cls_of = {}
for f in json.load(open(LU / 'data/landuse_pieces_EPSG3826.geojson'))['features']:
    pr = f['properties']; a = pr['area']
    if pr['bid'] not in cls_of or a > cls_of[pr['bid']][1]: cls_of[pr['bid']] = (pr['cls_bld'], a)
NO_ARC_CLS = {'GOV', 'EDU', 'MED', 'REC', 'REL', 'HER', 'IND', 'TRN'}
osm = json.load(open(BASE / 'source/expanded_osm.geojson'))['features']
DRIVE = {'trunk', 'primary', 'secondary', 'tertiary', 'unclassified', 'residential', 'trunk_link', 'primary_link',
         'secondary_link', 'tertiary_link', 'living_street'}
ways = []
for f in osm:
    p = f['properties']
    if f['geometry']['type'] != 'LineString' or p.get('highway') not in DRIVE: continue
    if p.get('bridge') == 'yes' or p.get('tunnel') in ('yes', 'building_passage') or (p.get('layer') or '0') != '0': continue
    g = transform(tf, shape(f['geometry']))
    if g.intersects(WORK): ways.append((g, p))
wtree = STRtree([w[0] for w in ways])
MAJOR = {'trunk', 'primary', 'secondary', 'tertiary', 'trunk_link', 'primary_link', 'secondary_link', 'tertiary_link'}
n_off = n_est = n_none = 0
for f in FB:
    blk = shape(f['geometry'])
    # 臨街邊＝地界線：街廓扣除人行道後，面向人行道或車道之邊（無人行道處即路緣）；扣除 150 m 截斷邊
    core = blk.difference(sw_side.buffer(.05))
    front = core.boundary.intersection(face.buffer(.6)).difference(clip_e.buffer(.5))
    fz = front.buffer(TOUCH)
    for i in btree.query(blk, predicate='intersects'):
        b = bld[i].intersection(core)
        if b.area < 15: continue
        touch = b.boundary.intersection(fz)
        if touch.length < 3: continue
        arc = b.intersection(front.buffer(ARC_W, cap_style='flat', join_style='mitre')).intersection(touch.buffer(ARC_W + TOUCH))
        for piece in getattr(arc, 'geoms', [arc]):
            if piece.geom_type != 'Polygon' or piece.area < 6: continue
            probe = piece.buffer(5)
            hits = [(SEC[j][0].intersection(probe).area, j) for j in stree.query(probe, predicate='intersects')]
            hits = [h for h in hits if h[0] > 2]
            if hits:
                j = max(hits)[1]
                if SEC[j][1]:
                    add(piece, kind='arcade_official', section=SEC[j][2]); n_off += 1
                else: n_none += 1
                continue
            # 推估：臨主要道路（OSM tertiary 以上或具名非巷弄道路）、非退縮人行道、非大型公共設施
            if setback.distance(piece) < 3: continue
            if cls_of.get(i, ('UNK', 0))[0] in NO_ARC_CLS or bld[i].area > 5000: continue
            near = [ways[k] for k in wtree.query(probe.buffer(20), predicate='intersects')]
            ok = any(p.get('highway') in MAJOR or (p.get('name') and not re.search('巷|弄', p['name'])) for g, p in near)
            if ok: add(piece, kind='arcade_est'); n_est += 1
print('arcade official', n_off, 'estimated', n_est, 'official sidewalk-only (not drawn)', n_none)

# ---------- 4. 車道線 ----------
carr = road.difference(sw_all.buffer(.05))
ctree_geoms = [p for p in getattr(carr, 'geoms', [carr]) if p.geom_type == 'Polygon']
ctree = STRtree(ctree_geoms)
def nlanes(p):
    def iv(k):
        try: return int(str(p.get(k, '')).split(';')[0])
        except ValueError: return None
    one = p.get('oneway') in ('yes', '1', 'true') or p.get('junction') == 'roundabout'
    n = iv('lanes')
    if n is None:
        n = {'primary': 4, 'secondary': 4, 'trunk': 4}.get(p.get('highway'), 2 if not one else 1)
    fw, bw = iv('lanes:forward'), iv('lanes:backward')
    if one: return n, n, 0
    if fw is None and bw is None: fw = (n + 1) // 2; bw = n - fw
    elif fw is None: fw = n - bw
    elif bw is None: bw = n - fw
    return n, fw, bw

def tangent(g, t):
    a = np.array(g.interpolate(max(0, t - 2)).coords[0]); b = np.array(g.interpolate(min(g.length, t + 2)).coords[0])
    d = b - a; L = np.linalg.norm(d)
    return d / L if L else None

lines_out = collections.defaultdict(list)   # (kind) -> list of point lists
for wi, (g, p) in enumerate(ways):
    n, fw, bw = nlanes(p)
    if n < 1: continue
    gg = g.intersection(WORK)
    for part in getattr(gg, 'geoms', [gg]):
        if part.geom_type != 'LineString' or part.length < 10: continue
        recs = []   # 每 3 m 一筆剖面：(pt, nrm, lo, hi, sepL, sepR) 或 None
        for t in np.arange(1, part.length - 1, STEP):
            pt = np.array(part.interpolate(t).coords[0]); d = tangent(part, t)
            if d is None: continue
            nrm = np.array([-d[1], d[0]])                       # 左側
            ray = LineString([pt - nrm * 30, pt + nrm * 30])
            P0 = Point(pt)
            seg = None
            for c in (ctree_geoms[k] for k in ctree.query(ray, predicate='intersects')):
                x_ = ray.intersection(c)
                for q in getattr(x_, 'geoms', [x_]):
                    if q.geom_type == 'LineString' and q.distance(P0) < 2.5: seg = q; break
                if seg: break
            rec = None
            if seg is not None:
                ss = sorted(float(np.dot(np.array(c) - pt, nrm)) for c in seg.coords)
                lo, hi = ss[0], ss[-1]
                # 同一車道面上平行之其他車道（雙向分離或快慢車道）：以兩中心線中點為界
                sepL = sepR = None
                for k in wtree.query(seg, predicate='intersects'):
                    if k == wi: continue
                    og, op = ways[k]
                    x = og.intersection(seg)
                    if x.is_empty or x.geom_type != 'Point': continue
                    td = tangent(og, og.project(x))
                    if td is None or abs(float(np.dot(td, d))) < .85: continue
                    sq = float(np.dot(np.array(x.coords[0]) - pt, nrm)); mid = sq / 2
                    kind_ = 'center' if np.dot(td, d) < 0 else 'lane_sep'
                    if sq > 0 and mid < hi: hi = mid; sepL = kind_
                    if sq < 0 and mid > lo: lo = mid; sepR = kind_
                if LANE_MIN <= (hi - lo) / n <= LANE_MAX: rec = (pt, nrm, lo, hi, sepL, sepR)
            recs.append(rec)
        # 短缺口（≤ 3 筆＝9 m）以前後剖面線性內插補齊；路口等長缺口維持斷開
        ok_idx = [i for i, r in enumerate(recs) if r]
        for a_, b_ in zip(ok_idx, ok_idx[1:]):
            if 1 < b_ - a_ <= 4:
                ra, rb = recs[a_], recs[b_]
                for i in range(a_ + 1, b_):
                    u = (i - a_) / (b_ - a_)
                    pt = part.interpolate(1 + i * STEP).coords[0]
                    recs[i] = (np.array(pt), ra[1] * (1 - u) + rb[1] * u, ra[2] * (1 - u) + rb[2] * u, ra[3] * (1 - u) + rb[3] * u,
                               ra[4] if ra[4] == rb[4] else None, ra[5] if ra[5] == rb[5] else None)
        tracks = collections.defaultdict(list)   # 每條線固定鍵：('lane', k)／('center', 0)／(sep 種類, 'L'|'R')
        for rec in recs:
            pos = {}
            if rec is not None:
                pt, nrm, lo, hi, sepL, sepR = rec
                w = hi - lo
                if n == fw:   # 單行
                    for k in range(1, n): pos[('lane', k)] = lo + w * k / n
                else:          # 雙向：靠右行駛，順向車道在右（-nrm 側）
                    c = lo + w * fw / n
                    for k in range(1, fw): pos[('lane', k)] = lo + w * k / n
                    pos[('center', 0)] = c
                    for k in range(1, bw): pos[('lane', 100 + k)] = c + (hi - c) * k / bw
                if sepL: pos[(sepL, 'L')] = hi
                if sepR: pos[(sepR, 'R')] = lo
            for k_ in set(tracks) | set(pos):
                tracks[k_].append(tuple(pt + nrm * pos[k_]) if k_ in pos else None)
        for (kind_, j), seq in tracks.items():
            cur = []
            for q in seq + [None]:
                if q is None:
                    if len(cur) >= 3: lines_out[kind_].append(cur)
                    cur = []
                else: cur.append(q)

def smooth(pts, k=2):
    a = np.array(pts); out = a.copy()
    for i in range(len(a)):
        out[i] = a[max(0, i - k): i + k + 1].mean(axis=0)
    out[0], out[-1] = a[0], a[-1]
    return out
# 路口：相距 < 30 m 之行穿線歸同一路口，取其凸包為路口範圍（車道線止於行穿線外）
grp = unary_union([g.buffer(15) for g, _, _ in CW if g.intersects(WORK)])
junction = unary_union([unary_union([g for g, _, _ in CW if g.intersects(comp)]).convex_hull
                        for comp in getattr(grp, 'geoms', [grp])
                        if sum(1 for g, _, _ in CW if g.intersects(comp)) >= 2])
cut = unary_union([cw_all.buffer(1.0), junction])
for kind_, L in lines_out.items():
    geoms = [LineString(smooth(s)) for s in L]
    m = unary_union(geoms).difference(cut).intersection(RU.buffer(2))
    for ln in getattr(m, 'geoms', [m]):
        if ln.geom_type == 'LineString' and ln.length >= 6:
            add(ln, kind={'lane': 'lane_line', 'center': 'center_line', 'lane_sep': 'lane_sep'}[kind_])

# ---------- 5. 行穿線紋樣：枕木紋白槓平行車流（取最近車道中心線方向），沿行走方向每 1.2 m 一條、槓寬 0.6 m（示意） ----------
for g, rec, fn in CW:
    if not g.intersects(RU.buffer(5)): continue
    c = g.centroid
    # 槓方向＝車流方向：行穿線外框明顯狹長（長寬比 ≥ 1.4）時取短邊方向；近方形者取最近車道中心線方向
    r = np.asarray(g.minimum_rotated_rectangle.exterior.coords)
    e1, e2 = r[1] - r[0], r[2] - r[1]
    es, el = sorted((e1, e2), key=np.linalg.norm)
    d = None
    if np.linalg.norm(el) >= 1.4 * np.linalg.norm(es): d = es / np.linalg.norm(es)
    else:
        near = sorted(((ways[k][0].distance(c), k) for k in wtree.query(c.buffer(25))), key=lambda x: x[0])
        if near: og = ways[near[0][1]][0]; d = tangent(og, og.project(c))
        if d is None: d = es / np.linalg.norm(es)
    nrm = np.array([-d[1], d[0]]); cc = np.array(c.coords[0]); R_ = 40
    zebra = '斑馬紋' in fn
    for s_ in np.arange(-R_, R_, 1.2):
        if zebra:   # 斑馬紋：斜紋
            v = (d + nrm) / np.sqrt(2); w_ = np.array([-v[1], v[0]])
            ln = LineString([cc + w_ * s_ - v * R_, cc + w_ * s_ + v * R_])
        else:
            ln = LineString([cc + nrm * s_ - d * R_, cc + nrm * s_ + d * R_])
        x_ = ln.intersection(g)
        for q in getattr(x_, 'geoms', [x_]):
            if q.geom_type == 'LineString' and q.length > .3: add(q, kind='crosswalk_bar', bar_w=0.6 if not zebra else 0.35)

# ---------- 6. 街道家具：樹穴／花圃、通風井、捷運出入口 ----------
for f in json.load(open(SRC / 'TP_TREE_樹穴.json'))['features']:
    pr = f['properties']
    if not WORK.contains(Point(pr['X_3826'], pr['Y_3826'])): continue
    add(shape(f['geometry']).buffer(0), kind='tree_pit' if pr.get('Name') == '樹穴' else 'planter')
for f in osm:
    if f['properties'].get('man_made') == 'ventilation_shaft' and f['geometry']['type'] != 'Point':
        g = transform(tf, shape(f['geometry'])).buffer(0)
        if g.intersects(WORK): add(g, kind='vent')
_pts = H / 'data/osm_street_points_4326.geojson'
if _pts.exists():
    for f in json.load(open(_pts))['features']:
        if f['properties']['kind'] != 'mrt_entrance': continue
        g = transform(tf, shape(f['geometry']))
        if WORK.contains(g): add(g, kind='mrt_entrance', ref=f['properties'].get('ref') or '', name=f['properties'].get('name') or '')

json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': OUT},
          open(H / 'data/street_detail_EPSG3826.geojson', 'w'), ensure_ascii=False)
c = collections.Counter(f['properties']['kind'] for f in OUT)
print(dict(c))
