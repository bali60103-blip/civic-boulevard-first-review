# Z6 滲透場所（使用者 2026-10-12 指定）：
#   「Z6 的特色是忠泰美術館那塊和旁邊的瑠公圳公園、懷生國小、八德市場，這幾塊有空地、學生、綠地，很適合在高架下方做改動加強地區之間的滲透性，
#    一樣把這幾樣列為主角調查。」——與 workflow 三之主角（長安段公辦都更 U02／U03）並列為主角（tier A）。
#   2026-10-12 補充：北科大學生宿舍列入（學生；建國南路以東、瑠公圳公園南側）；忠泰美術館街廓之未建築部分確認為空地（部分綠化）。
#   各場所：建物＝線稿建物（tier A，酒紅剪影）；開放地（空地、校園、公園綠地）＝場所範圍扣除路徑與建物（tier O，淡酒紅）。
#     忠泰美術館街廓：忠泰企業大樓（市民大道三段 178 號，美術館所在）所在之街廓＝路徑（整合後道路面 ∪ 新工處人行道）圍出之面；含明日博。
#     瑠公圳公園：OSM leisure=park 面；懷生國小：OSM amenity=school 面；八德市場：OSM amenity=marketplace 建物（跨建國高架刀位，使用者指定歸 Z6）。
#   主角公辦都更：U02 規劃量體由 17 KEY_A（PUB:U02:building）畫；U02 法定空地／街角廣場／人行步道（方案）＝開放地；
#     U02 基地內現有建物＝拆除改建（kind＝replaced，不畫）；U03 無方案，現有建物（中崙球場等）畫為酒紅（使用者 2026-10-12 指定）。
#   另輸出（19／20 讀取）：
#     data/Z6_mrt_ctx_EPSG3826.geojson：周邊捷運站體（OSM building=transportation；忠孝新生、忠孝復興、忠孝敦化），
#       使用者指定「捷運列進去，範圍外就讓它淡化」——不裁切至單元，由範圍外淡化遮罩處理。
#     data/Z6_elev_extra_EPSG3826.geojson：建國高架（OSM 建國快速道路 bridge=yes 主線，雙向）車道中心線，與市民高架主線同表現（+2）。
#   OSM 來源：臺灣 PBF 2026-09-08（~/Downloads/taiwan-260908.osm.pbf），首次執行擷取後快取於 data/osm_z6_pbf_cache_EPSG3826.geojson。
import json, sys, importlib.util
from pathlib import Path
from shapely.geometry import shape, mapping, box, Point
from shapely.ops import unary_union, transform
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
ZONE = 'Z6'
spec = importlib.util.spec_from_file_location('sheet', H / 'scripts/02_sheet.py')
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
S.VARIANT['full'] = True
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform
PBF = Path.home() / 'Downloads/taiwan-260908.osm.pbf'
CACHE = H / 'data/osm_z6_pbf_cache_EPSG3826.geojson'
PUB = H.parents[1] / '02_調整過程/公共都更編號圖/公共案件量體與基地_EPSG3826.geojson'
REB = Path.home() / 'Desktop/Civic_Rebuild_20260909_201934/data'
NAMES = ('忠泰企業大樓', '明日博', '瑠公圳公園', '懷生國小', '八德市場', '中崙球場', '北科大學生宿舍')
BB = (303300, 2770150, 305900, 2771500)          # 擷取範圍（EPSG:3826）

# ---------- OSM 擷取（快取）----------
if not CACHE.exists() or set(json.load(open(CACHE)).get('names', [])) != set(NAMES):   # 場所名單變動時重新擷取
    import osmium
    from shapely import wkb
    from shapely.geometry import LineString
    inv = Transformer.from_crs(3826, 4326, always_xy=True).transform
    LON0, LAT0 = inv(BB[0], BB[1]); LON1, LAT1 = inv(BB[2], BB[3])
    fab = osmium.geom.WKBFactory(); out = []
    class Hd(osmium.SimpleHandler):
        def way(self, w):
            t = w.tags
            if t.get('name') == '建國快速道路' and t.get('bridge') == 'yes' and t.get('highway') == 'trunk':
                cs = [(nd.lon, nd.lat) for nd in w.nodes]
                if any(LON0 < x < LON1 and LAT0 < y < LAT1 for x, y in cs):
                    out.append({'type': 'Feature', 'geometry': mapping(transform(tf, LineString(cs))), 'properties': {'kind': 'elev', 'osm': f'w{w.id}', **dict(t)}})
        def area(self, a):
            t = a.tags; nm = t.get('name', '')
            mrt = t.get('building') == 'transportation' and nm.endswith('站')
            if nm not in NAMES and not mrt: return
            try: g = wkb.loads(fab.create_multipolygon(a), hex=True)
            except Exception: return
            c = g.centroid
            if LON0 < c.x < LON1 and LAT0 < c.y < LAT1:
                out.append({'type': 'Feature', 'geometry': mapping(transform(tf, g)), 'properties': {'kind': 'mrt' if mrt else 'place', **dict(t)}})
    Hd().apply_file(str(PBF), locations=True, idx='flex_mem')
    json.dump({'type': 'FeatureCollection', 'source': 'OSM 臺灣 PBF 2026-09-08（taiwan-260908.osm.pbf）', 'names': list(NAMES), 'features': out}, open(CACHE, 'w'), ensure_ascii=False)
