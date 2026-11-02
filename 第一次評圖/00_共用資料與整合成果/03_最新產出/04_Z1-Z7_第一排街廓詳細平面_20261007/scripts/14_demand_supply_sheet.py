# 主題圖：單元「穿越需求與供給」A1 一張（先做 Z1）
#   底圖：05_sheets 同一表現（本段置中、前後段與周邊街廓淡化，1:2500），本段覆淡白
#   藍＝供給（平面穿越點與其行穿線、地下街、天橋）；橘＝需求（街口、巷口、步道口、捷運／地下街出入口、公車站、YouBike、設施）
#   下方：沿市民大道拉直之分布圖、數量表、供給點表、圖例
#   資料：13_demand_supply.py → data/{Z}_demand_supply_EPSG3826.geojson
import json, sys, importlib.util, collections
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Patch, PathPatch
from matplotlib.collections import PathCollection, LineCollection
from matplotlib.lines import Line2D
from shapely.geometry import shape, box, Point

H = Path(__file__).resolve().parents[1]
ZONE = sys.argv[1] if len(sys.argv) > 1 else 'Z1'
MODES = sys.argv[2].split(',') if len(sys.argv) > 2 else ['A', 'B']
_argv = sys.argv; sys.argv = [_argv[0], 'A1']          # 05 以 argv[1] 判讀紙張，主題圖固定 A1
spec = importlib.util.spec_from_file_location('sheets', H / 'scripts/05_sheets.py')
F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
sys.argv = _argv
S = F.S
plt.rcParams['axes.unicode_minus'] = False
SCALE, m2mm, W, Hh, MM = F.SCALE, F.m2mm, F.W, F.Hh, F.MM
BLUE, BLUE_L = '#2166AC', '#92C5DE'
DEM = '#D95F02'
BULK_FC = '#F5B183'      # 大量體色塊（淺橘純色，需求點符號為深橘）
ROUTE_LW = 1.3           # 路線統一線寬（pt）
DATA = json.load(open(H / f'data/{ZONE}_demand_supply_EPSG3826.geojson'))
FEAT = [(shape(f['geometry']), f['properties']) for f in DATA['features']]
ST = DATA['stats']
DTYPES = [  # 需求點三類（cat）：標籤, marker, size, 填色, 一覽表簡稱
    ('bulk', '大量體（大型商辦、高樓）', 'p', 12.5, DEM, '量體'),
    ('transit', '捷運／地下街出入口', 's', 7.5, 'white', '捷運'),
    ('alley', '巷道出入口（街口、巷口、步道口）', None, 9.0, DEM, '巷道')]
DT = {t[0]: t for t in DTYPES}
STYPES = {'at_grade': ('平面穿越', 'o', 11.5), 'underground': ('地下街（需上下樓）', 's', 10), 'footbridge': ('人行天橋', '^', 11.5)}

def street_name(pt):
    t = S.center.project(pt)
    a_ = np.array(S.center.interpolate(max(0, t - 15)).coords[0]); b_ = np.array(S.center.interpolate(t + 15).coords[0])
    u = (b_ - a_) / np.linalg.norm(b_ - a_)
    best = None
    for n, g in S.streets.items():
        if n.startswith('市民大道'): continue
        d_ = g.distance(pt)
        if d_ >= 45: continue
        loc = g.intersection(pt.buffer(60))
        segs = [np.asarray(q.coords) for q in getattr(loc, 'geoms', [loc]) if q.geom_type == 'LineString' and q.length > 5]
        if not segs: continue
        v = np.vstack(segs); v = v - v.mean(axis=0); dv = np.linalg.svd(v, full_matrices=False)[2][0]
        if abs(float(np.dot(dv, u))) > .7: continue
        if best is None or d_ < best[0]: best = (d_, n)
    return best[1] if best else ''

def tri(side):   # 街口三角形指向大道：北側朝下、南側朝上
    return 'v' if side == 'N' else '^'

