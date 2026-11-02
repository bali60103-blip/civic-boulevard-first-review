"""Fill tools/boundary_overlay_map.html's evidence layers with measured data.

That tool is a STRAIGHTENED CORRIDOR STRIP: x runs along the road, y is
distance north/south of it. That happens to be exactly the (chainage, signed
distance) space every measurement in this pipeline already works in, so real
data drops straight into the existing viewBox — no need to turn the tool into
a second geographic map (tools/civic_blvd_severance.html is that).

Layer by layer, what replaced the hand-placed circles:

  heat   商家密度        real:餐飲/零售/超商/夜生活 POIs, binned
  mass   建物量體高度     real: Blender masses, 12.0 m default excluded.
                         REPLACES the old 建物樓齡 layer — building AGE needs a
                         permit-year dataset we do not have, so the layer now
                         shows what is actually measurable and is relabelled.
  brand  已標記連鎖門市   real positions, but only 18.7% of shop POIs carry a
                         brand tag, so this shows WHERE mapped chains are and
                         makes NO claim about the chain/independent ratio — an
                         untagged shop is not evidence of an independent one.
  detour 繞路係數        real: the 64 probe pairs (new layer)
  cog    認知地圖邊界     still empty. Needs a survey. Rendered as an explicit
                         "no data" state instead of invented tick marks.

Scope: the strip spans the full 6,533 m elevated deck rather than only
市民大道一段 — confirmed with the user on 2026-09-09. The severance question is
a property of the elevated structure, not of one section. To narrow it back to
一段 (環河北路→中山北路), set STRIP_S_MAX to 1700 and relabel the end text in
the tool's SVG.
"""
import json

import numpy as np
from shapely.geometry import LineString, Point

from config import DATA_PROCESSED
from sectors import classify

TOOL = "../tools/boundary_overlay_map.html"

# --- strip geometry, read off the tool's existing SVG ----------------------
VB_W, VB_H = 1000, 620
ROAD_TOP, ROAD_BOT = 284, 318          # the road band rect
X0, X1 = 24, 976
Y_N_EDGE, Y_N_FAR = ROAD_TOP - 2, 26   # north: near the road -> far
Y_S_EDGE, Y_S_FAR = ROAD_BOT + 2, 578  # south: near the road -> far
STRIP_S_MIN, STRIP_S_MAX = 0.0, None   # None = the whole axis
DIST_MAX = 600.0

axis = json.load(open(f"{DATA_PROCESSED}/axis.json"))
A = LineString(axis["axis_m"])
S_MAX = STRIP_S_MAX if STRIP_S_MAX else axis["axis_length_m"]


def sx(s):
    return X0 + (s - STRIP_S_MIN) / (S_MAX - STRIP_S_MIN) * (X1 - X0)


def sy(signed_d):
    """signed distance in metres (+ = north) -> strip y."""
    f = min(abs(signed_d), DIST_MAX) / DIST_MAX
    if signed_d >= 0:
        return Y_N_EDGE - f * (Y_N_EDGE - Y_N_FAR)
    return Y_S_EDGE + f * (Y_S_FAR - Y_S_EDGE)


def side_dist(x, y):
    p = Point(x, y)
    s = A.project(p)
    d = A.distance(p)
    a = A.interpolate(max(0, s - 15)); b = A.interpolate(min(A.length, s + 15))
    sgn = 1 if ((b.x - a.x) * (y - a.y) - (b.y - a.y) * (x - a.x)) > 0 else -1
    return s, d * sgn


# --- source points ---------------------------------------------------------
from geo import TO_M
nodes = json.load(open(f"{DATA_PROCESSED}/osm_nodes.json"))
areas = json.load(open(f"{DATA_PROCESSED}/osm_areas.json"))
SHOP = {"餐飲", "零售", "便利超市", "夜生活"}

shops, chains = [], []
for rec in nodes:
    t = rec["t"]
    if classify(t) not in SHOP:
        continue
    x, y = TO_M.transform(rec["lon"], rec["lat"])
    s, sd = side_dist(x, y)
    if not (STRIP_S_MIN <= s <= S_MAX) or abs(sd) > DIST_MAX:
        continue
    shops.append((s, sd))
    if "brand" in t:
        chains.append((s, sd))
for rec in areas:
    t = rec["t"]
    if classify(t) not in SHOP:
        continue
    lon = sum(c[0] for c in rec["c"]) / len(rec["c"])
    lat = sum(c[1] for c in rec["c"]) / len(rec["c"])
    x, y = TO_M.transform(lon, lat)
    s, sd = side_dist(x, y)
    if not (STRIP_S_MIN <= s <= S_MAX) or abs(sd) > DIST_MAX:
        continue
    shops.append((s, sd))
    if "brand" in t:
        chains.append((s, sd))
print(f"shop POIs on the strip: {len(shops)}  (brand-tagged: {len(chains)}, "
      f"{len(chains)/max(len(shops),1)*100:.1f}%)")


def esc(v):
    return f"{v:.1f}"


