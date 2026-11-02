"""Stage 7 — 南北分隔證據 G: the barrier's own footprint.

Stage 6 showed the industry *mix* north vs south is no more divergent than
across an arbitrary parallel line — a negative result, reported as such.

That failure points at the better question. A barrier does not necessarily put
different shops on either side; it puts NOTHING on itself. So here we measure
POI density as a function of signed perpendicular distance from the axis, in
25 m bins from -600 m (south) to +600 m (north), and compare the shape of that
profile with the same profile taken about the five control arterials.

  trough depth = 1 - (density in the innermost +-50 m) / (density at 200-400 m)

A normal shopping street has a PEAK at 0 (shops face the street). A barrier
has a TROUGH. That difference in sign is the evidence.
"""
import json, math, collections
import numpy as np
from shapely.geometry import LineString, Point
from geo import to_m, to_deg, ll_to_m, TO_M
from sectors import classify, SECTOR_KEYS

BINW, RANGE = 25.0, 600.0
ACTIVE = {"餐飲","零售","便利超市","夜生活","商辦","金融","旅宿","醫療"}

axis = json.load(open("../data/processed/axis.json"))
A = LineString(axis["axis_m"])
nodes = json.load(open("../data/processed/osm_nodes.json"))
areas = json.load(open("../data/processed/osm_areas.json"))
ways  = json.load(open("../data/processed/osm_ways.json"))
X0, X1 = A.bounds[0], A.bounds[2]

pois = []
for n in nodes:
    s = classify(n["t"])
    if s:
        x,y = TO_M.transform(n["lon"], n["lat"]); pois.append((x,y,s))
for a in areas:
    s = classify(a["t"])
    if s:
        xy=[TO_M.transform(lo,la) for lo,la in a["c"]]
        pois.append((sum(p[0] for p in xy)/len(xy), sum(p[1] for p in xy)/len(xy), s))
P = np.array([(x,y) for x,y,_ in pois])
SEC = np.array([s for _,_,s in pois])
print(f"POIs: {len(P):,}")


def signed_profile(line, mask=None, label=""):
    """POI density per hectare vs signed distance from `line`."""
    corridor = line.buffer(RANGE)
    minx,miny,maxx,maxy = corridor.bounds
    box = (P[:,0]>=minx)&(P[:,0]<=maxx)&(P[:,1]>=miny)&(P[:,1]<=maxy)
    idx = np.where(box)[0]
    if mask is not None:
        idx = idx[mask[idx]]
    # signed distance + chainage
    sd, keep = [], []
    for i in idx:
        pt = Point(P[i,0], P[i,1])
        d = line.distance(pt)
        if d > RANGE: continue
        s = line.project(pt)
        if s <= 5 or s >= line.length-5: continue     # avoid end effects
        eps=15.0
        a = line.interpolate(max(0,s-eps)); b = line.interpolate(min(line.length,s+eps))
        side = 1 if ((b.x-a.x)*(P[i,1]-a.y)-(b.y-a.y)*(P[i,0]-a.x))>0 else -1
        sd.append(side*d); keep.append(i)
    sd = np.array(sd)
    edges = np.arange(-RANGE, RANGE+BINW, BINW)
    cnt,_ = np.histogram(sd, bins=edges)
    # each bin's area = axis length * bin width (m^2) -> hectares
    area_ha = line.length * BINW / 10000.0
    dens = cnt/area_ha
    centres = (edges[:-1]+edges[1:])/2
    inner = dens[np.abs(centres) <= 50]
    ref   = dens[(np.abs(centres) >= 200) & (np.abs(centres) <= 400)]
    trough = 1 - inner.mean()/ref.mean() if ref.mean() > 0 else None
    return {"label": label, "length_m": round(line.length,1),
            "centres": centres.tolist(), "density_per_ha": [round(v,3) for v in dens],
            "counts": cnt.tolist(),
            "inner_density": round(float(inner.mean()),3),
            "ref_density": round(float(ref.mean()),3),
            "trough_depth": None if trough is None else round(float(trough),4),
            "n": int(len(sd))}

active_mask = np.isin(SEC, list(ACTIVE))

print(f"\n=== G  density trough at the corridor centreline ===")
print(f"{'corridor':10s} {'len m':>7s} {'all: inner':>11s} {'ref':>7s} {'trough':>8s}"
      f" | {'active: inner':>13s} {'ref':>7s} {'trough':>8s}")
res = {}
def report(line, label):
    a = signed_profile(line, None, label)
    b = signed_profile(line, active_mask, label+"_active")
    res[label] = {"all": a, "active": b}
    print(f"{label:10s} {a['length_m']:7.0f} {a['inner_density']:11.2f} {a['ref_density']:7.2f}"
          f" {a['trough_depth']*100 if a['trough_depth'] is not None else float('nan'):7.1f}%"
          f" | {b['inner_density']:13.2f} {b['ref_density']:7.2f}"
          f" {b['trough_depth']*100 if b['trough_depth'] is not None else float('nan'):7.1f}%")

report(A, "市民大道")

def build_control(prefix):
    sel=[w for w in ways if w["t"].get("name","").startswith(prefix)
         and w["t"].get("highway") in ("trunk","primary","secondary","tertiary")
         and w["t"].get("bridge")!="yes"]
    Q=np.array([ll_to_m(lo,la) for w in sel for lo,la in w["c"]])
    if len(Q)<20: return None
    Q=Q[(Q[:,0]>=X0)&(Q[:,0]<=X1)]
    if len(Q)<20: return None
    Q=Q[np.argsort(Q[:,0])]
    bins=np.arange(Q[:,0].min(),Q[:,0].max()+20,20); idx=np.digitize(Q[:,0],bins)
    xs,ys=[],[]
    for b in range(1,len(bins)+1):
        m=idx==b
        if m.sum()>=2: xs.append(float(np.median(Q[m,0]))); ys.append(float(np.median(Q[m,1])))
    xs,ys=np.array(xs),np.array(ys)
    roll=np.array([np.median(ys[max(0,i-4):i+5]) for i in range(len(ys))])
    k=np.abs(ys-roll)<=60; xs,ys=xs[k],ys[k]
    ys=np.convolve(ys,np.ones(5)/5,mode="same"); ys[:2],ys[-2:]=ys[2],ys[-3]
    return LineString(np.c_[xs,ys])

for c in ["八德路","忠孝東路","南京東路","長安東路","民生東路"]:
    ls = build_control(c)
    if ls is not None: report(ls, c)

# ------------------------------------------------------- N/S asymmetry -------
print(f"\n=== G  north/south asymmetry of the profile (市民大道) ===")
a = res["市民大道"]["all"]
c = np.array(a["centres"]); d = np.array(a["density_per_ha"])
for lo,hi in ((0,100),(100,200),(200,400),(400,600)):
    nn = d[(c>lo)&(c<=hi)].mean(); ss = d[(c<-lo)&(c>=-hi)].mean()
    print(f"  {lo:3d}-{hi:3d} m   north {nn:7.2f} /ha   south {ss:7.2f} /ha   N/S {nn/ss:5.2f}")

json.dump(res, open("../data/processed/g_gradient.json","w"), ensure_ascii=False)
print("\nwrote data/processed/g_gradient.json")
