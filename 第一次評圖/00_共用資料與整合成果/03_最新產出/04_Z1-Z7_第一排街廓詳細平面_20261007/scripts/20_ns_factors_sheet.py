# 主題圖：影響南北通行之元素＋該段特性建築（先做 Z1），A1 一張
#   表現（使用者指定 2026-10-11 修訂）：
#     建物＝依樓高 5 級灰（2026-10-15；原塗黑；不畫街廓輪廓）；地圖上不標文字。
#     （2026-10-11 再修訂：紅色改不透明；十字路口〔平面穿越行穿線〕不上圖）
#     通行元素（地下街、地下連通道、捷運站體、出入口、人行天橋）同一圖層、紅色色塊，
#       每塊各自疊加 → 重複（上下重疊）處較深、不重複處較淺。捷運站、地下街範圍取 OSM。
#     中央分隔島、圍牆／圍籬／綠籬、停車場車道出入口、高架匝道、無平面穿越長段不上圖。
#     特性建築＝酒紅實心平面剪影（原位、無外框）；公辦都更基地範圍（U01）非建物，不上圖（列於下方表）。
#   資料：19_ns_factors.py → data/{Z}_ns_factors_EPSG3826.geojson（cls = pass_area／char）
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
from shapely.geometry import shape, box
from shapely.ops import unary_union

H = Path(__file__).resolve().parents[1]
ZONE = sys.argv[1] if len(sys.argv) > 1 else 'Z1'
_argv = sys.argv; sys.argv = [_argv[0], 'A1']
spec = importlib.util.spec_from_file_location('sheets', H / 'scripts/05_sheets.py')
F = importlib.util.module_from_spec(spec); spec.loader.exec_module(F)
sys.argv = _argv
S = F.S
SCALE, m2mm, W, Hh, MM = F.SCALE, F.m2mm, F.W, F.Hh, F.MM
RED, MAG, BLD_C = '#DF9134', '#8E1B3E', '#141414'   # 橘（通行元素；2026-10-13 使用者「橘色太亮、彩度調低」，原朱紅 #FF5A1F）、酒紅（特性建築）
# Z1–Z8 色彩統一（2026-10-13 使用者「每張圖的色塊都可以互通」）：同一顏色全八張只代表一種意義。以 OKLab ΔE＋Machado 2009 色覺模擬驗證：
#   各圖內兩兩 正常 ≥ 15、紅綠色弱 ≥ 8（淡酒紅↔路徑 15.4）；跨圖不同意義 ≥ 10；酒紅色階相鄰 ΔL ≥ 0.06。改色：橘、酒紅色階 2–4 級、淡酒紅、
#   住宅（原藍，與 Z3 商辦撞色）→黃、運動場（原青綠，與 Z3 日常生活店家撞色）→綠、開放空間（Z4 純綠地、Z5 空地原橄欖黃）→同一淡綠、Z8 匝道兩灰
PA_ALPHA = 1.0           # 通行元素不透明（使用者 2026-10-11 指定）
NO_MAP = {'平面穿越行穿線'}   # 十字路口不上圖（僅列於下方表）
DATA = json.load(open(H / f'data/{ZONE}_ns_factors_EPSG3826.geojson'))
FE = [(shape(f['geometry']), f['properties']) for f in DATA['features']]
SLAB = shape(DATA['slab'])
PA = [(g, p) for g, p in FE if p['cls'] == 'pass_area']
PA_ALL = PA      # 圖框計算用（含圖框外之周邊站體）；Z7 起繪圖、圖例只用圖框內者（見 map_frame 之後）
CHAR = sorted([(g, p) for g, p in FE if p['cls'] == 'char'], key=lambda gp: gp[1]['id'])
SIL = [(g, p) for g, p in CHAR if not p.get('site') and p['tier'] not in ('D', 'H', 'P', 'M', 'R', 'F', 'V', 'O', 'N')]   # 剪影：建物（含規劃中 B02、U17）
# 運動生活空間（Z4 起，使用者 2026-10-12 指定）：住宅建物（tier H，藍）、運動場（tier P，青綠；不開放者不上圖）——沿用 Z3 已驗證之兩色
HOUSE_C, SPORT_C, SPORT_LT = '#FDD856', '#4D8C3E', '#B8D1B2'   # 住宅黃、運動場綠（2026-10-13 統一）；SPORT_LT＝運動場綠 40%＋白（鄰近，長條用）
HOUSE = [(g, p) for g, p in CHAR if p['tier'] == 'H']
SPORT = [(g, p) for g, p in CHAR if p['tier'] == 'P' and p.get('public', True)]
_shf = H / f'data/{ZONE}_sports_housing_summary.json'
SH = json.load(open(_shf)) if (HOUSE or SPORT) and _shf.exists() else None     # 30_sports_housing 摘要（戶數、運動種類面積）
# 純綠地＋公園步道（Z4 起，使用者 2026-10-12：「加標純綠地的範圍」「公園有步道要加上步道」；32_green_paths）
GREEN_C = '#91D099'      # 淡綠＝開放空間（綠地、空地、廣場；Z4 純綠地、Z5 空地圖層共用，2026-10-13 統一）
_gpf, _gps = H / f'data/{ZONE}_green_paths_EPSG3826.geojson', H / f'data/{ZONE}_green_paths_summary.json'
_gp = json.load(open(_gpf))['features'] if _gpf.exists() else []
GREEN = [shape(f['geometry']) for f in _gp if f['properties']['kind'] == 'green']
PPATH = [shape(f['geometry']) for f in _gp if f['properties']['kind'] in ('parkpath', 'parkpave')]   # 公園步道＋公園內硬鋪面（廣場、停車），同淡灰
GPS = json.load(open(_gps)) if _gps.exists() else None
# 商業空間之密集（Z5 起，使用者 2026-10-12 指定；31_commercial_space）：商業空間 tier M（四種形式，酒紅色階）、古蹟 R（紫，建國啤酒廠）、
#   配套措施 F（步行街／廣場、公園綠地＝藍面；停車場＝深灰圓環〔面積∝汽＋機車格〕；公車站、YouBike、公廁＝藍色小記號）、可用空地 V（橄欖黃）。
#   配色經 OKLab ΔE＋Machado 2009 色覺模擬（紅／綠／藍色弱）驗證：與橘、建物黑、路徑淡灰兩兩最小 ΔE 0.085
COM_C = {'大型商場／市場': '#8E1B3E', '商業大樓／旅館': '#A4435F', '騎樓店面': '#B95F7D', '臨街店面': '#D2779C'}   # 酒紅色階（2026-10-13 統一，同 NIGHT_C）
HER_C, SUP_C, VAC_C, PARK_C = '#5E3C99', '#1479B0', GREEN_C, '#4D4D4D'   # 空地圖層＝開放空間淡綠（原橄欖黃 #C7C44D）
COM = {k: [(g, p) for g, p in CHAR if p['tier'] == 'M' and p['group'] == k] for k in COM_C}
HER = [(g, p) for g, p in CHAR if p['tier'] == 'R']
SUPA = [(g, p) for g, p in CHAR if p['tier'] == 'F' and g.geom_type != 'Point']   # 步行街／廣場、公園綠地（面）
SUPP = [(g, p) for g, p in CHAR if p['tier'] == 'F' and g.geom_type == 'Point' and not p.get('nomap')]   # 停車場等點：使用者 2026-10-12 刪除配套，不上圖
VAC = [(g, p) for g, p in CHAR if p['tier'] == 'V']   # 空地圖層：可用空地＋步行區、廣場、綠地（使用者 2026-10-12 併入，減少圖面顏色）
VAC_U = [(g, p) for g, p in VAC if p['group'] in ('空地', '平面停車場')]          # 其中可用空地（空照判讀）
OPEN5 = [(g, p) for g, p in VAC if p['group'] in ('步行街／廣場', '公園綠地')]    # 其中步行區、廣場、綠地
_cmf = H / f'data/{ZONE}_commercial_EPSG3826.geojson'
CM = json.load(open(_cmf)) if (VAC or HER or any(COM.values())) and _cmf.exists() else None   # 31 原始判讀（統計、施工中）
def park_r(p): return max(4.0, ((float(p.get('car') or 0) + float(p.get('moto') or 0)) * 1.2 / np.pi) ** .5)   # 停車場圓：地面 1.2 ㎡／格
def marker(g, kind, s_=3.2):
    from shapely.geometry import Polygon as _Pg
    x, y = g.x, g.y
    if kind == '公車站': return g.buffer(s_ * .9, cap_style=3)
    if kind == 'YouBike': return _Pg([(x, y + s_ * 1.3), (x - s_ * 1.15, y - s_ * .8), (x + s_ * 1.15, y - s_ * .8)])
    return _Pg([(x, y + s_ * 1.2), (x + s_ * 1.2, y), (x, y - s_ * 1.2), (x - s_ * 1.2, y)])   # 公廁：菱形
# 目的地建物（tier D，Z3 起；使用者 2026-10-11 指定兩色）——配色經 CVD 驗證（與橘、酒紅、黑兩兩 ΔE 足夠）
DEST_C = {'商辦／政府機關': '#2F6FD0', '日常生活店家': '#12A594'}
DEST = {k: [(g, p) for g, p in CHAR if p['tier'] == 'D' and p['group'] == k] for k in DEST_C}
_rep = [g for g, p in FE if p['cls'] == 'replaced']             # 主角基地內現有建物（拆除改建，不上圖）
REPL = unary_union(_rep) if _rep else None
MAIN = next((p for _, p in CHAR if p['tier'] == 'A' and p.get('planned') and ZONE != 'Z1'), None)   # 非 Z1：主角為規劃中公辦都更
# 源頭建築（tier S）與目的地（tier T，臺北車站）：Z2 起，使用者 2026-10-11 指定「流向台北車站之人群的源頭建築」
SRC = [(g, p) for g, p in CHAR if p['tier'] == 'S']
TGT = [(g, p) for g, p in CHAR if p['tier'] == 'T']
MAG_LT = '#E9A3BD'       # 淡酒紅＝主角基地／開放空間（Z2 臺北車站、Z6、Z8；2026-10-13 調整以與酒紅色階 4 級、路徑灰區隔）
# 滲透場所（Z6 起，使用者 2026-10-12 指定；33_z6_permeable）：主角＝U02 規劃量體、U03 現有建物（中崙球場等）、忠泰美術館街廓・瑠公圳公園・懷生國小・八德市場
#   之建物（酒紅）；場所開放地（空地、校園、公園綠地、U02 方案法定空地）tier O＝淡酒紅；行人穿越道（非路口）＝橘；建國高架主線＝灰點鏈（同市民高架）
PERM = [(g, p) for g, p in CHAR if p['tier'] == 'O']
_xef = H / f'data/{ZONE}_elev_extra_EPSG3826.geojson'
ELEV_X = unary_union([shape(f['geometry']) for f in json.load(open(_xef))['features']]) if _xef.exists() else None
# 夜間餐飲（Z7 起，使用者 2026-10-12 指定；34_z7_night_dining）：一樓有餐飲店家之建物依型態分四色，沿用 Z5 已驗證之酒紅色階
#   （居酒屋／燒肉串燒最深 → 一般餐飲最淺）；統計＝型態 × 營業時段（宵夜、晚餐、不明）× 南北，晚餐也列入
NIGHT_C = {'居酒屋／燒肉串燒': '#8E1B3E', '酒吧／飲酒店': '#A4435F', '宵夜小吃': '#B95F7D', '一般餐飲': '#D2779C'}
NIGHT = {k: [(g, p) for g, p in CHAR if p['tier'] == 'N' and p['group'] == k] for k in NIGHT_C}
_ndf = H / f'data/{ZONE}_night_dining_summary.json'
ND = json.load(open(_ndf)) if any(NIGHT.values()) and _ndf.exists() else None
HOURS_C = {'宵夜': '#3A3A3A', '晚餐': '#8C8C8C', '不明': '#D9D9D9'}   # 統計長條：營業時段（中性灰階，不與圖面色混用）
PATH_C = '#E3E3E3'       # 路徑（道路＋人行道）淡灰（2026-10-11 使用者指定）
# 建物樓高 5 級灰（2026-10-15 使用者：「把建物輪廓圖色套疊樓高參數進去調深淺；0–5 層一種、6–11 層一種，級距隨樓高變大」；資料＝42_building_floors）
#   級距 0–5｜6–11｜12–19｜20–29｜30 層以上（級寬 6、6、8、10、開放）；層數＝臺北三維模型 2017 高度 ÷ 3.3 m。
#   OKLab L 0.72→0.20 等距（相鄰 ΔE 12.6–13.8），最高級＝原建物黑 #141414；與路徑、可通過路口淡灰 ΔE ≥ 14。
#   限制：紅綠色弱下酒紅色階近乎無彩，與同明度之樓高灰相近（正常視覺 ΔE 12–28）；中段灰無法同時避開酒紅色階 1–4 級之明度。
#   連帶：Z8 匝道改斜線（原兩灰）、Z7 營業時段長條改斜線疏密（原三灰），以免與樓高灰同色異義（色塊互通）。
FLOOR_LABELS = ['0–5 層', '6–11 層', '12–19 層', '20–29 層', '30 層以上']
BLD_GRAYS = ['#A4A4A4', '#7E7E7E', '#585858', '#353535', '#141414']
_bff = H / 'data/building_floors_EPSG3826.geojson'
BFLOOR = {}
if _bff.exists():
    for _f in json.load(open(_bff))['features']: BFLOOR.setdefault(_f['properties']['cls'], []).append(shape(_f['geometry']))
BFLOOR_IN = sorted(k for k, gs in BFLOOR.items() if any(g.intersects(SLAB) for g in gs))   # 本單元內實有之級（圖例只列這些）
def BLD_ITEMS():   # 圖例：建物依樓高——一列色塊（只列本單元內實有之級，由低至高），色塊下標級距；2026-10-15 改精簡（原逐級一列擠壓結果區塊）
    if not BFLOOR: return [('patch', BLD_C, None, '建物')]
    return [('floors', None, None, '建物（樓高；臺北三維模型 2017，高度 ÷ 3.3 m＝層數，越高越深）')]
FLOOR_SHORT = ['0–5', '6–11', '12–19', '20–29', '30+']
def floors_row(fig, x, y, fw, fh, fs, k):
    # 一列五色塊（本單元內實有之級，由低至高；每塊 10 mm，級距字在色塊內）＋「建物樓高（層）」；高度同原單列「建物」，不擠壓結果區塊
    cs = sorted(BFLOOR_IN)
    for i, c in enumerate(cs):
        X = x + i * 10.4 * k
        fig.add_artist(plt.Rectangle((X / fw, (y - 1.6 - 3.4 * k + 1.7) / fh), 10.0 * k / fw, 3.4 * k / fh, transform=fig.transFigure, facecolor=BLD_GRAYS[c], edgecolor='none'))
        fig.text((X + 5.0 * k) / fw, (y - 1.6 - 1.7 * k + 1.7) / fh, FLOOR_SHORT[c], fontsize=fs - 2.0, va='center', ha='center', color='white' if c >= 2 else '#111')
    fig.text((x + len(cs) * 10.4 * k + 2) / fw, y / fh, '建物樓高（層）', fontsize=fs, va='top', color='#222')
    return y - 5.0 * k
HOURS_H = {'宵夜': 'xxxx', '晚餐': '////', '不明': ''}   # 營業時段長條：斜線疏密（2026-10-15 改，原灰階與樓高灰同色異義）
REB = Path.home() / 'Desktop/Civic_Rebuild_20260909_201934/data'
def paths_geom(wb, fill=True):
    # 路徑＝整合後道路面（路緣至路緣）∪ 新工處人行道範圍；扣除建物
    # fill：併入 26_road_islands 判讀為「非分隔島」之碎塊（空照比對；data/{Z}_road_islands_EPSG3826.geojson）
    sw = [shape(f['geometry']).buffer(0) for f in json.load(open(REB / 'taipei-sidewalks.geojson'))['features']]
    parts = [S.road.intersection(wb)] + [q.intersection(wb) for q in sw if q.intersects(wb)]
    fi = H / f'data/{ZONE}_road_islands_EPSG3826.geojson'
    if fill and fi.exists():
        parts += [shape(f['geometry']).buffer(.05) for f in json.load(open(fi))['features'] if f['properties']['decision'] == 'fill']
    g = unary_union(parts)
    return g.difference(S.bld.intersection(wb.buffer(10)))
# 圖層依高程排列（2026-10-11 使用者指定）：由下而上 B2 → B1 → 地面（路徑、出入口、建物、特性建築）→ +1 天橋 → +2 高架
#   地下層在路徑之下：路徑以「黑色 11% 不透明」繪製——白底上即淡灰 #E3E3E3，疊在橘地下層上等同色彩增值（multiply），
#   故大道下方之地下街透出較暗之橘，街廓內（無路徑覆蓋）之站體為原橘。
#   樓層依 OSM layer／level 標籤與告示圖：台北地下街 level −2、機捷月台 B2；北門站、台北車站地下通廊、機捷站體（大廳）、連通道 −1。
PATH_ALPHA = 0.11
def level_of(p):
    t, n = p['type'], p.get('name', '')
    if p.get('level') and t in ('地下街', '捷運／車站站體', '車站地下通廊'): return p['level']   # 23 描繪之樓層（OSM level）
    if t == '地下街' or (t == '捷運／車站站體' and '月台' in n): return 'B2'
    if t in ('捷運／車站站體', '車站地下通廊'): return 'B1'
    if t in ('地下連通道', '地下街廊道'): return None   # 連通道細帶不上圖（使用者 2026-10-11 於 AI 刪除）
    if t.startswith('人行天橋'): return 'U1'
    if t == '出入口': return None                 # 出入口方塊不上圖（使用者 2026-10-11 22:37 於 AI 刪除）
    if t == '行人穿越道': return 'G_XING'           # 非路口之行人穿越道：路徑剪影（使用者 2026-10-12，Z6 起）
    if t == '行穿線': return 'G_XING'               # Z8 起：交工處行穿線全部上圖（十字路口與巷口；使用者 2026-10-12「行穿線畫出來」）
    if t == '地下停車場': return 'B1'             # 市民大道地下停車場分段包絡（使用者 2026-10-12「算做剪影」，Z7 起）
    return None                                  # 平面穿越行穿線：不上圖
