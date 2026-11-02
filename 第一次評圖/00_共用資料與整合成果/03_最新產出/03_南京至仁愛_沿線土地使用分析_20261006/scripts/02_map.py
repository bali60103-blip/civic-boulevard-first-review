# 出圖：A1 橫式三頁 —— P1 全線 1:10000＋統計；P2 西段 1:5000；P3 東段 1:5000
import json, csv, importlib.util, collections, sys
EX = '--exhibit' in sys.argv  # 展覽版：刪除說明文字、資料來源與方法註記
X = lambda full, short: short if EX else full
SFX = '_展覽版' if EX else ''
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch, Patch
from matplotlib.collections import PathCollection, LineCollection
from matplotlib.lines import Line2D
from matplotlib.backends.backend_pdf import PdfPages
from shapely.geometry import shape, box, Point
from shapely.ops import unary_union

H = Path(__file__).resolve().parents[1]
BASE = H.parents[1] / '03_最新產出/02_南京至仁愛擴幅_20261005'
spec = importlib.util.spec_from_file_location('c', H / 'scripts/01_classify.py')
FONT = '/System/Library/Fonts/Hiragino Sans GB.ttc'
font_manager.fontManager.addfont(FONT)
plt.rcParams['font.family'] = font_manager.FontProperties(fname=FONT).get_name()
plt.rcParams['pdf.fonttype'] = 42

# 分類表直接從 01 讀，避免兩處不一致
src = (H / 'scripts/01_classify.py').read_text()
CLASSES = eval(src[src.index('CLASSES = [') + 10: src.index(']\nCODE') + 1])
COL = {c[0]: c[2] for c in CLASSES}
# 合併組（依 P4／P5 併圖）：P1–P3 以組色概括，P4／P5 以細部色區分；未標示不上圖、不入統計分母
# 只保留 P4／P5 有的類別；政府、宗教、未標示不上圖、不入統計分母（2026-10-13 使用者指示）
GROUPS = [('G_RES', '住宅', ['RES'], '#F2D35B'), ('G_COM', '商業（一樓店面／商業／辦公）', ['MIX', 'COM', 'OFF'], '#E0473C'),
          ('G_IND', '產業（工業倉儲／產業遺構・古蹟）', ['IND', 'HER'], '#9B6FC8'), ('G_TRN', '停車與交通', ['TRN'], '#7D7D7D'),
          ('G_PUB', '醫療／文教', ['EDU', 'MED'], '#4BA3C7'), ('G_REC', '運動休閒', ['REC'], '#5DA95A')]
DROP = ('UNK', 'GOV', 'REL')
GOF = {c: g for g, _, cs, _ in GROUPS for c in cs}
GCOL = {g: col for g, _, _, col in GROUPS}
# A3 輸出：版面以 A1 毫米設計、實際紙張 A3（線性 0.5），字級 0.62、線寬 0.5（見 a3ize）
PRINT_K, FONT_K, FONT_MIN = 0.5, 0.62, 4.3
REL = FONT_K / PRINT_K

MM = 1 / 25.4
W, Hh = 841, 594
X0, Y0, X1, Y1 = 300935, 2770000, 307545, 2771910
ROAD_C, LINE_C, FRAME_C = '#4E97A6', '#3a3a3a', '#d4006a'

pieces = json.load(open(H / 'data/landuse_pieces_EPSG3826.geojson'))['features']
civ = json.load(open(H / 'data/civic_elevated_EPSG3826.json'))
elev, ramps, axis = shape(civ['elevated']), shape(civ['ramps']), shape(civ['axis'])
road = shape(json.load(open(BASE / 'road_surfaces_TWD97.geojson'))['features'][0]['geometry'])
q = json.load(open(BASE / 'qa.json'))
frame = box(X0, Y0, X1, Y1)

def poly_path(g):
    vs, cs = [], []
    for p in getattr(g, 'geoms', [g]):
        if p.geom_type != 'Polygon': continue
        for r in [p.exterior, *p.interiors]:
            a = np.asarray(r.coords)
            vs.append(a); cs.append([MPath.MOVETO] + [MPath.LINETO] * (len(a) - 2) + [MPath.CLOSEPOLY])
    if not vs: return None
    return MPath(np.concatenate(vs), np.concatenate(cs))

def lines(g):
    out = []
    for p in getattr(g, 'geoms', [g]):
        if p.geom_type in ('Polygon',):
            out += [np.asarray(r.coords) for r in [p.exterior, *p.interiors]]
        elif p.geom_type == 'LineString':
            out.append(np.asarray(p.coords))
        elif hasattr(p, 'geoms'):
            out += lines(p)
    return out

# 預先整理
by_cls = {}
for f in pieces:
    by_cls.setdefault(f['properties']['cls'], []).append(shape(f['geometry']))
cls_paths = {k: [poly_path(g) for g in v] for k, v in by_cls.items()}
# 範圍規則：被高架兩側 300 m 範圍線切到之線稿建物整棟為「範圍內」（實色），其餘淡化
OUT_ALPHA = 0.3
cls_in, cls_out = {}, {}
for f in pieces:
    pr = f['properties']; d_ = cls_in if pr['zone'] else cls_out
    d_.setdefault(pr['cls'], []).append(poly_path(shape(f['geometry'])))
grp_in = {g: [q for c in cs for q in cls_in.get(c, []) if q is not None] for g, _, cs, _ in GROUPS}
grp_out = {g: [q for c in cs for q in cls_out.get(c, []) if q is not None] for g, _, cs, _ in GROUPS}
SHOW_ROADS = False  # 道路邊線（底圖線稿）全頁隱藏（2026-10-11 使用者指示）；改 True 即恢復
road_lines = lines(road) if SHOW_ROADS else []
DB = json.load(open(H / 'data/drawing_buildings_zone_EPSG3826.geojson'))['features']
outline_in = [l for f in DB if f['properties']['zone'] for l in lines(shape(f['geometry']))]
outline_out = [l for f in DB if not f['properties']['zone'] for l in lines(shape(f['geometry']))]
outline_lines = outline_in + outline_out
bands = {d: lines(elev.buffer(d, resolution=24).intersection(frame).boundary) for d in (100, 200)}
ZF = json.load(open(H / 'data/zones_EPSG3826.geojson'))['features']
ZONES = [(f['properties'], shape(f['geometry'])) for f in ZF if 'id' in f['properties']]
CUTL = [shape(f['geometry']) for f in ZF if 'cut' in f['properties']]
ZONE_C = '#1A9BD7'
GREEN_C = {'PARK': ('#8CC97C', '公園'), 'GRASS': ('#CFE7C1', '草地／樹林'), 'SPORT': ('#B2DBA0', '運動場／遊戲場')}
GREEN = {f['properties']['kind']: shape(f['geometry']) for f in json.load(open(H / 'data/green_EPSG3826.geojson'))['features']}
green_paths = {k: [poly_path(p) for p in getattr(g, 'geoms', [g]) if p.geom_type == 'Polygon'] for k, g in GREEN.items()}
GZ = {r['分區']: r for r in csv.DictReader(open(H / 'data/統計_公園綠地_分區.csv', encoding='utf-8-sig'))}
# 停車連動（10_parking_landuse.py）：平面停車場地面範圍＋含停車場建物斜線；統計另列
SP_FC, SP_HC = '#F1F1F1', '#6E6E6E'
_SPF = json.load(open(H / 'data/surface_parking_EPSG3826.geojson'))['features']
surf_paths = [poly_path(shape(f['geometry'])) for f in _SPF if f['properties']['kind'] == 'surface']
surf_pts = np.array([f['geometry']['coordinates'] for f in _SPF if f['properties']['kind'] == 'surface_point']).reshape(-1, 2)
_PBF = json.load(open(H / 'data/parking_buildings_EPSG3826.geojson'))['features']
_bz = {f['properties']['bid']: f['properties']['zone'] for f in json.load(open(H / 'data/drawing_buildings_zone_EPSG3826.geojson'))['features']}
pk_in = [poly_path(shape(f['geometry'])) for f in _PBF if _bz.get(f['properties']['bid'])]
pk_out = [poly_path(shape(f['geometry'])) for f in _PBF if not _bz.get(f['properties']['bid'])]
PKZ = {r['單元']: r for r in csv.DictReader(open(H / 'data/統計_停車_土地使用_單元.csv', encoding='utf-8-sig'))}
def draw_parking(ax, lw):
    ax.add_collection(PathCollection([q for q in surf_paths if q is not None], facecolors=SP_FC, edgecolors=SP_HC, linewidths=.25 * lw,
                                     hatch='....', zorder=0.9))
    if len(surf_pts): ax.scatter(surf_pts[:, 0], surf_pts[:, 1], s=9 * lw, marker='s', facecolors=SP_FC, edgecolors=SP_HC, linewidths=.6 * lw, zorder=4.5)
    ax.add_collection(PathCollection([q for q in pk_out if q is not None], facecolors='none', edgecolors='#222', linewidths=0, hatch='//////', alpha=OUT_ALPHA, zorder=3.3))
    ax.add_collection(PathCollection([q for q in pk_in if q is not None], facecolors='none', edgecolors='#222', linewidths=0, hatch='//////', zorder=3.3))
