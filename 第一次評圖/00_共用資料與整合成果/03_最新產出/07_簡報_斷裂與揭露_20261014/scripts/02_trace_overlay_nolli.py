# -*- coding: utf-8 -*-
"""痕跡疊圖（二）：底圖改為諾利圖（2026-10-14，使用者指示）
・底圖：06_市民大道諾利圖 之圖底（私有建物黑、公共室內外框、水域細橫線、暖黃紙紋），1:10,000 重繪於線稿帶範圍（E300935–307545、N2770000–2771910）。
・遮色片：市民大道中心線兩側 150 m 為基準，邊緣改抓街廓邊緣——街廓（線稿帶範圍扣除 road_surfaces 道路面）有一半以上落在 150 m 內者整塊納入，
  再加上市民大道路面，以 25 m 閉運算補上街廓之間的街道；河濱段以淡水河堤防（OSM flood_wall）為界，堤外不納入。
・遮色片內：當時的歷史地圖（同 01，WMTS 重投影、黑白、拉齊明暗）；紅線＝遮色片外框。
・垂直幹道極淡虛線、圖上下緣小字路名（同 01）。
用法：python3 02_trace_overlay_nolli.py [圖層代碼 ...]（預設 JM20K_1904 JM20K_1921 AMCityPlan_1945）
"""
import sys, io, json, importlib.util
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
from shapely.geometry import box, shape, Point, LineString, Polygon
from shapely.ops import unary_union
import fitz

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


T1 = load("t1", HERE / "scripts/01_trace_overlay.py")                      # 圖磚、重投影、幹道、insert_clipped
NL = load("nolli", ROOT / "03_最新產出/06_市民大道諾利圖_20261014/scripts/02_nolli.py")   # PRIV／PUB／WATER、紙紋
vs = T1.vs
OUT = HERE / "圖"
RED, INK, MUTED = vs.RED, vs.INK, vs.MUTED

VIEW = box(300935, 2770000, 307545, 2771910)
SCALE = 10000
K = 72 / 25.4
MX, MY = 8 * K, 9 * K                                    # 圖框外留白（上下放路名）
PW, PH = (VIEW.bounds[2] - VIEW.bounds[0]) / SCALE * 1000 * K + 2 * MX, (VIEW.bounds[3] - VIEW.bounds[1]) / SCALE * 1000 * K + 2 * MY


def tf(x, y):
    return fitz.Point(MX + (x - VIEW.bounds[0]) / SCALE * 1000 * K, PH - MY - (y - VIEW.bounds[1]) / SCALE * 1000 * K)


# ── 遮色片 ──────────────────────────────────────────────
BAND, CLOSE, SHARE = 150, 25, .5


def mask_geom():
    core = vs.civ.buffer(BAND, cap_style=2).buffer(-40).buffer(40)
    roads = unary_union([shape(f["geometry"]).buffer(0) for f in json.load(open(vs.EXP / "road_surfaces_TWD97.geojson"))["features"]])
    blocks = [b for b in getattr(VIEW.difference(roads), "geoms", []) if b.area > 20]
    sel = [b for b in blocks if b.intersection(core).area >= SHARE * b.area]
    m = unary_union(sel + [roads.intersection(vs.civ.buffer(70))])
    m = m.buffer(CLOSE, join_style=2).buffer(-CLOSE, join_style=2)
    # 河濱段：以堤防為界，只留堤內（東側）
    fs = {f["properties"]["osm_id"]: f["geometry"]["coordinates"] for f in json.load(open(HERE / "data/淡水河堤防_EPSG3826.geojson"))["features"]}
    pts = fs["way/1017345548"][::-1] + fs["way/383978058"][::-1][1:]   # 兩段堤防由南而北串接（交點 E301120／N2771503）
    river = Polygon(pts + [(298000, pts[-1][1]), (298000, pts[0][1])]).buffer(0)
    m = m.difference(river).intersection(VIEW)
    return unary_union([p for p in getattr(m, "geoms", [m]) if p.geom_type == "Polygon" and p.area > 2000]), len(sel)


# ── 繪圖工具 ────────────────────────────────────────────
def rings(g):
    return [[tf(*c[:2]) for c in r.coords] for p in getattr(g, "geoms", [g]) if p.geom_type == "Polygon" and not p.is_empty
            for r in [p.exterior] + list(p.interiors)]


def fill(page, gs, fillc=None, stroke=None, width=0.0):
    s_ = page.new_shape(); n = 0
    for g in gs:
        for ring in rings(g):
            s_.draw_polyline(ring); n += 1
    if n:
        s_.finish(color=stroke, fill=fillc, width=width, closePath=True, even_odd=True); s_.commit()


