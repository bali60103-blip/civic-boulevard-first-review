# 運動生活空間：住宅戶數＋運動場（Z4 起；使用者 2026-10-12 指定「Z4 主軸＝運動生活空間，調查周圍的住宅數量和運動場面積涵蓋的運動種類」）
#   一、住宅
#     戶數＝內政部戶政司「村里戶數、單一年齡人口」（115 年 9 月，data/source_moi/village_households/）× 各里落在本單元之住宅樓地板比例。
#       里界＝內政部地政司「村里界歷史圖資」114 年版（VILLAGE_NLSC_11401031；TWD97 經緯度 → EPSG:3826）。
#       住宅樓地板＝01_classify 土地使用「住宅」「一樓店面（住宅／街屋）」（扣一樓）「未標示／待調查」逐片 × 樓層
#         （臺北三維模型 2017 量體高度 ÷ 3.3 取整；未覆蓋部分以 OSM 樓層，無則 1 層）。未標示計入：正守里 56% 建物未標示，多為住宅。
#       建物歸屬單元依 workflow 五-4（drawing_buildings_zone）；建物歸屬里依代表點。另列四種權重之結果作為區間。
#     圖面「住宅建物」＝本單元內主要用途為住宅或一樓店面（住宅／街屋）之建物（未標示者不上色）。
#   二、運動場
#     OSM（臺灣 PBF 2026-09-08）leisure＝pitch／track／fitness_station／sports_centre／stadium／swimming_pool／playground 及具 sport 標籤者；
#       種類依 sport 標籤，面積＝OSM 面（點位無面積，圖上以直徑 6 m 圓點示意）。逐處以 Ortho_2025 空照核對（AERIAL）。
#     範圍內＝與本單元多邊形重疊面積最大者（同 workflow 五-4）；鄰近＝本單元外 150 m 內（含相鄰單元、學校）。機關圍牆內不開放者另列、不計入合計。
#     另列：公園（OSM leisure=park，本單元內面積）、環狀步道、稅籍登記之運動服務業（無面積，僅家數）。
#   輸出（後台）：data/{Z}_sports_housing_EPSG3826.geojson（17 讀）、data/{Z}_運動場_明細.csv、data/{Z}_運動場_種類統計.csv、
#     data/{Z}_住宅_里別戶數.csv、data/{Z}_sports_housing_summary.json（20 讀，圖面結果區塊）
#   執行：python3 scripts/30_sports_housing.py Z4（首次執行自 PBF 擷取運動設施，約 6 分鐘，快取於 data/osm_sports_4326.geojson）
import json, sys, csv, collections, importlib.util
from pathlib import Path
from shapely.geometry import shape, mapping, Point, box
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
ZONE = sys.argv[1] if len(sys.argv) > 1 else 'Z4'
spec = importlib.util.spec_from_file_location('sheet', H / 'scripts/02_sheet.py')
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
S.VARIANT['full'] = True
LU = H.parents[0] / '03_南京至仁愛_沿線土地使用分析_20261006/data'
MOI = H / 'data/source_moi'
PBF = Path.home() / 'Downloads/taiwan-260908.osm.pbf'
CACHE = H / 'data/osm_sports_4326.geojson'
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform
tf97 = Transformer.from_crs(3824, 3826, always_xy=True).transform
ADJ_D = 150            # 鄰近：本單元外 150 m 內
PT_R = 3.0             # 點位示意半徑（m）

# ---------- 0. OSM 運動設施快取（走廊範圍，同 03_南京至仁愛 00_extract_pbf 之 BB）----------
W_, S_, E_, N_ = 121.5037528384707, 25.034315313146706, 121.57135791788014, 25.061191902246893
LEI = {'pitch', 'sports_centre', 'fitness_centre', 'fitness_station', 'track', 'stadium', 'swimming_pool', 'playground', 'park',
       'sports_hall', 'ice_rink', 'garden', 'recreation_ground', 'dance', 'miniature_golf'}
