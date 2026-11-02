"""Stage 3 — 南北分隔證據 A: 穿越性 (permeability of the axis).

Three independent measurements, each falsifiable against OSM objects:

  A1 CROSSING INVENTORY  Which real ways actually cross the axis, and are they
     walkable? Individual ways are clustered into *crossing locations* (30 m)
     because one intersection is tagged as many parallel ways (2 carriageways,
     2 sidewalks, 4 crossing legs).
  A2 SEVERED STREETS     N-S streets whose end lies within 60 m of the axis
     but which do not continue to the other side = 斷頭路.
  A3 CONTROL CORRIDORS   The same two measures on the four parallel E-W
     arterials in the same district. Without a control, "1 crossing per 300 m"
     is a number with no meaning.
"""
import json, math, collections
import numpy as np
from shapely.geometry import LineString, Point, MultiPoint
from shapely.strtree import STRtree
from geo import to_m, to_deg, ll_to_m

axis = json.load(open("../data/processed/axis.json"))
ways = json.load(open("../data/processed/osm_ways.json"))
nodes = json.load(open("../data/processed/osm_nodes.json"))
axis_m = LineString(axis["axis_m"])
CIVIC_IDS = set(axis["civic_way_ids"])
X0, X1 = axis_m.bounds[0], axis_m.bounds[2]

# ---------------------------------------------------------------- helpers ----
WALK_NO = {"no", "private", "discouraged"}
PED_HW = {"footway","path","pedestrian","steps","living_street","residential",
          "service","unclassified","tertiary","secondary","primary","cycleway",
          "corridor","track","road"}

def walkable(t):
    """Is a pedestrian legally/physically able to use this way?"""
    if t.get("foot") in WALK_NO:
        return False
    if t.get("access") in WALK_NO and t.get("foot") not in ("yes","designated","permissive"):
        return False
    hw = t.get("highway")
    if hw in ("motorway","motorway_link","trunk","trunk_link"):
        # trunk in TW usually forbids pedestrians; only count if explicitly allowed
        return t.get("foot") in ("yes","designated","permissive")
    if hw == "construction":
        return False
    return hw in PED_HW

def geom_m(w):
    return to_m(LineString(w["c"]))

# cache metric geometry once (37k ways)
print("projecting ways to EPSG:3826 ...")
GM = {w["id"]: geom_m(w) for w in ways}
BYID = {w["id"]: w for w in ways}

# ------------------------------------------------- A1 crossing inventory ----
def crossing_report(ax, label, exclude_ids=frozenset(), name_prefix=None):
    """Find every way that geometrically crosses `ax`, classify it, and cluster
    into crossing locations along the axis chainage."""
    cand = [w for w in ways if w["id"] not in exclude_ids
            and not (name_prefix and w["t"].get("name","").startswith(name_prefix))]
    hits = []
    axbuf = ax.buffer(1.0)
    for w in cand:
        g = GM[w["id"]]
        if not g.intersects(axbuf):
            continue
        if not g.crosses(ax) and not g.intersects(ax):
            continue
        inter = g.intersection(ax)
        pts = []
        if inter.is_empty:
            continue
        if inter.geom_type == "Point":
            pts = [inter]
        elif inter.geom_type == "MultiPoint":
            pts = list(inter.geoms)
        else:  # overlapping line -> way runs along the axis, not across it
            continue
        t = w["t"]
        # classify the *vertical* relationship
        layer = t.get("layer")
        if t.get("tunnel") in ("yes","building_passage","culvert"):
            kind = "tunnel"
        elif t.get("bridge") == "yes" and t.get("highway") in ("footway","path","steps","pedestrian"):
            kind = "footbridge"
        elif t.get("bridge") == "yes":
            kind = "bridge"
        else:
            kind = "at_grade"
        for p in pts:
            hits.append({
                "id": w["id"], "hw": t.get("highway"), "name": t.get("name"),
                "walk": walkable(t), "kind": kind, "layer": layer,
                "s": ax.project(p), "xy": [p.x, p.y],
            })
    hits.sort(key=lambda h: h["s"])

    # cluster into locations (30 m along-axis)
    locs = []
    for h in hits:
        if locs and h["s"] - locs[-1]["s_max"] <= 30.0:
            L = locs[-1]
            L["s_max"] = h["s"]; L["members"].append(h)
        else:
            locs.append({"s_min": h["s"], "s_max": h["s"], "members": [h]})
    for L in locs:
        L["s"] = (L["s_min"] + L["s_max"]) / 2
        L["walkable"] = any(m["walk"] for m in L["members"])
        L["kinds"] = sorted({m["kind"] for m in L["members"]})
        L["names"] = sorted({m["name"] for m in L["members"] if m["name"]})
        L["n_ways"] = len(L["members"])
        p = ax.interpolate(L["s"])
        L["ll"] = [round(v,7) for v in to_deg(p).coords[0]]

    walk_locs = [L for L in locs if L["walkable"]]
    km = ax.length / 1000.0
    gaps = np.diff([L["s"] for L in walk_locs]) if len(walk_locs) > 1 else np.array([0.0])
    rep = {
        "label": label,
        "length_m": round(ax.length, 1),
        "n_crossing_ways": len(hits),
        "n_locations": len(locs),
        "n_walkable_locations": len(walk_locs),
        "walkable_per_km": round(len(walk_locs)/km, 2),
        "all_per_km": round(len(locs)/km, 2),
        "gap_mean_m": round(float(gaps.mean()), 1),
        "gap_median_m": round(float(np.median(gaps)), 1),
        "gap_max_m": round(float(gaps.max()), 1),
        "gap_p90_m": round(float(np.percentile(gaps, 90)), 1),
        "gaps_over_300m": int((gaps > 300).sum()),
        "locations": [{k: L[k] for k in ("s","ll","walkable","kinds","names","n_ways")}
                      for L in locs],
    }
    return rep