def ug_compress(names):
    # 地下停車場各段併為一名（Z7 起）：市民大道地下停車場（建復段）…（延吉段）→ 市民大道地下停車場（建復・復敦・敦延・延吉段）
    pk = [n[len('市民大道地下停車場（'):-2] for n in names if n.startswith('市民大道地下停車場（') and n.endswith('段）')]
    if len(pk) < 2: return list(names)
    out = [n for n in names if not (n.startswith('市民大道地下停車場（') and n.endswith('段）'))]
    return out + ['市民大道地下停車場（' + '・'.join(pk) + '段）']
UG_NAMES = {'Z1': ('B2｜台北地下街（Y區）・機捷月台', 'B1｜北門站・台北車站地下通廊・機捷站體'),
            'Z2': ('B2｜台北地下街（Y區）', 'B1｜台北車站地下通廊・捷運台北車站・中山地下街（R區）')}.get(ZONE, ('B2｜地下二層通行元素', 'B1｜地下一層通行元素'))
if ZONE == 'Z7':   # Z7 起：依本段實際之地下元素命名（地下停車場剪影；捷運站體單元外淡化）
    UG_NAMES = tuple(lv + '｜' + ('・'.join(ug_compress(dict.fromkeys(p['name'] for _, p in PA if level_of(p) == lv))) or '地下通行元素') for lv in ('B2', 'B1'))
# 南北兩側園區串連（Z8 起，使用者 2026-10-12 指定；35_z8_parks）：主角三園區建物（酒紅）＋戶外空間（淡酒紅，同 Z6 tier O）；
#   匝道（35：OSM trunk_link 展成面）高架段＝+1 灰、落地段＝±0 深灰（地面阻隔）；行穿線（交工處）全部上圖；東界＝基隆路中心線（35）
PARKS8 = ZONE == 'Z8'
RAMP_C, RAMP_G_C = '#666666', '#333333'   # 斜線色（2026-10-15 匝道由兩灰實心改白底斜線：高架段 ////、落地段 ××，避開建物樓高灰）
RAMP_H, RAMP_G_H = '/////', 'xxxx'
matplotlib.rcParams['hatch.linewidth'] = .3
_rpf = H / f'data/{ZONE}_ramps_EPSG3826.geojson'
_rp = json.load(open(_rpf))['features'] if PARKS8 and _rpf.exists() else []
RAMP_E = [(shape(f['geometry']), f['properties']) for f in _rp if f['properties']['kind'] == 'ramp_elev']
RAMP_G = [(shape(f['geometry']), f['properties']) for f in _rp if f['properties']['kind'] == 'ramp_grade']
_ecf = H / f'data/{ZONE}_east_cut_EPSG3826.geojson'
EAST_CUT = shape(json.load(open(_ecf))['features'][0]['geometry']) if PARKS8 and _ecf.exists() else None
# 可通過之路口標記（2026-10-14 使用者於 Z1 紙本以藍筆斜線標記：「在 Z1–Z8 每個可以通過的十字路口都做像我藍色筆跡這樣的標記」；41_cross_marks）
#   符號＝橫越大道之帶＋兩端路緣各一「十」字；斜線＋外框，畫在地面層最上（如筆跡疊在圖上）。只標經交工處行穿線核對確實橫越大道者。
XMARK_C = '#0C1781'   # （2026-10-14 初版斜線標記用；已改為道路上色，保留供 36 舊版圖例相容）
# 2026-10-14 再修訂（使用者：「把藍色圖塊覆蓋到的道路圖層區域上色，然後把藍色圖塊移除，只要留道路上色區域」）：
#   標記範圍（41）∩ 路徑面（同 G_PATH：道路＋人行道）以淺藍實心上色，不畫斜線與外框；圖層移至路徑之上、建物之下。
# 2026-10-14 三修（使用者：「淺藍改淺灰，比其他路段深色就好，我不要太明顯的透出來；圖層的高度跟路線層一樣」）：
#   可通過之路口＝路徑圖層之一部分（同一 AI 圖層、同為黑色半透明），只比其他路段稍深：路徑黑 11%（白底 #E3E3E3）、路口黑 18.4%（白底 #D0D0D0）；
#   地下層在其下同樣透出（同路徑之色彩增值表現）。
XROAD_ALPHA = 1 - 208 / 255   # 黑 18.4%：白底上＝#D0D0D0
XROAD_C = '#D0D0D0'   # 圖例色塊（白底上之顯示色）
XMARK_SP, XMARK_LW = 1.5, .5   # 斜線間距（m；1:2500 下 0.6 mm）、線寬（pt）
_xmf = H / f'data/{ZONE}_cross_marks_EPSG3826.geojson'
XMARK = [(shape(f['geometry']), f['properties']) for f in json.load(open(_xmf))['features']] if _xmf.exists() else []
XS = sorted([p['s'] for _, p in XMARK] + [p['s2'] for _, p in XMARK if 's2' in p])   # 經交工處行穿線核對橫越大道之平面穿越里程（間距、無平面穿越段用）
def hatch_lines(poly, sp, ang=45):
    # 多邊形內之平行斜線（座標單位同 poly；ang＝與水平夾角）
    from shapely import affinity
    from shapely.geometry import MultiLineString
    c = poly.centroid; r = affinity.rotate(poly, -ang, origin=c); x0, y0, x1, y1 = r.bounds
    ls = MultiLineString([[(x0 - 1, y), (x1 + 1, y)] for y in np.arange(y0 + sp / 2, y1, sp)])
    out = affinity.rotate(ls.intersection(r), ang, origin=c)
    return [g for g in getattr(out, 'geoms', [out]) if g.geom_type == 'LineString' and not g.is_empty]
LAYERS = [  # (鍵, AI 圖層名稱)，由下而上
    ('B2', UG_NAMES[0]),
    ('B1', UG_NAMES[1]),
    ('G_PATH', '±0｜路徑（道路＋人行道）'),
    ('G_XING', '±0｜行人穿越道（非路口）'),
    ('G_RAMP', '±0｜市民高架匝道：落地段（地面阻隔）'),
    ('G_OPEN', '±0｜主角開放地：空地・校園・公園綠地'),
    ('G_GREEN', '±0｜純綠地（公園綠地扣除鋪面、步道、設施）'),
    ('G_PPATH', '±0｜公園步道與鋪面（廣場、停車）'),
    ('G_VAC', '±0｜空地：可用空地・步行區・廣場・綠地'),
    ('G_SUPA', '±0｜配套措施：步行街・廣場・公園綠地'),
    ('G_SPORT', '±0｜運動場：球場・體健設施・兒童遊戲場'),
    ('G_BLD0', '±0｜建物：0–5 層'),
    ('G_BLD1', '±0｜建物：6–11 層'),
    ('G_BLD2', '±0｜建物：12–19 層'),
    ('G_BLD3', '±0｜建物：20–29 層'),
    ('G_BLD4', '±0｜建物：30 層以上'),
    ('G_NT_G', '±0｜夜間餐飲：一般餐飲'),
    ('G_NT_S', '±0｜夜間餐飲：宵夜小吃'),
    ('G_NT_B', '±0｜夜間餐飲：酒吧／飲酒店'),
    ('G_NT_I', '±0｜夜間餐飲：居酒屋／燒肉串燒'),
    ('G_COM_S', '±0｜商業空間：臨街店面'),
    ('G_COM_A', '±0｜商業空間：騎樓店面'),
    ('G_COM_B', '±0｜商業空間：商業大樓／旅館'),
    ('G_COM_M', '±0｜商業空間：大型商場／市場'),
    ('G_HER', '±0｜古蹟：建國啤酒廠'),
    ('G_HOUSE', '±0｜住宅建物'),
    ('G_DEST_O', '±0｜目的地建物：商辦／政府機關'),
    ('G_DEST_L', '±0｜目的地建物：日常生活店家'),
    ('G_TGT', '±0｜目的地：' + '・'.join(p['name'] for _, p in TGT) + '（主角）' if TGT else ''),
    ('G_CHAR', '±0｜主角剪影：U02 方案・U03 現有建物・忠泰美術館街廓・懷生國小・北科大學生宿舍・八德市場' if PERM else ('±0｜源頭建築剪影' if SRC else '±0｜特性建築剪影') if MAIN is None else '±0｜主角剪影：' + '・'.join(p['name'] for _, p in SIL if p['tier'] == 'A')),
    ('G_SUPP', '±0｜配套措施：停車場・公車站・YouBike・公廁（點）'),
    ('U1', '+1｜人行天橋'),
    ('U1_RAMP', '+1｜市民高架匝道：高架段'),
    ('U2', '+2｜市民高架主線中心線' + ('・建國高架主線中心線' if ELEV_X is not None else '')),
    ('MASK', '範圍外淡化遮罩'),
    ('CUT', '單元界線'),
    ('TEXT', '圖框・標題・圖例・索引・比例尺'),
]
_has = {k: any(level_of(p) == k for _, p in PA) for k in ('B2', 'B1', 'U1')}
_has.update(G_DEST_O=bool(DEST['商辦／政府機關']), G_DEST_L=bool(DEST['日常生活店家']), G_TGT=bool(TGT), G_HOUSE=bool(HOUSE), G_SPORT=bool(SPORT),
            G_GREEN=bool(GREEN), G_PPATH=bool(PPATH))
_has.update(G_XING=any(level_of(p) == 'G_XING' for _, p in PA), G_OPEN=bool(PERM))   # Z6
_COMK = {'G_COM_M': '大型商場／市場', 'G_COM_B': '商業大樓／旅館', 'G_COM_A': '騎樓店面', 'G_COM_S': '臨街店面'}
_has.update({k: bool(COM[g]) for k, g in _COMK.items()}, G_HER=bool(HER), G_SUPA=bool(SUPA), G_SUPP=bool(SUPP), G_VAC=bool(VAC))   # Z5
_NTK = {'G_NT_I': '居酒屋／燒肉串燒', 'G_NT_B': '酒吧／飲酒店', 'G_NT_S': '宵夜小吃', 'G_NT_G': '一般餐飲'}
_has.update({k: bool(NIGHT[g]) for k, g in _NTK.items()})   # Z7
if ND is not None: _has['G_CHAR'] = bool(SIL)
if CM is not None: _has['G_CHAR'] = bool(SIL)
_has.update(G_RAMP=bool(RAMP_G), U1_RAMP=bool(RAMP_E))   # Z8（其餘單元無匝道圖層）
_has['G_XMARK'] = bool(XMARK)   # 41 可通過之路口標記
if PARKS8:   # Z8：圖層名稱依本段內容
    _N8 = {'G_XING': '±0｜行穿線（交工處；十字路口與巷口）', 'G_OPEN': '±0｜主角戶外空間：廣場・花園・空地',
           'G_CHAR': '±0｜主角剪影：國家鐵道博物館（臺北機廠）・松山文創園區・臺北大巨蛋'}
    LAYERS = [(k, _N8.get(k, n)) for k, n in LAYERS]
_has.update({f'G_BLD{k}': bool(BFLOOR.get(k)) if BFLOOR else k == 4 for k in range(5)})   # 樓高 5 級（42）；無資料檔時全畫為最高級（原建物黑）
LAYERS = [(k, n) for k, n in LAYERS if _has.get(k, True)]          # 本段無內容之圖層不輸出（Z1 不受影響）
_PATHS = {}
def draw_layer(ax, key, T, wb, view):
    P = lambda gs: [q for q in (S.poly_path(T(g)) for g in gs) if q is not None]
    if key in ('B2', 'B1', 'G_EXIT', 'U1', 'G_XING'):
        gs = [g for g, p in PA if level_of(p) == key]
        if gs: ax.add_collection(PathCollection(P(gs), facecolors=RED, edgecolors='none', zorder=1))
    elif key == 'G_PATH':   # 路徑（黑 11%）；可通過之路口（41 範圍 ∩ 路徑）同圖層、黑 18.4%（2026-10-14）
        if 'g' not in _PATHS: _PATHS['g'] = paths_geom(wb)
        xr = unary_union([g for g, _ in XMARK]).intersection(_PATHS['g']) if XMARK else None
        pg = _PATHS['g'].difference(xr) if xr is not None and not xr.is_empty else _PATHS['g']
        ax.add_collection(PathCollection(P(S.polys(pg)), facecolors='#000000', alpha=PATH_ALPHA, edgecolors='none', zorder=1))
        if xr is not None and not xr.is_empty:
            ax.add_collection(PathCollection(P(S.polys(xr)), facecolors='#000000', alpha=XROAD_ALPHA, edgecolors='none', zorder=1))
    elif key == 'G_XMARK':   # 可通過之路口：41 標記範圍內之路徑面，淺藍實心（2026-10-14 再修訂：不畫斜線、外框）
        if 'g' not in _PATHS: _PATHS['g'] = paths_geom(wb)
        xr = unary_union([g for g, _ in XMARK]).intersection(_PATHS['g'])
        ax.add_collection(PathCollection(P(S.polys(xr)), facecolors=XROAD_C, edgecolors='none', zorder=1))
    elif key == 'G_XMARK_HATCH':   # （舊：斜線＋外框；保留未用）
        ax.add_collection(PathCollection(P([g for g, _ in XMARK]), facecolors='none', edgecolors=XMARK_C, linewidths=.6, zorder=2))
        _fmm = ax.figure.get_figwidth() * 25.4 * ax.get_position().width   # 斜線間距固定為圖紙 0.6 mm（37 A3 1:4200、38 A1 1:8000 亦同）
        _sp = XMARK_SP * ((view.bounds[2] - view.bounds[0]) / _fmm / 2.5 if _fmm > 0 else 1)
        ax.add_collection(LineCollection([np.asarray(l.coords) for g, _ in XMARK for l in hatch_lines(T(g), _sp)], colors=XMARK_C, linewidths=XMARK_LW, zorder=2))
    elif key.startswith('G_BLD'):   # 建物依樓高 5 級灰（42；2026-10-15）；扣除主角基地拆除改建、Z5 已拆除基地
        k_ = int(key[5:])
        ck = ('bld', k_, tuple(round(v) for v in wb.bounds))
        if ck not in _PATHS:
            ex = ([REPL.buffer(.3)] if REPL is not None else []) + ([unary_union([g for g, _ in VAC]).buffer(.2)] if VAC else [])   # Z5：線稿仍為建物、2025 空照為裸土之已拆除基地不畫建物
            src = BFLOOR.get(k_, []) if BFLOOR else [S.bld]
            g_ = unary_union([q for q in src if q.intersects(wb)]).intersection(wb) if src else None
            if g_ is not None and ex: g_ = g_.difference(unary_union(ex))
            _PATHS[ck] = g_
        if _PATHS[ck] is not None and not _PATHS[ck].is_empty:
            ax.add_collection(PathCollection(P(S.polys(_PATHS[ck])), facecolors=BLD_GRAYS[k_] if BFLOOR else BLD_C, edgecolors='none', zorder=1))
    elif key in ('G_DEST_O', 'G_DEST_L'):
        k = '商辦／政府機關' if key == 'G_DEST_O' else '日常生活店家'
        ax.add_collection(PathCollection(P([g for g, _ in DEST[k]]), facecolors=DEST_C[k], edgecolors='none', zorder=1))
    elif key == 'G_TGT':
        ax.add_collection(PathCollection(P([g for g, _ in TGT]), facecolors=MAG_LT, edgecolors='none', zorder=1))
    elif key == 'G_HOUSE':
        ax.add_collection(PathCollection(P([g for g, _ in HOUSE]), facecolors=HOUSE_C, edgecolors='none', zorder=1))
    elif key == 'G_SPORT':
        ax.add_collection(PathCollection(P([g for g, _ in SPORT]), facecolors=SPORT_C, edgecolors='none', zorder=1))
    elif key == 'G_GREEN':
        ax.add_collection(PathCollection(P([q for g in GREEN for q in S.polys(g)]), facecolors=GREEN_C, edgecolors='none', zorder=1))
    elif key == 'G_PPATH':   # 同路徑表現（黑 11%）：與道路、人行道成一個路徑系統；扣除已在路徑圖層者，避免重疊處加深
        if 'g' not in _PATHS: _PATHS['g'] = paths_geom(wb)
        pp = unary_union(PPATH).difference(_PATHS['g'])
        ax.add_collection(PathCollection(P(S.polys(pp)), facecolors='#000000', alpha=PATH_ALPHA, edgecolors='none', zorder=1))
    elif key in _COMK:
        ax.add_collection(PathCollection(P([g for g, _ in COM[_COMK[key]]]), facecolors=COM_C[_COMK[key]], edgecolors='none', zorder=1))
    elif key in _NTK:
        ax.add_collection(PathCollection(P([g for g, _ in NIGHT[_NTK[key]]]), facecolors=NIGHT_C[_NTK[key]], edgecolors='none', zorder=1))
    elif key == 'G_HER':
        ax.add_collection(PathCollection(P([g for g, _ in HER]), facecolors=HER_C, edgecolors='none', zorder=1))
    elif key == 'G_SUPA':
        ax.add_collection(PathCollection(P([g for g, _ in SUPA]), facecolors=SUP_C, edgecolors='none', zorder=1))
    elif key == 'G_VAC':
        ax.add_collection(PathCollection(P([g for g, _ in VAC]), facecolors=VAC_C, edgecolors='none', zorder=1))
    elif key == 'G_SUPP':
        rings = [g.buffer(park_r(p)) for g, p in SUPP if p['group'] == '停車場']
        ax.add_collection(PathCollection(P(rings), facecolors='none', edgecolors=PARK_C, linewidths=1.0, zorder=1))
        ax.add_collection(PathCollection(P([g.buffer(1.4) for g, p in SUPP if p['group'] == '停車場']), facecolors=PARK_C, edgecolors='none', zorder=1))
        ax.add_collection(PathCollection(P([marker(g, p['group']) for g, p in SUPP if p['group'] != '停車場']), facecolors=SUP_C, edgecolors='white', linewidths=.3, zorder=2))
    elif key == 'G_CHAR':
        ax.add_collection(PathCollection(P([g for g, p in SIL if p['tier'] != 'T']), facecolors=MAG, edgecolors='none', zorder=1))
    elif key == 'G_OPEN':
        ax.add_collection(PathCollection(P([g for g, _ in PERM]), facecolors=MAG_LT, edgecolors='none', zorder=1))
    elif key == 'G_RAMP':
        ax.add_collection(PathCollection(P([g for g, _ in RAMP_G]), facecolors='white', edgecolors=RAMP_G_C, linewidths=.4, hatch=RAMP_G_H, zorder=1))
    elif key == 'U1_RAMP':
        ax.add_collection(PathCollection(P([g for g, _ in RAMP_E]), facecolors='white', edgecolors=RAMP_C, linewidths=.4, hatch=RAMP_H, zorder=1))
    elif key == 'U2':
        if ELEV_X is not None:
            ax.add_collection(LineCollection(S.lines(T(ELEV_X.intersection(wb))), colors='#9a9a9a', linewidths=.45,
                                             linestyles=(0, (6, 1.5, 1.5, 1.5)), zorder=1))
        ax.add_collection(LineCollection(S.lines(T(S.elev.intersection(wb))), colors='#9a9a9a', linewidths=.45,
                                         linestyles=(0, (6, 1.5, 1.5, 1.5)), zorder=1))
    elif key == 'MASK':
        _um = [g for g, p in CHAR if p.get('unmask')]   # Z6：使用者指定歸本單元之跨界場所（八德市場）不淡化
        ax.add_patch(PathPatch(S.poly_path(view.buffer(50).difference(T(unary_union([SLAB] + _um)))), facecolor='white', edgecolor='none', alpha=1 - F.CTX_ALPHA, zorder=1))
    elif key == 'CUT':
        k = int(ZONE[1:])
        for g in (F.CUT_G[k - 1], F.CUT_G[k] if k < len(F.CUT_G) else EAST_CUT):   # Z8：東界＝基隆路（35）
            if g is not None:
                ax.add_collection(LineCollection(S.lines(T(g)), colors=S.ZONE_C, linewidths=1.0, linestyles=(0, (6, 3)), zorder=1))