short = lambda n: n.replace('高架', '').replace('路', '').replace('街', '').split('／')[0]
SHOW_UNDERBRIDGE = False  # 橋下空間（05_underbridge.py）暫不上圖；改 True 即恢復
UBF = json.load(open(H / 'data/underbridge_EPSG3826.geojson'))['features']
UB = {f['properties']['id']: f['properties'] for f in UBF if f['properties']['kind'] == '主線橋下'}
ub_paths = [poly_path(shape(f['geometry'])) for f in UBF]
UB_FC, UB_EC = '#F7B6CF', '#C2185B'
def draw_underbridge(ax, lw, labels=True):
    ax.add_collection(PathCollection([p for p in ub_paths if p is not None], facecolors=UB_FC, edgecolors=UB_EC,
                                     linewidths=.5 * lw, hatch='////', zorder=5.5))
    if not labels: return
    for f in UBF:
        pr = f['properties']
        if pr['kind'] != '主線橋下': continue
        g = shape(f['geometry']); c = g.representative_point()
        ax.annotate(f"{pr['id']} 橋下｜{pr['len_m']:,} m × {pr['avg_w_m']:.0f} m｜{pr['area_m2']/1e4:.2f} ha", (c.x, c.y),
                    xytext=(0, -14 - 6 * lw), textcoords='offset points', ha='center', va='top', fontsize=5 + 2.5 * lw, color=UB_EC,
                    fontweight='bold', zorder=9, clip_on=True, annotation_clip=True,
                    bbox=dict(boxstyle='round,pad=0.2', fc='white', ec=UB_EC, lw=.4, alpha=.9),
                    arrowprops=dict(arrowstyle='-', color=UB_EC, lw=.5))
ZLABEL = {z['id']: f"{z['id']}　{z['from']}—{z['to'].split('／')[0]}" for z, _ in ZONES}
# 設計介入單元：主角取自 zones 資料（01_classify.py UNIT_INFO）；界線沿實際路口中心線（走廊外為垂直引線）
ZONE_FUNC = {z['id']: z.get('info', '').split('（')[0] for z, _ in ZONES}
ZRANGE = f"Z1–Z{len(ZONES)}"
ZLIST = '｜'.join(f"{z['id']} {short(z['from'])}—{short(z['to'])}" for z, _ in ZONES)
import matplotlib.transforms as mtrans
CUT_G = [shape(f['geometry']) for f in ZF if 'cut' in f['properties']]
END_X = axis.coords[-1][0]
def zone_cuts(ax, lw, fs, below=0.03, func=True, pct=None, top_ext=4):
    # 分段虛線：圖內沿路口中心線，上下以垂直線延伸出圖框；圖框下方於各段之間標單元名稱與主角（或比例）
    # 單元過窄放不下文字時，奇偶單元上下錯層標示
    tr = mtrans.blended_transform_factory(ax.transData, ax.transAxes)
    pos = ax.get_position(); hmm = pos.height * Hh; wmm = pos.width * W; f = lambda mm: mm / hmm
    x0_, x1_ = ax.get_xlim(); mm_per_m = wmm / (x1_ - x0_)
    bx = [np.asarray(g.coords)[0][0] for g in CUT_G] + [END_X]
    lines_per = 2.9 if func else 2.6
    def need(k_):
        z = ZONES[k_][0]; t1 = f"{z['id']}  {short(z['from'])}—{short(z['to'])}"
        t2 = ZONE_FUNC[z['id']] if func else ''
        return max(len(t1), len(t2) * .9) * fs * 0.353 * REL
    stagger = any((min(bx[k + 1], x1_) - max(bx[k], x0_)) * mm_per_m < need(k) for k in range(len(ZONES))
                  if min(bx[k + 1], x1_) - max(bx[k], x0_) > 80)
    tier = fs * 0.353 * lines_per * REL
    b0 = f(3.5); top = 1 + f(top_ext); bot = -(b0 + f(tier * (2 if stagger else 1)))
    for g in CUT_G:
        c = np.asarray(g.coords)
        ax.plot(c[:, 0], c[:, 1], color=ZONE_C, lw=1.4 * lw, ls=(0, (6, 3)), zorder=8, clip_on=True)
        xb, xt = c[0][0], c[-1][0]
        if x0_ <= xb <= x1_: ax.plot([xb, xb], [0, bot], transform=tr, clip_on=False, color=ZONE_C, lw=1.4 * lw, ls=(0, (6, 3)), zorder=8)
        if x0_ <= xt <= x1_: ax.plot([xt, xt], [1, top], transform=tr, clip_on=False, color=ZONE_C, lw=1.4 * lw, ls=(0, (6, 3)), zorder=8)
    if x0_ <= END_X <= x1_:
        ax.plot([END_X, END_X], [top, bot], transform=tr, clip_on=False, color=ZONE_C, lw=.8 * lw, ls=(0, (6, 3)), zorder=8)
    for k_, (z, _) in enumerate(ZONES):
        a_, b_ = max(bx[k_], x0_), min(bx[k_ + 1], x1_)
        if b_ - a_ < 80: continue
        cx = (a_ + b_) / 2
        yy = -b0 - (f(tier) if stagger and k_ % 2 else 0)
        ax.text(cx, yy, f"{z['id']}  {short(z['from'])}—{short(z['to'])}", transform=tr, ha='center', va='top', fontsize=fs,
                fontweight='bold', color=ZONE_C, clip_on=False)
        if func:
            ax.text(cx, yy - f(fs * 0.353 * 1.45 * REL), ZONE_FUNC[z['id']], transform=tr, ha='center', va='top', fontsize=fs * .9, color='#333', clip_on=False)
        if pct is not None:
            pct(ax, tr, cx, yy - f(fs * 0.353 * 1.5 * REL), z['id'])

def draw_map(ax, lw):
    for k in ('GRASS', 'SPORT', 'PARK'):
        ax.add_collection(PathCollection(green_paths[k], facecolors=GREEN_C[k][0], edgecolors='none', zorder=0.8))
    ax.add_collection(LineCollection(road_lines, colors=ROAD_C, linewidths=0.18 * lw, zorder=1))
    for g, _, _, c in GROUPS:  # 組色概括；未標示不填色（僅留線稿輪廓）
        ax.add_collection(PathCollection(grp_out[g], facecolors=c, edgecolors='none', alpha=OUT_ALPHA, zorder=2))
        ax.add_collection(PathCollection(grp_in[g], facecolors=c, edgecolors='none', zorder=2.2))
    ax.add_collection(LineCollection(outline_out, colors=LINE_C, linewidths=0.08 * lw, alpha=OUT_ALPHA, zorder=3))
    ax.add_collection(LineCollection(outline_in, colors=LINE_C, linewidths=0.12 * lw, zorder=3.1))
    draw_parking(ax, lw)
    E = lines(elev)
    if SHOW_UNDERBRIDGE:
        draw_underbridge(ax, lw, labels=lw >= 1)
        ax.add_collection(LineCollection(E, colors='#111', linewidths=.7 * lw, zorder=6, capstyle='round'))
    else:
        ax.add_collection(LineCollection(E, colors='white', linewidths=3.6 * lw, zorder=5, capstyle='round'))
        ax.add_collection(LineCollection(E, colors='#111', linewidths=2.0 * lw, zorder=6, capstyle='round'))
    ax.add_collection(LineCollection(lines(ramps), colors='#111', linewidths=1.0 * lw, linestyles=(0, (2, 1.2)), zorder=6))
    # 分段：垂直虛線延伸出圖框，圖框下方標分段與功能
    zone_cuts(ax, lw, 8 + 1.5 * (lw - .6) / .4)

