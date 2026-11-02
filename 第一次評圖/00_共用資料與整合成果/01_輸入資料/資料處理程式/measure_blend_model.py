"""Stage 9 — what the site model knows that OSM does not, and what it only
PRETENDS to know.

  H 物理阻隔     piers (clustered into bents), guardrail, soundwall, median.
  I 建築量體     19,592 separated masses -> north vs south, but 42.4% of the
                 heights are the literal default 12.0 m, so the comparison is
                 also run on the real-height subset only.
  J 行道樹樹冠   REJECTED. The 10,000 canopy meshes are byte-identical
                 placeholders (std < 1e-5 on every dimension), so canopy
                 volume is NOT measurable from this model. The earlier
                 dossier's limitation stands; no number is reported.
"""
import json, math, collections
import numpy as np
from shapely.geometry import LineString, Point
from geo import to_deg

G = json.load(open("../data/processed/blend_georef.json"))
TX, TY = G["tx"], G["ty"]
axis = json.load(open("../data/processed/axis.json"))
A = LineString(axis["axis_m"])
SEG = 200.0
n_seg = int(round(A.length/SEG))

def xf(a):
    a = np.asarray(a, dtype=np.float64).copy()
    a[..., 0] += TX; a[..., 1] += TY
    return a

def side_chain(x, y, line=A, eps=15.0):
    p = Point(x, y); s = line.project(p)
    a = line.interpolate(max(0, s-eps)); b = line.interpolate(min(line.length, s+eps))
    sd = 1 if ((b.x-a.x)*(y-a.y) - (b.y-a.y)*(x-a.x)) > 0 else -1
    return sd, s, line.distance(p)

out = {"georef": G}

# =============================================================== H 物理阻隔 ==
piers = json.load(open("../data/blend/piers.json"))
P = xf([[p["cx"], p["cy"]] for p in piers])
rows = []
for p, (x, y) in zip(piers, P):
    sd, s, d = side_chain(x, y)
    rows.append({**p, "s": s, "d": d, "side": sd, "area": p["w"]*p["d"],
                 "ll": [round(v,7) for v in to_deg(Point(x,y)).coords[0]]})
on = [r for r in rows if r["d"] <= 120]

# A pier BENT is a row of columns across the deck. Cluster columns whose
# chainage differs by <15 m, otherwise "spacing" just measures column pitch
# within one bent (which came out at 3.1 m - meaningless as a span).
ss = np.array(sorted(r["s"] for r in on))
bent_ids, cur = [], [ss[0]]
bents = []
for v in ss[1:]:
    if v - cur[-1] <= 15.0:
        cur.append(v)
    else:
        bents.append(cur); cur = [v]
bents.append(cur)
bent_s = np.array([np.mean(b) for b in bents])
bent_gap = np.diff(bent_s)
cols_per_bent = np.array([len(b) for b in bents])

print("=== H  physical obstruction inventory (from the site model) ===")
print(f"  pier columns: {len(rows)} total, {len(on)} within 120 m of the axis")
print(f"  grouped into {len(bents)} pier bents (columns within 15 m of chainage)")
print(f"  columns per bent: median {np.median(cols_per_bent):.0f}, max {cols_per_bent.max()}")
print(f"  BENT SPACING along the axis: median {np.median(bent_gap):.1f} m, "
      f"mean {bent_gap.mean():.1f} m, min {bent_gap.min():.1f} m, max {bent_gap.max():.1f} m")
foot = sum(r["area"] for r in on)
print(f"  column footprint: {foot:,.0f} m2 total, {foot/len(on):.1f} m2 each "
      f"({np.median([r['w'] for r in on]):.1f} x {np.median([r['d'] for r in on]):.1f} m), "
      f"height median {np.median([r['h'] for r in on]):.1f} m")
underdeck = [r for r in rows if r["d"] <= 30]
print(f"  columns standing directly under the deck (<=30 m from centreline): "
      f"{len(underdeck)}, {sum(r['area'] for r in underdeck):,.0f} m2 of ground taken")