def handles():   # A4 用（線性圖例）
    return [Patch(facecolor=BLD_C, edgecolor='none', label='建物（依樓高 5 級灰）'),
            Patch(facecolor=PATH_C, edgecolor='none', label='路徑：道路（路緣至路緣）＋人行道（淡灰）'),
            Line2D([], [], color='#9a9a9a', lw=.5, ls=(0, (6, 1.5, 1.5, 1.5)), label='市民高架主線車道中心線'),
            Line2D([], [], color=S.ZONE_C, lw=1.0, ls=(0, (6, 3)), label='單元界線（路口中心線）'),
            Patch(facecolor='#f2f2f2', edgecolor='#d0d0d0', lw=.4, label='界線外：市民大道前後段（淡化）'),
            Patch(facecolor=RED, edgecolor='none', label='通行元素：地下街、捷運／機捷站體、車站地下通廊、地下連通道、出入口、人行天橋'),
            Patch(facecolor=MAG, edgecolor='none', label='特性建築（酒紅實心剪影，原位）')]

def mix(c, a=PATH_ALPHA):   # 橘上疊 11% 黑之顯示色
    h = c.lstrip('#'); r, g, b = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return '#%02x%02x%02x' % tuple(round(v * (1 - a)) for v in (r, g, b))

def legend_left(fig, x, ytop, fw, fh, fs=7.4, col2_x=None):
    # 依高程分組之圖例（由上而下＝高程由高至低，與圖層堆疊一致）
    def sw(y, kind, c, c2=None):
        X, Y = x / fw, (y - 1.6) / fh
        if kind == 'patch': fig.add_artist(plt.Rectangle((X, Y), 7 / fw, 3.4 / fh, transform=fig.transFigure, facecolor=c, edgecolor='none'))
        elif kind == 'split':
            fig.add_artist(plt.Rectangle((X, Y), 3.5 / fw, 3.4 / fh, transform=fig.transFigure, facecolor=c, edgecolor='none'))
            fig.add_artist(plt.Rectangle((X + 3.5 / fw, Y), 3.5 / fw, 3.4 / fh, transform=fig.transFigure, facecolor=c2, edgecolor='none'))
        elif kind == 'sq': fig.add_artist(plt.Rectangle((X + 2.2 / fw, Y + .6 / fh), 2.2 / fw, 2.2 / fh, transform=fig.transFigure, facecolor=c, edgecolor='none'))
        elif kind in ('line', 'dash', 'dashdot', 'thick'):
            ls = {'line': '-', 'thick': '-', 'dash': (0, (6, 3)), 'dashdot': (0, (6, 1.5, 1.5, 1.5))}[kind]
            fig.add_artist(plt.Line2D([X, X + 7 / fw], [(y) / fh] * 2, transform=fig.transFigure, color=c, lw=2.4 if kind == 'thick' else 1.0, ls=ls))
        elif kind == 'fade':
            fig.add_artist(plt.Rectangle((X, Y), 7 / fw, 3.4 / fh, transform=fig.transFigure, facecolor='#f2f2f2', edgecolor='#cfcfcf', lw=.4))
        elif kind in ('rhatch', 'rxhatch'):   # 匝道：白底斜線（高架段 ////、落地段 ××）
            fig.add_artist(plt.Rectangle((X, Y), 7 / fw, 3.4 / fh, transform=fig.transFigure, facecolor='white', edgecolor=c, lw=.4, hatch=RAMP_H if kind == 'rhatch' else RAMP_G_H))
        elif kind == 'hatch':   # 斜線＋外框（可通過之路口標記）
            fig.add_artist(plt.Rectangle((X, Y), 7 / fw, 3.4 / fh, transform=fig.transFigure, facecolor='none', edgecolor=c, lw=.6))
            for t_ in np.arange(-3.4 + .55, 7, 1.1):
                xa, xb = max(t_, 0), min(t_ + 3.4, 7)
                if xb > xa: fig.add_artist(plt.Line2D([X + xa / fw, X + xb / fw], [Y + (xa - t_) / fh, Y + (xb - t_) / fh], transform=fig.transFigure, color=c, lw=.45))
        elif kind in ('ring', 'msq', 'mtri', 'mdia'):   # Z5 配套點：停車場圓環、公車站方塊、YouBike 三角、公廁菱形
            from matplotlib.patches import Ellipse, Polygon as _MP
            cx, cy = X + 3.5 / fw, Y + 1.7 / fh; rx, ry = 1.7 / fw, 1.7 / fh
            if kind == 'ring':
                fig.add_artist(Ellipse((cx, cy), 2 * rx, 2 * ry, transform=fig.transFigure, facecolor='none', edgecolor=c, lw=1.0))
                fig.add_artist(Ellipse((cx, cy), .5 * rx, .5 * ry, transform=fig.transFigure, facecolor=c, edgecolor='none'))
            else:
                pts = {'msq': [(-.8, -.8), (.8, -.8), (.8, .8), (-.8, .8)], 'mtri': [(0, 1.1), (-1, -.7), (1, -.7)], 'mdia': [(0, 1.1), (1.1, 0), (0, -1.1), (-1.1, 0)]}[kind]
                fig.add_artist(_MP([(cx + a * rx, cy + b * ry) for a, b in pts], closed=True, transform=fig.transFigure, facecolor=c, edgecolor='none'))
    k = fs / 7.4
    y = ytop
    fig.text(x / fw, y / fh, '圖例', fontsize=fs + 3, fontweight='bold', va='top', color='#111'); y -= 9 * k
    fig.text(x / fw, y / fh, '圖層依高程排列（上＝高、下＝深）', fontsize=fs - .6, va='top', color='#666'); y -= 8 * k
    groups = legend_groups(); y_start = y; y_col1 = None
    _z1_groups = [
        ('+2 高架', [('dashdot', '#9a9a9a', None, '市民高架主線車道中心線')]),
        ('+1 天橋', [('thick', RED, None, '人行天橋（承德路）')]),
        ('±0 地面', [('patch', MAG, None, '特性建築（酒紅剪影）'), *BLD_ITEMS(),
                     ('patch', PATH_C, None, '路徑（道路＋人行道）')]),
        ('B1 地下一層', [('split', RED, mix(RED), '北門站、台北車站地下通廊、'), (None, None, None, '機捷站體（大廳）')]),
        ('B2 地下二層', [('split', RED, mix(RED), '台北地下街（Y區）、機捷月台')]),
    ]
    for gname, items in groups:
        if not items: continue
        if col2_x is not None and y_col1 is None and gname.startswith('B'):   # 兩欄：地下層起換欄
            y_col1 = y; x = col2_x; y = y_start
        fig.text(x / fw, y / fh, gname, fontsize=fs, fontweight='bold', va='top', color='#333'); y -= 5.6 * k
        for kind, c, c2, lab in items:
            if kind == 'floors': y = floors_row(fig, x, y, fw, fh, fs, k); continue   # 建物樓高一列（2026-10-15）
            if kind: sw(y - 1.6 * k, kind, c, c2)
            fig.text((x + 10) / fw, y / fh, lab, fontsize=fs, va='top', color='#222'); y -= 5.0 * k
        y -= 2.2 * k
    if _has['B1'] or _has['B2']:
        fig.text(x / fw, y / fh, '地下層位於路徑之下：大道下方透出較暗之橘（左半色塊），\n街廓內為原橘（右半色塊）。', fontsize=fs - 1, va='top',
                 color='#666', linespacing=1.5); y -= 12 * k
    for kind, c, lab in (('dash', S.ZONE_C, '單元界線（路口中心線）'), ('fade', None, '界線外：市民大道前後段（淡化）')):
        sw(y - 1.6 * k, kind, c); fig.text((x + 10) / fw, y / fh, lab, fontsize=fs, va='top', color='#222'); y -= 5.0 * k
    return min(y, y_col1) if y_col1 is not None else y

def XMARK_ITEM():
    return [('patch', XROAD_C, None, f'可通過之路口（路徑較深灰，{len(XMARK)} 處）')] if XMARK else []

def legend_groups():
    if ZONE == 'Z1':
        return [
            ('+2 高架', [('dashdot', '#9a9a9a', None, '市民高架主線車道中心線')]),
            ('+1 天橋', [('thick', RED, None, '人行天橋（承德路）')]),
            ('±0 地面', [('patch', MAG, None, '特性建築（酒紅剪影）'), *BLD_ITEMS()] + XMARK_ITEM() +
                        [('patch', PATH_C, None, '路徑（道路＋人行道）')]),
            ('B1 地下一層', [('split', RED, mix(RED), '北門站、台北車站地下通廊、'), (None, None, None, '機捷站體（大廳）')]),
            ('B2 地下二層', [('split', RED, mix(RED), '台北地下街（Y區）、機捷月台')]),
        ]
    ground = []
    if PARKS8: ground += [('patch', MAG, None, '主角：國家鐵道博物館（臺北機廠）、'), (None, None, None, '松山文創園區、臺北大巨蛋（酒紅剪影）'),
                          ('patch', MAG_LT, None, '主角戶外空間：廣場、花園、空地（淡酒紅）'),
                          ('patch', RED, None, '行穿線（交工處；十字路口與巷口）'),
                          ('rxhatch', RAMP_G_C, None, '市民高架匝道：落地段（地面阻隔）')]
    elif PERM: ground += [('patch', MAG, None, '主角：U02 方案量體、U03 現有建物、'), (None, None, None, '忠泰美術館街廓、懷生國小、北科大學生宿舍、'), (None, None, None, '八德市場（酒紅剪影）'),
                        ('patch', MAG_LT, None, '主角開放地：空地（部分綠化）、校園、'), (None, None, None, '瑠公圳公園、U02 方案法定空地（淡酒紅）')] + \
                       ([('patch', RED, None, '行人穿越道（非路口；可通過之路口以較深灰表示）')] if _has.get('G_XING') else [])
    elif MAIN: ground += [('patch', MAG, None, '主角：' + MAIN['name'].replace('（規劃中）', '')),
                        (None, None, None, {'Z4': '（規劃量體）＋華山1914，酒紅剪影'}.get(ZONE, '（規劃量體，酒紅剪影）'))]
    elif SRC: ground += [('patch', MAG, None, '源頭建築（流向台北車站之人群來源）')] + ([('patch', MAG_LT, None, '目的地：' + '・'.join(p['name'] for _, p in TGT) + '（主角）')] if TGT else [])
    elif SIL: ground += [('patch', MAG, None, '特性建築（酒紅剪影）')]
    if DEST['商辦／政府機關']: ground += [('patch', DEST_C['商辦／政府機關'], None, '目的地：商辦／政府機關')]
    if DEST['日常生活店家']: ground += [('patch', DEST_C['日常生活店家'], None, '目的地：日常生活店家'), (None, None, None, '（餐飲、便利超市、生活服務）')]
    if HOUSE: ground += [('patch', HOUSE_C, None, '住宅建物（住宅、一樓店面住宅）')]
    if SPORT: ground += [('patch', SPORT_C, None, '運動場（範圍內）：' + '、'.join(dict.fromkeys(p['group'] for _, p in SPORT))), (None, None, None, '（點位以圓點示意）')]
    if CM is not None:   # Z5：由上而下＝圖層由高至低
        gs_ = {p['group'] for _, p in SUPP}
        ground += [(k_, c_, None, lab) for g_, k_, c_, lab in (('停車場', 'ring', PARK_C, '配套：停車場（圓面積∝汽＋機車格）'), ('公車站', 'msq', SUP_C, '配套：公車站'),
                                                            ('YouBike', 'mtri', SUP_C, '配套：YouBike 站'), ('公廁', 'mdia', SUP_C, '配套：公廁')) if g_ in gs_]
        if HER: ground += [('patch', HER_C, None, '古蹟：建國啤酒廠（使用者指定歸類）')]
        ground += [('patch', COM_C[k], None, '商業空間：' + k) for k in ('大型商場／市場', '商業大樓／旅館', '騎樓店面', '臨街店面') if COM[k]]
    if ND is not None:   # Z7：由上而下＝圖層由高至低
        ground += [('patch', NIGHT_C[k], None, '夜間餐飲：' + k) for k in ('居酒屋／燒肉串燒', '酒吧／飲酒店', '宵夜小吃', '一般餐飲') if NIGHT[k]]
        ground += [(None, None, None, '（一樓有餐飲店家之建物，依最特定之型態）')]
    ground += [*BLD_ITEMS()]
    if SUPA: ground += [('patch', SUP_C, None, '配套：步行街、廣場、公園綠地')]
    if VAC: ground += [('patch', VAC_C, None, '空地：可用空地（空地、平面停車場）'), (None, None, None, '＋步行區、廣場、綠地')]
    if PPATH: ground += [('patch', PATH_C, None, '公園步道與鋪面（廣場、停車）')]
    if GREEN: ground += [('patch', GREEN_C, None, '純綠地（公園綠地扣除鋪面、步道、設施）')]
    ground += XMARK_ITEM() + [('patch', PATH_C, None, '路徑（道路＋人行道）')]
    fb = sorted({p['name'] for _, p in PA if level_of(p) == 'U1'})
    return [('+2 高架', [('dashdot', '#9a9a9a', None, '市民高架主線車道中心線')] + ([('dashdot', '#9a9a9a', None, '建國高架主線車道中心線')] if ELEV_X is not None else [])),
            ('+1 天橋' + ('・匝道' if RAMP_E else ''), ([('thick', RED, None, '人行天橋' + (f"（{'、'.join(fb)}）" if fb else ''))] if _has['U1'] else [])
                                                + ([('rhatch', RAMP_C, None, '市民高架匝道：高架段')] if RAMP_E else [])),
            ('±0 地面', ground),
            ('B1 地下一層', ug_items('B1')),
            ('B2 地下二層', ug_items('B2'))]

def ug_items(lv):
    # 地下層圖例：列出本段該層之地下街、站體、通廊名稱（每列約 18 字斷行）
    if not _has[lv]: return []
    nm = ug_compress(dict.fromkeys(p['name'] for _, p in PA if level_of(p) == lv and p.get('name')))
    if not nm: return [('split', RED, mix(RED), '地下通行元素')]
    lines_, cur = [], ''
    for t in nm:
        if cur and len(cur) + len(t) > 18: lines_.append(cur + '、'); cur = t
        else: cur = (cur + '、' + t) if cur else t
    lines_.append(cur)
    extra = [(None, None, None, '（地下停車場：著色限中央分隔島範圍）')] if any(p['type'] == '地下停車場' and level_of(p) == lv for _, p in PA) else []   # Z7 起
    return [('split', RED, mix(RED), lines_[0])] + [(None, None, None, l) for l in lines_[1:]] + extra

