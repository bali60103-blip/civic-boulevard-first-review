# Z1–Z8 橋下空間：以 OSM 市民大道高架主線／匝道之車道數推估橋面投影（＝橋下空間範圍），依分區切分
# 橋面寬＝車道數 × 3.5 m ＋ 2.0 m（路肩＋護欄）；雙向分離橋面間距 ≤ 8 m 者視為同一橋下空間（閉合運算）
# 分區取自 zones_EPSG3826.geojson（01_classify.py）；01 重跑後須重跑本程式
import json, csv
from pathlib import Path
from shapely.geometry import shape, mapping, LineString, Point
from shapely.ops import unary_union, transform
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
ROOT = H.parents[1]
OUT = H / 'data'
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform
LANE_W, EXTRA_W, GAP = 3.5, 2.0, 8.0

main, ramp = [], []
for f in json.load(open(ROOT / '01_輸入資料/原始來源/civic_blvd_osm.geojson'))['features']:
    p = f['properties']
    if not p.get('bridge') or f['geometry']['type'] != 'LineString': continue
    try: lanes = int(p.get('lanes') or 1)
    except ValueError: lanes = 1
    g = transform(tf, LineString(f['geometry']['coordinates']))
    deck = g.buffer((lanes * LANE_W + EXTRA_W) / 2, cap_style='flat', join_style='mitre', mitre_limit=3)
    (ramp if p.get('highway') == 'trunk_link' else main).append(deck)
close = lambda g: g.buffer(GAP / 2, join_style='mitre').buffer(-GAP / 2, join_style='mitre')
MAIN = close(unary_union(main))
RAMP = unary_union(ramp).difference(MAIN)

ZF = json.load(open(OUT / 'zones_EPSG3826.geojson'))['features']
ZONES = [(f['properties'], shape(f['geometry'])) for f in ZF if 'id' in f['properties']]
civ = json.load(open(OUT / 'civic_elevated_EPSG3826.json'))
axis = shape(civ['axis'])
polys = lambda g: [p for p in getattr(g, 'geoms', [g]) if p.geom_type == 'Polygon']

feats, rows = [], []
for z, zg in ZONES:
    # 以分區多邊形本身切分（界線沿實際路口中心線，為斜線；外接矩形會使相鄰分區重疊而重複計算）
    m, r = MAIN.intersection(zg), RAMP.intersection(zg)
    # 長度＝分區軸線里程 × 橋面沿軸線實際延伸比例（以軸線里程投影；Z8 光復—基隆段高架於圖幅內落地）
    ax = axis.intersection(zg)
    ts = [axis.project(Point(c)) for s in getattr(ax, 'geoms', [ax]) for c in s.coords]
    mt = [axis.project(Point(c)) for p in polys(m) for c in p.exterior.coords]
    L = round(z['len_m'] * max(0, min(max(ts), max(mt)) - max(min(ts), min(mt))) / (max(ts) - min(ts))) if mt else 0
    w = m.area / L if L else 0
    feats.append({'type': 'Feature', 'geometry': mapping(m), 'properties': {
        'id': z['id'], 'kind': '主線橋下', 'from': z['from'], 'to': z['to'],
        'area_m2': round(m.area), 'len_m': L, 'avg_w_m': round(w, 1)}})
    if not r.is_empty:
        feats.append({'type': 'Feature', 'geometry': mapping(r), 'properties': {'id': z['id'], 'kind': '匝道橋下', 'area_m2': round(r.area)}})
    rows.append([z['id'], z['from'], z['to'].split('／')[0], L, round(w, 1), round(m.area), round(r.area),
                 round(m.area + r.area)])
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': feats},
          open(OUT / 'underbridge_EPSG3826.geojson', 'w'), ensure_ascii=False)
with open(OUT / '統計_橋下空間_分區.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.writer(fh)
    w.writerow(['分區', '起', '迄', '主線橋下長度_m', '平均寬_m', '主線橋下面積_m2', '匝道橋下面積_m2', '合計_m2'])
    w.writerows(rows)
for r in rows: print(r)
print('total', sum(r[7] for r in rows), 'm2; outside zones', round(MAIN.area - sum(r[5] for r in rows)))
