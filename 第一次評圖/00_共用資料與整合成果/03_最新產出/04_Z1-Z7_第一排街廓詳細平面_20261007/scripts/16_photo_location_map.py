# 照片位置圖（A3 橫式 2 頁，北向朝上）——現場照片 ~/Desktop/civic photo
#   P1 全線總圖 1:16000：iPhone 拍攝點（GPS，依 60 m 分群標編號區間與張數）＋ Sony 判讀路段（括線，依 photo_reading.csv）
#   P2 iPhone 拍攝點放大 1:4500（兩列）：每張扇形（拍攝方向、視角 ±28°），15 m 內同群列編號末四碼
import json, csv, collections, importlib.util
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.collections import LineCollection, PathCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from shapely.geometry import box, Point

H = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sheet', H / 'scripts/02_sheet.py')
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)   # 共用底圖資料、字型
S.VARIANT['full'] = True
W, Hh, MM = 420, 297, 1 / 25.4
PH_C = '#C2410C'; SONY_C = '#1D4ED8'; ZC = S.ZONE_C
rows = json.load(open(H / 'data/photos/photo_index.json'))
IP = [r for r in rows if 'x' in r]
RD = list(csv.DictReader(open(H / 'data/photos/photo_reading.csv', encoding='utf-8-sig')))
ZONES = S.ZONES_USE

def axes_mm(fig, x, y, w, h): return fig.add_axes([x / W, y / Hh, w / W, h / Hh])
def frame_page(fig, title, sub):
    fig.text(14 / W, 1 - 14 / Hh, title, fontsize=15, va='top')
    fig.text(14 / W, 1 - 22 / Hh, sub, fontsize=6.8, va='top', color='#444')
    fig.add_artist(plt.Rectangle((5 / W, 5 / Hh), (W - 10) / W, (Hh - 10) / Hh, transform=fig.transFigure, fill=False, lw=.6))
def scalebar(fig, x, y, scale, lens):
    m2mm = 1000 / scale
    for i in range(len(lens) - 1):
        a, b = lens[i] * m2mm, lens[i + 1] * m2mm
        fig.add_artist(plt.Rectangle(((x + a) / W, y / Hh), (b - a) / W, 1.2 / Hh, transform=fig.transFigure,
                                     facecolor='#111' if i % 2 == 0 else 'white', edgecolor='#111', lw=.4))
    for L in lens: fig.text((x + L * m2mm) / W, (y + 1.9) / Hh, f'{L}', fontsize=5, ha='center', va='bottom')
    fig.text((x + lens[-1] * m2mm + 2) / W, y / Hh, f'm　1:{scale:,}（A3）', fontsize=5, va='bottom')
def north(fig, x, y):
    fig.add_artist(matplotlib.patches.FancyArrowPatch((x / W, (y - 4) / Hh), (x / W, (y + 3) / Hh), transform=fig.transFigure,
                                                      arrowstyle='-|>', mutation_scale=6, color='#111', lw=.7))
    fig.text(x / W, (y + 5) / Hh, 'N', fontsize=5.5, ha='center', va='bottom')

def base(ax, view, fine):
    ax.add_collection(LineCollection(S.lines(S.road.boundary.intersection(view)), colors='#c8c8c8' if not fine else '#9a9a9a',
                                     linewidths=.12 if not fine else .2, zorder=1))
    if fine:
        b = [S.poly_path(p) for p in S.polys(S.bld.intersection(view))]
        ax.add_collection(PathCollection([q for q in b if q is not None], facecolors='#ececec', edgecolors='#b5b5b5', linewidths=.12, zorder=1.1))
    for z in ZONES:
        ax.add_collection(PathCollection([S.poly_path(S.PZ(z)['R'])], facecolors='#DCEBF7', edgecolors='none', zorder=.5))
    ax.add_collection(LineCollection(S.lines(S.elev.intersection(view)), colors='#333', linewidths=.6 if not fine else .5, zorder=2))
    # 分段界線
    for f in S.ZF:
        if 'cut' in f['properties']:
            from shapely.geometry import shape
            g = shape(f['geometry']).intersection(view)
            ax.add_collection(LineCollection(S.lines(g), colors=ZC, linewidths=.5, linestyles=(0, (4, 2)), zorder=2.2))

def clusters(items, dist):
    out = []
    for r in sorted(items, key=lambda r: (r['x'], r['y'])):
        g = next((g for g in out if min(np.hypot(q['x'] - r['x'], q['y'] - r['y']) for q in g) < dist), None)
        (g.append(r) if g else out.append([r]))
    return out
