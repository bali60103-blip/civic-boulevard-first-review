# 公園綠地：各分區面積與比例（一樓店家判讀已併入 01_classify.py）
import json, csv, collections
from pathlib import Path
from shapely.geometry import shape, mapping, Point, box
from shapely.ops import unary_union, transform
from shapely.strtree import STRtree
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
D = H / 'data'
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform
frame = box(300935, 2770000, 307545, 2771910)

zf = json.load(open(D / 'zones_EPSG3826.geojson'))['features']
ZONES = [(f['properties'], shape(f['geometry'])) for f in zf if 'id' in f['properties']]
axis = shape(json.load(open(D / 'civic_elevated_EPSG3826.json'))['axis'])
elev = shape(json.load(open(D / 'civic_elevated_EPSG3826.json'))['elevated'])

def side(pt):
    # 以軸線上最近點的切線方向判斷南北側
    t = axis.project(pt); a = axis.interpolate(max(t - 20, 0)); b = axis.interpolate(min(t + 20, axis.length))
    cross = (b.x - a.x) * (pt.y - a.y) - (b.y - a.y) * (pt.x - a.x)
    return '北' if cross > 0 else '南'

def zone_side_polys():
    out = {}
    for z, g in ZONES:
        for sd in ('北', '南'):
            parts = [p for p in getattr(g.difference(axis.buffer(0.01)), 'geoms', [g]) if side(p.representative_point()) == sd]
            out[(z['id'], sd)] = unary_union(parts)
    return out
ZS = zone_side_polys()

# ---------- (1) 公園綠地 ----------
PARK = {'leisure=park', 'leisure=garden', 'leisure=common', 'leisure=nature_reserve', 'landuse=recreation_ground', 'landuse=village_green'}
SPORT = {'leisure=pitch', 'leisure=track', 'leisure=playground'}
gr = json.load(open(D / 'osm_green_4326.geojson'))['features']
G = {'PARK': [], 'GRASS': [], 'SPORT': []}
for f in gr:
    k = f['properties']['kind']; g = transform(tf, shape(f['geometry'])).buffer(0).intersection(frame)
    if g.is_empty: continue
    G['PARK' if k in PARK else 'SPORT' if k in SPORT else 'GRASS'].append(g)
park = unary_union(G['PARK']); sport = unary_union(G['SPORT']).difference(park)
grass = unary_union(G['GRASS']).difference(park).difference(sport)
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}},
           'features': [{'type': 'Feature', 'geometry': mapping(g), 'properties': {'kind': k}}
                        for k, g in (('PARK', park), ('GRASS', grass), ('SPORT', sport))]},
          open(D / 'green_EPSG3826.geojson', 'w'))
with open(D / '統計_公園綠地_分區.csv', 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.writer(fh); w.writerow(['分區', '分區土地_ha', '公園_ha', '草地樹林_ha', '運動場遊戲場_ha', '綠地合計_ha', '綠地佔分區_%', '北側綠地_ha', '南側綠地_ha'])
    for z, g in ZONES:
        a = [g.intersection(x).area / 1e4 for x in (park, grass, sport)]; tot = sum(a)
        ns = [ZS[(z['id'], s)].intersection(unary_union([park, grass, sport])).area / 1e4 for s in ('北', '南')]
        w.writerow([z['id'], round(g.area / 1e4, 2)] + [round(v, 2) for v in a] + [round(tot, 2), round(100 * tot * 1e4 / g.area, 1)] + [round(v, 2) for v in ns])

print(open(D / '統計_公園綠地_分區.csv', encoding='utf-8-sig').read())
