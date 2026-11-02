# 商業空間之密集（Z5 起，使用者 2026-10-12 指定）：標出各種形式的商業空間、周圍已出現之配套措施與可用空地；建國啤酒廠歸類為古蹟
#   使用者原話要點：「這區的重點是找到可用的空地和已經存在的商業空間（大商場、騎樓店家等），然後已有的配套措施（如光華商場旁的步行街）標記出來」
#   範圍：本單元多邊形（高架兩側 300 m）；建物歸屬依 workflow 五-4（跨單元者歸重疊面積最大之單元，01_classify drawing_buildings_zone）
#   一、古蹟：建國啤酒廠（OSM landuse=industrial「建國啤酒廠」範圍內全部建物；使用者指定歸類古蹟，不列商業／工業）
#   二、商業空間（建物，四種形式；依序判定，先符合者為準）：
#     1 大型商場／市場：OSM shop=mall／department_store、amenity=marketplace（面或點落於建物內）
#     2 商業大樓／旅館：OSM building=commercial／retail／hotel、tourism=hotel，或土地使用（01_classify）以「商業」為主（≥ 50%）
#     3 騎樓店面：一樓有實際店面，且臨騎樓（04 騎樓：停管處官方路段或依規則推估，與建物重疊 ≥ 2 m²）
#     4 臨街店面：一樓有實際店面、無騎樓
#     實際店面＝財政部營業（稅籍）登記（27 定位結果）之店面型行業（零售 47／48〔無店面零售 487 除外〕、餐飲 56、個人服務 96、
#       娛樂運動 93、醫療 86），一樓、地下或未載樓層；同一完整地址 ≥ 3 家為借址登記不計（同 27）；與 OSM 店家點（06_industry）取多者。
#       大型商場不限樓層。3C（電腦、通訊、家電零售 4831–4833、474）另計，供光華商圈說明。
#     校園（北科大）建物屬文教，不列。
#   三、配套措施（既有）：
#     步行街／廣場＝OSM 步行區（highway=pedestrian 面／線、place=square）＋商場基地（OSM landuse=retail）內扣除建物與道路之開放鋪面
#       （三創—光華數位新天地之間廣場、希望廣場）；校園內步道不列。公園綠地＝OSM leisure=park。
#     停車場＝北市好停車路外停車場（08；點，汽／機車格）；公車站、YouBike、公廁＝OSM 點。
#   四、可用空地：本單元內扣除路徑（道路＋人行道）、建物（外擴 1 m）、公園、校園、古蹟廠區、宗教用地、商場廣場、施工中基地後之開放地，
#     以 2.5 m 開運算去除建物間細縫與退縮帶，≥ 100 m² 者為候選；另併入 OSM 平面停車場。逐塊以 Ortho_2025（0.6 m/px）判讀（scan 輸出比對圖），
#     判讀結果寫在 DECISIONS：空地（裸地、草地、圍籬內閒置）、平面停車場（空地作臨時停車）＝可用；其餘（中庭、私人前院、機車停放帶等）保留不列。
#     施工中基地（OSM landuse=construction）不列為可用空地，另列於 A4。
#   輸出：data/{Z}_commercial_EPSG3826.geojson（cat＝heritage／commerce／support／vacant／construction；group；名稱與指標）
#   執行：python3 scripts/31_commercial_space.py Z5 scan [比對圖資料夾] → 判讀 → python3 scripts/31_commercial_space.py Z5 apply
import csv, json, re, sys, collections, importlib.util
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import shape, mapping, box, Point
from shapely.ops import unary_union, transform
from shapely.strtree import STRtree
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
ZONE = sys.argv[1] if len(sys.argv) > 1 else 'Z5'
MODE = sys.argv[2] if len(sys.argv) > 2 else 'scan'
spec = importlib.util.spec_from_file_location('sheet', H / 'scripts/02_sheet.py')
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform
LU = H.parents[0] / '03_南京至仁愛_沿線土地使用分析_20261006/data'
IMG = H.parents[0] / '02_南京至仁愛擴幅_20261005'
REB = Path.home() / 'Desktop/Civic_Rebuild_20260909_201934/data'
OUT = H / f'data/{ZONE}_commercial_EPSG3826.geojson'

