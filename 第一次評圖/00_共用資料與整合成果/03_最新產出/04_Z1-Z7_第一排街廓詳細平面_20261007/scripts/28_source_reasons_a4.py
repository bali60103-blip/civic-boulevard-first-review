# 源頭建築判讀依據（A4 橫式）：每一棟找出來的源頭建築「為什麼是流向台北車站之人群的源頭」（使用者 2026-10-11 指示，先做 Z2）
#   左：編號定位圖（與 A1 同方向：大道水平；只有本頁標編號，A1 圖面維持不標文字）；右：逐棟判讀表
#   每列：編號｜名稱與量體｜人流來源（誰會走去車站）｜往車站路徑（是否須穿越市民大道、最近地下入口、地面穿越點距離）｜判定
#   資料：17（data/{Z}_key_buildings、{Z}_source_candidates）、19（通行元素）、13（穿越供給）、OSM 標籤與出入口、06 店家點（industry_pois）
import json, sys, importlib.util, collections
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.collections import PathCollection, LineCollection
from shapely.geometry import shape, box, Point
from shapely.ops import unary_union, transform
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
ZONE = sys.argv[1] if len(sys.argv) > 1 else 'Z2'
_argv = sys.argv; sys.argv = [_argv[0], ZONE]
spec = importlib.util.spec_from_file_location('ns', H / 'scripts/20_ns_factors_sheet.py')
N = importlib.util.module_from_spec(spec); spec.loader.exec_module(N)
sys.argv = _argv
S, F = N.S, N.F
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform
MM = 1 / 25.4
FW, FH = 297, 210                                  # A4 橫式

SRC = sorted(N.SRC, key=lambda gp: -gp[1]['fa'])   # 編號＝樓地板由大到小
TGT = N.TGT
SITE = [(g, p) for g, p in N.CHAR if p.get('site')]
CAND = json.load(open(H / f'data/{ZONE}_source_candidates.json'))
MIN_FA = 10000

# ---------- 證據：OSM 標籤、店家點、出入口 ----------
osm = json.load(open(S.BASE / 'source/expanded_osm.geojson'))['features']
OB = [(transform(tf, shape(f['geometry'])).buffer(0), f['properties']) for f in osm if f['geometry']['type'] != 'LineString' and 'building' in f['properties']]
POI = [(shape(f['geometry']), f['properties']) for f in json.load(open(H.parents[0] / '03_南京至仁愛_沿線土地使用分析_20261006/data/industry_pois_EPSG3826.geojson'))['features']]
ENT = []
for f in json.load(open(H / 'data/osm_street_points_4326.geojson'))['features']:
    p = f['properties']
    if p['kind'] != 'mrt_entrance': continue
    lab = (p.get('ref') or p.get('name') or '').strip()
    if lab[:1] in ('Y', 'R', 'M'): ENT.append((transform(tf, shape(f['geometry'])), lab.split()[0]))
for f in json.load(open(H.parents[1] / '02_調整過程/公共都更編號圖/公共案件量體與基地_EPSG3826.geojson'))['features']:
    pr = f['properties']
    if pr['case'] == 'B03' and pr['layer'] == 'building' and pr['label'][:1] == 'R':   # 中山地下街 R1–R6 出入口（北捷前期評估描圖）
        lab = pr['label'][:2]
        if not any(l == lab for _, l in ENT): ENT.append((shape(f['geometry']).centroid, lab))
MALL = {'Y': '台北地下街 Y區', 'R': '中山地下街 R區', 'M': '捷運台北車站'}
DS = json.load(open(H / f'data/{ZONE}_demand_supply_EPSG3826.geojson'))
CROSS = sorted([(p['s'], {'at_grade': f"{p['name'].replace('一段', '')}路口（平面）", 'footbridge': f"{p['name'].replace('一段', '')}天橋"}[p['type']])
                for f in DS['features'] for p in [f['properties']] if p['kind'] == 'supply' and p['type'] in ('at_grade', 'footbridge')])

def evidence(g):
    tags = {}
    for og, op in OB:
        if og.intersects(g) and og.intersection(g).area > .3 * min(og.area, g.area):
            for k, v in op.items(): tags.setdefault(k, v)
    pois = [pp for pg, pp in POI if g.buffer(4).contains(pg)]
    return tags, collections.Counter(pp['ind'] for pp in pois), [pp['name'] for pp in pois if pp.get('name')]

