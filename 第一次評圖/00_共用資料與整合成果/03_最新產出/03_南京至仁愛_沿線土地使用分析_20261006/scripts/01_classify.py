# 市民高架沿線（南京西路—仁愛路）建物現況使用分類
# 底圖：02_南京至仁愛擴幅_20261005 線稿（EPSG:3826）；使用屬性：本地 OSM 2026-09-08
import json, collections
from pathlib import Path
from shapely.geometry import shape, mapping, LineString, MultiLineString, box, Polygon
from shapely.ops import unary_union, transform
from shapely.strtree import STRtree
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
ROOT = H.parents[1]
BASE = ROOT / '03_最新產出/02_南京至仁愛擴幅_20261005'
OUT = H / 'data'; OUT.mkdir(exist_ok=True)
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform

# 分類（依台灣土地使用現況調查慣用色系）
CLASSES = [  # 2026-10-13 修訂：恢復原彩度（P1–P3 以合併組代表色概括，P4／P5 用細部色）
    ('RES', '住宅', '#F2D35B'),
    ('COM', '商業（零售／餐飲／旅館）', '#E0473C'),
    ('MIX', '一樓店面（住宅／街屋）', '#F39A4A'),
    ('OFF', '辦公', '#B03A73'),
    ('GOV', '政府機關／公共服務', '#2F6DB5'),
    ('EDU', '文教（學校／文化）', '#4BA3C7'),
    ('MED', '醫療', '#E79BBE'),
    ('REL', '宗教', '#9A6A3A'),
    ('HER', '產業遺構／登錄古蹟・歷史建築', '#C98BD9'),
    ('IND', '工業／倉儲', '#7B5BB5'),
    ('TRN', '交通／停車', '#7D7D7D'),
    ('REC', '運動休閒', '#5DA95A'),
    ('UNK', '未標示／待調查', '#D6D6D6'),
]
CODE = {c[0]: c for c in CLASSES}

def classify(p):
    a, s, o, t = p.get('amenity'), p.get('shop'), p.get('office'), p.get('tourism')
    b = p.get('building'); le = p.get('leisure')
    if p.get('healthcare') or a in ('hospital', 'clinic', 'doctors', 'dentist', 'pharmacy') or b == 'hospital': return 'MED'
    if a == 'place_of_worship' or p.get('religion') or b in ('temple', 'church', 'shrine', 'mosque', 'chapel', 'cathedral'): return 'REL'
    if a in ('school', 'university', 'college', 'kindergarten', 'library', 'arts_centre', 'theatre', 'cinema') or t == 'museum' \
       or b in ('school', 'university', 'college', 'kindergarten') or o == 'educational_institution': return 'EDU'
    if a in ('townhall', 'police', 'fire_station', 'post_office', 'courthouse', 'community_centre', 'social_facility') \
       or o in ('government', 'police', 'post_office') or b in ('government', 'public', 'civic'): return 'GOV'
    if le in ('sports_centre', 'stadium', 'fitness_centre', 'swimming_pool') or b in ('sports_hall', 'stadium', 'grandstand'): return 'REC'
    if a in ('parking', 'bus_station') or p.get('public_transport') == 'station' or p.get('railway') == 'station' \
       or b in ('transportation', 'parking', 'train_station', 'garage', 'garages'): return 'TRN'
    if o or b == 'office': return 'OFF'
    if s or t in ('hotel', 'hostel', 'guest_house') or a in ('restaurant', 'cafe', 'fast_food', 'bank', 'marketplace', 'bar') \
       or b in ('commercial', 'retail', 'hotel', 'supermarket', 'kiosk'): return 'COM'
    if b in ('industrial', 'warehouse', 'factory', 'manufacture'): return 'IND'
    if b in ('apartments', 'residential', 'house', 'dormitory', 'terrace', 'detached'): return 'RES'
    return 'UNK'

def levels(p):
    try: return max(1.0, float(str(p.get('building:levels', '')).split(';')[0]))
    except ValueError: return None