def place_axes(fig, x_mm, y_mm, w_mm, h_mm):
    return fig.add_axes([x_mm / W, y_mm / Hh, w_mm / W, h_mm / Hh])

def sheet_frames(ax, fs):
    for s in q['sheets']:
        b = s['bounds']
        ax.plot([b[0], b[2], b[2], b[0], b[0]], [b[1], b[1], b[3], b[3], b[1]], color=FRAME_C, lw=.6, zorder=7)
        ax.text(b[0] + 15, b[3] + 15, s['id'], fontsize=fs, color=FRAME_C, zorder=7, clip_on=True)

def legend(ax_or_fig, x, y, fs=9, ncol=1):
    h = [Patch(facecolor=c, edgecolor='#666', lw=.3, label=n) for _, n, _, c in GROUPS]
    h += [Patch(facecolor=GREEN_C[k][0], edgecolor='none', label=GREEN_C[k][1] + X('（地面，非建物）', '')) for k in ('PARK', 'GRASS', 'SPORT')]
    h += [Patch(facecolor=SP_FC, edgecolor=SP_HC, hatch='....', lw=.4, label=X('平面停車場（地面，非建物）', '平面停車場')),
          Patch(facecolor='white', edgecolor='#222', hatch='//////', lw=.4, label=X('含停車場之建物（一樓用途不變）', '含停車場之建物'))]
    h += ([Patch(facecolor=UB_FC, edgecolor=UB_EC, hatch='////', lw=.5, label='橋下空間（高架橋面投影，Z1–Z7）'),
           Line2D([], [], color='#111', lw=1, label='市民高架（主線車道中心線）')] if SHOW_UNDERBRIDGE else
          [Line2D([], [], color='#111', lw=3, label='市民高架')])
    h += [
          Line2D([], [], color='#111', lw=1.2, ls=(0, (2, 1.2)), label='匝道'),
          Line2D([], [], color=ZONE_C, lw=1.6, ls=(0, (6, 3)), label=X(f'設計介入單元界線 {ZRANGE}（沿實際路口中心線）', f'設計介入單元 {ZRANGE}')),
          Patch(facecolor=GCOL['G_RES'], edgecolor=LINE_C, lw=.4, label=X('高架兩側 300 m 範圍內建物（範圍線切到即整棟）', '高架兩側 300 m 範圍')),
          Patch(facecolor=GCOL['G_RES'], edgecolor=LINE_C, lw=.4, alpha=OUT_ALPHA, label=X('範圍外建物（淡化）', '範圍外'))]
    return ax_or_fig.legend(handles=h, loc='upper left', bbox_to_anchor=(x, y), frameon=False, fontsize=fs,
                            ncol=ncol, handlelength=2.2, handleheight=1.1, borderaxespad=0, labelspacing=.55, columnspacing=2)

def north_scale(fig, x, y, scale, lens):
    a = place_axes(fig, x, y, 120, 22); a.axis('off'); a.set_xlim(0, 120); a.set_ylim(0, 22)
    tot = lens[-1] / scale * 1000
    for i in range(len(lens) - 1):
        x0 = lens[i] / scale * 1000; x1 = lens[i + 1] / scale * 1000
        a.add_patch(plt.Rectangle((x0, 4), x1 - x0, 2.2, facecolor='#111' if i % 2 == 0 else 'white', edgecolor='#111', lw=.5))
    for L in lens:
        a.text(L / scale * 1000, 0, f'{L}', ha='center', va='bottom', fontsize=6)
    a.text(tot + 3, 4, 'm', fontsize=6)
    a.annotate('', xy=(110, 21), xytext=(110, 8), arrowprops=dict(arrowstyle='-|>', color='#111', lw=1))
    a.text(110, 3, 'N', ha='center', fontsize=8)

def header(fig, title, sub):
    fig.text(28 / W, 1 - 34 / Hh, title, fontsize=20, va='top')
    if not EX: fig.text(28 / W, 1 - 46 / Hh, sub, fontsize=9, va='top', color='#444')
    fig.add_artist(plt.Rectangle((10 / W, 10 / Hh), (W - 20) / W, (Hh - 20) / Hh, transform=fig.transFigure, fill=False, lw=.8))

NOTE = ('一樓判讀：OSM 標為住宅／未標示／辦公之建物，若一樓（或 12 m 內騎樓、人行道）有店家點（shop、餐飲、金融、藥局診所等；排除 level 標示地下或樓上者），改判為「一樓店面」（辦公大樓→商業、診所藥局→醫療）；政府、學校、宗教等維持原用途。整棟投影面積計入，店面比例以面積計會偏高。'
        '\n資料：底圖為 02_南京至仁愛擴幅_20261005 線稿（EPSG:3826，道路閉合外緣與可見建物輪廓）；使用屬性取自本地 OSM（檔名日期 2026-09-08）的 building／amenity／shop／office／tourism 標籤。'
        '\n每棟線稿建物依重疊之 OSM 建物切分著色；無對應標籤者列為「未標示／待調查」。為「一樓現況用途」概估，非法定使用分區，亦非逐棟現勘；OSM 店家點不完整，一樓店面比例為下限。'
        '\n產業遺構：OSM 標為 industrial，且具 historic 標籤或名稱含「工場／工廠」者（松山菸廠、臺北機廠、華山）。面積為建築投影面積，不含樓地板。'
        '\n設計介入單元：每段一個主要基地或界面類型；依紙本 A01–A07 藍色標記修訂（起點淡水河堤，新增承德路、光復南路，安東—光復依宵夜／居酒屋餐飲帶連續合併），界線沿實際路口中心線；統計採「範圍線切到即整棟」計入。'
        '\n公園綠地：OSM leisure=park／garden／pitch／playground、landuse=grass／forest 等地面範圍（含 multipolygon），以分區土地面積計比例，與建物投影面積分開計算。'
        '\n© OpenStreetMap contributors / ODbL｜2026-10-06')

# ---------- 統計 ----------
rows = list(csv.reader(open(H / 'data/統計_距離帶與分幅.csv', encoding='utf-8-sig')))
hdr = rows[0]; data = rows[1:]
_IU = [c[0] for c in CLASSES].index('UNK')
_ID = {[c[0] for c in CLASSES].index(k) for k in DROP}
def getraw(group):  # 細部類別實際面積；未標示、政府、宗教歸零（不入分母）
    return {r[1]: [0.0 if j in _ID else float(v) for j, v in enumerate(r[2:2 + len(CLASSES)])] for r in data if r[0] == group}
def get(group):
    return {k: [x / (sum(v) or 1) * 100 for x in v] for k, v in getraw(group).items()}
_CI = {c[0]: j for j, c in enumerate(CLASSES)}
def graw(group):  # 合併組實際面積
    return {k: [sum(v[_CI[c]] for c in cs) for _, _, cs, _ in GROUPS] for k, v in getraw(group).items()}
def gget(group):
    return {k: [x / (sum(v) or 1) * 100 for x in v] for k, v in graw(group).items()}
GLIST = [(g, n, c) for g, n, _, c in GROUPS]
def fa(m2):  # 面積格式：萬㎡ 或 ㎡
    return f'{m2 / 1e4:.1f}萬㎡' if m2 >= 1e4 else f'{m2:,.0f}㎡'
DARK = ('COM', 'OFF', 'GOV', 'REL', 'IND', 'TRN', 'REC', 'G_COM', 'G_IND', 'G_TRN', 'G_PUB', 'G_REC')

def stacked(ax, d, title, raw=None, cls=None):
    # raw：同鍵之實際面積（㎡）；比例旁標示實際數字，條末標總面積；cls 預設為合併組
    cls = cls or GLIST
    labels = list(d)[::-1]
    left = np.zeros(len(labels))
    for i, (k, n, c) in enumerate(cls):
        v = np.array([d[l][i] for l in labels])
        ax.barh(labels, v, left=left, color=c, edgecolor='white', lw=.4, height=.72)
        for j, (vv, ll) in enumerate(zip(v, left)):
            if vv >= 7:
                t = f'{vv:.0f}%' + (f'\n{fa(raw[labels[j]][i])}' if raw and vv >= 9 else '')
                ax.text(ll + vv / 2, j, t, ha='center', va='center', fontsize=5.8, linespacing=1.1,
                        color='white' if k in DARK else '#222')
        left += v
    if raw:
        for j, l in enumerate(labels):
            ax.text(101, j, f'計 {fa(sum(raw[l]))}', ha='left', va='center', fontsize=6.3, color='#444')
    ax.set_xlim(0, 100); ax.set_title(title, fontsize=10, loc='left', pad=6)
    ax.tick_params(labelsize=7.5, length=0); ax.set_xticks([0, 25, 50, 75, 100]); ax.set_xticklabels(['0', '25', '50', '75', '100%'])
    for s in ('top', 'right', 'left'): ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_linewidth(.4)