# 人流來源（誰會走去車站）：依 OSM 標籤與 06 店家點整理之描述（Z2）；未列者依用途自動產生
WHO = {'Z2': {
    '京站時尚廣場／臺北轉運站': '國道客運轉運站（臺北轉運站，2009 啟用）之轉乘旅客；京站商場購物人潮（店家點：餐飲 31、零售 4 家）；君品酒店住客、威秀影城觀眾',
    '壽德大樓': '20 層商辦之上班族與洽公民眾（健保署台北業務組、補習班等商辦 9 家）；地面層餐飲 9 家之顧客',
    '崇聖大樓': '19–23 層商辦之上班族（中國信託、東森電視等）',
    'Jingwang（集合住宅）': '32 層集合住宅（2022 完工，高 122 m）之住戶通勤、通學',
    '天成大飯店': '17 層旅館之住客（站前旅館，住宿與車站轉乘）；餐廳 5 家之顧客',
    '中山辦公大樓': '市府辦公大樓（OSM office=government）之公務員與洽公民眾（市立圖書館長安分館、自來水北區營業處等）',
    '中央保險大樓': '20 層商辦之上班族（滙豐銀行等）',
    '中央大樓': '11 層商業大樓之上班族與顧客（店家 10 家：餐飲、零售、運動用品）',
    '第五大道': '12–15 層住商大樓之住戶與上班族（台北富邦銀行）',
    '住宅（OSM 未具名）': '住宅為主、一樓銀行與店家（永豐銀行、7-Eleven）之住戶通勤與顧客',
    '實益大樓／長安富裕大樓': '11 層店面＋住宅之住戶與顧客（店家 9 家：餐飲、便利商店、建材）',
    '集合住宅（OSM 未具名）': '22 層集合住宅之住戶通勤',
}}.get(ZONE, {})
FLOW = {'轉乘＋商業': '轉乘旅客與顧客', '商業': '上班族與顧客', '辦公': '上班族', '機關': '公務員與洽公民眾', '旅館': '旅客',
        '住宅': '住戶通勤', '店面＋住宅': '住戶與顧客', '醫療': '病患與醫護', '文教': '學生與訪客'}

def route(g, p):
    c = g.representative_point(); s_ = S.center.project(c)
    if p['side'] == 'N':
        ug = sorted((g.distance(eg), lab) for eg, lab in ENT if lab[0] in 'YR')
        d_u, lab_u = ug[0] if ug else (None, '')
        gr = '、'.join(f"{nm} {abs(s_ - sc):.0f} m" for sc, nm in CROSS)
        return (f"北側，須穿越市民大道。地下：最近入口 {lab_u} 約 {d_u:.0f} m，經{MALL[lab_u[0]]}進站；"
                f"地面：{gr}（沿大道距離）")
    ms = sorted((g.distance(eg), lab) for eg, lab in ENT if lab[0] == 'M')
    d_m, lab_m = ms[0]
    return f"南側，不須穿越市民大道。至捷運台北車站 {lab_m} 出口約 {d_m:.0f} m、至站房約 {g.distance(TGT[0][0]):.0f} m"

def verdict(p):
    if '轉運站' in p['name']: return '轉乘設施（不設門檻）；主角之一'
    return f"總樓地板 ≥ 1 萬㎡"

# ---------- 版面 ----------
fig = plt.figure(figsize=(FW * MM, FH * MM))
fig.add_artist(plt.Rectangle((8 / FW, 8 / FH), (FW - 16) / FW, (FH - 16) / FH, transform=fig.transFigure, fill=False, lw=.6))
zp = S.ZP[ZONE]
fig.text(14 / FW, 1 - 14 / FH, f"{ZONE}　{zp['from']}—{zp['to']}｜源頭建築判讀依據：流向台北車站之人群從哪裡來", fontsize=12, va='top')
fig.text(14 / FW, 1 - 20.5 / FH, f"判準（使用者 2026-10-11 指定）：{ZONE} 範圍內，流向台北車站之人群的源頭建築——總樓地板 ≥ 1 萬㎡（臺北三維模型逐量體加總），"
         f"轉乘設施不設門檻；目的地＝臺北車站（主角之一）。編號＝樓地板由大到小，對應 A1 酒紅剪影。", fontsize=6.6, va='top', color='#444')

