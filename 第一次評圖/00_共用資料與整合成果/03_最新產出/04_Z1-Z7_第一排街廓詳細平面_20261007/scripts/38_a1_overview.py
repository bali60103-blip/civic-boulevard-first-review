# A1 全段圖（2026-10-13 使用者：「做一張 A1，Z1–Z8 全段都要進到圖面，整理一張共用的圖例」）
#   比例尺：Z1–Z8 範圍內內容（第一排範圍＋特性建築 ∩ 單元界線）世界座標外包 6,184 × 1,180 m；北向上（最佳旋轉僅省約 2%，不採用）
#     → A1 圖框內寬 821 mm 下取 1:8,000（地圖 788 × 236 mm：東西含 60 m 邊界、南北取底圖資料全幅以填滿圖面）。
#   繪製：逐單元載入 20（各自之資料、碎塊補齊、拆除建物、主題色），依高程順序逐圖層繪製，每一圖層以該單元界線範圍剪裁
#     （Z1 含其西側、Z8 含其東側；Z6 跨界場所〔八德市場〕歸 Z6）；全段不淡化，Z1 以西、Z8 以東淡化。
#   圖面下方：各單元標示（範圍、主角、特性建築判準）與 36 共用圖例。
import sys, importlib.util
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, PathPatch, FancyArrowPatch
from shapely.geometry import box
from shapely.ops import unary_union

H = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('legend36', H / 'scripts/36_shared_legend.py'); LG = importlib.util.module_from_spec(spec); spec.loader.exec_module(LG)
ZS = ['Z%d' % i for i in range(1, 9)]
SCALE1 = 8000; M2MM = 1000 / SCALE1
FW, FH, MM = 841, 594, 1 / 25.4
VIEW_W = box(301030 - 60, 2770000 + 10, 307214 + 60, 2771910 - 10)      # 世界座標（EPSG:3826）；南北取底圖資料全幅，以周邊脈絡填滿 A1
MAP_W, MAP_H = (VIEW_W.bounds[2] - VIEW_W.bounds[0]) * M2MM, (VIEW_W.bounds[3] - VIEW_W.bounds[1]) * M2MM
MAP_X0, MAP_TOP = (FW - MAP_W) / 2, FH - 64
CRIT = LG.CRIT

