# 出圖：Z1–Z8 各一張 A1 橫式，八張統一 1:2500 —— 第一排街廓詳細平面＋車道線、人行道、騎樓、行人穿越線
# 每張一個單元、置中（沿市民大道之中點對齊圖面中心）；左右延伸市民大道前後段，同表現、範圍外淡化（透明度 30%）。
# 比例：各張同比例且每段單列，最長之 Z7（1.6 km）在 1:2000 即 812 mm 超出 A1 可用寬，故取 1:2500。
# 下方資訊帶：圖例、索引、比例尺、單元摘要。
# 紙張：python3 05_sheets.py [A1|A3]。A3（420×297）為 A1 之一半：比例 1:5000、版面 ×0.5、字級 ×0.75、線寬 ×0.6（印出可讀）。
import json, collections, importlib.util, sys, textwrap, unicodedata
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
from shapely.ops import unary_union

H = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sheet', H / 'scripts/02_sheet.py')
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)   # 共用：資料、轉正、底圖繪製、字型
S.VARIANT['full'] = True   # Z4、Z6、Z7 用完整版範圍（不截斷、跨界街廓整塊）
plt.rcParams['lines.scale_dashes'] = False

PAPER = (sys.argv[1] if len(sys.argv) > 1 else 'A1').upper()
PROF = {'A1': dict(W=841, H=594, SCALE=2500, K=1.0, F=1.0, LW=1.0, date='20261008', lens=(0, 25, 50, 100, 200)),
        'A3': dict(W=420, H=297, SCALE=5000, K=0.5, F=0.75, LW=0.6, date='20261009', lens=(0, 50, 100, 200, 400))}[PAPER]
SCALE = PROF['SCALE']; K, F, LWF = PROF['K'], PROF['F'], PROF['LW']
S.W, S.Hh = PROF['W'], PROF['H']   # 02 之 header／north 依此換算
S.TXT['f'] = F
m2mm = 1000 / SCALE
W, Hh, MM = S.W, S.Hh, S.MM
BAND = 104 * K             # 下方資訊帶高（mm）
CTX_ALPHA = 0.3            # 範圍外（前後段）不透明度
MAP_X0, MAP_X1 = 20 * K, W - 20 * K
CUT_G = [shape(f['geometry']) for f in S.ZF if 'cut' in f['properties']]
ALL_Z = ['Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6', 'Z7', 'Z8']
SDK = S.SDK
def ends(z):
    # 單元兩端：分段界線（路口中心線）與市民大道中心線之交點；Z8 東端為中心線終點
    k = int(z[1:])
    def hit(g):
        x = g.intersection(S.center)
        return x.centroid if not x.is_empty else S.center.interpolate(S.center.project(g.centroid))
    a = hit(CUT_G[k - 1]) if k - 1 < len(CUT_G) else Point(S.center.coords[-1])
    b = hit(CUT_G[k]) if k < len(CUT_G) else Point(S.center.coords[-1])
    return a, b

def key_map(fig, z, x_mm, y_mm, w_mm, h_mm):
    kx0, kx1 = 300990, 307330
    ka = fig.add_axes([x_mm / W, y_mm / Hh, w_mm / W, h_mm / Hh])
    sx = (kx1 - kx0) / w_mm
    ymid = S.center.interpolate(S.center.project(Point((kx0 + kx1) / 2, 2771100))).y
    ka.set_xlim(kx0, kx1); ka.set_ylim(ymid - h_mm / 2 * sx, ymid + h_mm / 2 * sx); ka.axis('off')
    vb = box(kx0, ymid - h_mm / 2 * sx, kx1, ymid + h_mm / 2 * sx)
    ka.add_collection(LineCollection(S.lines(S.road.boundary.intersection(vb)), colors='#c4c4c4', linewidths=.12))
    for z2 in S.ZONES_USE:
        ka.add_collection(PathCollection([S.poly_path(S.PZ(z2)['R'])], facecolors=S.ZONE_C if z2 == z else '#BFDDF0',
                                         edgecolors='none', zorder=2))
        c = S.PZ(z2)['R'].centroid; yb = S.center.interpolate(S.center.project(c)).y
        ka.text(c.x, yb - 230, z2, fontsize=(6.5 if z2 == z else 5.5) * F, ha='center', va='top', color=S.ZONE_C,
                fontweight='bold' if z2 == z else 'normal', path_effects=S.halo)
    ka.add_collection(LineCollection(S.lines(S.elev.intersection(vb)), colors='#111', linewidths=.5, zorder=3))
    return sx