# 定位圖（轉正：大道水平，同 A1）
d = S.PZ(ZONE); T = d['T']
pa_, pb_ = F.ends(ZONE); xa, xb = sorted([T(pa_).x, T(pb_).x])
cont = T(unary_union([g for g, _ in SRC + TGT]))
X0, X1 = xa - 45, xb + 45
Y0, Y1 = min(cont.bounds[1], -60) - 22, max(cont.bounds[3], 60) + 22
MAP_W = 112; MAP_H = MAP_W * (Y1 - Y0) / (X1 - X0)
if MAP_H > 168: MAP_H = 168; MAP_W = MAP_H * (X1 - X0) / (Y1 - Y0)
mx0, my_top = 14, FH - 30
ax = fig.add_axes([mx0 / FW, (my_top - MAP_H) / FH, MAP_W / FW, MAP_H / FH]); ax.axis('off')
ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1)
o = d['R'].centroid
from shapely import affinity
VW = affinity.rotate(affinity.translate(box(X0, Y0, X1, Y1), o.x, o.y), d['ang'], origin=(o.x, o.y)).buffer(30)
WB = box(*VW.bounds)
P = lambda gs: [q for q in (S.poly_path(T(g)) for g in gs) if q is not None]
ax.add_collection(PathCollection(P(S.polys(N.paths_geom(WB))), facecolors='#ececec', edgecolors='none', zorder=1))
UGC = '#%02X%02X%02X' % tuple(round(.45 * int(N.RED[i:i + 2], 16) + .55 * 255) for i in (1, 3, 5))   # 地下層＝通行元素色 45%＋白（2026-10-13 隨 N.RED 統一）
ax.add_collection(PathCollection(P([g for g, p in N.PA if N.level_of(p) in ('B1', 'B2')]), facecolors=UGC, edgecolors='none', zorder=2))
ax.add_collection(PathCollection(P(S.polys(S.bld.intersection(WB))), facecolors='#bdbdbd', edgecolors='none', zorder=3))
ax.add_collection(PathCollection(P([g for g, _ in TGT]), facecolors=N.MAG_LT, edgecolors='none', zorder=4))
ax.add_collection(PathCollection(P([g for g, _ in SRC]), facecolors=N.MAG, edgecolors='none', zorder=4))
ax.add_collection(PathCollection(P([g for g, p in N.PA if N.level_of(p) == 'U1']), facecolors=N.RED, edgecolors='none', zorder=5))
k_ = int(ZONE[1:])
for cg in (F.CUT_G[k_ - 1], F.CUT_G[k_] if k_ < len(F.CUT_G) else None):
    if cg is not None: ax.add_collection(LineCollection(S.lines(T(cg)), colors=S.ZONE_C, linewidths=.7, linestyles=(0, (5, 2.5)), zorder=6))
ax.add_patch(plt.Rectangle((X0, Y0), X1 - X0, Y1 - Y0, fill=False, lw=.4, ec='#999', zorder=9))
# 外部（界線外）淡化
from matplotlib.patches import PathPatch
SL = T(shape(N.DATA['slab']))
ax.add_patch(PathPatch(S.poly_path(box(X0 - 50, Y0 - 50, X1 + 50, Y1 + 50).difference(SL)), facecolor='white', edgecolor='none', alpha=.6, zorder=7))
# 編號
from shapely.ops import polylabel
def lab_pt(g):
    q = T(g); q = max(getattr(q, 'geoms', [q]), key=lambda t: t.area)
    try: return polylabel(q, 1.0)
    except Exception: return q.representative_point()
for i, (g, p) in enumerate(SRC, 1):
    c = lab_pt(g)
    ax.add_patch(plt.Circle((c.x, c.y), 7.5, color='white', zorder=10)); ax.add_patch(plt.Circle((c.x, c.y), 6.3, color=N.MAG, zorder=11))
    ax.text(c.x, c.y, str(i), fontsize=6, color='white', ha='center', va='center', fontweight='bold', zorder=12)
