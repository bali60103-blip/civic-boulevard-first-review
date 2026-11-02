# 路徑內碎塊（分隔島狀、切割殘片）檢核（2026-10-11 使用者指示：寬路徑中常出現類似分隔島或切割後碎塊，以空照圖對照修正）
#   候選＝圖面視窗內、路徑（整合後道路面 ∪ 新工處人行道 − 建物）以外、被路徑包圍之小塊（≤ 3,000 m²、建物覆蓋 < 20%）
#   以臺北市 2025 正射影像（02_南京至仁愛擴幅/imagery X11–X33，0.6 m/px）量測各塊內植栽（綠）與鋪面（灰）比例，
#   並輸出逐塊影像比對圖供人工判讀；判讀結果寫入 data/{Z}_road_islands_EPSG3826.geojson（decision：fill＝填為路徑、keep＝保留）
import json, sys, importlib.util
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import shape, mapping, box, Polygon
from shapely.ops import unary_union
from shapely import affinity

H = Path(__file__).resolve().parents[1]
ZONE = sys.argv[1] if len(sys.argv) > 1 else 'Z1'
MODE = sys.argv[2] if len(sys.argv) > 2 else 'scan'          # scan：列候選＋比對圖；apply：依 DECISIONS 寫出
_argv = sys.argv; sys.argv = [_argv[0], ZONE]
spec = importlib.util.spec_from_file_location('ns', H / 'scripts/20_ns_factors_sheet.py')
N = importlib.util.module_from_spec(spec); spec.loader.exec_module(N)
sys.argv = _argv
S, F = N.S, N.F
IMG = N.H.parents[0] / '02_南京至仁愛擴幅_20261005'
MAN = json.load(open(IMG / 'imagery_manifest.json'))['images']
OUT = H / f'data/{ZONE}_road_islands_EPSG3826.geojson'

# 圖面視窗（與 20 build 相同之計算）→ 世界座標
def view_world():
    d = S.PZ(ZONE)
    xc, xlim, ylim, y_ax, H_AX = N.map_frame(ZONE)          # 與 20 共用地圖框（含上下界夾限）
    vb = box(xlim[0], ylim[0], xlim[1], ylim[1])
    o = d['R'].centroid
    return affinity.rotate(affinity.translate(vb, o.x, o.y), d['ang'], origin=(o.x, o.y))
VIEW = view_world()
WB = box(*VIEW.buffer(30).bounds)
paths = N.paths_geom(WB, fill=False)     # 未套用修正之原始路徑
bld = S.bld.intersection(WB.buffer(10))
holes = WB.difference(paths)
cands = []
for p in getattr(holes, 'geoms', [holes]):
    if p.geom_type != 'Polygon' or p.area < 2 or p.area > 3000: continue
    if not p.intersects(VIEW): continue
    if p.intersection(bld).area > .2 * p.area: continue
    if p.boundary.intersection(WB.exterior.buffer(.5)).length > 1: continue      # 視窗邊緣切到者略過
    if p.exterior.buffer(.6).intersection(paths).area < .5 * p.exterior.length * 1.2 * .85: continue   # 外圍 85% 以上須貼路徑
    cands.append(p)

def tiles_for(b):
    return [m for m in MAN if not (m['bbox'][2] < b[0] or m['bbox'][0] > b[2] or m['bbox'][3] < b[1] or m['bbox'][1] > b[3])]
_cache = {}
def chip(b, px=0.3):
    # 回傳 b=(x0,y0,x1,y1) 範圍之影像（每像素 px m）
    x0, y0, x1, y1 = b; W_ = int((x1 - x0) / px); H_ = int((y1 - y0) / px)
    out = Image.new('RGB', (W_, H_), 'white')
    for m in tiles_for(b):
        if m['file'] not in _cache: _cache[m['file']] = Image.open(IMG / 'imagery' / m['file']).convert('RGB')
        im = _cache[m['file']]; bx = m['bbox']; sx = im.width / (bx[2] - bx[0]); sy = im.height / (bx[3] - bx[1])
        cx0, cx1 = max(x0, bx[0]), min(x1, bx[2]); cy0, cy1 = max(y0, bx[1]), min(y1, bx[3])
        if cx0 >= cx1 or cy0 >= cy1: continue
        c = im.crop((int((cx0 - bx[0]) * sx), int((bx[3] - cy1) * sy), int((cx1 - bx[0]) * sx), int((bx[3] - cy0) * sy)))
        c = c.resize((int((cx1 - cx0) / px), int((cy1 - cy0) / px)))
        out.paste(c, (int((cx0 - x0) / px), int((y1 - cy1) / px)))
    return out
