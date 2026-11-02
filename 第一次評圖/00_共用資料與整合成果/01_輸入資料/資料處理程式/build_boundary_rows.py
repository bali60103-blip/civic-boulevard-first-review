"""Compute the real north/south values that seed tools/boundary_comparison.html.

That tool shipped with six 示意 (illustrative) numbers. This script replaces the
ones that are actually measurable with values traceable to OSM objects, and is
explicit about the ones that are NOT measurable from any data we hold.

WHAT THIS SCRIPT WILL NOT DO: invent a number for 連鎖品牌店占比, 建物樓齡,
騎樓型態一致度 or 認知地圖邊界. Those need brand/age datasets or fieldwork we do
not have. They are emitted with value None so the tool renders them as blanks
for the user to fill, rather than as plausible-looking fiction.

READ THIS BEFORE TRUSTING THE TOOL'S SCORE. The 分界性指數 is the mean relative
north/south difference. measure_industry.py showed that framing is not
sufficient evidence of severance: the north/south difference across 市民大道
(JS 0.213) sits INSIDE the range produced by placebo lines drawn 300–450 m away
entirely on one side (0.145–0.263). A high score on this tool means "the two
sides differ", which in a dense city is true of any two adjacent strips. For
whether the road CAUSES the divide, see tools/civic_blvd_severance.html.
"""
import json
import re

import networkx as nx
import numpy as np
from shapely.geometry import LineString, Point

import pedgraph
from config import BAND_M, DATA_PROCESSED, OUTPUT
from geo import to_deg

TOOL = "../tools/boundary_comparison.html"

axis = json.load(open(f"{DATA_PROCESSED}/axis.json"))
A = LineString(axis["axis_m"])
ind = json.load(open(f"{DATA_PROCESSED}/f_industry.json"))
blend = json.load(open(f"{DATA_PROCESSED}/h_blend.json"))

# Each side of the band is axis_length x BAND_M of ground.
area_km2 = A.length * BAND_M / 1e6
print(f"band area per side: {area_km2:.3f} km2")

# --- 1. shop density: the retail/food subset, not every POI ----------------
SHOP = ("餐飲", "零售", "便利超市", "夜生活")
shops = {}
for side, tot in (("north", ind["north_totals"]), ("south", ind["south_totals"])):
    shops[side] = sum(tot.get(k, 0) for k in SHOP)
    print(f"{side}: {shops[side]} shop POIs -> {shops[side]/area_km2:.0f} /km2")

# --- 2. building height (real-height subset only) --------------------------
bs = blend["massing"]["by_side"]["real_height_only"]
band0 = blend["massing"]["by_band_real_height"][0]     # the 0-50 m band
print(f"height 0-50 m band: north {band0['north']} m, south {band0['south']} m")

# --- 3. junction density from the pedestrian graph -------------------------
# A junction = a graph node of degree >= 3 in the walkable network. This is a
# real topological count, unlike the road-width proxy used elsewhere.
G, ids, pts, tree, coord = pedgraph.build(f"{DATA_PROCESSED}/osm_ways.json", verbose=False)
deg = dict(G.degree())
jn = {"north": 0, "south": 0}
for nid, d in deg.items():
    if d < 3:
        continue
    x, y = coord[nid]
    p = Point(x, y)
    if A.distance(p) > BAND_M:
        continue
    s = A.project(p)
    if s <= 0 or s >= A.length:
        continue
    a = A.interpolate(max(0, s - 15)); b = A.interpolate(min(A.length, s + 15))
    side = "north" if ((b.x - a.x) * (y - a.y) - (b.y - a.y) * (x - a.x)) > 0 else "south"
    jn[side] += 1
for side in jn:
    print(f"{side}: {jn[side]} junctions -> {jn[side]/area_km2:.0f} /km2")

