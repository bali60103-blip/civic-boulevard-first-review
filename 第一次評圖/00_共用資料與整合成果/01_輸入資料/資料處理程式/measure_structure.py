"""Stage 5 — 南北分隔證據 C/D/E: structural, institutional and historical.

  C 斷頭路   N-S streets whose end dies within 60 m of the axis without
             continuing across = severed street. Counted per km and compared
             with the control corridors.
  D 行政界線  Does 市民大道 double as an administrative boundary (里/區界)?
             If the city's own administrative geometry uses the road as an
             edge, the divide is institutional, not only physical.
  E 鐵路      The corridor sits on the old 縱貫線 railway trench. If the
             undergrounded railway still follows the axis, the severance
             predates the road by a century and the road inherited it.
"""
import json, math, collections
import numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from geo import to_m, to_deg, ll_to_m
import pedgraph

axis = json.load(open("../data/processed/axis.json"))
axis_m = LineString(axis["axis_m"])
ways  = json.load(open("../data/processed/osm_ways.json"))
areas = json.load(open("../data/processed/osm_areas.json"))
CIVIC = set(axis["civic_way_ids"])
X0, X1 = axis_m.bounds[0], axis_m.bounds[2]

print("projecting ...")
GM = {w["id"]: to_m(LineString(w["c"])) for w in ways}

# ------------------------------------------------------------- C 斷頭路 ------
def severed(ax, label, exclude_ids, name_prefix, near=60.0, min_len=40.0):
    """A street is 'severed' if one of its endpoints is within `near` of the
    axis, the way is at least `min_len` long, it runs mostly perpendicular to
    the axis (so it is a N-S street, not a frontage road), and neither the way
    nor anything connected to it continues to the other side of the axis."""
    axbuf = ax.buffer(near)
    # which node ids sit on ways that cross the axis? used to test continuation
    crossing_nodes = set()
    for w in ways:
        if w["id"] in exclude_ids: continue
        if GM[w["id"]].crosses(ax):
            crossing_nodes.update(w["n"])
    res = []
    for w in ways:
        if w["id"] in exclude_ids: continue
        t = w["t"]
        if name_prefix and t.get("name","").startswith(name_prefix): continue
        if t.get("highway") is None: continue
        if not pedgraph.walkable(t): continue
        g = GM[w["id"]]
        if g.length < min_len: continue
        if not g.intersects(axbuf): continue
        if g.crosses(ax): continue
        a, b = Point(g.coords[0]), Point(g.coords[-1])
        da, db = ax.distance(a), ax.distance(b)
        tip, far = (a, b) if da < db else (b, a)
        if min(da, db) > near: continue
        if max(da, db) < min_len: continue          # both ends hug the axis -> frontage
        # perpendicularity: the way must approach the axis, not run along it
        sa, sb = ax.project(a), ax.project(b)
        along = abs(sa - sb)
        across = abs(da - db)
        if across <= along: continue                # runs more along than across
        # does the tip connect to anything that crosses?
        tip_ref = w["n"][0] if da < db else w["n"][-1]
        if tip_ref in crossing_nodes: continue
        s = ax.project(tip)
        res.append({"id": w["id"], "name": t.get("name"), "hw": t.get("highway"),
                    "len_m": round(g.length,1), "tip_dist_m": round(min(da,db),1),
                    "s": round(float(s),1),
                    "ll": [round(v,7) for v in to_deg(tip).coords[0]]})
    km = ax.length/1000
    return {"label": label, "length_m": round(ax.length,1), "n": len(res),
            "per_km": round(len(res)/km, 2), "items": res}

print("\n=== C  斷頭路 (severed N-S streets) ===")
civic_sev = severed(axis_m, "市民大道", CIVIC, "市民大道")
print(f"  市民大道: {civic_sev['n']} severed streets over {civic_sev['length_m']:.0f} m "
      f"= {civic_sev['per_km']}/km")

def build_control(prefix):
    sel = [w for w in ways if w["t"].get("name","").startswith(prefix)
           and w["t"].get("highway") in ("trunk","primary","secondary","tertiary")
           and w["t"].get("bridge") != "yes"]
    P = np.array([ll_to_m(lon,lat) for w in sel for lon,lat in w["c"]])
    if len(P)<20: return None, set()
    P = P[(P[:,0]>=X0)&(P[:,0]<=X1)]
    if len(P)<20: return None, set()
    P = P[np.argsort(P[:,0])]
    bins = np.arange(P[:,0].min(), P[:,0].max()+20, 20); idx = np.digitize(P[:,0], bins)
    xs, ys = [], []
    for b in range(1,len(bins)+1):
        m = idx==b
        if m.sum()>=2: xs.append(float(np.median(P[m,0]))); ys.append(float(np.median(P[m,1])))
    xs, ys = np.array(xs), np.array(ys)
    roll = np.array([np.median(ys[max(0,i-4):i+5]) for i in range(len(ys))])
    k = np.abs(ys-roll)<=60; xs, ys = xs[k], ys[k]
    ys = np.convolve(ys, np.ones(5)/5, mode="same"); ys[:2], ys[-2:] = ys[2], ys[-3]
    return LineString(np.c_[xs,ys]), {w["id"] for w in ways if w["t"].get("name","").startswith(prefix)}

