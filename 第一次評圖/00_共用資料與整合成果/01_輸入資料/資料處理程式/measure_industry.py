"""Stage 6 — 產業分布 + 區域特色 + 南北分隔證據 F.

For every 200 m of axis and each side, count POIs by industry sector inside a
0-300 m band. Then ask the only question that makes the N/S contrast
meaningful:

  Does the industry mix differ across 市民大道 MORE than it differs across an
  arbitrary line drawn 300 m north (or south) of it?

Without that placebo, "north and south are different" is vacuous — in a dense
city any two neighbouring strips differ. The placebo lines sit wholly inside
one side, so they measure ordinary spatial heterogeneity. The axis has to beat
them to count as evidence of a divide.

Divergence measure: Jensen-Shannon distance between the two sector-share
vectors (0 = identical mix, 1 = disjoint), plus a chi-square test of
independence on the raw counts.
"""
import json, math, collections
import numpy as np
from scipy.stats import chi2_contingency
from shapely.geometry import LineString, Point
from shapely.strtree import STRtree
from geo import to_m, to_deg, ll_to_m, TO_M
from sectors import classify, SECTOR_KEYS

BAND = 300.0
SEG  = 200.0

axis = json.load(open("../data/processed/axis.json"))
A = LineString(axis["axis_m"])
nodes = json.load(open("../data/processed/osm_nodes.json"))
areas = json.load(open("../data/processed/osm_areas.json"))

# ------------------------------------------------------------- POI table ----
pois = []
seen = set()
for n in nodes:
    s = classify(n["t"])
    if not s: continue
    x, y = TO_M.transform(n["lon"], n["lat"])
    pois.append({"src":"n","id":n["id"],"x":x,"y":y,"sec":s,
                 "name":n["t"].get("name"),"t":n["t"]})
    seen.add(("n", n["id"]))
for a in areas:
    s = classify(a["t"])
    if not s: continue
    if ("w", a["id"]) in seen: continue
    xy = [TO_M.transform(lon, lat) for lon, lat in a["c"]]
    x = sum(p[0] for p in xy)/len(xy); y = sum(p[1] for p in xy)/len(xy)
    pois.append({"src":"w","id":a["id"],"x":x,"y":y,"sec":s,
                 "name":a["t"].get("name"),"t":a["t"]})
print(f"classified POIs in the extraction bbox: {len(pois):,}")
print("  by sector:", dict(collections.Counter(p['sec'] for p in pois).most_common()))

# ------------------------------------------------- side / chainage / band ----
def side_of(line, x, y):
    """+1 = left of the line's direction (= north here), -1 = right."""
    s = line.project(Point(x, y))
    eps = 15.0
    a = line.interpolate(max(0, s-eps)); b = line.interpolate(min(line.length, s+eps))
    return 1 if ((b.x-a.x)*(y-a.y) - (b.y-a.y)*(x-a.x)) > 0 else -1

