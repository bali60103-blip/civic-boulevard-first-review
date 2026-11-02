# 主題圖：單元「重點建物」A1 一張（實驗：先做 Z1）
#   底圖只留：建物輪廓（02 線稿）＋市民高架分隔島（17 判定）；其他道路、人行道、車道線等全部不畫
#   範圍＝單元兩端分段界線之間（本段置中；界線外前後段淡化），重點建物依 17 之規則 A／B／C 上色、編號、標名，下方附判定表
import json, sys, importlib.util
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Patch, PathPatch
from matplotlib.collections import PathCollection, LineCollection
from matplotlib.lines import Line2D
from shapely.geometry import shape, box
from shapely.ops import unary_union

H = Path(__file__).resolve().parents[1]
ZONE = sys.argv[1] if len(sys.argv) > 1 else 'Z1'
_argv = sys.argv; sys.argv = [_argv[0], 'A1']          # 05 以 argv[1] 判讀紙張，主題圖固定 A1
spec = importlib.util.spec_from_file_location('sheets', H / 'scripts/05_sheets.py')
F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
sys.argv = _argv
S = F.S
SCALE, m2mm, W, Hh, MM = F.SCALE, F.m2mm, F.W, F.Hh, F.MM
DATA = json.load(open(H / f'data/{ZONE}_key_buildings_EPSG3826.geojson'))
FEAT = [(shape(f['geometry']), f['properties']) for f in DATA['features']]
SLAB = shape(DATA['slab'])
KEYS = sorted([(g, p) for g, p in FEAT if p['kind'] == 'key'], key=lambda gp: gp[1]['id'])
MED = [g for g, p in FEAT if p['kind'] == 'median']
GC = {'河岸門戶': '#2F6F9F', '北門古蹟群': '#B23A3A', '台北雙子星': '#E08A1E', '公共案件基地': '#6A4C93', '界面大型建物': '#7d7d7d'}
OUT_C, MED_FC, MED_EC = '#6b6b6b', '#D6D6D6', '#8a8a8a'
halo = [pe.withStroke(linewidth=2.2, foreground='white')]
PT = 72 / 25.4

def draw_keys(ax, T):
    for g, p in KEYS:
        c = GC[p['group']]; path = S.poly_path(T(g))
        if path is None: continue
        if p.get('site'):
            ax.add_patch(PathPatch(path, facecolor=c, alpha=.10, edgecolor='none', zorder=3))
            ax.add_patch(PathPatch(path, facecolor='none', edgecolor=c, lw=1.1, ls=(0, (5, 2.5)), zorder=6))
        elif p.get('planned'):
            ax.add_patch(PathPatch(path, facecolor=c, alpha=.30, edgecolor='none', zorder=4))
            ax.add_patch(PathPatch(path, facecolor='none', edgecolor=c, lw=.9, ls=(0, (3, 1.6)), zorder=6))
        elif p['tier'] == 'C':
            plt.rcParams['hatch.color'] = c; plt.rcParams['hatch.linewidth'] = .5
            ax.add_patch(PathPatch(path, facecolor='#E3E3E3', edgecolor=c, lw=.6, hatch='////', zorder=4))
        else:
            ax.add_patch(PathPatch(path, facecolor=c, edgecolor='#222', lw=.35, zorder=5))

def anchor(g):
    big = max(S.polys(g), key=lambda q: q.area)
    return big.representative_point()

