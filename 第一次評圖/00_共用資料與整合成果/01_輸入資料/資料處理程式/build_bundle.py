"""Stage 11 — build the data bundle the visualisation loads.

Everything is clipped to a corridor around the axis and quantised. Geometry is
stored as integer offsets from a bundle-wide origin at 1e-5 deg (~1 m)
resolution, which is roughly 3x smaller than JSON floats and still finer than
the georeferencing residual (7 m), so the encoding loses nothing real.
"""
import json, math, collections
import numpy as np
from shapely.geometry import LineString, Point, Polygon, box
from shapely.prepared import prep
from config import PDF_ZONES
from geo import to_m, to_deg, ll_to_m, TO_M
from sectors import classify, SECTOR_KEYS

axis = json.load(open("../data/processed/axis.json"))
A = LineString(axis["axis_m"])
ways  = json.load(open("../data/processed/osm_ways.json"))
areas = json.load(open("../data/processed/osm_areas.json"))
nodes = json.load(open("../data/processed/osm_nodes.json"))
verdict = json.load(open("../data/processed/verdict.json"))
b_det = json.load(open("../data/processed/b_detour.json"))
g_grad = json.load(open("../data/processed/g_gradient.json"))
f_ind = json.load(open("../data/processed/f_industry.json"))
c_str = json.load(open("../data/processed/c_structure.json"))
h_bl  = json.load(open("../data/processed/h_blend.json"))
a1    = json.load(open("../data/processed/a1_crossings.json"))

# clip zones (metres from the axis)
Z = {"wide": 1600.0, "mid": 900.0, "near": 950.0}
BUF = {k: prep(A.buffer(v)) for k, v in Z.items()}
BUFG = {k: A.buffer(v) for k, v in Z.items()}

Q = 100000.0     # 1e-5 deg quantisation
def enc_line(coords_ll):
    """[[lon,lat],...] -> [x0,y0,dx1,dy1,...] as ints at 1e-5 deg."""
    out = []
    px = py = None
    for lon, lat in coords_ll:
        x = int(round(lon*Q)); y = int(round(lat*Q))
        if px is None: out += [x, y]
        else: out += [x-px, y-py]
        px, py = x, y
    return out

def in_zone(geom_m, zone):
    return BUF[zone].intersects(geom_m)

bundle = {"meta": {
    "title": "市民大道南北分隔 — 疊圖分析系統",
    "crs_display": "EPSG:4326", "crs_compute": "EPSG:3826",
    "quant": 1/Q,
    "axis_length_m": axis["axis_length_m"],
    "sources": [
      "taiwan-260908.osm.pbf (OpenStreetMap, ODbL)",
      "市民大道全長.geojson (overpass-turbo export, ODbL)",
      "site model 市民大道new.blend (使用者建置的 Blender 基地模型)",
      "市民高架都市空間活化論述_1150610.pdf (設計論述)",
    ],
}}

# ------------------------------------------------------------------ axis ----
bundle["axis"] = enc_line(axis["axis_ll"])
bundle["elevated"] = [enc_line(l) for l in axis["elevated_ll"]]
bundle["atgrade"]  = [enc_line(l) for l in axis["atgrade_ll"]]
bundle["ramps"]    = [enc_line(l) for l in axis["ramps_ll"]]

# ------------------------------------------------------------- base geo -----
def collect_areas(pred, zone, simplify_m=4.0, max_n=None):
    out = []
    for a in areas:
        if not pred(a["t"]): continue
        g = to_m(LineString(a["c"]))
        if not in_zone(g, zone): continue
        gs = g.simplify(simplify_m, preserve_topology=False)
        if len(gs.coords) < 3: continue
        out.append(enc_line([tuple(c) for c in to_deg(gs).coords]))
        if max_n and len(out) >= max_n: break
    return out

print("collecting base geography ...")
bundle["water"] = collect_areas(
    lambda t: t.get("natural")=="water" or t.get("waterway") in ("riverbank",)
              or t.get("landuse")=="reservoir", "wide", 6.0)