def half_bands(ex0, ex1):
    order = ['0-100', '100-200', '200-300', '>300']; t = {o: np.zeros(len(CLASSES)) for o in order}
    idx = {c[0]: i for i, c in enumerate(CLASSES)}
    for f in pieces:
        pr = f['properties']; x = shape(f['geometry']).representative_point().x
        if ex0 <= x < ex1: t[pr['band']][idx[pr['cls']]] += pr['area']
    return {o + ' m': list(v / v.sum() * 100) for o, v in t.items()}

summary = json.load(open(H / 'data/summary.json'))
import matplotlib.text as mtext
from matplotlib.collections import Collection
from matplotlib.patches import Patch as _P
plt.rcParams['hatch.linewidth'] = .35
def a3ize(fig, paper):
    # 以 A1 毫米排版之圖面縮為 A3：紙張 0.5、字級 FONT_K（下限 FONT_MIN）、線寬／點徑 0.5
    fig.set_size_inches(paper[0] * MM, paper[1] * MM)
    for t in fig.findobj(mtext.Text):
        t.set_fontsize(max(t.get_fontsize() * FONT_K, FONT_MIN))
    for l in fig.findobj(Line2D):
        l.set_linewidth(l.get_linewidth() * PRINT_K); l.set_markersize(l.get_markersize() * .6)
    for c in fig.findobj(Collection):
        c.set_linewidths(np.asarray(c.get_linewidths()) * PRINT_K)
        if hasattr(c, 'get_sizes') and len(c.get_sizes()): c.set_sizes(np.asarray(c.get_sizes()) * .3)
    for pa in fig.findobj(_P):
        pa.set_linewidth(pa.get_linewidth() * PRINT_K)
def save(pdf, fig, png):
    W_mm, H_mm = fig.get_size_inches() / MM
    a3ize(fig, (420, 297) if W_mm > H_mm else (297, 420))
    pdf.savefig(fig); fig.savefig(png, dpi=220); plt.close(fig)