def place_labels(fig, T, xlim, ylim, y_ax, H_AX):
    # 編號圓點放在建物上；名稱以 mm 座標做簡單避讓（8 方向、近→遠），遠者加引線
    to_mm = lambda x, y: (F.MAP_X0 + (x - xlim[0]) * m2mm, y_ax + (y - ylim[0]) * m2mm)
    fs = 7.0; ch = fs * .353 * .98; hgt = fs * .353 * 1.25
    pts = []
    for g, p in KEYS:
        a = T(anchor(g)); pts.append(to_mm(a.x, a.y))
    boxes = [(x - 2.4, y - 2.4, x + 2.4, y + 2.4) for x, y in pts]   # 圓點本身
    def free(b):
        if b[0] < F.MAP_X0 + 1 or b[2] > F.MAP_X1 - 1 or b[1] < y_ax + 1 or b[3] > y_ax + H_AX - 1: return False
        return all(b[2] < o[0] or b[0] > o[2] or b[3] < o[1] or b[1] > o[3] for o in boxes)
    out = []
    for (g, p), (x, y) in zip(KEYS, pts):
        txt = p['name']; wl = len(txt) * ch
        done = None
        for r in (3.6, 8, 14, 20, 28):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)):
                cx, cy = x + dx * r, y + dy * r * .8
                bx0 = cx if dx > 0 else (cx - wl if dx < 0 else cx - wl / 2)
                b = (bx0, cy - hgt / 2, bx0 + wl, cy + hgt / 2)
                if free(b): done = (b, cx, cy, dx, r); break
            if done: break
        if not done:
            b = (x + 3.6, y - hgt / 2, x + 3.6 + wl, y + hgt / 2); done = (b, x + 3.6, y, 1, 3.6)
        boxes.append(done[0]); out.append(((x, y), done, txt, p))
    for (x, y), (b, cx, cy, dx, r), txt, p in out:
        c = GC[p['group']]
        if r > 4:
            fig.add_artist(plt.Line2D([x / W, ((b[0] if dx >= 0 else b[2]) if dx != 0 else (b[0] + b[2]) / 2) / W],
                                      [y / Hh, cy / Hh], transform=fig.transFigure, color=c, lw=.5, zorder=20))
        fig.text(b[0] / W, cy / Hh, txt, fontsize=7.0, va='center', ha='left', color='#111',
                 fontweight='bold' if p['tier'] == 'A' else 'normal', path_effects=halo, zorder=21)
        fig.add_artist(plt.Circle((x / W, y / Hh), 0, transform=fig.transFigure))
        fig.text(x / W, y / Hh, str(p['id']), fontsize=6.4, ha='center', va='center', color='white', fontweight='bold', zorder=23,
                 bbox=dict(boxstyle='circle,pad=0.22', fc=c, ec='white', lw=.6))

def handles():
    plt.rcParams['hatch.color'] = GC['界面大型建物']; plt.rcParams['hatch.linewidth'] = .5
    return [Line2D([], [], color=OUT_C, lw=.6, label='建物輪廓（線稿）'),
            Patch(facecolor=MED_FC, edgecolor=MED_EC, lw=.4, label='市民高架分隔島（橋面投影下或高架車道中心線 18 m 內之島塊）'),
            Line2D([], [], color=S.ZONE_C, lw=1.0, ls=(0, (6, 3)), label='單元界線（路口中心線）'),
            Patch(facecolor='#f0f0f0', edgecolor='#cfcfcf', lw=.4, label='界線外：市民大道前後段（淡化）'),
            Patch(facecolor=GC['河岸門戶'], edgecolor='#222', lw=.3, label='A 主角構成｜河岸門戶'),
            Patch(facecolor=GC['北門古蹟群'], edgecolor='#222', lw=.3, label='A 主角構成｜北門古蹟群'),
            Patch(facecolor=GC['台北雙子星'], edgecolor='#222', lw=.3, label='A 主角構成｜台北雙子星（交通樞紐）'),
            Patch(facecolor=(.18, .44, .62, .3), edgecolor=GC['河岸門戶'], lw=.8, ls=(0, (3, 1.6)), label='規劃中（B02 跨堤橋，描繪）'),
            Patch(facecolor=(.42, .30, .58, .1), edgecolor=GC['公共案件基地'], lw=1.0, ls=(0, (5, 2.5)), label='B 公共案件基地（公辦都更範圍）'),
            Patch(facecolor='#E3E3E3', edgecolor=GC['界面大型建物'], lw=.5, hatch='////', label='C 界面大型建物（第一排 120 m 內，> 2,500 平方公尺）')]

def table(fig, x, y, rows, widths, fs=8.0, lh=6.6, head=None, colors=None):
    yy = y
    if head:
        xx = x
        for t, w_ in zip(head, widths):
            fig.text(xx / W, yy / Hh, t, fontsize=fs + .3, fontweight='bold', va='top', color='#333'); xx += w_
        yy -= lh
        fig.add_artist(plt.Line2D([x / W, (x + sum(widths)) / W], [(yy + 1.2) / Hh] * 2, transform=fig.transFigure, color='#999', lw=.4))
    for i, r in enumerate(rows):
        xx = x
        for j, (t, w_) in enumerate(zip(r, widths)):
            fig.text(xx / W, yy / Hh, t, fontsize=fs, va='top', color=colors[i][j] if colors else '#222'); xx += w_
        yy -= lh
    return yy

