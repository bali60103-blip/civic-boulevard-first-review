# Z1–Z8 共用圖例（2026-10-13 使用者：「整理一張共用的圖例」）
#   色彩已於 2026-10-13 統一（同一顏色全八張只代表一種意義；見 20 檔頭與 說明.txt），故八張 A3／A1 全段圖共用此圖例。
#   draw(fig, N, ...) 供 37（A3 各單元）、38（A1 全段）嵌入；單獨執行輸出 A3 橫式圖例頁。
#   色彩一律取自 20（N）之常數，改色時自動同步。
import sys, importlib.util
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

H = Path(__file__).resolve().parents[1]

def load20(zone='Z1'):
    argv = sys.argv; sys.argv = [argv[0], zone]
    spec = importlib.util.spec_from_file_location('ns_' + zone, H / 'scripts/20_ns_factors_sheet.py')
    N = importlib.util.module_from_spec(spec); N.__file__ = str(H / 'scripts/20_ns_factors_sheet.py'); spec.loader.exec_module(N)
    sys.argv = argv
    return N

# 各單元特性建築判準（使用者逐段指定；見指令區 workflow 第十三、十四節）——37／38 共用
CRIT = {'Z1': 'workflow 三層：主角構成、公共案件基地、界面大型建物', 'Z2': '流向台北車站之人群的源頭建築',
        'Z3': 'U17 新增人口之目的地：商辦／政府機關、日常生活店家', 'Z4': '運動生活空間：住宅、運動場、純綠地',
        'Z5': '商業空間之密集：商場、商辦旅館、騎樓與臨街店面；空地', 'Z6': '滲透場所：空地、學生、綠地',
        'Z7': '夜間餐飲：居酒屋、酒吧、宵夜小吃、一般餐飲', 'Z8': '南北兩側園區串連：三園區建物與戶外空間'}

def unit_table(fig, N, x, ytop, fw, fh, fs=8.5, cols=(0, 16, 62, 190), width=376):
    # 各單元：範圍｜主角（workflow 第三節）｜特性建築判準
    S = N.S; y = ytop; rh = fs * .62
    fig.text(x / fw, y / fh, '各單元主角與特性建築判準', fontsize=fs + 1.5, fontweight='bold', va='top', color='#333'); y -= rh * 1.7
    for c, t in zip(cols, ('單元', '範圍', '主角（workflow 第三節）', '特性建築判準（酒紅系所指）')):
        fig.text((x + c) / fw, y / fh, t, fontsize=fs - .5, fontweight='bold', va='top', color='#555')
    y -= rh * 1.25
    fig.add_artist(plt.Line2D([x / fw, (x + width) / fw], [(y + rh * .25) / fh] * 2, transform=fig.transFigure, color='#bbb', lw=.5))
    for z in ['Z%d' % i for i in range(1, 9)]:
        zp = S.ZP[z]
        for c, t, col in zip(cols, (z, f"{S.short(zp['from'])}—{S.short(zp['to'])}", zp['info'], CRIT[z]), ('#1A9BD7', '#222', '#222', '#8E1B3E')):
            fig.text((x + c) / fw, y / fh, t, fontsize=fs, va='top', color=col)
        y -= rh * 1.25
    return y

