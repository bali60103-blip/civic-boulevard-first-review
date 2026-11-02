# 出圖：A1 橫式一頁 —— Z1–Z7 市民大道兩側第一排街廓詳細平面（統一 1:2500，各單元依大道走向轉正）
# 另輸出各單元單張 PNG（Z1…Z7）
import json, collections, re
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib import font_manager
from matplotlib.path import Path as MPath
from matplotlib.patches import Patch, PathPatch
from matplotlib.collections import PathCollection, LineCollection
from matplotlib.lines import Line2D
from shapely.geometry import shape, Point, LineString, box, Polygon
from shapely.ops import unary_union, transform
from shapely.strtree import STRtree
from shapely import affinity
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
ROOT = H.parents[1]
BASE = ROOT / '03_最新產出/02_南京至仁愛擴幅_20261005'
LU = ROOT / '03_最新產出/03_南京至仁愛_沿線土地使用分析_20261006'
FONT = '/System/Library/Fonts/Hiragino Sans GB.ttc'
# Hiragino 為 CFF 外框字型：pdf.fonttype=42 嵌入後僅 Apple 預覽程式顯示正常，Acrobat／MuPDF 會亂碼 → 改 Type 3。
# TTC 只會註冊第一個字面（W3），另抽出 W6 供粗體使用（暫存，不入專案）。
import tempfile
from fontTools.ttLib import TTCollection
_w6 = Path(tempfile.gettempdir()) / 'HiraginoSansGB-W6_extract.ttf'
if not _w6.exists():
    TTCollection(FONT).fonts[2].save(_w6)
font_manager.fontManager.addfont(FONT); font_manager.fontManager.addfont(str(_w6))
plt.rcParams['font.family'] = font_manager.FontProperties(fname=FONT).get_name()
plt.rcParams['pdf.fonttype'] = 3
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform

ZONES_USE = ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'Z7', 'Z8']   # 分頁圖、DXF（Z8 於 2026-10-08 加入）
OV_ZONES = ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'Z7']          # 一頁總圖（第三張 A1）維持 Z1–Z7
ROWS = [['Z1', 'Z2', 'Z3'], ['Z4', 'Z5', 'Z6'], ['Z7']]
SCALE = 2500
MM = 1 / 25.4
W, Hh = 841, 594
m2mm = 1000 / SCALE
ZONE_C = '#1A9BD7'
# 圖面風格比照「中山—台北車站段 平面配置圖」範例：黑白線稿，建物淺灰點網＋黑框，道路與人行道留白、以路緣及人行道邊線表現
BLD_FC, BLD_DOT, BLD_EC = '#EBEBEB', '#7a7a7a', '#141414'
CUT_PRE = ('承德路', '中山北路', '中山南路', '林森北路', '林森南路', '金山北路', '金山南路', '建國', '安東街', '光復南路', '光復北路')
GROUND_FC = 'white'
GREEN_FC, GREEN_DOT = '#E3EFD8', '#7FA86A'
ROAD_EC = '#141414'
DECK_EC = '#808080'
halo = [pe.withStroke(linewidth=1.6, foreground='white')]

# ---------- 資料 ----------
road = shape(json.load(open(H / 'data/road_surfaces_integrated_EPSG3826.geojson'))['features'][0]['geometry'])   # 已與官方人行道整合（00_integrate_sidewalk.py）
bld = shape(json.load(open(BASE / 'building_outlines_TWD97.geojson'))['features'][0]['geometry'])
edges = shape(json.load(open(BASE / 'building_display_edges.geojson'))['features'][0]['geometry'])
civ = json.load(open(LU / 'data/civic_elevated_EPSG3826.json'))
elev, ramps = shape(civ['elevated']), shape(civ['ramps'])
deck = unary_union([shape(f['geometry']) for f in json.load(open(LU / 'data/underbridge_EPSG3826.geojson'))['features']])
green = unary_union([shape(f['geometry']) for f in json.load(open(LU / 'data/green_EPSG3826.geojson'))['features']])
ZF = json.load(open(LU / 'data/zones_EPSG3826.geojson'))['features']
ZP = {f['properties']['id']: f['properties'] for f in ZF if 'id' in f['properties']}
FB = json.load(open(H / 'data/frontage_blocks_EPSG3826.geojson'))['features']
RG = json.load(open(H / 'data/frontage_region_EPSG3826.geojson'))['features']
REG = {f['properties']['zone']: shape(f['geometry']) for f in RG if f['properties']['kind'] == 'region'}
# 完整版範圍（01 FULL_ZONES：不截斷、跨界街廓整塊）——七張分頁圖與 DXF 用；一頁總圖維持截斷版
REG_FULL = {f['properties']['zone']: shape(f['geometry']) for f in RG if f['properties']['kind'] == 'region_full'}
_fbf = H / 'data/frontage_blocks_full_EPSG3826.geojson'
FB_FULL = json.load(open(_fbf))['features'] if _fbf.exists() else []
center = next(shape(f['geometry']) for f in RG if f['properties']['kind'] == 'centerline')
clip_e = next(shape(f['geometry']) for f in RG if f['properties']['kind'] == 'clipped_edge')
D_MAX = next(f['properties']['d_max'] for f in RG if f['properties']['kind'] == 'clipped_edge')
pieces = json.load(open(LU / 'data/landuse_pieces_EPSG3826.geojson'))['features']
osm = json.load(open(BASE / 'source/expanded_osm.geojson'))['features']
ROAD_KINDS = {'trunk', 'primary', 'secondary', 'tertiary', 'unclassified', 'residential', 'primary_link', 'secondary_link'}
streets = collections.defaultdict(list); civic_named = []
for f in osm:
    p = f['properties']; n = p.get('name', '')
    if f['geometry']['type'] != 'LineString' or p.get('highway') not in ROAD_KINDS or not n: continue
    if any(k in n for k in ('巷', '弄', '匝道', '地下道', '高架')) or p.get('bridge') == 'yes' or p.get('tunnel') == 'yes': continue
    g = transform(tf, shape(f['geometry']))
    if n.startswith('市民大道'): civic_named.append((g, n))
    else: streets[n].append(g)