def table(fig, x, y, rows, widths, fs=7.0, lh=5.0, head=None, colors=None, bold=None, fw=None, fh=None):
    W, Hh = fw or globals()['W'], fh or globals()['Hh']
    yy = y
    if head:
        xx = x
        for t, w_ in zip(head, widths):
            fig.text(xx / W, yy / Hh, t, fontsize=fs + .3, fontweight='bold', va='top', color='#333'); xx += w_
        yy -= lh
        fig.add_artist(plt.Line2D([x / W, (x + sum(widths)) / W], [(yy + 1.1) / Hh] * 2, transform=fig.transFigure, color='#999', lw=.4))
    for i, r in enumerate(rows):
        xx = x
        for j, (t, w_) in enumerate(zip(r, widths)):
            fig.text(xx / W, yy / Hh, t, fontsize=fs, va='top', color=colors[i][j] if colors else '#222',
                     fontweight='bold' if bold and bold[i] and j < 1 else 'normal'); xx += w_
        yy -= lh
    return yy

def factor_rows():
    if ZONE != 'Z1': return factor_rows_generic()
    rows, col, bd = [], [], []
    def r(item, note, b=False): rows.append([item, note]); col.append([RED, '#444']); bd.append(b)
    cr = sorted([(g, p) for g, p in FE if p['cls'] == 'pass' and p.get('type') == 'crossing'], key=lambda gp: gp[1]['s'])
    r(f'平面穿越 {len(cr)} 處（不上圖）', '、'.join(f"{p['name']}（{p['n_stages']} 段／{p['span_m']:.0f} m）" for _, p in cr), True)
    area = collections.Counter(); cnt = collections.Counter()
    for g, p in PA: area[p['type']] += g.area; cnt[p['type']] += 1
    names = sorted({p['name'] for _, p in PA if p['type'] == '捷運／車站站體'})
    r('捷運／機捷站體', '、'.join(names) + f"（告示圖描繪，本段約 {area['捷運／車站站體'] / 1e4:.1f} ha；機捷站體與月台兩層疊合）", True)
    r('台北地下街（Y區）', f"告示圖描繪剪影，本段約 {area['地下街'] / 1e4:.1f} ha（北門站—承德路以東）", True)
    if area['車站地下通廊']: r('台北車站地下通廊', f"北側通廊（告示圖描繪），本段約 {area['車站地下通廊'] / 1e4:.2f} ha", True)
    r('地下連通道（不上圖）', f"{cnt['地下連通道']} 段（北門機捷連通道等；OSM tunnel／indoor）", True)
    r('出入口（不上圖）', f"{cnt['出入口']} 處（台北地下街 Y9–Y28、北門站 3／6／7、台北車站 1–3 等）", True)
    r('人行天橋', '承德路天橋（3.5 m 寬示意；OSM bridge=yes）', True)
    r('平面穿越間距', '／'.join(str(v) for v in DATA['stats']['gaps']) + ' m（由西向東；最長段重慶北路—承德路僅地下街可過）')
    return rows, col, bd

def factor_rows_generic():
    rows, col, bd = [], [], []
    def r(item, note, b=False): rows.append([item, note]); col.append([RED, '#444']); bd.append(b)
    cr = sorted([(g, p) for g, p in FE if p['cls'] == 'pass' and p.get('type') == 'crossing'], key=lambda gp: gp[1]['s'])
    _xm = lambda p: any(abs(q['s'] - p['s']) < 1 or abs(q.get('s2', -1e9) - p['s']) < 1 for _, q in XMARK)   # 41（經交工處行穿線核對橫越大道）
    r(f'平面穿越 {len(cr)} 處（路口上色 {sum(_xm(p) for _, p in cr)} 處）' + ('（行穿線上圖）' if PARKS8 else ''),
      '、'.join(f"{p['name']}（{p['n_stages']} 段／{p['span_m']:.0f} m" + (f"，{p['xing']}" if p.get('xing') else '')
                + ('' if _xm(p) else '，行穿線未橫越大道，不標') + '）' for _, p in cr) or '無', True)
    area = collections.Counter(); cnt = collections.Counter()
    for g, p in PA: area[p['type']] += g.area; cnt[p['type']] += 1
    ug = [t for t in ('地下街', '捷運／車站站體', '車站地下通廊') if area[t]]
    if ug:
        an = collections.Counter()
        for g, p in PA:
            if p['type'] in ug: an[(p['type'], p.get('name', ''), level_of(p))] += g.area
        r('地下街／站體', '、'.join(f"{n}（{lv}，約 {a / 1e4:.2f} ha）" for (t, n, lv), a in an.items()) + ('；OSM 站體面，單元外者淡化（使用者 2026-10-12 指定列入）' if any(p.get('ctx') for _, p in PA) else '；告示圖描繪'), True)
    else: r('地下街／站體', '無（大道中心線 80 m 內無地下街、捷運站體）', True)
    if OFFMAP: r('捷運站體（圖框外，未上圖）', '、'.join(f"{p['name']}（{p.get('level', '')}）" for p in OFFMAP) +
                 '：位於忠孝東路，距大道中心線約 350–480 m；1:2500 圖框容不下（北側餐飲建物已至圖框上緣），未上圖，列此備查', True)
    _pk = [p for g, p in PA if p['type'] == '地下停車場']
    if _pk: r('地下停車場（剪影）', '、'.join(f"{p['name'].replace('市民大道地下停車場', '')}（地下 {p.get('levels', '')} 層）" for p in _pk) +
              '：市民大道地下停車場分段包絡（寬 24 m 之比較用外框，非實測），使用者 2026-10-12 指定列為南北通行元素（B1）；著色限於大道中央分隔島範圍（使用者指定），'
              f"約 {sum(g.area for g, p in PA if p['type'] == '地下停車場') / 1e4:.2f} ha；車道出入口不上圖", True)
    r('人行天橋', '、'.join(sorted({p['name'] for _, p in PA if p['type'].startswith('人行天橋')})) or '無', True)
    _xs = [p for g, p in PA if p['type'] == '行人穿越道']
    if _xs: r('行人穿越道（上圖）', f"{len(_xs)} 處：沿大道人行道之巷口／路段行穿線（交工處；非十字路口），以橘剪影上圖", True)
    _xa = [p for g, p in PA if p['type'] == '行穿線']
    if _xa: r('行穿線（上圖）', f"交工處行穿線，本單元內 {sum(1 for p in _xa if p.get('inside'))} 塊（十字路口與巷口皆畫；單元外者淡化）", True)
    if RAMP_E or RAMP_G:
        _rn = {}
        for g, p in RAMP_E + RAMP_G:
            if g.intersects(SLAB): _rn.setdefault(p['name'], []).append(p)
        r('市民高架匝道（上圖）', '、'.join(f"{n}（高架 {sum(q['len_m'] for q in L if q['kind'] == 'ramp_elev')} m" +
          (f"／落地 {sum(q['len_m'] for q in L if q['kind'] == 'ramp_grade')} m" if any(q['kind'] == 'ramp_grade' for q in L) else '') + '）' for n, L in _rn.items())
          + '；OSM 展成面（寬＝車道數 × 3.5 m＋1.0 m）；落地段兩側不可穿越', True)
    _fx = [p for g, p in FE if p['cls'] == 'pass' and p.get('type') == 'crossing_false']
    if _fx: r('未計入之平面穿越', '、'.join(p['name'] for p in _fx) + '：13 判為橫越大道，經交工處行穿線與 Ortho_2025 空照核對為巷口行穿線（未跨越中心線），不計入平面穿越與間距')
    if cnt['出入口'] or cnt['地下連通道']: r('出入口／連通道（不上圖）', f"出入口 {cnt['出入口']} 處、連通道 {cnt['地下連通道']} 段", True)
    gaps = [round(b - a) for a, b in zip(XS, XS[1:])] if XMARK else DATA['stats']['gaps']   # 2026-10-14：依 41 核對後之平面穿越
    if gaps: r('平面穿越間距', '／'.join(str(v) for v in gaps) + ' m（由西向東；經交工處行穿線核對）')
    if PARKS8 and DATA['stats']['crossings']:   # Z8：最東之平面穿越至東界（基隆路）
        from shapely.geometry import Point as _Pt
        _s_last = max(XS or DATA['stats']['crossings']); _end = S.center.length
        _d_kl = _Pt(S.center.coords[-1]).distance(EAST_CUT) if EAST_CUT is not None else 0
        r('無平面穿越段', f"里程 {_s_last:.0f} m 以東至基隆路約 {_end - _s_last + _d_kl:.0f} m（中心線終點 {_end:.0f} m＋至基隆路 {_d_kl:.0f} m）："
          '國家鐵道博物館（臺北機廠）南緣沿高架之全段；正門朝北開於市民大道五段（地面道路）', True)
    else:
        k_ = int(ZONE[1:]); cuts_ = [S.center.project(S.center.intersection(F.CUT_G[i]).centroid) for i in (k_ - 1, k_) if i < len(F.CUT_G)]
        marks = sorted(cuts_ + list(XS or DATA['stats']['crossings']))
        r('無平面穿越段', f"單元內最長 {max(b - a for a, b in zip(marks, marks[1:])):.0f} m（{ZP_FROM_TO()}；界線路口如無行穿線亦計入）")
    return rows, col, bd

def ZP_FROM_TO():
    zp = S.ZP[ZONE]; return f"{zp['from']}—{zp['to']}"

def src_rows():
    # 源頭建築（tier S）摘要＋逐棟（名稱｜用途｜側別｜樓地板）
    if not SRC: return [], []
    n_ = [p for _, p in SRC if p['side'] == 'N']; s_ = [p for _, p in SRC if p['side'] == 'S']
    fa = lambda L: sum(p['fa'] for p in L)
    rows = [['小計', f"源頭 {len(SRC)} 棟，樓地板約 {fa(n_ + s_) / 1e4:.0f} 萬㎡：北側 {len(n_)} 棟約 {fa(n_) / 1e4:.0f} 萬㎡"
                     f"（{fa(n_) / max(fa(n_ + s_), 1):.0%}，往車站須穿越市民大道）、南側 {len(s_)} 棟約 {fa(s_) / 1e4:.0f} 萬㎡"]]
    for _, p in sorted(SRC, key=lambda gp: -gp[1]['fa']):
        rows.append([p['name'], f"{p['group']}｜{'北側・須穿越大道' if p['side'] == 'N' else '南側'}｜約 {p['fa'] / 1e4:.1f} 萬㎡（{p['levels']} 層）"])
    for _, p in TGT: rows.append([p['name'], f"目的地（淡酒紅）｜{p['note']}"])
    return rows, [[MAG, '#555']] * len(rows)

def shop_stats():
    # 日常生活店家五類統計（27_official_shops.py；官方稅籍登記＋門牌定位，明細只存 data/）→ [(類別, 北, 南, 合計), ...]、合計列
    f = H / f'data/{ZONE}_日常生活店家_五類統計_官方.csv'
    if not f.exists(): return None
    import csv as _csv
    R = list(_csv.DictReader(open(f, encoding='utf-8-sig')))
    return [(r['類別'], int(r['北']), int(r['南']), int(r['合計'])) for r in R if r['類別'] != '合計'], next(r for r in R if r['類別'] == '合計')

def shop_block(fig, x, ytop, fw, fh, fs=8.0, w_mm=126):
    # 結果區塊：類別｜長條（合計）｜北／南；長條青綠（同目的地日常生活店家色）
    st = shop_stats()
    if not st: return ytop
    rows, tot = st; k = fs / 8.0; y = ytop
    fig.text(x / fw, y / fh, '日常生活店家：現況五類（實際店面家數）', fontsize=fs + 1, fontweight='bold', va='top', color='#222'); y -= 5.4 * k
    fig.text(x / fw, y / fh, f"財政部營業（稅籍）登記 2026-10-11｜{ZONE} 範圍內｜共 {tot['合計']} 家（北 {tot['北']}、南 {tot['南']}）",
             fontsize=fs - 1.2, va='top', color='#666'); y -= 6.0 * k
    lab_w, bar_w = 34 * k, w_mm - 34 * k - 26 * k; mx = max(r[3] for r in rows) or 1
    for c, n, s_, t in rows:
        fig.text(x / fw, y / fh, c, fontsize=fs - .4, va='top', color='#222')
        bw = bar_w * t / mx
        fig.add_artist(plt.Rectangle(((x + lab_w) / fw, (y - 2.9 * k) / fh), max(bw, .3) / fw, 2.6 * k / fh, transform=fig.transFigure,
                                     facecolor=DEST_C['日常生活店家'], edgecolor='none'))
        fig.text((x + lab_w + bw + 1.5) / fw, y / fh, f'{t}', fontsize=fs - .4, fontweight='bold', va='top', color='#222')
        fig.text((x + lab_w + bar_w + 8 * k) / fw, y / fh, f'北 {n}／南 {s_}', fontsize=fs - 1, va='top', color='#555')
        y -= 4.6 * k
    return y

def dest_rows():
    # 目的地建物摘要（每類一列：棟數、南北分布、店家數、具名建物）
    rows, col = [], []
    for k, c in DEST_C.items():
        L = [p for _, p in DEST[k]]
        if not L: continue
        sides = collections.Counter(p['side'] for p in L)
        nl, no = sum(p.get('n_life', 0) for p in L), sum(p.get('n_office', 0) for p in L)
        named = [p['name'] for p in sorted(L, key=lambda p: p['d_site']) if p['name']]
        cross = sum(1 for p in L if p.get('cross'))
        t = (f"{len(L)} 棟（北 {sides['北']}、南 {sides['南']}；需跨越市民大道 {cross} 棟）｜店家：日常 {nl}、商辦金融 {no}"
             + (f"｜具名：{'、'.join(named)}" if named else ''))
        rows.append([k, t]); col.append([c, '#444'])
    return rows, col

def sports_block(fig, x, ytop, fw, fh, fs=8.0, w_mm=126):
    # 運動生活空間結果區塊（30_sports_housing 摘要）：住宅戶數＋各運動種類面積長條（範圍內深青綠、鄰近淡青綠）
    k = fs / 8.0; y = ytop; sh = SH
    fig.text(x / fw, y / fh, '運動生活：住宅、運動場與綠地', fontsize=fs + 1, fontweight='bold', va='top', color='#222'); y -= 5.6 * k
    fig.text(x / fw, y / fh, f"{ZONE} 範圍內（高架兩側 300 m）", fontsize=fs - 1.2, va='top', color='#666'); y -= 6.2 * k
    sq = lambda c: fig.add_artist(plt.Rectangle((x / fw, (y - 3.0 * k) / fh), 3.2 * k / fw, 3.2 * k / fh, transform=fig.transFigure, facecolor=c, edgecolor='none'))
    sq(HOUSE_C)
    fig.text((x + 5 * k) / fw, y / fh, f"住宅 約 {sh['households']:,} 戶・{sh['population']:,} 人", fontsize=fs + .2, fontweight='bold', va='top', color='#222'); y -= 5.0 * k
    a65 = sh['age_share']['65+']
    fig.text((x + 5 * k) / fw, y / fh, f"北側 {sh['hh_N']:,}／南側 {sh['hh_S']:,} 戶｜65 歲以上 {a65:.0%}", fontsize=fs - .6, va='top', color='#333'); y -= 4.6 * k
    fig.text((x + 5 * k) / fw, y / fh, f"住宅建物 {sh['res_buildings']} 棟（北 {sh['res_buildings_N']}／南 {sh['res_buildings_S']}）",
             fontsize=fs - .6, va='top', color='#333'); y -= 4.6 * k
    fig.text((x + 5 * k) / fw, y / fh, f"內政部 {sh['households_ym'][:3]} 年 {int(sh['households_ym'][3:])} 月村里戶數 × 住宅樓地板比例（方法區間 {sh['households_range'][0]:,}–{sh['households_range'][1]:,} 戶）",
             fontsize=fs - 1.8, va='top', color='#777'); y -= 7.0 * k
    # 運動場：只列範圍內實際有的種類（使用者 2026-10-12：範圍內有幾類就顯示幾類，不硬湊）；鄰近者只存 30 後台 CSV
    rows = [r for r in sh['sport_types'] if r[1] > 0]
    rows = sorted([r for r in rows if r[0] != '兒童遊戲場'], key=lambda r: -r[2]) + [r for r in rows if r[0] == '兒童遊戲場']
    sq(SPORT_C)
    fig.text((x + 5 * k) / fw, y / fh, f'運動場：範圍內 {len(rows)} 類（㎡）', fontsize=fs + .2, fontweight='bold', va='top', color='#222'); y -= 5.4 * k
    lab_w = 20 * k; num_w = 34 * k; bar_w = w_mm - lab_w - num_w; mx = max([r[2] for r in rows] + [1])
    for t, n_in, a_in, _, _ in rows:
        fig.text(x / fw, y / fh, t, fontsize=fs - .4, va='top', color='#222')
        b1 = bar_w * a_in / mx
        if a_in: fig.add_artist(plt.Rectangle(((x + lab_w) / fw, (y - 2.9 * k) / fh), max(b1, .3) / fw, 2.6 * k / fh, transform=fig.transFigure, facecolor=SPORT_C, edgecolor='none'))
        txt = (f"{a_in:,}" if a_in else '') + (f"（{n_in} 處）" if n_in > 1 else '')
        fig.text((x + lab_w + b1 + 1.2) / fw, y / fh, txt or '點位', fontsize=fs - 1, va='top', color='#222'); y -= 4.6 * k
    y -= 1.0 * k
    per = sh['sport_in_area'] / max(sh['households'], 1)
    fig.text(x / fw, y / fh, f"運動場（不含兒童遊戲場）{sh['sport_in_area']:,} ㎡＝每戶約 {per:.2f} ㎡", fontsize=fs - .6, fontweight='bold', va='top', color='#222'); y -= 6.4 * k
    if GPS:   # 純綠地（32_green_paths）
        sq(GREEN_C)
        fig.text((x + 5 * k) / fw, y / fh, f"純綠地 {GPS['green_m2'] / 1e4:.2f} ha", fontsize=fs + .2, fontweight='bold', va='top', color='#222'); y -= 5.0 * k
        fig.text((x + 5 * k) / fw, y / fh, f"公園綠地 {GPS['cand_m2'] / 1e4:.2f} ha 之 {GPS['green_share_of_cand']:.0%}｜每戶約 {GPS['green_m2'] / max(sh['households'], 1):.1f} ㎡",
                 fontsize=fs - .6, va='top', color='#333'); y -= 4.6 * k
        pk = [p for p in GPS['parks'] if p['green_m2'] > 0]
        for p in pk[:4]:
            fig.text((x + 5 * k) / fw, y / fh, f"{p['name']}：綠 {p['green_m2'] / 1e4:.2f}／{p['park_m2'] / 1e4:.2f} ha" + (f"，步道約 {p['path_m']:,} m" if p['path_m'] else ''),
                     fontsize=fs - 1.2, va='top', color='#555'); y -= 4.2 * k
    return y