# 1. OSM 建物（僅 building=*，排除 building:part 以免重疊重算）
osm = json.load(open(BASE / 'source/expanded_osm.geojson'))['features']
B = []; tagged_areas = []
for f in osm:
    p = f['properties']
    if f['geometry']['type'] == 'LineString': continue
    g = transform(tf, shape(f['geometry'])).buffer(0)
    if g.is_empty: continue
    if 'building' in p and p['building'] != 'no':
        B.append((g, p))
    elif any(k in p for k in ('amenity', 'shop', 'office', 'tourism', 'leisure', 'healthcare')):
        tagged_areas.append((g, p))  # 非建物面（校地、園區）—— 用來補建物 'yes' 的用途
# 以所在用地面補上 building=yes 的用途
ta_tree = STRtree([g for g, _ in tagged_areas])
rows = []
for g, p in B:
    c = classify(p)
    if c in ('UNK', 'RES') and p.get('building') in ('yes', 'roof', None):
        pt = g.representative_point()
        for i in ta_tree.query(pt, predicate='within'):
            c2 = classify(tagged_areas[i][1])
            if c2 != 'UNK': c = c2; break
    # 產業遺構／古蹟改由文資局登錄名單判定（見 2f），此處不再依 historic 標籤或名稱推定
    rows.append((g, c, levels(p), p.get('name', '')))
# 面積小者優先（較具體的建物先佔位）
rows.sort(key=lambda r: r[0].area)
tree = STRtree([r[0] for r in rows])

# 2. 底圖線稿建物逐棟切分
outl = shape(json.load(open(BASE / 'building_outlines_TWD97.geojson'))['features'][0]['geometry'])
pieces = []
for bid, poly in enumerate(outl.geoms):
    rest = poly; got = []
    for i in sorted(tree.query(poly, predicate='intersects')):
        g, c, lv, nm = rows[i]
        part = rest.intersection(g)
        if part.area < 0.5: continue
        got.append((part, c, lv, nm)); rest = rest.difference(g)
        if rest.area < 0.5: break
    if rest.area >= 0.5: got.append((rest, 'UNK', None, ''))
    # 合併同棟同類小片
    for part, c, lv, nm in got:
        pieces.append({'geometry': part, 'cls': c, 'levels': lv, 'name': nm, 'bid': bid})

# 2b. 以一樓性質為準：住宅／未標示／辦公建物，一樓（或 12 m 內騎樓）有店家點者改判為一樓用途
FOOD = {'restaurant', 'cafe', 'fast_food', 'bar', 'pub', 'ice_cream', 'food_court', 'biergarten'}
def shop_type(t):
    lv = str(t.get('level', '')).split(';')[0].strip()
    if lv and lv not in ('0', '1', 'G', '0.5', '1F'): return None  # 地下街與樓上店不計
    s_, a_ = t.get('shop'), t.get('amenity')
    if s_ in ('vacant', 'no'): return None
    if a_ in ('pharmacy', 'clinic', 'dentist', 'doctors', 'veterinary') or t.get('healthcare') or s_ in ('chemist', 'optician', 'medical_supply'): return 'MED'
    if s_ or t.get('craft') or a_ in FOOD | {'bank', 'bureau_de_change', 'internet_cafe'} \
       or t.get('office') in ('estate_agent', 'insurance', 'travel_agent', 'telecommunication'): return 'COM'
    return None
GF_FROM = {'RES', 'UNK', 'OFF'}
SNAP = 12
ptree = STRtree([pc['geometry'] for pc in pieces])
gf = collections.defaultdict(collections.Counter)
for f in json.load(open(OUT / 'osm_poi_nodes_4326.geojson'))['features']:
    ty = shop_type(f['properties'])
    if not ty: continue
    pt = transform(tf, shape(f['geometry']))
    i = ptree.query_nearest(pt, max_distance=SNAP)
    if len(i): gf[int(i[0])][ty] += 1
