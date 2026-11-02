# -*- coding: utf-8 -*-
"""彙整 8 件公共都更／公共建設的「建築量體剪影、敷地設計、基地範圍」為單一 EPSG:3826 GeoJSON。

layer 欄位：
  building  建築量體剪影（官方平面圖描繪）
  landscape 敷地設計（廣場、綠地、步道、橋面等公共空間）
  site      基地範圍（有平面圖者為底層；無平面圖者為唯一圖層，basis=boundary_only）

來源：
  - U17、B01、B02、B03：官方平面描圖_EPSG3826.geojson（2026-10-04 既有描圖，對位紀錄見同目錄 JSON）
  - U02 長安市民：住都中心 2025-12-12 公辦公聽會簡報 p.33「建築物配置理念」一層配置，
    以紅色基地線 4 角對位官方 5 筆地號外界（仿射最小平方），本腳本描繪建物外輪廓
  - U01、U03、U10：無公開配置圖，以地籍／分區範圍概括
地籍：臺北市 historygis Urban/Land MapServer layer 5；分區：Urban/UrbanPlan MapServer layer 1。
"""
import json
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon, mapping, shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[2]
CAD = ROOT / "04_其他疊合與排版成果/CAD及官方平面疊合"
TRACE = CAD / "官方平面描圖_EPSG3826.geojson"
PARCELS_OLD = CAD / "正式地號界線_EPSG3826.geojson"
OUT = Path(__file__).resolve().parent / "公共案件量體與基地_EPSG3826.geojson"
LOG = Path(__file__).resolve().parent / "量體來源與對位紀錄.json"

GIS = "https://www.historygis.udd.gov.taipei/arcgis/rest/services"


def query(url, **params):
    params.update(f="json", outSR=3826, returnGeometry="true")
    with urllib.request.urlopen(url + "/query?" + urllib.parse.urlencode(params), timeout=90) as r:
        return json.load(r)


def parcels(sect, lots):
    where = f"SECTCODE='{sect}' AND LANDCODE IN ({','.join(repr(l) for l in lots)})"
    feats = query(f"{GIS}/Urban/Land/MapServer/5", where=where, outFields="SECTCODE,LANDCODE")["features"]
    missing = set(lots) - {f["attributes"]["LANDCODE"] for f in feats}
    assert not missing, (sect, missing)
    return clean(unary_union([Polygon(f["geometry"]["rings"][0]) for f in feats]))


def clean(g):
    return g.buffer(0.05, join_style=2).buffer(-0.05, join_style=2)


def rng(a, b):
    return [str(i) for i in range(a, b + 1)]


def affine_fit(src, dst):
    A = np.hstack([np.asarray(src, float), np.ones((len(src), 1))])
    M, *_ = np.linalg.lstsq(A, np.asarray(dst, float), rcond=None)
    resid = np.linalg.norm(A @ M - dst, axis=1)
    return M, resid


features, log = [], {}


def add(case, layer, geom, label, basis, source):
    features.append({"type": "Feature", "geometry": mapping(geom),
                     "properties": {"case": case, "layer": layer, "label": label,
                                    "basis": basis, "source": source}})


# ---------- 既有官方平面描圖（U17、B01、B02、B03） ----------
trace = json.loads(TRACE.read_text(encoding="utf-8"))["features"]
LAYER_OF = {"building": "building", "facility": "building", "heritage": "landscape",
            "landscape": "landscape", "bridge": "landscape", "study": "site"}
for f in trace:
    p = f["properties"]
    if p.get("case") not in ("U17", "B01", "B02", "B03") or f["geometry"]["type"] != "Polygon":
        continue
    layer = LAYER_OF.get(p["kind"])
    if not layer:
        continue
    # B02 橋面是公共工程本體，量體用中透明度：歸為 landscape（敷地／公共空間）
    add(p["case"], layer, shape(f["geometry"]), p["label"], "traced_plan", p.get("status", ""))

old = {f["properties"]["id"]: shape(f["geometry"]) for f in
       json.loads(PARCELS_OLD.read_text(encoding="utf-8"))["features"]}
add("U17", "site", clean(old["U17"]), "行二行三 46 筆地號外界", "parcel", "正式地號界線（2026-10-04 比對）")
add("B01", "site", clean(old["B01"]), "華山司法園區 9 筆地號外界", "parcel", "正式地號界線（2026-10-04 比對）")

