# Z7 夜間餐飲（使用者 2026-10-12 指定，回覆 Z7 問題清單）：
#   主角（workflow 三，不改寫）：東區北緣宵夜／居酒屋餐飲帶（微風廣場為西端節點；使用者指定微風廣場不列為主角）。
#   特性建築＝全部餐飲建物，依型態分四色（只計一樓店面）：居酒屋／燒肉串燒、酒吧／飲酒店、宵夜小吃、一般餐飲。
#   資料：OSM 判型態（料理標籤、店名）與營業時間，稅籍補數量；營業時間不明者另外標示。
#   統計＝夜間餐飲專用分類（型態 × 營業時段 × 南北）；正常營業時間之晚餐也列入，不只宵夜。
#   一、店家
#     OSM：amenity=restaurant／fast_food／bar／pub／biergarten／food_court（點＝03 osm_poi_nodes；面＝臺灣 PBF 2026-09-08，取代表點）。
#       咖啡館、冰品（cafe、ice_cream）屬飲料甜點，不列；addr:floor ≥ 2 或 level ≥ 1 之樓上店家不計（只計一樓）。
#     稅籍：財政部營業（稅籍）登記 2026-10-11（27 門牌定位）之餐館業 5611、餐食攤販 5612、飲酒店 563114；
#       早餐店 561111、飲料店（手搖飲、咖啡等 5631，飲酒店除外）、外燴團膳 5620 不列（非晚餐）；
#       一樓、地下或未載樓層；同一完整地址 ≥ 3 家為借址登記不計（同 27／31）。
#   二、型態（單店；依序判定，先符合者為準）
#     居酒屋／燒肉串燒：OSM cuisine＝izakaya／yakitori／yakiniku／barbecue 等，或店名含居酒、酒屋、酒場、串燒、燒鳥、燒肉、燒烤、炭火、爐端等；
#     酒吧／飲酒店：OSM amenity=bar／pub／biergarten，稅籍飲酒店，或店名含酒吧、酒館、啤酒、精釀、威士忌、Bar、Pub 等；
#     宵夜小吃：稅籍麵店小吃店 561113、餐食攤販 5612，OSM cuisine＝noodle／ramen／taiwanese／dumpling 等，或店名含熱炒、小吃、麵、粥、滷味、鹹酥雞等
#       （義大利麵除外）；
#     一般餐飲：其餘餐廳、便當自助餐、速食、吃到飽等。OSM 料理或店名為早餐、早午餐、飲料甜點者不列。
#   三、營業時段（OSM opening_hours；任一天任一時段）：營業至 23:00 以後（含跨午夜、24/7）＝宵夜；涵蓋 18:00–20:00 之任一時刻＝晚餐；
#     標有時間但晚間不營業＝非晚餐（不列）；未標＝營業時間不明（另外標示）。稅籍無營業時間，一律不明。
#   四、合併（同一建物）：店家點落在建物內，否則 15 m 內最近之本單元建物（門牌點多在騎樓、人行道側；31 用 6 m，Z7 以 6 m 會漏約 9% 店家）。建物歸屬依 workflow 五-4（01_classify drawing_buildings_zone）。
#     OSM 與稅籍以店名對應（去除公司字尾後互相包含或共有 3 字）；對應成功者型態取兩者較特定者。
#     建物店家數＝max（OSM 家數、稅籍家數）（同 31）：OSM 店家全列，稅籍多出之家數以未對應者補入（依型態優先序），營業時段記為不明。
#     建物型態＝店家中最特定者（居酒屋／燒肉串燒 > 酒吧／飲酒店 > 宵夜小吃 > 一般餐飲）。
#   另輸出（19／20 讀取）：
#     data/Z7_mrt_ctx_EPSG3826.geojson：周邊捷運站體（OSM building=transportation），單元外者淡化（比照 Z6，使用者 2026-10-12）。
#     data/Z7_ug_parking_EPSG3826.geojson：市民大道地下停車場分段包絡（03 07_parking；Civic_Rebuild ParkingSections），
#       使用者 2026-10-12「算做剪影」——南北通行元素，B1。車道出入口不上圖（同第十三節）。
#   輸出：data/Z7_night_dining_EPSG3826.geojson（建物）、data/Z7_night_dining_summary.json（統計）、data/Z7_夜間餐飲_明細.csv（逐店，含不計者與原因）
import csv, json, re, sys, collections, importlib.util
from pathlib import Path
from shapely.geometry import shape, mapping, Point
from shapely.ops import transform
from shapely.strtree import STRtree
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
ZONE = 'Z7'
spec = importlib.util.spec_from_file_location('sheet', H / 'scripts/02_sheet.py')
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
S.VARIANT['full'] = True
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform
LU = H.parents[0] / '03_南京至仁愛_沿線土地使用分析_20261006/data'
PBF = Path.home() / 'Downloads/taiwan-260908.osm.pbf'
CACHE = H / 'data/osm_z7_pbf_cache_EPSG3826.geojson'
BB = (304000, 2770100, 306900, 2771600)          # 擷取範圍（EPSG:3826）
FOOD = {'restaurant', 'fast_food', 'bar', 'pub', 'biergarten', 'food_court'}