def id_range(g):
    ids = sorted(int(r['id'].split('_')[-1]) for r in g)
    return f"IMG_{ids[0]}" if len(ids) == 1 else f"IMG_{ids[0]}–{ids[-1]}"

def fan(ax, r, size_m, alpha=.85):
    h = np.radians(r['heading']); p = np.array([r['x'], r['y']])
    pts = [p] + [p + size_m * np.array([np.sin(h + da), np.cos(h + da)]) for da in np.radians(np.linspace(-28, 28, 7))]
    ax.add_patch(plt.Polygon(pts, closed=True, facecolor=PH_C, edgecolor='white', lw=.25, alpha=alpha, zorder=5))

# ---------- Sony：判讀路段 ----------
def sony_groups():
    G = collections.OrderedDict()
    for r in RD:
        if r['相機'] == 'iPhone 17 Pro': continue
        parts = r['檔案'].split('/'); fold = parts[1] if parts[1] == 'C' else parts[1] + '/' + parts[2]
        key = (fold, r['單元'], r['定位方式'])
        G.setdefault(key, []).append(Path(r['檔案']).stem)
    out = []
    for (fold, z, how), ids in G.items():
        ids.sort()
        located = how.startswith('內容判讀')
        out.append(dict(fold=fold, zone=z, how=how.replace('內容判讀：', ''), n=len(ids), first=ids[0], last=ids[-1], located=located))
    return out
def zone_xr(zs):
    xs = []
    for z in zs:
        if z in S.P_FULL or z in S.P:
            b = S.PZ(z)['R'].bounds; xs += [b[0], b[2]]
    return (min(xs), max(xs)) if xs else None