lin = json.load(open("../data/blend/linear_elements.json"))
deck = lin["Civic_Blvd_Elevated_Deck"]; med = lin["Civic_Blvd_Median_分隔島"]
gr = lin["Guardrail_1.1m_Civic_Blvd_Elevated_Deck"]; sw = lin["Soundwall_3.0m_Civic_Blvd_Elevated_Deck"]
gr_h, sw_h = gr["z1"]-gr["z0"], sw["z1"]-sw["z0"]
gr_len = (gr["area_total"]-gr["area_horizontal"])/gr_h/2
sw_len = (sw["area_total"]-sw["area_horizontal"])/sw_h/2
same_geom = abs(gr_len-sw_len) < 100
print(f"  elevated deck: {deck['area_horizontal']:,.0f} m2 of horizontal surface "
      f"= {deck['area_horizontal']/1e4:.1f} ha of city roofed over, deck soffit "
      f"z={deck['z0']:.1f} m, top z={deck['z1']:.1f} m")
print(f"  at-grade median 分隔島: {med['area_horizontal']:,.0f} m2 "
      f"= {med['area_horizontal']/1e4:.1f} ha of continuous kerbed island")
print(f"  guardrail {gr_h:.2f} m high, {gr_len:,.0f} m of run "
      f"(~4 deck edges x 6.4 km -> {gr_len/4/1000:.2f} km per edge)")
print(f"  soundwall {sw_h:.2f} m high, {sw_len:,.0f} m of run")
if same_geom:
    print("  [CAVEAT] guardrail and soundwall have the same run length and the same "
          "vertex count -> in this model they are the SAME generated edge at two "
          "heights, i.e. a design option, not two separately surveyed objects.")

infra = json.load(open("../data/blend/infra_points.json"))
inf_sum = {}
for k, items in infra.items():
    if not items: continue
    Q = xf([[i["cx"], i["cy"]] for i in items])
    recs, near = [], 0
    for it, (x, y) in zip(items, Q):
        sd, s, d = side_chain(x, y)
        recs.append({"name": it["name"], "s": round(s,1), "d": round(d,1), "side": sd,
                     "h": round(it["h"],1), "w": round(it["w"],1), "dp": round(it["d"],1),
                     "ll": [round(v,7) for v in to_deg(Point(x,y)).coords[0]]})
        if d <= 150: near += 1
    inf_sum[k] = {"total": len(items), "within_150m_of_axis": near, "items": recs}
    print(f"  {k:14s} {len(items):3d} objects, {near:3d} within 150 m of the axis")

# crossing supply per km, from the model's own real objects
fb = inf_sum.get("footbridges", {}).get("within_150m_of_axis", 0)
up = inf_sum.get("underpasses", {}).get("within_150m_of_axis", 0)
print(f"\n  GRADE-SEPARATED CROSSINGS OF THE 6.53 km AXIS: {fb} footbridges + "
      f"{up} underpasses = {fb+up} -> one every "
      f"{A.length/max(fb+up,1)/1000:.2f} km" if fb+up else
      f"\n  GRADE-SEPARATED CROSSINGS OF THE AXIS: {fb} footbridges + {up} underpasses = 0")