def z4_rows():
    # A4 表：住宅（合計、各里、建物）＋運動場（範圍內逐處、鄰近依所在彙整、不開放）＋公園＋稅籍運動服務業
    if not SH: return [], []
    sh = SH; rows, col = [], []
    def r(a, b, c): rows.append([a, b]); col.append([c, '#444'])
    ag = sh['age_share']
    r('住宅（合計）', f"約 {sh['households']:,} 戶、{sh['population']:,} 人（北 {sh['hh_N']:,}／南 {sh['hh_S']:,} 戶）；四種權重之區間 {sh['households_range'][0]:,}–{sh['households_range'][1]:,} 戶；"
                     f"年齡 0–14 歲 {ag['0–14']:.0%}、15–64 歲 {ag['15–64']:.0%}、65 歲以上 {ag['65+']:.0%}", HOUSE_C)
    import csv as _csv
    for v in _csv.DictReader(open(H / f'data/{ZONE}_住宅_里別戶數.csv', encoding='utf-8-sig')):
        if int(v['分配戶數']) <= 0: continue
        r('　' + v['區'] + v['里'], f"{int(v['戶數']):,} 戶 × {float(v['權重']):.0%}（住宅樓地板在本單元之比例）→ 約 {int(v['分配戶數']):,} 戶", HOUSE_C)
    r('住宅建物（藍）', f"{sh['res_buildings']} 棟（北 {sh['res_buildings_N']}／南 {sh['res_buildings_S']}），住宅樓地板約 {sh['res_fa'] / 1e4:.1f} 萬㎡；"
                       f"另用途未標示 {sh['unk_buildings']} 棟不上色（計入戶數權重）", HOUSE_C)
    P_ = [p for _, p in CHAR if p['tier'] == 'P']
    for p in sorted([p for p in P_ if p['scope'] == '範圍內'], key=lambda p: -p['area']):
        r('運動場：' + p['group'], f"{p['name']}｜{'點位（無面積）' if p.get('point') else format(p['area'], ',') + ' ㎡'}｜{p['side']}側｜{p['note'].split('｜', 2)[-1]}", SPORT_C)
    if GPS:   # 純綠地與公園步道（32_green_paths）
        r('純綠地（合計）', f"{GPS['green_m2'] / 1e4:.2f} ha＝公園綠地 {GPS['cand_m2'] / 1e4:.2f} ha 之 {GPS['green_share_of_cand']:.0%}（扣除硬鋪面、步道、運動設施、建物；草地、樹冠、裸土皆算綠地）；"
                          f"每戶約 {GPS['green_m2'] / max(sh['households'], 1):.1f} ㎡", '#5E8F3A')
        loop_of = lambda pn: next((L for n, L, _ in sh['loops'] if n.startswith(pn)), None)
        for p in GPS['parks']:
            r('　' + p['name'], f"公園 {p['park_m2'] / 1e4:.2f} ha、純綠地 {p['green_m2'] / 1e4:.2f} ha" + (f"、鋪面 {p['pave_m2'] / 1e4:.2f} ha" if p.get('pave_m2') else '') +
              (f"；步道約 {p['path_m']:,} m" if p['path_m'] else '；無 OSM 步道') + (f"（含環狀步道約 {loop_of(p['name'])} m）" if loop_of(p['name']) else ''), '#5E8F3A')
    elif sh['parks']:
        r('公園', '、'.join(f"{p['name']} {p['area'] / 1e4:.2f} ha" for p in sh['parks']) + '（本單元內面積；OSM）', '#555')
    if sh['shops_sport']:
        r('稅籍運動服務業', f"{sum(sh['shops_sport'].values())} 家（" + '、'.join(f'{k} {v}' for k, v in sh['shops_sport'].items()) + '）；多為樓上辦公登記，無場地面積，不計入運動場', '#555')
    return rows, col

def z5_block(fig, x, ytop, fw, fh, fs=8.0, w_mm=126):
    # 商業空間之密集結果區塊（31 統計）：四種形式（棟數＋實際店面長條）、3C、可用空地、配套措施
    k = fs / 8.0; y = ytop; st = CM['stats']
    R_ = lambda x_, y_, w_, c: fig.add_artist(plt.Rectangle((x_ / fw, (y_ - 2.9 * k) / fh), max(w_, .3) / fw, 2.6 * k / fh, transform=fig.transFigure, facecolor=c, edgecolor='none'))
    fig.text(x / fw, y / fh, '商業空間之密集：現況', fontsize=fs + 1, fontweight='bold', va='top', color='#222'); y -= 5.6 * k
    fig.text(x / fw, y / fh, f"{ZONE} 範圍內（高架兩側 300 m）｜長條＝實際店面家數（稅籍登記＋OSM）", fontsize=fs - 1.2, va='top', color='#666'); y -= 6.2 * k
    rows = [(g_, len(COM[g_]), sum(p.get('n_front', 0) for _, p in COM[g_])) for g_ in COM_C]
    mx = max(r[2] for r in rows) or 1; lab_w = 28 * k; num_w = 28 * k; bar_w = w_mm - lab_w - num_w
    for g_, nb, ns in rows:
        fig.text(x / fw, y / fh, g_, fontsize=fs - .4, va='top', color='#222')
        bw = bar_w * ns / mx; R_(x + lab_w, y, bw, COM_C[g_])
        fig.text((x + lab_w + bw + 1.2) / fw, y / fh, f'{nb} 棟・店 {ns}', fontsize=fs - 1, va='top', color='#222'); y -= 4.6 * k
    gh = next((p for _, p in COM['大型商場／市場'] if '光華數位新天地' in p['name']), None)
    fig.text(x / fw, y / fh, f"其中 3C（電腦、通訊、家電零售）{st['n_3c']} 家" + (f"；光華數位新天地一棟 {gh['n_3c']} 家" if gh else ''),
             fontsize=fs - .8, va='top', color='#333'); y -= 7.0 * k
    va = sum(p['area'] for _, p in VAC_U); nv = collections.Counter(p['group'] for _, p in VAC_U)
    R_(x, y, 3.2 * k, VAC_C)
    fig.text((x + 5 * k) / fw, y / fh, f"空地 約 {sum(p['area'] for _, p in VAC) / 1e4:.2f} ha", fontsize=fs + .2, fontweight='bold', va='top', color='#222'); y -= 5.0 * k
    pa_ = [p for _, p in OPEN5 if p['group'] == '步行街／廣場']; pk_ = [p for _, p in OPEN5 if p['group'] == '公園綠地']
    for t in (f"可用空地 {len(VAC_U)} 處 約 {va:,} ㎡（" + '、'.join(f'{g_} {n_}' for g_, n_ in nv.items()) + '）',
              f"步行區／廣場 約 {sum(p['area'] for p in pa_):,} ㎡；綠地 {len(pk_)} 處 約 {sum(p['area'] for p in pk_):,} ㎡",
              f"施工中 {st['counts'].get('construction|施工中', 0)} 處不列"):
        fig.text((x + 5 * k) / fw, y / fh, t, fontsize=fs - .8, va='top', color='#333'); y -= 4.6 * k
    return y

def z5_rows():
    # A4 表：商業空間（四形式）、古蹟、配套措施（面、點）、可用空地（逐處）、施工中（不列）
    if CM is None: return [], []
    rows, col = [], []
    def r(a, b, c): rows.append([a, b]); col.append([c, '#444'])
    for g_, c_ in COM_C.items():
        L = [p for _, p in COM[g_]]
        if not L: continue
        sd = collections.Counter(p['side'] for p in L); ns = sum(p.get('n_front', 0) for p in L); n3 = sum(p.get('n_3c', 0) for p in L)
        arc = collections.Counter(p.get('arcade') for p in L if p.get('arcade'))
        named = [p['name'] for p in sorted(L, key=lambda p: -p.get('n_front', 0)) if p['name']][:8]
        r('商業空間：' + g_, f"{len(L)} 棟（北 {sd['北']}／南 {sd['南']}）｜實際店面 {ns} 家（3C {n3}）"
          + (f"｜騎樓：官方 {arc['官方']}、推估 {arc['推估']}" if arc else '') + (f"｜{'、'.join(named)}" if named else ''), c_)
    if HER:
        nm = [p['name'].replace('建國啤酒廠：', '') for _, p in HER]
        r('古蹟：建國啤酒廠', f"{len(HER)} 棟、建築面積約 {sum(p.get('area', 0) for _, p in HER):,} ㎡（使用者 2026-10-12 指定歸類古蹟；仍在生產）｜" + '、'.join(n for n in nm if '未具名' not in n)[:120], HER_C)
    for _, p in sorted(VAC_U, key=lambda gp: -gp[1]['area']):
        r('空地：可用（' + p['group'] + '）', f"{p['name']}｜約 {p['area']:,} ㎡｜{p['side']}側｜{p['note']}", '#8A8726')
    for g_, lab in (('步行街／廣場', '空地：步行區／廣場'), ('公園綠地', '空地：綠地')):
        a_ = collections.Counter()
        for _, p in OPEN5:
            if p['group'] == g_: a_[p['name'].replace('：開放廣場', '開放廣場')] += p['area']
        L = [(n_, v) for n_, v in a_.most_common() if v >= 50]
        if L: r(lab, '、'.join(f"{n_} {v:,} ㎡" for n_, v in L) + f"（計 {sum(a_.values()):,} ㎡）", '#8A8726')
    con = [f['properties'] for f in CM['features'] if f['properties']['cat'] == 'construction']
    if con: r('施工中（不列為可用空地）', '、'.join(f"{p['name']}（約 {p['area']:,} ㎡）" for p in con), '#999')
    return rows, col

def z7_block(fig, x, ytop, fw, fh, fs=8.0, w_mm=126):
    # 夜間餐飲結果區塊（34 統計）：各型態一樓店家數長條，依營業時段分段（宵夜／晚餐／不明），右側北／南
    k = fs / 8.0; y = ytop; nd = ND
    fig.text(x / fw, y / fh, '夜間餐飲：型態 × 營業時段', fontsize=fs + 1, fontweight='bold', va='top', color='#222'); y -= 5.6 * k
    fig.text(x / fw, y / fh, f"{ZONE} 範圍內一樓餐飲 {nd['shops']} 家（北 {nd['shops_N']}／南 {nd['shops_S']}）｜餐飲建物 {nd['buildings']} 棟",
             fontsize=fs - 1.2, va='top', color='#666'); y -= 6.2 * k
    lab_w, num_w = 30 * k, 56 * k; bar_w = w_mm - lab_w - num_w   # 長條後之數字（含宵夜／晚餐）約 32 mm，右側北／南欄 18 mm
    tot = lambda t: sum(nd['matrix'][t][h][sd] for h in nd['hours'] for sd in ('北', '南'))
    mx = max([tot(t) for t in nd['types']] + [1])
    for t in nd['types']:
        fig.add_artist(plt.Rectangle((x / fw, (y - 2.9 * k) / fh), 2.6 * k / fw, 2.6 * k / fh, transform=fig.transFigure, facecolor=NIGHT_C[t], edgecolor='none'))
        fig.text((x + 3.8 * k) / fw, y / fh, t, fontsize=fs - .6, va='top', color='#222')
        xx = x + lab_w
        for h in nd['hours']:
            v = sum(nd['matrix'][t][h][sd] for sd in ('北', '南'))
            if not v: continue
            w_ = bar_w * v / mx
            fig.add_artist(plt.Rectangle((xx / fw, (y - 2.9 * k) / fh), max(w_, .3) / fw, 2.6 * k / fh, transform=fig.transFigure, facecolor='white', edgecolor='#333333', lw=.3, hatch=HOURS_H[h]))
            xx += w_
        n_ = sum(nd['matrix'][t][h]['北'] for h in nd['hours']); s_ = sum(nd['matrix'][t][h]['南'] for h in nd['hours'])
        lt = sum(nd['matrix'][t]['宵夜'][sd] for sd in ('北', '南')); dn = sum(nd['matrix'][t]['晚餐'][sd] for sd in ('北', '南'))
        fig.text((xx + 1.2) / fw, y / fh, f"{tot(t)}" + (f"（宵夜 {lt}" + (f"、晚餐 {dn}" if dn else '') + '）' if lt or dn else (f"（晚餐 {dn}）" if dn else '')),
                 fontsize=fs - 1, va='top', color='#222')
        fig.text((x + w_mm - 18 * k) / fw, y / fh, f"北 {n_}／南 {s_}", fontsize=fs - 1.2, va='top', color='#555')
        y -= 4.8 * k
    y -= .6 * k; xx = x
    for h, lab in (('宵夜', '宵夜（營業至 23 點後）'), ('晚餐', '晚餐（18–20 點營業）'), ('不明', '營業時間不明')):
        fig.add_artist(plt.Rectangle((xx / fw, (y - 2.6 * k) / fh), 2.4 * k / fw, 2.4 * k / fh, transform=fig.transFigure, facecolor='white', edgecolor='#333333', lw=.3, hatch=HOURS_H[h]))
        fig.text((xx + 3.4 * k) / fw, y / fh, lab, fontsize=fs - 1.6, va='top', color='#444')
        xx += 3.4 * k + sum(1.0 if ord(c) >= 0x2E80 else .55 for c in lab) * (fs - 1.6) * .3528 + 4 * k   # 字寬（pt→mm）＋間距
    y -= 5.2 * k
    fig.text(x / fw, y / fh, f"營業時間僅 OSM 有標示（{nd['hours_known']} 家，其中宵夜 {nd['late']}、晚餐 {nd['dinner']}）；稅籍無營業時間，其餘列為不明",
             fontsize=fs - 1.6, va='top', color='#777'); y -= 4.6 * k
    return y

def z7_rows():
    # A4 表：各型態（棟數、店家數、營業時段、代表店家）、營業時間、資料來源、不計
    if ND is None: return [], []
    nd = ND; rows, col = [], []
    def r(a, b, c): rows.append([a, b]); col.append([c, '#444'])
    for t in nd['types']:
        L = [p for _, p in NIGHT[t]]
        m = nd['matrix'][t]
        n_ = sum(m[h]['北'] for h in nd['hours']); s_ = sum(m[h]['南'] for h in nd['hours'])
        bs = nd['buildings_by_type_side'].get(t, {'北': 0, '南': 0})
        top = nd.get('examples', {}).get(t, [])[:10]                 # 該型態之代表店家（營業時間已知者、OSM 招牌名優先）
        r('夜間餐飲：' + t, f"建物 {len(L)} 棟（北 {bs['北']}／南 {bs['南']}）｜一樓店家 {n_ + s_} 家（北 {n_}／南 {s_}）｜營業時段："
          + '、'.join(f"{h} {m[h]['北'] + m[h]['南']}" for h in nd['hours'] if m[h]['北'] + m[h]['南']) + (f"｜{'、'.join(top)}" if top else ''), NIGHT_C[t] if t != '一般餐飲' else '#C9787A')
    r('營業時段', f"OSM 標示營業時間者 {nd['hours_known']} 家：營業至 23 點後（宵夜）{nd['late']}、涵蓋 18–20 點（晚餐）{nd['dinner']}；其餘 {nd['shops'] - nd['hours_known']} 家不明"
      '（稅籍無營業時間，OSM 多未標示）。標示晚間不營業者不列。', '#555')
    bs_ = nd['by_source']
    r('資料來源', f"OSM {bs_.get('OSM', 0)}、OSM＋稅籍（店名對應）{bs_.get('OSM＋稅籍', 0)}、僅稅籍 {bs_.get('稅籍', 0)} 家；建物店家數取 max（OSM、稅籍）", '#555')
    ex = nd['excluded']
    r('不計', '、'.join(f"{k} {v}" for k, v in sorted(ex.items(), key=lambda kv: -kv[1]) if not k.startswith(('與 OSM', '建物店家數'))), '#999')
    return rows, col