streets = {n: unary_union(v) for n, v in streets.items()}
lanes_named = collections.defaultdict(list)   # 巷弄名（範例圖標註華陰街24巷6弄等）
for f in osm:
    p = f['properties']; n = p.get('name', '')
    if f['geometry']['type'] == 'LineString' and p.get('highway') and re.search('巷|弄', n) and not n.startswith('市民大道'):
        lanes_named[n].append(transform(tf, shape(f['geometry'])))
lanes_named = {n: unary_union(v) for n, v in lanes_named.items()}
civic_tree = STRtree([g for g, _ in civic_named])
btree = STRtree(list(bld.geoms)); bgeoms = list(bld.geoms)

def poly_path(g):
    vs, cs = [], []
    for p in getattr(g, 'geoms', [g]):
        if p.geom_type != 'Polygon' or p.is_empty: continue
        for r in [p.exterior, *p.interiors]:
            a = np.asarray(r.coords)
            vs.append(a); cs.append([MPath.MOVETO] + [MPath.LINETO] * (len(a) - 2) + [MPath.CLOSEPOLY])
    return MPath(np.concatenate(vs), np.concatenate(cs)) if vs else None

def lines(g):
    out = []
    for p in getattr(g, 'geoms', [g]):
        if p.is_empty: continue
        if p.geom_type == 'Polygon': out += [np.asarray(r.coords) for r in [p.exterior, *p.interiors]]
        elif p.geom_type in ('LineString', 'LinearRing'): out.append(np.asarray(p.coords))
        elif hasattr(p, 'geoms'): out += lines(p)
    return out

def polys(g):
    return [p for p in getattr(g, 'geoms', [g]) if p.geom_type == 'Polygon' and not p.is_empty]

# 行穿線（大道段名避開用）
_sdf = H / 'data/street_detail_EPSG3826.geojson'
CW_U = unary_union([shape(f['geometry']) for f in json.load(open(_sdf))['features'] if f['properties']['kind'] == 'crosswalk']) \
    if _sdf.exists() else Point(0, 0).buffer(0)

# ---------- 各單元：轉正與內容 ----------
def short(n): return n.replace('高架', '').split('（')[0]
def build_zone(z, R, full=False):
    cz = center.intersection(R.buffer(1))
    cs = sorted((c for g in getattr(cz, 'geoms', [cz]) for c in g.coords), key=lambda c: c[0])
    a, b = np.array(cs[0]), np.array(cs[-1])
    ang = np.degrees(np.arctan2(b[1] - a[1], b[0] - a[0]))
    o = R.centroid
    T = (lambda ang_, ox, oy: (lambda g: affinity.translate(affinity.rotate(g, -ang_, origin=(ox, oy)), -ox, -oy)))(ang, o.x, o.y)
    TR = T(R)
    cl = T(cz)
    yc = float(np.mean([c[1] for g in getattr(cl, 'geoms', [cl]) for c in g.coords]))
    x0, y0, x1, y1 = TR.bounds
    src_ = FB_FULL if full else FB
    blocks = [shape(f['geometry']) for f in src_ if f['properties']['zone'] == z]
    nside = collections.Counter(f['properties']['side'] for f in src_ if f['properties']['zone'] == z)
    bunion = unary_union(blocks)
    bl = [bgeoms[i].intersection(R) for i in btree.query(R, predicate='intersects')]
    bl = [g for g in bl if g.area > 1]
    # 地標：線稿建物對應之 OSM 名稱（面積大者）
    cnt = collections.Counter(); where = {}
    for f in pieces:
        n = f['properties']['name']
        if not n or any(k in n for k in ('換氣口', '出口', '停車場')): continue
        g = shape(f['geometry'])
        if not g.intersects(R): continue
        gi = g.intersection(R)
        cnt[n] += gi.area
        if n not in where or gi.area > where[n][1]: where[n] = (gi.representative_point(), gi.area)
    marks = [(n, where[n][0]) for n, ar in cnt.most_common(7) if ar >= 700]
    # 橫街：具名道路中心線裁至平面範圍並扣除大道中央 ±18 m，南北兩側各取最長一段（長 ≥ 20 m）標在街上
    # 單元兩端之界線道路（承德、中山北…）改標在圖與圖之間的空隙
    clc = sorted((c for g in getattr(cl, 'geoms', [cl]) for c in g.coords), key=lambda c: c[0])
    cx_, cy_ = np.array([c[0] for c in clc]), np.array([c[1] for c in clc])
    lab2 = []
    for n, g in streets.items():
        if n.startswith(CUT_PRE) or any(k in n for k in ('入口', '停車場', '快速道路')) or not g.intersects(R): continue
        gi = g.intersection(R).difference(center.buffer(18))
        best = {}
        for sg in getattr(gi, 'geoms', [gi]):
            if sg.geom_type != 'LineString' or sg.length < 20: continue
            m = T(sg.interpolate(.5, normalized=True))
            dy = m.y - np.interp(m.x, cx_, cy_)
            if abs(dy) < 15 or bunion.buffer(-1.5).contains(sg.interpolate(.5, normalized=True)): continue
            k = dy > 0
            if k not in best or sg.length > best[k].length: best[k] = sg
        for sg in best.values():
            a_, b_ = T(sg).coords[0], T(sg).coords[-1]
            rot = np.degrees(np.arctan2(b_[1] - a_[1], b_[0] - a_[0]))
            rot = (rot + 90) % 180 - 90
            lab2.append((n, sg.interpolate(.5, normalized=True), rot))
    # 範圍外緣道路（第一排街廓背側，如北平西路、鄭州路、華陰街）：沿範圍外 14 m 內、長 ≥ 40 m 者標於範圍外側
    have = {n for n, _, _ in lab2}
    for n, g in streets.items():
        if n in have or n.startswith(CUT_PRE) or any(k in n for k in ('入口', '停車場', '快速道路')): continue
        gi = g.intersection(R.buffer(14)).difference(R.buffer(1))
        segs_ = [sg for sg in getattr(gi, 'geoms', [gi]) if sg.geom_type == 'LineString' and sg.length >= 40]
        if not segs_: continue
        sg = max(segs_, key=lambda x: x.length)
        a_, b_ = T(sg).coords[0], T(sg).coords[-1]
        rot = (np.degrees(np.arctan2(b_[1] - a_[1], b_[0] - a_[0])) + 90) % 180 - 90
        lab2.append((n, sg.interpolate(.5, normalized=True), rot))
    lab_lane = []
    for n, g in lanes_named.items():
        if not g.intersects(R): continue
        gi = g.intersection(R).difference(center.buffer(18))
        segs_ = [sg for sg in getattr(gi, 'geoms', [gi]) if sg.geom_type == 'LineString' and sg.length >= 25]
        if not segs_: continue
        sg = max(segs_, key=lambda x: x.length)
        a_, b_ = T(sg).coords[0], T(sg).coords[-1]
        rot = (np.degrees(np.arctan2(b_[1] - a_[1], b_[0] - a_[0])) + 90) % 180 - 90
        lab_lane.append((n, sg.interpolate(.5, normalized=True), rot))
    # 大道段名
    civ_lab = []
    L0 = center.project(Point(cs[0])); L1 = center.project(Point(cs[-1]))
    for t in np.arange(L0 + 140, L1 - 100, 420):
        # 段名（字距加寬約 60 m 長）移到離行穿線 ≥ 35 m 處
        t = min((t + dt for dt in range(0, 160, 5) for dt in (dt, -dt) if L0 + 40 < t + dt < L1 - 40
                 and center.interpolate(t + dt).distance(CW_U) >= 35), key=lambda v: abs(v - t), default=t)
        q = center.interpolate(t)
        i = civic_tree.query_nearest(q, max_distance=100)
        if len(i): civ_lab.append((civic_named[int(i[0])][1], q))
    if not civ_lab:  # OSM 平面道路未標名之段（Z1 西段）取最近之市民大道段名
        q = center.interpolate((L0 + L1) / 2); i = civic_tree.query_nearest(q)
        if len(i): civ_lab.append((civic_named[int(i[0])][1], q))
    return dict(R=R, T=T, ang=ang, TR=TR, yc=yc, x0=x0, x1=x1, y0=y0, y1=y1, blocks=blocks, bl=bl, nside=nside,
                marks=marks, streets=lab2, lanes=lab_lane, civ=civ_lab, cz=cz, full=full)

