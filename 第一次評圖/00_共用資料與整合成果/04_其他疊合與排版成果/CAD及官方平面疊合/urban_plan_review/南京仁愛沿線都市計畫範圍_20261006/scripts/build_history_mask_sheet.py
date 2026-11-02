# -*- coding: utf-8 -*-
"""C 圖：紅框範圍為遮色片，框內放入該案公告當年航照（2026-10-14）
底圖同 B 圖（1:10000 線稿）；每個紅框以其計畫範圍裁切公告當年（無則最近後一年）之臺北市歷史正射影像，
小範圍疊在大範圍之上；紅框、編號與下方文字欄位同 B 圖，紅框一覽加註影像年份。
"""
import sys, io
from pathlib import Path
import fitz
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_vision_renewal_sheet as vs
import build_two_sheets as ts
import build_history_sheet as hs

RED, MUTED, INK = vs.RED, vs.MUTED, vs.INK


def masked_image(g, year, extent=None):
    minx, miny, maxx, maxy = (extent or g).bounds   # 影像範圍沿用全案外包（可重用快取）
    res = max(0.8, max(maxx - minx, maxy - miny) / 4000)
    w, h = max(8, int((maxx - minx) / res)), max(8, int((maxy - miny) / res))
    bbox = (round(minx, 1), round(miny, 1), round(minx + w * res, 1), round(miny + h * res, 1))
    img = Image.open(hs.fetch(year, bbox, w, h)).convert("L")   # 黑白處理
    m = Image.new("L", (w, h), 0); dr = ImageDraw.Draw(m)
    px = lambda c: ((c[0] - bbox[0]) / res, (bbox[3] - c[1]) / res)
    for p in getattr(g, "geoms", [g]):
        if p.geom_type != "Polygon" or p.is_empty:
            continue
        dr.polygon([px(c) for c in p.exterior.coords], fill=255)
        for r in p.interiors:
            dr.polygon([px(c) for c in r.coords], fill=0)
    jb, mb = io.BytesIO(), io.BytesIO()
    img.save(jb, "JPEG", quality=82); m.save(mb, "PNG")
    return bbox, jb.getvalue(), mb.getvalue()


CLOSE_M = 40   # 多街廓個案（如 TOD）以 40 m 閉合運算，補入街廓之間的幹道與巷道（含路口）


def full_geom(it, view):
    g = it["geom"].intersection(view)
    if len(getattr(g, "geoms", [g])) > 2:
        g = g.buffer(CLOSE_M, join_style=2).buffer(-CLOSE_M, join_style=2).intersection(view)
    return g


def mask_geom(it, view):
    g = full_geom(it, view)
    parts = [q for q in getattr(g, "geoms", [g]) if q.geom_type == "Polygon" and not q.is_empty]
    return min(parts, key=lambda q: q.distance(it["rp"]))   # 只留編號所在的那一塊


def frame_geom(it, view):
    return it["geom"].intersection(view).intersection(mask_geom(it, view).buffer(0.5))


def insert_clipped(page, rect, jpg, rings):
    """插入影像並以紅框多邊形作 PDF 剪裁路徑（W* n），避免 SMask 在 macOS 預覽程式不顯示。"""
    xref = page.insert_image(rect, stream=jpg)
    name = [x[7] for x in page.get_images(full=True) if x[0] == xref][0].encode()
    H = page.rect.height
    path = b"".join(b"%.3f %.3f m " % (r[0].x, H - r[0].y) + b"".join(b"%.3f %.3f l " % (q.x, H - q.y) for q in r[1:]) + b"h\n"
                    for r in rings)
    for cx in reversed(page.get_contents()):
        st = page.parent.xref_stream(cx); i = st.rfind(b"/" + name + b" Do")
        if i < 0:
            continue
        qpos = st.rfind(b"q", 0, i)
        page.parent.update_stream(cx, st[:qpos + 1] + b"\n" + path + b"W* n\n" + st[qpos + 1:])
        return
    raise RuntimeError("image op not found")