# --- heat: shop density, binned into the tool's soft-circle idiom ----------
SBIN, DBIN = 200.0, 120.0
grid = {}
for s, sd in shops:
    grid[(int(s // SBIN), int(sd // DBIN))] = grid.get((int(s // SBIN), int(sd // DBIN)), 0) + 1
mx = max(grid.values())
heat = []
for (si, di), n in sorted(grid.items()):
    s_mid = (si + 0.5) * SBIN
    d_mid = (di + 0.5) * DBIN
    if s_mid > S_MAX:
        continue
    r = 14 + 34 * (n / mx) ** 0.5
    op = 0.10 + 0.30 * (n / mx) ** 0.6
    heat.append(f'          <circle cx="{esc(sx(s_mid))}" cy="{esc(sy(d_mid))}" '
                f'r="{esc(r)}" opacity="{op:.2f}" />')
heat_svg = ('        <g fill="var(--heat)" filter="url(#blurSoft2)">\n'
            + "\n".join(heat) + "\n        </g>")

# --- mass: building heights (real-height subset only) ---------------------
bundle = json.load(open("../output/bundle.json"))
mass = []
hs = []
for i, h in enumerate(bundle["building_h"]):
    if not h or h[1]:            # missing, or the 12.0 m default -> excluded
        continue
    s = bundle["building_s"][i]
    d = bundle["building_d"][i] * bundle["building_side"][i]
    if not (STRIP_S_MIN <= s <= S_MAX) or abs(d) > DIST_MAX:
        continue
    hs.append((s, d, h[0]))
hmax = np.percentile([h for _, _, h in hs], 97) if hs else 1
# thin to keep the SVG small: keep the tallest mass per 60 m x 60 m cell
cell = {}
for s, d, h in hs:
    k = (int(s // 60), int(d // 60))
    if k not in cell or h > cell[k][2]:
        cell[k] = (s, d, h)
for s, d, h in sorted(cell.values()):
    f = min(h / hmax, 1.0)
    mass.append(f'          <circle cx="{esc(sx(s))}" cy="{esc(sy(d))}" '
                f'r="{esc(3 + 9 * f)}" opacity="{0.14 + 0.46 * f:.2f}" />')
print(f"building masses plotted: {len(mass)} (of {len(hs)} real-height in strip); "
      f"height p97 = {hmax:.1f} m")
mass_svg = ('        <g fill="var(--age)">\n' + "\n".join(mass) + "\n        </g>")

# --- brand: mapped chain outlets -----------------------------------------
brand = [f'          <circle cx="{esc(sx(s))}" cy="{esc(sy(sd))}" r="3.4" />'
         for s, sd in sorted(chains)]
brand_svg = ('        <g fill="var(--chain)" opacity=".72">\n'
             + "\n".join(brand) + "\n        </g>")

# --- detour: the probe pairs, as bars reaching out from the road ----------
det = []
for r in bundle["detour"]["rows"]:
    x = sx(r["s"])
    if r["st"] != "ok":
        det.append(f'          <rect x="{esc(x-3)}" y="{ROAD_TOP-46}" width="6" height="40" '
                   f'fill="var(--cog)" opacity=".28" />'
                   f'<text x="{esc(x)}" y="{ROAD_TOP-50}" text-anchor="middle" '
                   f'font-size="9" fill="var(--ink-faint)">缺</text>')
        continue
    f = min((r["d"] - 1) / 2.0, 1.0)
    hgt = 8 + 62 * f
    det.append(f'          <rect x="{esc(x-4)}" y="{esc(ROAD_TOP-6-hgt)}" width="8" '
               f'height="{esc(hgt)}" opacity="{0.30+0.55*f:.2f}" />')
det_svg = ('        <g fill="var(--indie)">\n' + "\n".join(det) + "\n        </g>")

# --- cog: no data --------------------------------------------------------
cog_svg = (f'        <g>\n'
           f'          <text x="{VB_W//2}" y="{Y_S_FAR-6}" text-anchor="middle" '
           f'font-size="12" fill="var(--ink-faint)">'
           f'認知地圖邊界：無資料（需要問卷調查，本專案未取得）</text>\n'
           f'        </g>')

# --- splice into the tool -------------------------------------------------
import re
html = open(TOOL, encoding="utf-8").read()


def replace_group(html, gid, body, extra_attrs=""):
    pat = re.compile(r'(<g id="' + gid + r'"[^>]*>)(.*?)(\n      </g>)', re.S)
    m = pat.search(html)
    if not m:
        raise SystemExit(f"group {gid} not found")
    head = m.group(1)
    if extra_attrs:
        head = re.sub(r'^<g id="' + gid + r'"[^>]*>',
                      f'<g id="{gid}" class="layer-group"{extra_attrs}>', head)
    return html[:m.start()] + head + "\n" + body + m.group(3) + html[m.end():]


html = replace_group(html, "layer-heat", heat_svg)
html = replace_group(html, "layer-age", mass_svg)
html = replace_group(html, "layer-brand", brand_svg)
html = replace_group(html, "layer-cog", cog_svg, extra_attrs="")
# the detour layer is new: add it just before the road band group
if 'id="layer-detour"' not in html:
    html = html.replace('      <!-- 市民大道 road band',
                        '      <g id="layer-detour" class="layer-group">\n'
                        + det_svg + '\n      </g>\n\n      <!-- 市民大道 road band')
else:
    html = replace_group(html, "layer-detour", det_svg)

open(TOOL, "w", encoding="utf-8").write(html)
print(f"\nspliced measured layers into {TOOL}")