def draw_theme(ax, T, texts=True):
    # 供給：橫越大道之行穿線改藍
    st = [S.poly_path(T(g)) for g, p in FEAT if p['kind'] == 'supply_stripe']
    ax.add_collection(PathCollection([q for q in st if q is not None], facecolors=BLUE, edgecolors=BLUE, linewidths=.4, zorder=21))
    for g, p in FEAT:
        if p['kind'] != 'supply': continue
        q = T(g); lab, mk, ms = STYPES[p['type']]
        ax.plot([q.x], [q.y], ls='none', marker=mk, ms=ms, mfc=BLUE, mec='white', mew=1.1, zorder=30)
        if p['type'] == 'at_grade':
            nm = street_name(g)
            txt = f"{nm}\n{p['n_stages']} 段／{p['span_m']:.0f} m"
        else:
            txt = {'underground': '地下街', 'footbridge': '天橋'}[p['type']]
        off = (12, 0) if p['type'] == 'at_grade' else (10, -13)     # 地下街／天橋標於右下，避免與相鄰平面穿越點重疊
        if texts: ax.annotate(txt, (q.x, q.y), xytext=off, textcoords='offset points', ha='left', va='center', fontsize=7.2, color=BLUE,
                    fontweight='bold', zorder=31, path_effects=S.halo, linespacing=1.15)
    # 匯聚路線：每個需求點沿可步行路線（巷道、步道、大道人行道中線）走到匯聚路口；統一線寬（重疊段合為一條）
    segs, sn = set(), []
    for g, p in FEAT:
        if p['kind'] != 'route': continue
        cs = [tuple(round(v, 2) for v in c) for c in g.coords]
        if len(cs) >= 2:
            qa, qb = T(Point(cs[0])), T(Point(cs[1])); sn.append([(qa.x, qa.y), (qb.x, qb.y)])   # 需求點到路網之吸附段（短）
        for a_, b_ in zip(cs[1:], cs[2:]):
            if a_ != b_: segs.add((min(a_, b_), max(a_, b_)))
    L_ = [[(T(Point(a_)).x, T(Point(a_)).y), (T(Point(b_)).x, T(Point(b_)).y)] for a_, b_ in segs]
    ax.add_collection(LineCollection(L_, colors=DEM, linewidths=ROUTE_LW, alpha=.9, zorder=26, capstyle='round', joinstyle='round'))
    ax.add_collection(LineCollection(sn, colors=DEM, linewidths=ROUTE_LW, alpha=.9, linestyles=(0, (1.2, 1.2)), zorder=26))
    # 大量體建物：橘色純色塊
    bp = [S.poly_path(T(g)) for g, p in FEAT if p['kind'] == 'bulk_bld']
    ax.add_collection(PathCollection([q for q in bp if q is not None], facecolors=BULK_FC, edgecolors='none', zorder=24))
    # 需求點符號
    for g, p in FEAT:
        if p['kind'] != 'demand': continue
        q = T(g); _, lab, mk, ms, fc, _ = DT[p['cat']]
        if mk is None: mk = tri(p['side'])
        if p['type'] == 'lane' or p['type'] == 'path_mouth': ms = ms * .78          # 巷口較街口小
        ax.plot([q.x], [q.y], ls='none', marker=mk, ms=ms, mfc=fc, mec=DEM if fc == 'white' else 'white', mew=1.3, zorder=28)
    # 路口角點：匯聚數量
    for g, p in FEAT:
        if p['kind'] != 'conv_corner' or not p['count']: continue
        c = T(g)
        ax.plot([c.x], [c.y], ls='none', marker='o', ms=12, mfc='white', mec=DEM, mew=1.4, zorder=29)
        ax.text(c.x, c.y, str(p['count']), ha='center', va='center', fontsize=6.8, fontweight='bold', color=DEM, zorder=30)
    if texts: label_demand(ax, T)

