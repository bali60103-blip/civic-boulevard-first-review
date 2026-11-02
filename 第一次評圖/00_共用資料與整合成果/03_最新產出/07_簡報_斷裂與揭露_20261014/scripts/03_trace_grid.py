# -*- coding: utf-8 -*-
"""痕跡疊圖（三）：500 m 方格判定（2026-10-14，使用者指示：「每 500 m 畫一條虛線，用虛線的矩陣去判定該方格要舊地圖或是諾利圖；
諾利圖底圖改白色，不要 texture；舊地圖反黑」）
・方格：TWD97 座標整 500 m（E…000／…500、N…000／…500）虛線。
・判定：02 之街廓遮色片（150 m 基準、外緣抓街廓、堤防為界）佔該方格（裁至圖框）面積 ≥ 30% → 舊地圖；其餘 → 諾利圖。
  舊地圖方格仍裁去堤外（河濱段停在堤防）。
・諾利圖：白底、私有建物黑、公共室內外框、水域細橫線（不用紙紋）。
・舊地圖：黑白反轉（黑底白線）。
・垂直幹道極淡虛線、上下緣小字路名、左下圖說（同 02）。
用法：python3 03_trace_grid.py [圖層代碼 ...]（預設 JM20K_1904 JM20K_1921 AMCityPlan_1945）
"""
import sys, io, json, math, importlib.util
from pathlib import Path
from PIL import ImageOps
from shapely.geometry import box, shape, LineString, Polygon
from shapely.ops import unary_union
import fitz

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("t2", HERE / "scripts/02_trace_overlay_nolli.py")
T2 = importlib.util.module_from_spec(spec); spec.loader.exec_module(T2)
T1, NL, vs = T2.T1, T2.NL, T2.vs
VIEW, tf, rings, fill = T2.VIEW, T2.tf, T2.rings, T2.fill
INK, MUTED = vs.INK, vs.MUTED
OUT = HERE / "圖"
GRID, SHARE = 200, .30   # 2026-10-14 使用者改 200 m（原 500 m）


def cells(M):
    """回傳 (舊地圖方格聯集, 方格線 x 值, 方格線 y 值, 方格判定表)"""
    b = VIEW.bounds
    xs = [x for x in range(math.ceil(b[0] / GRID) * GRID, int(b[2]) + 1, GRID)]
    ys = [y for y in range(math.ceil(b[1] / GRID) * GRID, int(b[3]) + 1, GRID)]
    fs = {f["properties"]["osm_id"]: f["geometry"]["coordinates"] for f in json.load(open(HERE / "data/淡水河堤防_EPSG3826.geojson"))["features"]}
    pts = fs["way/1017345548"][::-1] + fs["way/383978058"][::-1][1:]
    river = Polygon(pts + [(298000, pts[-1][1]), (298000, pts[0][1])]).buffer(0)
    old, table = [], []
    x0 = math.floor(b[0] / GRID) * GRID
    while x0 < b[2]:
        y0 = math.floor(b[1] / GRID) * GRID
        while y0 < b[3]:
            c = box(x0, y0, x0 + GRID, y0 + GRID).intersection(VIEW)
            sh = c.intersection(M).area / c.area if c.area else 0
            table.append((x0, y0, round(sh, 2), sh >= SHARE))
            if sh >= SHARE:
                old.append(c)
            y0 += GRID
        x0 += GRID
    return unary_union(old).difference(river), xs, ys, table