for i, pc in enumerate(pieces):
    pc['cls_bld'] = pc['cls']; pc['shops'] = sum(gf[i].values()) if i in gf else 0
    if i in gf and pc['cls'] in GF_FROM:
        t = gf[i].most_common(1)[0][0]
        pc['cls'] = 'MED' if t == 'MED' else ('COM' if pc['cls'] == 'OFF' else 'MIX')

# 2c. 工業／倉儲使用現況調查（2026-10-06）：已停止工業使用者改判現況用途；仍在使用者保留工業
IND_SURVEY = [  # (代號, 場址, E, N, 半徑 m, 現況判定類別, 使用狀態, 現況說明, 依據)
    ('S02', '華山（原台北酒廠）', 303370, 2770841, 200, 'HER', '已停止工業使用', '華山1914文化創意產業園區', '1987 年停產遷廠；現為文創園區'),
    ('S03', '臺北車站附屬機房', 302372, 2770982, 70, 'TRN', '使用中（非工業）', '車站空調／冷卻設施', 'OSM man_made=cooling，位於臺北車站旁'),
    ('S05', '鐵道部園區附屬建物', 301563, 2771311, 90, 'HER', '已停止工業使用', '國立臺灣博物館鐵道部園區（鐵道工場群）', '園區已作博物館使用；2026-10-13 依使用者指示歸產業遺構／古蹟'),
    ('S06', '華捷維修（臺北捷運）', 302438, 2771257, 45, 'TRN', '使用中（非工業）', '捷運維修設施', 'OSM operator=臺北大眾捷運股份有限公司'),
    ('S07', '忠孝抽水站', 301079, 2771379, 45, 'GOV', '使用中（非工業）', '市政防洪抽水站', 'OSM man_made=pumping_station'),
    ('S08', '長安抽水站', 303189, 2771702, 45, 'GOV', '使用中（非工業）', '市政防洪抽水站', 'OSM name'),
    ('S09', '建國啤酒廠（台北啤酒工場）', 303976, 2771053, 170, 'IND', '使用中（生產）', '啤酒生產持續；部分活化（346 倉庫餐廳）', '公視新聞等：市區唯一百年仍在生產之工廠，古蹟在生產線不中斷原則下活化'),
    ('S10', '松山菸廠', 306539, 2770778, 220, 'HER', '已停止工業使用', '松山文創園區', '1998 年停產；現為文創園區'),
    ('S11', '臺北機廠', 306933, 2771003, 420, 'HER', '已停止工業使用', '國家鐵道博物館（2025-07-31 第一階段開放，其餘修復中）', '2013 年遷廠；中央社 2025-07 報導'),
    ('S12', '省政府糧食局北市一號倉庫', 305007, 2771138, 40, 'HER', '已登錄歷史建築', '北市一號倉庫（歷史建築，2011 登錄）', '文資局開放資料案號 20110428000001'),
    ('S14', '臺大醫院附屬機房', 302280, 2770750, 130, 'MED', '使用中（非工業）', '醫院鍋爐室等附屬設施', 'OSM name=臺大醫院鍋爐室煙囪，位於院區內'),
    ('S13', '基隆路一段旁小型工業建物', 307374, 2771278, 60, 'IND', '待查', '未命名，位於分區外', 'OSM 僅 building=industrial'),
]
from shapely.geometry import Point as _Pt
for pc in pieces:
    pc['ind_site'] = ''
    if pc['cls'] not in ('IND',): continue
    rp = pc['geometry'].representative_point()
    for sid, nm, e, n, r, new, st, now, src in IND_SURVEY:
        if rp.distance(_Pt(e, n)) <= r:
            pc['cls'] = new; pc['ind_site'] = sid; break