def tabulate(line, label):
    """counts[side][seg][sector] for POIs within BAND of `line`."""
    buf = line.buffer(BAND)
    n_seg = int(round(line.length/SEG))
    cnt = {1: np.zeros((n_seg, len(SECTOR_KEYS)), int),
          -1: np.zeros((n_seg, len(SECTOR_KEYS)), int)}
    kept = []
    SI = {s:i for i,s in enumerate(SECTOR_KEYS)}
    for p in pois:
        pt = Point(p["x"], p["y"])
        if not buf.contains(pt): continue
        d = line.distance(pt)
        s = line.project(pt)
        seg = min(int(s//SEG), n_seg-1)
        sd = side_of(line, p["x"], p["y"])
        cnt[sd][seg, SI[p["sec"]]] += 1
        kept.append((p, sd, seg, d, s))
    return cnt, kept, n_seg

print(f"\n=== F  industry mix north vs south of 市民大道 (0-{BAND:.0f} m band) ===")
cnt, kept, n_seg = tabulate(A, "市民大道")
N = cnt[1].sum(0); S = cnt[-1].sum(0)
print(f"POIs inside the corridor: north {N.sum():,}  south {S.sum():,}")

def js_dist(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    if a.sum() == 0 or b.sum() == 0: return None
    p, q = a/a.sum(), b/b.sum()
    m = (p+q)/2
    def kl(u, v):
        mask = u > 0
        return float(np.sum(u[mask]*np.log2(u[mask]/v[mask])))
    return math.sqrt(max(0.0, 0.5*kl(p,m) + 0.5*kl(q,m)))

overall_js = js_dist(N, S)
tab = np.c_[N, S]
tab = tab[tab.sum(1) > 0]
chi2, pval, dof, _ = chi2_contingency(tab)
print(f"  whole-corridor JS distance (N vs S mix): {overall_js:.4f}")
print(f"  chi-square independence test: chi2={chi2:.1f} dof={dof} p={pval:.3e}")
print(f"\n  {'sector':10s} {'north':>7s} {'south':>7s} {'N share':>8s} {'S share':>8s} {'N/S':>7s}")
for i, k in enumerate(SECTOR_KEYS):
    ns, ss = N[i], S[i]
    if ns+ss == 0: continue
    print(f"  {k:10s} {ns:7d} {ss:7d} {ns/N.sum()*100:7.2f}% {ss/S.sum()*100:7.2f}% "
          f"{(ns/max(ss,1)):7.2f}")

# ------------------------------------------------------------- placebo -------
def offset_line(line, d):
    """Parallel line offset d metres (positive = left/north)."""
    try:
        o = line.parallel_offset(abs(d), "left" if d > 0 else "right", join_style=2)
    except Exception:
        return None
    if o.is_empty: return None
    if o.geom_type == "MultiLineString":
        o = max(o.geoms, key=lambda g: g.length)
    return o

print(f"\n=== F  placebo lines (same measurement, arbitrary line inside one side) ===")
placebos = []
for d in (300.0, 450.0, -300.0, -450.0):
    L = offset_line(A, d)
    if L is None or L.length < 2000: 
        print(f"  offset {d:+.0f} m: geometry failed"); continue
    c2, _, ns2 = tabulate(L, f"placebo{d:+.0f}")
    n2, s2 = c2[1].sum(0), c2[-1].sum(0)
    j = js_dist(n2, s2)
    t2 = np.c_[n2, s2]; t2 = t2[t2.sum(1) > 0]
    ch, pv, df, _ = chi2_contingency(t2) if len(t2) > 1 else (float('nan'),1.0,0,None)
    placebos.append({"offset_m": d, "length_m": round(L.length,1),
                     "n_poi_a": int(n2.sum()), "n_poi_b": int(s2.sum()),
                     "js": None if j is None else round(j,4),
                     "chi2": round(float(ch),1), "p": float(pv)})
    print(f"  offset {d:+5.0f} m  (len {L.length:5.0f} m)  JS={j:.4f}  "
          f"chi2={ch:7.1f}  p={pv:.2e}   n={n2.sum():,}/{s2.sum():,}")

# --------------------------------------------------------- per-segment JS ----
seg_rows = []
for i in range(n_seg):
    a, b = cnt[1][i], cnt[-1][i]
    mid = A.interpolate((i+0.5)*SEG)
    j = js_dist(a, b)
    seg_rows.append({
        "i": i, "s": round((i+0.5)*SEG,1),
        "ll": [round(v,7) for v in to_deg(mid).coords[0]],
        "n_north": int(a.sum()), "n_south": int(b.sum()),
        "js": None if j is None else round(j,4),
        "north": {SECTOR_KEYS[k]: int(a[k]) for k in range(len(SECTOR_KEYS)) if a[k]},
        "south": {SECTOR_KEYS[k]: int(b[k]) for k in range(len(SECTOR_KEYS)) if b[k]},
    })
valid = [r for r in seg_rows if r["js"] is not None and r["n_north"]>=15 and r["n_south"]>=15]
print(f"\n  per-segment JS (segments with >=15 POIs each side: {len(valid)}/{n_seg}): "
      f"mean {np.mean([r['js'] for r in valid]):.4f}  max {max(r['js'] for r in valid):.4f}")
print("  most divergent segments:")
for r in sorted(valid, key=lambda r:-r["js"])[:6]:
    top_n = max(r["north"], key=r["north"].get); top_s = max(r["south"], key=r["south"].get)
    print(f"    s={r['s']:6.0f} JS={r['js']:.3f}  N={r['n_north']:4d} (top {top_n})  "
          f"S={r['n_south']:4d} (top {top_s})")

json.dump({
    "band_m": BAND, "seg_m": SEG, "sectors": SECTOR_KEYS,
    "north_totals": {SECTOR_KEYS[i]: int(N[i]) for i in range(len(SECTOR_KEYS))},
    "south_totals": {SECTOR_KEYS[i]: int(S[i]) for i in range(len(SECTOR_KEYS))},
    "overall_js": round(overall_js,4), "chi2": round(float(chi2),1),
    "chi2_p": float(pval), "chi2_dof": int(dof),
    "placebos": placebos, "segments": seg_rows,
    "n_poi_total": len(pois),
}, open("../data/processed/f_industry.json","w"), ensure_ascii=False)

# also dump the POI point table for the map (lon/lat + sector only)
pt = [{"ll":[round(v,6) for v in to_deg(Point(p["x"],p["y"])).coords[0]],
       "s":p["sec"], "n":p["name"]} for p in pois]
json.dump(pt, open("../data/processed/poi_points.json","w"), ensure_ascii=False)
print(f"\nwrote data/processed/f_industry.json and poi_points.json ({len(pt):,} points)")
