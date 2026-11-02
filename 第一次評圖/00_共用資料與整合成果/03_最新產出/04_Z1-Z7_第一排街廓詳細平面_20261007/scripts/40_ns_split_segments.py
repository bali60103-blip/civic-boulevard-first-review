# 南北錯開分段（2026-10-13 使用者：「Z1–Z7 的分布好像都是垂直的，如果把 Z1–Z7 再從市民大道分南北呢」→「好」）
#   問題：現行 Z1–Z8 刀位垂直橫跨大道。半單元試算顯示：沿北側相鄰相異 0.36、跨大道 0.52、沿南側 0.56——
#     北側連續、南側一段一個機構。本程式改以每 100 m、南北分列，各側獨立找轉變點。
#   資料：03_南京至仁愛_沿線土地使用分析 landuse_pieces（用途、樓層、面積、距高架 dist）；高架兩側 300 m 內；
#     樓地板＝面積 × 樓層（缺樓層者以同類中位數補）。代表點投影至市民大道中心線（02 S.center）得里程與側別。
#   用途分組：沿用土地使用分析 GROUPS（住宅、商業〔一樓店面／商業／辦公〕、產業〔工業倉儲／產業遺構・古蹟〕、停車與交通、醫療／文教、運動休閒）
#     ＋政府機關（土地使用分析之 DROP，但為 Z3 南側主體〔行政院 64%〕，本分析不可省）；未標示、宗教不入分母（同土地使用分析）。
#   分段：各側獨立之最佳分段（動態規劃，最小化段內各格組成與段平均之平方差；各格等權〔有建物者〕，組成用樓地板比例），每段至少 3 格（300 m）；
#     段數規則兩側相同：每多一段須使總差異再降低 ≥ 6%（相對一段時之總差異），否則停止。
#   輸出：分析_南北錯開分段/ 下 PDF＋PNG（A3 橫式）、bins.csv、segments.csv。
import json, sys, importlib.util, collections, statistics, csv
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle
from shapely.geometry import shape, LineString
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
LU = H.parent / '03_南京至仁愛_沿線土地使用分析_20261006' / 'data'
OUT = H / '分析_南北錯開分段'; OUT.mkdir(exist_ok=True)
sys.argv = [sys.argv[0], 'A1']
spec = importlib.util.spec_from_file_location('sheet', H / 'scripts/02_sheet.py'); S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
S.VARIANT['full'] = True
spec = importlib.util.spec_from_file_location('sheets', H / 'scripts/05_sheets.py'); F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
CL = S.center
BIN, MIN_SEG, GAIN = 100.0, 3, 0.04   # 兩側同一門檻；6% 時北 3／南 4、8% 時北 3／南 2——南側無明顯轉折，故取 4% 呈現細部
GROUPS = [('G_RES', '住宅', ['RES'], '#F2D35B'), ('G_COM', '商業（一樓店面／商業／辦公）', ['MIX', 'COM', 'OFF'], '#E0473C'),
          ('G_GOV', '政府機關', ['GOV'], '#3D4F7C'),
          ('G_IND', '產業（工業倉儲／產業遺構・古蹟）', ['IND', 'HER'], '#9B6FC8'), ('G_TRN', '停車與交通', ['TRN'], '#7D7D7D'),
          ('G_PUB', '醫療／文教', ['EDU', 'MED'], '#4BA3C7'), ('G_REC', '運動休閒', ['REC'], '#5DA95A')]
GOF = {c: i for i, (_, _, cs, _) in enumerate(GROUPS) for c in cs}
NG = len(GROUPS)

def side_ch(pt):
    d = CL.project(pt); a = CL.interpolate(max(0, d - 5)); b = CL.interpolate(min(CL.length, d + 5))
    return d, ('N' if (b.x - a.x) * (pt.y - a.y) - (b.y - a.y) * (pt.x - a.x) > 0 else 'S')