NOTE = ['判定規則（依 市民高架沿線_設計介入單元分段_workflow_20261009_修訂1）：',
        'A 主角構成＝workflow 三「現行分段」本單元主角，及四「修訂紀錄」為不切穿基地而移動刀位所保護者（四-1 B02、西寧國宅；四-2 雙子星）。',
        'B 公共案件基地＝workflow 二-2 疊合之公共案件（公辦都更）。',
        'C 界面大型建物＝workflow 一-3 界面指標：第一排街廓、距高架軸線 120 m 內、建築面積 > 2,500 平方公尺，未列入 A、B 者。',
        '範圍＝兩端分段界線之間；北門古蹟群、西寧國宅位於第一排之後（距軸線 200–370 m），屬單元主角仍列入。',
        '未列入：高樓（海關大樓 25 層、一邸亞昕華威 29 層等）非 workflow 判定指標且面積 < 2,500 平方公尺；捷運北門站、台北地下街為地下設施，',
        '  無地面輪廓；福聚宮等不屬主角類型。',
        '底圖：建物輪廓＝02_南京至仁愛擴幅 線稿；分隔島＝整合後道路面以外之島塊（其他道路、人行道、車道線不畫）。',
        '限制：古蹟等級依 OSM 標籤（heritage=2 國定古蹟；historic=monument／building），未逐一比對文化部文化資產公告；',
        '  B02 為水利處規劃配置圖描繪，非核定界線；紙本黃色標記（重點基地／沿街立面）未取得，待使用者核對。',
        '© OpenStreetMap contributors / ODbL｜2026-10-11']