OC = json.load(open(CACHE))['features']
def osm_area(nm):
    gs = [shape(f['geometry']).buffer(0) for f in OC if f['properties'].get('name') == nm and f['properties']['kind'] == 'place']
    return unary_union(gs) if gs else None

# ---------- 路徑（同 20 paths_geom 之底：整合後道路面 ∪ 新工處人行道）與街廓 ----------
WB = box(*BB)
sw = unary_union([g for g in (shape(f['geometry']).buffer(0) for f in json.load(open(REB / 'taipei-sidewalks.geojson'))['features']) if g.intersects(WB)])
PATHS = unary_union([S.road.intersection(WB), sw.intersection(WB)])
FACES = WB.difference(PATHS)
BL = [b for b in S.bld.geoms if b.intersects(WB)]
def side(g):
    c = g.representative_point(); d = S.center.project(c); a = S.center.interpolate(d); b = S.center.interpolate(min(d + 5, S.center.length))
    return '北' if (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x) > 0 else '南'
feats = []
def add(g, **pr):
    g = g.buffer(0)
    if g.is_empty or g.area < 1: return
    pr.setdefault('side', side(g)); pr.setdefault('area', round(g.area)); pr['dist_m'] = round(S.center.distance(g))
    feats.append({'type': 'Feature', 'geometry': mapping(g), 'properties': pr})
RULE_TXT = 'Z6 判準（使用者 2026-10-12）：空地、學生、綠地之場所列為主角調查——高架下方改動以加強地區之間的滲透性'
def place(grp, name, extent, note, blds=None, extra=None):
    # 場所：建物（代表點落於範圍內之線稿建物，或指定）→ tier A；範圍扣除路徑與建物 → tier O
    bs = blds if blds is not None else [b for b in BL if extent.contains(b.representative_point())]
    bu = unary_union(bs) if bs else None
    if bu is not None: add(bu, kind='key', tier='A', group=grp, name=name, rule=RULE_TXT, **(extra or {}), note=note + f"；建物 {len(bs)} 棟、投影 {bu.area:,.0f} ㎡（線稿）")
    op = extent.difference(PATHS)
    if bu is not None: op = op.difference(bu.buffer(.3))
    op = unary_union([q for q in getattr(op, 'geoms', [op]) if q.geom_type == 'Polygon' and q.area > 20])
    if not op.is_empty: add(op, kind='key', tier='O', group=grp, name=name + '：開放地', rule=RULE_TXT, **(extra or {}), note=note + f"；開放地 {op.area:,.0f} ㎡（範圍扣除路徑與建物）")
    return bu, op

# 1 忠泰美術館街廓（忠泰企業大樓所在街廓）
jut = osm_area('忠泰企業大樓')
blk = next(q for q in FACES.geoms if q.contains(jut.representative_point()))
place('忠泰美術館街廓', '忠泰美術館街廓（忠泰企業大樓・明日博）', blk,
      f'忠泰美術館位於忠泰企業大樓（市民大道三段 178 號，OSM 12 層）；街廓＝路徑圍出之面 {blk.area:,.0f} ㎡；未建築部分為空地（部分綠化，使用者 2026-10-12 確認）')
# 2 瑠公圳公園（OSM 公園面；跨越巷道之部分扣除路徑）
park = osm_area('瑠公圳公園')
place('瑠公圳公園', '瑠公圳公園', park, f'OSM leisure=park，{park.area:,.0f} ㎡；沿舊瑠公圳之帶狀公園，位於大道南側第一排街廓之後')
# 3 懷生國小（OSM 學校面）
sch = osm_area('懷生國小')
place('懷生國小', '懷生國小', sch, f'OSM amenity=school（安東街 16 巷 2 號），校地 {sch.area:,.0f} ㎡')
# 3b 北科大學生宿舍（使用者 2026-10-12 指定列入；OSM building=dormitory，與線稿建物同形）
dorm = osm_area('北科大學生宿舍')
place('北科大學生宿舍', '北科大學生宿舍', dorm, f'學生（國立臺北科技大學，建國南路以東、瑠公圳公園南側）；OSM building=dormitory {dorm.area:,.0f} ㎡；使用者 2026-10-12 指定列入',
      blds=[b for b in BL if b.intersection(dorm).area > .5 * b.area])