def scalebar(fig, x_mm, y_mm, lens=None, fs=6.5):
    lens = lens or PROF['lens']; fs *= F
    for i in range(len(lens) - 1):
        a, b = lens[i] * m2mm, lens[i + 1] * m2mm
        fig.add_artist(plt.Rectangle(((x_mm + a) / W, y_mm / Hh), (b - a) / W, 1.6 * K / Hh, transform=fig.transFigure,
                                     facecolor='#111' if i % 2 == 0 else 'white', edgecolor='#111', lw=.5 * F))
    for L in lens:
        fig.text((x_mm + L * m2mm) / W, (y_mm + 2.6 * K) / Hh, f'{L}', fontsize=fs, ha='center', va='bottom')
    fig.text((x_mm + lens[-1] * m2mm + 3 * K) / W, y_mm / Hh, f'm　1:{SCALE:,}（{PAPER}）', fontsize=fs, va='bottom')

def summary(z):
    d = S.PZ(z); R = d['R']
    out = []
    sw = collections.defaultdict(list)
    for g, p in SDK['sw']:
        if (p['road'] or '').startswith('市民大道') and g.intersects(R) and g.intersection(R).area > 40:
            sw[p['side']].append(p['width'])
    for side in ('北側', '南側'):
        v = sw.get(side)
        out.append(f"市民大道{side}人行道（官方寬）：" + (f"{min(v):.1f}–{max(v):.1f} m" if v and min(v) != max(v) else f"{v[0]:.1f} m" if v else '無資料'))
    for kind, nm in (('arcade_official', '騎樓（官方路段）'), ('arcade_est', '騎樓（推估）')):
        L = sum(g.intersection(R).area for g, _ in SDK[kind] if g.intersects(R)) / 3.64
        out.append(f"{nm}臨街長：約 {L:,.0f} m")
    n_cw = sum(1 for g, _ in SDK['crosswalk'] if g.intersects(R))
    out.append(f"行人穿越線：{n_cw} 處（交工處圖資）")
    # 平面市民大道車道數（OSM），依行車方向
    dirs = collections.defaultdict(collections.Counter)
    for f in S.osm:
        p = f['properties']
        if f['geometry']['type'] != 'LineString' or not str(p.get('name', '')).startswith('市民大道') or p.get('bridge') == 'yes': continue
        if p.get('highway') not in ('tertiary', 'secondary', 'primary') or '巷' in p.get('name', ''): continue
        g = S.transform(S.tf, shape(f['geometry']))
        gi = g.intersection(R)
        if gi.length < 30: continue
        c = list(g.coords); dx = c[-1][0] - c[0][0]
        try: n = int(str(p.get('lanes', '')).split(';')[0])
        except ValueError: continue
        if p.get('oneway') == 'yes': dirs['往東' if dx > 0 else '往西'][n] += gi.length
        else: dirs['雙向'][n] += gi.length
    if dirs:
        out.append('平面市民大道車道（OSM）：' + '／'.join(f"{k} {v.most_common(1)[0][0]} 車道" for k, v in sorted(dirs.items())))
    return out