def extract_osm():
    import osmium
    from osmium.geom import GeoJSONFactory
    gf = GeoJSONFactory(); out = []
    def keep(t):
        return (t.get('leisure') in LEI or 'sport' in t or t.get('amenity') in ('school', 'university', 'college', 'kindergarten')
                or t.get('landuse') == 'recreation_ground')
    for o in osmium.FileProcessor(str(PBF)).with_locations().with_areas():
        t = dict(o.tags) if hasattr(o, 'tags') else {}
        if not t or not keep(t): continue
        try:
            if o.is_node():
                if not (W_ <= o.location.lon <= E_ and S_ <= o.location.lat <= N_): continue
                g = gf.create_point(o); kind, oid = 'n', o.id
            elif o.is_area():
                g = gf.create_multipolygon(o); c = json.loads(g)['coordinates'][0][0][0]
                if not (W_ <= c[0] <= E_ and S_ <= c[1] <= N_): continue
                kind, oid = ('w' if o.from_way() else 'r'), o.orig_id()
            else: continue
        except Exception: continue
        out.append({'type': 'Feature', 'geometry': json.loads(g), 'properties': dict(t, _osm=f'{kind}{oid}')})
    json.dump({'type': 'FeatureCollection', 'features': out, 'source': f'{PBF.name}（pyosmium 擷取）'}, open(CACHE, 'w'), ensure_ascii=False)
if not CACHE.exists(): extract_osm()
OSM = []
for f in json.load(open(CACHE))['features']:
    g = transform(tf, shape(f['geometry']))
    OSM.append((g if g.is_valid else g.buffer(0), f['properties']))

ZP_ = {f['properties']['id']: shape(f['geometry']) for f in S.ZF if 'id' in f['properties']}
ZPOLY = ZP_[ZONE]
def side(g):
    c = g.representative_point(); s_ = S.center.project(c); a = S.center.interpolate(s_); b = S.center.interpolate(min(s_ + 1, S.center.length))
    return 'N' if (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x) > 0 else 'S'
def owner(g):   # workflow 五-4：重疊面積最大之單元（點：所在單元）
    if g.area == 0: return next((z for z, p in ZP_.items() if p.contains(g)), None)
    ov = {z: g.intersection(p).area for z, p in ZP_.items() if g.intersects(p)}
    return max(ov, key=ov.get) if ov else None

# ---------- 一、運動場 ----------
SPORT_ZH = {'basketball': '籃球', 'tennis': '網球', 'volleyball': '排球', 'badminton': '羽球', 'badtim': '羽球', 'skateboard': '滑板',
            'running': '跑道', 'athletics': '跑道', 'fitness': '體健設施', 'table_tennis': '桌球', 'soccer': '足球', 'baseball': '棒壘球',
            'softball': '棒壘球', 'multi': '多功能球場', 'swimming': '游泳', 'roller_skating': '直排輪', 'futsal': '足球'}
LEI_ZH = {'fitness_station': '體健設施', 'playground': '兒童遊戲場', 'track': '跑道', 'swimming_pool': '游泳', 'sports_centre': '運動中心',
          'stadium': '運動場', 'sports_hall': '運動中心', 'pitch': '球場（未標種類）'}
# Ortho_2025 空照逐處核對（2026-10-12；02_南京至仁愛擴幅/imagery，0.6 m/px）。未列者＝「依 OSM（未逐處核對）」
AERIAL = {
 'Z4': {
  'w1454572604': ('確認', '華山公園（北側帶狀公園）內綠色硬鋪球場，空照可見'),
  'w1454427460': ('確認', '中央藝文公園西北角 L 形器材區，空照可見'),
  'r17935100':   ('確認', '中央藝文公園共融遊戲場，鋪面與遊具可見'),
  'n7081477577': ('依 OSM', '華山公園內點位，樹冠遮蔽，空照無法確認'),
  'n11311415382': ('依 OSM', '華山公園內點位，樹冠遮蔽，空照無法確認'),
  'w345998870':  ('依 OSM', '新生高架橋下，橋面遮蔽，空照無法確認'),
  'w345998871':  ('依 OSM', '新生高架橋下，橋面遮蔽，空照無法確認'),
  'n2575892486': ('依 OSM', '新生高架橋下點位，橋面遮蔽'),
  'r6075185':    ('確認', '長安國小 200 m 跑道，空照可見'),
  'w405334207':  ('確認', '長安國小跑道內場排球場'), 'w405334212': ('確認', '長安國小跑道內場排球場'),
  'w405334210':  ('確認', '長安國小跑道內場羽球場'), 'w405334213': ('確認', '長安國小跑道內場羽球場'),
  'w405334214':  ('確認', '長安國中籃球場（藍色硬鋪）'), 'w405334216': ('確認', '長安國中籃球場（藍色硬鋪）'),
  'w405334211':  ('確認', '忠孝國小籃球場'), 'w405334206': ('確認', '忠孝國小籃球場'),
  'w267170904':  ('確認・不開放', '機關圍牆內球場（林森南路西側），非公共運動場'),
  'w267170905':  ('確認・不開放', '機關圍牆內網球場（林森南路西側），非公共運動場'),
 }}.get(ZONE, {})
