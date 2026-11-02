# 由本地 OSM PBF 另取走廊範圍之「面＋線＋點」補充要素（Z5 起：商業空間、配套措施、可用空地之判讀用）
#   expanded_osm 只含建物與道路；本檔補：土地使用面（landuse）、停車場（amenity=parking 等）、廣場與步行區（place=square、
#   highway=pedestrian 面／線、area:highway）、市場、休閒（leisure）、古蹟（historic／heritage）、
#   點：公車站、YouBike、捷運出入口、公廁、停車場入口、市場、古蹟。
#   輸出 data/osm_extras_EPSG3826.geojson（properties：geom＝area／line／node、osm＝類型+id、其餘為完整 OSM 標籤）
import json
from pathlib import Path
import osmium
from shapely import wkb
from shapely.geometry import mapping, box, Point
from shapely.ops import transform
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
PBF = '/Users/ktlu/Downloads/taiwan-260908.osm.pbf'
BB = box(121.5037528384707, 25.034315313146706, 121.57135791788014, 25.061191902246893)   # 同 03_南京至仁愛 00_extract_pbf
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform

AREA_KEYS = ('landuse', 'leisure', 'place', 'area:highway', 'historic', 'heritage', 'tourism')
AREA_KV = {('amenity', 'parking'), ('amenity', 'motorcycle_parking'), ('amenity', 'bicycle_parking'), ('amenity', 'marketplace'),
           ('amenity', 'bus_station'), ('highway', 'pedestrian'), ('shop', 'mall'), ('shop', 'department_store'), ('building', 'construction'),
           ('amenity', 'university'), ('amenity', 'school'), ('amenity', 'college')}
LINE_KV = {('highway', 'pedestrian'), ('highway', 'living_street'), ('covered', 'arcade'), ('covered', 'colonnade')}
NODE_KV = {('highway', 'bus_stop'), ('public_transport', 'platform'), ('amenity', 'bicycle_rental'), ('railway', 'subway_entrance'),
           ('amenity', 'toilets'), ('amenity', 'parking_entrance'), ('amenity', 'parking'), ('amenity', 'marketplace'),
           ('amenity', 'motorcycle_parking'), ('amenity', 'bench'), ('amenity', 'shelter'), ('amenity', 'drinking_water')}
wkbf = osmium.geom.WKBFactory()

def hit(t, keys, kv):
    return any(k in t for k in keys) or any((k, v) in kv for k, v in t.items())

class Hd(osmium.SimpleHandler):
    def __init__(s):
        super().__init__(); s.out = []
    def push(s, g, t, kind, oid):
        g = transform(tf, g)
        s.out.append({'type': 'Feature', 'geometry': mapping(g), 'properties': {'geom': kind, 'osm': oid, **t}})
    def node(s, n):
        t = {k: v for k, v in n.tags}
        if not t or not hit(t, ('historic', 'heritage'), NODE_KV) or not n.location.valid(): return
        p = Point(n.location.lon, n.location.lat)
        if BB.contains(p): s.push(p, t, 'node', f'n{n.id}')
    def way(s, w):
        t = {k: v for k, v in w.tags}
        if not t or not hit(t, (), LINE_KV) or t.get('area') == 'yes': return
        try: g = wkb.loads(wkbf.create_linestring(w), hex=True)
        except Exception: return
        if g.intersects(BB): s.push(g, t, 'line', f'w{w.id}')
    def area(s, a):
        t = {k: v for k, v in a.tags}
        if not t or not hit(t, AREA_KEYS, AREA_KV): return
        try: g = wkb.loads(wkbf.create_multipolygon(a), hex=True)
        except Exception: return
        if g.intersects(BB): s.push(g, t, 'area', ('w' if a.from_way() else 'r') + str(a.orig_id()))

h = Hd(); h.apply_file(PBF, locations=True, idx='flex_mem')
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': h.out,
           'source': 'OpenStreetMap taiwan-260908.osm.pbf（2026-09-08）'}, open(H / 'data/osm_extras_EPSG3826.geojson', 'w'), ensure_ascii=False)
import collections
print(len(h.out), collections.Counter(f['properties']['geom'] for f in h.out))