ZPOLY = {f['properties']['id']: shape(f['geometry']) for f in S.ZF if 'id' in f['properties']}
zpoly = ZPOLY[ZONE]
W = box(*zpoly.buffer(80).bounds)
BL = list(S.bld.geoms)
BZ = {f['properties']['bid']: f['properties']['zone'] for f in json.load(open(LU / 'drawing_buildings_zone_EPSG3826.geojson'))['features']}
ZB = [bid for bid, z in BZ.items() if z == ZONE]
def side(g):
    c = g.representative_point() if g.geom_type != 'Point' else g
    s_ = S.center.project(c); a_ = S.center.interpolate(s_); b_ = S.center.interpolate(min(s_ + 1, S.center.length))
    return '北' if (b_.x - a_.x) * (c.y - a_.y) - (b_.y - a_.y) * (c.x - a_.x) > 0 else '南'

# ---------- OSM ----------
XT = [(shape(f['geometry']), f['properties']) for f in json.load(open(H / 'data/osm_extras_EPSG3826.geojson'))['features']]
XT = [(g, p) for g, p in XT if g.intersects(W) and p.get('place') not in ('subdistrict', 'island', 'suburb', 'quarter', 'city')]
def areas(cond): return [(g.buffer(0), p) for g, p in XT if p['geom'] == 'area' and cond(p)]
BREW = unary_union([g for g, p in areas(lambda p: p.get('landuse') == 'industrial' and p.get('name') == '建國啤酒廠')] or [Point(0, 0).buffer(0)])
CAMPUS = unary_union([g for g, p in areas(lambda p: p.get('amenity') in ('university', 'college', 'school'))] or [Point(0, 0).buffer(0)])
PARKS = [(g, p) for g, p in areas(lambda p: p.get('leisure') == 'park') if g.intersects(zpoly)]
RETAIL = [(g, p) for g, p in areas(lambda p: p.get('landuse') in ('retail',)) if g.intersects(zpoly)]
CONSTR = [(g, p) for g, p in areas(lambda p: p.get('landuse') == 'construction' or p.get('building') == 'construction') if g.intersects(zpoly)]
RELIG = unary_union([g for g, p in areas(lambda p: p.get('landuse') == 'religious' or p.get('amenity') == 'place_of_worship')] or [Point(0, 0).buffer(0)])
SURF = [(g, p) for g, p in areas(lambda p: (p.get('amenity') == 'parking' and p.get('parking', 'surface') == 'surface') or p.get('landuse') == 'garages')
        if g.intersects(zpoly)]
SQUARES = [(g, p) for g, p in areas(lambda p: p.get('place') == 'square' or p.get('highway') == 'pedestrian' or p.get('area:highway') == 'pedestrian')
           if g.intersects(zpoly)]
PEDL = [(g, p) for g, p in XT if p['geom'] == 'line' and p.get('highway') == 'pedestrian' and g.intersects(zpoly)]
NODES = [(g, p) for g, p in XT if p['geom'] == 'node' and zpoly.contains(g)]
osm = json.load(open(S.BASE / 'source/expanded_osm.geojson'))['features']
OSMB = []
for f in osm:
    p = f['properties']
    if f['geometry']['type'] == 'LineString' or 'building' not in p: continue
    g = transform(tf, shape(f['geometry'])).buffer(0)
    if g.intersects(zpoly.buffer(30)): OSMB.append((g, p))
otree = STRtree([g for g, _ in OSMB])
def osm_of(b):
    return [OSMB[i][1] for i in otree.query(b) if OSMB[i][0].intersection(b).area > .3 * b.area]   # OSM 面須覆蓋本棟 30% 以上（小面不代表整棟）