def page1(pdf):
    fig = plt.figure(figsize=(W * MM, Hh * MM))
    frame_page(fig, '現場照片位置圖｜全線總圖',
               f'~/Desktop/civic photo 原始照片 {len(rows)} 張：iPhone {len(IP)} 張（EXIF GPS，誤差約 10–15 m）以橘點標拍攝位置；'
               f'Sony {len(rows) - len(IP)} 張無 GPS、相機時鐘未設，依路牌／門牌／地標與拍攝序號判讀至路段（藍括線）｜北向朝上｜逐張紀錄 data/photos/photo_reading.csv')
    scale = 16000; m2mm = 1000 / scale
    x0, x1 = 300990, 307330; xc = (x0 + x1) / 2
    mw = (x1 - x0) * m2mm; mh = 78; mx = (W - mw) / 2; my = Hh - 32 - mh
    yc = 2770980
    view = box(xc - mw / 2 / m2mm, yc - mh / 2 / m2mm, xc + mw / 2 / m2mm, yc + mh / 2 / m2mm)
    ax = axes_mm(fig, mx, my, mw, mh); base(ax, view, False)
    ax.set_xlim(view.bounds[0], view.bounds[2]); ax.set_ylim(view.bounds[1], view.bounds[3]); ax.axis('off')
    for z in ZONES:   # 單元名
        R = S.PZ(z)['R']; c = R.centroid
        ax.text(c.x, min(R.bounds[3] + 40, view.bounds[3] - 120), z, fontsize=6.5, color=ZC, fontweight='bold', ha='center', va='bottom',
                zorder=6, path_effects=S.halo, clip_on=True)
    # iPhone 群
    CL = clusters(IP, 60)
    for k, g in enumerate(CL):
        xs = np.array([r['x'] for r in g]); ys = np.array([r['y'] for r in g])
        ax.scatter(xs, ys, s=4, c=PH_C, linewidths=0, zorder=5)
        cx, cy = xs.mean(), ys.mean(); up = k % 2 == 0
        ty = cy + (230 if up else -230) + (90 if (k // 2) % 2 else 0) * (1 if up else -1)
        ax.annotate(f"{id_range(g)}\n{len(g)} 張", (cx, cy), (cx, ty), fontsize=4.6, color=PH_C, ha='center',
                    va='bottom' if up else 'top', zorder=7, path_effects=S.halo,
                    arrowprops=dict(arrowstyle='-', color=PH_C, lw=.35, shrinkA=0, shrinkB=1.5))
    # Sony 括線（地圖下方，依路段分層）
    SG = [g for g in sony_groups() if g['located']]
    tiers = []
    yb = my - 6
    for g in sorted(SG, key=lambda g: zone_xr(g['zone'].split('–') if '–' not in g['zone'] else
                                               [f"Z{i}" for i in range(int(g['zone'].split('–')[0][1:]), int(g['zone'].split('–')[1][1:]) + 1)])[0]):
        zs = g['zone'].split('–'); zs = [f"Z{i}" for i in range(int(zs[0][1:]), int(zs[-1][1:]) + 1)]
        xr = zone_xr(zs); a, b = mx + (xr[0] - view.bounds[0]) * m2mm, mx + (xr[1] - view.bounds[0]) * m2mm
        t = next((i for i, e in enumerate(tiers) if e < a - 2), None)
        if t is None: tiers.append(b); t = len(tiers) - 1
        else: tiers[t] = b
        y = yb - t * 13
        fig.add_artist(Line2D([a / W, a / W, b / W, b / W], [(y + 1.5) / Hh, y / Hh, y / Hh, (y + 1.5) / Hh], transform=fig.transFigure,
                              color=SONY_C, lw=.6))
        fig.text(a / W, (y - 1.2) / Hh, f"{g['fold']}　{g['first']}–{g['last'][3:]}（{g['n']} 張）｜{g['zone']}", fontsize=5, color=SONY_C,
                 fontweight='bold', va='top')
        fig.text(a / W, (y - 4.4) / Hh, S_fit(g['how'], b - a + 30, 4.4), fontsize=4.4, color='#444', va='top')
    # 表：iPhone 依原資料夾（現場地點）
    ty = yb - len(tiers) * 13 - 8
    fig.text(14 / W, ty / Hh, 'iPhone 照片（依原資料夾＝拍攝地點）', fontsize=6.5, fontweight='bold', va='top', color=PH_C)
    byf = collections.OrderedDict()
    for r in sorted(IP, key=lambda r: r['id']): byf.setdefault(r['file'].split('/')[1], []).append(r)
    lines_ = [f"{f}：{len(v)} 張　{id_range(v)}　單元 {'、'.join(sorted({r.get('zone', '').rstrip('?') for r in v}))}" for f, v in byf.items()]
    fig.text(14 / W, (ty - 5) / Hh, '\n'.join(lines_), fontsize=5.2, va='top', linespacing=1.55)
    un = [g for g in sony_groups() if not g['located']]
    fig.text(215 / W, ty / Hh, 'Sony 未定位照片', fontsize=6.5, fontweight='bold', va='top', color=SONY_C)
    fig.text(215 / W, (ty - 5) / Hh, '\n'.join(f"{g['fold']}　{g['first']}–{g['last'][3:]}（{g['n']} 張）：{g['how']}" for g in un) +
             '\n夜間照片無路牌可辨，拍攝順序同白天路線，僅能歸到區段；未用於平面補繪。', fontsize=5.2, va='top', linespacing=1.55)
    scalebar(fig, 14, 9, scale, (0, 250, 500, 1000))
    north(fig, W - 12, Hh - 30)
    fig.legend(handles=[Line2D([], [], ls='none', marker='o', ms=3, mfc=PH_C, mec='none', label='iPhone 拍攝點（GPS）'),
                        Line2D([], [], color=SONY_C, lw=.8, label='Sony 判讀路段（無 GPS）'),
                        Patch(facecolor='#DCEBF7', edgecolor='none', label='Z1–Z8 第一排街廓範圍'),
                        Line2D([], [], color='#333', lw=.8, label='市民高架'), Line2D([], [], color=ZC, lw=.6, ls=(0, (4, 2)), label='單元界線')],
               loc='lower right', bbox_to_anchor=((W - 10) / W, 9 / Hh), frameon=False, fontsize=5.2, ncol=5, columnspacing=1.2, borderaxespad=0)
    pdf.savefig(fig); fig.savefig(H / '照片位置圖_P1_全線_預覽.png', dpi=200); plt.close(fig)

def S_fit(txt, wmm, fs):
    import unicodedata
    lim = wmm / (fs * 25.4 / 72); out, w = '', 0.0
    for ch in txt:
        cw = 1.0 if unicodedata.east_asian_width(ch) in ('W', 'F') else 0.55
        if w + cw > lim: return out + '…'
        out += ch; w += cw
    return out

def page2(pdf):
    fig = plt.figure(figsize=(W * MM, Hh * MM))
    frame_page(fig, '現場照片位置圖｜iPhone 拍攝點與方向',
               f'iPhone {len(IP)} 張（EXIF GPS＋方位角）：扇形＝拍攝位置與方向（視角約 ±28°），旁註編號末四碼（15 m 內同群合註）｜'
               'GPS 水平誤差約 10–15 m，位置為概略｜北向朝上')
    scale = 4500; m2mm = 1000 / scale
    rowsx = [(302100, 303580), (303580, 305060)]
    mw = (rowsx[0][1] - rowsx[0][0]) * m2mm; mh = 116
    mx = 12; ys = [Hh - 30 - mh, Hh - 30 - 2 * mh - 8]
    ycs = [2771013, 2770978]
    for (x0, x1), my, yc in zip(rowsx, ys, ycs):
        view = box(x0, yc - mh / 2 / m2mm, x1, yc + mh / 2 / m2mm)
        ax = axes_mm(fig, mx, my, mw, mh); base(ax, view, True)
        ax.add_patch(plt.Rectangle((view.bounds[0], view.bounds[1]), x1 - x0, view.bounds[3] - view.bounds[1], fill=False, lw=.4, zorder=9))
        ax.set_xlim(view.bounds[0], view.bounds[2]); ax.set_ylim(view.bounds[1], view.bounds[3]); ax.axis('off')
        for z in ZONES:
            R = S.PZ(z)['R']; c = R.centroid
            if view.contains(Point(c.x, view.bounds[3] - 10)) or view.contains(c):
                ax.text(c.x, view.bounds[3] - 8, z, fontsize=7, color=ZC, fontweight='bold', ha='center', va='top', zorder=8,
                        path_effects=S.halo, clip_on=True)
        inview = [r for r in IP if view.contains(Point(r['x'], r['y']))]
        SHOWN.update(r['id'] for r in inview)
        for r in inview: fan(ax, r, 9)
        for g in clusters(inview, 15):
            xs = np.array([r['x'] for r in g]); ys_ = np.array([r['y'] for r in g])
            ids = sorted(r['id'][-4:] for r in g)
            # 編號：每 4 個一行；放在群之北／南（避開大道中心線方向）
            lab = '\n'.join('・'.join(ids[i:i + 4]) for i in range(0, len(ids), 4))
            cx, cy = xs.mean(), ys_.mean()
            yaxis = S.center.interpolate(S.center.project(Point(cx, cy))).y
            up = cy >= yaxis
            nl = lab.count('\n') + 1
            if up and cy + 22 + nl * 6 > view.bounds[3]: up = False      # 靠圖框上緣：改標下方
            if not up and cy - 22 - nl * 6 < view.bounds[1]: up = True   # 靠圖框下緣：改標上方
            ax.annotate(lab, (cx, cy), (cx, cy + (22 if up else -22)), fontsize=4.6, color=PH_C, fontweight='bold', ha='center',
                        va='bottom' if up else 'top', zorder=10, path_effects=S.halo, clip_on=True,
                        arrowprops=dict(arrowstyle='-', color=PH_C, lw=.3, shrinkA=0, shrinkB=1))
    # 右側：資料夾對照
    lx = mx + mw + 6
    fig.text(lx / W, (Hh - 30) / Hh, '原資料夾（拍攝地點）', fontsize=6.5, fontweight='bold', va='top', color=PH_C)
    byf = collections.OrderedDict()
    for r in sorted(IP, key=lambda r: r['id']): byf.setdefault(r['file'].split('/')[1], []).append(r)
    yy = Hh - 36
    for f, v in byf.items():
        fig.text(lx / W, yy / Hh, f, fontsize=5.4, fontweight='bold', va='top'); yy -= 3.6
        fig.text(lx / W, yy / Hh, f"{len(v)} 張｜{id_range(v)}", fontsize=5, va='top', color='#444'); yy -= 6.5
    fig.legend(handles=[Patch(facecolor=PH_C, edgecolor='none', label='拍攝點＋方向（扇形）'),
                        Patch(facecolor='#ececec', edgecolor='#b5b5b5', lw=.3, label='建物'),
                        Patch(facecolor='#DCEBF7', edgecolor='none', label='第一排街廓範圍'),
                        Line2D([], [], color='#333', lw=.8, label='市民高架'), Line2D([], [], color=ZC, lw=.6, ls=(0, (4, 2)), label='單元界線')],
               loc='upper left', bbox_to_anchor=(lx / W, (yy - 4) / Hh), frameon=False, fontsize=5.2, borderaxespad=0, labelspacing=.7)
    scalebar(fig, lx, 18, scale, (0, 50, 100, 200))
    north(fig, W - 14, 40)
    pdf.savefig(fig); fig.savefig(H / '照片位置圖_P2_iPhone拍攝點_預覽.png', dpi=200); plt.close(fig)

SHOWN = set()
if __name__ == '__main__':
    out = H / '市民大道_現場照片位置圖_A3_20261009.pdf'
    with PdfPages(out) as pdf:
        page1(pdf); page2(pdf)
    miss = [r['id'] for r in IP if r['id'] not in SHOWN]
    print(out.name, 'P2 shown', len(SHOWN), '/', len(IP), 'missing', miss)
