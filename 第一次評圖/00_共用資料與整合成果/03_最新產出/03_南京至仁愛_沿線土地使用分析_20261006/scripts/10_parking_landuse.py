# 停車與一樓使用連動（2026-10-13）：
# (1) 含停車場之建物（09 判讀）→ 圖面斜線疊加，一樓用途不變
# (2) 平面停車場 → 地面範圍（OSM amenity=parking 之平面多邊形，扣除線稿建物）；停管處「平面」停車場未對到多邊形者以點標示
# (3) 各單元停車統計：含停車場建物棟數／投影面積、平面停車場面積、汽機車格（08 統計）
import json, csv
from pathlib import Path
from shapely.geometry import shape, mapping, Point, box
from shapely.ops import unary_union, transform
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]; D = H / 'data'; ROOT = H.parents[1]
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform
frame = box(300935, 2770000, 307545, 2771910)
zf = json.load(open(D / 'zones_EPSG3826.geojson'))['features']
ZONES = [(f['properties'], shape(f['geometry'])) for f in zf if 'id' in f['properties']]
DB = json.load(open(D / 'drawing_buildings_zone_EPSG3826.geojson'))['features']
bld = unary_union([shape(f['geometry']) for f in DB])

# (2) 平面停車場地面範圍
polys = []
for a in json.load(open(ROOT / '01_輸入資料/前處理資料/osm_areas.json')):
    t = a.get('t') or {}
    if t.get('amenity') != 'parking' or t.get('parking') in ('underground', 'multi-storey', 'rooftop') or len(a['c']) < 4: continue
    g = transform(tf, shape({'type': 'Polygon', 'coordinates': [a['c']]})).buffer(0)
    if not g.intersects(frame): continue
    g = g.intersection(frame).difference(bld)
    if g.area >= 30: polys.append((g, a['id'], t.get('name', '')))
lots = [f for f in json.load(open(D / 'parking_pma_EPSG3826.geojson'))['features'] if f['properties']['kind'] == 'lot']
judge = {(r['停車場'], r['地址']): r for r in csv.DictReader(open(D / '停車場建物判讀.csv', encoding='utf-8-sig'))}
feats, unmatched = [], []
used = set()
for f in lots:
    p = f['properties']; r = judge.get((p['name'], p['addr']))
    if not r or r['判型'] != '平面': continue
    pt = Point(f['geometry']['coordinates'])
    near = [(g.distance(pt), i) for i, (g, _, _) in enumerate(polys)]
    d, i = min(near) if near else (9e9, None)
    if d <= 25: used.add(i)
    elif frame.contains(pt): unmatched.append((pt, p))
for i, (g, oid, nm) in enumerate(polys):
    feats.append({'type': 'Feature', 'geometry': mapping(g), 'properties': {'kind': 'surface', 'osm_id': oid, 'name': nm, 'pma_matched': i in used}})
for pt, p in unmatched:
    feats.append({'type': 'Feature', 'geometry': mapping(pt), 'properties': {'kind': 'surface_point', 'name': p['name'], 'car': p['car'], 'moto': p['moto']}})
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': feats},
          open(D / 'surface_parking_EPSG3826.geojson', 'w'), ensure_ascii=False)
surf = unary_union([g for g, _, _ in polys])

# (3) 單元統計
PB = json.load(open(D / 'parking_buildings_EPSG3826.geojson'))['features']
zone_of = {f['properties']['bid']: f['properties']['zone'] for f in DB}
SUP = {r['單元']: r for r in csv.DictReader(open(D / '統計_停車供給_單元.csv', encoding='utf-8-sig'))}
rows = []
for z, g in ZONES:
    pbz = [f for f in PB if zone_of.get(f['properties']['bid']) == z['id']]
    sp = surf.intersection(g).area
    pts_ = sum(1 for pt, _ in unmatched if g.contains(pt))
    s = SUP.get(z['id'], {})
    rows.append({'單元': z['id'], '範圍': f"{z['from']}—{z['to']}", '含停車場建物_棟': len(pbz),
                 '含停車場建物_投影面積_m2': round(sum(shape(f['geometry']).area for f in pbz)),
                 '平面停車場_m2': round(sp), '平面停車場_佔土地_%': round(100 * sp / g.area, 2), '平面停車場_未對到範圍_處': pts_,
                 '汽車格合計': s.get('汽車格合計', ''), '路外機車格': s.get('路外機車格', ''), '汽車格密度_格每ha': s.get('汽車格密度_格每ha', '')})
with open(D / '統計_停車_土地使用_單元.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print('平面停車場多邊形', len(polys), '（停管處對到', len(used), '）｜未對到點', len(unmatched))
for r in rows: print(r)
