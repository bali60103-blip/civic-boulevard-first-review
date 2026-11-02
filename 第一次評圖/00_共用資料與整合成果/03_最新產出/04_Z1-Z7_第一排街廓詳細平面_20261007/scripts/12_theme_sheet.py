# 主題圖：單元「南北斷裂證據＋操作基地」A1 一張（先做 Z1）
#   底圖：05_sheets 同一表現（本段置中、前後段淡化，1:2500）；上疊紅色＝斷裂證據、橘色＝操作基地
#   下方證據欄：繞路係數剖面、臨街商業凹陷、穿越點表、操作基地面積表
#   資料：11_fracture_site.py → data/{Z}_fracture_site_EPSG3826.geojson
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
from shapely.geometry import shape, box, Point, LineString

H = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sheets', H / 'scripts/05_sheets.py')
F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)   # 05：版面工具（同時載入 02 為 F.S）
S = F.S
plt.rcParams['axes.unicode_minus'] = False   # Hiragino 無 U+2212
ZONE = sys.argv[1] if len(sys.argv) > 1 else 'Z1'
SCALE, m2mm, W, Hh, MM = F.SCALE, F.m2mm, F.W, F.Hh, F.MM
RED, RED_D, RED_L = '#D7301F', '#99000D', '#F4A582'
BLUE = '#2166AC'
ORG, ORG_D = '#F28E2B', '#B35806'
GRAY = '#8a8a8a'
DATA = json.load(open(H / f'data/{ZONE}_fracture_site_EPSG3826.geojson'))
FEAT = [(shape(f['geometry']), f['properties']) for f in DATA['features']]
ST = DATA['stats']
SITE_STYLE = {   # cat: (標籤, 填色, 邊線, hatch, 操作基地?)
    'under_island': ('橋下分隔島／空地', ORG, ORG_D, None, True),
    'under_road': ('橋下車道（高架正下方）', '#FDD9B5', ORG, '////', True),
    'vacant_wooded': ('未開發空地（航照：樹林覆蓋）', '#FDB863', ORG_D, 'xx', True),
    'ramp_leftover': ('匝道間畸零地', '#FEE0B6', ORG_D, '\\\\\\\\', True),
    'elev_island': ('高架旁分隔島／交通島', '#FEE0B6', ORG_D, '\\\\\\\\', True),
    'parking': ('平面停車場', '#FEE0B6', ORG_D, '..', True),
    'small_lot': ('小型空地（待現勘）', 'none', ORG_D, None, True),
    'developing': ('開發中基地（非操作基地）', 'none', GRAY, '////', False),
}

def street_name(pt):
    # 穿越點之橫街名：45 m 內、走向與市民大道夾角 > 45° 之具名道路（排除平行之鄭州路等）
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
        v = np.vstack(segs); v = v - v.mean(axis=0)
        dirv = np.linalg.svd(v, full_matrices=False)[2][0]
        if abs(float(np.dot(dirv, u))) > .7: continue
        if best is None or d_ < best[0]: best = (d_, n)
    return best[1] if best else ''