# ---------- 土地使用（01_classify）----------
LUA = collections.defaultdict(collections.Counter)
for f in json.load(open(LU / 'landuse_pieces_EPSG3826.geojson'))['features']:
    p = f['properties']
    if BZ.get(p['bid']) == ZONE: LUA[p['bid']][p['cls_zh']] += p['area']

# ---------- 店面（官方稅籍＋OSM 店家點）----------
FW = str.maketrans('０１２３４５６７８９－―—‐', '0123456789之之之之')
def norm_addr(a):
    return re.sub(r'^(臺|台)北市[^\d]{2}區([^\d路街]{1,3}里)?(\d+鄰)?', '', a.translate(FW).replace(' ', '').replace('　', ''))
def storefront(c): return not c.startswith('487') and c.startswith(('47', '48', '56', '96', '93', '86'))
def is3c(c): return c.startswith(('4831', '4832', '4833', '474'))
ALL = list(csv.DictReader(open(H / 'data/official_shops_geocoded_EPSG3826.csv', encoding='utf-8-sig')))
same = collections.Counter(norm_addr(r['營業地址']) for r in ALL)
zb_geo = [BL[b] for b in ZB]; ztree = STRtree(zb_geo)
def bld_at(pt, snap=6):
    idx = [i for i in ztree.query(pt) if zb_geo[i].contains(pt)]
    if idx: return ZB[idx[0]]
    near = [(zb_geo[i].distance(pt), i) for i in ztree.query(pt.buffer(snap))]
    return ZB[min(near)[1]] if near else None
OFF = collections.defaultdict(list)          # bid → [(行業代號, 樓層, 名稱, 行業)]
n_off_raw = 0
for r in ALL:
    pt = Point(float(r['E']), float(r['N']))
    if not zpoly.buffer(6).contains(pt) or not storefront(r['行業代號']): continue
    n_off_raw += 1
    if same[norm_addr(r['營業地址'])] >= 3: continue                 # 借址登記
    b = bld_at(pt)
    if b is not None: OFF[b].append((r['行業代號'], r['樓層'], r['營業人名稱'], r['名稱']))
POI_IND = ('餐飲', '3C電子', '零售', '便利超市', '生活服務', '夜生活', '運動休閒', '汽機車', '醫療')
OP = collections.defaultdict(collections.Counter)
for f in json.load(open(LU / 'industry_pois_EPSG3826.geojson'))['features']:
    p = f['properties']
    if p['ind'] not in POI_IND: continue
    pt = shape(f['geometry'])
    if not zpoly.buffer(6).contains(pt): continue
    b = bld_at(pt)
    if b is not None: OP[b][p['ind']] += 1

# ---------- 騎樓 ----------
#   第一排街廓：沿用 04（arcade_official／arcade_est）。第二排以後（04 未處理）依 04 同一規則補判：建物臨路徑（道路＋人行道）貼齊
#   （≤ 1.5 m、臨接長 ≥ 3 m），沿境界線向內 3.64 m 之帶狀；停管處「機車退出騎樓路段」含「騎樓」者為官方、標「僅人行道」者不計；
#   無路段資料者，臨 OSM tertiary 以上或具名非巷弄道路、非退縮人行道、非大型公共設施（> 5,000 m²）者推估為騎樓。
import glob, shapefile
ARC = [(shape(f['geometry']), f['properties']['kind']) for f in json.load(open(H / 'data/street_detail_EPSG3826.geojson'))['features']
       if f['properties'].get('kind', '').startswith('arcade') and shape(f['geometry']).intersects(W)]
atree = STRtree([g for g, _ in ARC])
SEC = []
for fn in sorted(glob.glob(str(H / 'data/source_taipei/arcade_*/*.shp'))):
    r_ = shapefile.Reader(fn)
    for s_, rec in zip(r_.shapes(), r_.records()):
        g_ = shape(s_.__geo_interface__).buffer(0); rec = rec.as_dict(); n_ = rec.get('rname') or ''
        if not g_.intersects(W): continue
        SEC.append((g_, True if '騎樓' in n_ else False if '人行道' in n_ else rec.get('motype') == '01', n_))