out_pdf = H / f'市民高架沿線_南京西至仁愛_一樓使用現況分析_A3_20261013{SFX}.pdf'
with PdfPages(out_pdf) as pdf:
    # P1
    fig = plt.figure(figsize=(W * MM, Hh * MM))
    header(fig, '市民高架沿線｜南京西路至仁愛路｜一樓使用現況分析',
           'A3｜全線約 1:17000（左右滿版）｜一樓使用為準｜底圖：南京至仁愛擴幅線稿 2026-10-05｜屬性：OSM 2026-09-08｜2026-10-06')
    SC1 = (X1 - X0) / (W - 56)  # 左右滿版（A1 設計毫米；A3 輸出比例 ×2）
    mw, mh = (X1 - X0) / SC1, (Y1 - Y0) / SC1
    ax = place_axes(fig, 28, 594 - 60 - mh, mw, mh); ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_aspect('equal'); ax.axis('off')
    draw_map(ax, .6)
    ymap = 594 - 60 - mh
    lg = legend(fig, 28 / W, (ymap - 30) / Hh, fs=8, ncol=7)
    north_scale(fig, W - 28 - 120, ymap - 52, SC1 * 1000, [0, 250, 500, 1000])
    zraw = gget('分區'); zids = list(zraw); zarea = graw('分區')
    zname = {z['id']: f"{short(z['from'])}—\n{short(z['to'])}" for z, _ in ZONES}
    xs = np.arange(len(zids))
    # (2) 各合併組小圖：同一組在各單元的波動（各圖縱軸獨立，虛線為各段平均）
    cols, rows_ = 9, 1; x0, cw, ch, gx, gy = 28, (W - 56 - 8 * 8) / 9, (40 if not EX else 150), 8, 0; y0 = ymap - 78 - ch
    fig.text(28 / W, (y0 + rows_ * (ch + gy) + 14) / Hh, X(f'各用途於 {ZRANGE} 的比例波動（%｜實際建物投影面積；各圖縱軸獨立；虛線＝各段平均）', f'各用途於 {ZRANGE} 的變化'), fontsize=10, va='bottom')
    panels = [(g, nm.split('（')[0], c, np.array([zraw[z][n] for z in zids]), [fa(zarea[z][n]) for z in zids]) for n, (g, nm, c) in enumerate(GLIST)]
    panels.append(('GRN', '公園綠地（佔分區土地）', GREEN_C['PARK'][0], np.array([float(GZ[z]['綠地佔分區_%']) for z in zids]),
                   [f"{float(GZ[z]['綠地合計_ha']):.1f}ha" for z in zids]))
    panels.append(('SPK', '平面停車場（佔分區土地）', '#A9A6A1', np.array([float(PKZ[z]['平面停車場_佔土地_%']) for z in zids]),
                   [fa(float(PKZ[z]['平面停車場_m2'])) for z in zids]))
    panels.append(('CAR', '汽車格密度（格／ha）', '#6B6863', np.array([float(PKZ[z]['汽車格密度_格每ha']) for z in zids]),
                   [f"{int(PKZ[z]['汽車格合計']):,}格" for z in zids]))
    for n, (k, nm, c, v, rv) in enumerate(panels):
        r_, c_ = divmod(n, cols)
        ax_ = place_axes(fig, x0 + c_ * (cw + gx), y0 + (rows_ - 1 - r_) * (ch + gy), cw, ch)
        top = max(v.max() * (1.7 if not EX else 1.3), 2)
        ax_.bar(xs, v, width=.62, color=c, lw=0)
        ax_.plot(xs, v, color='#444', lw=.6, marker='o', ms=1.6, zorder=3)
        ax_.axhline(v.mean(), color='#444', lw=.5, ls=(0, (3, 2)))
        u_ = '' if k == 'CAR' else '%'; dg = 1 if k == 'SPK' else 0
        for j, vv in enumerate(v):
            ax_.text(xs[j], vv + top * .03, f'{vv:.{dg}f}{u_}\n{rv[j]}', ha='center', va='bottom', fontsize=5.6, color='#333', linespacing=1.05)
        ax_.set_ylim(0, top); ax_.set_xlim(-.6, len(zids) - .4); ax_.set_yticks([])
        ax_.set_xticks(xs); ax_.set_xticklabels(zids, fontsize=6); ax_.tick_params(length=0, pad=1.5)
        for sp in ('top', 'right', 'left'): ax_.spines[sp].set_visible(False)
        ax_.spines['bottom'].set_linewidth(.4)
        ax_.set_title(nm + (f'　{v.min():.0f}–{v.max():.0f}' if k == 'CAR' else f'　{v.min():.{dg}f}–{v.max():.{dg}f}%'), fontsize=8, loc='left', pad=2, color='#222')
    # 摘要（合併組）
    i = {g: n for n, (g, _, _) in enumerate(GLIST)}
    zone_lines = []
    for z, _ in ZONES:
        v = zraw[z['id']]
        top = sorted([(v[n], GLIST[n][1].split('（')[0]) for n in range(len(GLIST))], reverse=True)[:3]
        zone_lines.append(f"・{ZLABEL[z['id']]}：" + '、'.join(f'{nm} {pct:.0f}%' for pct, nm in top))
    zz = zraw
    allr = np.sum(np.array(list(zarea.values())), axis=0); allp = [x / allr.sum() * 100 for x in allr]
    unk_ha = sum(float(r[2 + _IU]) for r in data if r[0] == '分區') / 1e4
    txt = ['分析摘要（以一樓使用為準；不含政府、宗教、未標示）',
           f'・合併為六組：住宅 {allp[0]:.0f}%、商業 {allp[1]:.0f}%、產業 {allp[2]:.0f}%、停車與交通 {allp[3]:.0f}%、醫療文教 {allp[4]:.0f}%、運動休閒 {allp[5]:.0f}%（政府、宗教、未標示不計）。',
           f'・未標示：先調用 Z1–Z8 主題圖逐棟判讀與本機都更案基地補判；仍無對應之 {unk_ha:.1f} ha 不上圖、不入統計，清單見 workflow。',
           f'・停車：高架兩側 300 m 內汽車格 {sum(int(PKZ[z]["汽車格合計"]) for z in PKZ):,}、路外機車格 {sum(int(PKZ[z]["路外機車格"]) for z in PKZ):,}；',
           f'   含停車場之建物 {sum(int(PKZ[z]["含停車場建物_棟"]) for z in PKZ)} 棟（多為地下層，一樓用途不變）；平面停車場 {sum(float(PKZ[z]["平面停車場_m2"]) for z in PKZ)/1e4:.1f} ha，以 Z6 最高。',
           '', '各單元前三大用途（高架兩側 300 m）'] + zone_lines + [
           '', f'・商業最高：{max(zz, key=lambda z: zz[z][i["G_COM"]])}（{max(v[i["G_COM"]] for v in zz.values()):.0f}%）；住宅最高：{max(zz, key=lambda z: zz[z][i["G_RES"]])}（{max(v[i["G_RES"]] for v in zz.values()):.0f}%）；'
           f'產業最高：{max(zz, key=lambda z: zz[z][i["G_IND"]])}；醫療文教最高：{max(zz, key=lambda z: zz[z][i["G_PUB"]])}。']
    # 摘要：橫向兩欄（左：總覽與停車；右：各單元前三大用途）
    k_ = txt.index('各單元前三大用途（高架兩側 300 m）') - 1
    if not EX:
        fig.text(28 / W, (y0 - 14) / Hh, '\n'.join(txt[:k_] + txt[-1:]), fontsize=7.6, va='top', linespacing=1.7)
        fig.text(440 / W, (y0 - 14) / Hh, '\n'.join(txt[k_ + 1:-2]), fontsize=7.6, va='top', linespacing=1.7)
        fig.text(28 / W, 46 / Hh, NOTE, fontsize=6.5, va='top', color='#444', linespacing=1.6)
    save(pdf, fig, H / f'P1_全線_預覽{SFX}.png')

    # P2/P3 西段、東段 1:5000
    mid = (X0 + X1) / 2
    for n, (ex0, ex1, nm, zids) in enumerate([(X0, mid, '西段（Z1–Z5）', ['Z1', 'Z2', 'Z3', 'Z4', 'Z5']), (mid, X1, '東段（Z6–Z8）', ['Z6', 'Z7', 'Z8'])], start=2):
        fig = plt.figure(figsize=(W * MM, Hh * MM))
        header(fig, f'市民高架沿線｜一樓使用現況分析｜{nm}', 'A3｜1:10000｜一樓使用為準｜底圖：南京至仁愛擴幅線稿 2026-10-05｜屬性：OSM 2026-09-08｜2026-10-06')
        mw, mh = (ex1 - ex0) / 5, (Y1 - Y0) / 5
        ax = place_axes(fig, 28, 594 - 58 - mh, mw, mh); ax.set_xlim(ex0, ex1); ax.set_ylim(Y0, Y1); ax.set_aspect('equal'); ax.axis('off')
        ax.add_patch(plt.Rectangle((ex0, Y0), ex1 - ex0, Y1 - Y0, fill=False, lw=.4, ec='#999'))
        draw_map(ax, 1.0)
        legend(fig, 705 / W, (594 - 60) / Hh, fs=8.5)
        north_scale(fig, 705, 594 - 58 - mh, 5000, [0, 100, 200, 400])
        a3 = place_axes(fig, 95, 48, 300, 62); stacked(a3, {ZLABEL[k]: v for k, v in gget('分區').items() if k in zids}, X(f'{nm}：各單元（高架兩側 300 m 內）建物投影面積組成（%｜實際面積）', f'{nm}各單元建物組成'),
                                                              raw={ZLABEL[k]: v for k, v in graw('分區').items() if k in zids})
        if not EX: fig.text(430 / W, 112 / Hh, NOTE, fontsize=6.5, va='top', color='#444', linespacing=1.6, wrap=True)
        pk_txt = [X('各單元停車（高架兩側 300 m）', '各單元停車')] + [
            f"{z}  汽車格 {int(PKZ[z]['汽車格合計']):,}｜機車格 {int(PKZ[z]['路外機車格']):,}｜含停車場建物 {PKZ[z]['含停車場建物_棟']} 棟｜平面停車場 {fa(float(PKZ[z]['平面停車場_m2']))}（{PKZ[z]['平面停車場_佔土地_%']}%）"
            for z in zids]
        fig.text(430 / W, (60 if not EX else 104) / Hh, '\n'.join(pk_txt), fontsize=7.2, va='top', color='#222', linespacing=1.7)
        save(pdf, fig, H / f'P{n}_{nm[:2]}_預覽{SFX}.png')
    # ---------- P5：Z1–Z7 橋下空間 ----------
    if SHOW_UNDERBRIDGE:
        fig = plt.figure(figsize=(W * MM, Hh * MM))
        header(fig, '市民高架沿線｜Z1–Z7 橋下空間',
               'A1｜各分區 1:5000｜橋下空間＝市民高架主線橋面投影（依 OSM 車道數推估）｜分區依紙本藍色標記｜2026-10-06')
        civ_axis = shape(civ['axis'])
        allb = [p for k, _, _ in CLASSES for p in cls_paths.get(k, []) if p is not None]
        HALF = 140  # 每條帶狀圖：軸線南北各 140 m
        slots = [(28, 398), (28, 312), (28, 226), (28, 140), (430, 398), (430, 312), (430, 226)]
        for (z, zg), (sx, sy) in zip(ZONES, slots):
            pr = UB[z['id']]
            x0, x1 = zg.bounds[0], zg.bounds[2]
            seg = civ_axis.intersection(box(x0, Y0, x1, Y1)); cy = seg.centroid.y
            if x1 - x0 > 1900: x1 = x0 + 1900  # Z7：只畫到高架落地處附近（380 mm）
            mw = (x1 - x0) / 5; mh = 2 * HALF / 5
            ax = place_axes(fig, sx, sy, mw, mh); ax.set_xlim(x0, x1); ax.set_ylim(cy - HALF, cy + HALF); ax.set_aspect('equal'); ax.axis('off')
            ax.add_patch(plt.Rectangle((x0, cy - HALF), x1 - x0, 2 * HALF, fill=False, lw=.4, ec='#999'))
            ax.add_collection(LineCollection(road_lines, colors=ROAD_C, linewidths=.2, zorder=1))
            ax.add_collection(PathCollection(allb, facecolors='#E4E4E4', edgecolors='none', zorder=2))
            ax.add_collection(LineCollection(outline_lines, colors='#9a9a9a', linewidths=.08, zorder=3))
            draw_underbridge(ax, .8, labels=False)
            ax.add_collection(LineCollection(lines(elev), colors='#111', linewidths=.5, zorder=6))
            ax.add_collection(LineCollection([np.asarray(l.coords) for l in CUTL], colors=ZONE_C, linewidths=3, zorder=8))
            fig.text(sx / W, (sy + mh + 2) / Hh, f"{ZLABEL[z['id']]}", fontsize=10, fontweight='bold', color='white', va='bottom',
                     bbox=dict(boxstyle='round,pad=0.25', fc=ZONE_C, ec='none'))
            fig.text((sx + 75) / W, (sy + mh + 2) / Hh,
                     f"橋下長 {pr['len_m']:,} m｜平均寬 {pr['avg_w_m']:.0f} m｜面積 {pr['area_m2']:,} m2（{pr['area_m2']/1e4:.2f} ha）",
                     fontsize=9, color=UB_EC, va='bottom', fontweight='bold')
        # 統計長條
        zids = [z['id'] for z, _ in ZONES]
        ab = place_axes(fig, 450, 150, 170, 62)
        v = np.array([UB[k]['area_m2'] / 1e4 for k in zids])
        ab.bar(zids, v, color=UB_FC, edgecolor=UB_EC, hatch='////', lw=.6)
        for j, vv in enumerate(v): ab.text(j, vv, f'{vv:.2f}', ha='center', va='bottom', fontsize=7)
        ab.set_title('各分區主線橋下面積（ha）', fontsize=10, loc='left'); ab.tick_params(labelsize=7.5, length=0)
        for sp in ('top', 'right'): ab.spines[sp].set_visible(False)
        tot = sum(UB[k]['area_m2'] for k in zids)
        txt = ['橋下空間摘要',
               f'・Z1–Z7 主線橋下合計約 {tot/1e4:.1f} ha，長約 {sum(UB[k]["len_m"] for k in zids)/1000:.1f} km，平均寬 {tot/sum(UB[k]["len_m"] for k in zids):.0f} m。',
               f'・最大為 Z7（{UB["Z7"]["area_m2"]/1e4:.1f} ha）與 Z1（{UB["Z1"]["area_m2"]/1e4:.1f} ha）；最短為 Z2（{UB["Z2"]["len_m"]} m）與 Z6（{UB["Z6"]["len_m"]} m）。',
               '・橋下即市民大道平面車道與中央分隔帶，現況以車行為主。',
               '',
               '方法與限制',
               '・橋面寬＝OSM 各路段 lanes × 3.5 m ＋ 2.0 m（路肩、護欄），沿車道中心線兩側展開；',
               '  雙向分離橋面間距 ≤ 8 m 者合併為一處橋下空間。匝道另計（僅 Z7 有 0.10 ha）。',
               '・非實測橋面輪廓、未含橋墩位置與淨高；宜以竣工圖或航照描繪校正。',
               '・長度為分區軸線里程，Z7 依高架實際東端截短。']
        fig.text(640 / W, 212 / Hh, '\n'.join(txt), fontsize=8, va='top', linespacing=1.7)
        hh = [Patch(fc=UB_FC, ec=UB_EC, hatch='////', lw=.5, label='橋下空間（主線橋面投影）'), Line2D([], [], color='#111', lw=.8, label='高架車道中心線（OSM）'),
              Patch(fc='#E4E4E4', label='建物'), Line2D([], [], color=ROAD_C, lw=1, label='道路邊線（底圖線稿）'), Line2D([], [], color=ZONE_C, lw=3, label='分區界線')]
        fig.legend(handles=hh, loc='upper left', bbox_to_anchor=(640 / W, 135 / Hh), frameon=False, fontsize=8, ncol=2)
        north_scale(fig, 640, 40, 5000, [0, 100, 200, 400])
        fig.text(28 / W, 34 / Hh, '© OpenStreetMap contributors / ODbL｜底圖：南京至仁愛擴幅線稿 2026-10-05｜2026-10-06', fontsize=6.5, color='#444')
        pdf.savefig(fig); fig.savefig(H / 'P5_Z1-Z7橋下空間_預覽.png', dpi=110); plt.close(fig)
    # ---------- 產業分布圖：自一樓使用圖逐色提取（同分類、同色）；併圖＝同一張圖顯示多類，各自保留顏色 ----------
    zids = [z['id'] for z, _ in ZONES]
    zr = get('分區'); ci = {c[0]: n for n, c in enumerate(CLASSES)}
    zarea = getraw('分區')  # 細部類別面積
    CN = {k: (nm, c) for k, nm, c in CLASSES}; CN['GRN'] = ('公園綠地', GREEN_C['PARK'][0])
    all_paths = [p for k, _, _ in CLASSES for p in cls_paths.get(k, []) if p is not None]
    PK = json.load(open(H / 'data/parking_streetview_EPSG3826.geojson'))
    SURV = list(csv.DictReader(open(H / 'data/工業倉儲使用現況調查.csv', encoding='utf-8-sig')))
    PKS = {r['單元']: r for r in csv.DictReader(open(H / 'data/統計_停車供給_單元.csv', encoding='utf-8-sig'))}
    PMA = json.load(open(H / 'data/parking_pma_EPSG3826.geojson'))
    PARK_BC = '#3A78B5'
    CN['PKC'] = ('汽車格（路外＋路邊）', '#4A4A4A'); CN['PKM'] = ('機車格（路外）', '#A6A6A6')
    def zval(k, z):
        if k == 'GRN': return float(GZ[z]['綠地佔分區_%'])
        if k == 'PKC': return float(PKS[z]['占全線汽車格_%'])
        if k == 'PKM': return float(PKS[z]['占全線機車格_%'] or 0)
        return zr[z][ci[k]]
    def zreal(k, z):
        if k == 'GRN': return f"{float(GZ[z]['綠地合計_ha']):.1f}ha"
        if k == 'PKC': return f"{int(PKS[z]['汽車格合計']):,}格"
        if k == 'PKM': return f"{int(PKS[z]['路外機車格']):,}格"
        return fa(zarea[z][ci[k]])
    # 單欄垂直堆疊：各圖同比例、同東西範圍，分段界線上下對齊可垂直比對
    sy0, sy1 = Y0, Y1  # 每頁三圖：取完整南北範圍
    PSC = 12.5  # A1 直式，1:12500
    pw, ph = (X1 - X0) / PSC, (sy1 - sy0) / PSC
    def site_label(ax_, e, n, txt, c):
        ax_.annotate(txt, (e, n), xytext=(0, 16), textcoords='offset points', ha='center', fontsize=6.3, color='#222', zorder=10,
                     bbox=dict(boxstyle='round,pad=0.2', fc='white', ec=c, lw=.6), arrowprops=dict(arrowstyle='-', color=c, lw=.6), annotation_clip=True)
    all_in = [p for k, _, _ in CLASSES for p in cls_in.get(k, []) if p is not None]
    all_out = [p for k, _, _ in CLASSES for p in cls_out.get(k, []) if p is not None]
    def extract_panel(fig, x, y, keys, title, extra=None):
        ax_ = place_axes(fig, x, y, pw, ph); ax_.set_xlim(X0, X1); ax_.set_ylim(sy0, sy1); ax_.set_aspect('equal'); ax_.axis('off')
        ax_.add_patch(plt.Rectangle((X0, sy0), X1 - X0, sy1 - sy0, fill=False, lw=.3, ec='#bbb'))
        if 'GRN' in keys:
            for g in ('GRASS', 'SPORT', 'PARK'):
                ax_.add_collection(PathCollection(green_paths[g], facecolors=GREEN_C[g][0], edgecolors='none', zorder=0.8))
        ax_.add_collection(LineCollection(road_lines, colors=ROAD_C, linewidths=0.1, alpha=.6, zorder=1))
        # 其他建物：範圍內灰、範圍外淡灰；提取類別：範圍內實色、範圍外淡化
        ax_.add_collection(PathCollection(all_out, facecolors='#D9D9D9', edgecolors='none', alpha=.45, zorder=2))
        ax_.add_collection(PathCollection(all_in, facecolors='#CFCFCF', edgecolors='none', zorder=2.1))
        for k in keys:
            if k != 'GRN':
                ax_.add_collection(PathCollection([p for p in cls_out.get(k, []) if p is not None], facecolors=CN[k][1], edgecolors='none', alpha=OUT_ALPHA, zorder=3))
                ax_.add_collection(PathCollection([p for p in cls_in.get(k, []) if p is not None], facecolors=CN[k][1], edgecolors='none', zorder=3.1))
        E = lines(elev)
        ax_.add_collection(LineCollection(E, colors='white', linewidths=1.8, zorder=5)); ax_.add_collection(LineCollection(E, colors='#111', linewidths=1.0, zorder=6))
        if extra: extra(ax_)
        # 標題：各類色票＋名稱＋全幅比例
        xx = x
        fig.text(x / W, (y + ph + 7.5) / Hh, title, fontsize=10, fontweight='bold', va='bottom')
        for k in keys:
            nm, c = CN[k]
            fig.add_artist(plt.Rectangle((xx / W, (y + ph + 2) / Hh), 4.5 / W, 3.4 / Hh, transform=fig.transFigure, fc=c, ec='#666', lw=.3))
            tot = summary['class_pct'].get(nm)
            lbl = nm.split('（')[0] + (f' {tot}%' if tot is not None else '（佔土地）')
            fig.text((xx + 6) / W, (y + ph + 1.9) / Hh, lbl, fontsize=7.6, va='bottom')
            xx += 6 + len(lbl) * 2.55 + 6
        # 分段虛線延伸出圖框；圖框下方標分段與各類比例（單類最高者色底；多類各自顏色並列）
        def pct(ax__, tr, cx, yy, zid):
            if len(keys) == 1:
                k = keys[0]; v = [zval(k, q) for q in zids]; mx = max(v); val = zval(k, zid)
                ax__.text(cx, yy, f'{val:.0f}%', transform=tr, ha='center', va='top', fontsize=6.6, clip_on=False,
                          color='white' if val == mx and val > 0 else '#333', fontweight='bold' if val == mx else 'normal',
                          bbox=dict(boxstyle='round,pad=0.18', fc=CN[k][1] if val == mx and val > 0 else 'white', ec='none'))
            else:
                dx = 95; x0_ = cx - dx * (len(keys) - 1) / 2
                for j, k in enumerate(keys):
                    ax__.text(x0_ + j * dx, yy, f'{zval(k, zid):.0f}', transform=tr, ha='center', va='top', fontsize=6.6, clip_on=False,
                              color='white', fontweight='bold', bbox=dict(boxstyle='round,pad=0.15', fc=CN[k][1], ec='none'))
        zone_cuts(ax_, .7, 6.6, below=0.03, func=False, top_ext=0)
        return ax_
    def extra_ind(ax_):
        for r in SURV:
            if r['現況判定類別'] == '工業／倉儲':
                (r['使用狀態'] != '待查' or not EX) and site_label(ax_, float(r['E']), float(r['N']), X(f"{r['場址'].split('（')[0]}｜{r['使用狀態']}", r['場址'].split('（')[0]), CN['IND'][1])
    def extra_her(ax_):
        for r in SURV:
            if r['現況判定類別'] == '產業遺構／登錄古蹟・歷史建築':
                site_label(ax_, float(r['E']), float(r['N']), r['現況說明'].split('（')[0], CN['HER'][1])
        site_label(ax_, 301710, 2771165, '三井倉庫', CN['HER'][1])
    def extra_trn(ax_):
        for f in PK['features']:
            pr = f['properties']; g = shape(f['geometry'])
            if pr['kind'] == 'section':
                x_, y_ = g.exterior.xy
                ax_.fill(x_, y_, fc='none', ec='#444', hatch='////', lw=.6, zorder=4)
                ax_.text(g.centroid.x, g.centroid.y - 45, f"{pr['name']} B{pr['levels']}", ha='center', va='top', fontsize=5.6, color='#333', zorder=9, clip_on=True)
            elif pr['kind'] == 'entrance':
                ax_.plot(g.x, g.y, marker='v', ms=3.5, color='#222', zorder=9)
            else:
                if not EX: ax_.plot(g.x, g.y, marker='*', ms=7, mfc='#FFD400', mec='#222', mew=.5, zorder=10)
        # 停車場建物（09_parking_buildings.py 就近判讀）：藍色填色；範圍外淡化
        PBF = json.load(open(H / 'data/parking_buildings_EPSG3826.geojson'))['features']
        for inr in (False, True):
            ps = [poly_path(shape(f['geometry'])) for f in PBF if bool(f['properties']['zone']) == inr]
            ax_.add_collection(PathCollection([q for q in ps if q is not None], facecolors=PARK_BC, edgecolors='#1F4E79', linewidths=.25,
                                              alpha=1 if inr else OUT_ALPHA, zorder=3.2))
        # 北市好停車：路外停車場（圓面積∝汽車格）、路邊汽車格（小點）
        cb = np.array([f['geometry']['coordinates'] for f in PMA['features'] if f['properties']['kind'] == 'curb' and f['properties']['car']])
        if len(cb): ax_.scatter(cb[:, 0], cb[:, 1], s=.5, c='#E67E22', lw=0, zorder=4.5)
        lt = [f for f in PMA['features'] if f['properties']['kind'] == 'lot' and f['properties']['car'] > 0]
        xy = np.array([f['geometry']['coordinates'] for f in lt]); cars = np.array([f['properties']['car'] for f in lt])
        ax_.scatter(xy[:, 0], xy[:, 1], s=np.sqrt(cars) * 2.2, fc='#4A4A4A', ec='white', lw=.4, alpha=.85, zorder=4.6)
    SUB = 'A3 直式｜各圖 1:25000，東西範圍與比例一致，分段界線上下對齊｜自 P1 一樓使用圖逐色提取，同分類同色；併圖各類保留原色｜圖下長條＝各單元比例 %＋實際數字｜2026-10-06'
    NOTE2 = ('分類與色彩同 P1（一樓使用為準）。產業遺構／古蹟：文化部文化資產局國家文化資產網開放資料（2026-10-13 抓取）臺北市已登錄古蹟、歷史建築、聚落建築群、紀念建築，登錄點對應線稿建物（data/文資登錄_對應建物.csv）；工業／倉儲經使用現況調查（抽水站→公共服務；捷運維修、車站機房→交通），'
             '\n仍在生產者（建國啤酒廠，已登錄古蹟）保留工業；北市一號倉庫為登錄歷史建築。交通停車：地下停車場分段、出入口與街景查核點取自本機 Blender 重建專案 Civic_Rebuild_20260909（停管處分段資料；外框為假設包絡，非實測）。'
             '\n停車供給：北市好停車（停管處 itaipeiparking.pma.gov.taipei，2026-10-11 抓取）路外停車場 422 處、路邊汽車格 5,936 格；停車場代表點落於單元內即計入，比例＝占 Z1–Z8 合計之百分比；機車路邊格未逐格公開，僅計路外機車格。'
             '\n公園綠地比例以分區土地面積計，其餘以建物投影面積計（不含未標示）；未標示建物先以主題圖與都更案補判，仍無對應者不上圖。© OpenStreetMap contributors / ODbL｜底圖：南京至仁愛擴幅線稿 2026-10-05')
    BX = [np.asarray(g.coords)[0][0] for g in CUT_G] + [END_X]
    def mini_chart(fig, x, y, w, h, keys):
        # 與地圖同寬、同東西座標：每單元的長條置於該單元正下方
        a = place_axes(fig, x, y, w, h); a.set_xlim(X0, X1); n_ = len(keys)
        top_ = max(max(zval(k, z) for z in zids) for k in keys) * (2.8 if 'PKC' in keys else 1.9) or 1
        for i_, z in enumerate(zids):
            cx = (BX[i_] + BX[i_ + 1]) / 2; zw = BX[i_ + 1] - BX[i_]
            bw = min(zw * .55, 70 * n_) / n_
            for j, k in enumerate(keys):
                vv = zval(k, z); xx = cx + (j - (n_ - 1) / 2) * bw
                a.bar(xx, vv, width=bw * .9, color=CN[k][1], edgecolor='#666' if k == 'UNK' else 'none', lw=.3)
                if n_ >= 3:  # 類別多：只標比例，且只標 ≥1%
                    if vv >= 1: a.text(xx, vv + top_ * .03, f'{vv:.0f}', ha='center', va='bottom', fontsize=4.8, color='#333')
                elif vv >= .5:
                    a.text(xx, vv + top_ * .03, f'{vv:.0f}%\n{zreal(k, z)}', ha='center', va='bottom', fontsize=4.8, color='#333', linespacing=1.05)
            if 'PKC' in keys:
                a.text(cx, top_ * .99, f"{z} 計 {int(PKS[z]['汽車格合計']) + int(PKS[z]['路外機車格']):,} 格\n汽 {int(PKS[z]['汽車格合計']):,}｜機 {int(PKS[z]['路外機車格']):,}",
                       ha='center', va='top', fontsize=4.9, color='#222', fontweight='bold', linespacing=1.15)
        for xb in BX: a.axvline(xb, color=ZONE_C, lw=.6, ls=(0, (6, 3)))
        a.set_ylim(0, top_); a.set_xticks([]); a.set_yticks([])
        for sp in ('top', 'right', 'left'): a.spines[sp].set_visible(False)
        a.spines['bottom'].set_linewidth(.4)
        a.text(0, 1.02, X(('各單元占全線停車格 %｜格數（深灰＝汽車格〔路外＋路邊〕、淺灰＝路外機車格）' if 'PKC' in keys else '各單元比例 %｜實際面積') + ('（公園綠地以土地面積計）' if 'GRN' in keys else ''), '深灰＝汽車格　淺灰＝機車格' if 'PKC' in keys else ''), transform=a.transAxes, fontsize=5.8, color='#666', va='bottom')
    def page(title, panels):
        fig = plt.figure(figsize=(W * MM, Hh * MM))
        header(fig, title, SUB)
        x0 = (W - pw) / 2; top0 = Hh - 84; step = (top0 - 40) / len(panels)
        for j, (keys, ttl, ex, *ck) in enumerate(panels):
            y = top0 - j * step - 14 - ph
            extract_panel(fig, x0, y, keys, ttl, ex)
            mini_chart(fig, x0, y - 24 - 30, pw, 30, ck[0] if ck else keys)
        hh = [Line2D([], [], color='#111', lw=2.5, label='市民高架'),
              Line2D([], [], color=ZONE_C, lw=1.6, ls=(0, (6, 3)), label=f'設計介入單元界線 {ZRANGE}'),
              Patch(fc='#CFCFCF', label=X('其他建物：300 m 範圍內（切到即整棟）', '其他建物（300 m 範圍內）')), Patch(fc='#D9D9D9', alpha=.45, label=X('範圍外（淡化）', '範圍外')),
              Patch(fc='none', ec='#444', hatch='////', lw=.6, label=X('地下停車場分段（假設包絡）', '市民大道地下停車場')),
              Line2D([], [], marker='v', ls='', color='#222', ms=4, label='停車場出入口'),
              Patch(fc='#3A78B5', ec='#1F4E79', lw=.4, label='停車場建物'),
              Line2D([], [], marker='o', ls='', mfc='#4A4A4A', mec='white', ms=6, label=X('路外停車場（圓面積∝汽車格）', '路外停車場（圓大小＝汽車格數）')),
              Line2D([], [], marker='o', ls='', mfc='#E67E22', mec='none', ms=2.5, label='路邊汽車格')]
        fig.legend(handles=hh, loc='upper left', bbox_to_anchor=(x0 / W, (Hh - 52) / Hh), frameon=False, fontsize=6.8, ncol=4, columnspacing=1.2, handlelength=2)
        if not EX: fig.text(x0 / W, 30 / Hh, NOTE2, fontsize=5.4, color='#444', va='top', linespacing=1.5, wrap=True)
        return fig
    def extra_indher(ax_): extra_ind(ax_); extra_her(ax_)
    PAGES = [('市民高架沿線｜產業分布圖（一）商業、產業與停車', [
                (['MIX', 'COM', 'OFF'], '商業｜一樓店面＋商業＋辦公', None),
                (['IND', 'HER'], X('產業｜工業／倉儲（使用中）＋產業遺構／登錄古蹟・歷史建築（文資局登錄，各段重抓）', '產業｜工業倉儲＋登錄古蹟・歷史建築'), extra_indher),
                (['TRN'], X('停車與交通｜路外停車場（圓∝汽車格）＋路邊汽車格＋市民大道地下停車場', '停車與交通'), extra_trn, ['PKC', 'PKM'])]),
             ('市民高架沿線｜產業分布圖（二）居住、醫療文教與開放空間', [
                (['RES'], '住宅', None), (['MED', 'EDU'], '醫療＋文教', None), (['REC', 'GRN'], '運動休閒＋公園綠地', None)])]
    W_, H_ = W, Hh; W, Hh = 594, 841  # 產業分布圖改 A1 直式
    for n_, (ttl, panels) in enumerate(PAGES, start=4):
        fig = page(ttl, panels)
        save(pdf, fig, H / f'P{n_}_產業分布_{"一二"[n_ - 4]}_預覽{SFX}.png')
    W, Hh = W_, H_