def build(lid, M):
    yr, title, *_ = T1.LAYERS[lid]
    doc = fitz.open(); page = doc.new_page(width=PW, height=PH)
    page.insert_font(fontname="hl", fontfile=vs.FONT_L); page.insert_font(fontname="hm", fontfile=vs.FONT_M)
    fl, fm = fitz.Font(fontfile=vs.FONT_L), fitz.Font(fontfile=vs.FONT_M)

    def text(x, y, s, size, font="hl", color=INK, align="L"):
        w = (fm if font == "hm" else fl).text_length(s, fontsize=size)
        page.insert_text((x - w if align == "R" else x - w / 2 if align == "C" else x, y), s, fontsize=size, fontname=font, color=color); return w
    paper = tuple(int(NL.PAPER_HEX[i:i + 2], 16) / 255 for i in (1, 3, 5))
    s_ = page.new_shape(); s_.draw_rect(page.rect); s_.finish(color=None, fill=(1, 1, 1)); s_.commit()
    frame = fitz.Rect(tf(VIEW.bounds[0], VIEW.bounds[3]), tf(VIEW.bounds[2], VIEW.bounds[1]))
    # 1. 紙紋（自諾利圖 A1 紙紋裁出同一範圍）
    if not NL.TEX.exists():
        NL.make_texture(NL.TEX)
    tex = Image.open(NL.TEX); fx0, fy0, fx1, fy1 = NL.FRAME.bounds; ppm = tex.width / (fx1 - fx0)
    crop = tex.crop((int((VIEW.bounds[0] - fx0) * ppm), int((fy1 - VIEW.bounds[3]) * ppm), int((VIEW.bounds[2] - fx0) * ppm), int((fy1 - VIEW.bounds[1]) * ppm)))
    jb = io.BytesIO(); crop.save(jb, "JPEG", quality=88); page.insert_image(frame, stream=jb.getvalue())
    # 2. 水域細橫線
    W_ = NL.WATER.intersection(VIEW); s_ = page.new_shape(); n = 0
    if not W_.is_empty:
        y = VIEW.bounds[1]
        while y < VIEW.bounds[3]:
            seg = LineString([(VIEW.bounds[0], y), (VIEW.bounds[2], y)]).intersection(W_)
            for l in getattr(seg, "geoms", [seg]):
                if l.geom_type == "LineString" and l.length > 0:
                    s_.draw_line(tf(*l.coords[0]), tf(*l.coords[-1])); n += 1
            y += 9
        if n:
            s_.finish(color=INK, width=.25); s_.commit()
    # 3. 建物：私有黑、公共室內外框
    fill(page, [g.intersection(VIEW) for g in NL.PRIV if g.intersects(VIEW)], fillc=(0, 0, 0))
    fill(page, [g.intersection(VIEW) for g in NL.PUB if g.intersects(VIEW)], stroke=(0, 0, 0), width=.35)
    # 4. 遮色片：當時的地圖
    img = ImageOps.autocontrast(T1.raster_3826(lid, VIEW.bounds), cutoff=1)
    jb = io.BytesIO(); img.save(jb, "JPEG", quality=85)
    T1.insert_clipped(page, frame, jb.getvalue(), rings(M))
    fill(page, [M], stroke=RED, width=.9)
    # 5. 垂直幹道：極淡虛線＋上下緣小字路名
    b = VIEW.bounds
    for key, g, n_top, n_bot in T1.arterials(VIEW):
        s_ = page.new_shape(); xs = []
        for l in getattr(g, "geoms", [g]):
            if l.geom_type == "LineString":
                s_.draw_polyline([tf(*c) for c in l.coords]); xs += list(l.coords)
        s_.finish(color=(.55, .55, .55), width=0.5, dashes="[2 2.5] 0", stroke_opacity=.5); s_.commit()
        if n_top:
            text(tf(min(xs, key=lambda c: abs(c[1] - b[3]))[0], 0).x, frame.y0 - 4, n_top, 6.5, "hl", MUTED, "C")
        if n_bot:
            text(tf(min(xs, key=lambda c: abs(c[1] - b[1]))[0], 0).x, frame.y1 + 9, n_bot, 6.5, "hl", MUTED, "C")
    s_ = page.new_shape(); s_.draw_rect(frame); s_.finish(color=INK, width=.4); s_.commit()
    # 6. 圖說（只放背景資料）
    lab = f"{yr}｜{title}"; w = fm.text_length(lab, fontsize=8)
    s_ = page.new_shape(); s_.draw_rect(fitz.Rect(frame.x0 + 6, frame.y1 - 20, frame.x0 + 18 + w, frame.y1 - 6)); s_.finish(color=None, fill=paper); s_.commit()
    text(frame.x0 + 12, frame.y1 - 10, lab, 8, "hm", INK)
    p = OUT / f"痕跡疊圖_諾利底_{yr}_{lid}.pdf"
    doc.set_metadata({"title": f"市民大道痕跡疊圖（諾利圖底）{yr}"}); doc.save(p, garbage=3, deflate=True)
    fitz.open(p)[0].get_pixmap(dpi=200).save(str(p).replace(".pdf", "_預覽.png"))
    print(p.name, round(p.stat().st_size / 1e6, 1), "MB")


if __name__ == "__main__":
    M, n = mask_geom()
    print("遮色片：街廓", n, "塊；面積", round(M.area / 1e4, 1), "ha")
    for lid in (sys.argv[1:] or ["JM20K_1904", "JM20K_1921", "AMCityPlan_1945"]):
        build(lid, M)
