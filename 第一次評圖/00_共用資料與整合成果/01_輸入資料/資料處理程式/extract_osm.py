"""Stage 1 — extract everything we need from taiwan-260908.osm.pbf, clipped to a
generous bbox around 市民大道, into compact JSON in data/processed/.

Nothing is invented here: every record keeps its OSM id + tags so any downstream
number can be traced back to a real object.
"""
import json, os, sys, collections
import osmium

from config import OSM_PBF as PBF, BBOX, DATA_PROCESSED as OUT

os.makedirs(OUT, exist_ok=True)
W, S, E, N = BBOX

HW_KEEP = {
    "motorway","motorway_link","trunk","trunk_link","primary","primary_link",
    "secondary","secondary_link","tertiary","tertiary_link","residential",
    "living_street","unclassified","service","pedestrian","footway","path",
    "steps","cycleway","track","corridor","road","construction",
}
POI_KEYS = ("amenity","shop","office","leisure","tourism","craft","healthcare",
            "industrial","man_made","emergency","club","government","military")
AREA_KEYS = ("building","landuse","leisure","natural","amenity","waterway","boundary","place")


def inbox(lon, lat):
    return W <= lon <= E and S <= lat <= N


class Handler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.nodes = []          # POI nodes + crossing/traffic_signals nodes
        self.ways = []           # highway ways (geometry via locations)
        self.areas = []          # buildings / landuse / water polygons
        self.rels_admin = []
        self.n_seen = 0

    def node(self, n):
        try:
            lon, lat = n.location.lon, n.location.lat
        except Exception:
            return
        if not inbox(lon, lat):
            return
        t = dict(n.tags)
        if not t:
            return
        keep = any(k in t for k in POI_KEYS) or t.get("highway") in (
            "crossing","traffic_signals","elevator","street_lamp","bus_stop") \
            or "railway" in t or "public_transport" in t or "entrance" in t
        if keep:
            self.nodes.append({"id": n.id, "lon": round(lon,7), "lat": round(lat,7), "t": t})

    def way(self, w):
        t = dict(w.tags)
        hw = t.get("highway")
        rw = t.get("railway")
        is_area = any(k in t for k in AREA_KEYS)
        if not (hw in HW_KEEP or rw or is_area):
            return
        try:
            coords = [(round(nd.lon,7), round(nd.lat,7)) for nd in w.nodes if nd.location.valid()]
        except Exception:
            return
        if len(coords) < 2:
            return
        if not any(inbox(x, y) for x, y in coords):
            return
        refs = [nd.ref for nd in w.nodes]
        rec = {"id": w.id, "c": coords, "t": t, "n": refs}
        if hw in HW_KEEP:
            self.ways.append(rec)
        elif rw:
            rec["_rail"] = True
            self.ways.append(rec)
        else:
            self.areas.append(rec)


h = Handler()
h.apply_file(PBF, locations=True, idx="flex_mem")

print("nodes", len(h.nodes), "ways", len(h.ways), "areas", len(h.areas))
json.dump(h.nodes, open(f"{OUT}/osm_nodes.json","w"), ensure_ascii=False)
json.dump(h.ways,  open(f"{OUT}/osm_ways.json","w"),  ensure_ascii=False)
json.dump(h.areas, open(f"{OUT}/osm_areas.json","w"), ensure_ascii=False)

print("\nhighway histogram:")
for k,v in collections.Counter(w["t"].get("highway") for w in h.ways).most_common():
    print(f"  {k}: {v}")
print("\ncivic blvd named ways:",
      sum(1 for w in h.ways if (w["t"].get("name","")).startswith("市民大道")))