# ---------- U02 長安市民：描繪 p.33 一層配置 ----------
u02_site = parcels("AC0420", ["596", "596-1", "596-2", "596-3", "596-4"])
# 簡報頁碼 -33-（PDF index 16 下半，200 dpi 裁切）紅色基地線角點 ↔ 地號外界角點
src = [(881, 300), (881, 739), (285, 739), (170, 312)]
dst = [(304522.3, 2770901.8), (304519.2, 2770847.4), (304445.0, 2770852.5), (304434.0, 2770905.0)]
M, resid = affine_fit(src, dst)
bldg_px = [(301, 366), (609, 366), (609, 447.5), (745, 447.5), (745, 540), (815, 540),
           (815, 620), (480, 620), (480, 600), (301, 600)]
bldg = Polygon([tuple(np.array([x, y, 1.0]) @ M) for x, y in bldg_px])
SRC_U02 = "住都中心 1141212 公辦公聽會簡報 p.33 建築物配置理念（送審版本）"
add("U02", "site", u02_site, "長安段二小段 596 等 5 筆", "parcel", "臺北市地籍 GIS")
add("U02", "landscape", u02_site.difference(bldg), "法定空地／街角廣場／人行步道", "traced_plan", SRC_U02)
add("U02", "building", bldg, "23 層住宅（1F 托嬰中心＋店鋪）", "traced_plan", SRC_U02)
log["U02"] = {"source_url": "https://apis-ur.hurc.org.tw/static/A-104-002/file/81942d028dc54b6aa0f4a6429a8e7742.pdf",
              "page": "PDF index 16 下半（簡報頁碼 -33-）", "render": "200 dpi，裁下半頁",
              "controls_px": src, "controls_3826": dst, "residual_m": [round(r, 2) for r in resid],
              "building_area_m2": round(bldg.area, 1), "site_area_m2": round(u02_site.area, 1),
              "coverage": round(bldg.area / u02_site.area, 3),
              "check": "簡報載開放空間 65.84%（建蔽約 34%）"}

# ---------- 無配置圖：基地範圍概括 ----------
u03 = parcels("AC0420", ["576", "576-1", "576-2", "576-3"])
add("U03", "site", u03, "長安段二小段 576 等 4 筆（4,107 ㎡）", "boundary_only", "都更處 S14 地號清單＋地籍 GIS")

u10_lots = (["58", "58-1"] + rng(61, 71) + ["61-1", "71-1", "72", "72-1", "72-2", "72-3", "73"]
            + rng(77, 87) + ["89", "90"])
u10 = parcels("AD0704", u10_lots)
add("U10", "site", u10, "西松段三小段 58 等 33 筆（3,900 ㎡）", "boundary_only",
    "都更處 S18 地號清單＋地籍 GIS；清單漏列 72 地號，依面積 3,900 ㎡ 補入")

z = query(f"{GIS}/Urban/UrbanPlan/MapServer/1", geometry="301300,2771300,301420,2771420",
          geometryType="esriGeometryEnvelope", inSR=3826, spatialRel="esriSpatialRelIntersects",
          outFields="ID,NAME")["features"]
e1e2 = [Polygon(f["geometry"]["rings"][0]) for f in z if f["attributes"]["ID"] == "D"][0]
add("U01", "site", clean(e1e2), "E1／E2 特定專用區街廓（更新單元 17 筆 16,086 ㎡ 位於其中）",
    "boundary_only", "都市計畫使用分區 GIS；未逐筆比對 17 筆地號")

for k, g in {"U01": e1e2, "U03": u03, "U10": u10}.items():
    log[k] = {"area_m2": round(g.area, 1), "basis": "boundary_only"}
log["U10"]["note"] = "官網文字 33 筆，列舉僅 32 筆；補 72 地號後 3,895 ㎡ ≈ 公告 3,900 ㎡"
log["U03"]["doc_area_m2"] = 4107
log["U01"]["doc_area_m2"] = 16085.70

OUT.write_text(json.dumps({"type": "FeatureCollection",
                           "crs": {"type": "name", "properties": {"name": "EPSG:3826"}},
                           "features": features}, ensure_ascii=False), encoding="utf-8")
LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
print(len(features), "features ->", OUT.name)
print(json.dumps(log, ensure_ascii=False, indent=1))