stree = STRtree([s[0] for s in SEC]) if SEC else None
_SWF = [(shape(f['geometry']).buffer(0), f['properties'].get('code')) for f in json.load(open(REB / 'taipei-sidewalks.geojson'))['features']]
SETBACK = unary_union([g for g, c in _SWF if c == '退縮地' and g.intersects(W)] or [Point(0, 0).buffer(0)])
PATHS0 = unary_union([S.road.intersection(W)] + [g.intersection(W) for g, _ in _SWF if g.intersects(W)])
PB = PATHS0.boundary
DRIVE_MAJOR = {'trunk', 'primary', 'secondary', 'tertiary', 'trunk_link', 'primary_link', 'secondary_link', 'tertiary_link'}
WAYS = [(transform(tf, shape(f['geometry'])), f['properties']) for f in osm if f['geometry']['type'] == 'LineString'
        and f['properties'].get('highway') in DRIVE_MAJOR | {'unclassified', 'residential', 'living_street'}
        and f['properties'].get('bridge') != 'yes' and (f['properties'].get('layer') or '0') == '0']
WAYS = [(g, p) for g, p in WAYS if g.intersects(W)]
wtree = STRtree([g for g, _ in WAYS])
def arcade_of(b):
    hit = [(ARC[i][0].intersection(b.buffer(.5)).area, ARC[i][1]) for i in atree.query(b)]
    hit = [(a, k) for a, k in hit if a >= 2]
    if hit: return '官方' if any(k == 'arcade_official' for _, k in hit) else '推估'
    touch = b.boundary.intersection(PB.buffer(1.5))
    if touch.length < 3: return ''
    piece = b.intersection(touch.buffer(3.64 + 1.5))
    if piece.area < 6: return ''
    probe = piece.buffer(5)
    if stree is not None:
        sh = [(SEC[j][0].intersection(probe).area, j) for j in stree.query(probe)]
        sh = [h for h in sh if h[0] > 2]
        if sh: return '官方' if SEC[max(sh)[1]][1] else ''
    if SETBACK.distance(piece) < 3 or b.area > 5000: return ''
    near = [WAYS[k][1] for k in wtree.query(probe.buffer(20))]
    ok = any(p.get('highway') in DRIVE_MAJOR or (p.get('name') and not re.search('巷|弄', p['name'])) for p in near)
    return '推估' if ok else ''

feats = []
def add(g, **pr):
    if g is not None and not g.is_empty: feats.append({'type': 'Feature', 'geometry': mapping(g), 'properties': pr})
MKT_PTS = [(g, p.get('name', '')) for g, p in NODES if p.get('amenity') == 'marketplace' or p.get('shop') in ('mall', 'department_store')]