def build(pdf, png):
    z = ZONE; d = S.PZ(z); zp = S.ZP[z]; T = d['T']
    fig = plt.figure(figsize=(W * MM, Hh * MM))
    fig.add_artist(plt.Rectangle((10 / W, 10 / Hh), (W - 20) / W, (Hh - 20) / Hh, transform=fig.transFigure, fill=False, lw=.8))
    nA = sum(1 for _, p in KEYS if p['tier'] == 'A'); nB = sum(1 for _, p in KEYS if p['tier'] == 'B'); nC = len(KEYS) - nA - nB
    fig.text(28 / W, 1 - 30 / Hh, f"{z}　{zp['from']}—{zp['to']}｜重點建物（實驗）", fontsize=20, va='top')
    fig.text(28 / W, 1 - 41 / Hh, f"1:{SCALE:,}（A1）｜底圖：建物輪廓＋市民高架分隔島｜本段置中，界線外為前後段（淡化）｜主角：{zp['info']}",
             fontsize=8.5, va='top', color='#444')
    fig.text(28 / W, 1 - 50 / Hh, f"重點建物 {len(KEYS)} 項：A 主角構成 {nA}・B 公共案件基地 {nB}・C 界面大型建物 {nC}",
             fontsize=10.5, va='top', color='#222', fontweight='bold')
    F.key_map(fig, z, 600, Hh - 50, 221, 32)
    S.north(fig, W - 16, Hh - 66, d['ang'], size=7)
    # 地圖範圍：水平置中於單元兩端；垂直涵蓋第一排範圍與所有重點建物
    pa, pb = F.ends(z); xa_, xb_ = T(pa).x, T(pb).x; xc = (xa_ + xb_) / 2
    cont = T(unary_union([d['R']] + [g for g, _ in KEYS]))
    y0, y1 = cont.bounds[1] - 25, cont.bounds[3] + 25
    H_AX = min((y1 - y0) * m2mm, Hh - 64 - 175)
    yc_ = (y0 + y1) / 2; hm = H_AX / m2mm / 2
    wm = (F.MAP_X1 - F.MAP_X0) / m2mm / 2
    xlim, ylim = (xc - wm, xc + wm), (yc_ - hm, yc_ + hm)
    y_ax = Hh - 64 - H_AX
    rect = [F.MAP_X0 / W, y_ax / Hh, (F.MAP_X1 - F.MAP_X0) / W, H_AX / Hh]
    view = box(xlim[0], ylim[0], xlim[1], ylim[1])
    wb = box(*SLAB.buffer(1100).bounds)
    axc = fig.add_axes(rect)
    axc.add_collection(PathCollection([q for q in (S.poly_path(T(g)) for g in MED) if q is not None], facecolors=MED_FC,
                                      edgecolors=MED_EC, linewidths=.35, zorder=1))
    axc.add_collection(LineCollection(S.lines(T(S.bld.intersection(wb).boundary)), colors=OUT_C, linewidths=.3, zorder=2))
    axc.add_patch(PathPatch(S.poly_path(view.buffer(50).difference(T(SLAB))), facecolor='white', edgecolor='none', alpha=1 - F.CTX_ALPHA, zorder=50))
    axc.set_xlim(*xlim); axc.set_ylim(*ylim); axc.axis('off')
    ax = fig.add_axes(rect); ax.patch.set_alpha(0)
    draw_keys(ax, T)
    k = int(z[1:])
    for g, nm, px in ((F.CUT_G[k - 1], zp['from'], xa_), (F.CUT_G[k] if k < len(F.CUT_G) else None, zp['to'], xb_)):
        if g is not None:
            ax.add_collection(LineCollection(S.lines(T(g)), colors=S.ZONE_C, linewidths=1.0, linestyles=(0, (6, 3)), zorder=12))
            gv = T(g).intersection(view)
            cs = [c for q in getattr(gv, 'geoms', [gv]) if not q.is_empty for c in q.coords]
            if cs: px = max(cs, key=lambda c: c[1])[0]
        fig.text((F.MAP_X0 + (px - xlim[0]) * m2mm) / W, (y_ax + H_AX + 1.5) / Hh, nm, fontsize=8, fontweight='bold', color=S.ZONE_C,
                 ha='center', va='bottom')
    ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.axis('off')
    place_labels(fig, T, xlim, ylim, y_ax, H_AX)
    F.scalebar(fig, F.MAP_X0 + 2, y_ax - 8)
    # 下方：判定表、圖例、說明
    top = y_ax - 15
    fig.add_artist(plt.Line2D([20 / W, (W - 20) / W], [(top + 4) / Hh] * 2, transform=fig.transFigure, color='#999', lw=.5))
    fig.text(22 / W, top / Hh, '重點建物判定表', fontsize=11, fontweight='bold', va='top', color='#111')
    rows, colr = [], []
    for g, p in KEYS:
        rows.append([str(p['id']), p['name'], f"{p['tier']} {p['group']}", p['rule'], ''])
        rows.append(['', '', '', '　' + p['note'], ''])
        c = GC[p['group']]
        colr.append([c, '#111', c, '#222', '#555']); colr.append(['#555'] * 5)
    table(fig, 22, top - 9, rows, [8, 60, 32, 176, 0], head=['編號', '名稱', '類別', '依據（workflow 條號）／說明（灰）', ''], colors=colr,
          fs=7.4, lh=4.75)
    lx = 22 + 8 + 60 + 32 + 176 + 24   # 判定表右側
    fig.text(lx / W, top / Hh, '圖例', fontsize=11, fontweight='bold', va='top', color='#111')
    fig.legend(handles=handles(), loc='upper left', bbox_to_anchor=(lx / W, (top - 7) / Hh), frameon=False, fontsize=7.6, ncol=1,
               handlelength=2.4, handleheight=1.0, labelspacing=.5, borderaxespad=0)
    fig.text(lx / W, (top - 82) / Hh, '\n'.join(NOTE), fontsize=6.3, va='top', color='#444', linespacing=1.55)
    pdf.savefig(fig); fig.savefig(png, dpi=110); plt.close(fig)

if __name__ == '__main__':
    out = H / '主題圖_重點建物'; out.mkdir(exist_ok=True)
    zp = S.ZP[ZONE]; stem = f"{ZONE}_{S.short(zp['from'])}-{S.short(zp['to'])}_重點建物_A1_1-{SCALE}"
    with PdfPages(out / f'{stem}.pdf') as pdf:
        build(pdf, out / f'{stem}_預覽.png')
    print(stem)