bundle["green"] = collect_areas(
    lambda t: t.get("leisure") in ("park","garden","pitch","playground","nature_reserve")
              or t.get("landuse") in ("grass","forest","recreation_ground","cemetery","village_green"),
    "wide", 3.0)
print(f"  water {len(bundle['water'])}, green {len(bundle['green'])}")

# buildings: real footprints, but only in the mid zone and simplified hard
bl = []; bl_cent = []; bl_side = []
for a in areas:
    if "building" not in a["t"]: continue
    g = to_m(LineString(a["c"]))
    if not in_zone(g, "mid"): continue
    if g.length < 24: continue
    gs = g.simplify(2.5, preserve_topology=False)
    if len(gs.coords) < 4: continue
    bl.append(enc_line([tuple(c) for c in to_deg(gs).coords]))
    cx = sum(c[0] for c in g.coords)/len(g.coords)
    cy = sum(c[1] for c in g.coords)/len(g.coords)
    bl_cent.append((cx, cy))
    _s = A.project(Point(cx,cy)); _e = 15.0
    _a = A.interpolate(max(0,_s-_e)); _b = A.interpolate(min(A.length,_s+_e))
    bl_side.append(1 if ((_b.x-_a.x)*(cy-_a.y)-(_b.y-_a.y)*(cx-_a.x))>0 else -1)
# attach a height to each bundled building from the nearest Blender mass
# (nearest-centroid within 25 m; None when no mass is close enough, and flagged
# when the height is the model's 12.0 m default rather than a real value)
from scipy.spatial import cKDTree
_G = json.load(open("../data/processed/blend_georef.json"))
_B = np.load("../data/blend/buildings_parts.npy").astype(np.float64)
_BXY = _B[:, :2].copy(); _BXY[:,0] += _G["tx"]; _BXY[:,1] += _G["ty"]
_BH = _B[:,3] - _B[:,2]
_btree = cKDTree(_BXY)
bh = []
for cent in bl_cent:
    d, i = _btree.query(cent, distance_upper_bound=25.0)
    if not np.isfinite(d):
        bh.append(None)
    else:
        hh = float(_BH[i])
        bh.append([round(hh,1), 1 if abs(hh-12.0) < 0.05 else 0])
bundle["buildings"] = bl
bundle["building_h"] = bh
bundle["building_side"] = bl_side
bundle["building_s"] = [int(round(A.project(Point(*c)))) for c in bl_cent]
bundle["building_d"] = [int(round(A.distance(Point(*c)))) for c in bl_cent]
_known = sum(1 for x in bh if x)
_dflt  = sum(1 for x in bh if x and x[1])
print(f"  buildings {len(bl)}; height matched {_known} ({_known/len(bl)*100:.0f}%), "
      f"of which {_dflt} are the 12.0 m default")

# roads by class
RCLS = {"trunk":0,"motorway":0,"primary":1,"secondary":1,
        "tertiary":2,"residential":3,"unclassified":3,"living_street":3,
        "service":4,"footway":5,"path":5,"pedestrian":5,"steps":5,"cycleway":5}
roads = {0:[],1:[],2:[],3:[],4:[],5:[]}
for w in ways:
    hw = w["t"].get("highway")
    if hw not in RCLS: continue
    cls = RCLS[hw]
    zone = "wide" if cls <= 1 else ("mid" if cls <= 3 else "near")
    g = to_m(LineString(w["c"]))
    if not in_zone(g, zone): continue
    gs = g.simplify(3.0 if cls>=4 else 2.0, preserve_topology=False)
    roads[cls].append(enc_line([tuple(c) for c in to_deg(gs).coords]))
bundle["roads"] = {str(k): v for k, v in roads.items()}
print("  roads per class:", {k: len(v) for k,v in roads.items()})

# rail
rail = {"metro": [], "trunkline": []}
for w in ways:
    if not w.get("_rail"): continue
    rw = w["t"].get("railway")
    if rw not in ("rail","subway","disused","abandoned"): continue
    g = to_m(LineString(w["c"]))
    if not in_zone(g, "wide"): continue
    key = "trunkline" if "縱貫線" in w["t"].get("name","") else "metro"
    rail[key].append(enc_line([tuple(c) for c in to_deg(g.simplify(3.0)).coords]))