def groups(N):
    # (群組, [(符號, 色, 色2, 圖例文字, 出現單元)])；由上而下＝高程由高至低（同各單元圖例）
    L2, L3, L4 = (N.COM_C[k] for k in ('商業大樓／旅館', '騎樓店面', '臨街店面'))
    return [
        ('+2 高架', [('dashdot', '#9a9a9a', None, '市民高架主線車道中心線', '全部'),
                    ('dashdot', '#9a9a9a', None, '建國高架主線車道中心線', 'Z6')]),
        ('+1 天橋・匝道', [('thick', N.RED, None, '人行天橋', 'Z1 Z2 Z5 Z6'),
                         ('rhatch', N.RAMP_C, None, '市民高架匝道：高架段', 'Z8')]),
        ('±0 地面：特性建築系（酒紅）', [
            ('patch', N.MAG, None, '特性建築／主角（各單元第一級）', '全部'),
            (None, None, None, 'Z1 特性建築・Z2 源頭建築・Z3 主角 U17・Z4 主角 B01＋華山1914', ''),
            (None, None, None, 'Z5 大型商場／市場・Z6 主角場所・Z7 居酒屋／燒肉串燒', ''),
            (None, None, None, 'Z8 主角三園區', ''),
            ('patch', L2, None, '特性建築子類 2 級：商業大樓／旅館・酒吧／飲酒店', 'Z5 Z7'),
            ('patch', L3, None, '特性建築子類 3 級：騎樓店面・宵夜小吃', 'Z5 Z7'),
            ('patch', L4, None, '特性建築子類 4 級：臨街店面・一般餐飲', 'Z5 Z7'),
            ('patch', N.MAG_LT, None, '主角基地／開放空間（臺北車站、主角開放地、戶外空間）', 'Z2 Z6 Z8'),
            ('patch', N.HER_C, None, '古蹟（建國啤酒廠）', 'Z5'),
        ]),
        ('±0 地面：其他類別與底圖', [
            ('patch', N.DEST_C['商辦／政府機關'], None, '目的地：商辦／政府機關', 'Z3'),
            ('patch', N.DEST_C['日常生活店家'], None, '目的地：日常生活店家（餐飲、便利超市、生活服務）', 'Z3'),
            ('patch', N.HOUSE_C, None, '住宅建物（住宅、一樓店面住宅）', 'Z4'),
            ('patch', N.SPORT_C, None, '運動場（球場、體健設施、兒童遊戲場）', 'Z4'),
            ('patch', N.GREEN_C, None, '開放空間：綠地・空地・廣場', 'Z4 Z5'),
            ('patch', N.RED, None, '行穿線（Z6 非路口、Z8 交工處全部）', 'Z6 Z8'),
            ('rxhatch', N.RAMP_G_C, None, '市民高架匝道：落地段（地面阻隔）', 'Z8'),
            *[('patch', N.BLD_GRAYS[k], None, '建物 ' + N.FLOOR_LABELS[k], '全部') for k in range(4, -1, -1)],   # 2026-10-15 依樓高 5 級灰（42）
            (None, None, None, '建物樓高：臺北三維模型 2017，高度 ÷ 3.3 m＝層數；越高越深', ''),
            ('patch', N.XROAD_C, None, '可通過之路口（路徑較深灰；經交工處行穿線核對橫越大道）', '全部'),
            ('patch', N.PATH_C, None, '路徑（道路＋人行道；Z4 含公園步道與鋪面）', '全部'),
        ]),
        ('B1・B2 地下', [('split', N.RED, N.mix(N.RED), '地下通行元素：地下街、捷運站體、車站地下通廊、地下停車場', 'Z1 Z2 Z6 Z7'),
                        (None, None, None, '地下層位於路徑之下：大道下方透出較暗之橘（左半），街廓內為原橘（右半）', '')]),
        ('界線', [('dash', N.S.ZONE_C, None, '單元界線（路口中心線）', '全部'),
                 ('fade', None, None, '界線外：市民大道前後段（淡化；A1 全段圖不淡化）', '各單元圖')]),
    ]

N_HATCH = {'rhatch': '/////', 'rxhatch': 'xxxx'}   # 同 20 RAMP_H／RAMP_G_H
def swatch(fig, x, y, kind, c, c2, fw, fh, sw=7.0, sh=3.4):
    X, Y = x / fw, (y - sh / 2) / fh
    if kind == 'patch': fig.add_artist(Rectangle((X, Y), sw / fw, sh / fh, transform=fig.transFigure, facecolor=c, edgecolor='none'))
    elif kind == 'split':
        fig.add_artist(Rectangle((X, Y), sw / 2 / fw, sh / fh, transform=fig.transFigure, facecolor=c2, edgecolor='none'))
        fig.add_artist(Rectangle((X + sw / 2 / fw, Y), sw / 2 / fw, sh / fh, transform=fig.transFigure, facecolor=c, edgecolor='none'))
    elif kind in ('dashdot', 'dash', 'thick'):
        ls = {'dashdot': (0, (6, 1.5, 1.5, 1.5)), 'dash': (0, (6, 3)), 'thick': '-'}[kind]
        fig.add_artist(plt.Line2D([X, X + sw / fw], [y / fh] * 2, transform=fig.transFigure, color=c, lw=2.4 if kind == 'thick' else 1.0, ls=ls))
    elif kind in ('rhatch', 'rxhatch'):   # 匝道：白底斜線（同 20）
        fig.add_artist(Rectangle((X, Y), sw / fw, sh / fh, transform=fig.transFigure, facecolor='white', edgecolor=c, lw=.4, hatch=N_HATCH[kind]))
    elif kind == 'fade':
        fig.add_artist(Rectangle((X, Y), sw / fw, sh / fh, transform=fig.transFigure, facecolor='#f2f2f2', edgecolor='#cfcfcf', lw=.4))
    elif kind == 'hatch':   # 斜線＋外框（可通過之路口標記；同 20 legend_left）
        import numpy as np
        fig.add_artist(Rectangle((X, Y), sw / fw, sh / fh, transform=fig.transFigure, facecolor='none', edgecolor=c, lw=.6))
        for t_ in np.arange(-sh + sh / 6, sw, sh / 3):
            xa, xb = max(t_, 0), min(t_ + sh, sw)
            if xb > xa: fig.add_artist(plt.Line2D([X + xa / fw, X + xb / fw], [Y + (xa - t_) / fh, Y + (xb - t_) / fh], transform=fig.transFigure, color=c, lw=.45))

