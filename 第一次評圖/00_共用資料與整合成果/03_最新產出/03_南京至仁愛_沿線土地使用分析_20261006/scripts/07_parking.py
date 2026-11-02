# 交通停車：自本機 Blender 重建專案（Civic_Rebuild_20260909_201934）讀取市民大道地下停車場分段、出入口與街景查核點
import json, math
from pathlib import Path
from shapely.geometry import Polygon, Point, mapping
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
B = Path.home() / 'Desktop/Civic_Rebuild_20260909_201934'
reg = json.load(open(B / 'registration.json'))
o = reg['origin_epsg3826']; t = reg['live_to_twd97']['translation']; sc = reg['live_to_twd97']['scale']
th = math.radians(reg['live_to_twd97']['rotation_degrees'])
def to3826(x, y):  # TWD97 = scale × R × model + origin + translation（registration.json）
    return (sc * (math.cos(th) * x - math.sin(th) * y) + o[0] + t[0], sc * (math.sin(th) * x + math.cos(th) * y) + o[1] + t[1])
sec = json.load(open(B / 'ParkingSections/source/sections.json'))
feats = []
for s in sec['sections']:
    feats.append({'type': 'Feature', 'geometry': mapping(Polygon([to3826(*p) for p in s['outline']])),
                  'properties': {'kind': 'section', 'name': s['name'], 'levels': s['levels'], 'length_m': round(s['length_m']),
                                 'extent_status': s['extent_status']}})
    for e in s.get('entrances', []):
        feats.append({'type': 'Feature', 'geometry': mapping(Point(to3826(*e['xy']))),
                      'properties': {'kind': 'entrance', 'name': s['name'], 'osm_id': e['osm_id'], 'status': e['status']}})
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform
sv = json.load(open(B / 'PriorityNodes_20260914/junction_ramp_streetview_20260914.json'))
for site in sv['sites']:
    feats.append({'type': 'Feature', 'geometry': mapping(Point(tf(site['lon'], site['lat']))),
                  'properties': {'kind': 'streetview', 'name': site['id'], 'date': site.get('imagery_date', site.get('date_label', '')),
                                 'observed': '；'.join(site.get('observed', []))[:300]}})
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': feats,
           'source': {'blender_project': str(B), 'sections_url': sec['source_sections_url'], 'assumptions': sec['assumptions'],
                      'streetview_reviewed': sv['date_reviewed'], 'streetview_scope': sv['scope']}},
          open(H / 'data/parking_streetview_EPSG3826.geojson', 'w'), ensure_ascii=False)
for f in feats:
    if f['properties']['kind'] != 'entrance': print(f['properties']['kind'], f['properties']['name'], f['properties'].get('levels', ''), f['properties'].get('length_m', ''), f['properties'].get('date', ''))
