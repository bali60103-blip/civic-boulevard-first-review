#!/usr/bin/env python3
"""
大直 OSM 下載 → GeoJSON（WGS84 + TWD97 / EPSG:3826）

用法：
    python3 大直_OSM下載.py              # 輸出到本檔同層的 大直_OSM/
    python3 大直_OSM下載.py --out 某資料夾

範圍＝下列「里」界聯集（OSM 台北市的里是 admin_level=9）。
要加減範圍，直接改 VILLAGES。
"""
import argparse
import json
import time
from pathlib import Path

import requests
from pyproj import Transformer
from shapely.geometry import LineString, Point, Polygon, MultiPolygon, mapping, shape
from shapely.ops import linemerge, polygonize, transform, unary_union

# ── 範圍設定 ─────────────────────────────────────────
DISTRICT = "中山區"
VILLAGES = ["大直里", "永安里", "成功里", "北安里"]

# Overpass 沒帶 User-Agent 會回 406
HEADERS = {"User-Agent": "dazhi-studio-osm/1.0"}
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# 要抓的圖層：名稱 → Overpass 篩選式（在 area.dz 範圍內）
LAYERS = {
    "buildings": 'nwr["building"](area.dz);',
    "roads": 'way["highway"](area.dz);',
    "railways": 'way["railway"](area.dz);',
    "water": 'nwr["natural"="water"](area.dz);nwr["waterway"](area.dz);',
    "landuse": 'nwr["landuse"](area.dz);nwr["leisure"](area.dz);',
    "pois": 'node["amenity"](area.dz);node["shop"](area.dz);',
}

to_twd97 = Transformer.from_crs("EPSG:4326", "EPSG:3826", always_xy=True).transform


def overpass(query):
    last = None
    for url in ENDPOINTS:
        for attempt in range(3):
            try:
                r = requests.post(url, data={"data": query}, headers=HEADERS, timeout=200)
                if r.status_code == 200:
                    return r.json()
                last = f"{url} HTTP {r.status_code}"
            except requests.RequestException as e:
                last = f"{url} {e}"
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Overpass 失敗：{last}")


def area_block():
    names = "|".join(VILLAGES)
    return (
        f'area["name"="{DISTRICT}"]["admin_level"="7"]->.d;'
        f'rel(area.d)["boundary"="administrative"]["admin_level"="9"]["name"~"^({names})$"]->.v;'
        f".v map_to_area->.dz;"
    )


# ── OSM 元素 → shapely ───────────────────────────────
AREA_KEYS = {"building", "landuse", "leisure", "natural", "amenity", "area"}


def way_geom(el):
    coords = [(p["lon"], p["lat"]) for p in el.get("geometry", [])]
    if len(coords) < 2:
        return None
    tags = el.get("tags", {})
    closed = coords[0] == coords[-1] and len(coords) >= 4
    is_area = closed and (tags.get("area") == "yes" or (AREA_KEYS & tags.keys() and "highway" not in tags))
    return Polygon(coords) if is_area else LineString(coords)


def relation_geom(el):
    """multipolygon / boundary：把 outer、inner 成員線段拼回多邊形。"""
    outers, inners = [], []
    for m in el.get("members", []):
        if m.get("type") != "way" or "geometry" not in m:
            continue
        line = LineString([(p["lon"], p["lat"]) for p in m["geometry"]])
        (inners if m.get("role") == "inner" else outers).append(line)
    if not outers:
        return None
    outer = unary_union(list(polygonize(linemerge(outers))))
    if inners:
        outer = outer.difference(unary_union(list(polygonize(linemerge(inners)))))
    return outer if not outer.is_empty else None


def to_geom(el):
    t = el["type"]
    if t == "node":
        return Point(el["lon"], el["lat"])
    if t == "way":
        return way_geom(el)
    if t == "relation":
        return relation_geom(el)


def write_fc(path, feats):
    path.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False), encoding="utf-8")


def export(name, elements, boundary, out):
    wgs, twd = [], []
    for el in elements:
        g = to_geom(el)
        if g is None or not g.is_valid and not (g := g.buffer(0)).is_valid:
            continue
        if not g.intersects(boundary):  # 跨界的保留整棟/整條，不切
            continue
        props = {"osm_id": f'{el["type"]}/{el["id"]}', **el.get("tags", {})}
        wgs.append({"type": "Feature", "properties": props, "geometry": mapping(g)})
        twd.append({"type": "Feature", "properties": props, "geometry": mapping(transform(to_twd97, g))})
    write_fc(out / f"dazhi_{name}_WGS84.geojson", wgs)
    write_fc(out / f"dazhi_{name}_TWD97.geojson", twd)
    print(f"  {name:10s} {len(wgs):6d} 筆")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).with_name("大直_OSM")))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    print("抓里界…")
    data = overpass(f"[out:json][timeout:180];{area_block()}.v out geom;")
    villages = [(e["tags"]["name"], relation_geom(e)) for e in data["elements"]]
    found = {n for n, _ in villages}
    if missing := set(VILLAGES) - found:
        print(f"  ⚠ OSM 找不到：{missing}")
    boundary = unary_union([g for _, g in villages if g is not None])

    vfeats = [{"type": "Feature", "properties": {"name": n}, "geometry": mapping(g)} for n, g in villages if g]
    write_fc(out / "dazhi_boundary_villages_WGS84.geojson", vfeats)
    write_fc(out / "dazhi_boundary_WGS84.geojson",
             [{"type": "Feature", "properties": {"name": "大直", "villages": sorted(found)}, "geometry": mapping(boundary)}])
    write_fc(out / "dazhi_boundary_TWD97.geojson",
             [{"type": "Feature", "properties": {"name": "大直", "villages": sorted(found)},
               "geometry": mapping(transform(to_twd97, boundary))}])
    print(f"  里：{sorted(found)}")

    for name, filt in LAYERS.items():
        print(f"抓 {name}…")
        data = overpass(f"[out:json][timeout:180];{area_block()}({filt});out geom;")
        export(name, data["elements"], boundary, out)
        time.sleep(2)  # 對公用伺服器客氣一點

    print(f"完成 → {out}")


if __name__ == "__main__":
    main()