NOT_PUBLIC = {k for k, (v, _) in AERIAL.items() if '不開放' in v}
HOSTS = [(g, p) for g, p in OSM if g.geom_type in ('Polygon', 'MultiPolygon') and p.get('name')
         and (p.get('leisure') in ('park', 'garden') or p.get('amenity') in ('school', 'university', 'college', 'kindergarten'))]
def host_of(g):
    c = g.representative_point()
    hs = sorted([(h.area, p) for h, p in HOSTS if h.buffer(1).contains(c)], key=lambda t: t[0])
    if hs: return hs[0][1]['name'], ('學校（課後開放）' if hs[0][1].get('amenity') else '公園')
    if g.buffer(2).intersects(S.deck) or any(g.buffer(2).intersects(q) for q in BRIDGES): return '新生高架橋下', '高架橋下'
    return '', ''
_osm_roads = json.load(open(S.BASE / 'source/expanded_osm.geojson'))['features']
BRIDGES = [transform(tf, shape(f['geometry'])).buffer(8) for f in _osm_roads
           if f['geometry']['type'] == 'LineString' and f['properties'].get('bridge') == 'yes' and '新生' in (f['properties'].get('name') or '')]
sports = []
for g, p in OSM:
    lei = p.get('leisure')
    if lei in ('park', 'garden', 'fitness_centre', 'dance') or (lei is None and 'sport' not in p): continue
    if p.get('amenity') in ('school', 'university', 'college', 'kindergarten'): continue
    d = g.distance(ZPOLY)
    if d > ADJ_D: continue
    sp = p.get('sport', '')
    typ = '、'.join(dict.fromkeys(SPORT_ZH.get(s.strip(), s.strip()) for s in sp.split(';') if s.strip())) if sp else LEI_ZH.get(lei, lei or '')
    if lei == 'playground': typ = '兒童遊戲場'
    own = owner(g); scope = '範圍內' if own == ZONE else '鄰近'
    hn, hk = host_of(g)
    ver, vnote = AERIAL.get(p['_osm'], ('依 OSM', '未逐處核對'))
    pub = p['_osm'] not in NOT_PUBLIC
    gd = g if g.area > 0 else g.buffer(PT_R)
    sports.append(dict(osm=p['_osm'], g=gd, typ=typ, area=round(g.area), scope=scope, owner=own or '範圍外', host=hn, host_kind=hk if pub else '機關（不開放）',
                       public=pub, side=side(g), dist=round(S.center.distance(g)), aerial=ver, aerial_note=vnote, name=p.get('name', ''), point=g.area == 0))
sports.sort(key=lambda r: (r['scope'] != '範圍內', r['typ'], -r['area']))
for i, r in enumerate(sports, 1): r['id'] = f'P{i:02d}'
# 公園（本單元內面積）與環狀步道
parks = []
for g, p in OSM:
    if p.get('leisure') != 'park' or not p.get('name') or not g.intersects(ZPOLY): continue
    a_in = g.intersection(ZPOLY).area
    if a_in < 100: continue
    parks.append(dict(name=p['name'], area=round(a_in), area_all=round(g.area), side=side(g), osm=p['_osm']))
