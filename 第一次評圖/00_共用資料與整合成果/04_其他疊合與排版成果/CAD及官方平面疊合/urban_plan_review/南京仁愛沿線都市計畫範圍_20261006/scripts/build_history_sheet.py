# -*- coding: utf-8 -*-
"""紅框範圍 × 公告當年航照（2026-10-14）
每個紅框（24 個都市計畫個案）套入「公告當年」之臺北市歷史正射影像；當年無影像者，取公告後最近一年。
影像：臺北市歷史圖資 historygis.udd.gov.taipei（Aerial／Image 資料夾之 Ortho 服務），以 export 端點輸出 EPSG:3826 影像。
"""
import sys, json, io, urllib.request, urllib.parse
from pathlib import Path
import fitz
from PIL import Image
from shapely.geometry import box, LineString
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_vision_renewal_sheet as vs
import build_two_sheets as ts

OUT = vs.OUT
CACHE = OUT / "history_cache"; CACHE.mkdir(exist_ok=True)
GIS = "https://www.historygis.udd.gov.taipei/arcgis/rest/services/"
YEARS = {1957: "Aerial/Ortho_1957", 1973: "Aerial/Ortho_1973", 1979: "Aerial/Ortho_1979_2", 1986: "Image/Ortho_1986_5K",
         1987: "Image/Ortho_1987_5K", 1990: "Image/Ortho_1990_5K", 1991: "Aerial/Ortho_1991", 1994: "Aerial/Ortho_1994",
         1997: "Image/Ortho_1997_5K", 2000: "Image/Ortho_2000_5K", 2002: "Aerial/Ortho_2002", 2005: "Aerial/Ortho_2005",
         2007: "Aerial/Ortho_2007", 2009: "Aerial/Ortho_2009", 2010: "Aerial/Ortho_2010", 2011: "Aerial/Ortho_2011",
         2012: "Aerial/Ortho_2012", 2013: "Aerial/Ortho_2013", 2015: "Aerial/Ortho_2015", 2017: "Aerial/Ortho_2017",
         2018: "Aerial/Ortho_2018", 2019: "Aerial/Ortho_2019", 2020: "Aerial/Ortho_2020", 2021: "Aerial/Ortho_2021",
         2022: "Aerial/Ortho_2022", 2023: "Aerial/Ortho_2023", 2024: "Aerial/Ortho_2024", 2025: "Aerial/Ortho_2025"}
RED = (.85, .05, .05)


def pick_year(ad):
    return min([y for y in YEARS if y >= ad] or [max(YEARS)])


def fetch(year, bbox, w, h):
    f = CACHE / f"{year}_{'_'.join(str(int(v)) for v in bbox)}_{w}x{h}.png"
    if not f.exists():
        q = dict(bbox=",".join(str(v) for v in bbox), bboxSR=3826, imageSR=3826, size=f"{w},{h}", format="png", f="image")
        data = urllib.request.urlopen(GIS + YEARS[year] + "/MapServer/export?" + urllib.parse.urlencode(q), timeout=180).read()
        Image.open(io.BytesIO(data)).convert("RGB").save(f)
    return f


