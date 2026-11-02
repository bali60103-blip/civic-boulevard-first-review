"""Stage 4 — 南北分隔證據 B: 繞路係數 (pedestrian detour factor).

THE measurement. Every 100 m along the axis we place a pair of points 150 m
north and 150 m south of the centreline, snap both onto the real pedestrian
network, and route between them. Straight-line need = 300 m.

  detour factor = network distance / 300 m

A permeable street gives ~1.2-1.4 (you walk to the corner and cross). A
barrier gives 2, 3, 5 - because the only way across is far away. The measure
needs no definition of "a crossing" at all, so it cannot be gamed by OSM
tagging quirks, and it is directly interpretable as walking metres lost.

The same probe is run on the five parallel E-W arterials in the same district
as controls. It also records WHERE each path crosses the axis, which yields the
*functional* crossing inventory (as opposed to the geometric one in stage 3).
"""
import json, math, collections
import numpy as np
import networkx as nx
from shapely.geometry import LineString, Point
import pedgraph
from geo import to_deg, ll_to_m, TO_M

STEP   = 100.0   # probe spacing along the axis
OFFSET = 150.0   # perpendicular offset each side

G, ids, pts, tree, coord = pedgraph.build()
GIANT = pedgraph.giant(G)
print(f'  snapping restricted to giant component: {len(GIANT):,} nodes')

axis = json.load(open("../data/processed/axis.json"))
axis_m = LineString(axis["axis_m"])
ways = json.load(open("../data/processed/osm_ways.json"))
X0, X1 = axis_m.bounds[0], axis_m.bounds[2]


def normal_at(ls, s, eps=15.0):
    a = ls.interpolate(max(0, s-eps)); b = ls.interpolate(min(ls.length, s+eps))
    dx, dy = b.x-a.x, b.y-a.y
    n = math.hypot(dx, dy) or 1.0
    return (-dy/n, dx/n)          # left normal