def draw_theme(ax, T):
    # 操作基地
    for cat, (lab, fc, ec, ht, op) in SITE_STYLE.items():
        geoms = [g for g, p in FEAT if p['kind'] == 'site' and p['cat'] == cat]
        paths = [S.poly_path(T(g)) for g in geoms]; paths = [q for q in paths if q is not None]
        if not paths: continue
        plt.rcParams['hatch.color'] = ec; plt.rcParams['hatch.linewidth'] = .5
        ax.add_collection(PathCollection(paths, facecolors=fc, edgecolors=ec, linewidths=.6 if cat != 'small_lot' else .7,
                                         hatch=ht, alpha=.75 if fc != 'none' else 1, zorder=20,
                                         linestyles=(0, (3, 2)) if cat in ('small_lot', 'developing') else '-'))
    # 面積標註（≥ 2,000 m²）
    for g, p in FEAT:
        if p['kind'] != 'site' or p['area'] < 2000 or p['cat'] not in SITE_STYLE or p['cat'] in ('under_road',): continue
        c = T(g.representative_point())
        lab = SITE_STYLE[p['cat']][0].split('（')[0]
        if p['cat'] == 'developing': lab = p.get('note', '').split('施工')[0].strip() or lab
        ax.text(c.x, c.y, f"{lab}\n{p['area'] / 1e4:.2f} ha", fontsize=5.6, ha='center', va='center', zorder=26,
                color=GRAY if p['cat'] == 'developing' else ORG_D, fontweight='bold', path_effects=S.halo)
    # 橋下合計標註
    ub = [g for g, p in FEAT if p['kind'] == 'site' and p['cat'] in ('under_island', 'under_road')]
    # 無平面穿越段（沿中心線紅色帶）＋長度
    for g, p in FEAT:
        if p['kind'] != 'gap': continue
        L = S.lines(T(g))
        w = 3.2 if p['len_m'] >= 200 else 1.8
        ax.add_collection(LineCollection(L, colors='white', linewidths=w + 2.2, zorder=24.5, capstyle='butt'))
        ax.add_collection(LineCollection(L, colors=RED_D, linewidths=w, zorder=24.6, capstyle='butt'))
        if p['open_end'] and p['len_m'] < 60: continue
        c = T(g.interpolate(.5, normalized=True))
        ax.text(c.x, c.y + 12, f"{p['len_m']} m", fontsize=9 if p['len_m'] >= 200 else 7, ha='center', va='bottom', zorder=27,
                color=RED_D, fontweight='bold', path_effects=S.halo)
    # 繞路路徑：≥ 1.8× 粗紅實線，其餘淡紅細線
    for g, p in sorted([q for q in FEAT if q[1]['kind'] == 'probe'], key=lambda q: q[1]['detour']):
        hi = p['detour'] >= 1.8
        ax.add_collection(LineCollection(S.lines(T(g)), colors=RED_D if hi else RED_L, linewidths=1.3 if hi else .5,
                                         alpha=.95 if hi else .55, zorder=23 if hi else 22, capstyle='round', joinstyle='round'))
        A, B = T(Point(p['A'])), T(Point(p['B']))
        ax.plot([A.x, B.x], [A.y, B.y], ls='none', marker='o', ms=2.6 if hi else 1.6, mfc='white', mec=RED_D if hi else RED_L,
                mew=.7, zorder=24)
        if hi:
            ax.annotate(f"{p['detour']:.1f}×｜多走 {p['extra_m']:.0f} m", (A.x, A.y), xytext=(0, 5), textcoords='offset points',
                        ha='center', va='bottom', fontsize=6.2, color=RED_D, fontweight='bold', zorder=27, path_effects=S.halo)
    # 穿越點
    for g, p in FEAT:
        if p['kind'] != 'crossing': continue
        q = T(g)
        mk = {'at_grade': 'o', 'underground': 's', 'footbridge': '^'}[p['type']]
        ax.plot([q.x], [q.y], ls='none', marker=mk, ms=6.5, mfc=BLUE, mec='white', mew=1.0, zorder=28)
        lab = street_name(g) if p['type'] == 'at_grade' else {'underground': '地下街', 'footbridge': '天橋'}[p['type']]
        ax.annotate(lab, (q.x, q.y), xytext=(0, -8), textcoords='offset points', ha='center', va='top', fontsize=6, color=BLUE,
                    fontweight='bold', zorder=28, path_effects=S.halo)