def main():
    view = box(*json.load(open(vs.EXP / "qa.json"))["bounds"])
    civ = vs.civ
    W, H = 2383.937, 1683.78
    doc = fitz.open(); page = doc.new_page(width=W, height=H)
    page.insert_font(fontname="hl", fontfile=vs.FONT_L); page.insert_font(fontname="hm", fontfile=vs.FONT_M)
    fl, fm = fitz.Font(fontfile=vs.FONT_L), fitz.Font(fontfile=vs.FONT_M)

    def text(x, y, s, size, font="hl", color=vs.INK, align="L"):
        w = (fm if font == "hm" else fl).text_length(s, fontsize=size)
        x = x - w if align == "R" else x - w / 2 if align == "C" else x
        page.insert_text((x, y), s, fontsize=size, fontname=font, color=color); return w

    def wrap(s, size, width):
        lines, cur = [], ""
        for ch in s:
            if fl.text_length(cur + ch, fontsize=size) > width:
                lines.append(cur); cur = ch
            else:
                cur += ch
        return lines + ([cur] if cur else [])

    s_ = page.new_shape(); s_.draw_rect(fitz.Rect(28.35, 28.35, W - 28.35, H - 28.35)); s_.finish(color=vs.INK, width=.7); s_.commit()
    text(115, 118, "南京西路—仁愛路沿線｜紅框範圍 × 公告當年航照", 30, "hm")
    text(115, 146, "24 個都市計畫個案（編號同《紅框範圍與更新意圖》）各自套入公告當年之臺北市歷史正射影像；當年無影像者取公告後最近一年（民國 115 年公告者尚無 2026 影像，暫以 2025 代之）。"
         "合併案（主要＋細部或先後修訂）以最早公告年為準。紅線＝計畫範圍（裁至原十幅沿線範圍）；青線＝市民大道中心線。", 11.5, "hl", vs.MUTED)

    COLS, ROWS = 6, 4
    X0, Y0, X1, Y1 = 115, 180, W - 115, H - 70
    cw, ch = (X1 - X0) / COLS, (Y1 - Y0) / ROWS
    CAP = 64
    rows = []
    for it in vs.items:
        ad0 = min(int(vs.PER[c]) for c in it["codes"]) + 1911
        ad1 = max(int(vs.PER[c]) for c in it["codes"]) + 1911
        yr = pick_year(ad0)
        key = next(c for c in it["codes"] if c in ts.SHORT)
        g = it["geom"].intersection(vs.mask if it["geom"].area > 2e6 else view)
        if g.is_empty:
            g = it["geom"].intersection(view)
        k = (it["no"] - 1); px, py = X0 + (k % COLS) * cw, Y0 + (k // COLS) * ch
        fr = fitz.Rect(px + 6, py + 6, px + cw - 6, py + ch - CAP)
        # 影像範圍：計畫範圍外擴 25%，並配合框的長寬比
        minx, miny, maxx, maxy = g.bounds; gw, gh = maxx - minx, maxy - miny
        pad = max(gw, gh) * 0.12 + 40; minx -= pad; maxx += pad; miny -= pad; maxy += pad
        ar = fr.width / fr.height; gw, gh = maxx - minx, maxy - miny
        if gw / gh > ar:
            d_ = (gw / ar - gh) / 2; miny -= d_; maxy += d_
        else:
            d_ = (gh * ar - gw) / 2; minx -= d_; maxx += d_
        bbox = (round(minx), round(miny), round(maxx), round(maxy))
        pw = min(1400, max(500, int((maxx - minx) / 0.6))); ph = int(pw / ar)
        img = fetch(yr, bbox, pw, ph)
        page.insert_image(fr, filename=str(img))

        def P(x, y):
            return fitz.Point(fr.x0 + (x - bbox[0]) / (bbox[2] - bbox[0]) * fr.width, fr.y1 - (y - bbox[1]) / (bbox[3] - bbox[1]) * fr.height)
        clipbox = box(*bbox)
        cl = civ.intersection(clipbox)
        s_ = page.new_shape()
        for l in getattr(cl, "geoms", [cl]):
            if l.geom_type == "LineString" and not l.is_empty:
                s_.draw_polyline([P(*c) for c in l.coords])
        s_.finish(color=(0, .85, .95), width=0.9, stroke_opacity=.8); s_.commit()
        s_ = page.new_shape()
        for poly in getattr(g, "geoms", [g]):
            if poly.geom_type != "Polygon":
                continue
            for r in [poly.exterior] + list(poly.interiors):
                s_.draw_polyline([P(*c) for c in r.coords])
        s_.finish(color=RED, width=1.6, closePath=True); s_.commit()
        s_ = page.new_shape(); s_.draw_rect(fr); s_.finish(color=vs.INK, width=.5); s_.commit()
        # 年份標籤
        lab = f"{yr}"
        w = fm.text_length(lab, fontsize=13)
        s_ = page.new_shape(); s_.draw_rect(fitz.Rect(fr.x1 - w - 14, fr.y0, fr.x1, fr.y0 + 20)); s_.finish(color=None, fill=(1, 1, 1), fill_opacity=.9); s_.commit()
        text(fr.x1 - 7, fr.y0 + 15, lab, 13, "hm", vs.INK, "R")
        # 比例尺 100 m
        m100 = 100 / (bbox[2] - bbox[0]) * fr.width
        s_ = page.new_shape(); s_.draw_rect(fitz.Rect(fr.x0 + 8, fr.y1 - 12, fr.x0 + 8 + m100, fr.y1 - 8)); s_.finish(color=(1, 1, 1), fill=(1, 1, 1)); s_.commit()
        text(fr.x0 + 12 + m100, fr.y1 - 7, "100 m", 8, "hm", (1, 1, 1))
        # 圖說
        c = fitz.Point(fr.x0 + 8, fr.y1 + 15); s_ = page.new_shape(); s_.draw_circle(c, 7.5); s_.finish(color=RED, fill=(1, 1, 1), width=.9); s_.commit()
        text(c.x, c.y + 3.4, str(it["no"]), 9, "hm", RED, "C")
        codes = "／".join("P" + x for x in it["codes"][:2])
        yrs = f"民國 {ad0 - 1911}" + (f"／{ad1 - 1911}" if ad1 != ad0 else "") + " 公告"
        seg = ts.SEG[ts.seg_index(it["rp"].x)][2].split(" ")[0]
        text(fr.x0 + 21, fr.y1 + 19, f"{codes}｜{yrs}｜影像 {yr}" + ("" if yr == ad0 else "（最近後一年）" if yr > ad0 else f"（{ad0} 尚無影像，取前一年）") + f"｜{seg}", 9.2, "hm")
        for j, ln in enumerate(wrap(ts.SHORT[key], 9.2, fr.width - 4)[:2]):
            text(fr.x0 + 2, fr.y1 + 34 + j * 12, ln, 9.2)
        rows.append((it["no"], codes, ad0, ad1, yr, YEARS[yr]))
    text(115, H - 42, "影像：臺北市政府都市發展局 臺北市歷史圖資展示系統 historygis.udd.gov.taipei（1957–2025 正射影像，含浮水印）；計畫範圍：歷年計畫索引（查詢 2026-10-05）。"
         "影像與計畫線皆以 EPSG:3826 對位，早年影像之幾何精度較低，僅供時序判讀。", 9.5, "hl", vs.MUTED)
    p = OUT / "市民大道_南京西至仁愛_C紅框範圍與公告當年航照_20261014.pdf"
    doc.set_metadata({"title": "南京西路—仁愛路沿線 紅框範圍 × 公告當年航照"}); doc.save(p, garbage=3, deflate=True)
    fitz.open(p)[0].get_pixmap(dpi=72).save(str(p).replace(".pdf", "_預覽.png"))
    for r in rows:
        print(*r)


if __name__ == "__main__":
    main()