sev_controls = []
for c in ["八德路","忠孝東路","南京東路","長安東路","民生東路"]:
    ls, ids_c = build_control(c)
    if ls is None: continue
    r = severed(ls, c, ids_c, c)
    r.pop("items")
    sev_controls.append(r)
    print(f"  {c:8s}: {r['n']:3d} severed over {r['length_m']:.0f} m = {r['per_km']}/km")

# --------------------------------------------------------- D 行政界線 --------
print("\n=== D  行政界線 coincidence (里界 admin_level=9) ===")
adm = [a for a in areas if a["t"].get("boundary")=="administrative"
       and a["t"].get("admin_level") in ("7","8","9")]
tot = collections.Counter()
coinc = collections.Counter()
buf = axis_m.buffer(35.0)
for a in adm:
    g = to_m(LineString(a["c"]))
    lvl = a["t"].get("admin_level")
    tot[lvl] += g.length
    if g.intersects(buf):
        coinc[lvl] += g.intersection(buf).length
for lvl in sorted(coinc):
    print(f"  admin_level={lvl}: {coinc[lvl]:,.0f} m of boundary line runs within 35 m of the axis")
# how much of the axis itself is used as an administrative boundary?
named_bnd = []
for a in adm:
    if not a["t"].get("name"): continue
    g = to_m(LineString(a["c"]))
    if g.intersects(buf):
        named_bnd.append({"name": a["t"]["name"], "level": str(a["t"].get("admin_level")),
                          "len_in_corridor_m": round(g.intersection(buf).length,1),
                          "s": round(float(axis_m.project(g.interpolate(0.5, normalized=True))),1),
                          "ll": [[round(v,7) for v in c] for c in to_deg(g).coords]})
adm_union = unary_union([to_m(LineString(a["c"])) for a in adm if to_m(LineString(a["c"])).intersects(buf)])
on_axis = axis_m.buffer(35.0).intersection(adm_union).length if not adm_union.is_empty else 0.0
STEP = 25.0
adm_cov = adm_tot = 0
for s in np.arange(0, axis_m.length, STEP):
    p = axis_m.interpolate(float(s)); adm_tot += 1
    if not adm_union.is_empty and adm_union.distance(p) <= 35.0: adm_cov += 1
ADMIN_SHARE = adm_cov/adm_tot*100
print(f"  share of the 6.5 km axis that doubles as a 里/區 boundary (±35 m): "
      f"{ADMIN_SHARE:.1f}%  ({adm_cov*STEP:,.0f} m of {axis_m.length:,.0f} m)")

# ------------------------------------------------------------- E 鐵路 --------
print("\n=== E  railway coincidence (縱貫線, undergrounded) ===")
rails = [w for w in ways if w.get("_rail") and w["t"].get("railway") in
         ("rail","disused","abandoned","construction","subway")]
rail_by_kind = collections.defaultdict(float)
rail_near = collections.defaultdict(float)
axbuf120 = axis_m.buffer(120.0)
for w in rails:
    g = GM[w["id"]]
    kind = w["t"].get("railway")
    nm = w["t"].get("name","")
    key = f"{kind}|{'縱貫線' if '縱貫線' in nm else ('捷運' if kind=='subway' else 'other')}"
    rail_by_kind[key] += g.length
    if g.intersects(axbuf120):
        rail_near[key] += g.intersection(axbuf120).length
for k in sorted(rail_near, key=lambda k:-rail_near[k])[:8]:
    print(f"  {k:22s} {rail_near[k]:8,.0f} m within 120 m of the axis")
# how much of the axis has the 縱貫線 underneath?
zg = unary_union([GM[w["id"]] for w in rails if "縱貫線" in w["t"].get("name","")])
rail_cov = rail_tot = 0
for s in np.arange(0, axis_m.length, STEP):
    p = axis_m.interpolate(float(s)); rail_tot += 1
    if not zg.is_empty and zg.distance(p) <= 120.0: rail_cov += 1
RAIL_SHARE = rail_cov/rail_tot*100
print(f"  share of the axis with the undergrounded 縱貫線 within 120 m: "
      f"{RAIL_SHARE:.1f}%  ({rail_cov*STEP:,.0f} m)")

json.dump({"severed_civic": civic_sev, "severed_controls": sev_controls,
           "admin_share_pct": round(ADMIN_SHARE,1),
           "admin_covered_m": round(adm_cov*STEP,1),
           "admin_boundary_len_by_level": {k: round(v,1) for k,v in coinc.items()},
           "rail_near_axis_m": {k: round(v,1) for k,v in rail_near.items()},
           "rail_axis_share_pct": round(RAIL_SHARE,1),
           "rail_covered_m": round(rail_cov*STEP,1),
           "named_boundaries": named_bnd},
          open("../data/processed/c_structure.json","w"), ensure_ascii=False)
print("\nwrote data/processed/c_structure.json")