def theme_handles():
    plt.rcParams['hatch.linewidth'] = .5
    h = [Line2D([], [], color=RED_D, lw=1.4, marker='o', ms=3, mfc='white', label='繞路 ≥ 1.8× 之實際步行路徑（南北各 150 m 兩點）'),
         Line2D([], [], color=RED_L, lw=.7, label='其他取樣點之步行路徑'),
         Line2D([], [], color=RED_D, lw=3, label='無平面穿越段（數字＝長度）'),
         Line2D([], [], ls='none', marker='o', ms=6, mfc=BLUE, mec='white', label='平面穿越點（交工處行穿線）'),
         Line2D([], [], ls='none', marker='s', ms=5.5, mfc=BLUE, mec='white', label='地下街穿越（需上下樓）'),
         Line2D([], [], ls='none', marker='^', ms=6, mfc=BLUE, mec='white', label='人行天橋')]
    for cat, (lab, fc, ec, ht, op) in SITE_STYLE.items():
        plt.rcParams['hatch.color'] = ec
        h.append(Patch(facecolor=fc, edgecolor=ec, hatch=ht, lw=.6, alpha=.8 if fc != 'none' else 1,
                       ls=(0, (3, 2)) if cat in ('small_lot', 'developing') else '-', label=lab))
    return h

def panel_title(fig, x, y, t, sub=None):
    fig.text(x / W, y / Hh, t, fontsize=11, fontweight='bold', va='top', color='#111')
    if sub: fig.text(x / W, (y - 6) / Hh, sub, fontsize=7, va='top', color='#555')

def chart_detour(fig, x, y, w, h):
    ax = fig.add_axes([x / W, y / Hh, w / W, h / Hh])
    pr = sorted([p for _, p in FEAT if p['kind'] == 'probe'], key=lambda p: p['s'])
    s = np.array([p['s'] for p in pr]) - ST['s0']; dv = np.array([p['detour'] for p in pr])
    ax.bar(s, dv - 1, bottom=1, width=38, color=[RED_D if v >= 1.8 else RED_L for v in dv], edgecolor='none', zorder=3)
    ax.axhline(ST['control_detour_mean'], color='#555', lw=.8, ls=(0, (4, 2)), zorder=4)
    ax.axhline(ST['detour_mean'], color=RED_D, lw=.9, ls=(0, (4, 2)), zorder=4)
    ax.text(ST['len_m'] + 8, ST['control_detour_mean'], f"平行幹道平均 {ST['control_detour_mean']:.2f}×", fontsize=7.5, va='center', color='#555')
    ax.text(ST['len_m'] + 8, ST['detour_mean'] + .06, f"{ZONE} 平均 {ST['detour_mean']:.2f}×", fontsize=7.5, va='center', color=RED_D,
            fontweight='bold')
    for _, p in FEAT:
        if p['kind'] == 'crossing':
            mk = {'at_grade': 'o', 'underground': 's', 'footbridge': '^'}[p['type']]
            ax.plot([p['s'] - ST['s0']], [1.0], marker=mk, ms=4.5, mfc=BLUE, mec='white', mew=.6, zorder=5, clip_on=False)
    for g_ in ST['gaps']:
        if g_['len_m'] < 60: continue
        ax.text((g_['from'] + g_['to']) / 2 - ST['s0'], .9, f"{g_['len_m']} m", fontsize=7, ha='center', va='top',
                color=RED_D if g_['len_m'] >= 200 else '#555', fontweight='bold' if g_['len_m'] >= 200 else 'normal')
    ax.set_xlim(-10, ST['len_m'] + 10); ax.set_ylim(.8, 2.5)
    ax.set_yticks([1, 1.5, 2, 2.5]); ax.set_yticklabels(['1.0×', '1.5×', '2.0×', '2.5×'], fontsize=7.5)
    ax.set_xticks(np.arange(0, ST['len_m'] + 1, 200)); ax.tick_params(axis='x', labelsize=7.5)
    ax.set_xlabel(f"沿市民大道里程（m，{F.S.ZP[ZONE]['from']} → {F.S.ZP[ZONE]['to']}）；下方數字＝相鄰平面穿越點間距 m", fontsize=7.2)
    for sp in ('top', 'right'): ax.spines[sp].set_visible(False)
    for sp in ('left', 'bottom'): ax.spines[sp].set_linewidth(.5)
    ax.grid(axis='y', lw=.3, color='#ddd', zorder=0)