PT_M = 0.3528 * SCALE / 1000          # 1 pt 在圖上代表之公尺數
def text_wh(txt, fs):
    w = sum(fs * (1.0 if ord(ch) > 0x2e80 else .56) for ch in txt) * PT_M
    return w, fs * 1.25 * PT_M
def label_demand(ax, T):
    # 每個需求點標「編號 原因」：北側往上、南側往下找不重疊位置，遠離時加引線
    fs = 5.6
    occ = []
    for g, p in FEAT:
        if p['kind'] in ('demand', 'supply', 'conv_corner'):
            q = T(g); r = 5.5; occ.append((q.x - r, q.y - r, q.x + r, q.y + r))
    items = sorted([(T(g), p) for g, p in FEAT if p['kind'] == 'demand'], key=lambda x: x[1]['s'])
    for q, p in items:
        txt = f"{p['id']} {p['reason']}"
        w, h = text_wh(txt, fs)
        sg = 1 if p['side'] == 'N' else -1
        placed = None
        for k in range(0, 9):
            dy = sg * (8 + 7 * k) * PT_M
            for dx in (0, 1, -1, 2, -2):
                cx = q.x + dx * w * .55; cy = q.y + dy
                bx = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
                if all(bx[2] < o[0] or bx[0] > o[2] or bx[3] < o[1] or bx[1] > o[3] for o in occ):
                    placed = (cx, cy, bx, k > 1 or dx != 0); break
            if placed: break
        if not placed:
            cy = q.y + sg * 75 * PT_M; placed = (q.x, cy, (q.x - w / 2, cy - h / 2, q.x + w / 2, cy + h / 2), True)
        cx, cy, bx, lead = placed
        occ.append(bx)
        if lead:
            ax.plot([q.x, cx], [q.y, cy - sg * h / 2], color='#8a8a8a', lw=.3, alpha=.9, zorder=27)   # 標註引線（灰，與步行路線區分）
        ax.text(cx, cy, txt, ha='center', va='center', fontsize=fs, color=DEM, zorder=31, path_effects=S.halo,
                fontweight='bold' if p['cat'] == 'bulk' or p['type'] == 'street' else 'normal')

UB_FC, UB_EC, OUT_C = '#E2E2E2', '#8f8f8f', '#5f5f5f'
RD_FC, RD_EC = '#EFEFEF', '#5a5a5a'
# 市民大道道路形狀（B 版用）：沿中心線每 3 m 向兩側找第一排街廓邊線（±60 m 滾動中位數，跨過橫街口），
#   外推 18 m（含路口轉角與橫街開口）圍出範圍，取其內之道路面（路緣、中央分隔島、路口形狀）；其他道路不畫
from shapely.strtree import STRtree as _STR
from shapely.geometry import LineString as _LS, Polygon as _PG
_FBG = [shape(f['geometry']) for fn in ('frontage_blocks_EPSG3826.geojson', 'frontage_blocks_full_EPSG3826.geojson')
        for f in json.load(open(H / 'data' / fn))['features']]
_FBT = _STR(_FBG)
def boulevard_shape(t0, t1, extra=18.0):
    C = S.center; t0, t1 = max(0, t0), min(C.length, t1)
    ts = np.arange(t0, t1, 3.0)
    def nrm(t):
        a_ = np.array(C.interpolate(max(0, t - 15)).coords[0]); b_ = np.array(C.interpolate(min(C.length, t + 15)).coords[0])
        v = (b_ - a_) / np.linalg.norm(b_ - a_); return np.array([-v[1], v[0]])
    sides = {}
    for sd in (1, -1):
        e = []
        for t in ts:
            p_ = np.array(C.interpolate(t).coords[0]); n_ = nrm(t)
            ray = _LS([p_, p_ + sd * n_ * 140])
            hit = [ray.intersection(_FBG[i]) for i in _FBT.query(ray, predicate='intersects')]
            ds = [float(np.linalg.norm(np.array(c) - p_)) for h in hit for q in getattr(h, 'geoms', [h]) if not q.is_empty for c in q.coords]
            e.append(min(ds) if ds else np.nan)
        e = np.array(e); m = 20
        med = np.array([np.nanmedian(e[max(0, i - m): i + m + 1]) if np.isfinite(e[max(0, i - m): i + m + 1]).any() else np.nan for i in range(len(e))])
        ok = np.isfinite(med)
        med = np.interp(np.arange(len(med)), np.where(ok)[0], med[ok]) if ok.any() else np.full(len(med), 40.0)
        med = np.minimum(med, 90)
        sides[sd] = [tuple(np.array(C.interpolate(t).coords[0]) + sd * nrm(t) * (o + extra)) for t, o in zip(ts, med)]
    band = _PG(sides[1] + sides[-1][::-1]).buffer(0)
    return S.road.intersection(band)