import csv as _csv
with open(OUT / '工業倉儲使用現況調查.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = _csv.writer(fh); w.writerow(['代號', '場址', 'E', 'N', '現況判定類別', '使用狀態', '現況說明', '依據'])
    for sid, nm, e, n, r, new, st, now, src in IND_SURVEY: w.writerow([sid, nm, e, n, CODE[new][1], st, now, src])

# 2d. 停車（2026-10-13）：立體停車場（整棟為停車用途）改判交通／停車；含地下停車場之建物維持一樓用途（圖面另以斜線標示，見 10_parking_landuse.py）
# 對應表為 09_parking_buildings.py 之輸出（bid 依線稿建物順序，線稿不變即穩定）
import re as _re
_pk = OUT / '停車場建物判讀.csv'
PARK_STRUCT = set()
if _pk.exists():
    for r in _csv.DictReader(open(_pk, encoding='utf-8-sig')):
        if r['對應建物bid'] and _re.search('立體停車場', r['停車場']): PARK_STRUCT.add(int(r['對應建物bid']))
for pc in pieces:
    if pc['bid'] in PARK_STRUCT and pc['cls'] != 'TRN':
        pc['cls'] = 'TRN'; pc['park_struct'] = True

# 2e. 未標示補判（2026-10-13 使用者指示）：先調用 Z1–Z8 主題圖逐棟判讀（04_Z1-Z7_第一排街廓詳細平面／data/Z*_key_buildings 等），
#     其次本機都更案基地（公共案件量體與基地、都更案基地與剪影 U04–U09）；都對不到者保留 UNK，圖面不顯示，清單寫入 workflow 與 data/未標示建物_無對應.csv
THEME = ROOT / '03_最新產出/04_Z1-Z7_第一排街廓詳細平面_20261007/data'
GROUP2CLS = {'住宅': 'RES', '店面＋住宅': 'MIX', '騎樓店面': 'MIX', '臨街店面': 'MIX', '一般餐飲': 'MIX', '宵夜小吃': 'MIX',
             '居酒屋／燒肉串燒': 'MIX', '酒吧／飲酒店': 'MIX', '商業': 'COM', '轉乘＋商業': 'COM', '商業大樓／旅館': 'COM',
             '日常生活店家': 'COM', '商辦／政府機關': 'OFF', '大型商場／市場': 'COM', '古蹟': 'HER', '北門古蹟群': 'HER',
             '國家鐵道博物館（臺北機廠）': 'HER', '松山文創園區': 'HER', '臺北大巨蛋（文化體育園區）': 'REC',
             '懷生國小': 'EDU', '北科大學生宿舍': 'RES', '忠泰美術館街廓': 'COM', '兒童遊戲場': 'REC'}
NAME2CLS = [('國宅', 'RES'), ('宿舍', 'RES'), ('抽水站', 'GOV'), ('國小', 'EDU'), ('大學', 'EDU'), ('雙子星', 'COM'), ('車站', 'TRN')]
CASE2CLS = {  # 都更案：已完成者依完成用途；審議中私人案依現況舊有住宅；公辦／公共依現況
    'U01': ('HER', '臺北車站 E1／E2：鐵道遺構與文資修復區'), 'U17': ('RES', '行二行三：現住戶原地安置'), 'B01': ('GOV', '華山司法園區（施工中）'),
    'U02': ('GOV', '長安市民公辦都更：公有地'), 'U03': ('REC', '中油中山公辦都更：現有中崙球場'), 'U04': ('COM', '明日博（已完成）'),
    'U05': ('RES', '德杰（已完成，敦南樞苑）'), 'U06': ('OFF', '富邦敦南大樓（已完成）'), 'U07': ('RES', '麗寶（已完成）'),
    'U08': ('RES', '青園（審議中，現況舊住宅）'), 'U09': ('RES', '馗豐（審議中，現況舊住宅）'), 'U10': ('RES', '機廠北側（結案，現況舊住宅）')}
theme_src = []
import glob as _glob
for fn in sorted(_glob.glob(str(THEME / 'Z*_key_buildings_EPSG3826.geojson'))):
    for f in json.load(open(fn))['features']:
        pr = f['properties']
        if pr.get('kind') != 'key' or f['geometry']['type'] == 'Point': continue
        c = GROUP2CLS.get(pr.get('group') or '')
        if not c:
            c = next((v for k, v in NAME2CLS if k in (pr.get('name') or '')), None)
        if c: theme_src.append((shape(f['geometry']).buffer(0), c, f"主題圖 {Path(fn).name[:2]}｜{pr.get('group') or pr.get('name')}"))
case_src = []
for fn in [ROOT / '02_調整過程/公共都更編號圖/公共案件量體與基地_EPSG3826.geojson',
           ROOT / '04_其他疊合與排版成果/CAD及官方平面疊合/urban_plan_review/南京仁愛沿線都市計畫範圍_20261006/都更案基地與剪影_U04-U09_EPSG3826.geojson']:
    for f in json.load(open(fn))['features']:
        pr = f['properties']
        if pr['layer'] in ('site', 'building', 'locator') and pr['case'] in CASE2CLS:
            g = shape(f['geometry']).buffer(0)
            if g.area >= 50: case_src.append((g, CASE2CLS[pr['case']][0], f"都更案 {pr['case']}｜{CASE2CLS[pr['case']][1]}"))
fill_log = collections.Counter()
for pc in pieces:
    pc['fill_src'] = ''
    if pc['cls'] != 'UNK': continue
    g = pc['geometry']
    for src in (theme_src, case_src):
        hit = next(((c, why) for sg, c, why in src if g.intersects(sg) and g.intersection(sg).area >= 0.3 * g.area), None)
        if hit:
            pc['cls'], pc['fill_src'] = hit; fill_log[hit[1].split('｜')[0]] += 1; break
print('未標示補判', dict(fill_log))

# 2f. 產業遺構／古蹟（2026-10-13 使用者指示：每一段重新抓，以臺北市已登錄文化資產為準）
#     來源：文化部文化資產局 國家文化資產網開放資料（11_heritage_fetch.py → data/文資登錄_圖幅內.json：古蹟、歷史建築、聚落建築群、紀念建築）
#     對應：登錄點落在線稿建物內 → 該建物；否則 20 m 內最近建物；再否則名稱比對、40 m 內最近建物；廠區型（臺北酒廠、松山菸廠、臺北機廠、鐵道部）另依 IND_SURVEY 範圍整區
#     例外：建國啤酒廠仍在生產，維持工業／倉儲（同屬產業組）；一案多點者（臺北府城四門）以名稱補北門
REG = json.load(open(OUT / '文資登錄_圖幅內.json'))['cases']
EXTRA = [('臺北府城北門', '19980903000001', '臺北府城—東門、南門、小南門、北門', '古蹟')]
by_bid = collections.defaultdict(list)
for pc in pieces: by_bid[pc['bid']].append(pc)
bgeom = list(outl.geoms); btree = STRtree(bgeom)
reg_rows = []
for c in REG:
    pt = _Pt(c['E'], c['N'])
    ins = [int(i) for i in btree.query(pt, predicate='within')]
    if ins: bid, d = max(ins, key=lambda i: bgeom[i].area), 0.0
    else:
        near = btree.query_nearest(pt, max_distance=40)
        bid, d = (int(near[0]), round(bgeom[int(near[0])].distance(pt), 1)) if len(near) else (None, None)
        if bid is None or d > 20:  # 名稱比對優先於 20–40 m 就近
            core = c['name'].split('(')[0].split('（')[0]
            nm_hit = [pc for pc in pieces if len(core) >= 2 and core in (pc.get('name') or '')]
            if nm_hit: bid, d = max(nm_hit, key=lambda q: q['geometry'].area)['bid'], 'name'
    reg_rows.append((c, bid, d))
    if bid is None: continue
    for pc in by_bid[bid]:
        if '建國啤酒廠' in c['name']: continue
        pc['cls'] = 'HER'; pc['fill_src'] = f"文資登錄｜{c['type']}｜{c['name']}"
for nm, cid, case, typ in EXTRA:
    for pc in pieces:
        if nm in (pc.get('name') or ''): pc['cls'] = 'HER'; pc['fill_src'] = f'文資登錄｜{typ}｜{case}'
with open(OUT / '文資登錄_對應建物.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = _csv.writer(fh); w.writerow(['案號', '名稱', '類別', '等級', '類型', 'E', 'N', '對應建物bid', '距離_m'])
    for c, bid, d in reg_rows: w.writerow([c['caseId'], c['name'], c['type'], c['grade'] or '', '／'.join(c['kinds']), c['E'], c['N'], '' if bid is None else bid, '' if d is None else d])
print('文資登錄', len(REG), '件；對應建物', sum(1 for _, b, _ in reg_rows if b is not None))

# 3. 市民高架軸線與距離帶
ax = json.load(open(ROOT / '01_輸入資料/前處理資料/axis.json'))
elev = unary_union([transform(tf, LineString(l)) for l in ax['elevated_ll'] if len(l) > 1])
ramps = unary_union([transform(tf, LineString(l)) for l in ax['ramps_ll'] if len(l) > 1])
axis = transform(tf, LineString(ax['axis_ll']))
frame = box(300935, 2770000, 307545, 2771910)
BANDS = [(0, 100), (100, 200), (200, 300), (300, 9999)]
q = json.load(open(BASE / 'qa.json'))
sheets = [(s['id'], box(*s['bounds'])) for s in q['sheets']]

# 分區：依使用者紙本藍色標記（2026-10-06 照片 A01–A07），對位至與市民大道軸線相交之路口
from shapely.ops import substring
from shapely.geometry import Point
# 設計介入單元（2026-10-06 修訂）：每段一個主要基地或界面類型；界線沿實際路口中心線
# (標示名, OSM 道路名前綴, 與市民大道交會之概略 E)；起點為淡水河堤；原「安東—大安」「大安—光復」依宵夜／居酒屋餐飲帶連續性合併
CUTS = [('淡水河堤', None, 301030), ('承德路', ('承德路一段',), 302125), ('中山北路', ('中山北路一段', '中山南路'), 302546),
        ('林森北路', ('林森北路', '林森南路'), 302893), ('新生高架（金山北路）', ('金山北路', '金山南路一段'), 303547),
        ('建國高架', ('建國北路一段', '建國南路一段', '建國北路二段'), 304150), ('安東街', ('安東街',), 304726),
        ('光復南路', ('光復南路', '光復北路'), 306285)]
END = (axis.coords[-1][0], '基隆路')
UNIT_INFO = {  # 單元主角
    'Z1': '河岸門戶＋北門古蹟群＋台北雙子星', 'Z2': '臺北車站樞紐（車站、京站、轉運站、心中山）', 'Z3': '行政院行二行三公辦都更（U17）',
    'Z4': '華山（司法園區＋華山1914）', 'Z5': '光華—北科大—建國啤酒廠', 'Z6': '長安段公辦都更（U02／U03）',
    'Z7': '東區北緣宵夜／居酒屋餐飲帶（微風廣場為西端節點）', 'Z8': '松山文創＋大巨蛋＋國家鐵道博物館'}
ZONE_W = 300
osm_lines = [(transform(tf, shape(f['geometry'])), f['properties'].get('name', '')) for f in osm
             if f['geometry']['type'] == 'LineString' and 'highway' in f['properties']]
def street_centerline(prefixes, e0, y0=2770000, y1=2771910, win=160):
    # 逐 15 m 水平掃描，取該道路（含雙向分隔車道）交點平均 x 為中心線；無交點處以前後已知點線性外插
    geoms = unary_union([g for g, n in osm_lines if n and n.startswith(prefixes) and not any(k in n for k in ('巷', '弄', '匝道', '地下道'))
                         and g.intersects(box(e0 - win, y0, e0 + win, y1))])
    ys, xs = [], []
    for y in range(y0, y1 + 1, 15):
        hit = geoms.intersection(LineString([(e0 - win, y), (e0 + win, y)]))
        pts_ = [q.x for q in getattr(hit, 'geoms', [hit]) if q.geom_type == 'Point']
        if pts_: ys.append(y); xs.append(sum(pts_) / len(pts_))
    import numpy as _np
    if len(ys) < 2: return LineString([(e0, y0), (e0, y1)])
    yy = _np.arange(y0, y1 + 1, 15)
    k1 = _np.polyfit(ys[:6], xs[:6], 1); k2 = _np.polyfit(ys[-6:], xs[-6:], 1)
    xx = _np.interp(yy, ys, xs)
    xx = _np.where(yy < ys[0], _np.polyval(k1, yy), xx); xx = _np.where(yy > ys[-1], _np.polyval(k2, yy), xx)
    return LineString(list(zip(xx, yy)))
def unit_cut(pre, e):
    # 走廊內（軸線 ±(300+40) m）沿實際路口中心線；走廊外以垂直線延伸至圖框上下緣
    if pre is None: return LineString([(e, 2770000), (e, 2771910)])
    ya = axis.interpolate(axis.project(Point(e, 2771000))).y
    cl = street_centerline(pre, e, int(ya - ZONE_W - 40), int(ya + ZONE_W + 40))
    c = list(cl.coords)
    return LineString([(c[0][0], 2770000)] + c + [(c[-1][0], 2771910)])
from shapely.geometry import Point
cut_geoms = [unit_cut(pre, e) for nm, pre, e in CUTS]
marks = [(e, nm) for nm, pre, e in CUTS] + [END]
def station(e):
    best = min(((abs(axis.interpolate(t).x - e), t) for t in range(0, int(axis.length) + 1, 2)))
    return best[1]
st = [station(e) for e, _ in marks]
corridor = axis.buffer(ZONE_W, cap_style='flat').intersection(frame)
ZONES = []
for i in range(len(marks) - 1):
    left = list(cut_geoms[i].coords)
    right = list(cut_geoms[i + 1].coords)[::-1] if i + 1 < len(cut_geoms) else [(END[0] + 400, 2771910), (END[0] + 400, 2770000)]
    poly = corridor.intersection(Polygon(left + right).buffer(0))
    ZONES.append({'id': f'Z{i + 1}', 'from': marks[i][1], 'to': marks[i + 1][1], 'len_m': round(st[i + 1] - st[i]),
                  'info': UNIT_INFO[f'Z{i + 1}'], 'geometry': poly})
cutlines = cut_geoms
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}},
           'features': [{'type': 'Feature', 'geometry': mapping(z['geometry']), 'properties': {k: v for k, v in z.items() if k != 'geometry'}} for z in ZONES]
                     + [{'type': 'Feature', 'geometry': mapping(l), 'properties': {'cut': marks[i][1]}} for i, l in enumerate(cutlines)]},
          open(OUT / 'zones_EPSG3826.geojson', 'w'), ensure_ascii=False)