P = {z: build_zone(z, REG[z]) for z in ZONES_USE}
P_FULL = {z: build_zone(z, REG_FULL[z], full=True) for z in ZONES_USE if z in REG_FULL}
P_CTX = {z: build_zone(z, REG[z]) for z in REG if z not in ZONES_USE}   # 分頁圖以外之單元（目前無）：僅作前後段淡化底圖
VARIANT = {'full': False}   # 05（七張）與 03（DXF）設為 True
def zone_in_frame(z2, T):
    # 前後段：取 z2 之內容，改用本張轉正 T（文字不標）
    d2 = dict(P_CTX[z2] if z2 in P_CTX else PZ(z2)); d2['T'] = T
    return d2
def PZ(z):
    return P_FULL[z] if VARIANT['full'] and z in P_FULL else P[z]

def _pc(ax, geoms, T, fc, ec, z_, lw_, hatch=None, hc=None, ls='-'):
    paths = [poly_path(T(g)) for g in geoms if not g.is_empty]
    paths = [q for q in paths if q is not None]
    if not paths: return
    if hatch: plt.rcParams['hatch.color'] = hc or ec
    ax.add_collection(PathCollection(paths, facecolors=fc, edgecolors=ec, linewidths=lw_, hatch=hatch, linestyles=ls, zorder=z_))