# ---------- OSM 擷取（快取）：捷運站體、餐飲面 ----------
if not CACHE.exists():
    import osmium
    from shapely import wkb
    inv = Transformer.from_crs(3826, 4326, always_xy=True).transform
    LON0, LAT0 = inv(BB[0], BB[1]); LON1, LAT1 = inv(BB[2], BB[3])
    fab = osmium.geom.WKBFactory(); out = []
    class Hd(osmium.SimpleHandler):
        def area(self, a):
            t = a.tags; nm = t.get('name', '')
            mrt = t.get('building') == 'transportation' and nm.endswith('站')
            food = t.get('amenity') in FOOD
            if not mrt and not food: return
            try: g = wkb.loads(fab.create_multipolygon(a), hex=True)
            except Exception: return
            c = g.centroid
            if LON0 < c.x < LON1 and LAT0 < c.y < LAT1:
                out.append({'type': 'Feature', 'geometry': mapping(transform(tf, g)), 'properties': {'kind': 'mrt' if mrt else 'food', **dict(t)}})
    Hd().apply_file(str(PBF), locations=True, idx='flex_mem')
    json.dump({'type': 'FeatureCollection', 'source': 'OSM 臺灣 PBF 2026-09-08（taiwan-260908.osm.pbf）', 'bbox': BB, 'features': out}, open(CACHE, 'w'), ensure_ascii=False)
OC = json.load(open(CACHE))['features']

ZPOLY = {f['properties']['id']: shape(f['geometry']) for f in S.ZF if 'id' in f['properties']}
zpoly = ZPOLY[ZONE]
BL = list(S.bld.geoms)
BZ = {f['properties']['bid']: f['properties']['zone'] for f in json.load(open(LU / 'drawing_buildings_zone_EPSG3826.geojson'))['features']}
ZB = [b for b, z in BZ.items() if z == ZONE and BL[b].area >= 12]
zb_geo = [BL[b] for b in ZB]; ztree = STRtree(zb_geo)
def bld_at(pt, snap=15):
    idx = [i for i in ztree.query(pt) if zb_geo[i].contains(pt)]
    if idx: return ZB[idx[0]]
    near = [(zb_geo[i].distance(pt), i) for i in ztree.query(pt.buffer(snap))]
    return ZB[min(near)[1]] if near else None
def side(g):
    c = g.representative_point() if g.geom_type != 'Point' else g
    s_ = S.center.project(c); a_ = S.center.interpolate(s_); b_ = S.center.interpolate(min(s_ + 1, S.center.length))
    return '北' if (b_.x - a_.x) * (c.y - a_.y) - (b_.y - a_.y) * (c.x - a_.x) > 0 else '南'