# ---------- 一、古蹟／二、商業空間 ----------
GROUPS_K = ('大型商場／市場', '商業大樓／旅館', '騎樓店面', '臨街店面')
for bid in ZB:
    b = BL[bid]
    if b.area < 12: continue
    tags = osm_of(b); names = [t['name'] for t in tags if t.get('name')] + [n_ for q, n_ in MKT_PTS if n_ and b.buffer(2).contains(q)]
    if BREW.contains(b.representative_point()):
        add(b, cat='heritage', group='古蹟', bid=bid, name='建國啤酒廠：' + ('、'.join(dict.fromkeys(names)) or '廠房（OSM 未具名）'),
            note='使用者 2026-10-12 指定歸類古蹟（臺北市定古蹟，仍在生產）', side=side(b), area=round(b.area))
        continue
    if CAMPUS.contains(b.representative_point()): continue
    lu = LUA.get(bid, collections.Counter()); tot = sum(lu.values()) or 1
    com_share = lu.get('商業（零售／餐飲／旅館）', 0) / tot
    mall = any(t.get('shop') in ('mall', 'department_store') or t.get('amenity') == 'marketplace' for t in tags) or any(b.buffer(2).contains(q) for q, _ in MKT_PTS)
    combld = any(t.get('building') in ('commercial', 'retail', 'hotel') or t.get('tourism') == 'hotel' for t in tags) or com_share >= .5
    offs = OFF.get(bid, [])
    ground = [o for o in offs if o[1] in ('1F', 'B', '未載')]
    n_off = len(offs) if mall else len(ground)
    n_osm = sum(OP.get(bid, collections.Counter()).values())
    n_front = max(n_off, n_osm)
    n3c = sum(1 for o in (offs if mall else ground) if is3c(o[0]))
    arc = arcade_of(b)
    if mall: grp = '大型商場／市場'
    elif combld: grp = '商業大樓／旅館'
    elif n_front >= 1: grp = '騎樓店面' if arc else '臨街店面'
    else: continue
    top = collections.Counter(o[3] for o in (offs if mall else ground)).most_common(3)
    add(b, cat='commerce', group=grp, bid=bid, name='、'.join(dict.fromkeys(names)), side=side(b), area=round(b.area),
        n_front=n_front, n_official=n_off, n_osm=n_osm, n_3c=n3c, arcade=arc, com_share=round(com_share, 2),
        osm_tags='；'.join(sorted({f"{k}={t[k]}" for t in tags for k in ('shop', 'amenity', 'building', 'tourism') if t.get(k) and t.get(k) != 'yes'})),
        top='、'.join(f'{k} {v}' for k, v in top), d_axis=round(S.center.distance(b)))

# ---------- 三、配套措施 ----------
bldW = S.bld.intersection(W.buffer(10))
def campus_free(g): return g.difference(CAMPUS)
plaza = []
for g, p in RETAIL:
    q = g.intersection(zpoly.buffer(20)).difference(bldW.buffer(.3)).difference(S.road)
    q = q.buffer(-1).buffer(1)
    for pc in S.polys(q):
        if pc.area >= 40: plaza.append((pc, (p.get('name') or '商場基地') + '：開放廣場'))
for g, p in SQUARES:
    q = campus_free(g).difference(bldW)
    for pc in S.polys(q):
        if pc.area >= 20: plaza.append((pc, p.get('name') or ('廣場' if p.get('place') == 'square' else '步行區')))
for g, p in PEDL:
    q = campus_free(g.buffer(3, cap_style='flat')).difference(bldW)
    if q.area >= 20: plaza.append((q, p.get('name') or '步行道'))
PLAZA_U = unary_union([g for g, _ in plaza]) if plaza else Point(0, 0).buffer(0)
for g, nm in plaza:
    add(g, cat='support', group='步行街／廣場', name=nm, area=round(g.area), side=side(g))
for g, p in PARKS:
    q = g.intersection(zpoly.buffer(10)).difference(bldW)
    if q.area >= 20: add(q, cat='support', group='公園綠地', name=p.get('name', '公園'), area=round(q.area), side=side(q))
for f in json.load(open(LU / 'parking_pma_EPSG3826.geojson'))['features']:
    p = f['properties']
    if p.get('zone') != ZONE or p.get('kind') != 'lot': continue
    add(shape(f['geometry']), cat='support', group='停車場', name=p['name'], addr=p['addr'], car=p['car'], moto=p['moto'], op=p['type'],
        side=side(shape(f['geometry'])))
n_curb = sum(1 for f in json.load(open(LU / 'parking_pma_EPSG3826.geojson'))['features'] if f['properties'].get('zone') == ZONE and f['properties'].get('kind') == 'curb')
seen = []
for g, p in NODES:
    if p.get('highway') == 'bus_stop' or (p.get('public_transport') == 'platform' and p.get('bus') == 'yes'):
        nm = p.get('name', '公車站')
        if any(nm == n_ and g.distance(g_) < 40 for n_, g_ in seen): continue
        seen.append((nm, g)); add(g, cat='support', group='公車站', name=nm, side=side(g))
    elif p.get('amenity') == 'bicycle_rental':
        add(g, cat='support', group='YouBike', name=p.get('name', 'YouBike'), cap=p.get('capacity', ''), side=side(g))
    elif p.get('amenity') == 'toilets':
        add(g, cat='support', group='公廁', name=p.get('name', '公廁'), side=side(g))