parks.sort(key=lambda r: -r['area'])
LOOPS = {'Z4': [('中央藝文公園環狀步道', 350, 'OSM footway 347314123（北側弧段 201 m）＋448227622 南側直段約 146 m；環繞開放草坪，可散步、慢跑')]}.get(ZONE, [])
# 稅籍登記之運動服務業（27 已定位；無面積）
shops_sport = collections.Counter(); shops_list = []
_sf = H / 'data/official_shops_geocoded_EPSG3826.csv'
if _sf.exists():
    for r in csv.DictReader(open(_sf, encoding='utf-8-sig')):
        cs = [c for c in (r['行業代號'], r['行業代號1']) if c]
        if not r['E'] or not any(c.startswith(('9312', '9311', '9319', '859399')) for c in cs): continue
        if not ZPOLY.contains(Point(float(r['E']), float(r['N']))): continue
        k = '運動場館／健身（9312）' if any(c.startswith('9312') for c in cs) else '其他運動服務、運動教育（9311、9319、8593）'
        shops_sport[k] += 1; shops_list.append((r['營業人名稱'], r['名稱'], r['樓層']))

# ---------- 二、住宅 ----------
BL = list(S.bld.geoms)
BZ = {f['properties']['bid']: f['properties']['zone'] for f in json.load(open(LU / 'drawing_buildings_zone_EPSG3826.geojson'))['features']}
import shapefile
rd = shapefile.Reader(str(MOI / 'village_boundary/extracted/VILLAGE_NLSC_11401031'), encoding='utf-8')
VIL = {}
for sr in rd.iterShapeRecords():
    a = sr.record.as_dict()
    if a['COUNTYNAME'] != '臺北市': continue
    g = transform(tf97, shape(sr.shape.__geo_interface__)).buffer(0)
    if g.intersects(ZPOLY.buffer(-1)): VIL[a['VILLCODE']] = (a['TOWNNAME'], a['VILLNAME'], g)
HH = {}
for r in csv.DictReader(open(MOI / 'village_households/opendata11509M030.csv', encoding='utf-8-sig')):
    if r['區域別代碼'] in VIL:
        age = lambda lo, hi: sum(int(r[f'{a}歲-{s}'] or 0) for a in range(lo, hi + 1) for s in ('男', '女'))
        a100 = sum(int(r[k] or 0) for k in r if k.startswith('100歲以上'))
        HH[r['區域別代碼']] = dict(hh=int(r['戶數']), pop=int(r['人口數']), a0=age(0, 14), a15=age(15, 64), a65=age(65, 99) + a100, ym=r['統計年月'])
T3 = []
for f in json.load(open(H.parents[1] / '02_調整過程/歷次處理與版本紀錄/過程_臺北三維參照/civic_approximate_buildings_wgs84.geojson'))['features']:
    if f['properties'].get('height'): T3.append((transform(tf, shape(f['geometry'])).buffer(0), float(f['properties']['height'])))
t3 = STRtree([g for g, _ in T3])
def floor_area(q, lv):
    parts = [(T3[j][0].intersection(q), T3[j][1]) for j in t3.query(q)]
    parts = [(x, h) for x, h in parts if not x.is_empty and x.area > .5]
    cov = sum(x.area for x, _ in parts)
    return sum(x.area * max(1, round(h / 3.3)) for x, h in parts) + max(0, q.area - cov) * (lv or 1)
RES, SHOP, UNK = '住宅', '一樓店面（住宅／街屋）', '未標示／待調查'
vpolys = [(c, g) for c, (_, _, g) in VIL.items()]
def vil_of(pt): return next((c for c, g in vpolys if g.contains(pt)), None)
bstat = collections.defaultdict(lambda: {'cls': collections.Counter(), 'res': 0.0, 'unk': 0.0, 'resfp': 0.0, 'unkfp': 0.0, 'lv': 0})
for f in json.load(open(LU / 'landuse_pieces_EPSG3826.geojson'))['features']:
    p = f['properties']; q = shape(f['geometry'])
    if not any(g.intersects(q) for _, g in vpolys): continue
    b = bstat[p['bid']]; b['cls'][p['cls_zh']] += q.area
    if p['levels']: b['lv'] = max(b['lv'], p['levels'])
    if p['cls_zh'] in (RES, SHOP, UNK):
        fa = floor_area(q, p['levels'])
        if p['cls_zh'] == RES: b['res'] += fa; b['resfp'] += q.area
        elif p['cls_zh'] == SHOP: b['res'] += max(0.0, fa - q.area); b['resfp'] += q.area
        else: b['unk'] += fa; b['unkfp'] += q.area