NOTE_Z = {}
def z6_rows():
    # Z6：主角＝公辦都更＋滲透場所（使用者 2026-10-12）；逐場所列 建物／開放地 面積、側別、距中心線
    if not PERM: return [], []
    import collections as _c
    G_ = _c.OrderedDict()
    for g, p in CHAR:
        if p['tier'] in ('A', 'O'): G_.setdefault(p['group'], []).append((g, p))
    DESC = {'主角：U02': '住都中心公辦都更方案（23 層住宅，1 樓托嬰中心＋店鋪；公聽會版）；基地 4,511 ㎡（範圍不上圖），基地內現有建物拆除改建，不畫',
            '主角：U03': '都更處 S14，無方案；基地 4,107 ㎡（範圍不上圖）；現有建物（中崙球場等）上色（使用者指定）',
            '忠泰美術館街廓': '忠泰美術館（忠泰企業大樓）＋明日博；街廓內未建築部分＝空地（部分綠化，使用者確認）',
            '北科大學生宿舍': '學生（國立臺北科技大學，建國南路以東、瑠公圳公園南側）；使用者指定列入',
            '瑠公圳公園': '沿舊瑠公圳之帶狀公園；跨巷道部分扣除路徑',
            '懷生國小': '學生；校地扣除建物＝校園開放地', '八德市場': '跨建國高架刀位（Z5 47%／Z6 53%），使用者指定歸 Z6'}
    DESC.update({'國家鐵道博物館（臺北機廠）': '大道（高架）北側；OSM 臺北機廠鐵道博物館園區（historic=heritage），2025-07-31 第一階段開放；正門朝北開於市民大道五段；另含大道南側之縫紉工場舊址',
                 '松山文創園區': '大道南側；原松山菸廠（1998 年停產），OSM recreation_ground；含巴洛克花園、生態池',
                 '臺北大巨蛋（文化體育園區）': '大道南側；OSM 臺北文化體育園區扣除與松菸重疊；含臺北大巨蛋（2023-12 啟用）、遠雄巨蛋大樓'})   # Z8
    rows, col = [], []
    for k, gp in G_.items():
        a_ = sum(g.area for g, p in gp if p['tier'] == 'A'); o_ = sum(g.area for g, p in gp if p['tier'] == 'O')
        sd = gp[0][1].get('side') or ('北' if k.startswith('主角') else '')
        d_ = min(p.get('dist_m') or 0 for _, p in gp)
        parts = [f"{sd}側、距中心線 {d_} m" if sd else f"距中心線 {d_} m"]
        if a_: parts.append(('方案量體 ' if any(p.get('planned') for _, p in gp) else '建物 ') + f"{a_:,.0f} ㎡")
        if o_: parts.append(('戶外空間' if PARKS8 else '開放地') + f" {o_:,.0f} ㎡")
        rows.append([k, '｜'.join(parts) + '。' + DESC.get(k, '')]); col.append([MAG, '#444'])
    if PARKS8:   # Z8：公共案件基地（範圍不上圖）
        for _, p in CHAR:
            if p.get('site'): rows.append([p['name'].split(' ')[0] + '（不上圖）', '公辦都更基地範圍（workflow 三 Z8 主角「含 U10」）｜' + p['note']]); col.append([MAG, '#555'])
    return rows, col

NOTE_Z['Z6'] = [
    '判斷標準（使用者 2026-10-12 指定）：Z6 的特色是忠泰美術館那塊和旁邊的瑠公圳公園、懷生國小、八德市場——有空地、學生、綠地，很適合在高架下方做改動以加強地區之間的滲透性，'
    '一樣列為主角調查；與 workflow 三之主角長安段公辦都更（U02／U03）並列；同日補充北科大學生宿舍（學生）列入。U02 畫方案量體（基地內現有建物拆除改建，不畫）；U03 無方案，現有建物（中崙球場等）上色。',
    '  場所範圍：忠泰美術館街廓＝忠泰企業大樓（市民大道三段 178 號）所在、由路徑圍出之街廓（含明日博）；瑠公圳公園、懷生國小＝OSM 公園／學校面；八德市場＝OSM 市場建物（跨建國高架刀位，歸 Z6）；北科大學生宿舍＝OSM 宿舍建物（與線稿同形）。'
    '建物＝線稿建物，開放地＝範圍扣除路徑與建物。',
    '  通行元素：捷運站體列入（忠孝新生 B1、忠孝復興 B2；OSM 站體面），位於單元外者以範圍外淡化表現；平面穿越中，十字路口（建國南路、安東街）之行穿線不上圖，'
    '非十字路口之行穿線（沿大道人行道之巷口行穿線 5 處）以橘剪影上圖；13 判為平面穿越之里程 3539 m 經交工處行穿線與空照核對為巷口行穿線，不計。'
    '建國南路—安東街 538 m 間無橫越大道之平面穿越，僅懷生國小西側人行天橋（OSM footway bridge）可南北穿越。',
    '表現：圖層依高程排列；建物依樓高 5 級灰（0–5／6–11／12–19／20–29／30 層以上，越高越深；臺北三維模型 2017）；路徑淡灰（黑 11%）；酒紅＝主角建物；淡酒紅＝主角開放地；橘＝通行元素；灰點鏈＝市民高架、建國高架主線車道中心線。',
    '資料：建物＝02 線稿；路徑＝整合後道路面＋新工處人行道（26 空照補齊碎塊）；平面穿越＝交工處行穿線（13）；場所、捷運站體、建國高架、天橋＝OSM（臺灣 PBF 2026-09-08）；'
    'U02／U03＝公共案件量體與基地（住都中心公聽會簡報描圖、都更處地號）。',
    '未上圖（使用者指定）：街廓輪廓、地圖註解、十字路口之行穿線、中央分隔島、圍牆／圍籬／綠籬、停車場車道出入口、高架匝道、無平面穿越長段、地下連通道、出入口、公辦都更基地範圍。',
    '限制：場所範圍依 OSM 與線稿，非地籍；忠泰美術館街廓之未建築部分為空地（部分綠化，使用者確認），綠化範圍未另行區分；天橋於空照被高架橋面遮蔽，位置依 OSM，待現勘；U02 方案為公聽會版本，非核定。',
    '© OpenStreetMap contributors / ODbL｜政府資料開放授權條款第 1 版｜2026-10-12']
NOTE_Z['Z7'] = [
    '判斷標準（使用者 2026-10-12 指定）：Z7 主角＝東區北緣宵夜／居酒屋餐飲帶（workflow 三；微風廣場不列為主角）。特性建築＝範圍內一樓有餐飲店家之建物，依型態分四色：'
    '居酒屋／燒肉串燒、酒吧／飲酒店、宵夜小吃、一般餐飲；建物取店家中最特定之型態。統計為夜間餐飲專用分類（型態 × 營業時段 × 南北），正常營業時間之晚餐也列入。',
    '  型態：OSM 料理標籤（izakaya、yakitori、yakiniku、barbecue；noodle、ramen、taiwanese 等）與店名關鍵字（居酒、串燒、燒鳥、燒肉、炭火；酒吧、酒館、啤酒、Bar；熱炒、小吃、麵、粥、滷味等），'
    'OSM bar／pub 為酒吧；稅籍飲酒店為酒吧、麵店小吃店與餐食攤販為宵夜小吃，其餘餐館為一般餐飲。早餐、咖啡、手搖飲、冰品甜點、外燴不列（非晚餐）。',
    '  營業時段：依 OSM opening_hours，營業至 23 點以後（含跨午夜）為宵夜、涵蓋 18–20 點為晚餐、未標示為不明；稅籍無營業時間。'
    '店家數：店家點落在建物內，否則歸 15 m 內最近之本單元建物；OSM 與稅籍以店名對應，建物店家數取兩者較多者；只計一樓（稅籍一樓、地下或未載樓層；同址 ≥ 3 家為借址登記不計）。',
    '  通行元素：市民大道地下停車場（建復、復敦、敦延、延吉段）以剪影列入 B1（使用者指定），著色限於大道中央分隔島範圍（分段包絡 ∩ 分隔島，扣除路徑與建物）；捷運站體（忠孝復興、忠孝敦化、國父紀念館）位於忠孝東路，落在 1:2500 圖框南緣之外，未上圖，列於「通行元素」表；行穿線不上圖（十字路口與巷口皆不畫，使用者指定），'
    '平面穿越經交工處行穿線核對是否橫越大道後列於「通行元素」表。',
    '表現：圖層依高程排列；建物依樓高 5 級灰（0–5／6–11／12–19／20–29／30 層以上，越高越深；臺北三維模型 2017）；路徑淡灰（黑 11%）；酒紅色階＝夜間餐飲建物（居酒屋／燒肉串燒最深 → 一般餐飲最淺，同 Z5 已驗證色階）；橘＝通行元素。統計長條之斜線為營業時段（宵夜交叉線、晚餐單斜線、不明空白；不用灰階以免與建物樓高灰同色異義）。',
    '資料：建物＝02 線稿；建物歸屬＝01_classify（跨單元者歸重疊面積最大之單元）；餐飲＝OSM 2026-09-08（點＝03 osm_poi_nodes、面＝臺灣 PBF）＋財政部全國營業（稅籍）登記資料集 2026-10-11 版（27 門牌定位）；'
    '地下停車場＝Civic_Rebuild ParkingSections（03 07_parking）；平面穿越＝交工處行穿線（13）。明細只存 data/（後台）：Z7_夜間餐飲_明細.csv（含不計者與原因）。',
    '未上圖（使用者指定）：街廓輪廓、地圖註解、行穿線（十字路口與巷口）、中央分隔島、圍牆／圍籬／綠籬、停車場車道出入口、高架匝道、無平面穿越長段；微風廣場不另標為主角。',
    '限制：營業時間僅少數 OSM 店家有標示，宵夜／晚餐比例只代表已標示者；稅籍登記地址不等於實際店面，居酒屋多登記為餐廳（依店名補判）；OSM 非完整普查；地下停車場外框為寬 24 m 之比較用包絡，非實測，'
    '人行出入口位置未查；評圖前宜夜間現勘。',
    '© OpenStreetMap contributors / ODbL｜政府資料開放授權條款第 1 版｜2026-10-12']
NOTE_Z['Z8'] = [
    '判斷標準（使用者 2026-10-12 指定）：Z8 要表達的問題＝南北兩側園區串連。主角依 workflow 三：松山文創＋大巨蛋＋國家鐵道博物館（含 U10）——三園區之建物（酒紅）與戶外空間（淡酒紅）；'
    '匝道、行穿線上圖。U10 為公辦都更基地範圍（非建物），不上圖。',
    '  園區範圍：OSM 臺北機廠鐵道博物館園區（historic=heritage；含大道南側之縫紉工場舊址，園區南緣即高架）、松山文創園區（recreation_ground）、臺北文化體育園區（扣除與松菸重疊；含大巨蛋、遠雄巨蛋大樓）；'
    '建物＝範圍內線稿建物＋線稿缺漏之 OSM 建物；戶外空間＝範圍扣除路徑與建物。',
    '  單元東界：市民大道中心線（02）止於高架轉向基隆路處（E307105），原 Z8 詳細平面以中心線終點為東端；本圖依 workflow 三「光復南路—基隆路」，以基隆路一段中心線（雙向車道平均）為東界，走廊外垂直延伸（五-1）。',
    '  現況：地面市民大道五段在本段向東北偏離高架，沿臺北機廠北緣而行——機廠位於高架北側、地面道路南側，正門朝北開於市民大道五段；松菸、大巨蛋在高架南側。'
    '高架下（菸廠路）之平面穿越 3 處皆在西段（光復南路、里程 5577、5726 m，間距 150 m），以東至基隆路約 612 m（機廠南緣全段）無平面穿越、天橋或地下道；'
    '基隆路側 4 段地下道為跨越基隆路（松山高中），非南北穿越大道，不上圖。里程 5670 m 經核對為巷口行穿線，不計。',
    '  匝道：OSM highway=trunk_link（名稱含匝道）展成面，寬＝車道數 × 3.5 m＋1.0 m；bridge=yes 為高架段（灰，+1），其餘為落地段（深灰，地面阻隔）。'
    '行穿線：交工處行穿線（2024-07）於圖框內者全部上圖（十字路口與巷口），單元外者淡化。',
    '表現：圖層依高程排列；建物依樓高 5 級灰（0–5／6–11／12–19／20–29／30 層以上，越高越深；臺北三維模型 2017）；路徑淡灰（黑 11%）；酒紅＝主角三園區建物；淡酒紅＝主角戶外空間；橘＝行穿線；灰＝匝道高架段、深灰＝匝道落地段；灰點鏈＝市民高架主線車道中心線。'
    '地圖高 310 mm（主角南北跨距約 740 m；其餘單元 270 mm）。',
    '資料：建物＝02 線稿；路徑＝整合後道路面＋新工處人行道（26 空照判讀補齊碎塊 20 塊）；平面穿越＝交工處行穿線（13，經 19 核對是否橫越大道）；園區、匝道、基隆路＝OSM（臺灣 PBF 2026-09-08）；U10＝都更處地號清單＋地籍 GIS。',
    '未上圖（沿用 Z1 規格）：街廓輪廓、地圖註解、中央分隔島、圍牆／圍籬／綠籬、停車場車道出入口、無平面穿越長段（列於「通行元素」表）、地下連通道、出入口、U10 基地範圍。',
    '限制：園區範圍依 OSM，非地籍；臺北機廠部分建物修復中，開放範圍未逐棟查核；匝道寬為示意（非實測橋面）；行穿線以 2024-07 資料為準，評圖前宜現勘。',
    '© OpenStreetMap contributors / ODbL｜政府資料開放授權條款第 1 版｜2026-10-12']
NOTE_Z['Z5'] = [
    '判斷標準（使用者 2026-10-12 指定）：Z5 主題＝商業空間之密集；標出各種形式的商業空間，重點為可用的空地與已存在之商業空間（大商場、騎樓店家等）；建國啤酒廠歸類為古蹟。範圍＝Z5 單元多邊形（高架兩側 300 m；跨單元建物歸重疊面積最大之單元）。',
    '  商業空間（依序判定）：大型商場／市場＝OSM shop=mall、amenity=marketplace（光華數位新天地、三創生活園區、光華玉市／新光華商場）；商業大樓／旅館＝OSM building=commercial／retail／hotel 或土地使用以商業為主；騎樓店面＝一樓有實際店面且臨騎樓（停管處機車退出騎樓路段，或依臺北市建築管理自治條例臨主要道路貼齊者推估 3.64 m）；臨街店面＝一樓有實際店面、無騎樓。實際店面＝財政部營業（稅籍）登記之零售、餐飲、個人服務、娛樂、醫療（一樓、地下或未載樓層；同址 ≥ 3 家為借址登記不計），與 OSM 店家點取多者；大型商場不限樓層。北科大校園建物屬文教，不列。',
    '  空地（同一圖層，使用者 2026-10-12 將步行區、廣場、綠地併入空地圖層以減少圖面顏色）：可用空地＝扣除路徑、建物、公園、校園、古蹟廠區、宗教用地、商場廣場、施工中基地後之開放地（≥ 100 ㎡），加上 OSM 平面停車場與「線稿仍為建物、2025 空照為裸土」之已拆除基地，逐塊以 Ortho_2025 空照判讀，空地與作臨時停車之平面停車場列為可用；步行區／廣場＝OSM 步行區與廣場，加上商場基地內扣除建物與道路之開放鋪面（三創—光華數位新天地之間廣場、希望廣場）；綠地＝OSM 公園。施工中基地不列。',
    '表現：圖層依高程排列；建物依樓高 5 級灰（0–5／6–11／12–19／20–29／30 層以上，越高越深；臺北三維模型 2017）；路徑淡灰（黑 11%）；酒紅色階＝商業空間（大型商場最深、臨街店面最淺）；紫＝古蹟；淡綠＝空地（可用空地、步行區、廣場、綠地）；橘＝通行元素（含光華數位新天地—三創空橋）。配色經 OKLab ΔE 與色覺模擬（紅、綠、藍色弱）驗證。十字路口（平面穿越）不上圖，僅列於「通行元素」表。',
    '資料：建物＝02 線稿；建物用途＝01_classify 土地使用；店面＝財政部全國營業（稅籍）登記資料集 2026-10-11 版（27 門牌定位）＋OSM 店家點（06_industry）；騎樓＝04 與停管處機車退出騎樓路段；OSM 2026-09-08（29_osm_extras）；空照＝臺北市 Ortho_2025；平面穿越＝交工處行穿線（13）。明細只存 data/（後台）：Z5_commercial_EPSG3826.geojson。',
    '未上圖（使用者指定）：街廓輪廓、地圖註解、十字路口（平面穿越）、中央分隔島、圍牆／圍籬／綠籬、停車場車道出入口、高架匝道、無平面穿越長段；配套措施（停車場、公車站、YouBike、公廁；使用者 2026-10-12 刪除，QGIS 保留隱藏層）；施工中基地。',
    '限制：稅籍登記地址不等於實際店面，商場內店家多登記樓上；OSM 店家點非完整普查；騎樓第二排以後依規則推估，實際有無須現勘；線稿與 OSM 皆有缺漏建物（空照可見），空地判讀以 2025 空照為準，權屬與使用許可未查。',
    '© OpenStreetMap contributors / ODbL｜政府資料開放授權條款第 1 版｜2026-10-12']
