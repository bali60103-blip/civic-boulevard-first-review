# 由本地 OSM PBF（2026-09-08）抽出照片中可見之街道設施（節點／線／面）：機車／自行車停車、停車場出入口、樓梯、候車亭、
# 公共藝術、座椅、圍籬、地下道等；供照片核實後上圖
import json, osmium
from pathlib import Path
from shapely import wkb
from shapely.geometry import mapping, box, Point, LineString
H = Path(__file__).resolve().parents[1]
PBF = '/Users/ktlu/Downloads/taiwan-260908.osm.pbf'
BB = box(121.5037528384707, 25.034315313146706, 121.57135791788014, 25.061191902246893)
def kind(t):
    a = t.get('amenity'); h = t.get('highway')
    if a == 'motorcycle_parking': return 'moto_parking'
    if a == 'bicycle_parking': return 'bike_parking'
    if a == 'bicycle_rental': return 'bike_rental'
    if a == 'parking_entrance': return 'parking_entrance'
    if a == 'shelter' or t.get('shelter') == 'yes' and (h == 'bus_stop' or t.get('public_transport') == 'platform'): return 'shelter'
    if h == 'bus_stop' or (t.get('public_transport') == 'platform' and t.get('bus') == 'yes'): return 'bus_stop'
    if t.get('tourism') == 'artwork': return 'artwork'
    if h == 'steps': return 'steps'
    if a == 'bench': return 'bench'
    if t.get('barrier') in ('fence', 'wall', 'retaining_wall', 'hedge'): return 'barrier_' + t['barrier']
    if t.get('man_made') in ('ventilation_shaft', 'street_cabinet'): return t['man_made']
    if t.get('natural') == 'tree_row': return 'tree_row'
    if t.get('covered') in ('yes', 'arcade', 'colonnade') and h in ('footway', 'pedestrian', 'path'): return 'covered_walk'
    if t.get('railway') in ('abandoned', 'disused'): return 'rail_' + t['railway']
    if t.get('playground') or t.get('leisure') in ('playground', 'fitness_station'): return 'play_fitness'
    return None
wkbf = osmium.geom.WKBFactory()
class X(osmium.SimpleHandler):
    def __init__(s): super().__init__(); s.out = []
    def push(s, g, t, oid, typ):
        k = kind(t)
        if not k or g is None or not g.intersects(BB): return
        s.out.append({'type': 'Feature', 'geometry': mapping(g), 'properties': {'kind': k, 'osm': f'{typ}/{oid}', 'name': t.get('name', ''),
                      'tags': {kk: vv for kk, vv in t.items() if kk in ('amenity', 'highway', 'shelter', 'covered', 'barrier', 'tourism',
                               'artwork_type', 'capacity', 'level', 'layer', 'location', 'access', 'ref', 'railway', 'material')}}})
    def node(s, n):
        if not n.tags or not n.location.valid(): return
        t = {k: v for k, v in n.tags}
        if kind(t): s.push(Point(n.location.lon, n.location.lat), t, n.id, 'node')
    def way(s, w):
        t = {k: v for k, v in w.tags}
        if not kind(t): return
        try: g = LineString([(nd.lon, nd.lat) for nd in w.nodes])
        except Exception: return
        s.push(g, t, w.id, 'way')
h = X(); h.apply_file(PBF, locations=True, idx='flex_mem')
json.dump({'type': 'FeatureCollection', 'features': h.out}, open(H / 'data/osm_furniture_4326.geojson', 'w'), ensure_ascii=False)
import collections; print(collections.Counter(f['properties']['kind'] for f in h.out))