agg = {c: collections.Counter() for c in VIL}
houses = []
for bid, b in bstat.items():
    bg = BL[bid]; c = vil_of(bg.representative_point())
    if c is None: continue
    tag = 'in' if BZ.get(bid) == ZONE else 'out'; sd = side(bg)
    A = agg[c]
    A[('w', tag)] += b['res'] + b['unk']; A[('rfa', tag)] += b['res']; A[('rfp', tag)] += b['resfp']; A[('rufp', tag)] += b['resfp'] + b['unkfp']
    if tag == 'in': A[('w', sd)] += b['res'] + b['unk']
    main = b['cls'].most_common(1)[0][0] if b['cls'] else ''
    if tag == 'in' and main in (RES, SHOP):
        houses.append(dict(bid=bid, g=bg, main=main, side=sd, res_fa=round(b['res']), village=VIL[c][1], levels=b['lv']))
unk_in = sum(1 for bid, b in bstat.items() if BZ.get(bid) == ZONE and b['cls'] and b['cls'].most_common(1)[0][0] == UNK)
rows_v = []; tot = collections.Counter(); alt = collections.Counter()
for c, (town, vn, g) in sorted(VIL.items(), key=lambda kv: -kv[1][2].intersection(ZPOLY).area):
    A = agg[c]; h = HH[c]
    sh = lambda k: A[(k, 'in')] / (A[(k, 'in')] + A[(k, 'out')]) if (A[(k, 'in')] + A[(k, 'out')]) else 0.0
    w = sh('w'); wn = A[('w', 'N')] / A[('w', 'in')] if A[('w', 'in')] else 0.0
    ws = {'里面積': g.intersection(ZPOLY).area / g.area, '住宅建築面積': sh('rfp'), '住宅樓地板': sh('rfa'), '住宅＋未標示建築面積': sh('rufp'), '住宅＋未標示樓地板（採用）': w}
    for k, v in ws.items(): alt[k] += h['hh'] * v
    r = dict(區=town, 里=vn, 里代碼=c, 戶數=h['hh'], 人口=h['pop'], 權重=round(w, 3), 分配戶數=round(h['hh'] * w), 分配人口=round(h['pop'] * w),
             北側戶數=round(h['hh'] * w * wn), 南側戶數=round(h['hh'] * w * (1 - wn)), **{f'權重_{k}': round(v, 3) for k, v in ws.items() if '採用' not in k})
    rows_v.append(r)
    for k, v in (('hh', h['hh'] * w), ('pop', h['pop'] * w), ('N', h['hh'] * w * wn), ('S', h['hh'] * w * (1 - wn)),
                 ('a0', h['a0'] * w), ('a15', h['a15'] * w), ('a65', h['a65'] * w)): tot[k] += v
YM = next(iter(HH.values()))['ym']

# ---------- 輸出 ----------
feats = []
for r in sports:
    feats.append({'type': 'Feature', 'geometry': mapping(r['g']), 'properties': {k: v for k, v in r.items() if k != 'g'} | {'kind': 'sport'}})
for r in houses:
    feats.append({'type': 'Feature', 'geometry': mapping(r['g']), 'properties': {k: v for k, v in r.items() if k != 'g'} | {'kind': 'housing'}})
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': feats},
          open(H / f'data/{ZONE}_sports_housing_EPSG3826.geojson', 'w'), ensure_ascii=False)
with open(H / f'data/{ZONE}_運動場_明細.csv', 'w', encoding='utf-8-sig', newline='') as fo:
    w_ = csv.writer(fo)
    w_.writerow(['編號', '種類', '面積_m2', '範圍', '歸屬單元', '所在', '所在類型', '開放', '側', '距軸線_m', '空照核對', '核對說明', 'OSM'])
    for r in sports:
        w_.writerow([r['id'], r['typ'], r['area'] if not r['point'] else '（點位）', r['scope'], r['owner'], r['host'], r['host_kind'], '是' if r['public'] else '否',
                     {'N': '北', 'S': '南'}[r['side']], r['dist'], r['aerial'], r['aerial_note'], r['osm']])