def draw_zone(ax, z, lw=1.0, fs=1.0, scale=None, detail=True, sw_labels=False, texts=True):
    # z：單元代號或 zone dict（前後段淡化底圖時傳入已換成本張轉正之 dict）；texts=False 不標文字
    d = z if isinstance(z, dict) else PZ(z); T, R = d['T'], d['R']
    sc = scale or SCALE
    plt.rcParams['hatch.linewidth'] = .45
    gz = green.intersection(R)
    _pc(ax, polys(gz), T, GREEN_FC, 'none', 1.2, 0, hatch='...', hc=GREEN_DOT)
    if detail: draw_detail(ax, d, sc, lw, sw_labels and texts, texts=texts)
    # 道路邊線（路緣，含大道中央分隔島、橫街口）
    ax.add_collection(LineCollection(lines(T(road.boundary.intersection(R))), colors=ROAD_EC, linewidths=.35 * lw, zorder=3))
    # 建物：淺灰點網＋黑框
    plt.rcParams['hatch.linewidth'] = .5
    _pc(ax, d['bl'], T, BLD_FC, 'none', 2, 0, hatch='....', hc=BLD_DOT)
    ax.add_collection(LineCollection(lines(T(edges.intersection(R))), colors=BLD_EC, linewidths=.35 * lw, zorder=4))
    # 第一排街廓外框（地界）
    clip_buf = clip_e.buffer(.3) if not d.get('full') else Point(0, 0).buffer(0)   # 完整版無截斷邊
    ax.add_collection(LineCollection([l for b0 in d['blocks'] for b in polys(b0) for l in lines(T(b.exterior.difference(clip_buf)))],
                                     colors=INK, linewidths=.5 * lw, zorder=4.5))
    ce = clip_e.intersection(R.buffer(.5))
    if not ce.is_empty and not d.get('full'):
        ax.add_collection(LineCollection(lines(T(ce)), colors=INK, linewidths=.45 * lw, linestyles=(0, (8, 2, 1.5, 2)), zorder=4.6))
    # 市民高架橋面投影（上方構造，灰虛線）
    dk = deck.intersection(R)
    if not dk.is_empty:
        ax.add_collection(LineCollection(lines(T(dk.boundary.difference(R.boundary.buffer(.3)))), colors=DECK_EC, linewidths=.55 * lw,
                                         linestyles=(0, (4, 2)), zorder=5.2))
    ax.add_collection(LineCollection(lines(T(ramps.intersection(R))), colors=DECK_EC, linewidths=.5 * lw, linestyles=(0, (2, 1.5)), zorder=5.2))
    # 文字：路名粗體黑字（範例），大道名字距加寬
    if not texts:
        ax.set_xlim(d['x0'], d['x1']); ax.axis('off'); return
    for n, q in d['civ']:
        p = T(q)
        ax.text(p.x, p.y, '　'.join(n), fontsize=7.8 * fs, ha='center', va='center', color=INK, zorder=9, path_effects=halo,
                fontweight='bold', clip_on=True)
    for n, q, rot in d['streets']:
        p = T(q)
        ax.text(p.x, p.y, n, fontsize=5.8 * fs, ha='center', va='center', rotation=rot, rotation_mode='anchor', color=INK,
                fontweight='bold', zorder=9, path_effects=halo, clip_on=True)
    for n, q, rot in d.get('lanes', []):
        p = T(q)
        ax.text(p.x, p.y, n, fontsize=4.4 * fs, ha='center', va='center', rotation=rot, rotation_mode='anchor', color=INK,
                fontweight='bold', zorder=8.9, path_effects=halo, clip_on=True)
    for n, q in d['marks']:
        p = T(q)
        ax.text(p.x, p.y, n, fontsize=4.6 * fs, ha='center', va='center', color='#222', zorder=9.5, path_effects=halo, clip_on=True)
    ax.set_xlim(d['x0'], d['x1']); ax.axis('off')

# ---------- 街道細部（04_street_detail.py）：人行道、騎樓、車道線、行人穿越線、樹穴、通風井、捷運出入口 ----------
INK = '#141414'
SW_EC = '#3c3c3c'
SB_HC = '#9a9a9a'
ARC_O_HC, ARC_E_HC = '#3c3c3c', '#8c8c8c'
LANE_C, CEN_C, CW_C = '#3c3c3c', INK, INK
SDK = collections.defaultdict(list)
_sd = H / 'data/street_detail_EPSG3826.geojson'
if _sd.exists():
    for f in json.load(open(_sd))['features']: SDK[f['properties']['kind']].append((shape(f['geometry']), f['properties']))
# 照片判讀補繪（09_photo_features.py）
PFK = collections.defaultdict(list)
_pf = H / 'data/photo_features_EPSG3826.geojson'
if _pf.exists():
    for f in json.load(open(_pf))['features']: PFK[f['properties']['kind']].append((shape(f['geometry']), f['properties']))
PT = 72 / 25.4
TXT = {'f': 1.0}   # 圖內固定字級／符號倍率（A3 版由 05 設定）
def lane_dash(scale): return (0, (4 * 1000 / scale * PT, 6 * 1000 / scale * PT))   # 車道線 4 m 線、6 m 間（紙面 pt）