# 範圍規則：線稿建物只要被 300 m 範圍線切到（相交）即整棟計入；跨分區界線者歸重疊面積最大之分區
bid_zone = {}
for bid, poly in enumerate(outl.geoms):
    ov = [(poly.intersection(z['geometry']).area, z['id']) for z in ZONES if poly.intersects(z['geometry'])]
    ov = [o for o in ov if o[0] > 0]
    bid_zone[bid] = max(ov)[1] if ov else ''
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}},
           'features': [{'type': 'Feature', 'geometry': mapping(poly), 'properties': {'bid': bid, 'zone': bid_zone[bid]}}
                        for bid, poly in enumerate(outl.geoms)]}, open(OUT / 'drawing_buildings_zone_EPSG3826.geojson', 'w'))
for pc in pieces:
    pt = pc['geometry'].representative_point()
    d = elev.distance(pt) if not elev.is_empty else axis.distance(pt)
    pc['dist'] = d
    pc['band'] = next(f'{a}-{b}' if b < 9999 else f'>{a}' for a, b in BANDS if a <= d < b)
    pc['sheet'] = next((sid for sid, sb in sheets if sb.contains(pt)), '')
    pc['zone'] = bid_zone[pc['bid']]
    pc['area'] = pc['geometry'].area

fc = {'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}},
      'features': [{'type': 'Feature', 'geometry': mapping(pc['geometry']),
                    'properties': {k: (round(v, 2) if isinstance(v, float) else v) for k, v in pc.items() if k != 'geometry'}
                                  | {'cls_zh': CODE[pc['cls']][1]}} for pc in pieces]}