types = collections.OrderedDict()
for r in sports:
    if not r['public']: continue
    t = types.setdefault(r['typ'], collections.Counter())
    t[(r['scope'], 'n')] += 1; t[(r['scope'], 'a')] += r['area']
with open(H / f'data/{ZONE}_運動場_種類統計.csv', 'w', encoding='utf-8-sig', newline='') as fo:
    w_ = csv.writer(fo); w_.writerow(['種類', '範圍內_處', '範圍內_m2', '鄰近_處', '鄰近_m2'])
    for k, t in sorted(types.items(), key=lambda kv: -(kv[1][('範圍內', 'a')] + kv[1][('鄰近', 'a')])):
        w_.writerow([k, t[('範圍內', 'n')], round(t[('範圍內', 'a')]), t[('鄰近', 'n')], round(t[('鄰近', 'a')])])
with open(H / f'data/{ZONE}_住宅_里別戶數.csv', 'w', encoding='utf-8-sig', newline='') as fo:
    w_ = csv.DictWriter(fo, fieldnames=list(rows_v[0].keys())); w_.writeheader(); [w_.writerow(r) for r in rows_v]
summary = {
 'zone': ZONE, 'households_ym': YM,
 'households': round(tot['hh']), 'population': round(tot['pop']), 'hh_N': round(tot['N']), 'hh_S': round(tot['S']),
 'households_range': [round(min(alt.values())), round(max(alt.values()))], 'weights_alt': {k: round(v) for k, v in alt.items()},
 'age_share': {'0–14': round(tot['a0'] / tot['pop'], 3), '15–64': round(tot['a15'] / tot['pop'], 3), '65+': round(tot['a65'] / tot['pop'], 3)},
 'villages': [f"{r['區']}{r['里']}" for r in rows_v if r['分配戶數'] > 0],
 'res_buildings': len(houses), 'res_buildings_N': sum(1 for r in houses if r['side'] == 'N'), 'res_buildings_S': sum(1 for r in houses if r['side'] == 'S'),
 'res_fa': round(sum(r['res_fa'] for r in houses)), 'unk_buildings': unk_in,
 'sport_types': [[k, t[('範圍內', 'n')], round(t[('範圍內', 'a')]), t[('鄰近', 'n')], round(t[('鄰近', 'a')])] for k, t in types.items()],
 'sport_in_area': round(sum(r['area'] for r in sports if r['public'] and r['scope'] == '範圍內' and r['typ'] != '兒童遊戲場')),
 'sport_adj_area': round(sum(r['area'] for r in sports if r['public'] and r['scope'] == '鄰近' and r['typ'] != '兒童遊戲場')),
 'playground_in_area': round(sum(r['area'] for r in sports if r['scope'] == '範圍內' and r['typ'] == '兒童遊戲場')),
 'not_public': [[r['typ'], r['area'], r['owner']] for r in sports if not r['public']],
 'parks': parks, 'loops': LOOPS, 'shops_sport': dict(shops_sport), 'shops_sport_list': shops_list,
}
json.dump(summary, open(H / f'data/{ZONE}_sports_housing_summary.json', 'w'), ensure_ascii=False, indent=1)
print('households', summary['households'], 'range', summary['households_range'], 'pop', summary['population'], 'N/S', summary['hh_N'], summary['hh_S'])
print('age', summary['age_share'], 'villages', summary['villages'])
print('res buildings', summary['res_buildings'], 'N', summary['res_buildings_N'], 'S', summary['res_buildings_S'], 'res_fa', summary['res_fa'], 'unk', unk_in)
for t in summary['sport_types']: print('sport', t)
print('in', summary['sport_in_area'], 'adj', summary['sport_adj_area'], 'playground', summary['playground_in_area'], 'not public', summary['not_public'])
print('parks', [(p['name'], p['area']) for p in parks]); print('shops', dict(shops_sport))