print("\n=== A1  crossing inventory: 市民大道 ===")
civic_rep = crossing_report(axis_m, "市民大道 (高架軸線)", CIVIC_IDS, "市民大道")
for k in ("length_m","n_crossing_ways","n_locations","n_walkable_locations",
          "walkable_per_km","gap_mean_m","gap_median_m","gap_max_m","gaps_over_300m"):
    print(f"  {k:24s} {civic_rep[k]}")

# ------------------------------------------------------ control corridors ----
CONTROLS = ["八德路", "忠孝東路", "南京東路", "長安東路", "民生東路"]
def build_control(prefix):
    sel = [w for w in ways
           if w["t"].get("name","").startswith(prefix)
           and w["t"].get("highway") in ("trunk","primary","secondary","tertiary")
           and w["t"].get("bridge") != "yes"]
    pts = np.array([ll_to_m(lon,lat) for w in sel for lon,lat in w["c"]])
    if len(pts) < 20: return None, set()
    pts = pts[(pts[:,0]>=X0) & (pts[:,0]<=X1)]
    if len(pts) < 20: return None, set()
    pts = pts[np.argsort(pts[:,0])]
    bins = np.arange(pts[:,0].min(), pts[:,0].max()+20, 20)
    idx = np.digitize(pts[:,0], bins)
    xs, ys = [], []
    for b in range(1, len(bins)+1):
        m = idx == b
        if m.sum() >= 2:
            xs.append(float(np.median(pts[m,0]))); ys.append(float(np.median(pts[m,1])))
    xs, ys = np.array(xs), np.array(ys)
    k = 9
    roll = np.array([np.median(ys[max(0,i-k//2):i+k//2+1]) for i in range(len(ys))])
    keep = np.abs(ys-roll) <= 60
    xs, ys = xs[keep], ys[keep]
    ys = np.convolve(ys, np.ones(5)/5, mode="same"); ys[:2], ys[-2:] = ys[2], ys[-3]
    ids = {w["id"] for w in ways if w["t"].get("name","").startswith(prefix)}
    return LineString(np.c_[xs,ys]), ids

control_reps = []
for c in CONTROLS:
    ax_c, ids_c = build_control(c)
    if ax_c is None:
        print(f"  [skip] {c}: not enough geometry in the easting window"); continue
    r = crossing_report(ax_c, c, ids_c, c)
    r["axis_ll"] = [[round(v,7) for v in p] for p in to_deg(ax_c).coords]
    control_reps.append(r)
    print(f"\n=== A1  control: {c} ===")
    print(f"  length {r['length_m']:.0f} m | walkable crossings {r['n_walkable_locations']}"
          f" ({r['walkable_per_km']}/km) | mean gap {r['gap_mean_m']} m | max gap {r['gap_max_m']} m")

json.dump({"civic": civic_rep, "controls": control_reps},
          open("../data/processed/a1_crossings.json","w"), ensure_ascii=False)
print("\nwrote data/processed/a1_crossings.json")