bundle["rail"] = rail
print("  rail:", {k: len(v) for k,v in rail.items()})

# MRT stations + entrances
st = []
for n in nodes:
    t = n["t"]
    if t.get("railway") in ("station","subway_entrance") or t.get("public_transport")=="station":
        x, y = TO_M.transform(n["lon"], n["lat"])
        if A.distance(Point(x,y)) > Z["wide"]: continue
        st.append({"p": [int(round(n["lon"]*Q)), int(round(n["lat"]*Q))],
                   "n": t.get("name"), "k": "e" if t.get("railway")=="subway_entrance" else "s"})
bundle["stations"] = st
print(f"  stations/entrances {len(st)}")

# ------------------------------------------------------------------ POIs ----
poi = []
SI = {s: i for i, s in enumerate(SECTOR_KEYS)}
def push(lon, lat, sec, name):
    x, y = TO_M.transform(lon, lat)
    p = Point(x, y)
    if A.distance(p) > Z["near"]: return
    s = A.project(p); d = A.distance(p)
    eps = 15.0
    aa = A.interpolate(max(0, s-eps)); bb = A.interpolate(min(A.length, s+eps))
    sd = 1 if ((bb.x-aa.x)*(y-aa.y)-(bb.y-aa.y)*(x-aa.x)) > 0 else -1
    poi.append([int(round(lon*Q)), int(round(lat*Q)), SI[sec], int(round(s)),
                int(round(d))*sd, name or ""])
for n in nodes:
    s = classify(n["t"])
    if s: push(n["lon"], n["lat"], s, n["t"].get("name"))
for a in areas:
    s = classify(a["t"])
    if s:
        lon = sum(c[0] for c in a["c"])/len(a["c"]); lat = sum(c[1] for c in a["c"])/len(a["c"])
        push(lon, lat, s, a["t"].get("name"))
bundle["poi"] = poi
bundle["sectors"] = SECTOR_KEYS
print(f"  POIs in the {Z['near']:.0f} m corridor: {len(poi)}")

# -------------------------------------------------------------- analysis ----
bundle["detour"] = {
    "rows": [{"s": r["s"], "ll": [int(round(r["ll"][0]*Q)), int(round(r["ll"][1]*Q))],
              "st": r["status"],
              "d": r.get("detour"), "net": r.get("net_m"), "cs": r.get("cross_s")}
             for r in b_det["civic"]["rows"]],
    "summary": {k: b_det["civic"][k] for k in
                ("detour_mean","detour_median","detour_p90","detour_max",
                 "extra_walk_mean_m","share_over_2x","share_over_3x","n_ok","n_probes",
                 "offset_m","step_m","fail_reasons")},
    "offsets": b_det["civic_offsets"],
    "controls": [{k: c[k] for k in ("label","length_m","detour_mean","detour_median",
                                    "detour_p90","extra_walk_mean_m","share_over_2x")}
                 for c in b_det["controls"]],
    "control_axes": {c["label"]: enc_line(c["axis_ll"]) for c in b_det["controls"]},
}
bundle["gradient"] = {k: {"centres": v["all"]["centres"],
                          "all": v["all"]["density_per_ha"],
                          "active": v["active"]["density_per_ha"],
                          "trough_all": v["all"]["trough_depth"],
                          "trough_active": v["active"]["trough_depth"],
                          "inner_active": v["active"]["inner_density"],
                          "ref_active": v["active"]["ref_density"]}
                      for k, v in g_grad.items()}
bundle["industry"] = {"north": f_ind["north_totals"], "south": f_ind["south_totals"],
                      "js": f_ind["overall_js"], "chi2_p": f_ind["chi2_p"],
                      "placebos": f_ind["placebos"],
                      "segments": [{"s": r["s"], "js": r["js"], "n": r["n_north"],
                                    "sn": r["n_south"], "north": r["north"], "south": r["south"]}
                                   for r in f_ind["segments"]]}
bundle["piers"] = [[int(round(p["ll"][0]*Q)), int(round(p["ll"][1]*Q)), p["side"],
                    round(p["h"],1)] for p in h_bl["piers"]]