def draw(fig, N, x, ytop, fw, fh, fs=8.0, col_w=None, ncols=1, unit_x=None, gap=8.0):
    # 由 (x, ytop)（mm，自下）向下排；ncols > 1 時依群組分欄（群組不拆欄）；unit_x＝「出現單元」欄相對 x（mm）
    k = fs / 8.0; row, ghead = 5.4 * k, 6.2 * k
    gs = groups(N)
    hts = [ghead + sum(row for _ in items) + 2.5 * k for _, items in gs]
    cols, cur, acc, target = [[]], 0, 0.0, sum(hts) / ncols
    for (g, items), h in zip(gs, hts):   # 依高度平均分欄
        if acc + h > target * 1.08 and cols[-1] and len(cols) < ncols: cols.append([]); acc = 0.0
        cols[-1].append((g, items)); acc += h
    col_w = col_w or 120.0; unit_x = unit_x if unit_x is not None else col_w - 26
    ybot = ytop
    for ci, col in enumerate(cols):
        cx, y = x + ci * (col_w + gap), ytop
        for g, items in col:
            fig.text(cx / fw, y / fh, g, fontsize=fs, fontweight='bold', va='top', color='#333'); y -= ghead
            for kind, c, c2, lab, units in items:
                if kind: swatch(fig, cx, y - 1.9 * k, kind, c, c2, fw, fh, sw=7 * k, sh=3.4 * k)
                fig.text((cx + 10 * k) / fw, y / fh, lab, fontsize=fs if kind else fs - 1, va='top', color='#222' if kind else '#666')
                if units: fig.text((cx + unit_x) / fw, y / fh, units, fontsize=fs - 1, va='top', color='#1A9BD7')
                y -= row
            y -= 2.5 * k
        ybot = min(ybot, y)
    return ybot

if __name__ == '__main__':
    from matplotlib.backends.backend_pdf import PdfPages
    N = load20('Z1')
    FW, FH, MM = 420, 297, 1 / 25.4
    out = H / '主題圖_南北通行因素與特性建築' / 'Z1-Z8_南北通行因素與特性建築_共用圖例_A3.pdf'
    fig = plt.figure(figsize=(FW * MM, FH * MM))
    fig.add_artist(Rectangle((10 / FW, 10 / FH), (FW - 20) / FW, (FH - 20) / FH, transform=fig.transFigure, fill=False, lw=.8))
    fig.text(22 / FW, 1 - 24 / FH, 'Z1–Z8｜影響南北通行之元素與特性建築　共用圖例', fontsize=16, va='top')
    fig.text(22 / FW, 1 - 33 / FH, '色彩全八張統一（2026-10-13）：同一顏色只代表一種意義。圖層依高程排列（上＝高、下＝深）。'
             '藍字＝出現之單元；酒紅系＝各單元依其判準之特性建築（第一級最深），判準見各單元圖例與說明 A4。', fontsize=8, va='top', color='#555')
    yb = draw(fig, N, 22, FH - 50, FW, FH, fs=10.5, col_w=180, ncols=2, unit_x=152, gap=16)
    unit_table(fig, N, 22, yb - 6, FW, FH, fs=8.5, cols=(0, 14, 58, 200), width=376)
    with PdfPages(out) as pdf: pdf.savefig(fig)
    fig.savefig(str(out).replace('.pdf', '_預覽.png'), dpi=110); plt.close(fig)
    print(out.name)