def handles(mode='A'):
    h = []
    if mode == 'B':
        h += [Patch(facecolor='none', edgecolor=OUT_C, lw=.6, label='建物輪廓'),
              Line2D([], [], color=RD_EC, lw=.6, label='市民大道路緣、中央分隔島、路口形狀（其他道路不畫）'),
              Line2D([], [], color=UB_EC, lw=.6, ls=(0, (4, 2)), label='市民大道橋下空間（高架橋面投影，推估）')]
    h += [Line2D([], [], ls='none', marker=STYPES[k][1], ms=STYPES[k][2] * .85, mfc=BLUE, mec='white', label=STYPES[k][0]) for k in STYPES]
    h.append(Patch(facecolor=BLUE, edgecolor=BLUE, label='橫越大道之行穿線（交工處）'))
    h.append(Line2D([], [], color=DEM, lw=ROUTE_LW, label='步行匯聚路線：沿巷道、步道及大道人行道中線到最近之平面穿越'))
    h.append(Line2D([], [], ls='none', marker='o', ms=9, mfc='white', mec=DEM, mew=1.3, label='路口角點：匯聚之需求點數'))
    for cat, lab, mk, ms, fc, _ in DTYPES:
        h.append(Line2D([], [], ls='none', marker=mk or 'v', ms=ms * .85, mfc=fc, mec=DEM if fc == 'white' else 'white', mew=1.0,
                        label=lab + ('；三角形指向大道，大＝街口、小＝巷口' if mk is None else '')))
    h.append(Patch(facecolor=BULK_FC, edgecolor='none', label='大量體建物（三維模型 ≥ 36 m 或 ≥ 12 層；或建築面積 ≥ 2,000 m2 之商辦／公共）'))
    return h

def panel_title(fig, x, y, t, sub=None):
    fig.text(x / W, y / Hh, t, fontsize=11, fontweight='bold', va='top', color='#111')
    if sub: fig.text(x / W, (y - 6) / Hh, sub, fontsize=7, va='top', color='#555')