# ---------- 型態 ----------
TYPES = ('居酒屋／燒肉串燒', '酒吧／飲酒店', '宵夜小吃', '一般餐飲')
PRI = {t: i for i, t in enumerate(TYPES)}                    # 數字小＝較特定
IZK_CUI = {'izakaya', 'yakitori', 'yakiniku', 'barbecue', 'bbq', 'robatayaki', 'kushikatsu', 'kushiyaki', 'korean_barbecue'}
IZK_KW = re.compile(r'居酒|居食|酒屋|酒場|酒肴|串燒|串焼|串カツ|燒鳥|焼鳥|燒き鳥|燒肉|焼肉|燒烤|烧烤|炭火|炭烤|爐端|炉端|烤肉|やきとり|焼き鳥|izakaya|yakitori|yakiniku', re.I)
BAR_KW = re.compile(r'酒吧|酒館|酒馆|小酌|啤酒|精釀|威士忌|調酒|\bbar\b|\bpub\b|beer|whisk(e)?y|lounge|brew', re.I)
SNACK_CUI = {'noodle', 'ramen', 'beef_noodle', 'taiwanese', 'dumpling', 'dumplings', 'congee', 'street_food', 'fried_chicken', 'soup', 'oden', 'noodle;regional', 'regional'}
SNACK_KW = re.compile(r'熱炒|快炒|小吃|麵|面館|粥|滷味|鹽酥雞|鹹酥雞|炸雞|臭豆腐|宵夜|夜宵|拉麵|ラーメン|餛飩|水餃|鍋貼|米粉|肉圓|擔仔|麻辣燙|關東煮|おでん|ramen|noodle', re.I)
NOT_BAR = re.compile(r'(pita|salad|juice|sushi|oyster|snack|noodle|tea|smoothie)\s*bar', re.I)   # 「Pita Bar」等為餐飲店名，非酒吧
NOT_SNACK = re.compile(r'義大利|意大利|pasta|italian', re.I)
NODINNER_CUI = {'breakfast', 'brunch', 'coffee_shop', 'bubble_tea', 'juice', 'ice_cream', 'cake', 'dessert', 'donut', 'bakery', 'tea', 'coffee', 'sandwich',
                '咖啡_鬆餅_三明治_冰淇淋_甜點', 'crepe', 'waffle', 'frozen_yogurt'}
NODINNER_KW = re.compile(r'早餐|早午餐|brunch|豆漿|蛋餅|晨間', re.I)
def cuis(t): return {c.strip().lower() for c in re.split(r'[;,]', t.get('cuisine') or '') if c.strip()}
def osm_type(t):
    am = t.get('amenity'); cu = cuis(t)
    nm = ' '.join(t.get(k, '') for k in ('name', 'name:zh', 'name:en', 'name:ja', 'brand'))
    izk = bool(cu & IZK_CUI) or bool(IZK_KW.search(nm))
    if am in ('bar', 'pub', 'biergarten'): return '居酒屋／燒肉串燒' if izk else '酒吧／飲酒店'
    if izk: return '居酒屋／燒肉串燒'
    if BAR_KW.search(nm) and not NOT_BAR.search(nm): return '酒吧／飲酒店'
    if (cu and cu <= NODINNER_CUI) or NODINNER_KW.search(nm): return None          # 早餐、飲料甜點：非晚餐
    if (cu & SNACK_CUI or SNACK_KW.search(nm)) and not NOT_SNACK.search(nm + ' ' + ' '.join(cu)): return '宵夜小吃'
    return '一般餐飲'
def tax_type(code, nm):
    if code.startswith('563114'): return '酒吧／飲酒店'
    if code.startswith('561111') or not code.startswith(('5611', '5612')): return None   # 早餐、飲料店、外燴團膳：非晚餐
    if IZK_KW.search(nm): return '居酒屋／燒肉串燒'
    if BAR_KW.search(nm): return '酒吧／飲酒店'
    if NODINNER_KW.search(nm): return None
    if code.startswith(('561113', '5612')) or (SNACK_KW.search(nm) and not NOT_SNACK.search(nm)): return '宵夜小吃'
    return '一般餐飲'

# ---------- 營業時段 ----------
def hours_class(oh):
    if not oh: return '不明'
    s = oh.replace(' ', '').replace('：', ':')
    if '24/7' in s: return '宵夜'
    rng = re.findall(r'(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})', s)
    if not rng: return '不明'
    late = dinner = False
    for h1, m1, h2, m2 in rng:
        a = int(h1) * 60 + int(m1); b = int(h2) * 60 + int(m2)
        if b <= a: b += 1440                                  # 跨午夜（含 24:00）
        if b > 23 * 60: late = True
        if a < 20 * 60 and b > 18 * 60: dinner = True
    return '宵夜' if late else '晚餐' if dinner else '非晚餐'
HOURS = ('宵夜', '晚餐', '不明')
def upper_floor(t):
    f = str(t.get('addr:floor') or '').upper().replace('F', '')
    if re.fullmatch(r'\d+', f) and int(f) >= 2: return True
    lv = str(t.get('level') or '')
    return bool(re.fullmatch(r'\d+(\.\d+)?', lv) and float(lv) >= 1)