def main():
    src = fitz.open(vs.EXP / "pdf/A01_A10_Nanjing_Renai_20261005.pdf"); doc = fitz.open(); doc.insert_pdf(src, from_page=0, to_page=0)
    d = ts.setup(doc[0], doc); page = d.page
    yr = {}
    for it in vs.items:
        ad0 = min(int(vs.PER[c]) for c in it["codes"]) + 1911
        yr[it["no"]] = (ad0, hs.pick_year(ad0))
    # 1. 遮色片影像：面積大者先放，小者疊上
    for it in sorted(vs.items, key=lambda it: -mask_geom(it, d.VIEW).area):
        g = mask_geom(it, d.VIEW)
        if g.is_empty:
            continue
        bbox, jpg, _ = masked_image(g, yr[it["no"]][1], full_geom(it, d.VIEW))
        rings = [[d.tf(*c[:2]) for c in r.coords] for p in getattr(g, "geoms", [g]) if p.geom_type == "Polygon" and not p.is_empty
                 for r in [p.exterior] + list(p.interiors)]
        insert_clipped(page, fitz.Rect(d.tf(bbox[0], bbox[3]), d.tf(bbox[2], bbox[1])), jpg, rings)
    # 2. 紅框與編號
    for nm, k in vs.DIST:
        g = vs.U[k].intersection(d.VIEW)
        if not g.is_empty:
            d.draw(g, (.55, .55, .55), 0.0, 0.5, "[1 2] 0")
    for it in vs.items:
        g0 = frame_geom(it, d.VIEW); g1 = mask_geom(it, d.VIEW)
        if g1.symmetric_difference(g0).area < 1:
            d.draw(g0, RED, 0.0, 1.0)
        else:   # 街廓群：外框粗線、原街廓細線
            d.draw(g1, RED, 0.0, 1.0); d.draw(g0, RED, 0.0, 0.35)
    for it in vs.items:
        pt = d.tf(it["rp"].x, it["rp"].y); s_ = page.new_shape(); s_.draw_circle(pt, 6.2)
        s_.finish(color=RED, fill=(1, 1, 1), width=0.8); s_.commit()
        d.text(pt.x, pt.y + 2.9, str(it["no"]), 7.8, "hm", RED, "C")
    Y_END = 1626
    ts.segments(d, Y_END)
    d.text(115, 118, "南京西路—仁愛路沿線｜紅框範圍 × 公告當年航照", 30, "hm")
    d.text(115, 144, "底圖：A01_A10_Nanjing_Renai_20261005 第 1 頁線稿（1:10000）。紅框＝沿線 24 個都市計畫個案範圍，以紅框為遮色片，框內置入該案公告當年之臺北市歷史正射影像"
           "（當年無影像取公告後最近一年；合併案以最早公告年為準）。範圍重疊處小範圍疊於大範圍之上；影像皆經黑白處理。多街廓個案（#4、#16）以 40 m 閉合運算補入街廓間之道路與巷道，粗紅線為閉合後外框、細紅線為原街廓。各案僅保留編號所在之範圍，其餘分散範圍不繪。", 11.5, "hl", MUTED)
    x, y = 115, 182
    s_ = page.new_shape(); s_.draw_rect(fitz.Rect(x, y - 10, x + 22, y + 3)); s_.finish(color=RED, fill=(.45, .45, .4), fill_opacity=.6, width=1.1); s_.commit()
    x += 30 + d.text(x + 30, y, "都市計畫個案範圍（框內＝公告當年航照）", 11) + 22
    s_ = page.new_shape(); s_.draw_line(fitz.Point(x, y - 4), fitz.Point(x + 22, y - 4)); s_.finish(color=(.55, .55, .55), width=.6, dashes="[1 2] 0"); s_.commit()
    d.text(x + 30, y, "行政區通檢範圍界", 11)
    ts.scalebar(d)

    PAD = 8; y0 = 985
    d.heading(115, y0 - 16, "各段更新意圖", 16); d.rule(y0 - 8, 1.4)
    sb = y0
    for i, (_, _, nm, rng, _) in enumerate(ts.SEG):
        x0, x1 = d.SEGX[i]; cw = x1 - x0 - 2 * PAD
        d.text(x0 + PAD, y0 + 12, nm, 13, "hm"); d.text(x0 + PAD, y0 + 27, rng, 9.5, "hl", MUTED)
        ls = d.wrap(ts.INTENT[i], 10.5, cw)
        for j, ln in enumerate(ls):
            d.text(x0 + PAD, y0 + 46 + j * 14, ln, 10.5)
        sb = max(sb, y0 + 46 + len(ls) * 14)
    ty = sb + 30
    d.heading(115, ty - 14, "紅框一覽｜依所在分段排列（公告年 → 框內影像年）", 14); d.rule(ty - 6, 1.0)
    yb = []
    for i in range(len(ts.SEG)):
        x0, x1 = d.SEGX[i]; cw = x1 - x0 - 2 * PAD - 22; yy = ty + 8
        for it in [it for it in vs.items if ts.seg_index(it["rp"].x) == i]:
            key = next(c for c in it["codes"] if c in ts.SHORT); ad0, y_ = yr[it["no"]]
            c_ = fitz.Point(x0 + PAD + 7, yy + 3); s_ = page.new_shape(); s_.draw_circle(c_, 6.6)
            s_.finish(color=RED, fill=(1, 1, 1), width=.8); s_.commit()
            d.text(c_.x, c_.y + 3, str(it["no"]), 8, "hm", RED, "C")
            codes = "／".join("P" + c for c in it["codes"][:2])
            tag = f"{ad0}→{y_}" + ("（尚無當年影像）" if y_ < ad0 else "")
            d.text(x0 + PAD + 20, yy + 7, tag, 9.6, "hm", RED)
            ls = d.wrap(codes + "　" + ts.SHORT[key], 9.6, cw - d.fm.text_length(tag, fontsize=9.6) - 8)
            for j, ln in enumerate(ls):
                d.text(x0 + PAD + 28 + d.fm.text_length(tag, fontsize=9.6), yy + 7 + j * 12, ln, 9.6, "hl")
            yy += 7 + len(ls) * 12 + 7
        yb.append(yy)
    assert max(yb) < Y_END, max(yb)
    d.text(115, 1643, "影像：臺北市政府都市發展局 臺北市歷史圖資展示系統 historygis.udd.gov.taipei（1994–2025 正射影像，含浮水印）；計畫範圍：歷年計畫索引（查詢 2026-10-05）。"
           "影像以 EPSG:3826 輸出對位，早年影像幾何精度較低，僅供時序判讀。民國 115 年公告者尚無 2026 影像，暫以 2025 代之。底圖 © OpenStreetMap contributors / ODbL", 9.5, "hl", MUTED)
    p = vs.OUT / "市民大道_南京西至仁愛_C紅框範圍與公告當年航照_20261014.pdf"
    doc.set_metadata({"title": "南京西路—仁愛路沿線 紅框範圍 × 公告當年航照"}); doc.save(p, garbage=3, deflate=True)
    fitz.open(p)[0].get_pixmap(dpi=72).save(str(p).replace(".pdf", "_預覽.png"))
    print(p, round(p.stat().st_size / 1e6, 1), "MB")


if __name__ == "__main__":
    main()