def chart_trough(fig, x, y, w, h):
    fr = ST['frontage']
    rows = [(f'{ZONE}（本段）', fr['trough'], True), ('市民大道全線', fr['civic_all_trough'], True)] + \
           [(k, v, False) for k, v in fr['controls'].items()]
    ax = fig.add_axes([x / W, y / Hh, w / W, h / Hh])
    ys = np.arange(len(rows))[::-1]
    for yy, (lab, v, civ) in zip(ys, rows):
        ax.barh(yy, v * 100, color=(RED_D if lab.startswith(ZONE) else RED) if v > 0 else '#bdbdbd', height=.62)
        ax.text(v * 100 + (3 if v > 0 else -3), yy, f"{v * 100:+.0f}%", fontsize=7.5, va='center', ha='left' if v > 0 else 'right',
                color=RED_D if v > 0 else '#555', fontweight='bold' if civ else 'normal')
    ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in rows], fontsize=7.8)
    ax.axvline(0, color='#333', lw=.6)
    ax.set_xlim(-130, 100); ax.set_xticks([-100, -50, 0, 50, 100]); ax.tick_params(axis='x', labelsize=5.5)
    ax.text(50, len(rows) - .1, '凹陷（障礙）→', fontsize=7.2, ha='center', va='bottom', color=RED_D)
    ax.text(-65, len(rows) - .1, '← 隆起（一般街道）', fontsize=7.2, ha='center', va='bottom', color='#555')
    for sp in ('top', 'right', 'left'): ax.spines[sp].set_visible(False)
    ax.spines['bottom'].set_linewidth(.5); ax.tick_params(axis='y', length=0)

def table(fig, x, y, rows, widths, fs=6.2, lh=4.1, head=None, colors=None):
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
            c = colors[i][j] if colors else '#222'
            fig.text(xx / W, yy / Hh, t, fontsize=fs, va='top', color=c); xx += w_
        yy -= lh
    return yy