NOTE_Z['Z4'] = [
    '判斷標準（使用者 2026-10-12 指定）：Z4 主軸＝運動生活空間；調查周圍之住宅數量，以及運動場面積涵蓋之運動種類（範圍內實際有幾類就列幾類）；另標純綠地與公園步道。主角依 workflow 三：華山（司法園區 B01＋華山1914＋大草原），酒紅＝B01 規劃量體（司法院 2023-03-20 方案描圖）與華山1914 建物。',
    '  住宅：戶數＝內政部戶政司村里戶數（115 年 9 月）× 各里住宅樓地板落在 Z4 之比例（住宅＋一樓店面〔扣一樓〕＋未標示用途；樓層依臺北三維模型 2017，未覆蓋者依 OSM）；里界＝內政部村里界 114 年版。另以里面積、住宅建築面積、住宅樓地板、住宅＋未標示建築面積四種權重試算，列為區間。藍＝本單元內主要用途為住宅或一樓店面（住宅／街屋）之建物。',
    '  運動場：OSM（2026-09-08）球場、跑道、體健設施、兒童遊戲場，種類依 sport 標籤、面積依 OSM 面；逐處以臺北市 Ortho_2025 空照核對（樹冠遮蔽者依 OSM）。只列與 Z4 重疊最大者（範圍內）；單元外之學校運動場、新生高架橋下球場只存後台明細。',
    '  純綠地：公園綠地（OSM leisure=park／garden、landuse=grass、natural=wood 等）扣除硬鋪面、公園步道、運動設施與建物之範圍；草地、樹冠、裸土、枯草皆算綠地，公園內不留白洞。硬鋪面＝Ortho_2025 灰色低彩度成片（≥ 40 m²）且與步道或公園邊界相連者（廣場、停車），與公園步道同繪淡灰，輪廓以圓角平滑（約 3.5 m）只表達大概形狀；孤立於草地中之灰塊（空照浮水印、陰影）不計。公園步道＝OSM footway／path／steps／service 等落在公園綠地內之段，依 width 標籤展寬（無標籤者步道 2.5 m、小徑 1.5 m、服務道路 3 m）。',
    '表現：圖層依高程排列；建物依樓高 5 級灰（0–5／6–11／12–19／20–29／30 層以上，越高越深；臺北三維模型 2017）；路徑與公園步道淡灰（黑 11%）；淡綠＝純綠地；酒紅＝主角；黃＝住宅建物；綠＝運動場（點位以直徑 6 m 圓點示意）；橘＝通行元素。本段大道中心線 80 m 內無地下街、捷運站體或人行天橋（華山車站為保存之舊站房，非通行元素）；十字路口（平面穿越）不上圖，僅列於「通行元素」表。',
    '資料：建物＝02 線稿；建物用途＝01_classify 土地使用；平面穿越＝交工處行穿線（13）；B01＝公共案件量體與基地；戶數＝內政部 opendata11509M030.csv；里界＝VILLAGE_NLSC_11401031；運動服務業＝財政部營業（稅籍）登記 2026-10-11 版（27 定位）；純綠地＝Ortho_2025＋04_green。明細只存 data/（後台）：Z4_住宅_里別戶數.csv、Z4_運動場_明細.csv（含鄰近）、Z4_green_paths_EPSG3826.geojson。',
    '未上圖（使用者指定）：街廓輪廓、地圖註解、十字路口（平面穿越）、中央分隔島、圍牆／圍籬／綠籬、停車場車道出入口、高架匝道、無平面穿越長段；B01 基地範圍（非建物）；單元外之運動場。',
    '限制：戶數為依樓地板比例分配之推估（非逐戶門牌），北／南分配同法；OSM 運動設施非完整普查；純綠地之鋪面以 2025 空照色彩判讀，40 m² 以下或未與動線相連之鋪面計入綠地；公園步道依 OSM，未標示之小徑未計；未標示用途建物不上色；稅籍運動服務業無場地面積。',
    '© OpenStreetMap contributors / ODbL｜政府資料開放授權條款第 1 版｜2026-10-12']
NOTE_Z['Z3'] = [
    '判斷標準（使用者 2026-10-11 指定）：特性建築＝主角 U17 行二行三公辦都更（2024 公聽會方案描圖，規劃中；基地內現有建物以拆除改建處理，不上圖）＋U17 完成後新增之辦公與居住人口在 Z3 範圍內會走去之目的地建物，分兩色：',
    '  商辦／政府機關（藍）＝含 OSM 商辦金融店家點，或建物土地使用以辦公、政府機關／公共服務為主；日常生活店家（青綠）＝含餐飲、便利超市、生活服務店家點（06_industry「日常生活服務」族）；',
    '  兩者兼有者比家數（辦公／政府機關用途商辦加 1），同數依土地使用；員工餐廳不計。範圍＝Z3 單元多邊形（高架兩側 300 m；跨單元建物歸重疊面積最大之單元）。',
    '表現：圖層依高程排列；建物依樓高 5 級灰（0–5／6–11／12–19／20–29／30 層以上，越高越深；臺北三維模型 2017）；路徑淡灰（黑 11%）；酒紅＝主角規劃量體；藍、青綠＝目的地建物（配色經色覺辨識驗證）。本段大道中心線 80 m 內無地下街、捷運站體或人行天橋；十字路口（平面穿越）不上圖，僅列於「通行元素」表。',
    '資料：建物＝02 線稿；店家＝OSM（2026-09-08）經 06_industry 分類；建物用途＝01_classify 土地使用；平面穿越＝交工處行穿線（13）；U17＝公共案件量體與基地（2024 公聽會描圖）。',
    '資料（日常生活店家五類，27）：財政部全國營業（稅籍）登記資料集 2026-10-11 版，以 OSM 門牌點定位（全部完全對號）；依主行業代號分五類；同一完整地址登記 ≥ 3 家視為借址登記不計，便利商店與零售限一樓或地下；診所等醫療機構免營業稅，不在資料內。明細只存 data/（後台）。',
    '未上圖（使用者指定）：街廓輪廓、地圖註解、十字路口（平面穿越）、中央分隔島、圍牆／圍籬／綠籬、停車場車道出入口、高架匝道、無平面穿越長段；U17 基地範圍（非建物）。',
    '限制：OSM 店家點非完整普查（約為實際店家之一部分），無店家點之一樓店面未計入；U17 方案為公聽會版本，非核定；建物以線稿輪廓計。',
    '© OpenStreetMap contributors / ODbL｜政府資料開放授權條款第 1 版｜2026-10-11']

NOTE_Z['Z2'] = [
    '判斷標準（使用者 2026-10-11 指定）：特性建築＝Z2 範圍內，流向台北車站之人群的源頭建築。目的地＝臺北車站（台鐵／高鐵站房，主角之一，淡酒紅）；',
    '  源頭（酒紅）＝Z2 單元多邊形內（高架兩側 300 m；跨單元建物歸重疊面積最大之單元）總樓地板 ≥ 1 萬㎡ 之建物，用途不限（停車場、施工中除外）；臺北轉運站（京站複合體）為轉乘源，不設門檻。',
    '  樓地板＝臺北三維模型（2017）各量體高度 ÷ 3.3 取整 × 量體面積逐一加總，未覆蓋部分以 OSM 樓層計。北側源頭往車站須穿越市民大道。',
    '表現：圖層依高程排列（B2 台北地下街 Y區 → B1 車站地下通廊・捷運台北車站北端大廳・中山地下街 R區 → 地面路徑・建物・目的地・源頭建築 → +1 承德路天橋 → +2 高架）；地下層在路徑之下，路徑為黑 11%（色彩增值等效）；建物依樓高 5 級灰（0–5／6–11／12–19／20–29／30 層以上，越高越深；臺北三維模型 2017）；通行元素橘不透明；十字路口（平面穿越）不上圖，僅列於「通行元素」表。',
    '資料：建物＝02 線稿；樓層＝臺北三維模型（2017）、OSM；建物用途＝01_classify 土地使用；平面穿越＝交工處行穿線（13）；地下街、捷運站、車站地下通廊＝Metro Taipei「台北車站全區位置圖」站內告示描繪，',
    '  16 個路口控制點薄板樣條（TPS）對位（Z2 增中山北路 4 點；留一驗證中位誤差約 10 m）；中山地下街 R區改用 OSM 面（告示圖描繪偏西 15–20 m，以對準心中山線形公園）；天橋＝OSM（2026-09-09）。',
    '未上圖（使用者指定）：街廓輪廓、地圖註解、十字路口（平面穿越）、中央分隔島、圍牆／圍籬／綠籬、停車場車道出入口、高架匝道、無平面穿越長段、地下連通道細帶、出入口；B03 心中山基地範圍（非建物）。',
    '限制：樓地板為量體估算（非使用執照面積），代表人流潛力而非實測人數；門檻以下之小型建物合計人流未列；告示圖為示意圖，剪影位置誤差約 5–20 m。',
    '© OpenStreetMap contributors / ODbL｜政府資料開放授權條款第 1 版｜2026-10-11']

NOTE = ['表現：圖層依高程排列（B2 地下街・機捷月台 → B1 站體・通廊・連通道 → 地面路徑・出入口・建物・特性建築 → +1 天橋 → +2 高架）；地下層在路徑之下，路徑為黑 11%（色彩增值等效）；建物依樓高 5 級灰（0–5／6–11／12–19／20–29／30 層以上，越高越深；臺北三維模型 2017）；通行元素橘不透明；十字路口（平面穿越行穿線）不上圖，僅列於「通行元素」表。',
        '資料：建物＝02 線稿；平面穿越＝交工處行穿線（13）；地下街、捷運站、機捷站、台北車站地下通廊＝Metro Taipei「台北車站全區位置圖」站內告示描繪，',
        '  以 12 個路口控制點薄板樣條（TPS）對位（留一驗證中位誤差約 7 m，大道北側 3–6 m）；地下連通道、天橋＝OSM（2026-09-09），出入口＝OSM。特性建築＝17。',
        '未上圖（使用者指定）：街廓輪廓、地圖註解、十字路口（平面穿越）、中央分隔島、圍牆／圍籬／綠籬、停車場車道出入口、高架匝道、無平面穿越長段；U01 基地範圍（非建物）。',
        '限制：告示圖為示意圖（比例不均），剪影位置誤差約 5–20 m；連通道、天橋、出入口寬度為示意；地下街營業時間外之通行未納入。',
        '© OpenStreetMap contributors / ODbL｜政府資料開放授權條款第 1 版｜2026-10-11']

MAP_H = 270                       # 地圖高（mm）；上下各留約 124 mm 放區塊圖
if ZONE == 'Z8': MAP_H = 310      # Z8：主角南北跨距約 740 m（大巨蛋南緣—臺北機廠北緣），270 mm（675 m）放不下；上下各留約 104 mm
LEG_X0, LEG_X1 = 20, 150          # 左側圖例欄
MAP_L, MAP_R = 160, None          # 地圖左緣（圖例欄右側）；右緣＝圖框內 W−20

def map_frame(z):
    # 地圖框：回傳 (xc, xlim, ylim, y_ax, H_AX)；轉正座標。build 與 sheet_to_world（26 使用者 AI 修改回寫）共用
    d = S.PZ(z); T = d['T']
    pa_, pb_ = F.ends(z); xa_, xb_ = T(pa_).x, T(pb_).x; xc = (xa_ + xb_) / 2
    cont = T(unary_union([d['R']] + [g for g, p in CHAR if not p.get('site') and not p.get('adj')]))   # 基地範圍（不上圖）、鄰近運動場（Z4，單元外）不參與定框；Z1–Z3 不變
    cx_mm = W / 2                                            # 本段中點對齊圖紙中線
    if cx_mm - abs(xb_ - xa_) / 2 * m2mm < MAP_L + 8: cx_mm = (MAP_L + W - 20) / 2   # Z7 起：本段過長（置中於圖紙會切掉西端）→ 改置中於地圖區；Z1–Z6 不變
    wx = lambda xmm: xc + (xmm - cx_mm) / m2mm              # 圖紙 x（mm）→ 轉正後世界座標
    hm = MAP_H / m2mm / 2; yc_ = (cont.bounds[1] + cont.bounds[3]) / 2
    _ctx = [g for g, p in PA_ALL if p.get('ctx')]   # Z6 起：周邊捷運站體（單元外，使用者指定列入）——在不切掉主角之前提下納入圖框
    if _ctx:   # 只計圖框左右範圍內之部分；放不下時以主角上緣為準、圖框盡量下移
        cx_ = T(unary_union(_ctx)).intersection(box(wx(MAP_L), -1e5, wx(W - 20), 1e5))
        if not cx_.is_empty:
            cb = cx_.bounds; lo_, hi_ = min(cb[1], cont.bounds[1]) - 12, max(cb[3], cont.bounds[3]) + 12
            yc_ = min(max(yc_, hi_ - hm), lo_ + hm) if hi_ - lo_ <= 2 * hm else hi_ - hm
    TF = T(box(300935, 2770000, 307545, 2771910))
    from shapely.geometry import LineString as _LS
    tops, bots = [], []
    for xx in np.linspace(min(xa_, xb_), max(xa_, xb_), 12):
        seg = TF.intersection(_LS([(xx, -1e5), (xx, 1e5)]))
        if not seg.is_empty: tops.append(seg.bounds[3]); bots.append(seg.bounds[1])
    if tops:
        ytop, ybot = min(tops), max(bots)
        if 2 * hm > ytop - ybot: hm = (ytop - ybot) / 2
        yc_ = min(max(yc_, ybot + hm), ytop - hm)
    H_AX = 2 * hm * m2mm
    y_ax = 20 + ((Hh - 56) - 20 - H_AX) / 2
    return xc, (wx(MAP_L), wx(W - 20)), (yc_ - hm, yc_ + hm), y_ax, H_AX

def sheet_to_world(z, xm, ym):
    # 圖紙座標（mm；x 自左、y 自上，同 Illustrator）→ EPSG:3826
    from shapely import affinity
    from shapely.geometry import Point
    d = S.PZ(z); o = d['R'].centroid
    xc, xlim, ylim, y_ax, H_AX = map_frame(z)
    pr = Point(xlim[0] + (xm - MAP_L) / m2mm, ylim[0] + ((Hh - ym) - y_ax) / m2mm)
    return affinity.rotate(affinity.translate(pr, o.x, o.y), d['ang'], origin=(o.x, o.y))

OFFMAP = []
if ZONE == 'Z7':   # Z7：周邊捷運站體（忠孝東路，距大道 350–480 m）完全落在 1:2500 圖框外（北側餐飲建物已至圖框上緣）→ 不上圖、不列圖例，改列於「通行元素」表
    _xc_, _xl_, _yl_, _, _ = map_frame(ZONE); _T_ = S.PZ(ZONE)['T']; _V_ = box(_xl_[0], _yl_[0], _xl_[1], _yl_[1])
    OFFMAP = [p for g, p in PA if p.get('ctx') and _T_(g).intersection(_V_).area < 1]
    PA = [(g, p) for g, p in PA if not (p.get('ctx') and _T_(g).intersection(_V_).area < 1)]
    UG_NAMES = tuple(lv + '｜' + ('・'.join(ug_compress(dict.fromkeys(p['name'] for _, p in PA if level_of(p) == lv))) or '地下通行元素') for lv in ('B2', 'B1'))
    _has.update({k: any(level_of(p) == k for _, p in PA) for k in ('B2', 'B1')})
    LAYERS = [(k, {'B2': UG_NAMES[0], 'B1': UG_NAMES[1]}.get(k, n)) for k, n in LAYERS if _has.get(k, True)]

