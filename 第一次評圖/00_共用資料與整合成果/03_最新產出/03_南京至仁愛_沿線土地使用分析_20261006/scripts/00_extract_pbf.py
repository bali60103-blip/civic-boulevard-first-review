# 由本地 OSM PBF 另取：(1) 公園綠地面（含 multipolygon relation）；(2) 店家 POI 節點（含完整標籤）
import json, osmium
from pathlib import Path
from shapely import wkb
from shapely.geometry import mapping, box, Point

H = Path(__file__).resolve().parents[1]
OUT = H / 'data'; OUT.mkdir(exist_ok=True)
PBF = '/Users/ktlu/Downloads/taiwan-260908.osm.pbf'
BB = box(121.5037528384707, 25.034315313146706, 121.57135791788014, 25.061191902246893)

GREEN = {('leisure', 'park'), ('leisure', 'garden'), ('leisure', 'playground'), ('leisure', 'common'),
         ('leisure', 'nature_reserve'), ('leisure', 'pitch'), ('leisure', 'track'), ('landuse', 'grass'),
         ('landuse', 'forest'), ('landuse', 'recreation_ground'), ('landuse', 'village_green'), ('landuse', 'meadow'),
         ('natural', 'wood'), ('natural', 'scrub'), ('natural', 'grassland')}
POI_KEYS = ('shop', 'amenity', 'office', 'craft', 'healthcare', 'tourism', 'leisure')
wkbf = osmium.geom.WKBFactory()

class H_(osmium.SimpleHandler):
    def __init__(s):
        super().__init__(); s.green = []; s.poi = []
    def node(s, n):
        t = {k: v for k, v in n.tags}
        if not any(k in t for k in POI_KEYS): return
        if not n.location.valid(): return
        p = Point(n.location.lon, n.location.lat)
        if BB.contains(p): s.poi.append({'type': 'Feature', 'geometry': mapping(p), 'properties': t | {'@id': n.id}})
    def area(s, a):
        t = {k: v for k, v in a.tags}
        kind = next((f'{k}={v}' for k, v in t.items() if (k, v) in GREEN), None)
        if not kind or 'building' in t: return
        try: g = wkb.loads(wkbf.create_multipolygon(a), hex=True)
        except Exception: return
        if not g.intersects(BB): return
        s.green.append({'type': 'Feature', 'geometry': mapping(g.intersection(BB)),
                        'properties': {'kind': kind, 'name': t.get('name', ''), 'access': t.get('access', ''),
                                       '@id': a.orig_id(), 'from_way': a.from_way()}})

h = H_()
h.apply_file(PBF, locations=True, idx='flex_mem')
for nm, fs in (('osm_green_4326.geojson', h.green), ('osm_poi_nodes_4326.geojson', h.poi)):
    json.dump({'type': 'FeatureCollection', 'features': fs}, open(OUT / nm, 'w'), ensure_ascii=False)
    print(nm, len(fs))