def draw_detail(ax, z, scale, lw=1.0, sw_labels=False, texts=True):
    d = z if isinstance(z, dict) else PZ(z); T, R = d['T'], d['R']
    get = lambda kind: [g.intersection(R) for g, _ in SDK[kind] if g.intersects(R)]
    plt.rcParams['hatch.linewidth'] = .35
    # 人行道：留白，邊線細實線；退縮地加灰斜線；標線型人行道虛線框
    _pc(ax, get('sw'), T, 'white', SW_EC, 1.6, .25 * lw)
    _pc(ax, get('sw_setback'), T, 'white', SW_EC, 1.6, .25 * lw, hatch='////', hc=SB_HC)
    _pc(ax, get('sw_marked'), T, 'white', SW_EC, 1.65, .3 * lw, ls=(0, (2, 1.5)))
    # 騎樓：建物內臨街 3.64 m 帶，去點網改斜線；官方實框深線，推估虛框淺線
    _pc(ax, get('arcade_official'), T, 'white', SW_EC, 2.6, .3 * lw, hatch='////', hc=ARC_O_HC)
    _pc(ax, get('arcade_est'), T, 'white', '#777', 2.6, .3 * lw, hatch='\\\\\\\\', hc=ARC_E_HC, ls=(0, (2, 1.5)))
    def lc(kind, color, lw_, ls='-', z_=3.3):
        L = [l for g in get(kind) for l in lines(T(g))]
        if L: ax.add_collection(LineCollection(L, colors=color, linewidths=lw_ * lw, linestyles=ls, zorder=z_, capstyle='butt'))
    lc('lane_line', LANE_C, .35, lane_dash(scale))
    lc('lane_sep', LANE_C, .35)
    lc('center_line', CEN_C, .6)
    for bw in (0.6, 0.35):   # 行人穿越線白槓：黑槓，線寬＝槓寬換算紙面
        L = [l for g, q in SDK['crosswalk_bar'] if q['bar_w'] == bw and g.intersects(R) for l in lines(T(g.intersection(R)))]
        if L: ax.add_collection(LineCollection(L, colors=CW_C, linewidths=bw * 1000 / scale * PT, zorder=3.4, capstyle='butt'))
    # 樹穴（小方塊＋樹點）、花圃（點網）
    pits = get('tree_pit')
    _pc(ax, pits, T, 'white', INK, 3.5, .3 * lw)
    if pits:
        c = np.array([T(g.centroid).coords[0] for g in pits])
        ax.scatter(c[:, 0], c[:, 1], s=(0.5 * 1000 / scale * PT) ** 2, c=INK, linewidths=0, zorder=3.55)
    plt.rcParams['hatch.linewidth'] = .45
    _pc(ax, get('planter'), T, GREEN_FC, INK, 3.5, .3 * lw, hatch='...', hc=GREEN_DOT)
    draw_photo(ax, d, scale, lw, texts=texts)
    # 通風井：方框打叉（範例）
    for g in get('vent'):
        for pg in polys(g):
            r = np.asarray(T(pg).minimum_rotated_rectangle.exterior.coords)
            ax.add_collection(LineCollection([r, r[[0, 2]], r[[1, 3]]], colors=INK, linewidths=.35 * lw, zorder=3.6))
    # 捷運出入口
    for g, q in SDK['mrt_entrance']:
        if not R.contains(g): continue
        p = T(g)
        ax.plot([p.x], [p.y], marker='s', ms=3.2 * TXT['f'], mfc=INK, mec='white', mew=.4, zorder=9.3)
        if q.get('ref') and texts:
            ax.text(p.x, p.y + 1.6 * scale / 1000, q['ref'], fontsize=4.2 * TXT['f'], ha='center', va='bottom', color=INK, zorder=9.3,
                    path_effects=halo, clip_on=True)
    if not sw_labels: return
    seen = []   # 市民大道人行道寬（官方 SW_WTH），沿人行道長向標註
    for g, q in SDK['sw']:
        if not (q['road'] or '').startswith('市民大道') or not g.intersects(R) or g.area < 80: continue
        gi = g.intersection(R)
        if gi.area < 60: continue
        c = gi.representative_point()
        if any(c.distance(s_) < 120 and abs(v_ - q['width']) < .3 for s_, v_ in seen): continue
        seen.append((c, q['width']))
        r = np.asarray(T(gi).minimum_rotated_rectangle.exterior.coords)
        e = max((r[1] - r[0], r[2] - r[1]), key=np.linalg.norm); rot = (np.degrees(np.arctan2(e[1], e[0])) + 90) % 180 - 90
        tq = T(c)
        ax.text(tq.x, tq.y, f"人行道 {q['width']:.1f} m", fontsize=4.5 * TXT['f'], color='#444', ha='center', va='center', rotation=rot,
                rotation_mode='anchor', zorder=9.2, path_effects=halo, clip_on=True)

def _orient_rect(c, d, L, Wd):
    n = np.array([-d[1], d[0]]); c = np.asarray(c)
    return Polygon([c + d * L / 2 + n * Wd / 2, c - d * L / 2 + n * Wd / 2, c - d * L / 2 - n * Wd / 2, c + d * L / 2 - n * Wd / 2])
_road_b = road.boundary
def _curb_dir(pt):
    # 最近路緣切線方向（候車亭、站牌沿路緣擺放）
    t = _road_b.project(pt); a = np.array(_road_b.interpolate(max(0, t - 3)).coords[0]); b = np.array(_road_b.interpolate(t + 3).coords[0])
    v = b - a; L = np.linalg.norm(v)
    return v / L if L else np.array([1.0, 0.0])

def draw_photo(ax, z, scale, lw=1.0, texts=True):
    d = z if isinstance(z, dict) else PZ(z); T, R = d['T'], d['R']
    get = lambda kind: [(g.intersection(R), q) for g, q in PFK[kind] if g.intersects(R)]
    # 分隔島植栽（照片判讀）：與花圃同表現
    plt.rcParams['hatch.linewidth'] = .45
    _pc(ax, [g for g, _ in get('median_planting')], T, GREEN_FC, 'none', 1.25, 0, hatch='...', hc=GREEN_DOT)
    # 機車停車列：灰底直線
    _pc(ax, [g for g, _ in get('moto_row')], T, '#e6e6e6', '#555', 2.7, .25 * lw, hatch='||||', hc='#777')
    # 橋墩：黑實心（Z1 無照片：灰）；門形墩帽梁：細框
    for unv, fc in ((False, INK), (True, '#9a9a9a')):
        g_ = [g for g, q in get('pier') if bool(q.get('unverified')) == unv]
        _pc(ax, g_, T, fc, fc, 5.6, .2 * lw)
    _pc(ax, [g for g, _ in get('pier_cap')], T, 'none', '#444', 5.5, .35 * lw, ls=(0, (3, 1.5)))
    # 地下化引道遺構（廢棄鐵道）：細線＋枕木
    L = [l for g, _ in get('osm_rail_disused') for l in lines(T(g))]
    if L:
        ax.add_collection(LineCollection(L, colors=INK, linewidths=.4 * lw, zorder=3.7))
        ax.add_collection(LineCollection(L, colors=INK, linewidths=2.4 * lw, linestyles=(0, (.4, 2.2)), zorder=3.7, capstyle='butt'))
    # 地面樓梯（OSM）：踏階線
    L = [l for g, _ in get('osm_steps') for l in lines(T(g))]
    if L: ax.add_collection(LineCollection(L, colors=INK, linewidths=2.0 * lw, linestyles=(0, (.25, .6)), zorder=3.7, capstyle='butt'))
    # 候車亭：沿路緣 4 × 1.6 m 框
    for g, _ in get('osm_shelter'):
        c = g.centroid; dd = _curb_dir(c)
        r = T(_orient_rect(c.coords[0], dd, 4.0, 1.6))
        ax.add_patch(PathPatch(poly_path(r), facecolor='white', edgecolor=INK, lw=.45 * lw, hatch='xxxx', zorder=5.8))
    # 點符號：YouBike、公共藝術、停車場出入口
    for kind, mk, ms_, fc in (('osm_bike_rental', 'h', 4.2, 'white'), ('osm_artwork', '*', 6.0, INK), ('osm_parking_entrance', 'v', 3.8, 'white')):
        pts = [T(g.centroid if g.geom_type != 'Point' else g) for g, _ in get(kind)]
        if pts:
            ax.plot([q.x for q in pts], [q.y for q in pts], ls='none', marker=mk, ms=ms_ * TXT['f'], mfc=fc, mec=INK, mew=.5, zorder=9.1)
    for g, q in get('osm_artwork'):
        if q.get('name') and texts:
            p_ = T(g.centroid); ax.text(p_.x, p_.y - 3.5 * scale / 1000, q['name'], fontsize=3.8 * TXT['f'], ha='center', va='top', color=INK,
                                         zorder=9.1, path_effects=halo, clip_on=True)