for g, p in TGT:
    c = lab_pt(g); ax.text(c.x, c.y, '目的地\n臺北車站', fontsize=6.2, color=N.MAG, ha='center', va='center', fontweight='bold', zorder=12, linespacing=1.2)
# 通行要素標示（本頁才標）
def tag(x, y, t, c=N.RED, ha='left'):
    ax.text(x, y, t, fontsize=5.4, color=c, ha=ha, va='center', zorder=13, path_effects=S.halo)
for g, p in N.PA:
    if p['type'] == '人行天橋':
        c = T(g).centroid; tag(c.x + 8, c.y + 20, '承德路天橋', ha='left'); break
cr = [T(g).centroid for g, p in N.FE if p['cls'] == 'pass' and p.get('type') == 'crossing']
for c in cr:
    ax.add_patch(plt.Circle((c.x, c.y), 9, fill=False, ec=N.RED, lw=1.0, zorder=13)); tag(c.x - 12, c.y - 16, '平面穿越（中山北路）', ha='right')
for g, p in N.PA:
    if p.get('name') == '中山地下街（R區）':
        q = T(g).intersection(box(X0, Y1 - 70, X1, Y1 - 50))          # 圖框上緣附近之 R區 段，標於其左側空隙
        if not q.is_empty: tag(q.bounds[0] - 4, (q.bounds[1] + q.bounds[3]) / 2, '中山地下街 R區（B1）', ha='right')
    if p.get('name') == '台北地下街（Y區）':
        q = T(g).intersection(box(X0, Y0, X1, Y1)); c = q.centroid if not q.is_empty else None
        if c is not None: tag(X0 + 6, c.y + 2, '台北地下街 Y區（B2）')
ax.text(X1 - 4, Y1 - 6, '市民大道 →', fontsize=5, color='#777', ha='right', va='top', zorder=13)
# 比例尺、指北
sm = (X1 - X0) / MAP_W                                   # m/mm
L = 100; bx = mx0 + 2; by = my_top - MAP_H - 6
fig.add_artist(plt.Line2D([bx / FW, (bx + L / sm) / FW], [by / FH] * 2, transform=fig.transFigure, color='#222', lw=1.4))
fig.text(bx / FW, (by + 1.2) / FH, '0', fontsize=5, va='bottom'); fig.text((bx + L / sm) / FW, (by + 1.2) / FH, f'{L} m', fontsize=5, va='bottom', ha='center')
fig.text((bx + L / sm + 6) / FW, by / FH, f'約 1:{round(sm * 1000, -2):,.0f}', fontsize=5, va='center', color='#555')
t_ = np.radians(-d['ang']); v = np.array([-np.sin(t_), np.cos(t_)]); c0 = np.array([mx0 + MAP_W - 6, my_top - MAP_H - 6])
fig.add_artist(plt.Line2D([c0[0] / FW, (c0[0] + 5 * v[0]) / FW], [c0[1] / FH, (c0[1] + 5 * v[1]) / FH], transform=fig.transFigure, color='#222', lw=.9))
fig.text((c0[0] + 7 * v[0]) / FW, (c0[1] + 7 * v[1]) / FH, 'N', fontsize=5.5, ha='center', va='center')
# 圖例（定位圖下）
ly = by - 7
for x_, c, t in ((14, N.MAG, '源頭建築（編號）'), (50, N.MAG_LT, '目的地：臺北車站'), (84, UGC, '地下街／站體（B1・B2）'), (122, N.RED, '人行天橋')):
    fig.add_artist(plt.Rectangle((x_ / FW, (ly - 1.4) / FH), 5 / FW, 2.8 / FH, transform=fig.transFigure, facecolor=c, edgecolor='none'))
    fig.text((x_ + 6.5) / FW, ly / FH, t, fontsize=5.4, va='center')

# ---------- 判讀表 ----------
TX = mx0 + MAP_W + 8; TW = FW - 14 - TX
cols = [('', 6), ('名稱／量體', 30), ('人流來源（誰會走去車站）', (TW - 36 - 22) * .5), ('往車站路徑', (TW - 36 - 22) * .5), ('判定', 22)]
fs, lh = 5.5, 2.5
y = FH - 30
xx = TX
for t, w in cols:
    fig.text(xx / FW, y / FH, t, fontsize=fs + .4, fontweight='bold', va='top', color='#333'); xx += w