# 單元界線里程（Z1 西界～Z8 東界）
cuts = [shape(f['geometry']) for f in S.ZF if 'cut' in f['properties']]
ef = H / 'data/Z8_east_cut_EPSG3826.geojson'
if ef.exists(): cuts = cuts[:8] + [shape(json.load(open(ef))['features'][0]['geometry'])]
cut_ch = []
for g in cuts:
    x = g.intersection(CL)
    p = x if x.geom_type == 'Point' else (list(getattr(x, 'geoms', [x]))[0] if not x.is_empty else None)
    cut_ch.append(CL.project(p) if p is not None and p.geom_type == 'Point' else CL.project(g.interpolate(g.project(CL.interpolate(CL.project(g.centroid))))))
cut_ch = sorted(cut_ch)[:9]
C0, C1 = cut_ch[0], cut_ch[-1]
NB = int(np.ceil((C1 - C0) / BIN))

# 樓地板：各側各格 × 用途組
P = json.load(open(LU / 'landuse_pieces_EPSG3826.geojson'))['features']
lv = collections.defaultdict(list)
for f in P:
    p = f['properties']
    if p['levels'] not in (None, 'None', ''): lv[p['cls']].append(float(p['levels']))
lv = {k: statistics.median(v) for k, v in lv.items()}
M = {s: np.zeros((NB, NG)) for s in 'NS'}; BIG = {s: np.zeros(NB) for s in 'NS'}; FP = {s: np.zeros(NB) for s in 'NS'}
for f in P:
    p = f['properties']
    if p['cls'] not in GOF or float(p['dist'] or 1e9) > 300: continue
    g = shape(f['geometry']); ch, s = side_ch(g.representative_point())
    if not (C0 <= ch < C1): continue
    b = int((ch - C0) // BIN); A = float(p['area'])
    L = float(p['levels']) if p['levels'] not in (None, 'None', '') else lv.get(p['cls'], 4)
    M[s][b, GOF[p['cls']]] += A * L; FP[s][b] += A
    if A > 2500: BIG[s][b] += A

def shares(X):
    w = X.sum(1); return X / np.where(w[:, None] > 0, w[:, None], 1), (w > 0).astype(float)
def seg_cost(X, i, j):      # 格 i..j-1：各格等權（有建物者）之組成平方差——「沿街走過什麼」，不讓高樓樓地板主導
    sh, w = shares(X[i:j])
    if w.sum() <= 0: return 0.0
    m = (sh * w[:, None]).sum(0) / w.sum()
    return float((w * ((sh - m) ** 2).sum(1)).sum())
def best_seg(X, kmax=12):
    n = len(X); C = np.full((n + 1, n + 1), np.inf)
    for i in range(n):
        for j in range(i + MIN_SEG, n + 1): C[i, j] = seg_cost(X, i, j)
    dp = np.full((kmax + 1, n + 1), np.inf); bk = np.zeros((kmax + 1, n + 1), int); dp[0, 0] = 0
    for k in range(1, kmax + 1):
        for j in range(n + 1):
            for i in range(j):
                v = dp[k - 1, i] + C[i, j]
                if v < dp[k, j]: dp[k, j], bk[k, j] = v, i
    costs = [dp[k, n] for k in range(1, kmax + 1)]
    k = 1
    while k < kmax and np.isfinite(costs[k]) and costs[k - 1] - costs[k] >= GAIN * costs[0]: k += 1
    bounds, j = [], n
    for kk in range(k, 0, -1):
        i = bk[kk, j]; bounds.append((i, j)); j = i
    return bounds[::-1], costs

# 橫越大道之具名道路（標記轉變點用）：OSM 具名道路（非巷弄、非市民大道）與中心線交點
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform
cross = []
for w in json.load(open(Path.home() / 'Desktop/Civic_Rebuild_20260909_201934/data/osm.json'))['ways']:
    t = w.get('tags', {}); nm = t.get('name', '')
    if not nm or t.get('highway') not in ('trunk', 'primary', 'secondary', 'tertiary', 'unclassified', 'residential', 'living_street') \
       or any(x in nm for x in ('巷', '弄', '市民大道', '匝道', '地下街', '機車道')): continue
    ln = LineString([tf(x, y) for x, y in w['ll']]) if len(w.get('ll', [])) > 1 else None
    if ln is None or not ln.intersects(CL): continue
    x = ln.intersection(CL)
    for q in getattr(x, 'geoms', [x]):
        if q.geom_type == 'Point': cross.append((CL.project(q), nm))
def road_at(ch, tol=150):
    if ch >= C1 - 1: return '基隆路'      # Z8 東界（35 基隆路中心線）；中心線止於 E307105，無交點
    if ch <= C0 + 1: return '淡水河堤'
    c = [(abs(c_ - ch), nm) for c_, nm in cross if abs(c_ - ch) <= tol]
    return min(c)[1] if c else None

res = {}
for s in 'NS':
    _, cs = best_seg(M[s])
    for g_ in (.04, .06, .08):
        k = 1
        while k < len(cs) and np.isfinite(cs[k]) and cs[k - 1] - cs[k] >= g_ * cs[0]: k += 1
        print(f"  {'北' if s == 'N' else '南'}側 門檻 {g_ * 100:.0f}% → {k} 段")
for s in 'NS':
    bounds, costs = best_seg(M[s]); res[s] = (bounds, costs)
    print(f"{'北' if s == 'N' else '南'}側：{len(bounds)} 段｜總差異 k=1..8：", [round(c, 1) for c in costs[:8]])

def label(X, i, j):
    sh_, w_ = shares(X[i:j]); sh = (sh_ * w_[:, None]).sum(0) / max(w_.sum(), 1)   # 各格等權平均組成
    top = [GROUPS[g][1].split('（')[0] + f'{sh[g] * 100:.0f}' for g in np.argsort(-sh)[:2] if sh[g] > .08]
    return '、'.join(top)
rows = []
for s in 'NS':
    for i, j in res[s][0]:
        a, b = C0 + i * BIN, C0 + j * BIN
        rows.append({'段': ('北' if s == 'N' else '南') + str(len([r for r in rows if r['側'] == ('北' if s == 'N' else '南')]) + 1), '側': '北' if s == 'N' else '南', '起_m': round(a - C0), '迄_m': round(b - C0), '長_m': round(b - a),
                     '起點道路': road_at(a) or '', '迄點道路': road_at(b) or '', '主要用途（樓地板%）': label(M[s], i, j),
                     '大型建物占比%': round(BIG[s][i:j].sum() / max(FP[s][i:j].sum(), 1) * 100)})
with open(OUT / 'segments.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    wr = csv.DictWriter(fh, fieldnames=list(rows[0])); wr.writeheader(); wr.writerows(rows)
with open(OUT / 'bins.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    wr = csv.writer(fh); wr.writerow(['側', '起_m'] + [g[1] + '_m2' for g in GROUPS] + ['大型建物面積_m2', '建物面積_m2'])
    for s in 'NS':
        for b in range(NB): wr.writerow(['北' if s == 'N' else '南', round(b * BIN)] + [round(v) for v in M[s][b]] + [round(BIG[s][b]), round(FP[s][b])])
for r in rows: print(r)

# ---------- 圖：A3 橫式，里程為橫軸；上＝北、下＝南 ----------
W3, H3, MM = 420, 297, 1 / 25.4
X0m, X1m = 22, 400; kx = (X1m - X0m) / (C1 - C0)
xm = lambda ch: X0m + (ch - C0) * kx
fig = plt.figure(figsize=(W3 * MM, H3 * MM))
def R(x, y, w, h, **kw): fig.add_artist(Rectangle((x / W3, y / H3), w / W3, h / H3, transform=fig.transFigure, **kw))
def T(x, y, t, **kw): fig.text(x / W3, y / H3, t, **kw)
def Ln(xs, ys, **kw): fig.add_artist(plt.Line2D([v / W3 for v in xs], [v / H3 for v in ys], transform=fig.transFigure, **kw))
R(10, 10, W3 - 20, H3 - 20, fill=False, lw=.8)
T(X0m, H3 - 24, '南北錯開分段｜市民大道兩側用途組成（每 100 m、南北分列）', fontsize=15, va='top')
T(X0m, H3 - 33, f'高架兩側 300 m 內建物樓地板；各側獨立以最佳分段找轉變點（每段 ≥ 300 m；每多一段須再降低總差異 ≥ {GAIN * 100:.0f}%）。'
  '藍虛線＝現行 Z1–Z8 單元界線。未標示、宗教不計。', fontsize=7.5, va='top', color='#555')
YAX = 156; BH = 60; SEGH = 15
# 長條：北向上、南向下
for s, sign in (('N', 1), ('S', -1)):
    base = YAX + sign * (SEGH + 8)
    for b in range(NB):
        tot = M[s][b].sum()
        if tot <= 0: continue
        y = 0.0
        for g in range(NG):
            h = M[s][b, g] / tot * BH
            if h <= 0: continue
            R(xm(C0 + b * BIN) + .15, base + (y if sign > 0 else -y - h), BIN * kx - .3, h, facecolor=GROUPS[g][3], edgecolor='none'); y += h
    T(X0m - 2, base + sign * BH / 2, '北側' if s == 'N' else '南側', fontsize=10, fontweight='bold', ha='right', va='center')
    # 分段帶
    for n_, ((i, j), r) in enumerate(zip(res[s][0], [r for r in rows if r['側'] == ('北' if s == 'N' else '南')]), 1):
        x0_, x1_ = xm(C0 + i * BIN), xm(C0 + j * BIN); yb = YAX + (2 if sign > 0 else -2 - SEGH); wide = x1_ - x0_ > 34
        R(x0_ + .4, yb, x1_ - x0_ - .8, SEGH, facecolor='#f4f4f4', edgecolor='#333', lw=.6)
        lab = r['主要用途（樓地板%）'] if wide else r['主要用途（樓地板%）'].split('、')[0].replace('醫療／文教', '醫教').replace('停車與交通', '交通')
        T((x0_ + x1_) / 2, yb + SEGH * .7, f"{r['側']}{n_}", fontsize=6.4, fontweight='bold', ha='center', va='center')
        T((x0_ + x1_) / 2, yb + SEGH * .45, lab, fontsize=6.0 if wide else 5.3, ha='center', va='center')
        T((x0_ + x1_) / 2, yb + SEGH * .2, f"{r['長_m']} m" + (f"｜大型 {r['大型建物占比%']}%" if wide else ''), fontsize=5.0, ha='center', va='center', color='#666')
    for i, j in res[s][0][1:]:
        nm = road_at(C0 + i * BIN)
        if nm: T(xm(C0 + i * BIN), YAX + sign * (SEGH + 8 + BH + 3), nm, fontsize=5.4, ha='center', va='bottom' if sign > 0 else 'top', color='#333', rotation=0)
# 單元界線與標籤
for k, c in enumerate(cut_ch):
    Ln([xm(c)] * 2, [YAX - SEGH - 8 - BH, YAX + SEGH + 8 + BH], color=S.ZONE_C, lw=.8, ls=(0, (4, 2)))
for k in range(len(cut_ch) - 1):
    T((xm(cut_ch[k]) + xm(cut_ch[k + 1])) / 2, YAX - .2, f'Z{k + 1}', fontsize=7, ha='center', va='center', color=S.ZONE_C, fontweight='bold',
      bbox=dict(facecolor='white', edgecolor='none', pad=.6))
Ln([X0m, X1m], [YAX] * 2, color='#9a9a9a', lw=.6, ls=(0, (6, 1.5, 1.5, 1.5)))
# 里程尺
for m_ in range(0, int(C1 - C0) + 1, 500):
    Ln([xm(C0 + m_)] * 2, [YAX - SEGH - 8 - BH - 9, YAX - SEGH - 8 - BH - 7], color='#333', lw=.5)
    T(xm(C0 + m_), YAX - SEGH - 8 - BH - 10, f'{m_ / 1000:.1f} km' if m_ else '0', fontsize=5.6, ha='center', va='top')
# 跨大道相異（每格，三格移動平均）
def di(a, b):
    ta, tb = a.sum(), b.sum()
    return .5 * np.abs(a / ta - b / tb).sum() if ta > 0 and tb > 0 else np.nan
d = np.array([di(M['N'][b], M['S'][b]) for b in range(NB)])
dm = np.array([np.nanmean(d[max(0, b - 1):b + 2]) if np.isfinite(d[max(0, b - 1):b + 2]).any() else np.nan for b in range(NB)])
y0d, hd = 26, 22
R(X0m, y0d, X1m - X0m, hd, facecolor='#fafafa', edgecolor='#ccc', lw=.4)
pts = [(xm(C0 + (b + .5) * BIN), y0d + v * hd) for b, v in enumerate(dm) if np.isfinite(v)]
Ln([p[0] for p in pts], [p[1] for p in pts], color='#8E1B3E', lw=1.0)
T(X0m - 2, y0d + hd / 2, '跨大道\n相異', fontsize=7, ha='right', va='center', linespacing=1.2)
for v in (0, .5, 1): T(X1m + 1.5, y0d + v * hd, f'{v:.1f}', fontsize=5.4, va='center', color='#666')
T(X0m, y0d + hd + 2.5, '同一里程北側與南側之用途組成相異指數（0＝相同、1＝完全不同；三格移動平均）', fontsize=6.2, color='#555')
# 圖例
lx = X0m
for _, nm, _, c in GROUPS:
    R(lx, 14, 5, 3, facecolor=c, edgecolor='none'); T(lx + 6.5, 15.5, nm, fontsize=6.3, va='center'); lx += 9 + len(nm) * 2.35
with PdfPages(OUT / '南北錯開分段_沿線用途剖面_A3.pdf') as pdf: pdf.savefig(fig)
fig.savefig(OUT / '南北錯開分段_沿線用途剖面_A3_預覽.png', dpi=150); plt.close(fig)
print('out', OUT)

# ---------- 北側分段疊至「產業分布」總圖（使用者 2026-10-13：「把北端的分割也加入平面圖，用產業分布那張總圖做」） ----------
#   底圖＝03 土地使用分析之 市民高架沿線產業分布_A3_*.pdf 第 1 頁（全線總圖，不改其程式與成果，另存一份）。
#   座標換算依 03 02_map.py P1：A1 設計毫米之地圖框 x 28、上緣 594−60、SC1＝(X1−X0)/(841−56) m/mm，整頁縮為 A3（×0.5）；
#     以現行單元界線核對，頁面虛線與預測位置差 0.2–0.4 mm。
import fitz, glob, subprocess, math
srcs = sorted(glob.glob(str(H.parent / '03_南京至仁愛_沿線土地使用分析_20261006' / '市民高架沿線產業分布_A3_*.pdf')))
if srcs:
    SRC = Path(srcs[-1]); X0w, Y1w = 300935, 2771910; SC1 = (307545 - 300935) / (841 - 56); PT = 72 / 25.4
    pg = lambda x, y: fitz.Point((14 + (x - X0w) / SC1 * .5) * PT, (30 + (Y1w - y) / SC1 * .5) * PT)
    def npt(ch, off):   # 中心線里程 ch 向北偏移 off m（N＝行進方向左側）
        a = CL.interpolate(max(0, ch - 15)); b = CL.interpolate(min(CL.length, ch + 15)); dx, dy = b.x - a.x, b.y - a.y; L = math.hypot(dx, dy)
        c = CL.interpolate(ch); return (c.x - dy / L * off, c.y + dx / L * off)
    doc = fitz.open(); doc.insert_pdf(fitz.open(SRC), from_page=0, to_page=0); page = doc[0]
    INK, OFF = (.12, .12, .12), 315
    FF = next((f for f in ('/Library/Fonts/Arial Unicode.ttf', '/System/Library/Fonts/Supplemental/Arial Unicode.ttf') if Path(f).exists()), None)
    FN = 'aru' if FF else 'china-t'                      # 比例字寬之中文字型（內建 china-t 之半形數字為全形寬）
    if FF: page.insert_font(fontname=FN, fontfile=FF)
    FO = fitz.Font(fontfile=FF) if FF else fitz.Font('china-t')
    def ctext(cx, y, t, fs, col=None):   # 置中單行（先量字寬）
        page.insert_text(fitz.Point(cx - FO.text_length(t, fs) / 2, y), t, fontname=FN, fontsize=fs, color=col or INK)
    FR = fitz.Rect(14 * PT, 30 * PT, 406.5 * PT, 143.4 * PT)   # 地圖框（A3 頁面）
    inside = lambda q: FR.x0 + 2 <= q.x <= FR.x1 - 2 and FR.y0 + 2 <= q.y <= FR.y1 - 2
    nrows = [r for r in rows if r['側'] == '北']
    for n_, ((i, j), r) in enumerate(zip(res['N'][0], nrows), 1):
        a, b = C0 + i * BIN, C0 + j * BIN
        line = [q for q in (pg(*npt(c, OFF)) for c in np.linspace(a + 6, b - 6, max(3, int((b - a) / 25)))) if inside(q)]
        if len(line) > 1: page.draw_polyline(line, color=INK, width=1.3)
        for c in (a + 6, b - 6):
            q1, q2 = pg(*npt(c, OFF - 25)), pg(*npt(c, OFF + 25))
            if inside(q1) and inside(q2): page.draw_line(q1, q2, color=INK, width=1.0)
        cm = (a + b) / 2 if b - a > 400 else (max(a, C0 + 120) + b) / 2   # 短段（西端）標籤往段內移
        P0 = pg(*npt(cm, OFF + 95))
        if P0.y < FR.y0 + 12: P0 = pg(*npt(cm, OFF - 110))     # 會超出圖框上緣 → 改放帶緣下方
        wide = b - a >= 1000
        t1 = f"{r['段']}　{r['主要用途（樓地板%）']}" if wide else f"{r['段']}"
        t2 = f"{r['長_m'] / 1000:.1f} km｜大型建物 {r['大型建物占比%']}%" if wide else r['主要用途（樓地板%）'].split('、')[0]
        bw = max(FO.text_length(t1, 6.0), FO.text_length(t2, 5.2)) + 8
        rect = fitz.Rect(P0.x - bw / 2, P0.y - 9, P0.x + bw / 2, P0.y + 9)
        page.draw_rect(rect, color=INK, fill=(1, 1, 1), width=.6, fill_opacity=.92)
        ctext(P0.x, P0.y - 1.2, t1, 6.0); ctext(P0.x, P0.y + 6.2, t2, 5.2, (.35, .35, .35))
    for i, j in res['N'][0][1:]:      # 轉變點：大道（高架外側）垂直拉至北側帶外緣
        c = C0 + i * BIN
        page.draw_line(pg(*npt(c, 12)), pg(*npt(c, OFF)), color=INK, width=1.3, dashes='[4 2] 0')
        nm = road_at(c)
        if nm:
            q = pg(*npt(c, OFF * .55))         # 路名：轉折虛線右側、中段
            page.insert_text(fitz.Point(q.x + 2.5, q.y), nm.replace('一段', ''), fontname=FN, fontsize=5.2, color=INK)
    # 圖例（圖框右上空白處）
    lx, ly = 268 * PT, 24.5 * PT
    page.draw_line(fitz.Point(lx, ly - 2), fitz.Point(lx + 22, ly - 2), color=INK, width=1.3, dashes='[4 2] 0')
    page.insert_text(fitz.Point(lx + 26, ly), '北側分段（南北錯開分段：每 100 m、北側獨立分段；北1–北4）', fontname=FN, fontsize=6.2, color=INK)
    out = OUT / f'{SRC.stem}_總圖_北側分段.pdf'; doc.subset_fonts(); doc.save(out, garbage=3, deflate=True)
    subprocess.run(['qlmanage', '-t', '-s', '2600', '-o', str(OUT), str(out)], capture_output=True)
    ql = OUT / (out.name + '.png')
    if ql.exists(): ql.replace(OUT / f'{SRC.stem}_總圖_北側分段_預覽.png')
    print('overlay', out.name, '← 底圖', SRC.name)