def photo_handles():
    plt.rcParams['hatch.linewidth'] = .45
    return [Patch(facecolor=INK, edgecolor=INK, label='橋墩（照片判讀柱型，柱位推估）'),
            Patch(facecolor='#9a9a9a', edgecolor='#9a9a9a', label='橋墩（Z1、Z8 無照片，未核）'),
            Patch(facecolor='none', edgecolor='#444', lw=.6, ls=(0, (3, 1.5)), label='門形墩帽梁（照片判讀）'),
            Patch(facecolor=GREEN_FC, edgecolor='none', hatch='...', label='分隔島植栽（照片判讀）'),
            Patch(facecolor='#e6e6e6', edgecolor='#555', hatch='||||', lw=.4, label='機車停車列（照片定位）'),
            Patch(facecolor='white', edgecolor=INK, hatch='xxxx', lw=.5, label='候車亭（OSM＋照片）'),
            Line2D([], [], ls='none', marker='h', ms=5, mfc='white', mec=INK, label='YouBike（OSM＋照片）'),
            Line2D([], [], ls='none', marker='*', ms=7, mfc=INK, mec=INK, label='公共藝術（OSM＋照片）'),
            Line2D([], [], ls='none', marker='v', ms=5, mfc='white', mec=INK, label='停車場出入口（OSM）'),
            Line2D([], [], color=INK, lw=2.4, ls=(0, (.4, 2.2)), label='舊鐵道引道（OSM＋照片）'),
            Line2D([], [], color=INK, lw=2.0, ls=(0, (.25, .6)), label='地面樓梯（OSM）')]

def detail_handles(scale):
    plt.rcParams['hatch.linewidth'] = .45
    return [Patch(facecolor='white', edgecolor=SW_EC, lw=.4, label='人行道（市府人行道範圍）'),
            Patch(facecolor='white', edgecolor=SB_HC, lw=.4, hatch='////', label='無遮簷人行道（退縮地）'),
            Patch(facecolor='white', edgecolor=SW_EC, lw=.5, ls=(0, (2, 1.5)), label='標線型人行道（交工處）'),
            Patch(facecolor='white', edgecolor=ARC_O_HC, lw=.5, hatch='////', label='騎樓（官方路段）'),
            Patch(facecolor='white', edgecolor=ARC_E_HC, lw=.5, ls=(0, (2, 1.5)), hatch='\\\\\\\\', label='騎樓（推估，3.64 m）'),
            Line2D([], [], color=LANE_C, lw=.5, ls=lane_dash(scale), label='車道線（推估）'),
            Line2D([], [], color=CEN_C, lw=.8, label='雙向分隔中心線（推估）'),
            Line2D([], [], color=LANE_C, lw=.5, label='快慢／同向車道分隔（推估）'),
            Line2D([], [], color=CW_C, lw=2.2, ls=(0, (1, 1)), label='行人穿越線（交工處位置，紋樣示意）'),
            Line2D([], [], color=INK, lw=0, marker='s', ms=4, mfc='white', mec=INK, mew=.5, label='樹穴（新工處）'),
            Patch(facecolor=GREEN_FC, edgecolor=INK, lw=.4, hatch='...', label='花圃（新工處）'),
            Line2D([], [], color=INK, lw=0, marker='s', ms=3.5, mfc=INK, mec='white', label='捷運出入口（OSM）')]

def north(fig, x_mm, y_mm, ang, size=7, f=1.0):
    # 北向：轉正後真北＝(0,1) 旋轉 -ang；f＝字級／符號倍率
    t = np.radians(-ang); v = np.array([-np.sin(t), np.cos(t)])
    c = np.array([x_mm, y_mm])
    a, b = c - v * size / 2, c + v * size / 2
    fig.add_artist(matplotlib.patches.FancyArrowPatch(a / [W, Hh], b / [W, Hh], transform=fig.transFigure, arrowstyle='-|>',
                                                      mutation_scale=7 * f, color='#111', lw=.8 * f))
    fig.text((b[0] + v[0] * 2.6 * f) / W, (b[1] + v[1] * 2.6 * f) / Hh, 'N', fontsize=6.5 * f, ha='center', va='center')

def scalebar(fig, x_mm, y_mm, lens=(0, 25, 50, 100, 200), fs=6.5):
    for i in range(len(lens) - 1):
        a, b = lens[i] * m2mm, lens[i + 1] * m2mm
        fig.add_artist(plt.Rectangle(((x_mm + a) / W, y_mm / Hh), (b - a) / W, 1.6 / Hh, transform=fig.transFigure,
                                     facecolor='#111' if i % 2 == 0 else 'white', edgecolor='#111', lw=.5))
    for L in lens:
        fig.text((x_mm + L * m2mm) / W, (y_mm + 2.6) / Hh, f'{L}', fontsize=fs, ha='center', va='bottom')
    fig.text((x_mm + lens[-1] * m2mm + 3) / W, y_mm / Hh, f'm　1:{SCALE:,}（A1）', fontsize=fs, va='bottom')