# ---------- 店家：OSM ----------
detail = []                                                   # 明細（含不計者）
O = collections.defaultdict(list)
osm_pts = []
for f in json.load(open(LU / 'osm_poi_nodes_4326.geojson'))['features']:
    t = f['properties']
    if t.get('amenity') in FOOD: osm_pts.append((transform(tf, shape(f['geometry'])), t, f"n{t.get('@id', '')}"))
for f in OC:
    t = f['properties']
    if t['kind'] == 'food': osm_pts.append((shape(f['geometry']).representative_point(), t, 'a'))
for pt, t, oid in osm_pts:
    if not zpoly.buffer(6).contains(pt): continue
    nm = t.get('name') or t.get('name:zh') or t.get('brand') or ''
    row = {'來源': 'OSM', '名稱': nm, '稅籍名稱': '', 'OSM': oid, 'amenity': t.get('amenity'), 'cuisine': t.get('cuisine', ''), 'opening_hours': t.get('opening_hours', ''),
           '行業': '', '樓層': t.get('addr:floor') or t.get('level') or '', 'E': round(pt.x, 1), 'N': round(pt.y, 1), '側': side(pt)}
    if any(k.startswith('disused:') for k in t) and not nm: row.update(計入='否', 排除原因='已歇業（disused）'); detail.append(row); continue
    typ = osm_type(t); hc = hours_class(t.get('opening_hours'))
    row.update(型態=typ or '', 營業時段=hc)
    why = '早餐、飲料甜點（非晚餐）' if typ is None else '樓上店家（只計一樓）' if upper_floor(t) else '營業時間標示晚間不營業（非晚餐）' if hc == '非晚餐' else ''
    b = bld_at(pt) if not why else None
    if not why and b is None: why = '15 m 內無本單元建物'
    if why: row.update(計入='否', 排除原因=why); detail.append(row); continue
    row.update(bid=b); O[b].append(row)

# ---------- 店家：稅籍 ----------
FW = str.maketrans('０１２３４５６７８９－―—‐', '0123456789之之之之')
def norm_addr(a): return re.sub(r'^(臺|台)北市[^\d]{2}區([^\d路街]{1,3}里)?(\d+鄰)?', '', a.translate(FW).replace(' ', '').replace('　', ''))
ALL = list(csv.DictReader(open(H / 'data/official_shops_geocoded_EPSG3826.csv', encoding='utf-8-sig')))
same = collections.Counter(norm_addr(r['營業地址']) for r in ALL)
X = collections.defaultdict(list)
for r in ALL:
    c = r['行業代號']
    if not c.startswith(('5611', '5612', '5631', '5620')) or not r['E']: continue
    pt = Point(float(r['E']), float(r['N']))
    if not zpoly.buffer(6).contains(pt): continue
    typ = tax_type(c, r['營業人名稱'])
    row = {'來源': '稅籍', '名稱': '', '稅籍名稱': r['營業人名稱'], 'OSM': '', 'amenity': '', 'cuisine': '', 'opening_hours': '', '行業': f"{c} {r['名稱']}",
           '樓層': r['樓層'], 'E': r['E'], 'N': r['N'], '側': side(pt), '型態': typ or '', '營業時段': '不明'}
    why = ('早餐、飲料店、外燴（非晚餐）' if typ is None else '樓上店家（只計一樓）' if r['樓層'] not in ('1F', 'B', '未載')
           else '借址登記（同址 ≥ 3 家）' if same[norm_addr(r['營業地址'])] >= 3 else '')
    b = bld_at(pt) if not why else None
    if not why and b is None: why = '15 m 內無本單元建物'
    if why: row.update(計入='否', 排除原因=why); detail.append(row); continue
    row.update(bid=b); X[b].append(row)

# ---------- 合併（同一建物）----------
SUFFIX = re.compile(r'(股份)?有限公司|企業社|商行|工作室|實業|國際|餐飲|事業|分公司|門市部?|[（(].*?[)）]')
def cj(s): return ''.join(c for c in SUFFIX.sub('', s or '') if '一' <= c <= '鿿' or c.isalnum()).lower()
def same_shop(a, b):
    a, b = cj(a), cj(b)
    if len(a) < 2 or len(b) < 2: return False
    return a in b or b in a or any(a[i:i + 3] in b for i in range(len(a) - 2))