rows = [
    {"name": "商家密度（餐飲＋零售＋超商＋夜生活）", "unit": "家 / km²",
     "north": round(shops["north"] / area_km2), "south": round(shops["south"] / area_km2),
     "src": "OSM tag 分類，軸線兩側 300 m 帶"},
    {"name": "路口密度（人行網路 degree≥3 節點）", "unit": "個 / km²",
     "north": round(jn["north"] / area_km2), "south": round(jn["south"] / area_km2),
     "src": "OSM 可步行路網拓樸，非道路寬度代理"},
    {"name": "建物平均樓高（貼線 0–50 m）", "unit": "m",
     "north": band0["north"], "south": band0["south"],
     "src": "Blender 量體，已排除 12.0 m 預設值"},
    {"name": "建物平均樓高（走廊 0–400 m）", "unit": "m",
     "north": bs["north"]["height_mean_m"], "south": bs["south"]["height_mean_m"],
     "src": "同上；注意 200 m 外南北關係反轉"},
    {"name": "停車設施佔 POI 比例", "unit": "%",
     "north": round(ind["north_totals"].get("停車", 0) / sum(ind["north_totals"].values()) * 100, 1),
     "south": round(ind["south_totals"].get("停車", 0) / sum(ind["south_totals"].values()) * 100, 1),
     "src": "OSM tag 分類；北側被停車佔據是走廊最不對稱的類別"},
    {"name": "綠地佔 POI 比例", "unit": "%",
     "north": round(ind["north_totals"].get("綠地", 0) / sum(ind["north_totals"].values()) * 100, 1),
     "south": round(ind["south_totals"].get("綠地", 0) / sum(ind["south_totals"].values()) * 100, 1),
     "src": "OSM tag 分類"},
    # --- not measurable from anything we hold; emitted blank on purpose ----
    {"name": "連鎖品牌店占比", "unit": "%", "north": None, "south": None,
     "src": "無資料：OSM brand tag 覆蓋率過低，需要商業登記或實地清點"},
    {"name": "建物平均樓齡", "unit": "年", "north": None, "south": None,
     "src": "無資料：需要建物執照年份資料集"},
    {"name": "騎樓／招牌型態一致度", "unit": "分(0–10)", "north": None, "south": None,
     "src": "無資料：需要實地觀察評分"},
    {"name": "認知地圖：視市民大道為活動邊界的受訪者比例", "unit": "%",
     "north": None, "south": None,
     "src": "無資料：需要問卷調查"},
]
for i, r in enumerate(rows, 1):
    r["id"] = i

with open(f"{OUTPUT}/boundary_rows.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)
print(f"\nwrote {OUTPUT}/boundary_rows.json ({len(rows)} rows, "
      f"{sum(1 for r in rows if r['north'] is None)} intentionally blank)")

# --- splice the seed straight into the tool -------------------------------
# Written back into the HTML rather than left as a snippet to paste, so a
# rerun of run_all.sh actually keeps the tool in step with these numbers.
# The replacement is idempotent: it rewrites whatever seedRows block is there.
lines = []
for r in rows:
    n = "null" if r["north"] is None else r["north"]
    sv = "null" if r["south"] is None else r["south"]
    lines.append(f'    {{ id: {r["id"]}, name: "{r["name"]}", unit: "{r["unit"]}", '
                 f'north: {n}, south: {sv}, src: "{r["src"]}" }}')
seed_js = "  var seedRows = [\n" + ",\n".join(lines) + "\n  ];"

with open(f"{OUTPUT}/boundary_seedrows.js", "w", encoding="utf-8") as f:
    f.write(seed_js + "\n")

html = open(TOOL, encoding="utf-8").read()
m = re.search(r"  var seedRows = \[.*?\n  \];", html, re.S)
if not m:
    raise SystemExit(f"seedRows block not found in {TOOL}")
open(TOOL, "w", encoding="utf-8").write(html[:m.start()] + seed_js + html[m.end():])
print(f"spliced {len(rows)} seed rows into {TOOL}")