def header(fig, title, sub, k=1.0, f=1.0):
    # k＝版面尺寸倍率（A3＝0.5），f＝字級倍率
    fig.text(28 * k / W, 1 - 34 * k / Hh, title, fontsize=20 * f, va='top')
    fig.text(28 * k / W, 1 - 46 * k / Hh, sub, fontsize=9 * f, va='top', color='#444')
    fig.add_artist(plt.Rectangle((10 * k / W, 10 * k / Hh), (W - 20 * k) / W, (Hh - 20 * k) / Hh, transform=fig.transFigure, fill=False,
                                 lw=.8 * f))

def zone_title(fig, z, x_mm, y_mm, w_mm, ang):
    zp = ZP[z]; d = P[z]
    fig.text(x_mm / W, y_mm / Hh, z, fontsize=15, fontweight='bold', color=ZONE_C, va='baseline')
    fig.text((x_mm + 12) / W, y_mm / Hh, f"{zp['from']}—{zp['to']}", fontsize=9.5, fontweight='bold', va='baseline')
    fig.text((x_mm + 12) / W, (y_mm - 4.2) / Hh,
             f"{zp['info']}｜軸線 {zp['len_m']:,} m｜第一排街廓：北 {d['nside']['N']}・南 {d['nside']['S']}",
             fontsize=6.3, color='#444', va='baseline')
    north(fig, x_mm + w_mm - 4, y_mm - 1.5, ang)

# ---------- 版面 ----------
GAP = 10; TITLE = 13; BOTTOM_PAD = 5
rows = []
for r in ROWS:
    N_ = max(P[z]['y1'] - P[z]['yc'] for z in r); S_ = max(P[z]['yc'] - P[z]['y0'] for z in r)
    rows.append((r, N_, S_))
widths = {z: (P[z]['x1'] - P[z]['x0']) * m2mm for z in OV_ZONES}
total_h = sum((N_ + S_) * m2mm + TITLE + BOTTOM_PAD for _, N_, S_ in rows)