shops_by_b = {}
for b in set(O) | set(X):
    os_, xs = O.get(b, []), X.get(b, [])
    used = set()
    for o in os_:
        for j, x in enumerate(xs):
            if j not in used and same_shop(o['名稱'], x['稅籍名稱']):
                used.add(j); o['來源'] = 'OSM＋稅籍'; o['稅籍名稱'] = x['稅籍名稱']; o['行業'] = x['行業']
                if PRI[x['型態']] < PRI[o['型態']]: o['型態'] = x['型態']
                x['計入'] = '否'; x['排除原因'] = '與 OSM 店家對應（併入該筆）'; detail.append(x)
                break
    need = max(0, len(xs) - len(os_))
    rest = sorted([x for j, x in enumerate(xs) if j not in used], key=lambda x: PRI[x['型態']])
    for x in rest[need:]:
        x['計入'] = '否'; x['排除原因'] = '建物店家數取 max（OSM、稅籍），多出者視為與 OSM 店家重複'; detail.append(x)
    fill = rest[:need]
    sh = os_ + fill
    for s_ in sh: s_['計入'] = '是'; s_['排除原因'] = ''
    detail.extend(sh)
    shops_by_b[b] = sh

# ---------- 建物 ----------
feats = []
for b, sh in shops_by_b.items():
    g = BL[b]
    bt = collections.Counter(s_['型態'] for s_ in sh); bh = collections.Counter(s_['營業時段'] for s_ in sh)
    typ = min(bt, key=lambda t: PRI[t])
    names = [s_['名稱'] or s_['稅籍名稱'] for s_ in sorted(sh, key=lambda s_: PRI[s_['型態']])]
    feats.append({'type': 'Feature', 'geometry': mapping(g), 'properties': {
        'kind': 'eatery', 'tier': 'N', 'group': typ, 'bid': b, 'side': side(g), 'area': round(g.area), 'n_shops': len(sh),
        'n_osm': sum(1 for s_ in sh if s_['來源'].startswith('OSM')), 'n_tax_only': sum(1 for s_ in sh if s_['來源'] == '稅籍'),
        'by_type': {t: bt[t] for t in TYPES if bt[t]}, 'by_hours': {h: bh[h] for h in HOURS if bh[h]},
        'names': '、'.join(dict.fromkeys(n for n in names if n))[:160], 'dist_m': round(S.center.distance(g))}})

# ---------- 統計 ----------
IN = [s_ for s_ in detail if s_.get('計入') == '是']
mat = {t: {h: {sd: sum(1 for s_ in IN if s_['型態'] == t and s_['營業時段'] == h and s_['側'] == sd) for sd in ('北', '南')} for h in HOURS} for t in TYPES}
nb = collections.Counter(f['properties']['group'] for f in feats)
nbs = collections.Counter((f['properties']['group'], f['properties']['side']) for f in feats)
ex = collections.Counter(s_['排除原因'] for s_ in detail if s_.get('計入') == '否')
def clean(nm): return re.sub(r'(股份)?有限公司.*$|企業社$|商行$|工作室$', '', nm or '').strip()
def examples(t, n=12):
    # 代表店家：同型態之計入店家；營業時間已知（宵夜、晚餐）優先，其次 OSM 招牌名，稅籍名稱去除公司字尾
    L = [s_ for s_ in IN if s_['型態'] == t]
    L.sort(key=lambda s_: ({'宵夜': 0, '晚餐': 1}.get(s_['營業時段'], 2), 0 if s_['名稱'] else 1))
    out = []
    for s_ in L:
        nm = s_['名稱'] or clean(s_['稅籍名稱'])
        if nm and len(nm) >= 2 and nm not in out: out.append(nm)
        if len(out) >= n: break
    return out
