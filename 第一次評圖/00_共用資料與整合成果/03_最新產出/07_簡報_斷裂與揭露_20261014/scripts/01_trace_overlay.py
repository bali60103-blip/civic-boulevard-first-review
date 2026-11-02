# -*- coding: utf-8 -*-
"""痕跡疊圖（2026-10-14，使用者指示）
做法同《C 紅框範圍與公告當年航照》：底圖為 1:10000 線稿；以市民大道兩側帶狀範圍為遮色片，框內置入當時的歷史地圖（黑白處理），浮現當時的痕跡。
垂直幹道以極淡虛線標示，路名以小字標在圖框上、下緣。
歷史地圖：中央研究院人社中心 臺灣百年歷史地圖 WMTS（gis.sinica.edu.tw/tileserver），Web Mercator 圖磚重投影至 EPSG:3826。
用法：python3 01_trace_overlay.py [圖層代碼 ...]（預設 JM20K_1904 AMCityPlan_1945）
"""
import sys, io, re, math, json, time, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
from pyproj import Transformer
from shapely.geometry import box, shape, LineString
from shapely.ops import unary_union, transform
import fitz

UP = Path("/Users/ktlu/Desktop/第一次評圖/00_共用資料與整合成果/04_其他疊合與排版成果/CAD及官方平面疊合/urban_plan_review/南京仁愛沿線都市計畫範圍_20261006/scripts")
sys.path.insert(0, str(UP))
import build_vision_renewal_sheet as vs
import build_two_sheets as ts
from build_history_mask_sheet import insert_clipped

HERE = Path(__file__).resolve().parents[1]
CACHE = HERE / "cache"; CACHE.mkdir(exist_ok=True)
OUT = HERE / "圖"; OUT.mkdir(exist_ok=True)

LAYERS = {  # 代碼: (年份, 名稱, 副檔名, 最大 zoom)
    "JM20K_1904": (1904, "日治臺灣堡圖（明治版）1:20,000", "jpg", 17),
    "JM20K_1921": (1921, "日治臺灣堡圖（大正版）1:20,000", "jpg", 17),
    "JM25K_1921": (1921, "日治二萬五千分之一地形圖", "png", 17),
    "AMCityPlan_1945": (1945, "美軍繪製臺灣城市地圖", "png", 17),
    "AM25K_1944B": (1944, "美軍航照圖 1:25,000", "png", 15),
    "TM25K_1966": (1966, "臺灣二萬五千分一地形圖（1957–1969）", "png", 15),
}
TILE = "https://gis.sinica.edu.tw/tileserver/file-exists.php?img={id}-{ext}-{z}-{x}-{y}"
BAND = 150          # 遮色片：市民大道中心線兩側各 150 m
RES = 1.0           # 重投影解析度 m/px
RED, INK, MUTED = vs.RED, vs.INK, vs.MUTED

to_ll = Transformer.from_crs(3826, 4326, always_xy=True)


