"""Stage 8 — georeference the Blender site model to EPSG:3826.

The .blend is in metres but its origin is a local offset, so nothing from it
can be compared with OSM until the offset is known. The scene contains an
`OSM_Major_Roads` object that was clearly built from OpenStreetMap, so the two
point clouds are the same object in two frames: recovering the transform is a
registration problem, not a guess.

Method: coarse grid search then Nelder-Mead refinement on the median
nearest-neighbour distance from Blender road vertices to OSM road vertices,
solving for translation only (tx, ty). Scale is asserted to be 1 and rotation
0; both assumptions are TESTED afterwards by fitting a full similarity
transform and reporting the residual scale/rotation. If those come out at
1.000/0.00 deg, the assumption held.
"""
import json, numpy as np
from scipy.spatial import cKDTree
from scipy.optimize import minimize
from shapely.geometry import LineString
from geo import ll_to_m, to_deg

# --- target cloud: OSM major roads in EPSG:3826 ------------------------------
ways = json.load(open("../data/processed/osm_ways.json"))
MAJ = {"motorway","trunk","primary","secondary","tertiary",
       "motorway_link","trunk_link","primary_link","secondary_link","tertiary_link"}
tgt = np.array([ll_to_m(lo, la) for w in ways
                if w["t"].get("highway") in MAJ for lo, la in w["c"]])
print(f"target (OSM major roads, EPSG:3826): {len(tgt):,} vertices")
tree = cKDTree(tgt)

# --- source cloud: the same object as Blender holds it ----------------------
src_all = np.load("../data/blend/OSM_Major_Roads.npy").astype(np.float64)
# subsample for speed, but keep it spatially spread
rng = np.random.default_rng(0)
src = src_all[rng.choice(len(src_all), size=min(8000, len(src_all)), replace=False)]
print(f"source (Blender OSM_Major_Roads):     {len(src_all):,} vertices "
      f"({len(src):,} sampled)")

def cost(t, S=src, cap=60.0):
    d, _ = tree.query(S + t)
    return float(np.median(np.minimum(d, cap)))

# coarse grid around the bbox-derived first guess
g0 = np.array([301313.0, 2770464.0])
best, bt = 1e18, g0
for dx in np.arange(-300, 301, 50.0):
    for dy in np.arange(-300, 301, 50.0):
        t = g0 + (dx, dy)
        c = cost(t)
        if c < best: best, bt = c, t
print(f"coarse grid best: t=({bt[0]:.1f}, {bt[1]:.1f})  median NN = {best:.2f} m")

r = minimize(cost, bt, method="Nelder-Mead",
             options={"xatol": 0.05, "fatol": 0.002, "maxiter": 800})
t = r.x
print(f"refined:          t=({t[0]:.2f}, {t[1]:.2f})  median NN = {r.fun:.2f} m")

# --- test the scale=1 / rotation=0 assumption -------------------------------
d, i = tree.query(src + t)
ok = d < 25.0
A = src[ok]; B = tgt[i[ok]]
print(f"inliers within 25 m: {ok.sum():,}/{len(src):,} ({ok.mean()*100:.1f}%)")
ca, cb = A.mean(0), B.mean(0)
Ac, Bc = A-ca, B-cb
H = Ac.T @ Bc
U, S, Vt = np.linalg.svd(H)
R = Vt.T @ U.T
if np.linalg.det(R) < 0:
    Vt[-1] *= -1; R = Vt.T @ U.T
scale = float(S.sum() / (Ac**2).sum())
rot = float(np.degrees(np.arctan2(R[1,0], R[0,0])))
print(f"full similarity fit on inliers: scale = {scale:.6f}, rotation = {rot:+.4f} deg")
resid = np.linalg.norm((A + t) - B, axis=1)
print(f"translation-only residual on inliers: median {np.median(resid):.2f} m, "
      f"p90 {np.percentile(resid,90):.2f} m, mean {resid.mean():.2f} m")

if abs(scale-1) > 0.002 or abs(rot) > 0.2:
    print("!! WARNING: scale/rotation are NOT negligible; a translation-only "
          "transform is not adequate. Downstream numbers would be biased.")
else:
    print("OK: translation-only transform is adequate "
          "(scale within 0.2%, rotation within 0.2 deg).")

json.dump({"tx": float(t[0]), "ty": float(t[1]),
           "median_nn_m": round(float(r.fun),3),
           "inlier_share": round(float(ok.mean()),4),
           "inlier_median_resid_m": round(float(np.median(resid)),3),
           "inlier_p90_resid_m": round(float(np.percentile(resid,90)),3),
           "fitted_scale": round(scale,6), "fitted_rotation_deg": round(rot,4),
           "crs": "EPSG:3826", "method": "NN median translation fit vs OSM major roads",
           "n_src": int(len(src_all)), "n_tgt": int(len(tgt))},
          open("../data/processed/blend_georef.json","w"), indent=1)
print("\nwrote data/processed/blend_georef.json")
