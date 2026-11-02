# P15 v3（2026-10-15）：自 OSM 臺灣 PBF 擷取圖框範圍內之道路中心線（開口方向用）與牆（barrier=wall／retaining_wall／city_wall）
#   範圍同 06_市民大道諾利圖 01_extract_osm.py（E300600–307900、N2768500–2773750）。
#   輸出 data/osm_ways_EPSG3826.geojson（kind：road／wall）；PBF 2026-09-08（~/Downloads/taiwan-260908.osm.pbf）
import json, time
from pathlib import Path
import osmium
from osmium.filter import KeyFilter
from shapely.geometry import LineString, mapping
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
PBF = Path.home() / 'Downloads/taiwan-260908.osm.pbf'
BB = (300600, 2768500, 307900, 2773750)
to = Transformer.from_crs(4326, 3826, always_xy=True).transform
inv = Transformer.from_crs(3826, 4326, always_xy=True).transform
L0, A0 = inv(BB[0], BB[1]); L1, A1 = inv(BB[2], BB[3])
WALLS = {'wall', 'retaining_wall', 'city_wall'}
KEEP = ('highway', 'name', 'bridge', 'tunnel', 'layer', 'foot', 'access', 'barrier', 'wall')
out = []; t0 = time.time()
for o in osmium.FileProcessor(str(PBF)).with_locations().with_filter(KeyFilter('highway', 'barrier')):
    if not o.is_way():
        continue
    t = dict(o.tags)
    kind = 'road' if 'highway' in t else 'wall' if t.get('barrier') in WALLS else None
    if kind is None:
        continue
    try:
        pts = [(n.lon, n.lat) for n in o.nodes if n.location.valid()]
    except Exception:
        continue
    if len(pts) < 2 or not any(L0 < x < L1 and A0 < y < A1 for x, y in pts):
        continue
    out.append({'type': 'Feature', 'geometry': mapping(LineString([to(x, y) for x, y in pts])),
                'properties': {'kind': kind, 'osm': f'w{o.id}', **{k: t[k] for k in KEEP if k in t}}})
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'bbox_3826': BB, 'features': out},
          open(H / 'data/osm_ways_EPSG3826.geojson', 'w'), ensure_ascii=False)
print('道路', sum(f['properties']['kind'] == 'road' for f in out), '牆', sum(f['properties']['kind'] == 'wall' for f in out), f'{time.time() - t0:.0f}s')