out["obstruction"] = {
    "n_pier_columns": len(rows), "n_pier_columns_near_axis": len(on),
    "n_pier_bents": len(bents),
    "columns_per_bent_median": int(np.median(cols_per_bent)),
    "bent_spacing_median_m": round(float(np.median(bent_gap)),1),
    "bent_spacing_mean_m": round(float(bent_gap.mean()),1),
    "bent_spacing_min_m": round(float(bent_gap.min()),1),
    "bent_spacing_max_m": round(float(bent_gap.max()),1),
    "column_footprint_total_m2": round(foot,1),
    "column_footprint_each_m2": round(foot/len(on),1),
    "column_height_median_m": round(float(np.median([r['h'] for r in on])),1),
    "n_columns_under_deck": len(underdeck),
    "ground_taken_under_deck_m2": round(sum(r['area'] for r in underdeck),1),
    "deck_area_m2": round(deck["area_horizontal"],1),
    "deck_soffit_z_m": round(deck["z0"],2), "deck_top_z_m": round(deck["z1"],2),
    "median_area_m2": round(med["area_horizontal"],1),
    "guardrail_height_m": round(gr_h,2), "guardrail_run_m": round(gr_len,1),
    "soundwall_height_m": round(sw_h,2), "soundwall_run_m": round(sw_len,1),
    "guardrail_soundwall_same_geometry": bool(same_geom),
    "footbridges_near_axis": fb, "underpasses_near_axis": up,
    "infra": {k: {kk: v[kk] for kk in ("total","within_150m_of_axis")} for k,v in inf_sum.items()},
}
out["infra_detail"] = inf_sum
out["piers"] = [{"ll": r["ll"], "s": round(r["s"],1), "d": round(r["d"],1),
                 "side": r["side"], "h": round(r["h"],1), "area": round(r["area"],1)}
                for r in rows if r["d"] <= 200]
out["bents"] = [{"s": round(float(np.mean(b)),1), "n_cols": len(b)} for b in bents]

# ============================================================ I 建築量體 ====
B = np.load("../data/blend/buildings_parts.npy").astype(np.float64)
XY = xf(B[:, :2]); h = B[:,3]-B[:,2]; fp = B[:,4]*B[:,5]
DEFAULT_H = 12.0
is_default = np.round(h,1) == DEFAULT_H
print("\n=== I  building massing north vs south ===")
print(f"  separated masses: {len(B):,}")
print(f"  [CAVEAT] {is_default.mean()*100:.1f}% of heights are exactly {DEFAULT_H} m, "
      f"and the rest cluster on multiples of 3.2 m -> heights are "
      f"building:levels x 3.2 m with a 12 m fallback, NOT surveyed heights. "
      f"Every height statistic below is reported twice: all masses, and the "
      f"real-height subset only.")
recs = []
for k in range(len(B)):
    sd, s, d = side_chain(XY[k,0], XY[k,1])
    if d > 400: continue
    recs.append((sd, s, d, h[k], fp[k], 0.0 if is_default[k] else 1.0))
recs = np.array(recs)
res = {}
for subset, mask_extra in (("all", np.ones(len(recs), bool)),
                           ("real_height_only", recs[:,5] > 0.5)):
    res[subset] = {}
    for lbl, sd in (("north",1), ("south",-1)):
        m = (recs[:,0]==sd) & mask_extra
        res[subset][lbl] = {
            "n": int(m.sum()),
            "height_mean_m": round(float(recs[m,3].mean()),2),
            "height_median_m": round(float(np.median(recs[m,3])),2),
            "height_p90_m": round(float(np.percentile(recs[m,3],90)),2),
            "footprint_mean_m2": round(float(recs[m,4].mean()),1),
            "volume_proxy_m3": round(float((recs[m,3]*recs[m,4]).sum()),0),
        }
    nn, sss = res[subset]["north"], res[subset]["south"]
    res[subset]["ns_height_ratio"] = round(nn["height_mean_m"]/sss["height_mean_m"],3)
    print(f"  [{subset}]  north n={nn['n']:5d} mean {nn['height_mean_m']:6.2f} m "
          f"p90 {nn['height_p90_m']:6.2f} | south n={sss['n']:5d} mean {sss['height_mean_m']:6.2f} m "
          f"p90 {sss['height_p90_m']:6.2f} | N/S {res[subset]['ns_height_ratio']:.3f}")
# is the missing-height rate itself lopsided? (a confound if so)
for lbl, sd in (("north",1),("south",-1)):
    m = recs[:,0]==sd
    print(f"    default-height share {lbl}: {(1-recs[m,5].mean())*100:.1f}%")