summ = {'zone': ZONE, 'types': [t for t in TYPES if any(mat[t][h][sd] for h in HOURS for sd in ('北', '南'))], 'hours': list(HOURS),
        'matrix': mat, 'shops': len(IN), 'shops_N': sum(1 for s_ in IN if s_['側'] == '北'), 'shops_S': sum(1 for s_ in IN if s_['側'] == '南'),
        'buildings': len(feats), 'buildings_by_type': {t: nb[t] for t in TYPES if nb[t]},
        'buildings_by_type_side': {t: {'北': nbs[(t, '北')], '南': nbs[(t, '南')]} for t in TYPES if nb[t]},
        'by_source': dict(collections.Counter(s_['來源'] for s_ in IN)),
        'hours_known': sum(1 for s_ in IN if s_['營業時段'] != '不明'), 'late': sum(1 for s_ in IN if s_['營業時段'] == '宵夜'),
        'dinner': sum(1 for s_ in IN if s_['營業時段'] == '晚餐'), 'excluded': dict(ex),
        'axis_len_m': S.ZP[ZONE]['len_m'],
        'examples': {t: examples(t) for t in TYPES},
        'source': 'OSM 2026-09-08（03 osm_poi_nodes、臺灣 PBF 餐飲面）；財政部營業（稅籍）登記 2026-10-11（27 門牌定位）'}
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': feats, 'source': summ['source']},
          open(H / f'data/{ZONE}_night_dining_EPSG3826.geojson', 'w'), ensure_ascii=False)
json.dump(summ, open(H / f'data/{ZONE}_night_dining_summary.json', 'w'), ensure_ascii=False, indent=1)
COLS = ['計入', '排除原因', '來源', '型態', '營業時段', '名稱', '稅籍名稱', '行業', 'amenity', 'cuisine', 'opening_hours', '樓層', '側', 'bid', 'OSM', 'E', 'N']
with open(H / f'data/{ZONE}_夜間餐飲_明細.csv', 'w', encoding='utf-8-sig', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=COLS, extrasaction='ignore'); w.writeheader()
    for s_ in sorted(detail, key=lambda s_: (s_.get('計入') != '是', PRI.get(s_.get('型態') or '', 9), s_.get('名稱') or s_.get('稅籍名稱'))): w.writerow(s_)

# ---------- 捷運站體（單元外者亦列，範圍外淡化；比照 Z6 33）----------
LV = {'-1': 'B1', '-2': 'B2', '-3': 'B2'}
mrt = [{'type': 'Feature', 'geometry': f['geometry'], 'properties': {'name': f['properties']['name'], 'level': LV.get(str(f['properties'].get('layer', '-1')), 'B1'),
        'osm_layer': f['properties'].get('layer'), 'area': round(shape(f['geometry']).area)}} for f in OC if f['properties']['kind'] == 'mrt']
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': mrt,
           'note': '比照 Z6（使用者 2026-10-12）：捷運列入，範圍外淡化'}, open(H / f'data/{ZONE}_mrt_ctx_EPSG3826.geojson', 'w'), ensure_ascii=False)
# ---------- 市民大道地下停車場分段（包絡）----------
PK = []
for f in json.load(open(LU / 'parking_streetview_EPSG3826.geojson'))['features']:
    p = f['properties']; g = shape(f['geometry'])
    if p['kind'] == 'section' and g.intersects(zpoly):
        PK.append({'type': 'Feature', 'geometry': f['geometry'], 'properties': {'name': f"市民大道地下停車場（{p['name']}段）", 'section': p['name'], 'levels': p['levels'],
                   'length_m': p['length_m'], 'extent': p['extent_status'], 'share_in_zone': round(g.intersection(zpoly).area / g.area, 2)}})
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': PK,
           'note': '使用者 2026-10-12「算做剪影」：地下停車場列為南北通行元素（B1）；分段包絡為寬 24 m 之比較用外框（非實測）；車道出入口不上圖'},
          open(H / f'data/{ZONE}_ug_parking_EPSG3826.geojson', 'w'), ensure_ascii=False)

print('店家（計入）', len(IN), '｜北', summ['shops_N'], '南', summ['shops_S'], '｜來源', summ['by_source'])
for t in TYPES:
    print(' ', t, {h: mat[t][h] for h in HOURS}, '建物', nb[t])
print('營業時間已知', summ['hours_known'], '（宵夜', summ['late'], '、晚餐', summ['dinner'], '）｜建物', len(feats))
print('不計', dict(ex))
print('捷運站體', [(f['properties']['name'], f['properties']['level']) for f in mrt], '｜地下停車場', [(f['properties']['section'], f['properties']['levels'], f['properties']['share_in_zone']) for f in PK])