y -= 3.6
fig.add_artist(plt.Line2D([TX / FW, (TX + TW) / FW], [(y + .8) / FH] * 2, transform=fig.transFigure, color='#999', lw=.4))
def wrap(t, w_mm): return N.wrap_w(t, w_mm / (fs * .3528) * .98)
def row(cells, color='#222', first_c=None, bold0=False):
    global y
    wr = [wrap(t, w - 1.5) if t else [''] for (t, (_, w)) in zip(cells, cols)]
    n = max(len(l) for l in wr); xx = TX
    for j, (lines_, (_, w)) in enumerate(zip(wr, cols)):
        c = first_c if (j <= 1 and first_c) else color
        fig.text(xx / FW, y / FH, '\n'.join(lines_), fontsize=fs, va='top', color=c, linespacing=1.32,
                 fontweight='bold' if (j == 0 and bold0) else 'normal'); xx += w
    y -= n * lh + 1.4
    fig.add_artist(plt.Line2D([TX / FW, (TX + TW) / FW], [(y + .7) / FH] * 2, transform=fig.transFigure, color='#e2e2e2', lw=.3))
for i, (g, p) in enumerate(SRC, 1):
    tags, pc, pn = evidence(g)
    who = WHO.get(p['name']) or (FLOW.get(p['use'], '使用者') + (f"（店家點 {sum(pc.values())} 處）" if pc else ''))
    row([str(i), f"{p['name']}　約 {p['fa'] / 1e4:.1f} 萬㎡・{p['levels']} 層・{p['use']}", who, route(g, p), verdict(p)], first_c=N.MAG, bold0=True)
for g, p in TGT:
    tags, pc, pn = evidence(g)
    row(['★', f"{p['name']}　約 {p['fa'] / 1e4:.1f} 萬㎡・{p['levels']} 層", f"台鐵、高鐵站房，捷運板南線／淡水信義線、機捷轉乘；站內店家點約 {sum(pc.values())} 處（微風台北車站等）",
         '—', '目的地（主角之一），不列源頭'], first_c='#B0607A', bold0=True)
for g, p in SITE:
    row(['—', p['name'].split('（')[0], '主角之一：線形公園（非建物）。其下中山地下街 R區為北側人流之地下進站路徑', '經 R1–R6 出入口入 R區，接捷運台北車站北端大廳',
         '非建物：不列源頭、不上圖'], first_c='#777')
near = [c for c in CAND if c['fa'] < MIN_FA and c['use'] not in ('交通',)][:4]
nt = '、'.join(f"{('／'.join(c['names']) or {'N': '北側', 'S': '南側'}[c['side']] + c['use'] + '（未具名）')} {c['fa'] / 1e4:.2f} 萬㎡" for c in near)
y -= 1.5
for t in (f"門檻以下最接近者（未列入）：{nt}。",
          "人流來源依 OSM 標籤與 06 店家點（OSM，非完整普查）整理；樓地板為量體估算，代表人流潛力而非實測人數。",
          "路徑距離為直線（地下入口）或沿大道距離（地面穿越點），供比較用；地下入口：台北地下街 Y、中山地下街 R（OSM、北捷前期評估描圖）、捷運 M（OSM）。"):
    for ln in N.wrap_w(t, TW / (5.2 * .3528) * .98):
        fig.text(TX / FW, y / FH, ln, fontsize=5.2, va='top', color='#555'); y -= 2.4
fig.text((FW - 14) / FW, 11 / FH, '© OpenStreetMap contributors / ODbL｜臺北三維模型（2017）｜2026-10-11', fontsize=4.8, ha='right', color='#888')
if y < 12: print('WARNING: table overflow', round(y, 1))

out = H / '主題圖_南北通行因素與特性建築'
stem = f"{ZONE}_{S.short(zp['from'])}-{S.short(zp['to'])}_南北通行因素與特性建築_源頭建築判讀依據_A4"
with PdfPages(out / f'{stem}.pdf') as pdf: pdf.savefig(fig)
fig.savefig(out / f'{stem}_預覽.png', dpi=170); plt.close(fig)
print(stem, 'table bottom y', round(y, 1))
