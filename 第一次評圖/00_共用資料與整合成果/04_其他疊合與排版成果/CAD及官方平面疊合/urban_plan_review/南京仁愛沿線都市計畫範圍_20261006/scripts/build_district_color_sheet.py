# -*- coding: utf-8 -*-
"""A 圖著色版（2026-10-14）：仿 Architecture Workroom Brussels《Thinkers versus Makers》表現法。
- 建物依所屬行政區（通檢細部計畫範圍）著色，紅→藍由西向東；不畫道路線，道路由留白呈現。
- 各區分區界內縮，區與區之間拉開留白。
- 市民大道以黑色粗線表示（同原圖鐵道表現）。
- 都更／發展案例一律以單一深色標示：剪影＋基地＋編號圈；狀態於下方文字說明。
- 版面：上 2/3 為圖，下 1/3 為依分段排列之案件說明。
"""
import sys, json
from pathlib import Path
import fitz
from shapely.geometry import shape, box, Point
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_vision_renewal_sheet as vs
import build_two_sheets as ts

W, H = 2383.937, 1683.78
M = 115
INK = (0.12, 0.12, 0.12); MUTED = (0.42, 0.42, 0.42); RULE = (0.75, 0.75, 0.75)
MARK = (0.10, 0.10, 0.12)   # 案件單一標示色
DC = {"大同": "#A50F15", "萬華": "#DE2D26", "中正": "#FB6A4A", "中山": "#FDAE6B",
      "大安": "#9ECAE1", "松山": "#4292C6", "信義": "#08519C"}
GAP = 16         # 各區內縮（m）→ 區間留白約 32 m
FONT_L, FONT_M = vs.FONT_L, vs.FONT_M


def case_layers(c):
    """回傳 [(layer, geom, dashed)]，layer∈site/landscape/building；與 A 圖幾何相同。"""
    typ = c["geom"][0]; out = []
    if typ == "massing":
        for l, b, g in vs.massing[c["geom"][1]]:
            if l == "locator":
                out.append(("site", g, True))
            else:
                out.append((l, g, b == "boundary_only"))
    elif typ == "schematic":
        site = vs.U[c["geom"][1]]
        parts = sorted(getattr(site, "geoms", [site]), key=lambda q: q.area, reverse=True)
        out.append(("site", site, False))
        if c["id"] == "TWIN":
            west, east = sorted(parts, key=lambda q: q.centroid.x)
            bridge = box(west.bounds[2] - 6, 2771262, east.bounds[0] + 6, 2771300)
            out.append(("landscape", unary_union([west.buffer(-5, join_style=2), east.buffer(-5, join_style=2), bridge]), False))
            for k in ("way/1502280746", "way/1502280687"):
                out.append(("building", vs.osm_bld[k], False))
        else:
            out.append(("building", parts[0].buffer(-8, join_style=2), True))
    elif typ == "osmset":
        u = unary_union([vs.osm_bld[k] for k in c["geom"][1] if k in vs.osm_bld])
        out += [("site", u.buffer(18, join_style=2).buffer(-12, join_style=2), False), ("building", u, False)]
    elif typ == "point":
        out.append(("site", Point(*c["geom"][1]).buffer(32), True))
    else:
        out.append(("site", c["geom"][1], False))
        if typ == "site+bld":
            out.append(("building", vs.osm_bld[c["geom"][2]], False))
    return out


