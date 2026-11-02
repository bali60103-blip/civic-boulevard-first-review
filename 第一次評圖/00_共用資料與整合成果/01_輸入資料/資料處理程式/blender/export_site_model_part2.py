import bpy, json, os
import numpy as np
OUT = os.environ["BLEND_OUT"]
rep = json.load(open(f"{OUT}/export_report.json")) if os.path.exists(f"{OUT}/export_report.json") else {}

def mesh_of(ob):
    """Evaluated mesh for any object type (curves get converted)."""
    dg = bpy.context.evaluated_depsgraph_get()
    oe = ob.evaluated_get(dg)
    try:
        return oe.to_mesh(), oe
    except Exception:
        return None, oe

for nm, fn in (("Railways_Underground_Ref","rail_underground"),
               ("Sidewalks","sidewalks"),
               ("OSM_Footway","footway"),
               ("Taipei_Terrain","terrain")):
    ob = bpy.data.objects.get(nm)
    if not ob:
        print("MISSING", nm); continue
    if ob.type == "CURVE":
        # dump the spline control points as polylines - a curve is a line, not a face
        lines = []
        for sp in ob.data.splines:
            pts = sp.points if len(sp.points) else sp.bezier_points
            L = [list((ob.matrix_world @ p.co.to_3d() if hasattr(p.co,'to_3d') else ob.matrix_world @ p.co)[:3]) for p in pts]
            if len(L) >= 2: lines.append([[round(c,2) for c in p[:2]] for p in L])
        json.dump(lines, open(f"{OUT}/{fn}_lines.json","w"))
        rep[fn] = {"n_splines": len(lines), "type":"curve"}
        print(nm, "-> curve,", len(lines), "splines")
        continue
    me, oe = mesh_of(ob)
    if me is None: print("no mesh", nm); continue
    mw = ob.matrix_world
    vs = np.array([(mw @ v.co)[:] for v in me.vertices], dtype=np.float32)
    polys = [[int(i) for i in p.vertices] for p in me.polygons if abs(p.normal.z) >= 0.5]
    np.save(f"{OUT}/{fn}_verts.npy", vs[:, :2])
    json.dump(polys, open(f"{OUT}/{fn}_polys.json","w"))
    rep[fn] = {"n_verts": int(len(vs)), "n_polys": len(polys)}
    print(nm, "->", len(vs), "verts", len(polys), "polys")
    oe.to_mesh_clear()

# Separate the street-tree meshes into loose parts. measure_blend_model.py
# needs canopy_parts.npy / trunk_parts.npy to TEST whether the canopy geometry
# is real, and it is not — every crown is an identical 3.00 x 2.60 x 3.00 m
# placeholder. That test has to be reproducible from the committed pipeline,
# so the separation belongs here rather than in a throwaway script.
def loose_parts_of(name):
    ob = bpy.data.objects.get(name)
    if ob is None or ob.type != "MESH":
        print("skip", name); return None
    me = ob.data
    bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
    parent = list(range(len(bm.verts)))
    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a
    for e in bm.edges:
        ra, rb = find(e.verts[0].index), find(e.verts[1].index)
        if ra != rb: parent[rb] = ra
    mw = ob.matrix_world
    co = np.array([(mw @ v.co)[:] for v in bm.verts], dtype=np.float64)
    root = np.array([find(i) for i in range(len(bm.verts))])
    bm.free()
    uniq, inv = np.unique(root, return_inverse=True)
    out = np.zeros((len(uniq), 7), dtype=np.float32)
    for k in range(len(uniq)):
        c = co[inv == k]
        out[k] = (c[:,0].mean(), c[:,1].mean(), c[:,2].min(), c[:,2].max(),
                  c[:,0].max()-c[:,0].min(), c[:,1].max()-c[:,1].min(), len(c))
    return out

import bmesh
for nm, fn in (("Street_Trees_Canopies", "canopy_parts"),
               ("Street_Trees_Trunks", "trunk_parts")):
    a = loose_parts_of(nm)
    if a is None: continue
    np.save(f"{OUT}/{fn}.npy", a)
    rep[fn] = {"n_parts": int(len(a)),
               "xy_w_std": float(a[:,4].std()), "xy_d_std": float(a[:,5].std())}
    print(f"{nm}: {len(a)} loose parts, XY size std "
          f"{a[:,4].std():.2e}/{a[:,5].std():.2e}")

# also: separate the buildings massing into loose parts so we get per-building
# height + footprint area (needed for the N/S massing comparison)
ob = bpy.data.objects["Buildings_Massing"]
me = ob.data
import bmesh
bm = bmesh.new(); bm.from_mesh(me); bm.verts.ensure_lookup_table()
# union-find over edges
parent = list(range(len(bm.verts)))
def find(a):
    while parent[a] != a:
        parent[a] = parent[parent[a]]; a = parent[a]
    return a
def union(a,b):
    ra, rb = find(a), find(b)
    if ra != rb: parent[rb] = ra
for e in bm.edges:
    union(e.verts[0].index, e.verts[1].index)
mw = ob.matrix_world
co = np.array([(mw @ v.co)[:] for v in bm.verts], dtype=np.float64)
root = np.array([find(i) for i in range(len(bm.verts))])
bm.free()
uniq, inv = np.unique(root, return_inverse=True)
n = len(uniq)
out = np.zeros((n, 6), dtype=np.float32)   # cx, cy, zmin, zmax, w, d
for k in range(n):
    m = inv == k
    c = co[m]
    out[k] = (c[:,0].mean(), c[:,1].mean(), c[:,2].min(), c[:,2].max(),
              c[:,0].max()-c[:,0].min(), c[:,1].max()-c[:,1].min())
np.save(f"{OUT}/buildings_parts.npy", out)
rep["buildings_parts"] = {"n_buildings": int(n)}
print("buildings separated into", n, "loose parts")

json.dump(rep, open(f"{OUT}/export_report.json","w"), ensure_ascii=False, indent=1)
print("OK")