print(out_pdf)

# ---------- 額外 A3：設計介入單元 Z1–Z8 建物投影面積組成（%｜實際面積） ----------
W, Hh = 420, 297
out_a3 = H / f'市民高架沿線_設計介入單元建物組成_A3_20261013{SFX}.pdf'
fig = plt.figure(figsize=(W * MM, Hh * MM))
header(fig, f'市民高架沿線｜設計介入單元 {ZRANGE} 建物投影面積組成',
       'A3｜高架兩側 300 m 內（範圍線切到即整棟計入）｜一樓使用為準，合併為六組，不含未標示｜柱內：比例 %＋實際面積｜柱頂：單元建物投影總面積｜西 → 東｜2026-10-11')
zraw = gget('分區'); zarea = graw('分區'); zids = list(zraw)
zname = {z['id']: f"{short(z['from'])}—\n{short(z['to'])}" for z, _ in ZONES}
a2 = place_axes(fig, 24, 92, 300, 153)
xs = np.arange(len(zids)); bw = .6; bottom = np.zeros(len(zids))
for n, (k, nm, c) in enumerate(GLIST):
    v = np.array([zraw[z][n] for z in zids])
    a2.bar(xs, v, bottom=bottom, width=bw, color=c, edgecolor='white', lw=.4, zorder=2)
    for j in range(len(zids) - 1):
        a2.fill([xs[j] + bw / 2, xs[j + 1] - bw / 2, xs[j + 1] - bw / 2, xs[j] + bw / 2],
                [bottom[j], bottom[j + 1], bottom[j + 1] + v[j + 1], bottom[j] + v[j]], color=c, alpha=.28, lw=0, zorder=1)
    for j, z in enumerate(zids):
        if v[j] >= 3.5:
            t = f'{v[j]:.0f}%' + (f'  {fa(zarea[z][n])}' if v[j] >= 4.5 else '')
            a2.text(xs[j], bottom[j] + v[j] / 2, t, ha='center', va='center', fontsize=6.2, zorder=3,
                    color='white' if k in DARK else '#222')
    bottom += v