# 4 八德市場（OSM 市場建物；跨建國高架刀位 Z5 47%／Z6 53%，使用者指定歸 Z6）
mkt = osm_area('八德市場')
mb = [b for b in BL if b.intersection(mkt).area > .3 * b.area or b.intersection(mkt).area > .5 * mkt.area]
place('八德市場', '八德市場', mkt, 'OSM amenity=marketplace、1 層；跨建國高架刀位（Z5 47%／Z6 53%），使用者 2026-10-12 指定歸 Z6', blds=mb, extra={'unmask': True})   # 跨界部分不淡化
# 5 主角公辦都更 U02／U03
pub = json.load(open(PUB))['features']
U = {(f['properties']['case'], f['properties']['layer']): shape(f['geometry']) for f in pub if f['properties']['case'] in ('U02', 'U03')}
for b in BL:   # U02：依方案拆除改建（同 Z3 U17）
    if b.intersection(U[('U02', 'site')]).area > .5 * b.area: feats.append({'type': 'Feature', 'geometry': mapping(b), 'properties': {'kind': 'replaced', 'case': 'U02', 'area': round(b.area)}})
u02o = U[('U02', 'landscape')].difference(U[('U02', 'building')].buffer(.3)).difference(PATHS)
add(u02o, kind='key', tier='O', group='主角：U02', name='U02 法定空地・街角廣場・人行步道（方案）', rule='workflow 三 Z6 主角「長安段公辦都更（U02）」',
    note='住都中心 1141212 公辦公聽會簡報 p.33 建築物配置理念（送審版本）描圖；規劃中')
u03b = [b for b in BL if b.intersection(U[('U03', 'site')]).area > .5 * b.area]
add(unary_union(u03b), kind='key', tier='A', group='主角：U03', name='U03 現有建物（中崙球場等）',
    rule='workflow 三 Z6 主角「長安段公辦都更（U03）」；無方案，現有建物上色（使用者 2026-10-12 指定）',
    note=f"U03 長安段二小段 576 等 4 筆（4,107 ㎡，都更處 S14）；基地內線稿建物 {len(u03b)} 棟、投影 {sum(b.area for b in u03b):,.0f} ㎡，含中崙球場（台灣中油）")
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': feats,
           'source': 'OSM 臺灣 PBF 2026-09-08；02 線稿建物；路徑＝整合後道路面 ∪ 新工處人行道；公共案件量體與基地', 'date': '2026-10-12'},
          open(H / f'data/{ZONE}_permeable_EPSG3826.geojson', 'w'), ensure_ascii=False)

# ---------- 捷運站體（單元外者亦列，範圍外淡化）----------
LV = {'-1': 'B1', '-2': 'B2', '-3': 'B2'}
mrt = [{'type': 'Feature', 'geometry': f['geometry'], 'properties': {'name': f['properties']['name'], 'level': LV.get(str(f['properties'].get('layer', '-1')), 'B1'),
        'osm_layer': f['properties'].get('layer'), 'area': round(shape(f['geometry']).area)}} for f in OC if f['properties']['kind'] == 'mrt']
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': mrt,
           'note': '使用者 2026-10-12：捷運列進去，範圍外就讓它淡化'}, open(H / f'data/{ZONE}_mrt_ctx_EPSG3826.geojson', 'w'), ensure_ascii=False)
# ---------- 建國高架主線中心線 ----------
el = [{'type': 'Feature', 'geometry': f['geometry'], 'properties': {'name': '建國高架（建國快速道路）', 'osm': f['properties']['osm'], 'oneway': f['properties'].get('oneway')}}
      for f in OC if f['properties']['kind'] == 'elev']
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': el,
           'note': '使用者 2026-10-12 同意：建國高架主線比照市民高架畫灰色點鏈中心線'}, open(H / f'data/{ZONE}_elev_extra_EPSG3826.geojson', 'w'), ensure_ascii=False)

import collections
for f in feats:
    p = f['properties']
    if p['kind'] == 'key': print(p['tier'], p['group'], p['name'], p['side'], p['area'], '㎡', p['dist_m'], 'm')
print('replaced', sum(1 for f in feats if f['properties']['kind'] == 'replaced'), '｜捷運站體', [(f['properties']['name'], f['properties']['level']) for f in mrt], '｜建國高架', len(el), '段')