def build(pdf, png, only=None):
    # A1：上方標題＋區塊圖留白、中間地圖（本段置中於圖紙）、下方區塊圖留白；左側圖例欄
    # only：只輸出指定圖層鍵（AI 分層用）；None＝全部
    keys = [k for k, _ in LAYERS] if only is None else list(only)
    z = ZONE; d = S.PZ(z); zp = S.ZP[z]; T = d['T']
    fig = plt.figure(figsize=(W * MM, Hh * MM))
    xc, xlim, ylim, y_ax, H_AX = map_frame(z)
    mr = W - 20
    rect = [MAP_L / W, y_ax / Hh, (mr - MAP_L) / W, H_AX / Hh]
    view = box(xlim[0], ylim[0], xlim[1], ylim[1])
    wb = box(*SLAB.buffer(1100).bounds)
    for k_, _ in LAYERS:
        if k_ == 'TEXT' or k_ not in keys: continue
        ax = fig.add_axes(rect); ax.patch.set_alpha(0)
        draw_layer(ax, k_, T, wb, view)
        ax.set_xlim(*xlim); ax.set_ylim(*ylim); ax.axis('off')
    if 'TEXT' in keys:
        fig.add_artist(plt.Rectangle((10 / W, 10 / Hh), (W - 20) / W, (Hh - 20) / Hh, transform=fig.transFigure, fill=False, lw=.8))
        fig.text(28 / W, 1 - 30 / Hh, f"{z}　{zp['from']}—{zp['to']}｜影響南北通行之元素與特性建築", fontsize=20, va='top')
        legend_txt = ('酒紅＝主角三園區建物、淡酒紅＝主角戶外空間、橘＝通行元素（含行穿線）、灰＝市民高架匝道（深灰＝落地段）、灰階＝建物樓高（越高越深）、淡灰＝路徑' if PARKS8 else
                      '酒紅色階＝夜間餐飲建物（居酒屋／燒肉串燒最深 → 一般餐飲最淺）、橘＝通行元素（含地下停車場剪影）、灰階＝建物樓高（越高越深）、淡灰＝路徑' if ND is not None else
                      '酒紅＝主角（U02 方案、U03 現有建物、忠泰美術館街廓、懷生國小、北科大學生宿舍、八德市場）、淡酒紅＝主角開放地、橘＝通行元素（含行人穿越道）、灰階＝建物樓高（越高越深）、淡灰＝路徑' if PERM else
                      '酒紅色階＝商業空間、紫＝古蹟、淡綠＝空地（可用空地、步行區、廣場、綠地）、橘＝通行元素、灰階＝建物樓高（越高越深）、淡灰＝路徑' if CM is not None else
                      '酒紅＝主角（B01 規劃量體、華山1914）、黃＝住宅建物、綠＝運動場、淡綠＝純綠地、橘＝通行元素、灰階＝建物樓高（越高越深）、淡灰＝路徑（含公園步道）' if SH else
                      '酒紅＝主角規劃量體、藍＝商辦／政府機關、青綠＝日常生活店家、橘＝通行元素、灰階＝建物樓高（越高越深）、淡灰＝路徑' if MAIN is not None else
                      '酒紅＝源頭建築、淡酒紅＝目的地（臺北車站）、橘＝通行元素、灰階＝建物樓高（越高越深）、淡灰＝路徑' if SRC else
                      '橘＝通行元素、酒紅＝特性建築、灰階＝建物樓高（越高越深）、淡灰＝路徑')
        fig.text(28 / W, 1 - 41 / Hh, f"1:{SCALE:,}（A1）｜圖層依高程排列：B2 → B1 → 地面 → 天橋 → 高架｜{legend_txt}｜"
                 f"本段置中，界線外淡化｜表與說明見 A4", fontsize=8.5, va='top', color='#444')
        if PARKS8:
            fig.text(28 / W, 1 - 48 / Hh, f"要表達的問題：{z} 三個主角被市民高架分在兩側——松山文創園區、臺北大巨蛋在南，國家鐵道博物館（臺北機廠）在北；"
                     "鐵博南緣沿高架約 600 m 無平面穿越、天橋或地下道，正門朝北開於市民大道五段；南北兩側園區之間缺乏串連（匝道、行穿線上圖）", fontsize=8.5, va='top', color='#444')
        elif ND is not None:
            fig.text(28 / W, 1 - 48 / Hh, f"特性建築判斷標準：{z} 主角＝東區北緣宵夜／居酒屋餐飲帶——一樓有餐飲店家之建物依型態分色（居酒屋／燒肉串燒、酒吧／飲酒店、宵夜小吃、一般餐飲）；"
                     "OSM 判型態與營業時間、稅籍補數量；正常營業時間之晚餐也列入", fontsize=8.5, va='top', color='#444')
        elif PERM:
            fig.text(28 / W, 1 - 48 / Hh, f"特性建築判斷標準：{z} 主角＝長安段公辦都更（U02／U03）＋使用者指定之滲透場所：忠泰美術館街廓、瑠公圳公園、懷生國小、北科大學生宿舍、八德市場"
                     "（空地、學生、綠地——高架下方改動以加強地區之間的滲透性）", fontsize=8.5, va='top', color='#444')
        elif CM is not None:
            fig.text(28 / W, 1 - 48 / Hh, f"特性建築判斷標準：{z} 主題＝商業空間之密集——各種形式的商業空間（大型商場、商業大樓、騎樓店面、臨街店面）與空地（可用空地、步行區、廣場、綠地）；建國啤酒廠歸類古蹟",
                     fontsize=8.5, va='top', color='#444')
        elif SH:
            fig.text(28 / W, 1 - 48 / Hh, f"特性建築判斷標準：{z} 主軸＝運動生活空間——範圍內住宅（官方戶數依住宅樓地板分配）與運動場（範圍內之運動種類與面積），另標純綠地與公園步道",
                     fontsize=8.5, va='top', color='#444')
        elif MAIN is not None:
            fig.text(28 / W, 1 - 48 / Hh, f"特性建築判斷標準：{MAIN['name'].replace('（規劃中）', '')} 完成後新增之辦公與居住人口，在 {z} 範圍內會走去之目的地建物",
                     fontsize=8.5, va='top', color='#444')
        elif SRC:
            fig.text(28 / W, 1 - 48 / Hh, f"特性建築判斷標準：{z} 範圍內，流向台北車站之人群的源頭建築（總樓地板 ≥ 1 萬㎡；轉乘設施不設門檻）",
                     fontsize=8.5, va='top', color='#444')
        key_map_full(fig, z, KEY_X, None, KEY_W, bottom_mm=y_ax + KEY_DY)
        yb = legend_left(fig, LEG_X0 + 2, y_ax + H_AX, W, Hh, fs=9.0)
        yb = shop_block(fig, LEG_X0 + 2, yb - 10, W, Hh, fs=8.0, w_mm=LEG_X1 - LEG_X0 - 4)   # 結果（有官方統計之單元）
        if SH: sports_block(fig, LEG_X0 + 2, yb - 10, W, Hh, fs=8.0, w_mm=LEG_X1 - LEG_X0 - 4)   # 運動生活空間結果（Z4 起）
        if CM is not None: z5_block(fig, LEG_X0 + 2, yb - 10, W, Hh, fs=8.0, w_mm=LEG_X1 - LEG_X0 - 4)   # 商業空間之密集結果（Z5 起）
        if ND is not None: z7_block(fig, LEG_X0 + 2, yb - 10, W, Hh, fs=8.0, w_mm=LEG_X1 - LEG_X0 - 4)   # 夜間餐飲結果（Z7 起）
        S.north(fig, NORTH_X, y_ax + NORTH_DY, d['ang'], size=8)
        F.scalebar(fig, LEG_X0 + 2, y_ax + SCALE_DY)
    if pdf is not None: pdf.savefig(fig, transparent=only is not None)
    if png: fig.savefig(png, dpi=110)
    plt.close(fig)

# 圖例欄下段排版（依使用者 2026-10-12 於 Z1 AI 之排版，2026-10-13 統一套用 Z1–Z8）：皆以地圖下緣 y_ax 為基準（mm，自下）
#   索引圖縮至圖例欄寬（x 22.2–157.8），下緣對齊地圖下緣；比例尺移至索引圖上方；指北置於比例尺右側
KEY_X, KEY_W, KEY_DY = 22.2, 135.6, -1.8
SCALE_DY = 41.0
NORTH_X, NORTH_DY = 134.2, 44.5
def key_map_full(fig, z, x_mm, top_mm, w_mm, bottom_mm=None):
    # 索引圖：範圍取 Z1–Z8 全部單元＋標籤，避免上下被裁切（原 05 key_map 固定 32 mm 高，Z1 上緣被切）
    regs = [S.PZ(z2)['R'] for z2 in S.ZONES_USE]
    allr = unary_union(regs); b0 = allr.bounds
    labs = [(z2, r.centroid.x, S.center.interpolate(S.center.project(r.centroid)).y - 230) for z2, r in zip(S.ZONES_USE, regs)]
    x0, x1 = b0[0] - 60, b0[2] + 60
    y0, y1 = min(b0[1], min(l[2] for l in labs) - 120), b0[3] + 60
    h_mm = w_mm * (y1 - y0) / (x1 - x0)
    if bottom_mm is not None: top_mm = bottom_mm + h_mm
    ka = fig.add_axes([x_mm / W, (top_mm - h_mm) / Hh, w_mm / W, h_mm / Hh])
    ka.set_xlim(x0, x1); ka.set_ylim(y0, y1); ka.axis('off')
    vb = box(x0, y0, x1, y1)
    ka.add_collection(LineCollection(S.lines(S.road.boundary.intersection(vb)), colors='#c4c4c4', linewidths=.12))
    for z2, r in zip(S.ZONES_USE, regs):
        ka.add_collection(PathCollection([S.poly_path(r)], facecolors=S.ZONE_C if z2 == z else '#BFDDF0', edgecolors='none', zorder=2))
    for z2, cx, cy in labs:
        ka.text(cx, cy, z2, fontsize=6.5 if z2 == z else 5.5, ha='center', va='top', color=S.ZONE_C,
                fontweight='bold' if z2 == z else 'normal', path_effects=S.halo)
    ka.add_collection(LineCollection(S.lines(S.elev.intersection(vb)), colors='#111', linewidths=.5, zorder=3))
    return h_mm

def export_ai_layers(out_dir):
    # 每圖層一頁 A1 PDF（同版面、透明底），供 24_assemble_ai.jsx 於 Illustrator 內依序置入成分層 AI
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in out_dir.glob('*.pdf'): f.unlink()
    files = []
    for i, (k_, name) in enumerate(LAYERS):
        fn = out_dir / f'{i:02d}_{k_}.pdf'
        with PdfPages(fn) as pdf: build(pdf, None, only=[k_])
        files.append((name, str(fn)))
    json.dump(files, open(out_dir / 'layers.json', 'w'), ensure_ascii=False, indent=1)
    return files

def wrap_w(t, maxw):
    # 依顯示寬度斷行；英數連續字串（詞）不拆開
    import re
    toks = re.findall(r'[A-Za-z0-9.=／/–\-]+|\s+|.', t)
    out, cur, w = [], '', 0.0
    for tk in toks:
        tw = sum(.55 if ord(c) < 0x2E80 else 1.0 for c in tk)
        if w + tw > maxw and cur.strip():
            out.append(cur.rstrip()); cur, w = ('' if tk.isspace() else tk), (0 if tk.isspace() else tw)
        else: cur += tk; w += tw
    if cur.strip(): out.append(cur.rstrip())
    return out or ['']

def build_a4(pdf, png):
    # A4 直式：圖例、通行元素表、特性建築表、說明（自 A1 下方資訊帶移出）
    fw, fh = 210, 297; z = ZONE; zp = S.ZP[z]
    fig = plt.figure(figsize=(fw * MM, fh * MM))
    fig.add_artist(plt.Rectangle((8 / fw, 8 / fh), (fw - 16) / fw, (fh - 16) / fh, transform=fig.transFigure, fill=False, lw=.6))
    fig.text(16 / fw, 1 - 18 / fh, f"{z}　{zp['from']}—{zp['to']}｜影響南北通行之元素與特性建築", fontsize=12.5, va='top')
    fig.text(16 / fw, 1 - 25 / fh, f"圖例與說明（配合 A1 圖面，1:{SCALE:,}）", fontsize=8, va='top', color='#555')
    y = fh - 36
    fig.text(16 / fw, y / fh, '圖例', fontsize=10, fontweight='bold', va='top', color='#111')
    y = legend_left(fig, 16, y + 1, fw, fh, fs=7.0, col2_x=108 if SRC else None) - 8
    fig.text(16 / fw, y / fh, '通行元素', fontsize=10, fontweight='bold', va='top', color=RED)
    rows, col, bd = factor_rows()
    import textwrap
    wrows, wcol, wbd = [], [], []
    for r_, c_, b_ in zip(rows, col, bd):
        lines_ = wrap_w(r_[1], 55)
        for i, ln in enumerate(lines_):
            wrows.append([r_[0] if i == 0 else '', ln]); wcol.append(c_); wbd.append(b_ and i == 0)
    y = table(fig, 16, y - 7, wrows, [36, 142], head=['項目', '說明'], colors=wcol, bold=wbd, fs=6.8, lh=4.3, fw=fw, fh=fh) - 6
    fig.text(16 / fw, y / fh, ('主角：南北兩側三園區（建物與戶外空間）' if PARKS8 else '夜間餐飲：型態與營業時段' if ND is not None else '主角：公辦都更與滲透場所（空地・學生・綠地）' if PERM else '商業空間、古蹟與空地' if CM is not None else '主角、住宅與運動場' if SH else '主角與目的地建物' if MAIN is not None else '特性建築：源頭建築（酒紅）與目的地（淡酒紅）' if SRC else '特性建築（酒紅剪影）'),
             fontsize=10, fontweight='bold', va='top', color=MAG)
    crow, ccol = src_rows()
    crow += [([p['name'].split('（')[0], '基地範圍（主角之一；非建物，不上圖）｜' + p['group']] if SRC and p.get('site') else
              [p['name'] + ('（不上圖）' if p.get('site') else ''), {'A': '主角構成', 'B': '公辦都更基地', 'C': '界面大型建物'}[p['tier']] + '｜' + p['group']])
             for _, p in CHAR if p['tier'] in (() if PERM else ('A', 'B', 'C'))]
    ccol = ccol + [[MAG, '#555']] * (len(crow) - len(ccol))
    if SRC:   # 長說明斷行
        w_ = []
        for r_, c_ in zip(crow, ccol):
            for i, ln in enumerate(wrap_w(r_[1], 50)): w_.append(([r_[0] if i == 0 else '', ln], c_))
        crow, ccol = [a for a, _ in w_], [b for _, b in w_]
    drows, dcol = dest_rows()
    for (k, t), c in zip(drows, dcol):
        for i, ln in enumerate(wrap_w(t, 52)):
            crow.append([('目的地：' + k) if i == 0 else '', ln]); ccol.append(c)
    zrows, zcol = z4_rows()                                    # 運動生活空間（Z4 起）
    _r6, _c6 = z6_rows(); zrows, zcol = _r6 + zrows, _c6 + zcol   # 滲透場所（Z6 起）
    _r5, _c5 = z5_rows(); zrows, zcol = zrows + _r5, zcol + _c5   # 商業空間之密集（Z5 起）
    _r7, _c7 = z7_rows(); zrows, zcol = zrows + _r7, zcol + _c7   # 夜間餐飲（Z7 起）
    for (k, t), c in zip(zrows, zcol):
        for i, ln in enumerate(wrap_w(t, 52)):
            crow.append([k if i == 0 else '', ln]); ccol.append(c)
    wide = bool(drows or SRC or SH or CM is not None or PERM or ND is not None)
    crow_p2, ccol_p2 = [], []
    if CM is not None or ND is not None:   # Z5、Z7：表列放不下時，其餘列移至第 2 頁（說明之前）
        nfit = int((y - 7 - 4.3 - 14) / 4.3)
        if len(crow) > nfit: crow, crow_p2, ccol, ccol_p2 = crow[:nfit], crow[nfit:], ccol[:nfit], ccol[nfit:]
    y = table(fig, 16, y - 7, crow, [42 if wide else 92, 136 if wide else 86], head=['項目', '說明'] if (drows or SH or CM is not None or PERM or ND is not None) else ['名稱', '類別'],
              colors=ccol, fs=6.8, lh=4.3, fw=fw, fh=fh) - 6
    if shop_stats(): y = shop_block(fig, 16, y, fw, fh, fs=7.2, w_mm=150) - 6
    sb_on_p2 = bool(SH) and y - 120 < 12           # 運動生活結果區塊放不下：移至第 2 頁（與說明同頁）
    if SH and not sb_on_p2: y = sports_block(fig, 16, y, fw, fh, fs=7.2, w_mm=150) - 6
    if ND is not None and not crow_p2: y = z7_block(fig, 16, y, fw, fh, fs=7.2, w_mm=150) - 6   # Z7：結果區塊（表列未溢頁時）
    note = []
    for t in NOTE_Z.get(ZONE, NOTE):
        t = t.strip()
        if note and not t.startswith(('表現', '資料', '未上圖', '限制', '©', '判斷標準')): note[-1] += t; continue   # 接續行併入上一段再重新斷行
        note.append(t)
    paras = note; nfs = 6.0; note = [ln for t in paras for ln in wrap_w(t, 70)]
    if (SRC or SH or CM is not None or PERM or ND is not None) and (y - 7) - len(note) * nfs * 1.55 * 25.4 / 72 < 12:      # 放不下：先縮字（5.5 pt），仍不足則移至第 2 頁（Z2、Z4 起）
        nfs = 5.5; note = [ln for t in paras for ln in wrap_w(t, 77)]
    if ((y - 7) - len(note) * nfs * 1.55 * 25.4 / 72 >= 12 or not (SRC or SH or CM is not None or PERM or ND is not None)) and not (SH and sb_on_p2) and not crow_p2:
        fig.text(16 / fw, y / fh, '說明', fontsize=10, fontweight='bold', va='top', color='#111')
    else:
        nfs = 6.0; note = [ln for t in paras for ln in wrap_w(t, 70)]
        pdf.savefig(fig); fig.savefig(png, dpi=150); plt.close(fig)
        fig = plt.figure(figsize=(fw * MM, fh * MM))
        fig.add_artist(plt.Rectangle((8 / fw, 8 / fh), (fw - 16) / fw, (fh - 16) / fh, transform=fig.transFigure, fill=False, lw=.6))
        fig.text(16 / fw, 1 - 18 / fh, f"{z}　{zp['from']}—{zp['to']}｜影響南北通行之元素與特性建築（續）", fontsize=12.5, va='top')
        y = fh - 30
        if SH and sb_on_p2: y = sports_block(fig, 16, y, fw, fh, fs=7.2, w_mm=150) - 8
        if crow_p2:
            fig.text(16 / fw, y / fh, '夜間餐飲（續）' if ND is not None else '商業空間、古蹟與空地（續）', fontsize=10, fontweight='bold', va='top', color=MAG)
            y = table(fig, 16, y - 7, crow_p2, [42, 136], head=['項目', '說明'], colors=ccol_p2, fs=6.8, lh=4.3, fw=fw, fh=fh) - 8
        fig.text(16 / fw, y / fh, '說明', fontsize=10, fontweight='bold', va='top', color='#111')
        fig.text(16 / fw, (y - 7) / fh, '\n'.join(note), fontsize=6.0, va='top', color='#444', linespacing=1.55)
        pdf.savefig(fig); fig.savefig(str(png).replace('_預覽.png', '_預覽_2.png'), dpi=150); plt.close(fig)
        return
    fig.text(16 / fw, (y - 7) / fh, '\n'.join(note), fontsize=nfs, va='top', color='#444', linespacing=1.55)
    pdf.savefig(fig); fig.savefig(png, dpi=150); plt.close(fig)

if __name__ == '__main__':
    out = H / '主題圖_南北通行因素與特性建築'; out.mkdir(exist_ok=True)
    zp = S.ZP[ZONE]; stem = f"{ZONE}_{S.short(zp['from'])}-{S.short(zp['to'])}_南北通行因素與特性建築_A1_1-{SCALE}"
    with PdfPages(out / f'{stem}.pdf') as pdf:
        build(pdf, out / f'{stem}_預覽.png')
    export_ai_layers(out / '_ai_layers' / ZONE)
    stem4 = f"{ZONE}_{S.short(zp['from'])}-{S.short(zp['to'])}_南北通行因素與特性建築_圖例與說明_A4"
    with PdfPages(out / f'{stem4}.pdf') as pdf:
        build_a4(pdf, out / f'{stem4}_預覽.png')
    print(stem); print(stem4)