json.dump(fc, open(OUT / 'landuse_pieces_EPSG3826.geojson', 'w'), ensure_ascii=False)
json.dump({'elevated': mapping(elev), 'ramps': mapping(ramps), 'axis': mapping(axis)}, open(OUT / 'civic_elevated_EPSG3826.json', 'w'))

# 4. 統計
def table(key):
    t = collections.defaultdict(lambda: collections.Counter())
    for pc in pieces:
        t[pc[key]][pc['cls']] += pc['area']
        if pc['levels']: t[pc[key]]['_floor'] += pc['area'] * pc['levels']; t[pc[key]]['_lvarea'] += pc['area']
    return t
import csv
with open(OUT / '統計_距離帶與分幅.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.writer(fh)
    w.writerow(['分組', '組別'] + [c[1] + '_m2' for c in CLASSES] + ['合計_m2'] + [c[1] + '_%' for c in CLASSES])
    for key, label in (('band', '距高架距離帶(m)'), ('sheet', '分幅'), ('zone', '分區')):
        t = table(key)
        order = {'band': [f'{a}-{b}' if b < 9999 else f'>{a}' for a, b in BANDS], 'sheet': [s for s, _ in sheets],
                 'zone': [z['id'] for z in ZONES]}[key]
        for g in order:
            tot = sum(t[g][c[0]] for c in CLASSES) or 1
            w.writerow([label, g] + [round(t[g][c[0]]) for c in CLASSES] + [round(tot)] + [round(100 * t[g][c[0]] / tot, 1) for c in CLASSES])
    t = collections.Counter()
    for pc in pieces: t[pc['cls']] += pc['area']
    tot = sum(t.values())
    w.writerow(['全幅', '全部'] + [round(t[c[0]]) for c in CLASSES] + [round(tot)] + [round(100 * t[c[0]] / tot, 1) for c in CLASSES])
lv = sum(pc['area'] for pc in pieces if pc['levels'])
n_gf = sum(1 for pc in pieces if pc['cls'] != pc['cls_bld'])
summary = {'ground_floor_reclassified_pieces': n_gf,
           'ground_floor_reclassified_m2': round(sum(pc['area'] for pc in pieces if pc['cls'] != pc['cls_bld'])),
           'drawing_buildings': len(outl.geoms), 'pieces': len(pieces), 'osm_buildings': len(rows),
           'footprint_m2': round(tot), 'unclassified_pct': round(100 * t['UNK'] / tot, 1),
           'levels_coverage_pct': round(100 * lv / tot, 1),
           'class_pct': {CODE[k][1]: round(100 * v / tot, 1) for k, v in t.most_common()}}
json.dump(summary, open(OUT / 'summary.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(summary, ensure_ascii=False, indent=1))

# 2e 續：補判後仍未標示者（範圍內）清單 → workflow 註記；圖面不顯示
_left = [pc for pc in pieces if pc['cls'] == 'UNK' and pc.get('zone')]
with open(OUT / '未標示建物_無對應.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = _csv.writer(fh); w.writerow(['單元', '線稿建物bid', 'E', 'N', '投影面積_m2', '距高架_m'])
    for pc in sorted(_left, key=lambda q: (q['zone'], -q['area'])):
        rp = pc['geometry'].representative_point()
        w.writerow([pc['zone'], pc['bid'], round(rp.x), round(rp.y), round(pc['area']), round(pc['dist'])])
print('範圍內仍未標示', len(_left), '片', round(sum(pc['area'] for pc in _left)), 'm2')
