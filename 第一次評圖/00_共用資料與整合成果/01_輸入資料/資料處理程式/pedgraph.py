"""A routable pedestrian graph built from the extracted OSM ways.

Why this exists: counting "ways that cross the axis" is unreliable, because a
smoothed centreline gets clipped by parallel sidewalk fragments, and because
railway/subway ways cross the axis without carrying a single pedestrian. A
graph answers the only question that matters — *can a person actually walk
from the north side to the south side, and how far do they have to go?*

Notes on Taipei OSM: sidewalks are usually mapped as separate
highway=footway ways that touch the carriageway only at
footway=crossing ways. Junction connectivity therefore comes from shared node
ids, which is why stage 1 kept every way's full node-ref list.
"""
import json, math
import numpy as np
import networkx as nx
from scipy.spatial import cKDTree
from geo import TO_M

WALK_NO = {"no", "private", "discouraged"}
PED_HW = {"footway","path","pedestrian","steps","living_street","residential",
          "service","unclassified","tertiary","secondary","primary","cycleway",
          "corridor","track","road","tertiary_link","secondary_link","primary_link"}

def walkable(t):
    if t.get("foot") in WALK_NO:
        return False
    if t.get("access") in WALK_NO and t.get("foot") not in ("yes","designated","permissive"):
        return False
    hw = t.get("highway")
    if hw is None:
        return False                      # railway/subway ways: not walkable
    if hw in ("motorway","motorway_link","trunk","trunk_link","construction","proposed"):
        return t.get("foot") in ("yes","designated","permissive")
    return hw in PED_HW


def build(ways_path="../data/processed/osm_ways.json", verbose=True):
    ways = json.load(open(ways_path))
    G = nx.Graph()
    coord = {}
    n_ways = 0
    for w in ways:
        if not walkable(w["t"]):
            continue
        n_ways += 1
        refs, cs = w["n"], w["c"]
        xy = [TO_M.transform(lon, lat) for lon, lat in cs]
        for r, p in zip(refs, xy):
            coord[r] = p
        for i in range(len(refs)-1):
            a, b = refs[i], refs[i+1]
            if a == b:
                continue
            d = math.dist(xy[i], xy[i+1])
            if G.has_edge(a, b):
                if G[a][b]["w"] <= d:
                    continue
            G.add_edge(a, b, w=d, way=w["id"])
    ids = np.array(list(coord.keys()))
    pts = np.array([coord[i] for i in ids])
    tree = cKDTree(pts)
    if verbose:
        comps = sorted((len(c) for c in nx.connected_components(G)), reverse=True)
        print(f"pedestrian graph: {n_ways:,} walkable ways -> "
              f"{G.number_of_nodes():,} nodes / {G.number_of_edges():,} edges")
        print(f"  components: {len(comps)}, largest {comps[0]:,} "
              f"({comps[0]/G.number_of_nodes()*100:.1f}%), next {comps[1:6]}")
    return G, ids, pts, tree, coord


def giant(G):
    """Node set of the largest connected component.

    Snapping must be restricted to this set. Taipei OSM contains hundreds of
    tiny orphan footway fragments (2-30 nodes) that are not joined to the
    network; snapping onto one of those produces a spurious "no route exists"
    which would otherwise be misread as a barrier.
    """
    import networkx as _nx
    return max(_nx.connected_components(G), key=len)


def snap(tree, ids, pts, xy, max_dist=90.0, k=40, allowed=None):
    """Nearest graph node to a metric point, restricted to `allowed` if given.
    Returns (node_id, snap_distance) or (None, None)."""
    d, i = tree.query(xy, k=k, distance_upper_bound=max_dist)
    d = np.atleast_1d(d); i = np.atleast_1d(i)
    for dd, ii in zip(d, i):
        if not np.isfinite(dd) or ii >= len(ids):
            continue
        nid = int(ids[ii])
        if allowed is None or nid in allowed:
            return nid, float(dd)
    return None, None