def main():
    mods = {z: LG.load20(z) for z in ZS}
    N1 = mods['Z1']; S, F = N1.S, N1.F
    T = lambda g: g                                   # 北向上：世界座標直接繪製
    slab = {z: mods[z].SLAB.intersection(VIEW_W) for z in ZS}
    outside = VIEW_W.difference(unary_union(list(slab.values())))
    cx1 = slab['Z1'].centroid.x
    west = unary_union([p for p in S.polys(outside) if p.centroid.x < cx1]); east = unary_union([p for p in S.polys(outside) if p.centroid.x >= cx1])
    um = {z: unary_union([g for g, p in mods[z].CHAR if p.get('unmask')]) for z in ZS}
    clip = {}
    for z in ZS:
        c = slab[z]
        if z == 'Z1': c = c.union(west)
        if z == 'Z8': c = c.union(east)
        if not um[z].is_empty: c = c.union(um[z])
        for z2 in ZS:
            if z2 != z and not um[z2].is_empty: c = c.difference(um[z2])
        clip[z] = c.buffer(0)
    # 圖層總順序（各單元 LAYERS 皆為同一範本之子集）
    master = []
    for z in ZS:
        for k, _ in mods[z].LAYERS:
            if k not in master: master.append(k)
    keys = [k for k in master if k not in ('MASK', 'CUT', 'TEXT')]
    fig = plt.figure(figsize=(FW * MM, FH * MM))
    ax = fig.add_axes([MAP_X0 / FW, (MAP_TOP - MAP_H) / FH, MAP_W / FW, MAP_H / FH]); ax.patch.set_alpha(0)
    b = VIEW_W.bounds
    for k in keys:
        for z in ZS:
            N = mods[z]
            if k not in [kk for kk, _ in N.LAYERS]: continue
            n0 = (len(ax.collections), len(ax.patches), len(ax.lines))
            N.draw_layer(ax, k, T, box(*clip[z].buffer(30).bounds), VIEW_W)
            cp = PathPatch(S.poly_path(clip[z]), transform=ax.transData, facecolor='none', edgecolor='none')
            for a in ax.collections[n0[0]:] + ax.patches[n0[1]:] + ax.lines[n0[2]:]: a.set_clip_path(cp)
    fade = west.union(east)
    ax.add_patch(PathPatch(S.poly_path(fade), facecolor='white', edgecolor='none', alpha=1 - F.CTX_ALPHA, zorder=1))
    for z in ZS: mods[z].draw_layer(ax, 'CUT', T, VIEW_W, VIEW_W)
    ax.set_xlim(b[0], b[2]); ax.set_ylim(b[1], b[3]); ax.set_aspect('equal'); ax.axis('off')
    # 圖框、標題
    fig.add_artist(Rectangle((10 / FW, 10 / FH), (FW - 20) / FW, (FH - 20) / FH, transform=fig.transFigure, fill=False, lw=.8))
    fig.text(MAP_X0 / FW, 1 - 28 / FH, 'Z1–Z8 全段｜影響南北通行之元素與特性建築', fontsize=22, va='top')
    fig.text(MAP_X0 / FW, 1 - 41 / FH, f'市民大道（淡水河堤—基隆路）｜1:{SCALE1:,}（A1）｜北向上｜各單元依其判準標示特性建築；色彩全八張統一（同一顏色只代表一種意義），'
             '見下方共用圖例｜圖層依高程排列（B2 → B1 → 地面 → 天橋 → 高架）', fontsize=9, va='top', color='#555')
    # 比例尺、指北（右上）
    lens = (0, 100, 200, 500, 1000); sx, sy = FW - 28 - lens[-1] * M2MM - 24, MAP_TOP + 6
    for i in range(len(lens) - 1):
        a_, b_ = lens[i] * M2MM, lens[i + 1] * M2MM
        fig.add_artist(Rectangle(((sx + a_) / FW, sy / FH), (b_ - a_) / FW, 1.8 / FH, transform=fig.transFigure, facecolor='#111' if i % 2 == 0 else 'white', edgecolor='#111', lw=.5))
    for L in lens: fig.text((sx + L * M2MM) / FW, (sy + 2.8) / FH, f'{L}', fontsize=7.5, ha='center', va='bottom')
    fig.text((sx + lens[-1] * M2MM + 3) / FW, sy / FH, 'm', fontsize=7.5, va='bottom')
    fig.add_artist(FancyArrowPatch(((FW - 18) / FW, (sy - 1) / FH), ((FW - 18) / FW, (sy + 9) / FH), transform=fig.transFigure, arrowstyle='-|>', mutation_scale=9, color='#111', lw=.9))
    fig.text((FW - 18) / FW, (sy + 12.5) / FH, 'N', fontsize=8, ha='center', va='center')
    # 各單元標示：置於地圖下方、對齊各單元軸線中點
    yb = MAP_TOP - MAP_H - 5
    for z in ZS:
        N = mods[z]; zp = S.ZP[z]; pa, pb = F.ends(z)
        xa, xb = sorted(((pa.x - b[0]) * M2MM + MAP_X0, (pb.x - b[0]) * M2MM + MAP_X0))
        wmm = xb - xa; xc = (xa + xb) / 2; mw = max(8, (wmm - 4) / 2.6)
        fig.add_artist(plt.Line2D([(xa + 1) / FW, (xb - 1) / FW], [(yb + 2) / FH] * 2, transform=fig.transFigure, color=S.ZONE_C, lw=1.2))
        y = yb - 1.5
        fig.text(xc / FW, y / FH, f"{z}　{S.short(zp['from'])}—{S.short(zp['to'])}", fontsize=9.5, fontweight='bold', ha='center', va='top', color=S.ZONE_C); y -= 5.8
        for lab, t in (('主角', zp['info']), ('特性建築', CRIT[z])):
            for i, ln in enumerate(N1.wrap_w(f'{lab}：{t}', mw)):
                fig.text(xc / FW, y / FH, ln, fontsize=7.2, ha='center', va='top', color='#333' if lab == '主角' else '#8E1B3E'); y -= 3.9
            y -= 1.0
    # 共用圖例
    ytop = yb - 44
    fig.text(MAP_X0 / FW, ytop / FH, '共用圖例（Z1–Z8）', fontsize=15, fontweight='bold', va='top'); ytop -= 12
    LG.draw(fig, N1, MAP_X0, ytop, FW, FH, fs=14, col_w=250, ncols=3, unit_x=222, gap=19)
    out = H / '主題圖_南北通行因素與特性建築' / f'Z1-Z8_全段_南北通行因素與特性建築_A1_1-{SCALE1}.pdf'
    with PdfPages(out) as pdf: pdf.savefig(fig)
    fig.savefig(str(out).replace('.pdf', '_預覽.png'), dpi=110); plt.close(fig)
    print(out.name, f'map {MAP_W:.0f} × {MAP_H:.0f} mm')

if __name__ == '__main__':
    main()