def stats(p):
    b = p.bounds; im = np.asarray(chip(b, .3)).astype(float)
    if im.size == 0: return 0, 0
    Hh_, Ww_ = im.shape[:2]
    mask = Image.new('L', (Ww_, Hh_), 0); dr = ImageDraw.Draw(mask)
    to = lambda c: ((c[0] - b[0]) / .3, (b[3] - c[1]) / .3)
    dr.polygon([to(c) for c in p.exterior.coords], fill=255)
    for r in p.interiors: dr.polygon([to(c) for c in r.coords], fill=0)
    m = np.asarray(mask) > 0
    if m.sum() < 3: return 0, 0
    R, G, B = im[..., 0][m], im[..., 1][m], im[..., 2][m]
    mx = np.maximum(np.maximum(R, G), B); mn = np.minimum(np.minimum(R, G), B)
    green = ((G > R + 6) & (G > B + 2)).mean()
    gray = (((mx - mn) < 22) & (mx > 60)).mean()
    return round(float(green), 2), round(float(gray), 2)

rows = []
for i, p in enumerate(sorted(cands, key=lambda q: (q.centroid.x))):
    w = 2 * p.area / p.length
    g, a = stats(p)
    rows.append({'id': i + 1, 'geom': p, 'area': round(p.area, 1), 'width': round(w, 2), 'green': g, 'gray': a})