def strip(fig, x, y, w, h):
    # 沿市民大道拉直：中線＝大道；北側需求在上、南側在下（每類一列）；供給＝藍色縱線
    ax = fig.add_axes([x / W, y / Hh, w / W, h / Hh])
    L = ST['len_m']
    have = {p['type'] for _, p in FEAT if p['kind'] == 'demand'}
    rows = [t[0] for t in DTYPES if t[0] in have]
    nr = len(rows)
    ax.axhline(0, color='#555', lw=1.0, zorder=2)
    ax.fill_between([0, L], -.45, .45, color='#eeeeee', zorder=1)
    ax.text(-12, 0, '市民大道', ha='right', va='center', fontsize=7.5, color='#333')
    for i, r in enumerate(rows):
        for sd, sign in (('N', 1), ('S', -1)):
            yy = sign * (i + 1)
            ax.axhline(yy, color='#f0f0f0', lw=.5, zorder=0)
        ax.text(-12, i + 1, DT[r][1].split('（')[0], ha='right', va='center', fontsize=7.6, color='#444')
        ax.text(-12, -(i + 1), DT[r][1].split('（')[0], ha='right', va='center', fontsize=7.6, color='#444')
    for g, p in FEAT:
        if p['kind'] == 'supply':
            sx = p['s'] - ST['s0']; lab, mk, ms = STYPES[p['type']]
            ax.plot([sx, sx], [-nr - .5, nr + .5], color=BLUE if p['type'] == 'at_grade' else BLUE_L, lw=1.6 if p['type'] == 'at_grade' else 1.2,
                    ls='-' if p['type'] == 'at_grade' else (0, (3, 2)), zorder=3)
            ax.plot([sx], [0], ls='none', marker=mk, ms=ms * .8, mfc=BLUE, mec='white', mew=.8, zorder=6)
            nm = street_name(g) if p['type'] == 'at_grade' else {'underground': '地下街', 'footbridge': '天橋'}[p['type']]
            ax.text(sx, nr + .8, nm, ha='center', va='bottom', fontsize=7.4, color=BLUE, fontweight='bold', rotation=0)
        elif p['kind'] == 'demand':
            sx = p['s'] - ST['s0']; i = rows.index(p['type']); sign = 1 if p['side'] == 'N' else -1
            _, lab, mk, ms, fc = DT[p['type']]
            if mk is None: mk = tri(p['side'])
            ax.plot([sx], [sign * (i + 1)], ls='none', marker=mk, ms=ms * .8, mfc=fc, mec=DEM if fc == 'white' else 'white', mew=.9, zorder=5)
    ax.text(L + 12, nr / 2 + .5, '北側', fontsize=8, fontweight='bold', va='center', color='#333')
    ax.text(L + 12, -nr / 2 - .5, '南側', fontsize=8, fontweight='bold', va='center', color='#333')
    ax.set_xlim(-5, L + 5); ax.set_ylim(-nr - 1, nr + 2.2)
    ax.set_yticks([]); ax.set_xticks(np.arange(0, L + 1, 100))
    ax.set_xticklabels([f'{v:.0f}' for v in np.arange(0, L + 1, 100)], fontsize=6.5)
    ax.set_xlabel(f"沿市民大道里程（m）　{S.ZP[ZONE]['from']} → {S.ZP[ZONE]['to']}", fontsize=7)
    for sp in ('top', 'right', 'left'): ax.spines[sp].set_visible(False)
    ax.spines['bottom'].set_linewidth(.5)

def table(fig, x, y, rows, widths, fs=7.6, lh=6.0, head=None, colors=None, bold_last=False):
    yy = y
    if head:
        xx = x
        for t, w_ in zip(head, widths):
            fig.text(xx / W, yy / Hh, t, fontsize=fs, fontweight='bold', va='top', color='#333'); xx += w_
        yy -= lh
        fig.add_artist(plt.Line2D([x / W, (x + sum(widths)) / W], [(yy + 1) / Hh] * 2, transform=fig.transFigure, color='#999', lw=.4))
    for i, r in enumerate(rows):
        xx = x
        for j, (t, w_) in enumerate(zip(r, widths)):
            fig.text(xx / W, yy / Hh, t, fontsize=fs, va='top', color=colors[i][j] if colors else '#222',
                     fontweight='bold' if bold_last and i == len(rows) - 1 else 'normal'); xx += w_
        yy -= lh
    return yy

