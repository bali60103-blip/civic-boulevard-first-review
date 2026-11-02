"""Stage 2 — reconstruct the 市民大道 barrier axis and cut it into 200 m segments.

DESIGN NOTE (this matters for every number downstream):
市民大道 is tagged in OSM as ~160 separate ways: the elevated deck (2
directions, layer 1/2), the at-grade dual carriageway (2 directions), ramps
and lanes. A naive "median northing per easting bin" over all of them
produced up to 350 m of northing jitter around 光復南路, because there the
at-grade 五段 genuinely peels ~300 m north of the elevated deck. Mixing them
creates a fictional centreline.

So the axis is built from the ELEVATED DECK ways only (highway=trunk,
bridge=yes, name=市民大道高架道路). That is the physical object the PDF is
about ("全長6.4公里"), it is a single clean corridor, and it is what actually
casts the barrier. The at-grade carriageway is kept as a separate geometry.
"""
import json, math, collections
import numpy as np
from shapely.geometry import LineString, MultiLineString, Point
from geo import to_m, to_deg, ll_to_m

ways = json.load(open("../data/processed/osm_ways.json"))
civic = [w for w in ways if w["t"].get("name","").startswith("市民大道")]
SEC = tuple(f"市民大道{c}段" for c in "一二三四五六七八")

elev  = [w for w in civic if w["t"].get("name") == "市民大道高架道路"
         and w["t"].get("highway") == "trunk"]
grade = [w for w in civic if w["t"].get("name") in SEC
         and w["t"].get("highway") in ("trunk","primary","secondary","tertiary")]
ramps = [w for w in civic if "匝道" in w["t"].get("name","")]
print(f"elevated deck ways {len(elev)} | at-grade carriageway ways {len(grade)} | ramps {len(ramps)}")


def robust_centreline(wlist, binw=20.0, max_dev=60.0):
    """Median-northing-per-easting-bin, then reject bins whose northing deviates
    more than max_dev from a 9-bin rolling median (kills parallel-alignment
    contamination), then smooth with a 5-bin moving average."""
    pts = np.array([ll_to_m(lon, lat) for w in wlist for lon, lat in w["c"]])
    pts = pts[np.argsort(pts[:, 0])]
    bins = np.arange(pts[:, 0].min(), pts[:, 0].max()+binw, binw)
    idx = np.digitize(pts[:, 0], bins)
    xs, ys = [], []
    for b in range(1, len(bins)+1):
        m = idx == b
        if m.sum() >= 2:
            xs.append(float(np.median(pts[m, 0])))
            ys.append(float(np.median(pts[m, 1])))
    xs, ys = np.array(xs), np.array(ys)
    # rolling median outlier rejection
    k = 9
    roll = np.array([np.median(ys[max(0, i-k//2):i+k//2+1]) for i in range(len(ys))])
    keep = np.abs(ys - roll) <= max_dev
    xs, ys = xs[keep], ys[keep]
    # moving average smoothing
    w5 = np.ones(5)/5
    ys = np.convolve(ys, w5, mode="same")
    ys[:2], ys[-2:] = ys[2], ys[-3]
    return LineString(np.c_[xs, ys]), int((~keep).sum())


axis_m, rejected = robust_centreline(elev)
straight = Point(axis_m.coords[0]).distance(Point(axis_m.coords[-1]))
print(f"AXIS (elevated deck): length {axis_m.length:,.0f} m, "
      f"end-to-end {straight:,.0f} m, sinuosity {axis_m.length/straight:.3f}, "
      f"{rejected} outlier bins rejected")

grade_m = [to_m(LineString(w["c"])) for w in grade]
elev_m  = [to_m(LineString(w["c"])) for w in elev]
ramp_m  = [to_m(LineString(w["c"])) for w in ramps]

# --- 200 m analysis segments -------------------------------------------------
SEGLEN = 200.0
n_seg = int(round(axis_m.length / SEGLEN))
segments = []
for i in range(n_seg):
    s = i*SEGLEN
    e = min((i+1)*SEGLEN, axis_m.length)
    a, b = axis_m.interpolate(s), axis_m.interpolate(e)
    mid = axis_m.interpolate((s+e)/2)
    segments.append({
        "i": i, "s": round(s,1), "e": round(e,1),
        "mid_m": [round(mid.x,2), round(mid.y,2)],
        "mid_ll": [round(v,7) for v in to_deg(mid).coords[0]],
        "brg": round(math.degrees(math.atan2(b.x-a.x, b.y-a.y)) % 180.0, 2),
    })

out = {
    "axis_ll": [[round(v,7) for v in c] for c in to_deg(axis_m).coords],
    "axis_m":  [[round(v,2) for v in c] for c in axis_m.coords],
    "axis_length_m": round(axis_m.length,1),
    "axis_sinuosity": round(axis_m.length/straight,4),
    "segments": segments,
    "seg_len_m": SEGLEN,
    "elevated_ll": [[[round(v,7) for v in c] for c in to_deg(g).coords] for g in elev_m],
    "atgrade_ll":  [[[round(v,7) for v in c] for c in to_deg(g).coords] for g in grade_m],
    "ramps_ll":    [[[round(v,7) for v in c] for c in to_deg(g).coords] for g in ramp_m],
    "civic_way_ids": [w["id"] for w in civic],
    "counts": {"elevated_ways": len(elev), "atgrade_ways": len(grade), "ramp_ways": len(ramps)},
}
json.dump(out, open("../data/processed/axis.json","w"))
print(f"segments: {len(segments)} x {SEGLEN:.0f} m")
print(f"at-grade carriageway total centreline length (both dirs summed): "
      f"{sum(g.length for g in grade_m):,.0f} m")