def legend(fig, x_mm, y_mm, ncol=3):
    plt.rcParams['hatch.color'] = S.BLD_DOT
    h = [Patch(facecolor=S.BLD_FC, edgecolor=S.BLD_EC, hatch='....', lw=.4, alpha=CTX_ALPHA, label='範圍外：市民大道前後段（同表現，淡化）'),
         Line2D([], [], color=S.ZONE_C, lw=1.2, ls=(0, (6, 3)), label='本張單元界線（路口中心線）')] + \
        S.base_handles() + S.detail_handles(SCALE) + S.photo_handles()
    fig.legend(handles=h, loc='upper left', bbox_to_anchor=(x_mm / W, y_mm / Hh),
               frameon=False, fontsize=6.0 * F, ncol=ncol, handlelength=2.3, handleheight=1.0, labelspacing=.55, columnspacing=1.2,
               borderaxespad=0)
    return -(-len(h) // ncol)

NOTE = ('資料：底圖 02_南京至仁愛擴幅_20261005 線稿（EPSG:3826）；人行道＝臺北市新工處人行道範圍（2026-01 更新檔，2026-09-09 下載）；'
        '標線型人行道、行人穿越線＝臺北市交工處圖資（2024）；樹穴、花圃＝新工處人行道固定設施物（2026-10 下載）；騎樓官方路段＝停管處「機車退出騎樓路段」（2026-10 下載，路段名稱含「騎樓」者）。\n'
        '騎樓推估：臨路貼齊（≤1.5 m）之建物沿道路境界向內 3.64 m（北市建管自治條例第 7 條）；官方註明「僅人行道」路段不畫；排除退縮地、公共設施及 >5,000 平方公尺建物。'
        '騎樓實際有無與深度須現勘。\n'
        '車道線：OSM lanes／oneway＋車道面（線稿道路面扣除人行道）每 3 m 剖面等分，路口斷開，非標線實測。橋面投影為推估。\n'
        '照片判讀補繪：依現場照片（~/Desktop/civic photo，iPhone 有 GPS；Sony 依路牌與地標判讀位置）判讀各單元柱型、分隔島植栽、機車停車列，'
        '並核實 OSM 候車亭、YouBike、公共藝術、舊鐵道引道；\n柱位依官方平均跨距 36.3 m（D028 市民大道主橋 5,802.5 m／160 孔）沿分隔島推估，非實測。'
        '照片判讀紀錄見 data/photos/photo_reading.csv。© OpenStreetMap contributors / ODbL｜政府資料開放授權條款第 1 版｜2026-10-07')


def wrap_note(txt, width_mm, fs):
    # 依可用寬度重新斷行（全形字寬≈字級，半形≈0.55 字級）
    lim = width_mm / (fs * 25.4 / 72)
    out = []
    for para in txt.replace('\n', '\n').split('\n'):
        line, w = '', 0.0
        for ch in para:
            cw = 1.0 if unicodedata.east_asian_width(ch) in ('W', 'F') else 0.55
            if w + cw > lim and line: out.append(line); line, w = '', 0.0
            line += ch; w += cw
        if line: out.append(line)
    return '\n'.join(out)

# ---------- 本頁引用照片（15_photo_refs.py）：地圖下方照片條＋地圖上 iPhone 拍攝點 ----------
PREF = json.load(open(H / 'data/photos/photo_refs_by_zone.json')) if (H / 'data/photos/photo_refs_by_zone.json').exists() else {}
PH_SRC = Path.home() / 'Desktop/civic photo'
PH_C = '#C2410C'           # 照片編號／拍攝點色
PG = 2.5 * K               # 照片間距
PCAP = 5.0 * F             # 照片說明（兩行）高
PAGE_PHOTOS = []           # 每頁：[(x, y, w, h（mm，左下原點）, 照片檔)]，存檔後以 PyMuPDF 嵌入 JPEG
def photo_grid(n, avail_h, width):
    for tw in [v * K for v in (56, 50, 44, 38, 33, 29, 25, 22, 19, 16)]:
        th = tw * 9 / 16
        cols = max(1, int((width + PG) // (tw + PG))); rows_ = -(-n // cols)
        need = 10 * F + rows_ * (th + PCAP + PG)
        if need <= avail_h: return tw, th, cols, rows_, need
    return None

def zone_map_h(z):
    d = S.PZ(z)
    return 2 * max(d['y1'] - d['yc'], d['yc'] - d['y0']) * m2mm + 8 * K

def fit_line(txt, width_mm, fs):
    lim = width_mm / (fs * 25.4 / 72); out, w = '', 0.0
    for ch in txt:
        cw = 1.0 if unicodedata.east_asian_width(ch) in ('W', 'F') else 0.55
        if w + cw > lim: return out.rstrip('・') + '…'
        out += ch; w += cw
    return out

def camera(ax, T, ang, x, y, hd, label, size_m):
    # 拍攝點：扇形（視角 ±28°）＋編號；方位角依本張轉正換算
    t = np.radians(hd - 0) ; v = np.array([np.sin(t), np.cos(t)])
    r_ = np.radians(-ang); v = np.array([v[0] * np.cos(r_) - v[1] * np.sin(r_), v[0] * np.sin(r_) + v[1] * np.cos(r_)])
    p = np.array(T(Point(x, y)).coords[0]); a0 = np.arctan2(v[1], v[0])
    arc = [p] + [p + size_m * np.array([np.cos(a0 + da), np.sin(a0 + da)]) for da in np.radians(np.linspace(-28, 28, 7))]
    ax.add_patch(plt.Polygon(arc, closed=True, facecolor=PH_C, edgecolor='white', lw=.3 * F, alpha=.85, zorder=13))
    if label:
        ax.text(p[0] - v[0] * size_m * .35, p[1] - v[1] * size_m * .35, label, fontsize=4.2 * F, color=PH_C, ha='center', va='center',
                fontweight='bold', zorder=13.5, path_effects=S.halo, clip_on=True)

# 圖面高度：各張一致，取各單元南北最大延伸之兩倍（大道中心線置於圖面垂直中心）

def build_page(pdf, z, png):
    d = S.PZ(z); zp = S.ZP[z]; T = d['T']; R = d['R']
    refs = PREF.get(z, [])
    PAGE_PHOTOS.append([])
    fig = plt.figure(figsize=(W * MM, Hh * MM))
    S.header(fig, f"{z}　{zp['from']}—{zp['to']}｜市民大道兩側第一排街廓詳細平面",
             f"{zp['info']}｜軸線 {zp['len_m']:,} m｜第一排街廓 北 {d['nside']['N']}・南 {d['nside']['S']}｜1:{SCALE:,}（{PAPER}，Z1–Z8 八張同比例）｜"
             f"本段置中，左右為市民大道前後段（淡化）｜依市民大道走向轉正，北向見指北", k=K, f=F)
    # 置中：兩端路口在中心線上之中點 → 圖面水平中心；該處中心線 → 垂直中心
    pa, pb = ends(z)
    ta, tb = sorted((S.center.project(pa), S.center.project(pb)))
    xa_, xb_ = T(pa).x, T(pb).x
    xc = (xa_ + xb_) / 2; yc = T(S.center.interpolate((ta + tb) / 2)).y
    top = Hh - 60 * K; bot = 24 * K + BAND
    # 地圖高依本段南北延伸（大道中心線置於地圖垂直中心）；有引用照片者地圖靠上，下方放照片條
    H_AX = min(zone_map_h(z), top - bot)
    grid = photo_grid(len(refs), top - bot - H_AX - 9 * K, MAP_X1 - MAP_X0) if refs else None
    y_ax = top - H_AX if grid else bot + (top - bot - H_AX) / 2
    wm = (MAP_X1 - MAP_X0) / m2mm / 2; hm = H_AX / m2mm / 2
    xlim, ylim = (xc - wm, xc + wm), (yc - hm, yc + hm)
    rect = [MAP_X0 / W, y_ax / Hh, (MAP_X1 - MAP_X0) / W, H_AX / Hh]
    view = box(xlim[0], ylim[0], xlim[1], ylim[1])
    # 底層：前後段（同表現、不標字），再覆白色半透明遮罩於本段範圍外
    axc = fig.add_axes(rect)
    vis = []
    for z2 in ALL_Z:
        if z2 == z: continue
        d2 = S.zone_in_frame(z2, T)
        if not T(d2['R']).intersects(view): continue
        S.draw_zone(axc, d2, lw=LWF, scale=SCALE, sw_labels=False, texts=False)
        vis.append(z2)
    veil = view.buffer(50).difference(T(R))
    axc.add_patch(PathPatch(S.poly_path(veil), facecolor='white', edgecolor='none', alpha=1 - CTX_ALPHA, zorder=50))
    axc.set_xlim(*xlim); axc.set_ylim(*ylim); axc.axis('off')
    # 上層：本段（原表現＋文字）
    ax = fig.add_axes(rect); ax.patch.set_alpha(0)
    S.draw_zone(ax, z, fs=F, lw=LWF, scale=SCALE, sw_labels=True)
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.axis('off')
    # 本段界線：路口中心線（藍虛線），圖上緣標路名
    k = int(z[1:])
    for g, nm, px in ((CUT_G[k - 1], zp['from'], xa_), (CUT_G[k] if k < len(CUT_G) else None, zp['to'], xb_)):
        if g is None:   # Z8 東端（基隆路，軸線終點）無路口中心線資料：垂直虛線
            ax.plot([px, px], ylim, color=S.ZONE_C, lw=1.0 * LWF, ls=(0, (6, 3)), zorder=12)
        if g is not None:
            ax.add_collection(LineCollection(S.lines(T(g)), colors=S.ZONE_C, linewidths=1.0 * LWF, linestyles=(0, (6, 3)), zorder=12))
            gv = T(g).intersection(view)   # 路名標在界線抵達圖框上緣處
            cs = [c for q in getattr(gv, 'geoms', [gv]) if not q.is_empty for c in q.coords]
            if cs: px = max(cs, key=lambda c: c[1])[0]
        fx = MAP_X0 + (px - xlim[0]) * m2mm
        fig.text(fx / W, (y_ax + H_AX + 2 * K) / Hh, nm, fontsize=8 * F, fontweight='bold', color=S.ZONE_C, ha='center', va='bottom')
    # 前後段標示（灰）
    for z2 in vis:
        a2, b2 = ends(z2)
        u0, u1 = sorted((T(a2).x, T(b2).x)); u0, u1 = max(u0, xlim[0]), min(u1, xlim[1])
        if (u1 - u0) * m2mm < 30: continue
        zp2 = S.ZP[z2]; fx = MAP_X0 + ((u0 + u1) / 2 - xlim[0]) * m2mm
        arrow = '← ' if (u0 + u1) / 2 < xc else ''
        arrow2 = ' →' if (u0 + u1) / 2 > xc else ''
        fig.text(fx / W, (y_ax - 3 * K) / Hh, f"{arrow}{z2}　{S.short(zp2['from'])}—{S.short(zp2['to'])}{arrow2}", fontsize=7 * F, color='#9a9a9a',
                 ha='center', va='top')
    fig.text((MAP_X0 + (xc - xlim[0]) * m2mm) / W, (y_ax - 3 * K) / Hh, f"{z}　本段", fontsize=8 * F, fontweight='bold', color=S.ZONE_C,
             ha='center', va='top')
    S.north(fig, MAP_X1 - 4 * K, top + 2 * K, d['ang'], size=8 * K, f=F)
    if refs and grid:
        n_gps = sum(1 for it in refs if it['gps'])
        # 拍攝點：相距 < 20 m 者同組，只標一次編號（例 4634–4637）
        gps = [it for it in refs if it['gps']]; groups = []
        for it in gps:
            g_ = next((g for g in groups if np.hypot(g[0]['x'] - it['x'], g[0]['y'] - it['y']) < 20), None)
            (g_.append(it) if g_ else groups.append([it]))
        for g_ in groups:
            ids = sorted(i['id'][-4:] for i in g_)
            lab = ids[0] if len(ids) == 1 else f"{ids[0]}–{ids[-1]}"
            for j, it in enumerate(g_):
                camera(ax, T, d['ang'], it['x'], it['y'], it['heading'], lab if j == 0 else None, 5 * K / m2mm)
        tw, th, cols, rows_, need = grid
        y0 = y_ax - 9 * K
        fig.text(MAP_X0 / W, y0 / Hh, f'本頁引用現場照片 {len(refs)} 張', fontsize=7.5 * F, fontweight='bold', va='top', color=PH_C)
        fig.text((MAP_X0 + 42 * F) / W, y0 / Hh,
                 (f'iPhone {n_gps} 張有 GPS，地圖上以橘色扇形＋編號末四碼標拍攝點與方向；' if n_gps else '') +
                 (f'Sony {len(refs) - n_gps} 張無 GPS（相機時鐘未設），依路牌、門牌、地標與拍攝序號判讀至路段，未標拍攝點；' if len(refs) > n_gps else '') +
                 '照片下方為編號與判讀用途｜來源 ~/Desktop/civic photo｜逐張紀錄 data/photos/photo_reading.csv',
                 fontsize=5.6 * F, va='top', color='#444')
        gy = y0 - 6.5 * F
        ncol = min(cols, len(refs)); used = ncol * tw + (ncol - 1) * PG
        x0g = MAP_X0 + (MAP_X1 - MAP_X0 - used) / 2
        for i, it in enumerate(refs):
            r_, c_ = divmod(i, cols)
            x = x0g + c_ * (tw + PG); ytop = gy - r_ * (th + PCAP + PG)
            fig.add_artist(plt.Rectangle((x / W, (ytop - th) / Hh), tw / W, th / Hh, transform=fig.transFigure, facecolor='#eeeeee',
                                         edgecolor='#999', lw=.3 * F))
            fig.text(x / W, (ytop - th - .6 * F) / Hh, it['id'] + ('　▲GPS' if it['gps'] else ''), fontsize=4.6 * F, color=PH_C,
                     fontweight='bold', va='top')
            fig.text(x / W, (ytop - th - 2.6 * F) / Hh, fit_line('・'.join(it['tags']), tw, 4.4 * F), fontsize=4.4 * F, color='#444', va='top')
            PAGE_PHOTOS[-1].append((x, ytop - th, tw, th, it['file']))
    elif refs:
        print(z, '照片條放不下', len(refs))
    # 資訊帶
    yb = 16 * K + BAND
    fig.add_artist(plt.Line2D([20 * K / W, (W - 20 * K) / W], [(yb + 3 * K) / Hh] * 2, transform=fig.transFigure, color='#999', lw=.5 * F))
    fig.text(22 * K / W, (yb - 3 * K) / Hh, '圖例', fontsize=8 * F, fontweight='bold', va='top')
    legend(fig, 22 * K, yb - 9 * K)
    kx, kw = 330 * K, 230 * K
    fig.text(kx / W, (yb - 3 * K) / Hh, f'索引｜{z} 位置（深藍）', fontsize=8 * F, fontweight='bold', va='top')
    key_map(fig, z, kx, yb - 62 * K, kw, 52 * K)
    scalebar(fig, kx, yb - 78 * K)
    sx = 580 * K
    fig.text(sx / W, (yb - 3 * K) / Hh, f'{z} 摘要', fontsize=8 * F, fontweight='bold', va='top')
    fig.text(sx / W, (yb - 10 * K) / Hh, '\n'.join(summary(z)), fontsize=6.4 * F, va='top', linespacing=1.6)
    fig.text(22 * K / W, 20 * K / Hh, wrap_note(NOTE, W - 44 * K, 5.3 * F), fontsize=5.3 * F, va='bottom', color='#444', linespacing=1.5)
    pdf.savefig(fig); plt.close(fig)

if __name__ == '__main__':
    out_dir = H / f'{PAPER}_八張_1-{SCALE}'; out_dir.mkdir(exist_ok=True)
    pdf_path = H / f"市民大道_Z1-Z8_第一排街廓詳細平面_八張_{PAPER}_1-{SCALE}_{PROF['date']}.pdf"
    pngs = [out_dir / f"{z}_{S.short(S.ZP[z]['from'])}-{S.short(S.ZP[z]['to'])}_1-{SCALE}_預覽.png" for z in S.ZONES_USE]
    tmp = pdf_path.with_suffix('.tmp.pdf')
    with PdfPages(tmp) as pdf:
        for z, png in zip(S.ZONES_USE, pngs):
            build_page(pdf, z, png)
            print(z, 'ok')
    # 照片以 JPEG 直接嵌入（保留 JPEG 壓縮，避免 PDF 過大）；預覽改由最終 PDF 轉出
    import fitz, io
    from PIL import Image, ImageOps
    doc = fitz.open(tmp); mmpt = 72 / 25.4
    for page, items in zip(doc, PAGE_PHOTOS):
        for x, y, w, h, f in items:
            im = Image.open(PH_SRC / f); im.draft('RGB', (int(w / 25.4 * 300) * 2, int(h / 25.4 * 300) * 2))
            im = ImageOps.exif_transpose(im).convert('RGB'); im.thumbnail((int(w / 25.4 * 300), int(h / 25.4 * 300)))
            buf = io.BytesIO(); im.save(buf, 'JPEG', quality=82)
            page.insert_image(fitz.Rect(x * mmpt, (Hh - y - h) * mmpt, (x + w) * mmpt, (Hh - y) * mmpt), stream=buf.getvalue(), keep_proportion=True)
    doc.save(pdf_path, garbage=3, deflate=True); doc.close(); tmp.unlink()
    doc = fitz.open(pdf_path)
    for page, png in zip(doc, pngs): page.get_pixmap(dpi=int(110 / K)).save(png)
    print(pdf_path.name, round(pdf_path.stat().st_size / 1e6, 1), 'MB')