def probe(ls, label, offset=OFFSET, step=STEP):
    n = int(ls.length // step)
    rows = []
    for i in range(1, n):
        s = i*step
        p = ls.interpolate(s)
        nx_, ny_ = normal_at(ls, s)
        A = (p.x + nx_*offset, p.y + ny_*offset)
        B = (p.x - nx_*offset, p.y - ny_*offset)
        na, da = pedgraph.snap(tree, ids, pts, A, allowed=GIANT)
        nb, db = pedgraph.snap(tree, ids, pts, B, allowed=GIANT)
        row = {"s": round(s,1), "ll": [round(v,7) for v in to_deg(p).coords[0]]}
        if na is None or nb is None:
            row.update(status="no_network"); rows.append(row); continue
        if na == nb:
            row.update(status="degenerate"); rows.append(row); continue
        try:
            d, path = nx.single_source_dijkstra(G, na, weight="w", target=nb,
                                                cutoff=6000)
        except (nx.NetworkXNoPath, KeyError):
            row.update(status="no_path"); rows.append(row); continue
        if d is None:
            row.update(status="no_path"); rows.append(row); continue
        straight = 2*offset
        # where does the path cross the axis?
        xs = None
        for u, v in zip(path, path[1:]):
            seg = LineString([coord[u], coord[v]])
            it = seg.intersection(axis_m)
            if not it.is_empty:
                q = it if it.geom_type == "Point" else list(it.geoms)[0] if it.geom_type=="MultiPoint" else it.interpolate(0.5)
                xs = ls.project(Point(q.x, q.y))
                break
        row.update(status="ok",
                   net_m=round(d + (da or 0) + (db or 0), 1),
                   straight_m=straight,
                   detour=round((d + (da or 0) + (db or 0))/straight, 3),
                   snap_a=round(da,1), snap_b=round(db,1),
                   cross_s=None if xs is None else round(float(xs),1),
                   n_edges=len(path)-1)
        rows.append(row)
    ok = [r for r in rows if r["status"] == "ok"]
    det = np.array([r["detour"] for r in ok])
    extra = np.array([r["net_m"] - r["straight_m"] for r in ok])
    rep = {
        "label": label, "length_m": round(ls.length,1),
        "offset_m": offset, "step_m": step,
        "n_probes": len(rows), "n_ok": len(ok),
        "n_failed": len(rows)-len(ok),
        "fail_reasons": dict(collections.Counter(r["status"] for r in rows if r["status"]!="ok")),
        "detour_mean": round(float(det.mean()),3),
        "detour_median": round(float(np.median(det)),3),
        "detour_p90": round(float(np.percentile(det,90)),3),
        "detour_max": round(float(det.max()),3),
        "extra_walk_mean_m": round(float(extra.mean()),1),
        "extra_walk_median_m": round(float(np.median(extra)),1),
        "share_over_2x": round(float((det>2).mean()),4),
        "share_over_3x": round(float((det>3).mean()),4),
        "rows": rows,
    }
    return rep


print(f"\n=== B  detour probe: 市民大道 (offset {OFFSET:.0f} m, step {STEP:.0f} m) ===")
civic = probe(axis_m, "市民大道")
civic_offsets = {}
for off in (100.0, 150.0, 250.0):
    r = probe(axis_m, f"市民大道@{off:.0f}m", offset=off)
    civic_offsets[int(off)] = {k: v for k, v in r.items() if k != "rows"}
    print(f"  offset {off:5.0f} m -> detour mean {r['detour_mean']:.3f} median {r['detour_median']:.3f} "
          f"p90 {r['detour_p90']:.2f} | extra {r['extra_walk_mean_m']:.0f} m | ok {r['n_ok']}/{r['n_probes']}")
for k in ("n_probes","n_ok","fail_reasons","detour_mean","detour_median",
          "detour_p90","detour_max","extra_walk_mean_m","share_over_2x","share_over_3x"):
    print(f"  {k:22s} {civic[k]}")

# --------------------------------------------------------- control corridors --
def build_control(prefix):
    sel = [w for w in ways if w["t"].get("name","").startswith(prefix)
           and w["t"].get("highway") in ("trunk","primary","secondary","tertiary")
           and w["t"].get("bridge") != "yes"]
    P = np.array([ll_to_m(lon,lat) for w in sel for lon,lat in w["c"]])
    if len(P) < 20: return None
    P = P[(P[:,0]>=X0) & (P[:,0]<=X1)]
    if len(P) < 20: return None
    P = P[np.argsort(P[:,0])]
    bins = np.arange(P[:,0].min(), P[:,0].max()+20, 20)
    idx = np.digitize(P[:,0], bins)
    xs, ys = [], []
    for b in range(1, len(bins)+1):
        m = idx==b
        if m.sum()>=2: xs.append(float(np.median(P[m,0]))); ys.append(float(np.median(P[m,1])))
    xs, ys = np.array(xs), np.array(ys)
    roll = np.array([np.median(ys[max(0,i-4):i+5]) for i in range(len(ys))])
    keep = np.abs(ys-roll)<=60
    xs, ys = xs[keep], ys[keep]
    ys = np.convolve(ys, np.ones(5)/5, mode="same"); ys[:2], ys[-2:] = ys[2], ys[-3]
    return LineString(np.c_[xs,ys])

controls = []
for c in ["八德路","忠孝東路","南京東路","長安東路","民生東路"]:
    ls = build_control(c)
    if ls is None: continue
    r = probe(ls, c)
    r["axis_ll"] = [[round(v,7) for v in p] for p in to_deg(ls).coords]
    controls.append(r)
    print(f"  {c:8s} len {r['length_m']:6.0f} m | detour mean {r['detour_mean']:.2f} "
          f"median {r['detour_median']:.2f} p90 {r['detour_p90']:.2f} | "
          f"extra walk {r['extra_walk_mean_m']:6.1f} m | >2x {r['share_over_2x']*100:.0f}%")

json.dump({"civic": civic, "civic_offsets": civic_offsets, "controls": controls},
          open("../data/processed/b_detour.json","w"), ensure_ascii=False)
print("\nwrote data/processed/b_detour.json")