# ---------- 施工中 ----------
CON_U = unary_union([g for g, _ in CONSTR]) if CONSTR else Point(0, 0).buffer(0)
for g, p in CONSTR:
    add(g.intersection(zpoly.buffer(10)), cat='construction', group='施工中', name=p.get('name', '施工中基地'), area=round(g.area), side=side(g))

# ---------- 四、可用空地：候選 ----------
SW = unary_union([shape(f['geometry']).buffer(0) for f in json.load(open(REB / 'taipei-sidewalks.geojson'))['features'] if shape(f['geometry']).intersects(W)])
PATHS = unary_union([S.road.intersection(W), SW.intersection(W)])
EXCL = unary_union([PATHS, bldW.buffer(1.0), unary_union([g for g, _ in PARKS] or [Point(0, 0).buffer(0)]), CAMPUS, BREW, RELIG, PLAZA_U, CON_U])
open_ = zpoly.difference(EXCL).buffer(-2.5).buffer(2.5).intersection(zpoly)
cand = [pc for pc in S.polys(open_) if pc.area >= 100]
for g, p in SURF:   # OSM 平面停車場（併入候選；與開放地重疊者合併）
    q = g.intersection(zpoly).difference(bldW).difference(PATHS)
    if q.area < 50: continue
    hit = [i for i, c in enumerate(cand) if c.intersects(q)]
    merged = unary_union([q] + [cand[i] for i in hit])
    cand = [c for i, c in enumerate(cand) if i not in hit] + S.polys(merged.buffer(0))
cand = [c for c in cand if c.area >= 100]
def tags_near(c):
    # 候選附近之停車場名稱（OSM 平面停車場名稱、停管處路外停車場名稱）；同名異寫（2段／二段）去重
    t = [p.get('name') for g, p in SURF if g.intersection(c).area > .2 * min(g.area, c.area)]
    t += [f['properties']['name'] for f in json.load(open(LU / 'parking_pma_EPSG3826.geojson'))['features']
          if f['properties'].get('zone') == ZONE and f['properties'].get('kind') == 'lot' and shape(f['geometry']).distance(c) < 12]
    out, seen = [], set()
    for x in t:
        k_ = re.sub(r'(\d)段', lambda m: '一二三四五六七八九'[int(m.group(1)) - 1] + '段', x or '')
        if x and k_ not in seen: seen.add(k_); out.append(x)
    return '、'.join(out)

MAN = json.load(open(IMG / 'imagery_manifest.json'))['images']
_cache = {}
def chip(b, px=0.3):
    x0, y0, x1, y1 = b; W_ = int((x1 - x0) / px); H_ = int((y1 - y0) / px)
    out = Image.new('RGB', (max(W_, 1), max(H_, 1)), 'white')
    for m in MAN:
        bx = m['bbox']
        if bx[2] < x0 or bx[0] > x1 or bx[3] < y0 or bx[1] > y1: continue
        if m['file'] not in _cache: _cache[m['file']] = Image.open(IMG / 'imagery' / m['file']).convert('RGB')
        im = _cache[m['file']]; sx = im.width / (bx[2] - bx[0]); sy = im.height / (bx[3] - bx[1])
        cx0, cx1 = max(x0, bx[0]), min(x1, bx[2]); cy0, cy1 = max(y0, bx[1]), min(y1, bx[3])
        if cx0 >= cx1 or cy0 >= cy1: continue
        c = im.crop((int((cx0 - bx[0]) * sx), int((bx[3] - cy1) * sy), int((cx1 - bx[0]) * sx), int((bx[3] - cy0) * sy)))
        c = c.resize((max(1, int((cx1 - cx0) / px)), max(1, int((cy1 - cy0) / px))))
        out.paste(c, (int((cx0 - x0) / px), int((y1 - cy1) / px)))
    return out