def main():
    bb = json.load(open(vs.EXP / "qa.json"))["bounds"]; VIEW = box(*bb)
    S = (W - 2 * M) / (bb[2] - bb[0])            # pt / m
    SPLIT = H * 2 / 3
    MAP_TOP = 230 + ((SPLIT - 60 - 230) - ((bb[3] - bb[1]) * S + 40)) / 2   # 圖面置中於上 2/3
    MAP_BOT = MAP_TOP + (bb[3] - bb[1]) * S
    SPLIT = H * 2 / 3                             # 圖：文字 = 2/3：1/3
    tf = lambda x, y: fitz.Point(M + (x - bb[0]) * S, MAP_TOP + (bb[3] - y) * S)

    doc = fitz.open(); page = doc.new_page(width=W, height=H)
    page.insert_font(fontname="hl", fontfile=FONT_L); page.insert_font(fontname="hm", fontfile=FONT_M)
    fl, fm = fitz.Font(fontfile=FONT_L), fitz.Font(fontfile=FONT_M)

    def text(x, y, s, size, font="hl", color=INK, align="L"):
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

    def draw(g, stroke, fill, fop, width, dashes=None):
        if g is None or g.is_empty:
            return
        sh = page.new_shape()
        for p in getattr(g, "geoms", [g]):
            if p.geom_type != "Polygon" or p.is_empty:
                continue
            for r in [p.exterior] + list(p.interiors):
                sh.draw_polyline([tf(*c[:2]) for c in r.coords])
        sh.finish(color=stroke, fill=fill, fill_opacity=fop, width=width, dashes=dashes, closePath=True, even_odd=True)
        sh.commit()

    s_ = page.new_shape(); s_.draw_rect(fitz.Rect(28.35, 28.35, W - 28.35, H - 28.35)); s_.finish(color=INK, width=.7); s_.commit()

    # ---------- 1. 分區著色建物（區界內縮拉開） ----------
    bld = shape(json.load(open(vs.EXP / "building_outlines_TWD97.geojson"))["features"][0]["geometry"])
    taken = None; zones = {}
    for nm, k in vs.DIST:
        z = vs.U[k].intersection(VIEW)
        if taken is not None:
            z = z.difference(taken)
        taken = z if taken is None else taken.union(z)
        zones[nm] = z
    for nm, z in zones.items():
        if z.is_empty:
            continue
        zb = bld.intersection(z.buffer(-GAP, join_style=2))
        draw(zb, None, vs.hex2rgb(DC[nm]), 1.0, 0)

    # ---------- 2. 市民大道（黑線） ----------
    civ = vs.civ.intersection(VIEW)
    sh = page.new_shape()
    for l in getattr(civ, "geoms", [civ]):
        if l.geom_type == "LineString" and not l.is_empty:
            sh.draw_polyline([tf(*c) for c in l.coords])
    sh.finish(color=(0, 0, 0), width=1.3, lineCap=1, lineJoin=1); sh.commit()

    # ---------- 3. 案例（單一深色） ----------
    CS = ts.cases(); anchor = {}
    for c in CS:
        L = case_layers(c)
        if c.get("mask"):
            for l, g, _ in L:
                if l == "site":
                    draw(g, None, (1, 1, 1), 1.0, 0)
        for l, g, dashed in L:
            if l == "site":
                draw(g, MARK, MARK, 0.10, 1.1 if dashed else 0.8, "[3 1.6] 0" if dashed else None)
        for lname, op in (("landscape", 0.35), ("building", 0.88)):
            for l, g, dashed in L:
                if l == lname:
                    draw(g, MARK, MARK, op, 0.5, "[2 1.2] 0" if dashed else None)
        u = unary_union([g for _, g, _ in L]); anchor[c["id"]] = u
        c["seg"] = ts.seg_index(u.centroid.x)
    order = sorted(CS, key=lambda c: anchor[c["id"]].centroid.x)
    for i, c in enumerate(order, 1):
        c["no"] = i
    placed = []
    for c in order:
        u = anchor[c["id"]]; ce = u.centroid; ns = vs.north(ce)
        a = tf(ce.x, u.bounds[3] if ns else u.bounds[1])
        for k in range(14):
            dy = (-24 - 22 * k) if ns else (24 + 22 * k)
            r = fitz.Rect(a.x - 11, a.y + dy - 11, a.x + 11, a.y + dy + 11)
            if not any(r.intersects(q) for q in placed):
                break
        placed.append(r); bc = fitz.Point(a.x, a.y + dy)
        sh = page.new_shape(); sh.draw_line(a, fitz.Point(bc.x, bc.y + (10 if ns else -10)))
        sh.finish(color=MARK, width=0.7); sh.draw_circle(a, 1.6); sh.finish(color=None, fill=MARK); sh.commit()
        closed = c["status"] == "closed"
        sh = page.new_shape(); sh.draw_circle(bc, 10)
        sh.finish(color=MARK, fill=(1, 1, 1) if closed else MARK, width=1.0, dashes="[2 1.5] 0" if closed else None); sh.commit()
        text(bc.x, bc.y + 4, str(c["no"]), 11, "hm", MARK if closed else (1, 1, 1), "C")

    # ---------- 4. 區名、分段 ----------
    for nm, z in zones.items():
        if z.is_empty or z.area < 2e4:
            continue
        p = z.buffer(-GAP).representative_point() if nm != "萬華" else z.centroid
        pt = tf(p.x, p.y); w = fm.text_length(nm + "區", fontsize=14)
        sh = page.new_shape(); sh.draw_rect(fitz.Rect(pt.x - 5, pt.y - 15, pt.x + w + 5, pt.y + 5)); sh.finish(color=None, fill=(1, 1, 1), fill_opacity=.92); sh.commit()
        text(pt.x, pt.y, nm + "區", 14, "hm", vs.hex2rgb(DC[nm]))
    SEGX = [(tf(e0, 0).x, tf(e1, 0).x) for e0, e1, *_ in ts.SEG]
    for i, (_, _, nm, rng, _) in enumerate(ts.SEG):
        x0, x1 = SEGX[i]
        sh = page.new_shape(); sh.draw_line(fitz.Point(x0 + 3, MAP_BOT + 16), fitz.Point(x1 - 3, MAP_BOT + 16)); sh.finish(color=INK, width=1.2); sh.commit()
        text((x0 + x1) / 2, MAP_BOT + 11, nm, 11, "hm", INK, "C")
        text((x0 + x1) / 2, MAP_BOT + 30, rng.split("｜")[0], 9, "hl", MUTED, "C")
        if i:
            sh = page.new_shape(); sh.draw_line(fitz.Point(x0, MAP_BOT + 6), fitz.Point(x0, H - 70))
            sh.finish(color=INK, width=0.5, dashes="[4 3] 0", stroke_opacity=.5); sh.commit()

    # ---------- 5. 標題與圖例 ----------
    text(M, 118, "南京西路—仁愛路沿線｜計畫範圍與都市發展、都更案例", 30, "hm")
    text(M, 146, "建物依所屬行政區（通盤檢討細部計畫範圍）著色，紅→藍由西向東；區界內縮拉開、不繪道路，留白即街道。黑線＝市民大道。"
         "都更與發展案例以單一深色剪影、基地範圍及編號標示，編號由西向東，案件狀態見下方說明。", 11.5, "hl", MUTED)
    x, y = M, 186
    text(x, y, "計畫範圍", 11, "hm", MUTED); x += 64
    for nm, k in vs.DIST:
        sh = page.new_shape(); sh.draw_rect(fitz.Rect(x, y - 10, x + 20, y + 3)); sh.finish(color=None, fill=vs.hex2rgb(DC[nm])); sh.commit()
        x += 27 + text(x + 27, y, f"{nm}區 P{k}", 11) + 16
    x += 14
    sh = page.new_shape(); sh.draw_line(fitz.Point(x, y - 4), fitz.Point(x + 24, y - 4)); sh.finish(color=(0, 0, 0), width=1.3); sh.commit()
    x += 32 + text(x + 32, y, "市民大道", 11) + 26
    text(x, y, "案例", 11, "hm", MUTED); x += 40
    for op, dashed, lab in [(0.88, False, "建物剪影"), (0.35, False, "敷地／裙樓"), (0.10, False, "基地範圍"), (0.10, True, "基地概括／推估（虛線）")]:
        sh = page.new_shape(); sh.draw_rect(fitz.Rect(x, y - 10, x + 20, y + 3))
        sh.finish(color=MARK, fill=MARK, fill_opacity=op, width=1 if dashed else .5, dashes="[3 2] 0" if dashed else None); sh.commit()
        x += 27 + text(x + 27, y, lab, 11) + 14
    sh = page.new_shape(); sh.draw_circle(fitz.Point(x + 9, y - 4), 8); sh.finish(color=MARK, fill=MARK); sh.commit()
    text(x + 9, y, "1", 9, "hm", (1, 1, 1), "C"); x += 24 + text(x + 24, y, "案件編號", 11) + 14
    sh = page.new_shape(); sh.draw_circle(fitz.Point(x + 9, y - 4), 8); sh.finish(color=MARK, fill=(1, 1, 1), width=1, dashes="[2 1.5] 0"); sh.commit()
    text(x + 24, y, "結案未續行", 11)
    sx, sy = W - M - 4 * 500 * S / 2, 214    # 比例尺 0–1000 m
    for k in range(4):
        sh = page.new_shape(); sh.draw_rect(fitz.Rect(sx + k * 250 * S, sy, sx + (k + 1) * 250 * S, sy + 6))
        sh.finish(color=INK, fill=INK if k % 2 == 0 else (1, 1, 1), width=.6); sh.commit()
    for k, t in [(0, "0"), (2, "500"), (4, "1000 m")]:
        text(sx + k * 250 * S, sy + 18, t, 8.5, "hl", MUTED, "C" if k else "L")
    text(sx - 12, sy + 7, f"1:{round(1 / (S / 72 * 25.4 / 1000)):,}", 9, "hm", MUTED, "R")
    sh = page.new_shape(); sh.draw_line(fitz.Point(W - M - 4, 96), fitz.Point(W - M - 4, 140)); sh.finish(color=INK, width=1); sh.commit()
    sh = page.new_shape(); sh.draw_polyline([fitz.Point(W - M - 9, 106), fitz.Point(W - M - 4, 94), fitz.Point(W - M + 1, 106)]); sh.finish(color=INK, fill=INK, closePath=True); sh.commit()
    text(W - M - 4, 154, "格網北", 8.5, "hl", MUTED, "C")
    assert MAP_BOT + 40 < SPLIT, (MAP_BOT, SPLIT)

    # ---------- 6. 下方 1/3：案件狀態說明（依分段欄） ----------
    ty = SPLIT + 10
    w_ = fm.text_length("案件狀態說明｜依所在分段排列", fontsize=16)
    sh = page.new_shape(); sh.draw_rect(fitz.Rect(M - 4, ty - 18, M + w_ + 8, ty + 6)); sh.finish(color=None, fill=(1, 1, 1)); sh.commit()
    text(M, ty, "案件狀態說明｜依所在分段排列", 16, "hm")
    text(W - M, ty, "推動階段：規劃中 → 前期／招商 → 審議中 → 審議通過 → 施工中／展延 → 已完成；另列 結案未續行。★＝推定待核", 10, "hl", MUTED, "R")
    sh = page.new_shape(); sh.draw_line(fitz.Point(M, ty + 8), fitz.Point(W - M, ty + 8)); sh.finish(color=INK, width=1.2); sh.commit()
    PAD = 8; yb = []
    for i in range(len(ts.SEG)):
        x0, x1 = SEGX[i]; cw = x1 - x0 - 2 * PAD; yy = ty + 26
        for c in [c for c in order if c["seg"] == i]:
            closed = c["status"] == "closed"
            cc = fitz.Point(x0 + PAD + 8, yy - 4)
            sh = page.new_shape(); sh.draw_circle(cc, 8)
            sh.finish(color=MARK, fill=(1, 1, 1) if closed else MARK, width=.9, dashes="[2 1.5] 0" if closed else None); sh.commit()
            text(cc.x, cc.y + 3.3, str(c["no"]), 9, "hm", MARK if closed else (1, 1, 1), "C")
            head = c["short"] + (" ★" if c.get("verify") else "")
            hw = text(x0 + PAD + 22, yy, head, 10.5, "hm")
            text(x0 + PAD + 30 + hw, yy, "［" + vs.STATUS[c["status"]][0] + "］", 10, "hm", MUTED)
            ls = wrap(c["who"] + "｜" + c["desc"], 9.2, cw)
            for j, ln in enumerate(ls):
                text(x0 + PAD, yy + 15 + j * 11.8, ln, 9.2)
            yy += 15 + len(ls) * 11.8 + 10
        yb.append(yy)
    assert max(yb) < H - 60, max(yb)
    text(M, H - 42, "資料：臺北市都發局歷年計畫索引與各區通盤檢討（查詢 2026-10-05）；案件階段沿用《簡要標記 v2》《公共都更與公共建設編號圖》並補展覽資料（2026-10-04）；建物：統一清理 v2 擴幅建物輪廓；"
         "表現法參考 Architecture Workroom Brussels, Thinkers versus Makers (2016)。底圖 © OpenStreetMap contributors / ODbL", 9, "hl", MUTED)

    p = vs.OUT / "市民大道_南京西至仁愛_A計畫範圍與都更案例_著色版_20261014.pdf"
    doc.set_metadata({"title": "南京西路—仁愛路沿線 計畫範圍與都市發展、都更案例（著色版）"}); doc.save(p, garbage=3, deflate=True)
    fitz.open(p)[0].get_pixmap(dpi=72).save(str(p).replace(".pdf", "_預覽.png"))
    print(p, round(p.stat().st_size / 1e6, 1), "MB", "map bottom", round(MAP_BOT), "split", round(SPLIT), "text bottom", round(max(yb)))


if __name__ == "__main__":
    main()