for j, z in enumerate(zids):
    a2.text(xs[j], 101.5, f'計 {fa(sum(zarea[z]))}', ha='center', va='bottom', fontsize=7, color='#222', fontweight='bold')
a2.set_xticks(xs); a2.set_xticklabels([f'{z}\n{zname[z]}' for z in zids], fontsize=7.5, linespacing=1.3)
a2.set_ylim(0, 106); a2.set_yticks([0, 25, 50, 75, 100]); a2.set_yticklabels(['0', '25', '50', '75', '100%'], fontsize=7)
a2.tick_params(length=0); a2.set_xlim(-.5, len(zids) - .5)
for sp in ('top', 'right', 'bottom'): a2.spines[sp].set_visible(False)
a2.spines['left'].set_linewidth(.4)
# 停車列：與上方柱同欄對齊——汽車格／機車格（格）＋含停車場建物、平面停車場
ap = place_axes(fig, 24, 42, 300, 26); xs2 = np.arange(len(zids)); car = np.array([int(PKZ[z]['汽車格合計']) for z in zids]); mo = np.array([int(PKZ[z]['路外機車格']) for z in zids])
ap.bar(xs2 - .15, car, width=.28, color='#5E5E5E'); ap.bar(xs2 + .15, mo, width=.28, color='#B5B5B5')
tp = max(car.max(), mo.max()) * 1.35
for j, z in enumerate(zids):
    ap.text(xs2[j] - .15, car[j] + tp * .02, f'{car[j]:,}', ha='center', va='bottom', fontsize=5.6)
    ap.text(xs2[j] + .15, mo[j] + tp * .02, f'{mo[j]:,}', ha='center', va='bottom', fontsize=5.6, color='#555')
    ap.text(xs2[j], -tp * .12, f"含停車場建物 {PKZ[z]['含停車場建物_棟']} 棟\n平面停車場 {fa(float(PKZ[z]['平面停車場_m2']))}（{PKZ[z]['平面停車場_佔土地_%']}%）",
            ha='center', va='top', fontsize=5.6, color='#333', linespacing=1.35)