def legend_block(fig, x_mm, y_mm, w_mm, h_mm):
    # 索引圖
    kx0, kx1 = 300990, 306320
    KH = 50
    ka = fig.add_axes([x_mm / W, (y_mm + h_mm - 12 - KH) / Hh, w_mm / W, KH / Hh])
    ymid = center.interpolate(center.project(Point((kx0 + kx1) / 2, 2771100))).y
    sx = (kx1 - kx0) / w_mm
    ka.set_xlim(kx0, kx1); ka.set_ylim(ymid - KH / 2 * sx, ymid + KH / 2 * sx); ka.axis('off')
    vb = box(kx0, ymid - KH / 2 * sx, kx1, ymid + KH / 2 * sx)
    ka.add_collection(LineCollection(lines(road.boundary.intersection(vb)), colors='#bdbdbd', linewidths=.15))
    for i, z in enumerate(OV_ZONES):
        ka.add_collection(PathCollection([poly_path(REG[z])], facecolors=ZONE_C, alpha=.55 if i % 2 == 0 else .3, edgecolors='none'))
        c = REG[z].centroid; yb = center.interpolate(center.project(c)).y
        ka.text(c.x, yb - 230, z, fontsize=6.5, ha='center', va='top', color=ZONE_C, fontweight='bold', path_effects=halo)
    ka.add_collection(LineCollection(lines(elev.intersection(vb)), colors='#111', linewidths=.6))
    fig.text(x_mm / W, (y_mm + h_mm - 8) / Hh, '索引｜Z1–Z7 第一排街廓範圍（藍）', fontsize=8, fontweight='bold', va='top')
    fig.text((x_mm + w_mm) / W, (y_mm + h_mm - 8) / Hh, f'約 1:{round(sx * 1000 / 1000) * 1000:,}　北向朝上', fontsize=6, va='top', ha='right', color='#555')
    # 圖例（含照片判讀補繪）；比例尺與說明依圖例列數往下排
    h = base_handles() + detail_handles(SCALE) + photo_handles()
    ncol = 2; rows_ = -(-len(h) // ncol); lg_top = y_mm + h_mm - 68
    fig.legend(handles=h, loc='upper left', bbox_to_anchor=(x_mm / W, lg_top / Hh), frameon=False, fontsize=5.7, ncol=ncol,
               handlelength=2.2, handleheight=.9, labelspacing=.5, columnspacing=1.0, borderaxespad=0)
    sb_y = lg_top - rows_ * 3.15 - 9
    scalebar(fig, x_mm, sb_y)
    fig.text(x_mm / W, (sb_y - 6) / Hh, NOTE_SHORT, fontsize=5.2, va='top', color='#444', linespacing=1.4)

def base_handles():
    plt.rcParams['hatch.linewidth'] = .5
    plt.rcParams['hatch.color'] = BLD_DOT
    return [Patch(facecolor=BLD_FC, edgecolor=BLD_EC, lw=.4, hatch='....', label='建物（線稿可見輪廓）'),
            Patch(facecolor='white', edgecolor=INK, lw=.6, label='第一排街廓（地界外框）'),
            Patch(facecolor=GREEN_FC, edgecolor='none', label='公園綠地（OSM）'),
            Line2D([], [], color=ROAD_EC, lw=.5, label='路緣（道路閉合外緣，含分隔島）'),
            Line2D([], [], color=DECK_EC, lw=.7, ls=(0, (4, 2)), label='市民高架橋面投影（上方構造，推估）'),
            Line2D([], [], color=DECK_EC, lw=.6, ls=(0, (2, 1.5)), label='匝道'),
            Line2D([], [], color=INK, lw=.6, ls=(0, (8, 2, 1.5, 2)), label=f'截斷線（距中心線 {D_MAX:.0f} m）' if not VARIANT['full'] else f'截斷線（Z1–Z3、Z5 距中心線 {D_MAX:.0f} m）'),
            Patch(facecolor='white', edgecolor=INK, lw=.4, hatch='x', label='通風井（OSM）')]

NOTE_SHORT = ('第一排街廓：沿市民大道中心線每 4 m 向南北打射線，第一個碰到的實體街廓；界線沿路口中心線。\n'
              '人行道＝市府新工處人行道範圍；標線型人行道、行人穿越線＝交工處圖資；騎樓官方路段＝停管處\n'
              '「機車退出騎樓路段」名稱含「騎樓」者；其餘臨路貼齊建物沿道路境界向內 3.64 m 推估。樹穴、花圃＝新工處人行道固定設施物。\n'
              '車道線：OSM lanes＋車道面等分推估，非標線實測。底圖 02_南京至仁愛擴幅 線稿（EPSG:3826）。\n'
              '照片判讀：現場照片（civic photo）判讀柱型、分隔島植栽與街道設施；柱位依官方平均跨距 36.3 m\n'
              '（D028 市民大道主橋 5,802.5 m／160 孔）沿分隔島推估，非實測。\n'
              '© OpenStreetMap contributors / ODbL｜政府資料開放授權第 1 版｜2026-10-07')

def end_label(fig, x_mm, y_mm, name, fw=W, fh=Hh):
    # 單元兩端界線道路：直書於圖與圖之間的空隙（空隙即該路口）
    fig.text(x_mm / fw, y_mm / fh, name, fontsize=6.5, rotation=90, ha='center', va='center', color=ZONE_C, fontweight='bold')

def build(out_pdf, out_png):
    fig = plt.figure(figsize=(W * MM, Hh * MM))
    header(fig, '市民大道兩側第一排街廓詳細平面｜Z1–Z7 設計介入單元',
           f'淡水河堤—光復南路｜七圖同比例 1:{SCALE:,}，依市民大道走向轉正排列（北向見各圖指北）｜範圍：市民大道南北兩側第一排街廓，'
           f'大型街廓於距中心線 {D_MAX:.0f} m 截斷｜標示車道線、人行道、騎樓、行人穿越線')
    top = Hh - 58
    free = top - 16 - total_h
    vgap = max(0, free / (len(rows)))
    y = top
    for ri, (r, N_, S_) in enumerate(rows):
        hmm = (N_ + S_) * m2mm
        y_title = y - 6
        y_bot = y - TITLE - hmm
        x = 20
        yc_mm = y_bot + S_ * m2mm
        for k, z in enumerate(r):
            d = P[z]; w = widths[z]
            ax = fig.add_axes([x / W, y_bot / Hh, w / W, hmm / Hh])
            draw_zone(ax, z)
            ax.set_ylim(d['yc'] - S_, d['yc'] + N_)
            zone_title(fig, z, x, y_title, w, d['ang'])
            if k == 0: end_label(fig, x - GAP / 2, yc_mm, ZP[z]['from'])
            end_label(fig, x + w + GAP / 2, yc_mm, ZP[z]['to'])
            x += w + GAP
        if ri == len(rows) - 1:
            legend_block(fig, x + 4, 16, W - 20 - x - 4, y - 16)
        y = y_bot - BOTTOM_PAD - vgap
    fig.savefig(out_pdf); fig.savefig(out_png, dpi=110); plt.close(fig)

def single(z, out_png, dpi=300):
    d = P[z]; w = (d['x1'] - d['x0']) * m2mm; hmm = (d['y1'] - d['y0']) * m2mm
    fw, fh = w + 20, hmm + 30
    fig = plt.figure(figsize=(fw * MM, fh * MM))
    ax = fig.add_axes([10 / fw, 10 / fh, w / fw, hmm / fh])
    draw_zone(ax, z); ax.set_ylim(d['y0'], d['y1'])
    zp = ZP[z]
    ycm = 10 + (d['yc'] - d['y0']) * m2mm
    end_label(fig, 5, ycm, zp['from'], fw, fh); end_label(fig, fw - 5, ycm, zp['to'], fw, fh)
    fig.text(10 / fw, 1 - 9 / fh, f"{z}　{zp['from']}—{zp['to']}　｜{zp['info']}", fontsize=9, fontweight='bold', va='baseline')
    fig.text(10 / fw, 1 - 14 / fh, f"1:{SCALE:,}｜軸線 {zp['len_m']:,} m｜第一排街廓 北 {d['nside']['N']}・南 {d['nside']['S']}", fontsize=6.3, color='#444', va='baseline')
    t = np.radians(-d['ang']); v = np.array([-np.sin(t), np.cos(t)]); c = np.array([fw - 14, fh - 11])
    fig.add_artist(matplotlib.patches.FancyArrowPatch((c - v * 3.5) / [fw, fh], (c + v * 3.5) / [fw, fh], transform=fig.transFigure,
                                                      arrowstyle='-|>', mutation_scale=7, color='#111', lw=.8))
    fig.text((c[0] + v[0] * 6) / fw, (c[1] + v[1] * 6) / fh, 'N', fontsize=6.5, ha='center', va='center')
    fig.savefig(out_png, dpi=dpi); plt.close(fig)

if __name__ == '__main__':
    build(H / f'市民大道_Z1-Z7_兩側第一排街廓詳細平面_A1_1-{SCALE}_20261007.pdf', H / 'A1_Z1-Z7_第一排街廓_預覽.png')
    (H / '單元單張').mkdir(exist_ok=True)
    for z in ZONES_USE:
        single(z, H / '單元單張' / f"{z}_{short(ZP[z]['from'])}-{short(ZP[z]['to'])}_第一排街廓_1-{SCALE}.png")
    print('done')