print("  by distance band, real-height subset only (mean height, m):")
band_rows = []
for lo, hi in ((0,50),(50,100),(100,200),(200,400)):
    vals = []
    for sd in (1,-1):
        m = (recs[:,0]==sd)&(recs[:,2]>lo)&(recs[:,2]<=hi)&(recs[:,5]>0.5)
        vals.append(float(recs[m,3].mean()) if m.sum() else float('nan'))
    band_rows.append({"lo":lo,"hi":hi,"north":round(vals[0],2),"south":round(vals[1],2),
                      "ratio":round(vals[0]/vals[1],3)})
    print(f"    {lo:3d}-{hi:3d} m   N {vals[0]:6.2f}   S {vals[1]:6.2f}   N/S {vals[0]/vals[1]:5.2f}")
seg_ns = []
for i in range(n_seg):
    lo, hi = i*SEG, (i+1)*SEG
    row = {"i": i, "s": round(lo+SEG/2,1)}
    for sd, lbl in ((1,"north"),(-1,"south")):
        m = (recs[:,0]==sd)&(recs[:,1]>=lo)&(recs[:,1]<hi)&(recs[:,2]<=300)
        row[lbl] = {"n": int(m.sum()),
                    "h_mean": round(float(recs[m,3].mean()),2) if m.sum() else None,
                    "vol": round(float((recs[m,3]*recs[m,4]).sum()),0) if m.sum() else 0}
    seg_ns.append(row)
out["massing"] = {"n_buildings": int(len(B)),
                  "default_height_share": round(float(is_default.mean()),4),
                  "default_height_m": DEFAULT_H,
                  "by_side": res, "by_band_real_height": band_rows,
                  "segments": seg_ns,
                  "caveat": "heights are building:levels x 3.2 m with a 12.0 m "
                            "fallback for 42% of masses; not surveyed heights"}

# ========================================================== J 樹冠 REJECTED =
can = np.load("../data/blend/canopy_parts.npy").astype(np.float64)
trk = np.load("../data/blend/trunk_parts.npy").astype(np.float64)
uni = {"canopy_width_std": float(can[:,4].std()), "canopy_depth_std": float(can[:,5].std()),
       "canopy_ztop_std": float(can[:,3].std()), "canopy_zbot_std": float(can[:,2].std()),
       "trunk_height_std": float((trk[:,3]-trk[:,2]).std())}
print("\n=== J  street tree canopy: REJECTED as a data source ===")
print(f"  {len(can):,} canopy meshes, {len(trk):,} trunk meshes (both exactly 10,000 "
      f"-> a capped placement, not the 25,388 trees the site actually holds)")
print(f"  every canopy is {can[:,4].mean():.2f} x {can[:,5].mean():.2f} m, "
      f"z {can[:,2].mean():.2f}-{can[:,3].mean():.2f} m; dimension std: "
      + ", ".join(f"{k.split('_')[-2]} {v:.2e}" for k,v in list(uni.items())[:4]))
print("  -> uniform placeholder geometry. Canopy area/volume is NOT computable "
      "from this model. No figure reported; the earlier dossier's limitation stands.")
tp = xf(trk[:, :2])
near = 0
for k in range(len(tp)):
    if A.distance(Point(tp[k,0], tp[k,1])) <= 300: near += 1
print(f"  what IS usable: {near:,} tree POSITIONS within 300 m of the axis.")
out["canopy"] = {"status": "REJECTED_PLACEHOLDER_GEOMETRY",
                 "n_canopy_meshes": int(len(can)), "n_trunk_meshes": int(len(trk)),
                 "uniform_dims": {k: round(v,8) for k,v in uni.items()},
                 "canopy_w_m": round(float(can[:,4].mean()),3),
                 "canopy_d_m": round(float(can[:,5].mean()),3),
                 "canopy_z": [round(float(can[:,2].mean()),2), round(float(can[:,3].mean()),2)],
                 "n_tree_positions_300m": int(near),
                 "note": "positions usable; canopy dimensions are placeholders, "
                         "so canopy area and volume are not reported"}

json.dump(out, open("../data/processed/h_blend.json","w"), ensure_ascii=False)
print("\nwrote data/processed/h_blend.json")