bundle["bents"] = h_bl["bents"]
bundle["obstruction"] = h_bl["obstruction"]
bundle["massing"] = {k: h_bl["massing"][k] for k in
                     ("n_buildings","default_height_share","by_side",
                      "by_band_real_height","segments","caveat")}
bundle["canopy"] = h_bl["canopy"]
bundle["infra"] = {k: [{"n": it["name"], "p": [int(round(it["ll"][0]*Q)), int(round(it["ll"][1]*Q))],
                        "s": it["s"], "d": it["d"], "h": it["h"]}
                       for it in v["items"] if it["d"] <= 400]
                   for k, v in h_bl["infra_detail"].items()}
bundle["admin"] = {"share_pct": c_str["admin_share_pct"],
                   "covered_m": c_str.get("admin_covered_m"),
                   "by_level": c_str["admin_boundary_len_by_level"],
                   "named": [{"n": n["name"], "l": n["level"],
                              "len": n["len_in_corridor_m"], "s": n["s"],
                              "g": enc_line(n["ll"])}
                             for n in c_str.get("named_boundaries", [])]}
bundle["railshare"] = {"pct": c_str["rail_axis_share_pct"],
                       "covered_m": c_str.get("rail_covered_m"),
                       "near": c_str["rail_near_axis_m"]}
bundle["severed"] = {"per_km": c_str["severed_civic"]["per_km"],
                     "n": c_str["severed_civic"]["n"],
                     "controls": c_str["severed_controls"],
                     "pts": [[int(round(i["ll"][0]*Q)), int(round(i["ll"][1]*Q)), i["s"]]
                             for i in c_str["severed_civic"]["items"]]}
bundle["crossings"] = {"per_km": a1["civic"]["walkable_per_km"],
                       "controls": [{k: c[k] for k in ("label","walkable_per_km",
                                                       "gap_mean_m","gap_max_m")}
                                    for c in a1["controls"]],
                       "locs": [{"p": [int(round(l["ll"][0]*Q)), int(round(l["ll"][1]*Q))],
                                 "s": round(l["s"],1), "w": l["walkable"],
                                 "k": l["kinds"], "n": l["names"][:2]}
                                for l in a1["civic"]["locations"]]}
# The proposal's three intervention zones, with the measured detour inside
# each. This is the check that matters for the design: do the zones the
# proposal picked actually coincide with the worst-severed stretches?
_ok = [r for r in b_det["civic"]["rows"] if r["status"] == "ok"]
_inzone = set()
_zones = []
for nm, ext, a, b in PDF_ZONES:
    v = [r for r in _ok if a <= r["s"] <= b]
    _inzone.update(r["s"] for r in v)
    d = [r["detour"] for r in v]
    _zones.append({"name": nm, "extent": ext, "s0": a, "s1": b,
                   "n": len(v),
                   "detour_mean": round(sum(d)/len(d), 3) if d else None,
                   "detour_max": round(max(d), 3) if d else None,
                   "share_over_2x": round(sum(1 for x in d if x > 2)/len(d), 4) if d else None})
_out = [r for r in _ok if r["s"] not in _inzone]
_do = [r["detour"] for r in _out]
bundle["zones"] = {
    "zones": _zones,
    "outside": {"n": len(_out),
                "detour_mean": round(sum(_do)/len(_do), 3),
                "detour_max": round(max(_do), 3),
                "share_over_2x": round(sum(1 for x in _do if x > 2)/len(_do), 4)},
    "worst": [{"s": r["s"], "detour": r["detour"], "extra": round(r["net_m"]-300)}
              for r in sorted(_ok, key=lambda r: -r["detour"])[:6]],
}
bundle["verdict"] = verdict

out = "../output/bundle.json"
json.dump(bundle, open(out, "w"), ensure_ascii=False, separators=(",", ":"))
import os
print(f"\nwrote {out}: {os.path.getsize(out)/1e6:.2f} MB")
for k, v in bundle.items():
    s = len(json.dumps(v, ensure_ascii=False, separators=(",",":")))
    if s > 40000: print(f"  {k:14s} {s/1e6:6.2f} MB")