def build(pdf_path, png_path):
    z = ZONE; d = S.PZ(z); zp = S.ZP[z]; T = d['T']; R = d['R']
    fig = plt.figure(figsize=(W * MM, Hh * MM))
    fig.text(28 / W, 1 - 30 / Hh, f"{z}　{zp['from']}—{zp['to']}｜南北斷裂與操作基地", fontsize=20, va='top')
    fig.text(28 / W, 1 - 41 / Hh, f"1:{SCALE:,}（A1）｜本段置中，左右為市民大道前後段（淡化）｜紅＝斷裂證據　藍＝可穿越處　橘＝操作基地（橋下空間＋高架兩側閒置空間）",
             fontsize=8.5, va='top', color='#444')
    fig.add_artist(plt.Rectangle((10 / W, 10 / Hh), (W - 20) / W, (Hh - 20) / Hh, transform=fig.transFigure, fill=False, lw=.8))
    # 主張
    op = sum(v for k, v in ST['site_m2'].items() if SITE_STYLE.get(k, (0, 0, 0, 0, False))[4])
    ag = [g_ for g_ in ST['gaps'] if not g_['end']]
    claim = (f"跨越一次市民大道平均多走 {ST['extra_mean_m']} m（{ST['detour_mean']:.2f}×，平行幹道 {ST['control_detour_mean']:.2f}×）；"
             f"{ST['len_m']:,} m 內只有 {ST['n_at_grade']} 處平面穿越，最長 {ST['gap_max_m']} m 無法穿越；"
             f"臨街店家在大道邊凹陷 {ST['frontage']['trough'] * 100:.0f}%。可操作基地 {op / 1e4:.1f} ha。")
    fig.text(28 / W, 1 - 50 / Hh, claim, fontsize=10.5, va='top', color=RED_D, fontweight='bold')
    # 索引（右上）
    F.key_map(fig, z, 600, Hh - 50, 221, 32)
    S.north(fig, W - 16, Hh - 66, d['ang'], size=7)
    # 地圖
    pa, pb = F.ends(z)
    ta, tb = sorted((S.center.project(pa), S.center.project(pb)))
    xa_, xb_ = T(pa).x, T(pb).x
    xc = (xa_ + xb_) / 2; yc = T(S.center.interpolate((ta + tb) / 2)).y
    H_AX = max(2 * max(d['y1'] - d['yc'], d['yc'] - d['y0']) * m2mm + 14, 240)   # 加高：南北周邊街廓一併呈現（繞路路徑會進入第二排）
    wm = (F.MAP_X1 - F.MAP_X0) / m2mm / 2; hm = H_AX / m2mm / 2
    xlim, ylim = (xc - wm, xc + wm), (yc - hm, yc + hm)
    y_ax = Hh - 64 - H_AX
    rect = [F.MAP_X0 / W, y_ax / Hh, (F.MAP_X1 - F.MAP_X0) / W, H_AX / Hh]
    view = box(xlim[0], ylim[0], xlim[1], ylim[1])
    axc = fig.add_axes(rect)
    # 周邊街廓（第一排以外）：建物與路緣，與前後段一同被淡化遮罩覆蓋
    wb = box(*R.buffer(520).bounds)
    fab_b = [S.poly_path(T(g)) for g in S.polys(S.bld.intersection(wb))]
    axc.add_collection(PathCollection([q for q in fab_b if q is not None], facecolors='#E6E6E6', edgecolors='#7a7a7a', linewidths=.25, zorder=1))
    axc.add_collection(LineCollection(S.lines(T(S.road.boundary.intersection(wb))), colors='#7a7a7a', linewidths=.3, zorder=1.1))
    for z2 in F.ALL_Z:
        if z2 == z: continue
        d2 = S.zone_in_frame(z2, T)
        if T(d2['R']).intersects(view): S.draw_zone(axc, d2, scale=SCALE, sw_labels=False, texts=False)
    axc.add_patch(PathPatch(S.poly_path(view.buffer(50).difference(T(R))), facecolor='white', edgecolor='none', alpha=1 - F.CTX_ALPHA, zorder=50))
    axc.set_xlim(*xlim); axc.set_ylim(*ylim); axc.axis('off')
    ax = fig.add_axes(rect); ax.patch.set_alpha(0)
    S.draw_zone(ax, z, fs=.95, scale=SCALE, sw_labels=False)
    # 底圖退後：本段範圍內覆淡白，讓主題色突出
    ax.add_patch(PathPatch(S.poly_path(T(R)), facecolor='white', edgecolor='none', alpha=.35, zorder=15))
    draw_theme(ax, T)
    k = int(z[1:])
    for g, nm, px in ((F.CUT_G[k - 1], zp['from'], xa_), (F.CUT_G[k] if k < len(F.CUT_G) else None, zp['to'], xb_)):
        if g is not None:
            ax.add_collection(LineCollection(S.lines(T(g)), colors=S.ZONE_C, linewidths=.9, linestyles=(0, (6, 3)), zorder=12))
            gv = T(g).intersection(view)
            cs = [c for q in getattr(gv, 'geoms', [gv]) if not q.is_empty for c in q.coords]
            if cs: px = max(cs, key=lambda c: c[1])[0]
        fig.text((F.MAP_X0 + (px - xlim[0]) * m2mm) / W, (y_ax + H_AX + 1.5) / Hh, nm, fontsize=7.5, fontweight='bold', color=S.ZONE_C,
                 ha='center', va='bottom')
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.axis('off')
    F.scalebar(fig, F.MAP_X0 + 2, y_ax - 8)
    # 證據欄（兩列）
    top = y_ax - 15
    fig.add_artist(plt.Line2D([20 / W, (W - 20) / W], [(top + 4) / Hh] * 2, transform=fig.transFigure, color='#999', lw=.5))
    plt.rcParams['font.size'] = 8
    # 第一列：證據一（繞路）｜證據二（凹陷）｜證據三（穿越點）
    panel_title(fig, 22, top, '證據一｜跨越一次要繞多遠', f"南北各 150 m 兩點之最短步行距離 ÷ 直線 300 m；每 50 m 取樣（{ST['n_probes']} 處）。深紅＝≥ 1.8×，藍點＝穿越點")
    chart_detour(fig, 34, top - 100, 330, 80)
    panel_title(fig, 410, top, '證據二｜店家離開大道', f"活躍店家密度：中線 ±50 m {ST['frontage']['inner_per_ha']:.1f} 家/ha，200–400 m {ST['frontage']['ref_per_ha']:.1f} 家/ha")
    chart_trough(fig, 452, top - 94, 150, 74)
    panel_title(fig, 630, top, '證據三｜可穿越處', '平面穿越須跨車道段數／南北總寬（含橋下分隔島）')
    cr = sorted([p for _, p in FEAT if p['kind'] == 'crossing'], key=lambda p: p['s'])
    rows, cols = [], []
    for i, p in enumerate(cr):
        g = next(g for g, q in FEAT if q is p)
        nxt = next((q['s'] for q in cr[i + 1:] if q['type'] == 'at_grade'), ST['s1']) if p['type'] == 'at_grade' else None
        nm = street_name(g) if p['type'] == 'at_grade' else {'underground': '台北地下街', 'footbridge': '承德路天橋'}[p['type']]
        typ = {'at_grade': '平面', 'underground': '地下', 'footbridge': '天橋'}[p['type']]
        wid = f"{p['n_carriageways']} 段／{p['span_m']:.0f} m" if p['type'] == 'at_grade' else '需上下樓'
        gap = f"{nxt - p['s']:.0f} m" if nxt is not None else '—'
        rows.append([nm or '（未具名）', typ, wid, gap])
        cols.append(['#222', '#222', '#222', RED_D if nxt is not None and nxt - p['s'] >= 200 else '#222'])
    table(fig, 630, top - 13, rows, [44, 16, 34, 30], fs=7.8, lh=6.2, head=['穿越點', '型式', '須跨越', '至下一處平面'], colors=cols)
    # 第二列：操作基地｜圖例
    r2 = top - 114
    fig.add_artist(plt.Line2D([20 / W, (W - 20) / W], [(r2 + 4) / Hh] * 2, transform=fig.transFigure, color='#ddd', lw=.4))
    panel_title(fig, 22, r2, '操作基地｜橋下空間＋高架兩側閒置空間', '逐塊以臺北市 2025 正射航照判讀；學校、醫院、博物館等使用中空間排除')
    srows = []
    for cat, (lab, fc, ec, ht, opn) in SITE_STYLE.items():
        a = ST['site_m2'].get(cat, 0)
        if a and opn: srows.append([lab, f"{a / 1e4:.2f} ha", f"{a:,.0f} m²".replace('m²', 'm2')])
    srows.append(['合計', f"{op / 1e4:.2f} ha", ''])
    dev = ST['site_m2'].get('developing', 0)
    yy = table(fig, 22, r2 - 13, srows, [70, 22, 26], fs=7.8, lh=6.2, head=['類別', '面積', ''],
               colors=[['#222', '#222', '#777']] * (len(srows) - 1) + [[ORG_D, ORG_D, ORG_D]])
    fig.text(22 / W, (yy - 1) / Hh, f"另：開發中基地 {dev / 1e4:.2f} ha（台北雙子星 C1／D1、國王雙子星）不列入操作基地", fontsize=6.8, va='top', color=GRAY)
    panel_title(fig, 190, r2, '圖例')
    fig.legend(handles=theme_handles(), loc='upper left', bbox_to_anchor=(190 / W, (r2 - 9) / Hh), ncol=2, frameon=False, fontsize=7.6,
               handlelength=2.8, handleheight=1.1, labelspacing=.75, columnspacing=2.2, borderaxespad=0)
    # 讀圖說明
    panel_title(fig, 520, r2, '讀圖')
    read = (f"1　紅色路徑是從北側 150 m 走到南側 150 m 的最短步行路線。直線只要 300 m，\n"
            f"　   本段平均要走 {300 + ST['extra_mean_m']:.0f} m；最差處（{ST['detour_max']:.1f}×）幾乎繞一整個街廓。\n"
            f"2　{ST['len_m']:,} m 內只有 {ST['n_at_grade']} 處平面穿越，每處都要分 2 段過車道、中間停在橋下分隔島；\n"
            f"　   最長 {ST['gap_max_m']} m 沒有任何平面穿越點。\n"
            f"3　店家密度在大道兩側 50 m 內只有 200–400 m 外的 {ST['frontage']['inner_per_ha'] / ST['frontage']['ref_per_ha'] * 100:.0f}%；\n"
            f"　   五條平行幹道都是相反的『路邊最密』。大道本身成為商業的邊界。\n"
            f"4　橘色是可操作的地面：橋下 {(ST['site_m2'].get('under_island', 0) + ST['site_m2'].get('under_road', 0)) / 1e4:.1f} ha"
            f"，以及兩側未開發空地、畸零地與停車場 "
            f"{(op - ST['site_m2'].get('under_island', 0) - ST['site_m2'].get('under_road', 0)) / 1e4:.1f} ha，\n"
            f"　   多數緊鄰無法穿越的路段，正是縫合南北的介入位置。")
    fig.text(520 / W, (r2 - 11) / Hh, read, fontsize=7.8, va='top', color='#222', linespacing=1.75)
    note = ('方法：繞路係數同 2026-09-09 分析 E2（OSM 步行路網、offset 150 m；控制組＝八德路、忠孝東路、南京東路、長安東路、民生東路同法計算）；'
            '商業凹陷同 E1（活躍店家＝餐飲、零售、便利超市、夜生活、商辦、金融、旅宿、醫療）。平面穿越點＝交工處行穿線中位於大道路面且橫越大道者（同路口 45 m 內合併）；'
            '\n須跨越＝路口前後 20–30 m 沿垂直線量測線稿車道段數與南北最外車道緣距離。操作基地：橋下＝高架橋面投影（推估）∩ 本段；兩側閒置＝OSM 平面停車場／施工中標記與第一排街廓內未建築空地，'
            '逐塊以臺北市 2025 正射航照判讀（學校、醫院、博物館院區等使用中空間排除；開發中基地另列）。權屬與實際使用狀態須現勘。'
            '\n底圖：02_南京至仁愛擴幅 線稿（EPSG:3826）；© OpenStreetMap contributors / ODbL｜政府資料開放授權第 1 版｜2026-10-08')
    fig.text(22 / W, 16 / Hh, note, fontsize=5.6, va='bottom', color='#444', linespacing=1.5)
    with PdfPages(pdf_path) as pdf: pdf.savefig(fig)
    fig.savefig(png_path, dpi=110); plt.close(fig)

if __name__ == '__main__':
    out = H / f'主題圖_南北斷裂與操作基地'; out.mkdir(exist_ok=True)
    nm = f"{ZONE}_{S.short(S.ZP[ZONE]['from'])}-{S.short(S.ZP[ZONE]['to'])}_南北斷裂與操作基地_A1_1-{SCALE}"
    build(out / f'{nm}.pdf', out / f'{nm}_預覽.png')
    print(nm)