def bare_frac(p):
    # 空照淺褐裸土／碎石像素比例（Ortho_2025，0.3 m 取樣）
    b = p.bounds; im = np.asarray(chip(b, .3)).astype(float)
    mask = Image.new('L', (im.shape[1], im.shape[0]), 0); dr = ImageDraw.Draw(mask)
    to = lambda c: ((c[0] - b[0]) / .3, (b[3] - c[1]) / .3)
    for pc in S.polys(p):
        dr.polygon([to(c) for c in pc.exterior.coords], fill=255)
        for r in pc.interiors: dr.polygon([to(c) for c in r.coords], fill=0)
    m = np.asarray(mask) > 0
    if m.sum() < 20: return 0.0
    R, G, B = im[..., 0][m], im[..., 1][m], im[..., 2][m]
    return float(((R > 140) & (R - B > 18) & (R - B < 70) & (G - B > 8) & (np.abs(R - G) < 30)).mean())
# 線稿建物較 2025 空照舊：已拆除之基地在線稿仍為建物（例：八德路二段臨時平面停車場）。
#   線稿建物扣除 OSM 建物後之殘餘（2.5 m 開運算、≥ 100 m²）且空照裸土比例 ≥ 30% 者，亦列為候選（疑似已拆除）
OSMBU = unary_union([g for g, _ in OSMB])
for bid in ZB:
    b = BL[bid]
    if b.area < 100 or BREW.contains(b.representative_point()) or CAMPUS.contains(b.representative_point()): continue
    r_ = b.difference(OSMBU.buffer(.5)).buffer(-2.5).buffer(2.5)
    for pc in S.polys(r_):
        if pc.area >= 100 and bare_frac(pc) >= .3:
            hit = [i for i, c in enumerate(cand) if c.buffer(1.5).intersects(pc)]
            merged = unary_union([pc] + [cand[i] for i in hit]).buffer(1.5).buffer(-1.5)
            cand = [c for i, c in enumerate(cand) if i not in hit] + S.polys(merged)
cand = sorted([c for c in cand if c.area >= 100], key=lambda c: c.centroid.x)

