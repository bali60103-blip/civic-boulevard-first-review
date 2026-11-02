# 由本地 OSM PBF（2026-09-08）抽出街道家具點：行道樹、捷運出入口、通風井、公車站（範例圖之樹穴、通風井、出入口）
import json, osmium
from pathlib import Path
from shapely.geometry import mapping, box, Point
H = Path(__file__).resolve().parents[1]
PBF = '/Users/ktlu/Downloads/taiwan-260908.osm.pbf'
BB = box(121.5037528384707, 25.034315313146706, 121.57135791788014, 25.061191902246893)
def kind(t):
    if t.get('natural') == 'tree': return 'tree'
    if t.get('railway') == 'subway_entrance' or (t.get('railway') == 'train_station_entrance'): return 'mrt_entrance'
    if t.get('man_made') == 'ventilation_shaft': return 'vent'
    if t.get('highway') == 'bus_stop' or t.get('public_transport') == 'platform' and t.get('bus') == 'yes': return 'bus_stop'
    if t.get('amenity') == 'bicycle_rental': return 'bike'
    return None
class N(osmium.SimpleHandler):
    def __init__(s): super().__init__(); s.out = []
    def node(s, n):
        if not n.tags: return
        t = {k: v for k, v in n.tags}; k = kind(t)
        if not k or not n.location.valid(): return
        p = Point(n.location.lon, n.location.lat)
        if BB.contains(p): s.out.append({'type': 'Feature', 'geometry': mapping(p), 'properties': {'kind': k, 'name': t.get('name', ''), 'ref': t.get('ref', ''), '@id': n.id}})
h = N(); h.apply_file(PBF)
json.dump({'type': 'FeatureCollection', 'features': h.out}, open(H / 'data/osm_street_points_4326.geojson', 'w'), ensure_ascii=False)
import collections; print(collections.Counter(f['properties']['kind'] for f in h.out))