def build(pdf, png_path, mode='A'):
    # mode A：現況底圖（線稿、人行道、車道線等），地圖不標文字
    # mode B：只留建物輪廓＋市民大道橋下空間（道路、分隔島、人行道等全部拿掉），地圖不標文字
    z = ZONE; d = S.PZ(z); zp = S.ZP[z]; T = d['T']; R = d['R']
    dem = [p for _, p in FEAT if p['kind'] == 'demand']; sup = [p for _, p in FEAT if p['kind'] == 'supply']
    n_at = sum(1 for p in sup if p['type'] == 'at_grade')
    fig = plt.figure(figsize=(W * MM, Hh * MM))
    fig.text(28 / W, 1 - 30 / Hh, f"{z}　{zp['from']}—{zp['to']}｜穿越需求與供給", fontsize=20, va='top')
    base = {'A': '底圖 A：現況線稿（道路、分隔島、人行道、車道線）', 'B': '底圖 B：建物輪廓＋市民大道道路面（分隔島、路口形狀）＋橋下空間'}[mode]
    fig.text(28 / W, 1 - 41 / Hh, f"1:{SCALE:,}（A1）｜{base}｜本段置中，左右為市民大道前後段（淡化）｜橘＝需求　藍＝供給",
             fontsize=8.5, va='top', color='#444')
    fig.add_artist(plt.Rectangle((10 / W, 10 / Hh), (W - 20) / W, (Hh - 20) / Hh, transform=fig.transFigure, fill=False, lw=.8))
    nN = sum(1 for p in dem if p['side'] == 'N'); nS = len(dem) - nN
    nc = {c: sum(1 for p in dem if p['cat'] == c) for c in DT}
    fig.text(28 / W, 1 - 50 / Hh, f"{ST['len_m']:,} m 內：需求點 {len(dem)} 處（大量體 {nc['bulk']}・捷運／地下街出入口 {nc['transit']}・巷道出入口 {nc['alley']}；"
             f"北 {nN}・南 {nS}）；平面穿越 {n_at} 處（另地下街 {sum(1 for p in sup if p['type'] == 'underground')}、天橋 {sum(1 for p in sup if p['type'] == 'footbridge')}）",
             fontsize=10.5, va='top', color='#222', fontweight='bold')
    F.key_map(fig, z, 600, Hh - 50, 221, 32)
    S.north(fig, W - 16, Hh - 66, d['ang'], size=7)
    # 地圖
    pa, pb = F.ends(z)
    ta, tb = sorted((S.center.project(pa), S.center.project(pb)))
    xa_, xb_ = T(pa).x, T(pb).x
    xc = (xa_ + xb_) / 2; yc = T(S.center.interpolate((ta + tb) / 2)).y
    H_AX = max(2 * max(d['y1'] - d['yc'], d['yc'] - d['y0']) * m2mm + 14, 240)
    wm = (F.MAP_X1 - F.MAP_X0) / m2mm / 2; hm = H_AX / m2mm / 2
    xlim, ylim = (xc - wm, xc + wm), (yc - hm, yc + hm)
    y_ax = Hh - 64 - H_AX
    rect = [F.MAP_X0 / W, y_ax / Hh, (F.MAP_X1 - F.MAP_X0) / W, H_AX / Hh]
    view = box(xlim[0], ylim[0], xlim[1], ylim[1])
    axc = fig.add_axes(rect)
    wb = box(*R.buffer(520).bounds)
    if mode == 'A':
        fab_b = [S.poly_path(T(g)) for g in S.polys(S.bld.intersection(wb))]
        axc.add_collection(PathCollection([q for q in fab_b if q is not None], facecolors='#E6E6E6', edgecolors='#7a7a7a', linewidths=.25, zorder=1))
        axc.add_collection(LineCollection(S.lines(T(S.road.boundary.intersection(wb))), colors='#7a7a7a', linewidths=.3, zorder=1.1))
        for z2 in F.ALL_Z:
            if z2 == z: continue
            d2 = S.zone_in_frame(z2, T)
            if T(d2['R']).intersects(view): S.draw_zone(axc, d2, scale=SCALE, sw_labels=False, texts=False)
    else:
        # 建物輪廓（全範圍）＋市民大道道路面（路緣、分隔島、路口形狀）＋橋下空間；本段外由遮罩淡化
        tm = S.center.project(S.center.interpolate((ta + tb) / 2))
        bv = boulevard_shape(tm - wm * 1.15, tm + wm * 1.15)
        axc.add_collection(LineCollection(S.lines(T(bv.boundary)), colors=RD_EC, linewidths=.5, zorder=1))          # 路緣、分隔島、路口（只畫線）
        axc.add_collection(LineCollection(S.lines(T(S.deck.intersection(wb).boundary)), colors=UB_EC, linewidths=.5,
                                          linestyles=(0, (4, 2)), zorder=1.3))                                       # 橋下空間（虛線框）
        axc.add_collection(LineCollection(S.lines(T(S.bld.intersection(wb).boundary)), colors=OUT_C, linewidths=.32, zorder=2))
    axc.add_patch(PathPatch(S.poly_path(view.buffer(50).difference(T(R))), facecolor='white', edgecolor='none', alpha=1 - F.CTX_ALPHA, zorder=50))
    axc.set_xlim(*xlim); axc.set_ylim(*ylim); axc.axis('off')
    ax = fig.add_axes(rect); ax.patch.set_alpha(0)
    if mode == 'A':
        S.draw_zone(ax, z, fs=.95, scale=SCALE, sw_labels=False, texts=False)
        ax.add_patch(PathPatch(S.poly_path(T(R)), facecolor='white', edgecolor='none', alpha=.4, zorder=15))
    draw_theme(ax, T, texts=False)
    k = int(z[1:])
    for g, nm, px in ((F.CUT_G[k - 1], zp['from'], xa_), (F.CUT_G[k] if k < len(F.CUT_G) else None, zp['to'], xb_)):
        if g is not None:
            ax.add_collection(LineCollection(S.lines(T(g)), colors=S.ZONE_C, linewidths=.9, linestyles=(0, (6, 3)), zorder=12))
            gv = T(g).intersection(view)
            cs = [c for q in getattr(gv, 'geoms', [gv]) if not q.is_empty for c in q.coords]
            if cs: px = max(cs, key=lambda c: c[1])[0]
        pass   # 地圖不標文字（界線路名見下方路口匯聚表）
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.axis('off')
    F.scalebar(fig, F.MAP_X0 + 2, y_ax - 8)
    # 下方
    top = y_ax - 15
    fig.add_artist(plt.Line2D([20 / W, (W - 20) / W], [(top + 4) / Hh] * 2, transform=fig.transFigure, color='#999', lw=.5))
    # 需求點一覽（兩欄）
    panel_title(fig, 22, top, '需求點一覽', '原因＝該點之類型與名稱；匯聚路口＝同側步行最近之平面穿越路口；距離＝沿可步行路線之步行距離')
    dl = sorted(dem, key=lambda p: (p['side'] != 'N', p['s']))
    half = (len(dl) + 1) // 2
    cols_w = [12, 10, 58, 33, 14]
    for ci, part in enumerate((dl[:half], dl[half:])):
        rows = [[p['id'], DT[p['cat']][5], p['reason'], p.get('conv', ''), f"{p.get('conv_dist', '')} m"] for p in part]
        colr = [['#222', DEM if p['cat'] == 'bulk' else '#666', '#222', BLUE, DEM if p.get('conv_dist', 0) >= 100 else '#222'] for p in part]
        table(fig, 22 + ci * 135, top - 13, rows, cols_w, fs=6.7, lh=5.25, head=['編號', '類別', '原因', '匯聚路口', '距離'], colors=colr)
    # 路口匯聚
    px0 = 300
    panel_title(fig, px0 + 4, top, '路口匯聚', '每個平面穿越路口兩側匯聚之需求點數；最遠＝最遠需求點之步行距離')
    xs = sorted([p for _, p in FEAT if p['kind'] == 'supply' and p['type'] == 'at_grade'], key=lambda p: p['s'])
    rows, colr = [], []
    for p in xs:
        nN_ = sum(1 for q in dem if q.get('conv') == p['name'] and q['side'] == 'N')
        nS_ = sum(1 for q in dem if q.get('conv') == p['name'] and q['side'] == 'S')
        far = max([q['conv_dist'] for q in dem if q.get('conv') == p['name']] or [0])
        cc = [sum(1 for q in dem if q.get('conv') == p['name'] and q['cat'] == c) for c in ('bulk', 'transit', 'alley')]
        rows.append([p['name'], f"{p['n_stages']} 段／{p['span_m']:.0f} m", f'{nN_}', f'{nS_}', f'{cc[0]}', f'{cc[1]}', f'{cc[2]}',
                     f'{nN_ + nS_}', f'{far} m'])
        colr.append([BLUE, '#222', '#222', '#222', DEM, '#222', '#222', DEM, DEM if far >= 100 else '#222'])
    yy = table(fig, px0 + 4, top - 13, rows, [36, 26, 11, 11, 13, 13, 13, 12, 15], fs=7.2, lh=6.0,
               head=['路口', '須跨越', '北', '南', '量體', '捷運', '巷道', '合計', '最遠'], colors=colr)
    others = [p for _, p in FEAT if p['kind'] == 'supply' and p['type'] != 'at_grade']
    if others:
        fig.text((px0 + 4) / W, (yy - 2) / Hh, '另有立體穿越：' + '、'.join({'underground': '台北地下街', 'footbridge': '承德路天橋'}[p['type']] for p in others)
                 + '（需上下樓，未列入匯聚）', fontsize=6.6, va='top', color='#555')
    # 圖例
    panel_title(fig, px0 + 4, yy - 16, '圖例')
    fig.legend(handles=handles(mode), loc='upper left', bbox_to_anchor=((px0 + 4) / W, (yy - 25) / Hh), ncol=2, frameon=False, fontsize=7.2,
               handlelength=2.2, handleheight=1.1, labelspacing=.7, columnspacing=2.0, borderaxespad=0)
    note = ('需求點三類：大量體＝第一排街廓內之建物，臺北三維模型（2017）高度 ≥ 36 m 或 OSM ≥ 12 層，或建築面積 ≥ 2,000 m2 之商辦／公共量體（住宅、學校除外），點位＝OSM 入口或面向大道之外牆；'
            '巷道出入口＝可步行之道路或步道穿過大道兩側第一排街廓邊線、並通往後方街區之處（OSM 2026-09-09；同處 10 m、同名道路 25 m 內合併）；'
            '捷運／地下街出入口＝OSM 節點，距大道中心線 80 m 內（排除緊急出口）。公車站、YouBike、公園不列入。'
            '\n供給點：平面＝臺北市交工處行人穿越線中位於大道路面且橫越大道者（同路口 45 m 內合併）；須跨越＝路口前後 20–30 m 沿垂直線量測之車道段數與南北最外車道緣距離（含橋下分隔島）；'
            '地下街、天橋＝2026-09-09 穿越清單。需求點不加權。匯聚路口＝同側步行距離最近之平面穿越路口：路線沿 OSM 可步行巷道／步道，'
            '\n並沿大道兩側一條連續的人行道主線（官方人行道範圍中線）行走，不跨越大道；距離＝步行距離。'
            '\n底圖：02_南京至仁愛擴幅 線稿（EPSG:3826）；© OpenStreetMap contributors / ODbL｜政府資料開放授權第 1 版｜2026-10-08')
    fig.text(22 / W, 16 / Hh, note, fontsize=5.6, va='bottom', color='#444', linespacing=1.5)
    pdf.savefig(fig)
    fig.savefig(png_path, dpi=110); plt.close(fig)

if __name__ == '__main__':
    out = H / '主題圖_穿越需求與供給'; out.mkdir(exist_ok=True)
    nm = f"{ZONE}_{S.short(S.ZP[ZONE]['from'])}-{S.short(S.ZP[ZONE]['to'])}_穿越需求與供給_A1_1-{SCALE}"
    with PdfPages(out / f'{nm}_底圖比較.pdf') as pdf:
        for m in MODES:
            build(pdf, out / f"{nm}_{m}_{'現況底圖' if m == 'A' else '建物輪廓'}_預覽.png", m)
            print(nm, m)