def tile_xy(lon, lat, z):
    n = 2 ** z
    return (lon + 180) / 360 * n, (1 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n


def get_tile(lid, z, x, y):
    _, _, ext, _ = LAYERS[lid]
    f = CACHE / "tiles" / lid / f"{z}_{x}_{y}.{ext}"
    if not f.exists():
        f.parent.mkdir(parents=True, exist_ok=True)
        for k in range(5):   # 伺服器偶爾斷線，重試
            try:
                b = urllib.request.urlopen(TILE.format(id=lid, ext=ext, z=z, x=x, y=y), timeout=60).read(); break
            except Exception:
                if k == 4:
                    raise
                time.sleep(2 + 3 * k)
        if len(b) < 400:            # 空圖磚（伺服器回傳 HTML）
            return None
        f.write_bytes(b)
    return Image.open(f).convert("L")


def raster_3826(lid, bounds):
    """把 WMTS 圖磚重投影成 EPSG:3826 灰階影像（左上為 minx, maxy）。"""
    f = CACHE / f"{lid}_{'_'.join(str(int(v)) for v in bounds)}_{RES}.png"
    if f.exists():
        return Image.open(f)
    z = LAYERS[lid][3]
    minx, miny, maxx, maxy = bounds
    (lo0, la0), (lo1, la1) = to_ll.transform(minx, miny), to_ll.transform(maxx, maxy)
    tx0, ty1 = tile_xy(lo0, la0, z); tx1, ty0 = tile_xy(lo1, la1, z)
    X0, X1, Y0, Y1 = int(tx0) - 1, int(tx1) + 1, int(ty0) - 1, int(ty1) + 1
    mos = np.full(((Y1 - Y0 + 1) * 256, (X1 - X0 + 1) * 256), 255, np.uint8)
    for ty in range(Y0, Y1 + 1):
        for tx in range(X0, X1 + 1):
            im = get_tile(lid, z, tx, ty)
            if im is not None:
                mos[(ty - Y0) * 256:(ty - Y0 + 1) * 256, (tx - X0) * 256:(tx - X0 + 1) * 256] = np.asarray(im)
    w, h = int((maxx - minx) / RES), int((maxy - miny) / RES)
    xs = minx + (np.arange(w) + .5) * RES; ys = maxy - (np.arange(h) + .5) * RES
    XX, YY = np.meshgrid(xs, ys)
    lon, lat = to_ll.transform(XX, YY)
    n = 2 ** z
    px = ((lon + 180) / 360 * n - X0) * 256
    py = ((1 - np.log(np.tan(np.radians(lat)) + 1 / np.cos(np.radians(lat))) / np.pi) / 2 * n - Y0) * 256
    out = mos[np.clip(py.astype(int), 0, mos.shape[0] - 1), np.clip(px.astype(int), 0, mos.shape[1] - 1)]
    img = Image.fromarray(out); img.save(f)
    return img


# 垂直幹道：OSM 主要道路，依路名歸併（去「段」、南北同名併為一條），取南北向且縱貫圖幅者
tr = Transformer.from_crs(4326, 3826, always_xy=True).transform
osm = json.load(open(vs.EXP / "source/expanded_osm.geojson"))["features"]


ARTERIALS = ["環河路", "延平路", "重慶路", "承德路", "中山路", "林森路", "新生路", "松江路", "建國路", "復興路", "敦化路", "光復路", "基隆路"]


def arterials(view):
    """與市民大道相交之南北向幹道（白名單）；回傳 (名, 幾何, 上緣路名或 None, 下緣路名或 None)。"""
    groups = {}
    for f in osm:
        p = f["properties"]; nm = p.get("name") or ""
        if p.get("highway") not in ("trunk", "primary", "secondary", "tertiary") or f["geometry"]["type"] != "LineString":
            continue
        short = re.sub(r"[一二三四五六七八九]段$", "", nm)
        key = re.sub(r"[南北]路$", "路", short)
        if key not in ARTERIALS:
            continue
        g = transform(tr, shape(f["geometry"])).intersection(view)
        if not g.is_empty:
            groups.setdefault(key, []).append((short, g))
    b = view.bounds; out = []
    for key, parts in groups.items():
        g = unary_union([q for _, q in parts])
        if not g.intersects(vs.civ.buffer(80)):
            continue

        def name_at(y):   # 碰到上／下緣之路段名稱；未達圖緣者不標
            short, q = min(parts, key=lambda t: abs((t[1].bounds[3] if y == b[3] else t[1].bounds[1]) - y))
            edge = q.bounds[3] if y == b[3] else q.bounds[1]
            return short if abs(edge - y) < 30 else None
        out.append((key, g, name_at(b[3]), name_at(b[1])))
    return sorted(out, key=lambda t: t[1].centroid.x)


def build(lid):
    yr, title, *_ = LAYERS[lid]
    src = fitz.open(vs.EXP / "pdf/A01_A10_Nanjing_Renai_20261005.pdf"); doc = fitz.open(); doc.insert_pdf(src, from_page=0, to_page=0)
    d = ts.setup(doc[0], doc); page = d.page; V = d.VIEW
    band = vs.civ.buffer(BAND, cap_style=2).buffer(-40).buffer(40).intersection(V)   # 開運算去除匝道、側路造成之突角
    # 1. 遮色片影像
    img = ImageOps.autocontrast(raster_3826(lid, V.bounds), cutoff=1)   # 紙色不一（大正版偏褐），拉齊明暗
    jb = io.BytesIO(); img.save(jb, "JPEG", quality=85)
    rings = [[d.tf(*c[:2]) for c in r.coords] for p in getattr(band, "geoms", [band]) if p.geom_type == "Polygon"
             for r in [p.exterior] + list(p.interiors)]
    b = V.bounds
    insert_clipped(page, fitz.Rect(d.tf(b[0], b[3]), d.tf(b[2], b[1])), jb.getvalue(), rings)
    d.draw(band, RED, 0.0, 0.9)
    # 2. 垂直幹道：極淡虛線＋上下緣小字路名
    top, bot = d.tf(b[0], b[3]).y, d.tf(b[0], b[1]).y
    for key, g, n_top, n_bot in arterials(V):
        s_ = page.new_shape()
        for l in getattr(g, "geoms", [g]):
            if l.geom_type == "LineString":
                s_.draw_polyline([d.tf(*c) for c in l.coords])
        s_.finish(color=(.55, .55, .55), width=0.5, dashes="[2 2.5] 0", stroke_opacity=.45); s_.commit()
        xs = [c for l in getattr(g, "geoms", [g]) if l.geom_type == "LineString" for c in l.coords]
        xt = min(xs, key=lambda c: abs(c[1] - b[3]))[0]; xb = min(xs, key=lambda c: abs(c[1] - b[1]))[0]
        if n_top:
            d.text(d.tf(xt, b[3]).x, top - 4, n_top, 6.5, "hl", MUTED, "C")
        if n_bot:
            d.text(d.tf(xb, b[1]).x, bot + 9, n_bot, 6.5, "hl", MUTED, "C")
    # 3. 只輸出圖面（裁到圖框，留上下路名空間）
    clip = fitz.Rect(d.tf(b[0], b[3]).x - 6, top - 16, d.tf(b[2], b[1]).x + 6, bot + 16)
    lab = f"{yr}｜{title}"; w = d.fm.text_length(lab, fontsize=8)
    s_ = page.new_shape(); s_.draw_rect(fitz.Rect(clip.x0 + 10, bot - 22, clip.x0 + 22 + w, bot - 8)); s_.finish(color=None, fill=(1, 1, 1)); s_.commit()
    d.text(clip.x0 + 16, bot - 12, lab, 8, "hm", INK)
    page.set_cropbox(clip)
    p = OUT / f"痕跡疊圖_{yr}_{lid}.pdf"
    doc.set_metadata({"title": f"市民大道痕跡疊圖 {yr}"}); doc.save(p, garbage=3, deflate=True)
    fitz.open(p)[0].get_pixmap(dpi=200).save(str(p).replace(".pdf", "_預覽.png"))
    print(p, round(p.stat().st_size / 1e6, 1), "MB", [a[0] for a in arterials(V)])


if __name__ == "__main__":
    for lid in (sys.argv[1:] or ["JM20K_1904", "AMCityPlan_1945"]):
        build(lid)