if MODE == 'scan':
    SP = Path(sys.argv[3]) if len(sys.argv) > 3 else H / 'data'
    font = ImageFont.truetype('/System/Library/Fonts/Hiragino Sans GB.ttc', 14)
    tiles = []
    for i, p in enumerate(cand):
        c = p.centroid; half = max(25, max(p.bounds[2] - p.bounds[0], p.bounds[3] - p.bounds[1]) * .75)
        b = (c.x - half, c.y - half, c.x + half, c.y + half)
        im = chip(b, half * 2 / 300).resize((300, 300)); dr = ImageDraw.Draw(im)
        to = lambda q: ((q[0] - b[0]) / (2 * half) * 300, (b[3] - q[1]) / (2 * half) * 300)
        for pg in S.polys(bldW.intersection(box(*b))): dr.line([to(q) for q in pg.exterior.coords], fill=(255, 255, 255), width=1)
        for pc in S.polys(p): dr.line([to(q) for q in pc.exterior.coords], fill=(255, 0, 255), width=3)
        dr.rectangle([0, 0, 300, 36], fill='white')
        dr.text((3, 1), f"#{i + 1} {p.area:.0f}m² {side(p)}側 E{c.x:.0f} N{c.y:.0f}", fill='black', font=font)
        dr.text((3, 18), tags_near(p)[:24], fill=(0, 0, 160), font=font)
        tiles.append(im)
    cols = 5
    for k in range(0, len(tiles), 20):
        part = tiles[k:k + 20]; n = (len(part) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * 304, n * 304), 'white')
        for j, t in enumerate(part): sheet.paste(t, ((j % cols) * 304, (j // cols) * 304))
        sheet.save(SP / f'{ZONE}_vacant_{k // 20 + 1}.jpg', quality=88)
    print('vacant candidates', len(cand), 'sheets', (len(tiles) + 19) // 20)

# ---------- 可用空地判讀（依單元；編號依候選形心由西向東，基圖變動須重新 scan）----------
DECISIONS = {}
# Z5（2026-10-12，依 Ortho_2025 逐塊比對；59 塊）。未列者保留不計：
#   路面（線稿缺道路面）#1、2、3、6、11、24、25、26、28、35、36、38、40、53–59；空照為建物（線稿或 OSM 缺建物）#5、10、17、19、20、23、29、31、34、49；
#   中庭、前院、建物間細縫、私人停車角落 #4、9、13–16、21、22、27、30、37、39、41–48、50–52；街角鋪面 #8；施工中 #32（華山松江）
DECISIONS['Z5'] = {
    7: ('空地', '空照為植被覆蓋之閒置地（三面為建物、空照未見建物；待現勘確認權屬與使用）'),
    12: ('平面停車場', 'Times 長安新生停車場、長安 36 停車場（停管處登錄地址「長安東路 2 段 36 巷 16 號邊空地」）：空地作平面停車'),
    18: ('平面停車場', '新生高架旁長條平面停車：公營「新生高架（松江—金山北）橋外」停車場、中山分局警備隊專用停車場等'),
    33: ('平面停車場', '八德路二段臨時平面停車場（公營，汽 12／機 12）：空照為裸土，線稿仍為建物（已拆除）'),
}
VACANT = DECISIONS.get(ZONE, {})
for i, p in enumerate(cand):
    d = VACANT.get(i + 1)
    if d is None: continue
    kind, why = d
    if kind == 'keep': continue
    add(p, cat='vacant', group=kind, id_scan=i + 1, name=tags_near(p) or ('閒置地（OSM 未標示）' if kind == '空地' else kind), reason=why, area=round(p.area), side=side(p))

# 已拆除基地：商業空間、古蹟建物扣除可用空地（線稿建物涵蓋已拆除部分者，如八德路二段臨時平面停車場之 B3416）
VU = unary_union([shape(f['geometry']) for f in feats if f['properties']['cat'] == 'vacant'] or [Point(0, 0).buffer(0)])
for f in feats:
    if f['properties']['cat'] in ('commerce', 'heritage'):
        g = shape(f['geometry'])
        if g.intersects(VU) and g.intersection(VU).area > 1:
            g2 = g.difference(VU.buffer(.2)); f['geometry'] = mapping(g2); f['properties']['area'] = round(g2.area); f['properties']['note_vacant'] = '已扣除已拆除部分（空照為空地）'
# ---------- 輸出 ----------
st = collections.Counter((f['properties']['cat'], f['properties']['group']) for f in feats)
K = [f['properties'] for f in feats if f['properties']['cat'] == 'commerce']
stats = {'zone': ZONE, 'counts': {f'{a}|{b}': v for (a, b), v in st.items()},
         'storefronts': sum(p['n_front'] for p in K), 'n_3c': sum(p['n_3c'] for p in K), 'official_storefront_raw': n_off_raw,
         'curb_spaces': n_curb, 'vacant_candidates': len(cand),
         'parking_car': sum(f['properties'].get('car') or 0 for f in feats if f['properties']['group'] == '停車場'),
         'parking_moto': sum(f['properties'].get('moto') or 0 for f in feats if f['properties']['group'] == '停車場')}
if MODE == 'apply' or not OUT.exists():
    json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': feats, 'stats': stats,
               'source': 'OSM 2026-09-08（29_osm_extras、expanded_osm）；財政部營業（稅籍）登記 2026-10-11（27 定位）；北市好停車（08）；04 騎樓；Ortho_2025'},
              open(OUT, 'w'), ensure_ascii=False)
print(dict(st)); print({k: v for k, v in stats.items() if k != 'counts'})
for grp in GROUPS_K:
    L = sorted([p for p in K if p['group'] == grp], key=lambda p: -p['n_front'])
    print(grp, len(L), '｜', '；'.join(f"{p['name'] or 'bid' + str(p['bid'])}（店 {p['n_front']}、3C {p['n_3c']}{'、騎樓' + p['arcade'] if p['arcade'] else ''}）" for p in L[:8]))
