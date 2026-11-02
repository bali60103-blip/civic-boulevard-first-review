"""Run inside Blender. Dumps the site model to plain JSON/NPY in Blender's own
local metric coordinates. Registration to EPSG:3826 happens outside Blender so
the fit is auditable."""
import bpy, json, os, sys
import numpy as np
from mathutils import Vector

OUT = os.environ["BLEND_OUT"]
os.makedirs(OUT, exist_ok=True)

def world_verts(o):
    mw = o.matrix_world
    return np.array([(mw @ v.co)[:] for v in o.data.vertices], dtype=np.float32)

def obb(o):
    xs = [(o.matrix_world @ Vector(c))[:] for c in o.bound_box]
    a = np.array(xs)
    return a.min(0).tolist(), a.max(0).tolist()

def footprint_edges(o, z_tol=None):
    """Return the mesh's polygons projected to XY as vertex-index rings.

    Returns (None, None) for anything that is not a mesh. Railways_Underground_Ref
    is a CURVE, and this used to raise AttributeError and abort the script
    partway through — which only went unnoticed because part 2 happened to
    re-export the survivors. A crash here loses export_report.json.
    """
    if o.type != "MESH":
        return None, None
    mw = o.matrix_world
    vs = np.array([(mw @ v.co)[:] for v in o.data.vertices], dtype=np.float32)
    polys = []
    for p in o.data.polygons:
        if abs(p.normal.z) < 0.5:      # skip vertical faces (sides of a slab)
            continue
        polys.append([int(i) for i in p.vertices])
    return vs, polys

report = {}

# --- 1. registration cloud: the OSM roads Blender imported -------------------
for nm in ("OSM_Major_Roads", "OSM_Minor_Roads"):
    o = bpy.data.objects.get(nm)
    if o:
        v = world_verts(o)
        np.save(f"{OUT}/{nm}.npy", v[:, :2])
        report[nm] = {"n_verts": int(len(v))}

# --- 2. buildings massing: full vertex cloud (x,y,z) -------------------------
o = bpy.data.objects["Buildings_Massing"]
v = world_verts(o)
np.save(f"{OUT}/Buildings_Massing.npy", v)
report["Buildings_Massing"] = {"n_verts": int(len(v)),
    "z_min": float(v[:,2].min()), "z_max": float(v[:,2].max())}

# --- 3. street trees: trunks + canopies -> canopy volume is derivable --------
for nm in ("Street_Trees_Trunks", "Street_Trees_Canopies"):
    o = bpy.data.objects.get(nm)
    if not o: continue
    v = world_verts(o)
    np.save(f"{OUT}/{nm}.npy", v)
    # per-loose-part stats are expensive; record aggregate + polygon count
    report[nm] = {"n_verts": int(len(v)), "n_polys": len(o.data.polygons),
                  "z_min": float(v[:,2].min()), "z_max": float(v[:,2].max())}

# --- 4. piers: one record per pier (this is the obstruction inventory) -------
piers = []
for ob in bpy.data.objects:
    if not ob.name.startswith("Pier_"): continue
    lo, hi = obb(ob)
    piers.append({"name": ob.name,
                  "cx": (lo[0]+hi[0])/2, "cy": (lo[1]+hi[1])/2,
                  "w": hi[0]-lo[0], "d": hi[1]-lo[1], "h": hi[2]-lo[2],
                  "z0": lo[2], "z1": hi[2]})
json.dump(piers, open(f"{OUT}/piers.json","w"))
report["piers"] = {"n": len(piers)}

# --- 5. linear barrier elements: guardrail / soundwall / median --------------
lin = {}
for nm in ("Guardrail_1.1m_Civic_Blvd_Elevated_Deck",
           "Soundwall_3.0m_Civic_Blvd_Elevated_Deck",
           "Civic_Blvd_Median_分隔島",
           "Civic_Blvd_Elevated_Deck"):
    ob = bpy.data.objects.get(nm)
    if not ob: continue
    v = world_verts(ob)
    np.save(f"{OUT}/{nm.replace('/','_')}.npy", v)
    # surface area of horizontal faces = deck / median area
    area_h = 0.0; area_all = 0.0
    for p in ob.data.polygons:
        area_all += p.area
        if abs(p.normal.z) > 0.7: area_h += p.area
    lo, hi = obb(ob)
    lin[nm] = {"n_verts": int(len(v)), "area_total": area_all,
               "area_horizontal": area_h,
               "z0": lo[2], "z1": hi[2],
               "bbox": [lo, hi]}
json.dump(lin, open(f"{OUT}/linear_elements.json","w"), ensure_ascii=False)
report["linear_elements"] = {k: {"area_h": round(v["area_horizontal"],1)} for k,v in lin.items()}

# --- 6. point-like real infrastructure --------------------------------------
groups = {
  "footbridges": "Footbridge_",
  "underpasses": "Nether_",
  "parking":     "Parking_",
  "ramps":       "Ramp_",
  "mrt_stations":"MRT_Station_",
  "other_bridges":"Bridge_",
}
pts = {k: [] for k in groups}
for ob in bpy.data.objects:
    for k, pref in groups.items():
        if ob.name.startswith(pref) and ob.type == "MESH":
            lo, hi = obb(ob)
            pts[k].append({"name": ob.name,
                           "cx": (lo[0]+hi[0])/2, "cy": (lo[1]+hi[1])/2,
                           "w": hi[0]-lo[0], "d": hi[1]-lo[1], "h": hi[2]-lo[2],
                           "z0": lo[2], "z1": hi[2]})
            break
json.dump(pts, open(f"{OUT}/infra_points.json","w"), ensure_ascii=False)
report["infra_points"] = {k: len(v) for k, v in pts.items()}

# --- 7. context surfaces: parks, water, riverside parks, terrain, rail -------
for nm, fn in (("Parks","parks"), ("Taipei_Rivers_Water","water"),
               ("Taipei_Riverside_Parks","riverside_parks"),
               ("Railways_Underground_Ref","rail_underground"),
               ("Sidewalks","sidewalks"),
               ("OSM_Footway","footway")):
    ob = bpy.data.objects.get(nm)
    if not ob: continue
    vs, polys = footprint_edges(ob)
    if vs is None:
        # not a mesh (e.g. a curve) — part 2 handles those
        report[fn] = {"skipped": f"not a mesh ({ob.type}); see export_site_model_part2.py"}
        continue
    np.save(f"{OUT}/{fn}_verts.npy", vs[:, :2])
    json.dump(polys, open(f"{OUT}/{fn}_polys.json","w"))
    report[fn] = {"n_verts": int(len(vs)), "n_polys": len(polys)}

json.dump(report, open(f"{OUT}/export_report.json","w"), ensure_ascii=False, indent=1)
print("EXPORT REPORT:", json.dumps(report, ensure_ascii=False, indent=1))
