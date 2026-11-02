# A3 各單元主題圖（2026-10-13 使用者：「先把 Z1 做 A3 的版本，盡量不要縮小比例尺、以填滿整個空間為主，但要確保 Z2–Z8 的範圍都能塞進圖面」）
#   比例尺：八單元共用，取「各單元範圍內內容（第一排範圍＋特性建築，限單元界線內）於轉正座標之外包」能放進 A3 地圖區之最大比例尺。
#     A3 地圖區 400 × 252 mm（圖框 10 mm、下緣資訊帶 25 mm）；Z7 最寬（1,644 m）→ 1:4,110 以上 → 取 1:4,200（Z7 391 mm 寬）；
#     1:4,000 需 411 mm，超出 A3 安全邊距。其餘單元同比例下皆有餘裕（Z1 267 × 133 mm）。
#   圖面：同 A1（20 draw_layer 逐圖層、依高程排列、單元外淡化、單元界線）；地圖填滿圖框，置中於本段範圍內內容；
#     下緣資訊帶：標題、比例尺、指北、索引圖；圖例見 36 共用圖例（色彩全八張統一）。
#   python3 scripts/37_a3_sheets.py Z1 [Z2 …]
import sys, importlib.util
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, FancyArrowPatch
from shapely.geometry import box, LineString
from shapely.ops import unary_union

H = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('legend36', H / 'scripts/36_shared_legend.py'); LG = importlib.util.module_from_spec(spec); spec.loader.exec_module(LG)
SCALE3 = 4200; M2MM = 1000 / SCALE3
W3, H3, MM = 420, 297, 1 / 25.4
STRIP_H, KEY_W = 25, 66                          # 下緣資訊帶高；索引圖寬（高約 12.75 mm → 上下各留白約 6 mm；使用者 2026-10-13 指定 5–8 mm）
MX0, MX1, MY0, MY1 = 10, 410, 10 + STRIP_H, 287   # 地圖區（mm，自下）
OUT = H / '主題圖_南北通行因素與特性建築' / f'A3_1-{SCALE3}'

def frame(N, z):
    # 置中於本段範圍內內容（第一排範圍＋特性建築 ∩ 單元界線內）；上下不超出底圖資料範圍
    d = N.S.PZ(z); T = d['T']
    cont = unary_union([d['R']] + [g for g, p in N.CHAR if not p.get('site') and not p.get('adj')]).intersection(N.SLAB)
    b = T(cont).bounds; xc, yc = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    hw, hh = (MX1 - MX0) / 2 / M2MM, (MY1 - MY0) / 2 / M2MM
    TF = T(box(300935, 2770000, 307545, 2771910)); tops, bots = [], []
    for xx in np.linspace(b[0], b[2], 12):
        seg = TF.intersection(LineString([(xx, -1e5), (xx, 1e5)]))
        if not seg.is_empty: tops.append(seg.bounds[3]); bots.append(seg.bounds[1])
    if tops and min(tops) - max(bots) > 2 * hh: yc = min(max(yc, max(bots) + hh), min(tops) - hh)
    assert b[2] - b[0] <= 2 * hw and b[3] - b[1] <= 2 * hh, f'{z} 範圍放不進 A3 1:{SCALE3}'
    return (xc - hw, xc + hw), (yc - hh, yc + hh), T

def scalebar(fig, x, y, lens=(0, 50, 100, 200, 400), fs=6.5):
    for i in range(len(lens) - 1):
        a, b = lens[i] * M2MM, lens[i + 1] * M2MM
        fig.add_artist(Rectangle(((x + a) / W3, y / H3), (b - a) / W3, 1.4 / H3, transform=fig.transFigure,
                                 facecolor='#111' if i % 2 == 0 else 'white', edgecolor='#111', lw=.5))
    for L in lens: fig.text((x + L * M2MM) / W3, (y + 2.2) / H3, f'{L}', fontsize=fs, ha='center', va='bottom')
    fig.text((x + lens[-1] * M2MM + 3) / W3, y / H3, f'm　1:{SCALE3:,}（A3）', fontsize=fs, va='bottom')

def north(fig, x, y, ang, size=7):
    t = np.radians(-ang); v = np.array([-np.sin(t), np.cos(t)]); c = np.array([x, y])
    a, b = c - v * size / 2, c + v * size / 2
    fig.add_artist(FancyArrowPatch(a / [W3, H3], b / [W3, H3], transform=fig.transFigure, arrowstyle='-|>', mutation_scale=7, color='#111', lw=.8))
    fig.text((b[0] + v[0] * 2.4) / W3, (b[1] + v[1] * 2.4) / H3, 'N', fontsize=6.5, ha='center', va='center')

def build(z):
    N = LG.load20(z); zp = N.S.ZP[z]
    xlim, ylim, T = frame(N, z)
    fig = plt.figure(figsize=(W3 * MM, H3 * MM))
    rect = [MX0 / W3, MY0 / H3, (MX1 - MX0) / W3, (MY1 - MY0) / H3]
    view = box(xlim[0], ylim[0], xlim[1], ylim[1]); wb = box(*N.SLAB.buffer(1500).bounds)
    for k_, _ in N.LAYERS:
        if k_ == 'TEXT': continue
        ax = fig.add_axes(rect); ax.patch.set_alpha(0)
        N.draw_layer(ax, k_, T, wb, view)
        ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.axis('off')
    # 圖框與下緣資訊帶
    fig.add_artist(Rectangle((MX0 / W3, 10 / H3), (MX1 - MX0) / W3, (H3 - 20) / H3, transform=fig.transFigure, fill=False, lw=.8))
    fig.add_artist(plt.Line2D([MX0 / W3, MX1 / W3], [MY0 / H3] * 2, transform=fig.transFigure, color='#111', lw=.5))
    ym = 10 + STRIP_H / 2                     # 資訊帶垂直中線
    fig.text(14 / W3, (ym + 3.2) / H3, f"{z}　{zp['from']}—{zp['to']}｜影響南北通行之元素與特性建築", fontsize=11.5, va='center')
    fig.text(14 / W3, (ym - 3.6) / H3, f"主角：{zp['info']}｜1:{SCALE3:,}（A3；Z1–Z8 同比例）｜圖層依高程排列｜圖例見「Z1–Z8 共用圖例」",
             fontsize=5.6, va='center', color='#555')
    scalebar(fig, 168, ym - 2.4)
    north(fig, 300, ym, N.S.PZ(z)['ang'])
    N.W, N.Hh = W3, H3                          # 索引圖：沿用 20 key_map_full（以本頁尺寸定位）
    _f = plt.figure(); kh = N.key_map_full(_f, z, 0, None, KEY_W, bottom_mm=0); plt.close(_f)   # 先量索引圖高，再於資訊帶內上下置中
    N.key_map_full(fig, z, MX1 - 2 - KEY_W, None, KEY_W, bottom_mm=10 + (STRIP_H - kh) / 2)
    print(f'  索引圖高 {kh:.2f} mm，上下留白各 {(STRIP_H - kh) / 2:.2f} mm')
    stem = f"{z}_{N.S.short(zp['from'])}-{N.S.short(zp['to'])}_南北通行因素與特性建築_A3_1-{SCALE3}"
    OUT.mkdir(parents=True, exist_ok=True)
    with PdfPages(OUT / f'{stem}.pdf') as pdf: pdf.savefig(fig)
    fig.savefig(OUT / f'{stem}_預覽.png', dpi=150); plt.close(fig)
    print(stem)

if __name__ == '__main__':
    for z in sys.argv[1:] or ['Z1']: build(z)
