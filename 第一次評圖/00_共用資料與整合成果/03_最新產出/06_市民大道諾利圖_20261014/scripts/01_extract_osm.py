# 市民大道諾利圖（一）：自 OSM 臺灣 PBF 擷取圖框範圍內之建物面、公共室內判定用標籤（建物面＋點）、水域
#   圖框＝A1 橫式 1:8,000 滿版（6,728 × 4,752 m），中心 E304240／N2771130（淡水河堤—基隆路置中）；擷取範圍外擴 250 m。
#   輸出 data/osm_nolli_EPSG3826.geojson（kind：building／poi／water）；PBF 2026-09-08（~/Downloads/taiwan-260908.osm.pbf）
import json, time
from pathlib import Path
import osmium
from shapely import wkb
from shapely.geometry import mapping, Point
from shapely.ops import transform
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
PBF = Path.home() / 'Downloads/taiwan-260908.osm.pbf'
BB = (300600, 2768500, 307900, 2773750)
to = Transformer.from_crs(4326, 3826, always_xy=True).transform
inv = Transformer.from_crs(3826, 4326, always_xy=True).transform
L0, A0 = inv(BB[0], BB[1]); L1, A1 = inv(BB[2], BB[3])
KEEP = ('building', 'amenity', 'shop', 'tourism', 'leisure', 'railway', 'public_transport', 'historic', 'name', 'religion', 'layer', 'location')
PUB_POI = {'amenity': {'place_of_worship', 'library', 'marketplace', 'theatre', 'arts_centre', 'concert_hall', 'exhibition_centre'},
           'shop': {'mall', 'department_store'}, 'tourism': {'museum', 'gallery'}}
fab = osmium.geom.WKBFactory(); out = []; t0 = time.time()
for o in osmium.FileProcessor(str(PBF)).with_locations().with_areas():
    t = dict(o.tags)
    if o.is_node():
        if not any(t.get(k) in v for k, v in PUB_POI.items()) or not o.location.valid(): continue
        if not (L0 < o.location.lon < L1 and A0 < o.location.lat < A1): continue
        out.append({'type': 'Feature', 'geometry': mapping(Point(to(o.location.lon, o.location.lat))),
                    'properties': {'kind': 'poi', 'osm': f'n{o.id}', **{k: t[k] for k in KEEP if k in t}}})
        continue
    if not o.is_area(): continue
    bld = 'building' in t
    water = t.get('natural') == 'water' or t.get('waterway') == 'riverbank' or t.get('water') in ('river', 'canal')
    if not (bld or water): continue
    try: g = wkb.loads(fab.create_multipolygon(o), hex=True)
    except Exception: continue
    c = g.representative_point()
    if not (L0 < c.x < L1 and A0 < c.y < A1): continue
    out.append({'type': 'Feature', 'geometry': mapping(transform(to, g)),
                'properties': {'kind': 'building' if bld else 'water', 'osm': f'a{o.id}', **{k: t[k] for k in KEEP if k in t}}})
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'bbox_3826': BB,
           'source': 'OSM 臺灣 PBF 2026-09-08（taiwan-260908.osm.pbf）', 'features': out},
          open(H / 'data/osm_nolli_EPSG3826.geojson', 'w'), ensure_ascii=False)
import collections
print(collections.Counter(f['properties']['kind'] for f in out), round(time.time() - t0), 's')