if MODE == 'scan':
    SP = Path(sys.argv[3]) if len(sys.argv) > 3 else H / 'data'
    font = ImageFont.truetype('/System/Library/Fonts/Hiragino Sans GB.ttc', 15)
    tiles = []
    for r in rows:
        p = r['geom']; c = p.centroid; half = max(18, max(p.bounds[2] - p.bounds[0], p.bounds[3] - p.bounds[1]) * .8)
        b = (c.x - half, c.y - half, c.x + half, c.y + half)
        im = chip(b, half * 2 / 260).resize((260, 260)); dr = ImageDraw.Draw(im)
        to = lambda q: ((q[0] - b[0]) / (2 * half) * 260, (b[3] - q[1]) / (2 * half) * 260)
        dr.line([to(q) for q in p.exterior.coords], fill=(255, 0, 255), width=2)
        for pg in S.polys(paths.intersection(box(*b))):
            dr.line([to(q) for q in pg.exterior.coords], fill=(0, 220, 255), width=1)
        dr.rectangle([0, 0, 260, 20], fill='white')
        dr.text((3, 2), f"#{r['id']} {r['area']:.0f}m² w{r['width']:.1f} g{r['green']:.2f} a{r['gray']:.2f}", fill='black', font=font)
        tiles.append(im)
    cols = 6
    for k in range(0, len(tiles), 24):
        part = tiles[k:k + 24]; n = (len(part) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * 264, n * 264), 'white')
        for j, t in enumerate(part): sheet.paste(t, ((j % cols) * 264, (j // cols) * 264))
        sheet.save(SP / f'islands_{k // 24 + 1}.jpg', quality=85)
    json.dump([{k: v for k, v in r.items() if k != 'geom'} for r in rows], open(SP / 'islands.json', 'w'), indent=0)
    print('candidates', len(rows), 'sheets', (len(tiles) + 23) // 24)

# ---------- 判讀結果（依單元；編號依幾何由西向東，基圖變動須重新 scan）----------
DECISIONS = {}
# Z1（2026-10-11，依 Ortho_2025 逐塊比對；#7、16、19、20、27、30、33、57、64 為使用者於 AI 已手動補齊者）
DECISIONS['Z1'] = dict(FILL={2, 3, 4, 7, 9, 11, 13, 14, 16, 19, 20, 27, 29, 30, 31, 33, 35, 37, 39, 43, 45, 46, 47, 49, 50, 55, 56, 57, 60, 64, 65, 66, 67, 68,
        69, 70, 71, 72, 73, 74, 76, 77, 78, 79, 80, 81, 82, 86, 87, 89, 90, 91, 92, 94, 95, 96, 97, 98, 99, 101, 105, 108, 109, 110, 112},
    UNDER_DECK_KEEP={28, 85, 113},      # 高架橋面下，空照僅見橋面，無法判讀 → 依分隔島保留
    USER_FILLED={7, 16, 19, 20, 27, 30, 33, 57, 64},
    # 使用者於 AI 補齊之碎塊（2026-10-11 22:37 存檔；圖紙座標 mm：x 自左、y 自上）——中華路南段中央細長島
    USER_SHEET_PTS=[(380.8, 395.9, '使用者於 AI 補齊（中華路中央細長島，2026-10-11 22:37）')])
# Z3（2026-10-11，依 Ortho_2025 逐塊比對；高架橋面下者空照只見橋面與橋上車輛，依 Z1 原則保留為橋下分隔島）
DECISIONS['Z3'] = dict(FILL={1, 2, 3, 4, 5, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 21, 24, 25, 26, 28, 30, 32, 33, 34, 35, 36, 38, 40, 45,
                             50, 53, 55, 62, 64, 66, 71, 77, 78, 79, 83, 85, 87, 89},
    UNDER_DECK_KEEP={6, 20, 47, 49, 51, 57, 59, 61, 68},          # 市民高架橋面下（橋面覆蓋 100%）
    KEEP_WHY={**{i: '新生高架（含匝道）橋面下，空照僅見橋面，依分隔島保留' for i in (69, 70, 82, 84, 86)},
              22: '公車專用道候車島（空照可見候車月台）', 39: '植栽分隔島（林蔭分隔帶）',
              72: '停車場內（非路徑）', 75: '街廓後側空地與停車（非路徑）'})
# Z2（2026-10-11）：103 塊中 95 塊與 Z1／Z3 已判讀之碎塊幾何相同（IoU＝1），沿用其判讀與原因；其餘 8 塊依 Ortho_2025 判讀
#   （#83、85 中山北路林蔭分隔島保留；#101 植栽保留；#89、98 細長縫，#92 路邊停車帶，#100、102 行穿線旁鋪面補齊）
DECISIONS['Z2'] = dict(FILL={4, 6, 7, 8, 10, 11, 16, 17, 18, 21, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 37, 38, 39, 40, 41, 42, 43, 47, 48, 50, 51, 52, 54, 56, 58, 59, 60, 61, 62, 64, 68, 71, 72, 73, 75, 76, 79, 81, 89, 91, 92, 94, 96, 98, 100, 102},
    USER_FILLED={18, 25},      # 對應 Z1 使用者於 AI 補齊者
    KEEP_WHY={1: '空照可見植栽（植栽 46%）：植栽分隔島／綠地',
              2: '高架橋下分隔島（橋墩所在）',
              3: '空照可見凸起分隔島／中央島或候車島',
              5: '空照可見植栽（植栽 65%）：植栽分隔島／綠地',
              9: '停車場、空地或街廓內開放空間（非路徑）',
              12: '空照可見植栽（植栽 51%）：植栽分隔島／綠地',
              13: '高架橋下分隔島（橋墩所在）',
              14: '高架橋下分隔島（橋墩所在）',
              15: '空照可見植栽（植栽 34%）：植栽分隔島／綠地',
              19: '停車場、空地或街廓內開放空間（非路徑）',
              20: '空照可見植栽（植栽 30%）：植栽分隔島／綠地',
              22: '空照可見植栽（植栽 37%）：植栽分隔島／綠地',
              23: '空照可見植栽（植栽 62%）：植栽分隔島／綠地',
              24: '空照可見植栽（植栽 33%）：植栽分隔島／綠地',
              36: '高架橋下分隔島（橋墩所在）',
              44: '高架橋下分隔島（橋墩所在）',
              45: '停車場、空地或街廓內開放空間（非路徑）',
              46: '高架橋面下，空照僅見橋面，依分隔島保留',
              49: '高架橋下分隔島（橋墩所在）',
              53: '空照可見植栽（植栽 32%）：植栽分隔島／綠地',
              55: '空照可見植栽（植栽 31%）：植栽分隔島／綠地',
              57: '空照可見植栽（植栽 30%）：植栽分隔島／綠地',
              63: '空照可見凸起分隔島／中央島或候車島',
              65: '空照可見凸起分隔島／中央島或候車島',
              66: '空照可見植栽（植栽 36%）：植栽分隔島／綠地',
              67: '高架橋下分隔島（橋墩所在）',
              69: '空照可見植栽（植栽 49%）：植栽分隔島／綠地',
              70: '停車場、空地或街廓內開放空間（非路徑）',
              74: '停車場、空地或街廓內開放空間（非路徑）',
              77: '高架橋面下，空照僅見橋面，依分隔島保留',
              78: '空照可見植栽（植栽 42%）：植栽分隔島／綠地',
              80: '空照可見植栽（植栽 51%）：植栽分隔島／綠地',
              82: '高架橋下分隔島（橋墩所在）',
              83: '中山北路林蔭分隔島（快慢車道分隔，空照可見行道樹冠）',
              84: '高架橋面下，空照僅見橋面，依分隔島保留',
              85: '中山北路林蔭分隔島（快慢車道分隔，空照可見行道樹冠）',
              86: '空照可見植栽（植栽 47%）：植栽分隔島／綠地',
              87: '高架橋面下，空照僅見橋面，依分隔島保留',
              88: '高架橋下分隔島（橋墩所在）',
              90: '高架橋面下，空照僅見橋面，依分隔島保留',
              93: '空照可見植栽（植栽 68%）：植栽分隔島／綠地',
              95: '高架橋下分隔島（橋墩所在）',
              97: '空照可見植栽（植栽 60%）：植栽分隔島／綠地',
              99: '高架橋面下，空照僅見橋面，依分隔島保留',
              103: '空照可見植栽（植栽 83%）：植栽分隔島／綠地'})
# Z4（2026-10-12）：84 塊中 41 塊與 Z3／Z2 已判讀者幾何相同（IoU > 0.98），沿用其判讀與原因；其餘 43 塊皆位於 Z4 範圍外之前後段與南緣
#   （金山南路、新生、松江、建國一帶），依 Ortho_2025 判讀：細縫、路口三角、行穿線鋪面、道路邊帶補齊；高架橋面下、公車專用道候車島、植栽保留
_DECK = '高架橋面下，空照僅見橋面，依分隔島保留'; _PIER = '高架橋下分隔島（橋墩所在）'; _BUS = '公車專用道候車島／中央分隔帶（空照可見）'
DECISIONS['Z4'] = dict(
    FILL={3, 10, 11, 13, 15, 17, 19, 21, 28, 31, 34, 41, 44, 46, 48,                      # 沿用 Z3／Z2
          22, 29, 32, 42, 49, 53, 55, 57, 58, 62, 66, 67, 70, 71, 72, 75, 77, 83},          # 新判讀
    KEEP_WHY={1: '停車場、空地或街廓內開放空間（非路徑）', 2: _DECK, 4: '空照可見植栽（植栽 51%）：植栽分隔島／綠地', 5: _PIER, 6: _DECK, 7: _DECK, 8: _PIER, 9: _DECK,
              12: '空照可見植栽（植栽 68%）：植栽分隔島／綠地', 14: _PIER, 16: '空照可見植栽（植栽 60%）：植栽分隔島／綠地', 18: _DECK,
              20: '空照可見植栽（植栽 47%）：植栽分隔島／綠地', 23: '停車場內（非路徑）', 24: '停車場、空地或街廓內開放空間（非路徑）',
              25: '空照可見植栽（植栽 83%）：植栽分隔島／綠地', 26: '街廓後側空地與停車（非路徑）', 27: '空照可見植栽（植栽 78%）：植栽分隔島／綠地',
              36: _PIER, 37: '空照可見植栽（植栽 52%）：植栽分隔島／綠地', 47: '空照可見植栽（植栽 34%）：植栽分隔島／綠地', 50: _PIER, 51: _PIER,
              **{i: '新生高架（含匝道）橋面下，空照僅見橋面，依分隔島保留' for i in (35, 38, 40, 43, 45)},
              **{i: _DECK for i in (59, 60, 73, 74, 76, 79, 81)},
              **{i: '建國高架（建國快速道路）橋面下，空照僅見橋面，依分隔島保留' for i in (80, 82)},
              **{i: _BUS for i in (63, 64, 65, 68, 69)},
              30: '建物屋頂（線稿建物輪廓未涵蓋之屋頂邊緣），非路徑', 33: '樹冠遮蔽之凸起三角島（金山南路口）', 52: '街角廣場／空地（新生北路口，非路徑）',
              54: '公車專用道旁行人庇護島', 78: '建國南路沿線分隔帶（判讀不確定，依分隔島保留）'})
# Z5（2026-10-12）：86 塊中 56 塊與 Z4／Z3／Z2 已判讀者幾何相同（IoU > 0.98），沿用其判讀與原因；其餘 30 塊（#55–60、63–86）位於 Z5 東段與建國高架以東之前後段，
#   依 Ortho_2025 判讀：路口三角、車道內碎塊、細縫、線稿缺之巷道補齊；建國高架與市民高架橋面下、植栽帶、街廓內停車場保留
_YB = '建國高架（建國快速道路）橋面下，空照僅見橋面，依分隔島保留'
DECISIONS['Z5'] = dict(
    FILL={1, 3, 4, 10, 11, 12, 13, 15, 20, 22, 24, 26, 31, 33, 37, 41, 42, 44, 45, 49, 61} | {55, 56, 60, 65, 70, 76, 77, 80, 85, 86},   # 沿用＋新判讀（#65、76、80 為線稿缺之巷道）
    KEEP_WHY={2: '空照可見植栽（植栽 47%）：植栽分隔島／綠地',
              5: '停車場內（非路徑）',
              6: '停車場、空地或街廓內開放空間（非路徑）',
              7: '空照可見植栽（植栽 83%）：植栽分隔島／綠地',
              8: '街廓後側空地與停車（非路徑）',
              9: '空照可見植栽（植栽 78%）：植栽分隔島／綠地',
              14: '樹冠遮蔽之凸起三角島（金山南路口）',
              16: '高架橋下分隔島（橋墩所在）',
              17: '空照可見植栽（植栽 52%）：植栽分隔島／綠地',
              18: '新生高架（含匝道）橋面下，空照僅見橋面，依分隔島保留',
              19: '新生高架（含匝道）橋面下，空照僅見橋面，依分隔島保留',
              21: '新生高架（含匝道）橋面下，空照僅見橋面，依分隔島保留',
              23: '新生高架（含匝道）橋面下，空照僅見橋面，依分隔島保留',
              25: '空照可見植栽（植栽 34%）：植栽分隔島／綠地',
              27: '高架橋下分隔島（橋墩所在）',
              28: '高架橋下分隔島（橋墩所在）',
              29: '街角廣場／空地（新生北路口，非路徑）',
              30: '公車專用道旁行人庇護島',
              32: '空照可見植栽（植栽 31%）：植栽分隔島／綠地',
              34: '高架橋面下，空照僅見橋面，依分隔島保留',
              35: '高架橋面下，空照僅見橋面，依分隔島保留',
              36: '空照可見凸起分隔島／中央島或候車島',
              38: '公車專用道候車島／中央分隔帶（空照可見）',
              39: '公車專用道候車島／中央分隔帶（空照可見）',
              40: '公車專用道候車島／中央分隔帶（空照可見）',
              43: '公車專用道候車島／中央分隔帶（空照可見）',
              46: '高架橋面下，空照僅見橋面，依分隔島保留',
              47: '高架橋面下，空照僅見橋面，依分隔島保留',
              48: '高架橋面下，空照僅見橋面，依分隔島保留',
              50: '建國南路沿線分隔帶（判讀不確定，依分隔島保留）',
              51: '高架橋面下，空照僅見橋面，依分隔島保留',
              52: '建國高架（建國快速道路）橋面下，空照僅見橋面，依分隔島保留',
              53: '高架橋面下，空照僅見橋面，依分隔島保留',
              54: '建國高架（建國快速道路）橋面下，空照僅見橋面，依分隔島保留',
              62: '空照可見植栽（植栽 34%）：植栽分隔島／綠地',
              57: _YB, 58: _YB, **{i: _DECK for i in (63, 78, 81, 83, 84)},
              59: '空照可見植栽（植栽 71%）：植栽分隔島／綠地', 64: '空照可見植栽（植栽 64%）：樹林綠地（非路徑）',
              **{i: '建物旁植栽帶（空照可見植栽），非路徑' for i in (66, 67, 68, 69)},
              **{i: '停車場內（非路徑）' for i in (71, 73, 74, 82)}, 72: '停車場、空地或街廓內開放空間（非路徑）',
              75: '街廓內建物與中庭（非路徑）', 79: '空照可見植栽（植栽 78%）：植栽分隔島／綠地'})
# Z6（2026-10-12）：76 塊中 44 塊與 Z4／Z5 已判讀者幾何相同（IoU > 0.98），沿用其判讀與原因；其餘 32 塊（#1、21、43、45–47、50、51、53–76）
#   多位於安東街以東（Z7 前段）與忠孝東路，依 Ortho_2025 判讀：路口三角、車道內細縫、行穿線旁鋪面、忠孝東路細長縫補齊；
#   市民高架橋面下與橋緣陰影、植栽帶、街廓內廣場、線稿缺建物之街廓保留
DECISIONS['Z6'] = dict(
    FILL={2, 3, 36, 37, 6, 8, 40, 14, 15, 49, 19, 20, 52, 25, 30} | {1, 66, 69, 74, 43, 75, 45, 47, 50, 21, 53, 54, 55, 56, 59, 62, 63},   # 沿用＋新判讀
    KEEP_WHY={4: '高架橋面下，空照僅見橋面，依分隔島保留',
              5: '高架橋面下，空照僅見橋面，依分隔島保留',
              7: '高架橋面下，空照僅見橋面，依分隔島保留',
              9: '建國南路沿線分隔帶（判讀不確定，依分隔島保留）',
              10: '高架橋面下，空照僅見橋面，依分隔島保留',
              11: '建國高架（建國快速道路）橋面下，空照僅見橋面，依分隔島保留',
              12: '高架橋面下，空照僅見橋面，依分隔島保留',
              13: '建國高架（建國快速道路）橋面下，空照僅見橋面，依分隔島保留',
              16: '建國高架（建國快速道路）橋面下，空照僅見橋面，依分隔島保留',
              17: '建國高架（建國快速道路）橋面下，空照僅見橋面，依分隔島保留',
              18: '空照可見植栽（植栽 71%）：植栽分隔島／綠地',
              22: '空照可見植栽（植栽 34%）：植栽分隔島／綠地',
              23: '高架橋面下，空照僅見橋面，依分隔島保留',
              24: '空照可見植栽（植栽 64%）：樹林綠地（非路徑）',
              26: '建物旁植栽帶（空照可見植栽），非路徑',
              27: '建物旁植栽帶（空照可見植栽），非路徑',
              28: '建物旁植栽帶（空照可見植栽），非路徑',
              29: '建物旁植栽帶（空照可見植栽），非路徑',
              31: '停車場內（非路徑）',
              32: '停車場、空地或街廓內開放空間（非路徑）',
              33: '停車場內（非路徑）',
              34: '停車場內（非路徑）',
              35: '街廓內建物與中庭（非路徑）',
              38: '高架橋面下，空照僅見橋面，依分隔島保留',
              39: '空照可見植栽（植栽 78%）：植栽分隔島／綠地',
              41: '高架橋面下，空照僅見橋面，依分隔島保留',
              42: '停車場內（非路徑）',
              44: '高架橋面下，空照僅見橋面，依分隔島保留',
              48: '高架橋面下，空照僅見橋面，依分隔島保留',
              46: '空照可見植栽（植栽 32%）：植栽分隔島／綠地',
              51: _DECK,
              57: _DECK,
              58: '街廓內廣場／開放鋪面（非路徑）',
              60: _DECK,
              61: _DECK,
              64: '線稿缺建物之街廓（空照為建物屋頂），非路徑',
              65: _DECK,
              67: '空照可見植栽（植栽 64%）：綠帶',
              68: '市民高架橋緣陰影，空照無法判讀，依橋下分隔島保留',
              70: _DECK,
              71: '市民高架橋緣陰影，空照無法判讀，依橋下分隔島保留',
              72: _DECK,
              73: '空照可見植栽（植栽 69%）：綠帶',
              76: '線稿缺建物之街廓（空照為建物屋頂），非路徑'})
# Z7（2026-10-12）：63 塊（地圖框改置中於地圖區後重新 scan，判讀依幾何〔IoU > 0.98〕轉入新編號）。安東街以東至光復南路一帶 37 塊依 Ortho_2025 新判讀
#   （寬視窗補看八德路、光復南／北路、停車場內者），其餘與 Z6 已判讀者幾何相同沿用：路口／行穿線旁三角、細縫、路邊停車帶、八德路車道補齊；
#   市民高架橋面（含匝道）下、植栽帶與林蔭分隔帶、光復南／北路中央分隔帶、停車場內、線稿缺建物者、凸起槽化島保留
DECISIONS['Z7'] = dict(
    FILL={4, 6, 8, 10, 12, 13, 14, 15, 16, 17, 25, 32, 35, 39, 44, 45, 54, 55, 56, 63},
    KEEP_WHY={
              1: '空照可見植栽（植栽 78%）：植栽分隔島／綠地',
              2: '高架橋面下，空照僅見橋面，依分隔島保留',
              3: '停車場內（非路徑）',
              5: '高架橋面下，空照僅見橋面，依分隔島保留',
              7: '空照可見植栽（植栽 32%）：植栽分隔島／綠地',
              9: '高架橋面下，空照僅見橋面，依分隔島保留',
              11: '高架橋面下，空照僅見橋面，依分隔島保留',
              18: '高架橋面下，空照僅見橋面，依分隔島保留',
              19: '街廓內廣場／開放鋪面（非路徑）',
              20: '高架橋面下，空照僅見橋面，依分隔島保留',
              21: '高架橋面下，空照僅見橋面，依分隔島保留',
              22: '街廓內建物前庭與植栽（非路徑）',
              23: '線稿缺建物之街廓（空照為建物屋頂），非路徑',
              24: '高架橋面下，空照僅見橋面，依分隔島保留',
              26: '空照可見植栽（植栽 64%）：綠帶',
              27: '市民高架橋緣陰影，空照無法判讀，依橋下分隔島保留',
              28: '高架橋面下，空照僅見橋面，依分隔島保留',
              29: '市民高架橋緣陰影，空照無法判讀，依橋下分隔島保留',
              30: '高架橋面下，空照僅見橋面，依分隔島保留',
              31: '空照可見植栽（植栽 69%）：綠帶',
              33: '線稿缺建物之街廓（空照為建物屋頂），非路徑',
              34: '高架橋面下，空照僅見橋面，依分隔島保留',
              36: '線稿缺建物（空照為建物屋頂），非路徑',
              37: '高架橋面下，空照僅見橋面，依分隔島保留',
              38: '線稿缺建物之街廓（空照為建物屋頂），非路徑',
              40: '高架橋面下，空照僅見橋面，依分隔島保留',
              41: '空照可見植栽（植栽 54%）：植栽三角島',
              42: '停車場內（非路徑）',
              43: '高架橋面下，空照僅見橋面，依分隔島保留',
              46: '空照可見植栽（植栽 91%）：樹林綠地（非路徑）',
              47: '停車場內（非路徑）',
              48: '高架橋面下，空照僅見橋面，依分隔島保留',
              49: '空照可見植栽：林蔭分隔帶',
              50: '空照可見植栽：林蔭分隔帶',
              51: '空照可見植栽：林蔭分隔帶',
              52: '高架橋面下，空照僅見橋面，依分隔島保留',
              53: '高架橋面下，空照僅見橋面，依分隔島保留',
              57: '光復南路／光復北路中央分隔帶（空照可見凸起分隔帶），依分隔島保留',
              58: '光復南路／光復北路中央分隔帶（空照可見凸起分隔帶），依分隔島保留',
              59: '光復南路／光復北路中央分隔帶（空照可見凸起分隔帶），依分隔島保留',
              60: '高架橋面下，空照僅見橋面，依分隔島保留',
              61: '高架橋面下，空照僅見橋面，依分隔島保留',
              62: '光復南路／光復北路中央分隔帶（空照可見凸起分隔帶），依分隔島保留'})
# Z8（2026-10-12）：55 塊，依 Ortho_2025 逐塊判讀——路口／行穿線旁三角、細縫、車道內小孔補齊；光復南／北路與忠孝東路中央分隔帶、
#   植栽帶、市民高架與基隆路匝道橋面下、線稿缺建物之街廓、停車場內保留
DECISIONS['Z8'] = dict(
    FILL={7, 8, 9, 10, 11, 18, 21, 22, 23, 28, 31, 36, 37, 46, 48, 49, 51, 53, 54, 55},
    KEEP_WHY={1: '停車場內（非路徑）', 5: '市民大道中央分隔帶（高架下），依分隔島保留', 6: '市民大道中央分隔帶（高架下），依分隔島保留',
              12: '光復南路／光復北路中央分隔帶（空照可見凸起分隔帶），依分隔島保留', 13: '光復南路／光復北路中央分隔帶（空照可見凸起分隔帶），依分隔島保留', 14: '光復南路／光復北路中央分隔帶（空照可見凸起分隔帶），依分隔島保留', 17: '光復南路／光復北路中央分隔帶（空照可見凸起分隔帶），依分隔島保留',
              20: '忠孝東路分隔帶（空照可見凸起分隔帶），依分隔島保留',
              32: '基隆路匝道橋面下（空照僅見橋面與陰影），依分隔島保留', 34: '基隆路匝道橋面下（空照僅見橋面與陰影），依分隔島保留', 38: '基隆路匝道橋面下（空照僅見橋面與陰影），依分隔島保留', 40: '基隆路匝道橋面下（空照僅見橋面與陰影），依分隔島保留', 41: '基隆路匝道橋面下（空照僅見橋面與陰影），依分隔島保留', 42: '基隆路匝道橋面下（空照僅見橋面與陰影），依分隔島保留', 44: '基隆路匝道橋面下（空照僅見橋面與陰影），依分隔島保留',
              39: '匝道與平面道路間之分隔帶（凸起），依分隔島保留',
              43: '線稿缺建物之街廓（空照為建物屋頂），非路徑', 47: '線稿缺建物之街廓（空照為建物屋頂），非路徑',
              50: '道路中央分隔帶／候車島（凸起），依分隔島保留', 52: '建物邊緣（空照為屋頂或騎樓），非路徑'})
_D = DECISIONS.get(ZONE, {})
KEEP_WHY = _D.get('KEEP_WHY', {})
FILL, UNDER_DECK_KEEP = _D.get('FILL', set()), _D.get('UNDER_DECK_KEEP', set())
USER_FILLED, USER_SHEET_PTS = _D.get('USER_FILLED', set()), _D.get('USER_SHEET_PTS', [])
def reason(r):
    g, a, w = r['green'], r['gray'], r['width']
    if r['id'] in KEEP_WHY: return 'keep', KEEP_WHY[r['id']]
    if r['id'] in UNDER_DECK_KEEP: return 'keep', '高架橋面下，空照僅見橋面，依分隔島保留'
    if r['id'] in FILL:
        base = '使用者已於 AI 補齊；' if r['id'] in USER_FILLED else ''
        if w < 2.2: return 'fill', base + f'細長縫（平均寬 {w:.1f} m），空照為鋪面'
        if r['area'] < 120: return 'fill', base + '路口／行穿線旁之鋪面三角碎塊'
        return 'fill', base + f'空照為車道或人行鋪面（鋪面 {a:.0%}、植栽 {g:.0%}），非分隔島'
    if g >= .3: return 'keep', f'空照可見植栽（植栽 {g:.0%}）：植栽分隔島／綠地'
    if r['geom'].intersection(S.deck).area > .5 * r['area']: return 'keep', '高架橋下分隔島（橋墩所在）'
    if r['area'] > 600: return 'keep', '停車場、空地或街廓內開放空間（非路徑）'
    return 'keep', '空照可見凸起分隔島／中央島或候車島'
if MODE == 'apply':
    feats = []
    for r in rows:
        dec, why = reason(r)
        feats.append({'type': 'Feature', 'geometry': mapping(r['geom']), 'properties': {'id': r['id'], 'decision': dec, 'reason': why,
                      'area_m2': r['area'], 'width_m': r['width'], 'green': r['green'], 'paved': r['gray']}})
    from shapely.geometry import Point as _P
    WB2 = box(*VIEW.buffer(400).bounds)
    allholes = WB2.difference(N.paths_geom(WB2, fill=False))
    for xm, ym, why in USER_SHEET_PTS:
        pw = N.sheet_to_world(ZONE, xm, ym)
        # 點位取自 AI 圖面比對（±1 mm＝±2.5 m）：取 6 m 內最近之單一孔洞
        cand = sorted((q.distance(pw), q) for q in getattr(allholes, 'geoms', [allholes]) if q.geom_type == 'Polygon' and q.area < 20000 and q.distance(pw) < 6)
        hit = [cand[0][1]] if cand else []
        for q in hit:
            q = q.difference(S.bld)
            feats.append({'type': 'Feature', 'geometry': mapping(q), 'properties': {'id': -1, 'decision': 'fill', 'reason': why, 'area_m2': round(q.area)}})
            print('user fill', round(q.area), 'm2 at', round(pw.x), round(pw.y))
        if not hit: print('user point: no hole found at', round(pw.x), round(pw.y))
    # 2 m² 以下之微小孔洞（無建物）一律補齊
    tiny = [q for q in getattr(holes, 'geoms', [holes]) if q.geom_type == 'Polygon' and q.area < 2 and q.intersects(VIEW) and q.intersection(bld).area < .2 * q.area]
    for q in tiny:
        feats.append({'type': 'Feature', 'geometry': mapping(q), 'properties': {'id': 0, 'decision': 'fill', 'reason': '2 m² 以下微小孔洞', 'area_m2': round(q.area, 2)}})
    json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': feats,
               'source': 'Ortho_2025（臺北市都發局 historygis，02_南京至仁愛擴幅/imagery）', 'date': '2026-10-11'},
              open(OUT, 'w'), ensure_ascii=False)
    import collections
    c = collections.Counter(f['properties']['decision'] for f in feats if f['properties']['id'])
    print('apply', dict(c), 'tiny', len(tiny), 'fill area m2', round(sum(r['area'] for r in rows if reason(r)[0] == 'fill')))