ap.set_xlim(-.5, len(zids) - .5); ap.set_ylim(0, tp); ap.set_xticks([]); ap.set_yticks([])
for sp in ('top', 'right', 'left'): ap.spines[sp].set_visible(False)
ap.spines['bottom'].set_linewidth(.4)
ap.set_title('停車｜汽車格（深灰）／路外機車格（淺灰）', fontsize=7.5, loc='left', pad=3, color='#222')
fig.legend(handles=[Patch(fc=c, label=nm) for _, nm, c in GLIST][::-1], loc='upper left', bbox_to_anchor=(334 / W, 245 / Hh),
           frameon=False, fontsize=7.5, labelspacing=.7)
fig.text(334 / W, 92 / Hh, '\n'.join(f"{z['id']} {short(z['from'])}—{short(z['to'])}｜{z.get('info', '').split('（')[0]}" for z, _ in ZONES),
         fontsize=6.3, va='top', linespacing=1.6, color='#333')
if not EX: fig.text(24 / W, 22 / Hh, '資料：南京至仁愛擴幅線稿 2026-10-05（EPSG:3826）；用途：OSM 2026-09-08 以一樓使用為準；建物投影面積，不含樓地板。相鄰柱之淡色帶連接同一用途，看各單元間消長。© OpenStreetMap contributors / ODbL',
         fontsize=6, color='#444')
fig.savefig(out_a3); fig.savefig(H / f'A3_設計介入單元建物組成_預覽{SFX}.png', dpi=130); plt.close(fig)
print(out_a3)