def build(lid, OLD, xs, ys):
    yr, title, *_ = T1.LAYERS[lid]
    doc = fitz.open(); page = doc.new_page(width=T2.PW, height=T2.PH)
    page.insert_font(fontname="hl", fontfile=vs.FONT_L); page.insert_font(fontname="hm", fontfile=vs.FONT_M)
    fl, fm = fitz.Font(fontfile=vs.FONT_L), fitz.Font(fontfile=vs.FONT_M)

    def text(x, y, s, size, font="hl", color=INK, align="L"):
        w = (fm if font == "hm" else fl).text_length(s, fontsize=size)
        page.insert_text((x - w if align == "R" else x - w / 2 if align == "C" else x, y), s, fontsize=size, fontname=font, color=color); return w
    s_ = page.new_shape(); s_.draw_rect(page.rect); s_.finish(color=None, fill=(1, 1, 1)); s_.commit()
    b = VIEW.bounds
    frame = fitz.Rect(tf(b[0], b[3]), tf(b[2], b[1]))
    # 1. 諾利圖（白底）
    W_ = NL.WATER.intersection(VIEW); s_ = page.new_shape(); n = 0; y = b[1]
    while y < b[3]:
        seg = LineString([(b[0], y), (b[2], y)]).intersection(W_)
        for l in getattr(seg, "geoms", [seg]):
            if l.geom_type == "LineString" and l.length > 0:
                s_.draw_line(tf(*l.coords[0]), tf(*l.coords[-1])); n += 1
        y += 9
    if n:
        s_.finish(color=INK, width=.25); s_.commit()
    fill(page, [g.intersection(VIEW) for g in NL.PRIV if g.intersects(VIEW)], fillc=(0, 0, 0))
    fill(page, [g.intersection(VIEW) for g in NL.PUB if g.intersects(VIEW)], stroke=(0, 0, 0), width=.35)
    # 2. 舊地圖方格（反黑）
    img = ImageOps.invert(ImageOps.autocontrast(T1.raster_3826(lid, b), cutoff=1).convert("L"))
    jb = io.BytesIO(); img.save(jb, "JPEG", quality=85)
    T1.insert_clipped(page, frame, jb.getvalue(), rings(OLD))
    # 3. 垂直幹道（極淡虛線）＋上下緣路名
    for key, g, n_top, n_bot in T1.arterials(VIEW):
        s_ = page.new_shape(); pts = []
        for l in getattr(g, "geoms", [g]):
            if l.geom_type == "LineString":
                s_.draw_polyline([tf(*c) for c in l.coords]); pts += list(l.coords)
        s_.finish(color=(.55, .55, .55), width=0.5, dashes="[2 2.5] 0", stroke_opacity=.5); s_.commit()
        if n_top:
            text(tf(min(pts, key=lambda c: abs(c[1] - b[3]))[0], 0).x, frame.y0 - 4, n_top, 6.5, "hl", MUTED, "C")
        if n_bot:
            text(tf(min(pts, key=lambda c: abs(c[1] - b[1]))[0], 0).x, frame.y1 + 9, n_bot, 6.5, "hl", MUTED, "C")
    # 4. 500 m 方格虛線
    s_ = page.new_shape()
    for x in xs:
        s_.draw_line(tf(x, b[1]), tf(x, b[3]))
    for y in ys:
        s_.draw_line(tf(b[0], y), tf(b[2], y))
    s_.finish(color=(.5, .5, .5), width=.6, dashes="[6 4] 0"); s_.commit()
    s_ = page.new_shape(); s_.draw_rect(frame); s_.finish(color=INK, width=.4); s_.commit()
    # 5. 圖說
    lab = f"{yr}｜{title}"; w = fm.text_length(lab, fontsize=8)
    s_ = page.new_shape(); s_.draw_rect(fitz.Rect(frame.x0 + 6, frame.y1 - 20, frame.x0 + 18 + w, frame.y1 - 6)); s_.finish(color=None, fill=(1, 1, 1)); s_.commit()
    text(frame.x0 + 12, frame.y1 - 10, lab, 8, "hm", INK)
    p = OUT / f"痕跡疊圖_方格{GRID}m_{yr}_{lid}.pdf"
    doc.set_metadata({"title": f"市民大道痕跡疊圖（{GRID} m 方格）{yr}"}); doc.save(p, garbage=3, deflate=True)
    fitz.open(p)[0].get_pixmap(dpi=200).save(str(p).replace(".pdf", "_預覽.png"))
    print(p.name, round(p.stat().st_size / 1e6, 1), "MB")


if __name__ == "__main__":
    M, _ = T2.mask_geom()
    OLD, xs, ys, table = cells(M)
    json.dump([dict(E=x, N=y, 遮色片占比=s, 舊地圖=o) for x, y, s, o in table], open(HERE / f"data/方格判定_{GRID}m.json", "w"), ensure_ascii=False, indent=0)
    print("舊地圖方格", sum(1 for *_, o in table if o), "／", len(table))
    for lid in (sys.argv[1:] or ["JM20K_1904", "JM20K_1921", "AMCityPlan_1945"]):
        build(lid, OLD, xs, ys)
