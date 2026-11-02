# -*- coding: utf-8 -*-
"""簡報「事件 · 痕跡 — 場域」：17 頁向量 PDF＋分層 PDF（供 Illustrator 組成 17 個工作區域的 AI）（2026-10-14）
頁序、圖說依《簡報逐頁文字_v4.txt》與其後指示（內頁無標題、只有圖說與頁碼；諾利圖白底；歷史痕跡用 200 m 方格舊圖反黑；
垂直幹道極淡虛線、圖上下緣小字路名）。每頁 1920 × 1080 pt（＝網頁版 px）。
輸出：簡報/事件痕跡場域_簡報.pdf（合成）、簡報/_ai_layers/{00_底色,01_圖,02_文字}.pdf（各 17 頁）、簡報/_預覽/pNN.jpg
重現：python3 04_slides.py → ./05_make_ai.sh
"""
import sys, io, json, math, importlib.util
from pathlib import Path
from PIL import Image, ImageOps
from shapely.geometry import box, shape, Point, LineString, mapping
from shapely.ops import unary_union
import fitz

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("t3", HERE / "scripts/03_trace_grid.py")
T3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(T3)
T2, T1, NL, vs = T3.T2, T3.T1, T3.NL, T3.vs
import build_history_sheet as hs          # 臺北市歷史正射影像（historygis）

OUT = HERE / "簡報"; (OUT / "_ai_layers").mkdir(parents=True, exist_ok=True); (OUT / "_預覽").mkdir(exist_ok=True)
FIG = OUT / "_圖"; FIG.mkdir(exist_ok=True)
D3 = ROOT / "03_最新產出/03_南京至仁愛_沿線土地使用分析_20261006/data"
D4 = ROOT / "03_最新產出/04_Z1-Z7_第一排街廓詳細平面_20261007/data"

SW, SH = 1920, 1080
BG, INK, MUTED, RED, GRAY = (0.969, 0.965, 0.945), (0.086, 0.086, 0.086), (0.42, 0.42, 0.40), (0.70, 0.15, 0.12), (0.45, 0.45, 0.43)
FL, FM = vs.FONT_L, vs.FONT_M
fl, fm = fitz.Font(fontfile=FL), fitz.Font(fontfile=FM)
LAB = 11            # 圖上路名（pt，置入簡報後約 10 px）
CW, CTOP, CBOT = 1664, 128, 920   # 內容區


def gj(p):
    return json.load(open(p))["features"]


# ── 地圖頁：任意範圍、指定寬度 ─────────────────────────────
class Map:
    def __init__(s, view, width, my=20):
        s.view, b = view, view.bounds
        s.k = width / (b[2] - b[0]); s.my = my
        s.W, s.H = width, (b[3] - b[1]) * s.k + 2 * my
        s.doc = fitz.open(); s.page = s.doc.new_page(width=s.W, height=s.H); s.fonts = set()   # 字型用到才嵌入（未用之字型無法子集化，會整個 ttc 嵌入）
        s.frame = fitz.Rect(0, my, s.W, s.H - my)

    def tf(s, x, y):
        b = s.view.bounds
        return fitz.Point((x - b[0]) * s.k, s.my + (b[3] - y) * s.k)

    def rings(s, g):
        return [[s.tf(*c[:2]) for c in r.coords] for p in getattr(g, "geoms", [g]) if p.geom_type == "Polygon" and not p.is_empty
                for r in [p.exterior] + list(p.interiors)]

    def poly(s, gs, fill=None, stroke=None, width=0.0, dashes=None, fo=1.0):
        sh = s.page.new_shape(); n = 0
        for g in gs:
            for r in s.rings(g):
                sh.draw_polyline(r); n += 1
        if n:
            sh.finish(color=stroke, fill=fill, width=width, closePath=True, even_odd=True, dashes=dashes, fill_opacity=fo); sh.commit()

    def lines(s, gs, color, width, dashes=None, op=1.0):
        sh = s.page.new_shape(); n = 0
        for g in gs:
            for l in getattr(g, "geoms", [g]):
                if l.geom_type == "LineString" and not l.is_empty:
                    sh.draw_polyline([s.tf(*c[:2]) for c in l.coords]); n += 1
        if n:
            sh.finish(color=color, width=width, dashes=dashes, stroke_opacity=op); sh.commit()

    def text(s, x, y, t, size, font="hl", color=INK, align="L", box_=None):
        w = (fm if font == "hm" else fl).text_length(t, fontsize=size)
        x0 = x - w if align == "R" else x - w / 2 if align == "C" else x
        if font not in s.fonts:
            s.page.insert_font(fontname=font, fontfile=FM if font == "hm" else FL); s.fonts.add(font)
        if box_ is not None:
            sh = s.page.new_shape(); sh.draw_rect(fitz.Rect(x0 - 3, y - size, x0 + w + 3, y + size * .3)); sh.finish(color=None, fill=box_); sh.commit()
        s.page.insert_text((x0, y), t, fontsize=size, fontname=font, color=color)

    def nolli(s, priv=(0, 0, 0), pub=(0, 0, 0), hatch=INK):
        V = s.view.buffer(5)
        W_ = NL.WATER.intersection(V); sh = s.page.new_shape(); n = 0; b = s.view.bounds; y = b[1]
        while y < b[3]:
            seg = LineString([(b[0], y), (b[2], y)]).intersection(W_)
            for l in getattr(seg, "geoms", [seg]):
                if l.geom_type == "LineString" and l.length > 0:
                    sh.draw_line(s.tf(*l.coords[0]), s.tf(*l.coords[-1])); n += 1
            y += 9
        if n:
            sh.finish(color=hatch, width=.25); sh.commit()
        if priv is not None:
            s.poly([g.intersection(V) for g in NL.PRIV if g.intersects(V)], fill=priv)
        s.poly([g.intersection(V) for g in NL.PUB if g.intersects(V)], stroke=pub, width=.35)

    def finish(s, labels=True, frame=True, top=True, bottom=True, lab=LAB, dash=(.55, .55, .55), dw=.5, dop=.5, lab_col=MUTED, dpat="[2 2.5] 0"):
        b = s.view.bounds
        for key, g, n_top, n_bot in T1.arterials(s.view):
            if dash is not None:          # dash=None：幹道線透明（不畫），只留路名
                s.lines([g], dash, dw, dpat, dop)
            if labels:
                pts = [c for l in getattr(g, "geoms", [g]) if l.geom_type == "LineString" for c in l.coords]
                if n_top and top:
                    s.text(s.tf(min(pts, key=lambda c: abs(c[1] - b[3]))[0], 0).x, s.frame.y0 - 4, n_top, lab, "hl", lab_col, "C")
                if n_bot and bottom:
                    s.text(s.tf(min(pts, key=lambda c: abs(c[1] - b[1]))[0], 0).x, s.frame.y1 + lab + 2, n_bot, lab, "hl", lab_col, "C")
        if frame:
            sh = s.page.new_shape(); sh.draw_rect(s.frame); sh.finish(color=INK, width=.4); sh.commit()

    def save(s, name):
        p = FIG / f"{name}.pdf"; s.doc.subset_fonts(); s.doc.save(p, garbage=3, deflate=True); return p


VIEW = T2.VIEW
ZONES = [f for f in gj(D3 / "zones_EPSG3826.geojson") if "id" in f["properties"]]
CUTS = [shape(f["geometry"]) for f in gj(D3 / "zones_EPSG3826.geojson") if "cut" in f["properties"]]


def zone_marks(m):
    m.lines(CUTS, (.25, .25, .25), .8, "[5 3] 0")
    for f in ZONES:
        g = shape(f["geometry"]).intersection(VIEW); c = g.centroid
        m.text(m.tf(c.x, 0).x, m.frame.y1 - 10, f["properties"]["id"], 13, "hm", INK, "C", box_=(1, 1, 1))


def key(z, pred):
    return [shape(f["geometry"]) for f in gj(D4 / f"Z{z}_key_buildings_EPSG3826.geojson") if pred(f["properties"])]


# ── 各頁圖 ──────────────────────────────────────────────
def fig_nolli(name, view, width):
    m = Map(view, width); m.nolli(); m.finish(); return m.save(name)


# ── 風格（2026-10-14 使用者提供參考圖，依圖之需求選擇）──────────────
# 痕跡方格（P06–P08）：London site plan 之「深淺不一的影像方格」——方格依街廓遮色片占比分三階（30–45%／45–60%／≥60%），
#   反黑舊圖與白色混合 55%／78%／100%，越貼近大道越深；不用透明度（避免 SMask 於 macOS 預覽不顯示）。
# 痕跡總圖、揭露（P05、P14）：Building classification——建物改暖灰，只以統一色表之紫（古蹟）、酒紅（主角）、淡酒紅（修復中）標出重點。
# 計畫兩輪（P11–P13）：Berlin 等城市圖底之單色實心——底圖建物淡灰，個案範圍以單色實心塊（第一輪深灰、第二輪酒紅）。
# 橋下（P09）：同單色實心，建物淡灰、橋下深灰（＝匝道灰 #666666 之構造語意）。
# 膜（P15、P17）：Barcelona 顆粒紋理——諾利圖不透處以灰黑顆粒紋理填滿（膜的材質），孔內清空。
HER_C, MAG, MAG_LT, BLD_W, BLD_L, STR_C = (0.369, 0.235, 0.6), (0.557, 0.106, 0.243), (0.914, 0.639, 0.741), (0.75, 0.71, 0.66), (0.80, 0.80, 0.80), (0.40, 0.40, 0.40)
TONES = [(.30, .55), (.45, .78), (.60, 1.0)]


def grain(w, h, seed=7):
    """Barcelona 式顆粒紋理（灰黑底＋白色細點、低頻斑駁）"""
    import numpy as np
    from scipy.ndimage import gaussian_filter
    rng = np.random.default_rng(seed)
    low = gaussian_filter(rng.standard_normal((h, w)), 18); low = (low - low.min()) / (low.max() - low.min())
    v = 40 + 50 * low + 35 * rng.standard_normal((h, w))
    v[rng.random((h, w)) < .035] = 215                     # 白色細點
    return Image.fromarray(np.clip(v, 0, 255).astype("uint8"))


def fig_trace(lid):
    M, _ = T2.mask_geom()
    OLD, xs, ys, table = T3.cells(M)
    m = Map(VIEW, CW); m.nolli()
    inv = ImageOps.invert(ImageOps.autocontrast(T1.raster_3826(lid, VIEW.bounds), cutoff=1).convert("L"))
    for i, (lo, a) in enumerate(TONES):
        hi = TONES[i + 1][0] if i + 1 < len(TONES) else 9
        cells = [box(x, y, x + T3.GRID, y + T3.GRID) for x, y, sh, o in table if lo <= sh < hi]
        g = unary_union(cells).intersection(OLD) if cells else None
        if g is None or g.is_empty:
            continue
        im = Image.blend(Image.new("L", inv.size, 255), inv, a)
        jb = io.BytesIO(); im.save(jb, "JPEG", quality=85)
        T1.insert_clipped(m.page, m.frame, jb.getvalue(), m.rings(g))
    m.finish()
    b = VIEW.bounds
    m.lines([LineString([(x, b[1]), (x, b[3])]) for x in xs] + [LineString([(b[0], y), (b[2], y)]) for y in ys], (.5, .5, .5), .6, "[6 4] 0")
    yr, title, *_ = T1.LAYERS[lid]
    m.text(m.frame.x0 + 10, m.frame.y1 - 10, f"{yr}｜{title}", 12, "hm", INK, box_=(1, 1, 1))
    return m.save(f"trace_{yr}")


def fig_aerials():
    """北門—臺北車站同一視窗，四年份 2×2（臺北市歷史正射影像，黑白）"""
    win = box(301250, 2770870, 302810, 2771570)          # 1,560 × 700 m
    fw = (CW - 24) / 2; k = fw / 1560; fh = 700 * k; my = 20
    doc = fitz.open(); page = doc.new_page(width=CW, height=2 * fh + 24 + 2 * my)
    page.insert_font(fontname="hl", fontfile=FL); page.insert_font(fontname="hm", fontfile=FM)
    arts = T1.arterials(win)
    for i, yr in enumerate([1973, 1994, 2005, 2025]):   # 1957 正射影像於此視窗為空白（2026-10-14 取回全白），改 1973
        x0 = (i % 2) * (fw + 24); y0 = my + (i // 2) * (fh + 24)
        r = fitz.Rect(x0, y0, x0 + fw, y0 + fh)
        b = win.bounds
        f = hs.fetch(yr, tuple(int(v) for v in b), 1560, 700)
        im = Image.open(f).convert("L"); jb = io.BytesIO(); im.save(jb, "JPEG", quality=85)
        page.insert_image(r, stream=jb.getvalue())
        tf = lambda x, y: fitz.Point(x0 + (x - b[0]) * k, y0 + (b[3] - y) * k)
        for key_, g, n_top, n_bot in arts:
            sh = page.new_shape()
            for l in getattr(g, "geoms", [g]):
                if l.geom_type == "LineString":
                    sh.draw_polyline([tf(*c) for c in l.coords])
            sh.finish(color=(1, 1, 1), width=.6, dashes="[2 2.5] 0", stroke_opacity=.55); sh.commit()
            pts = [c for l in getattr(g, "geoms", [g]) if l.geom_type == "LineString" for c in l.coords]
            if i < 2 and n_top:
                t = n_top; w = fl.text_length(t, fontsize=LAB); page.insert_text((tf(min(pts, key=lambda c: abs(c[1] - b[3]))[0], 0).x - w / 2, y0 - 5), t, fontsize=LAB, fontname="hl", color=MUTED)
            if i >= 2 and n_bot:
                t = n_bot; w = fl.text_length(t, fontsize=LAB); page.insert_text((tf(min(pts, key=lambda c: abs(c[1] - b[1]))[0], 0).x - w / 2, y0 + fh + LAB + 3), t, fontsize=LAB, fontname="hl", color=MUTED)
        sh = page.new_shape(); sh.draw_rect(fitz.Rect(x0 + 8, y0 + 8, x0 + 70, y0 + 32)); sh.finish(color=None, fill=(1, 1, 1)); sh.commit()
        page.insert_text((x0 + 14, y0 + 26), str(yr), fontsize=16, fontname="hm", color=INK)
        sh = page.new_shape(); sh.draw_rect(r); sh.finish(color=INK, width=.4); sh.commit()
    p = FIG / "aerials.pdf"; doc.subset_fonts(); doc.save(p, garbage=3, deflate=True); return p


def heritage():
    cs = json.load(open(D3 / "文資登錄_圖幅內.json"))["cases"]
    U = unary_union([shape(f["geometry"]) for f in ZONES]).buffer(60)
    return [(Point(c["E"], c["N"]), c, U.contains(Point(c["E"], c["N"]))) for c in cs if VIEW.contains(Point(c["E"], c["N"]))]


def dots(m, pts, r, fill, stroke=None):
    sh = m.page.new_shape()
    for p in pts:
        sh.draw_circle(m.tf(p.x, p.y), r)
    sh.finish(color=stroke, fill=fill, width=.5); sh.commit()


def fig_heritage():
    m = Map(VIEW, CW); m.nolli(priv=BLD_W, pub=BLD_W); zone_marks(m)
    H = heritage()
    dots(m, [p for p, c, inn in H if not inn], 2.6, (.62, .58, .70))
    dots(m, [p for p, c, inn in H if inn], 4.6, HER_C, (1, 1, 1))
    m.finish(); print("文資：範圍內", sum(1 for *_, i in H if i), "／圖幅", len(H)); return m.save("heritage")


def fig_underbridge():
    m = Map(VIEW, CW); m.nolli(priv=BLD_L, pub=BLD_L)
    ub = [shape(f["geometry"]) for f in gj(D3 / "underbridge_EPSG3826.geojson")]
    m.poly([g.intersection(VIEW) for g in ub], fill=STR_C)
    zone_marks(m); m.finish(); return m.save("underbridge")


ROUND1 = [("1994", "臺北車站特專區", {"082022", "082023"}), ("2002", "敦化特專區", {"091017"}), ("2003", "華山整體計畫", {"092029", "092034"}),
          ("2003", "松菸特專區", {"092031", "092044"}), ("2005", "懷生段", {"093013", "098027"}), ("2009", "市民大道兩側", {"097017"}),
          ("2015", "京華城", {"103018", "107003"})]
ROUND2 = [("2017", "北門廣場", {"105006"}), ("2019", "E1／E2", {"108001", "107017"}), ("2022", "行二行三 U17", {"111010"})]
SITES2 = [("2020", "鐵道部園區", lambda: key(1, lambda p: (p.get("name") or "").startswith("鐵道部園區"))),
          ("2025", "心中山線形公園", lambda: key(2, lambda p: "心中山" in (p.get("name") or "")))]


def case_geoms(codes):
    its = [it for it in vs.items if set(it["codes"]) & codes]
    return unary_union([it["geom"] for it in its]).intersection(VIEW), (its[0]["rp"] if its else None)


def draw_round(m, R, sites, col, fo):
    labs = []
    for yr, nm, codes in R:
        g, rp = case_geoms(codes)
        m.poly([g], fill=col, stroke=col, width=1.0, fo=fo); labs.append((rp, f"{yr} {nm}"))
    for yr, nm, fn in sites:
        g = unary_union(fn()).intersection(VIEW)
        m.poly([g], fill=col, stroke=col, width=1.0, fo=fo); labs.append((g.representative_point(), f"{yr} {nm}"))
    return labs


def label_all(m, labs, col):
    for p, t in sorted(labs, key=lambda a: a[0].x):
        q = m.tf(p.x, p.y); m.text(q.x, q.y - 8, t, 12, "hm", col, "C", box_=(1, 1, 1))


def arrow(m, x0, x1, y, col):
    a, b = m.tf(x0, 0).x, m.tf(x1, 0).x
    sh = m.page.new_shape(); sh.draw_line(fitz.Point(a, y), fitz.Point(b, y)); sh.finish(color=col, width=2.2); sh.commit()
    sh = m.page.new_shape(); sh.draw_polyline([fitz.Point(b - 14, y - 7), fitz.Point(b, y), fitz.Point(b - 14, y + 7)]); sh.finish(color=col, fill=col, closePath=True); sh.commit()


def xs_of(R, sites):
    xs = [case_geoms(c)[0].centroid.x for *_, c in R] + [unary_union(fn()).centroid.x for *_, fn in sites]
    return min(xs), max(xs)


C1, C2 = (0.25, 0.25, 0.24), MAG


def fig_rounds(which):
    m = Map(VIEW, CW, my=40); m.nolli(priv=BLD_L, pub=BLD_L); zone_marks(m)
    labs = []
    if which in (1, 3):
        labs += [(p, t, C1) for p, t in draw_round(m, ROUND1, [], C1, 1.0)]
    if which in (2, 3):
        labs += [(p, t, C2) for p, t in draw_round(m, ROUND2, SITES2, C2, 1.0)]
    m.finish()
    if which == 1:
        a, b = xs_of(ROUND1, []); arrow(m, a, b, m.H - 12, C1)
    if which == 2:
        a, b = xs_of(ROUND2, SITES2); arrow(m, a, b, m.H - 12, C2)
    if which == 3:
        a, b = xs_of(ROUND1, []); arrow(m, a, b, m.H - 24, C1)
        a, b = xs_of(ROUND2, SITES2); arrow(m, a, b, m.H - 8, C2)
    if which != 3:
        for p, t, c in labs:
            q = m.tf(p.x, p.y); m.text(q.x, q.y - 8, t, 12, "hm", c, "C", box_=(1, 1, 1))
    return m.save(f"round{which}")


OPENED = [("北門廣場", lambda: [case_geoms({"105006"})[0]]), ("鐵道部園區", SITES2[0][2]),
          ("華山1914", lambda: key(4, lambda p: "華山1914" in (p.get("name") or ""))), ("松山文創園區", lambda: key(8, lambda p: p.get("tier") == "A" and "松山文創" in (p.get("name") or "")))]
REPAIR = [("國家鐵道博物館", lambda: key(8, lambda p: p.get("tier") == "A" and ("鐵道博物館" in (p.get("name") or "") or "縫紉" in (p.get("name") or ""))))]
PLANNED = [("U01 E1／E2", lambda: key(1, lambda p: (p.get("name") or "").startswith("U01"))), ("U17", lambda: key(3, lambda p: p.get("tier") == "A")),
           ("U02／U03", lambda: key(6, lambda p: p.get("tier") == "A" and (p.get("name") or "").startswith("U0")))]


def fig_reveal():
    m = Map(VIEW, CW); m.nolli(priv=BLD_W, pub=BLD_W); zone_marks(m)
    H = heritage(); dots(m, [p for p, c, inn in H if inn], 3.2, HER_C)
    labs = []
    for grp, style in ((OPENED, dict(fill=MAG, stroke=MAG, width=1.0)), (REPAIR, dict(fill=MAG_LT, stroke=MAG, width=1.0)),
                       (PLANNED, dict(fill=None, stroke=MAG, width=1.8, dashes="[4 3] 0"))):
        for nm, fn in grp:
            g = unary_union(fn()).intersection(VIEW)
            if g.is_empty:
                print("找不到", nm); continue
            m.poly([g], **style); labs.append((g.representative_point(), nm))
    m.finish()
    for p, t in labs:
        q = m.tf(p.x, p.y); m.text(q.x, q.y - 9, t, 12, "hm", MAG, "C", box_=(1, 1, 1))
    return m.save("reveal")


def membrane_map(name, holes_=None):
    """膜：諾利圖不透處以顆粒紋理填滿；holes_＝[(中心, 半徑 m, 外框色)]，孔內清空"""
    m = Map(VIEW, CW); m.nolli(priv=None, pub=(.35, .35, .35))
    V = VIEW.buffer(5)
    priv = unary_union([g.intersection(V) for g in NL.PRIV if g.intersects(V)])
    if holes_:
        priv = priv.difference(unary_union([c.buffer(r, 64) for c, r, _ in holes_]))
    tex = grain(int(m.frame.width * 2), int(m.frame.height * 2))
    jb = io.BytesIO(); tex.save(jb, "JPEG", quality=88)
    T1.insert_clipped(m.page, m.frame, jb.getvalue(), m.rings(priv))
    for c, r, col in holes_ or []:
        sh = m.page.new_shape(); sh.draw_circle(m.tf(c.x, c.y), r * m.k); sh.finish(color=col, width=1.4); sh.commit()
    if holes_:
        zone_marks(m)
    m.finish(); return m.save(name)


# 膜與孔
EXCL = {("Z3", 1686), ("Z4", 2158), ("Z7", 5185)}     # 2026-10-14 交工處核對：未橫越大道之行穿線，不計
AXIS_END_S = 6338                                      # 至基隆路中心線（Z8 612 m 無穿越段終點）


def crossings():
    out = []
    for z in range(1, 9):
        for f in gj(D4 / f"Z{z}_ns_factors_EPSG3826.geojson"):
            p = f["properties"]
            if p.get("type") == "crossing" and (f"Z{z}", round(p["s"])) not in EXCL:
                out.append((p["s"], shape(f["geometry"]), f"Z{z}"))
    return sorted(out, key=lambda t: t[0])


def holes():
    cr = crossings()
    east = Point(307105, vs.civ_y(307105))
    seq = cr + [(AXIS_END_S, east, "Z8")]
    gaps = [(b[0] - a[0], a, b) for a, b in zip(seq, seq[1:])]
    small = {}
    for L, a, b in gaps:
        mid = Point((a[1].x + b[1].x) / 2, vs.civ_y((a[1].x + b[1].x) / 2))
        z = next((f["properties"]["id"] for f in ZONES if shape(f["geometry"]).contains(mid)), b[2])
        if L >= 300 and (z not in small or L > small[z][0]):
            small[z] = (L, mid)
    big = {"Z1": key(1, lambda p: p.get("group") == "北門古蹟群"), "Z2": key(2, lambda p: p.get("tier") == "T"),
           "Z3": key(3, lambda p: p.get("tier") == "A"), "Z4": key(4, lambda p: p.get("tier") == "A"),
           "Z5": key(5, lambda p: p.get("group") in ("古蹟", "大型商場／市場")), "Z6": key(6, lambda p: p.get("tier") == "A"),
           "Z7": key(7, lambda p: p.get("tier") == "N"), "Z8": key(8, lambda p: p.get("tier") == "A")}
    big = {z: unary_union(g).centroid for z, g in big.items()}
    return big, small


def fig_membrane():
    big, small = holes()
    RB, RS = 170, 60
    hs_ = [(c, RB, INK) for c in big.values()] + [(c, RS, MAG) for L, c in small.values()]
    print("大孔", {z: (round(c.x), round(c.y)) for z, c in big.items()}); print("小孔", {z: (round(L), round(c.x)) for z, (L, c) in small.items()})
    return membrane_map("membrane", hs_), len(big), len(small), small


def fig_diagram():
    doc = fitz.open(); page = doc.new_page(width=1400, height=600)
    jb = io.BytesIO(); grain(1400, 600).save(jb, "JPEG", quality=88); page.insert_image(page.rect, stream=jb.getvalue())   # 膜＝顆粒紋理
    sh = page.new_shape(); sh.draw_circle(fitz.Point(450, 300), 210); sh.finish(color=None, fill=BG); sh.commit()
    sh = page.new_shape(); sh.draw_circle(fitz.Point(1050, 300), 70); sh.finish(color=None, fill=BG); sh.commit()
    p = FIG / "diagram.pdf"; doc.save(p); return p


def clip_src(path, rect, name):
    src = fitz.open(path); doc = fitz.open(); pg = doc.new_page(width=rect.width, height=rect.height)
    pix = src[0].get_pixmap(dpi=200, clip=rect)
    im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples); jb = io.BytesIO(); im.save(jb, "JPEG", quality=88)
    pg.insert_image(pg.rect, stream=jb.getvalue())   # 原圖含大量影像，點陣化以控制檔案大小
    p = FIG / f"{name}.pdf"; doc.save(p, garbage=3, deflate=True); return p


# ── v4 使用者修改（2026-10-14）新增之圖 ─────────────────────────
ORANGE = (0.875, 0.569, 0.204)        # 統一色表：橘＝通行元素（#DF9134）


def fig_access():
    """P03：市民高架全長｜諾利圖淺灰＋市民大道分隔島（黑）＋可通過之路口（橘）；不計 150 m 繞行，只顯示路口可達性"""
    m = Map(VIEW, CW); m.nolli(priv=BLD_L, pub=BLD_L)
    isl, xm = [], []
    for z in range(1, 9):
        isl += [shape(f["geometry"]) for f in gj(D4 / f"Z{z}_road_islands_EPSG3826.geojson") if f["properties"].get("decision", "keep") == "keep"]
        xm += [shape(f["geometry"]) for f in gj(D4 / f"Z{z}_cross_marks_EPSG3826.geojson")]
    m.poly([g.intersection(VIEW) for g in isl], fill=INK)
    m.poly([g.intersection(VIEW) for g in xm], fill=ORANGE)
    zone_marks(m); m.finish()
    print("分隔島", len(isl), "可通過之路口", len(xm))
    return m.save("p03_access"), len(xm)


PERIODS = [("map", "JM20K_1904", "1904｜水圳"), ("map", "JM20K_1921", "1921｜埤塘"), ("map", "AMCityPlan_1945", "1945｜鐵路"),
           ("aerial", 1973, "1973｜鐵道在地面"), ("aerial", 1994, "1994｜地下化完成"), ("aerial", 2025, "2025｜市民大道與高架")]


def fig_periods():
    """P04：市民大道不同時期疊圖，2 欄 × 3 列；底圖諾利圖，200 m 方格（同 03 判定）內置入當時圖面——舊地圖反黑、航照黑白"""
    M, _ = T2.mask_geom()
    OLD, xs, ys, table = T3.cells(M)
    b0 = VIEW.bounds; ob = OLD.bounds
    strip = box(b0[0], max(b0[1], ob[1] - 100), b0[2], min(b0[3], ob[3] + 100))
    pw = (CW - 24) / 2
    panels = []
    for i, (kind, src, lab) in enumerate(PERIODS):
        m = Map(strip, pw, my=14); m.nolli()
        sb = strip.bounds
        if kind == "map":
            im = ImageOps.invert(ImageOps.autocontrast(T1.raster_3826(src, b0), cutoff=1).convert("L"))
            im = im.crop((0, int(b0[3] - sb[3]), im.width, int(b0[3] - sb[1])))
        else:
            w, h = int((sb[2] - sb[0]) / 2), int((sb[3] - sb[1]) / 2)
            im = Image.open(hs.fetch(src, tuple(int(v) for v in sb), w, h)).convert("L")
        jb = io.BytesIO(); im.save(jb, "JPEG", quality=85)
        T1.insert_clipped(m.page, m.frame, jb.getvalue(), m.rings(OLD.intersection(strip)))
        m.finish(top=i < 2, bottom=i >= 4, lab=8)
        m.lines([LineString([(x, sb[1]), (x, sb[3])]) for x in xs] + [LineString([(sb[0], y), (sb[2], y)]) for y in ys if sb[1] < y < sb[3]], (.5, .5, .5), .4, "[4 3] 0")
        m.text(m.frame.x0 + 6, m.frame.y0 + 14, lab, 10, "hm", INK, box_=(1, 1, 1))
        panels.append(m.save(f"p04_{i}"))
    ph = fitz.open(panels[0])[0].rect.height
    doc = fitz.open(); page = doc.new_page(width=CW, height=3 * ph + 2 * 6)
    for i, p in enumerate(panels):
        x0 = (i % 2) * (pw + 24); y0 = (i // 2) * (ph + 6)
        page.show_pdf_page(fitz.Rect(x0, y0, x0 + pw, y0 + ph), fitz.open(p), 0)
    p = FIG / "p04_periods.pdf"; doc.save(p, garbage=3, deflate=True); return p


PHOTO_ROOT = Path("/Users/ktlu/Desktop/civic photo")


def pick_photos(holes_):
    """依單元與距離挑照片：單元相符者，有座標取最近，否則依檔名順序；不重複。Z1、Z8 無現場照片。"""
    import csv
    rows = list(csv.DictReader(open(D4 / "photos/photo_reading.csv", encoding="utf-8-sig")))
    used, out = set(), []
    for z, c, r, kind in holes_:
        cand = [x for x in rows if z in x["單元"].replace("–", " ").split() and x["檔案"] not in used and (PHOTO_ROOT / x["檔案"]).exists()]
        cand.sort(key=lambda x: (Point(float(x["E_3826"]), float(x["N_3826"])).distance(c) if x["E_3826"] else 1e9, x["檔案"]))
        f = cand[0]["檔案"] if cand else None
        if f:
            used.add(f)
        out.append(f)
    return out


def photo_inv(path, px):
    im = Image.open(PHOTO_ROOT / path); im = ImageOps.exif_transpose(im).convert("L")   # 先調黑白
    s = min(im.size); im = im.crop(((im.width - s) // 2, (im.height - s) // 2, (im.width + s) // 2, (im.height + s) // 2)).resize((px, px), Image.LANCZOS)
    return ImageOps.invert(ImageOps.autocontrast(im, cutoff=1))                          # 再反白


def membrane_holes():
    big, small = holes()
    hs_ = [(z, c, 170, "big") for z, c in big.items()] + [(z, c, 60, "small") for z, (L, c) in small.items()]
    return hs_, small


ELEV = shape(json.load(open(D3 / "civic_elevated_EPSG3826.json"))["elevated"])


def fig_membrane2(only=None, name="p15_membrane"):
    """P15：諾利圖；市民高架兩側 300 m 內反黑（地黑、建物白）；Z1–Z8 主題之大孔（各段主角）／小孔（最長無平面穿越段），孔內放現場照片（黑白後反白）。
    only＝圖層名，供桌面編輯專案分層輸出：nolli／band／photos／rings／roads"""
    on = lambda k: only is None or only == k
    hs_, small = membrane_holes(); photos = pick_photos(hs_)
    band = ELEV.buffer(300).intersection(VIEW)
    m = Map(VIEW, CW)
    V = VIEW.buffer(5)
    if on("nolli"):
        m.nolli()
    if on("band"):
        m.poly([band], fill=INK)
        m.poly([g.intersection(band) for g in NL.PRIV if g.intersects(band)], fill=(1, 1, 1))
        m.poly([g.intersection(band) for g in NL.PUB if g.intersects(band)], stroke=(1, 1, 1), width=.35)
    if on("photos"):
        for (z, c, r, kind), f in zip(hs_, photos):
            circ = c.buffer(r, 64)
            if f is None:
                m.poly([circ], fill=(1, 1, 1)); continue
            im = photo_inv(f, 900); jb = io.BytesIO(); im.save(jb, "JPEG", quality=86)
            rect = fitz.Rect(m.tf(c.x - r, c.y + r), m.tf(c.x + r, c.y - r))
            T1.insert_clipped(m.page, rect, jb.getvalue(), m.rings(circ))
    if on("rings"):
        for z, c, r, kind in hs_:
            sh = m.page.new_shape(); sh.draw_circle(m.tf(c.x, c.y), r * m.k)
            sh.finish(color=(1, 1, 1) if kind == "big" else MAG, width=1.6 if kind == "big" else 1.4); sh.commit()
    if on("roads"):
        m.finish(dash=(.6, .6, .6))
    elif only is not None:
        pass
    if only is None:
        pass
    print("孔與照片：", [(z, kind, f) for (z, c, r, kind), f in zip(hs_, photos)])
    return m.save(name), hs_, photos


# ── P15 v2（2026-10-14 使用者指示）：諾利底圖（黑）＋分隔島（黑）＋沿線牆（紅）＋古蹟輪廓與討論度圓 ──
# 沿線古蹟＝文資登錄「古蹟」類、位於 Z1–Z8 範圍外擴 60 m 內（同 P05 範圍內定義）＋北門（Z1 主角，登錄點位不在圖幅內，輪廓取 Z1 key_buildings）。
# 輪廓＝登錄點位所在之諾利建物（含公共建物），點不落在建物時取 30 m 內最近者。
# 討論度＝中文維基百科條目近 12 個月（2025-10～2026-09）使用者瀏覽數（data/古蹟討論度_維基瀏覽_202510-202609.json）；無條目＝0。
# 圓：中心＝輪廓形心；r_min＝形心至輪廓最遠點＋0.05 m；r＝r_min＋s ×（50 − r_min），s＝log(1+瀏覽)／log(1+最大瀏覽)；
#     直徑上限 100 m，惟 r_min > 50 m 時無法同時滿足，以涵蓋輪廓為先並列出。
HER_WIKI = {"原大阪商船株式會社臺北支店": "原大阪商船株式會社台北支店", "臺北郵局": "臺北郵局", "監察院": "監察院廳舍", "行政院": "行政院中央大樓",
            "臺北撫臺街洋樓": "臺北撫臺街洋樓", "臺北酒廠": "華山1914文化創意產業園區", "清代機器局遺構": "清代機器局遺構",
            "鐵道部部長宿舍": "鐵道部部長宿舍", "臺北市政府舊廈(原建成小學校)": "臺北市政府舊廈", "鐵道部臺北工場車輛修理工場": "臺北工場",
            "中山基督長老教會": "中山基督長老教會", "臺北市政府衛生局舊址": "臺北市政府衛生局舊址", "建國啤酒廠": "建國啤酒廠",
            "臺北機廠": "臺北機廠 (國定古蹟)", "松山菸廠": "松山文創園區", "北門": "臺北府城北門",
            "臺灣總督府交通局鐵道部(廳舍、八角樓男廁、戰時指揮中心、工務室、電源室、食堂)": "臺灣總督府交通局鐵道部 (文化資產)"}
WALL_C = (0.85, 0.12, 0.10)


HER_OSM_NAME = {"行政院": "行政院大廈", "監察院": "監察院廳舍", "臺灣總督府交通局鐵道部(廳舍、八角樓男廁、戰時指揮中心、工務室、電源室、食堂)": "主廳舍", "北門": "臺北府城北門"}
HER_NONE = []   # 無建物輪廓之古蹟 (名稱, 登錄點)（執行時填入，供說明）


def heritage_rings():
    """輪廓用 OSM 單棟建物（諾利底圖之線稿會把相鄰建物合併成整個街廓，不宜作古蹟輪廓）：
    名稱對應（HER_OSM_NAME）→ 含登錄點之建物 → 20 m 內最近建物；皆無者不畫圓，列入 HER_NONE。"""
    pv = json.load(open(HERE / "data/古蹟討論度_維基瀏覽_202510-202609.json"))
    ob = [(shape(f["geometry"]).buffer(0), f["properties"]) for f in gj(ROOT / "03_最新產出/06_市民大道諾利圖_20261014/data/osm_nolli_EPSG3826.geojson")
          if f["properties"]["kind"] == "building"]
    ob = [(g, p) for g, p in ob if g.intersects(VIEW)]
    sites = [("北門", Point(301583, 2771162))] + [(c["name"], p) for p, c, inn in heritage() if inn and c["type"] == "古蹟"]
    out = []; HER_NONE.clear()
    for nm, p in sites:
        byname = [g for g, q in ob if nm in HER_OSM_NAME and q.get("name") == HER_OSM_NAME[nm]]
        hit = byname or [g for g, _ in ob if g.contains(p)] or sorted([g for g, _ in ob if g.distance(p) <= 20], key=p.distance)[:1]
        if hit:
            out.append((nm, min(hit, key=lambda g: g.distance(p))))
        else:
            HER_NONE.append((nm, p)); print("古蹟無對應建物輪廓：", nm)
    vmax = max(v for v in pv.values() if isinstance(v, int))
    res = []
    for nm, g in out:
        c = g.centroid
        rmin = max(c.distance(Point(xy)) for q in getattr(g, "geoms", [g]) for xy in q.exterior.coords) + 0.05
        v = pv.get(HER_WIKI.get(nm, ""), 0); v = v if isinstance(v, int) else 0
        s = math.log1p(v) / math.log1p(vmax)
        res.append(dict(name=nm, geom=g, c=c, rmin=rmin, views=v, r=max(rmin, rmin + s * (50 - rmin)), wiki=HER_WIKI.get(nm, "")))
    return res


def walls():
    out = []
    for z in range(1, 9):
        for f in gj(D4 / f"Z{z}_ns_factors_EPSG3826.geojson"):
            p = f["properties"]
            if p.get("type") == "barrier" and any(k in p.get("note", "") for k in ("OSM wall", "retaining_wall")):
                out.append(shape(f["geometry"]))
    return out


def medians():
    return [shape(f["geometry"]) for z in range(1, 9) for f in gj(D4 / f"Z{z}_ns_factors_EPSG3826.geojson") if f["properties"].get("type") == "median"]


def fig_membrane3(name="p15_membrane_v2"):
    m = Map(VIEW, CW)
    m.nolli()                                                            # 1 諾利底圖（黑）
    m.poly([g.intersection(VIEW) for g in medians()], fill=INK)          # 2 市民大道分隔島（黑）
    W_ = walls(); m.lines([g.intersection(VIEW) for g in W_], WALL_C, 1.2)   # 3 沿線牆（紅）
    H = heritage_rings()
    m.poly([h["geom"] for h in H], fill=HER_C)                           # 4 古蹟輪廓（統一色表：紫＝古蹟）
    for h in H:                                                          # 5 討論度圓
        sh = m.page.new_shape(); sh.draw_circle(m.tf(h["c"].x, h["c"].y), h["r"] * m.k); sh.finish(color=HER_C, width=.9); sh.commit()
    m.finish(dash=(.6, .6, .6))
    import csv
    with open(HERE / "data/P15v2_古蹟圓參數.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh); w.writerow(["古蹟", "維基條目", "近12月瀏覽", "形心E", "形心N", "最小半徑_m", "半徑_m", "直徑_m", "備註"])
        for h in sorted(H, key=lambda h: -h["views"]):
            w.writerow([h["name"], h["wiki"] or "（無條目）", h["views"], round(h["c"].x, 1), round(h["c"].y, 1), round(h["rmin"], 2), round(h["r"], 2), round(2 * h["r"], 1),
                        "輪廓大於 100 m 圓，以涵蓋輪廓為先" if h["rmin"] > 50 else ""])
        for nm, _ in HER_NONE:
            w.writerow([nm, HER_WIKI.get(nm, ""), "", "", "", "", "", "", "OSM 無建物輪廓（20 m 內），未畫圓"])
    print("牆", len(W_), "段", round(sum(g.length for g in W_)), "m；古蹟", len(H), "處")
    return m.save(name)


# ── P15 v3（2026-10-15 使用者指示）：古蹟 5 分鐘步行圈（400 m）沿街廓變形 → 聯集；聯集內做牆 ──
# 街廓＝OSM 平面道路中心線（BLOCK_HW，不含高架／地下、人行道、服務道路）圍成之面（scripts/07_extract_ways.py → data/osm_ways_EPSG3826.geojson）。
# 步行圈：以古蹟輪廓形心（無輪廓者用登錄點）為中心之 400 m 圓。圓周上每 10° 一個控制點，沿徑向推拉到最近的街廓邊（街道）：
#   圓穿過之街廓，圈內面積 ≥ 50% 者整塊納入（控制點外推至街廓外緣），否則排除（內拉至內緣）；推拉上限 ±半徑／8。
#   控制點作為週期三次 B-spline 之控制點（曲線受其牽引、不必通過）→ 平滑的變形圈。各圈取聯集。
# 聯集內：
#   牆＝OSM barrier=wall／retaining_wall（紅粗線）；
#   建物量體（諾利底圖不透之建物）挖空成牆（紅細線），開口預設朝大道或鄰近巷道——面向市民大道（平面道路 80 m 內、其間無其他建物遮擋）者朝大道，
#   否則朝最近街巷（LANE_HW，含服務道路、不含人行道）；開口在最靠近該街道之外牆邊之中點，寬＝邊長之半（3–15 m）。
#   古蹟本身不挖空（紫）。
# 使用者 2026-10-15 刪除（P15_沿線古蹟點位.csv 編號 8、9、11、13、14、15、16；12 市政府舊廈先刪後加回、改刪 13 衛生局舊址），步行圈留 14 處
HER_DROP = {"博愛路2號店屋", "博愛路4、6、8號店屋", "原大阪商船株式會社臺北支店", "臺北市政府衛生局舊址", "行政院", "監察院", "中山基督長老教會"}
ORTHO = ROOT / "03_最新產出/02_南京至仁愛擴幅_20261005"     # 臺北市 2025 正射影像（historygis Aerial/Ortho_2025，九張 0.6 m/px，2026-10-05 取回）


def ortho_mosaic(b, px=1.0, gray=True, lift=.18):
    """b 範圍之正射影像拼接（每像素 px m）；gray：轉黑白並提亮 lift（白色混合），讓紅牆與紫色古蹟可讀"""
    Image.MAX_IMAGE_PIXELS = None
    x0, y0, x1, y1 = b; out = Image.new("RGB", (int((x1 - x0) / px), int((y1 - y0) / px)), "white")
    for mm in json.load(open(ORTHO / "imagery_manifest.json"))["images"]:
        bx = mm["bbox"]; cx0, cx1, cy0, cy1 = max(x0, bx[0]), min(x1, bx[2]), max(y0, bx[1]), min(y1, bx[3])
        if cx0 >= cx1 or cy0 >= cy1:
            continue
        im = Image.open(ORTHO / "imagery" / mm["file"]).convert("RGB"); sx = im.width / (bx[2] - bx[0]); sy = im.height / (bx[3] - bx[1])
        c = im.crop((int((cx0 - bx[0]) * sx), int((bx[3] - cy1) * sy), int((cx1 - bx[0]) * sx), int((bx[3] - cy0) * sy)))
        out.paste(c.resize((max(1, round((cx1 - cx0) / px)), max(1, round((cy1 - cy0) / px))), Image.LANCZOS), (round((cx0 - x0) / px), round((y1 - cy1) / px)))
    if gray:
        out = Image.blend(ImageOps.autocontrast(out.convert("L"), cutoff=1), Image.new("L", out.size, 255), lift)
    return out
WALK_R, WALK_D, WALK_N = 400, 50, 36    # 預設 5 分鐘；推拉上限＝半徑之 1／8（使用者 2026-10-15）；另出 200 m、300 m
BLOCK_HW = {"trunk", "primary", "secondary", "tertiary", "unclassified", "residential", "living_street", "pedestrian"}
LANE_HW = BLOCK_HW | {"service"}


def osm_roads():
    def grade(p):
        try:
            lay = int(str(p.get("layer") or 0).split(";")[0])
        except ValueError:
            lay = 0
        return p.get("bridge") is None and p.get("tunnel") is None and lay == 0
    return [(shape(f["geometry"]), f["properties"]) for f in gj(HERE / "data/osm_ways_EPSG3826.geojson")
            if f["properties"]["kind"] == "road" and grade(f["properties"])]


def bspline_closed(P, n=24):
    """週期均勻三次 B-spline：P＝控制點（不必在曲線上）"""
    out, N = [], len(P)
    for i in range(N):
        p0, p1, p2, p3 = P[i - 1], P[i], P[(i + 1) % N], P[(i + 2) % N]
        for k in range(n):
            t = k / n; b = ((1 - t) ** 3 / 6, (3 * t ** 3 - 6 * t ** 2 + 4) / 6, (-3 * t ** 3 + 3 * t ** 2 + 3 * t + 1) / 6, t ** 3 / 6)
            out.append((sum(w * q[0] for w, q in zip(b, (p0, p1, p2, p3))), sum(w * q[1] for w, q in zip(b, (p0, p1, p2, p3)))))
    return out


def walk_shape(c, blocks, tree, WALK_R=WALK_R, WALK_D=WALK_D):
    from shapely.geometry import Polygon
    circ = c.buffer(WALK_R, 128)
    near = [blocks[i] for i in tree.query(c.buffer(WALK_R + WALK_D))]
    S = unary_union([b for b in near if b.intersects(circ) and b.intersection(circ).area >= .5 * b.area] + [c.buffer(WALK_R - WALK_D, 64)])
    B = S.boundary; cv = []
    for k in range(WALK_N):
        a = 2 * math.pi * k / WALK_N; ux, uy = math.cos(a), math.sin(a)
        at = lambda d: (c.x + ux * d, c.y + uy * d)
        hit = LineString([at(WALK_R - WALK_D), at(WALK_R + WALK_D)]).intersection(B)
        ds = [c.distance(Point(q)) for g in getattr(hit, "geoms", [hit]) if not g.is_empty for q in getattr(g, "coords", [])]
        if ds:
            d = min(ds, key=lambda d: abs(d - WALK_R))
        else:      # 推拉範圍內無街道（大街廓）：依該處是否納入決定外推或內拉到上限
            d = WALK_R + WALK_D if S.contains(Point(at(WALK_R))) else WALK_R - WALK_D
        cv.append(at(d))
    return Polygon(bspline_closed(cv)).buffer(0), cv


def hollow(g, target):
    """建物外牆挖開口：最靠近 target 之外牆邊（≥ 3 m）中點，開口寬＝邊長之半（3–15 m）；回傳牆線"""
    from shapely.ops import substring
    ring = g.exterior.simplify(.5)
    cs = list(ring.coords)
    edges = [(Point(a), Point(b)) for a, b in zip(cs, cs[1:]) if Point(a).distance(Point(b)) >= 3]
    walls_ = [LineString(r.coords) for r in g.interiors]
    if not edges:
        return [LineString(cs)] + walls_, False
    a, b = min(edges, key=lambda e: LineString(e).interpolate(.5, normalized=True).distance(target))
    L = a.distance(b); w = min(max(L / 2, 3), 15, L - .5)
    line = LineString(cs); Lr = line.length
    t0 = line.project(LineString((a, b)).interpolate(.5, normalized=True))
    dbl = LineString(cs + cs[1:])
    return [substring(dbl, t0 + w / 2, t0 - w / 2 + Lr)] + walls_, True


def hollow_split(g, target):
    """同 hollow，但把牆分成（開口側之牆, 其他牆）：開口所在外牆邊之剩餘兩段為開口側（細），其餘外牆與內院牆為加厚"""
    from shapely.ops import substring
    cs = list(g.exterior.simplify(.5).coords)
    inner = [LineString(r.coords) for r in g.interiors]
    cum = [0.0]
    for a, b in zip(cs, cs[1:]):
        cum.append(cum[-1] + Point(a).distance(Point(b)))
    idx = [i for i in range(len(cs) - 1) if cum[i + 1] - cum[i] >= 3]
    if not idx:
        return [LineString(cs)] + inner, [], False
    i = min(idx, key=lambda i: LineString(cs[i:i + 2]).interpolate(.5, normalized=True).distance(target))
    ta, tb, Lr = cum[i], cum[i + 1], cum[-1]; L = tb - ta
    w = min(max(L / 2, 3), 15, L - .5); t0 = (ta + tb) / 2
    dbl = LineString(cs + cs[1:])
    thin = [substring(dbl, ta, t0 - w / 2), substring(dbl, t0 + w / 2, tb)]
    return [substring(dbl, tb, ta + Lr)] + inner, thin, True


def junctions(roads):
    """沿線路口穿越點 → 十字路口圓。圓心＝橫交道路中心線與市民大道軸線之交點（T 字路口取軸線上最近點）；
    半徑＝涵蓋該路口所有行穿線，及其對橫交道路中心線之鏡射（只有單側行穿線者補齊另一側）＋1 m。
    同一路口（圓心 30 m 內）之多個穿越點合併；未橫越大道者（EXCL）與路段中行人穿越道不計。"""
    from shapely.ops import nearest_points
    b = VIEW.bounds
    axis = LineString([(x, vs.civ_y(x)) for x in range(int(b[0]) - 200, int(b[2]) + 200, 10)])
    cross = [(g, p) for g, p in roads if p["highway"] in BLOCK_HW and "市民大道" not in (p.get("name") or "")]
    st, pts = [], []
    for z in range(1, 9):
        for f in gj(D4 / f"Z{z}_ns_factors_EPSG3826.geojson"):
            q = f["properties"]
            if q.get("type") in ("crossing_stripe", "平面穿越行穿線", "行穿線", "行人穿越道"):
                st.append(shape(f["geometry"]))
            elif q.get("type") == "crossing" and (f"Z{z}", round(q["s"])) not in EXCL and not str(q.get("xing") or "").startswith("行人穿越道"):
                pts.append((shape(f["geometry"]), q, f"Z{z}"))
    J = []
    for pt, q, z in pts:
        near = [(g, r) for g, r in cross if g.distance(pt) < 45 and g.distance(axis) < 30]
        if not near:
            continue
        named = [(g, r) for g, r in near if q["name"][:2] in (r.get("name") or "")]
        g, r = min(named or near, key=lambda t: t[0].distance(pt))
        hit = g.intersection(axis)
        hp = [Point(c) for h in getattr(hit, "geoms", [hit]) if not h.is_empty for c in getattr(h, "coords", [])]
        c = min(hp, key=pt.distance) if hp else nearest_points(axis, g)[0]
        t = g.project(c); a1, a2 = g.interpolate(max(t - 8, 0)), g.interpolate(min(t + 8, g.length))
        n = math.hypot(a2.x - a1.x, a2.y - a1.y) or 1; u = ((a2.x - a1.x) / n, (a2.y - a1.y) / n)
        base = (r.get("name") or "").split("段")[0].rstrip("一二三四五六七八九十")
        j = next((j for j in J if j["c"].distance(c) < 30 or (base and j["base"] == base and j["c"].distance(c) < 100)), None)
        if j is None:
            J.append(dict(c=c, cs=[c], u=u, span=q.get("span_m") or 35, names={q["name"]}, zones={z}, road=r.get("name"), base=base))
        else:   # 同一路口（含雙向分隔之橫交道路，如建國南路、敦化南路）：圓心取各中心之中點
            j["span"] = max(j["span"], q.get("span_m") or 35); j["names"].add(q["name"]); j["zones"].add(z)
            if all(c.distance(o) > 5 for o in j["cs"]):
                j["cs"].append(c); j["c"] = Point(sum(o.x for o in j["cs"]) / len(j["cs"]), sum(o.y for o in j["cs"]) / len(j["cs"]))
    for j in J:
        c, (ux, uy) = j["c"], j["u"]
        sep = max((a.distance(b_) for a in j["cs"] for b_ in j["cs"]), default=0)
        off = lambda g: abs((g.centroid.x - c.x) * uy - (g.centroid.y - c.y) * ux)      # 至橫交道路中心線之距離
        mine = [s_ for s_ in st if s_.distance(c) <= j["span"] / 2 + 20 and off(s_) <= 25 + sep / 2]
        P = [(x, y) for s_ in mine for x, y in s_.exterior.coords]
        P += [(c.x + 2 * ((x - c.x) * ux + (y - c.y) * uy) * ux - (x - c.x), c.y + 2 * ((x - c.x) * ux + (y - c.y) * uy) * uy - (y - c.y)) for x, y in P]
        j["n_stripes"] = len(mine)
        j["r"] = max((max(c.distance(Point(xy)) for xy in P) + 1) if P else 0, math.hypot(j["span"] / 2, 8 + sep / 2))   # 至少涵蓋大道全寬
    return J


WINE_D, WINE_M, WINE_L = (52, 6, 22), (142, 27, 62), (238, 186, 202)   # 酒紅（統一色表 #8E1B3E）之深、中、淺


def wine_texture(w, h):
    """酒紅底紋理：grain（Barcelona 顆粒）上色為酒紅"""
    return ImageOps.colorize(grain(w, h), black=WINE_D, mid=WINE_M, white=WINE_L, midpoint=70)


def ortho_wine(b, px=1.0):
    """空拍：等化（加強對比）→ 負片 → 酒紅單色（深酒紅—酒紅—淺粉）"""
    g = ImageOps.equalize(ortho_mosaic(b, px, gray=True, lift=0))
    return ImageOps.colorize(ImageOps.invert(g), black=(18, 2, 8), mid=WINE_M, white=(225, 140, 162))


# P15 v5（2026-10-15 使用者）：諾利底圖全黑上材質；建物依臺北三維模型（2017）樓高灰階，越高越白、越低越黑
#   樓高：data/臺北三維模型2017_圖幅_EPSG3826.geojson（tpe3d 圖磚 3847／4347 截圖幅，approximate）；分 8 級（同 09_red_palette.py 色票之灰階）
H_CLASSES = [10, 17, 23, 33, 46, 63, 96]      # 各級上限 m：1–3／4–5／6–7／8–10／11–14／15–19／20–29 層、30 層以上


def h_class(h):
    return sum(h > t for t in H_CLASSES)


def h_gray(i):
    v = .14 + .86 * i / len(H_CLASSES); return (v, v, v)


def height_layers(blds):
    """{級: [面]}：量體與建物之交集逐一分級（裙樓、塔樓分開）；建物未被量體覆蓋之部分取重疊最大量體之高度；
    完全無量體者以土地使用判讀樓層 × 3.3 m；再無者列最低級並計數"""
    import collections
    from shapely.strtree import STRtree
    V3 = [(shape(f["geometry"]), f["properties"]["height"]) for f in gj(HERE / "data/臺北三維模型2017_圖幅_EPSG3826.geojson")]
    t3 = STRtree([g for g, _ in V3])
    LU = [(shape(f["geometry"]), f["properties"]["levels"]) for f in gj(D3 / "landuse_pieces_EPSG3826.geojson") if f["properties"].get("levels")]
    tl = STRtree([g for g, _ in LU])
    out, n3, nlu, nunk = collections.defaultdict(list), 0, 0, 0
    for b in blds:
        if b.is_empty:
            continue
        parts = [(V3[i][0].intersection(b), V3[i][1]) for i in t3.query(b) if V3[i][0].intersects(b)]
        parts = [(x, h) for x, h in parts if x.area >= 1]
        if parts:
            n3 += 1
            rest = b.difference(unary_union([x for x, _ in parts]))
            if rest.area >= 1:
                out[h_class(max(parts, key=lambda t: t[0].area)[1])].append(rest)
            for x, h in parts:
                out[h_class(h)].append(x)
            continue
        lv = [LU[i][1] for i in tl.query(b) if LU[i][0].intersects(b)]
        if lv:
            nlu += 1; out[h_class(max(lv) * 3.3)].append(b)
        else:
            nunk += 1; out[0].append(b)
    print(f"樓高：三維模型 {n3} 棟、土地使用樓層 {nlu} 棟、無資料 {nunk} 棟（列最低級）")
    return out


# P15 v6（2026-10-15 使用者 A）：圓外反白（白底，建物樓高灰階反轉：越高越黑）；圓內反黑（黑材質底，牆白線，不放空拍、取消酒紅）
#   分層輸出（由下而上），供 10_p15_v6.py 組 1920×1080 頁（加古蹟標注、色票）與 AI 圖層
V6_LAYERS = ["01_圓外建物樓高", "02_圓內黑底材質", "03_分隔島", "04_圓內公共建物線", "05_圓內牆_開口側", "06_圓內牆_加厚", "07_既有牆", "08_古蹟",
             "09_十字路口圓", "10_幹道虛線與路名"]


def h_gray_inv(i):
    v = 1 - h_gray(i)[0]; return (v, v, v)


def draw_v6(name, U, H, keep_black, wall_b, wall_t, wall_o, roads):
    M = {k: Map(VIEW, CW) for k in V6_LAYERS}
    V = VIEW.buffer(5); Uv = U.intersection(VIEW)
    m = M["01_圓外建物樓高"]; m.nolli(priv=None, pub=None)
    pubs = [g.intersection(V) for g in NL.PUB if g.intersects(V) and not U.contains(g.representative_point())]
    HLY = height_layers(keep_black + pubs)
    for k in sorted(HLY):
        m.poly([unary_union(HLY[k])], fill=h_gray_inv(k))
    m = M["02_圓內黑底材質"]
    tex = ImageOps.colorize(grain(int(m.frame.width * 2), int(m.frame.height * 2)), black=(0, 0, 0), white=(90, 90, 90))
    jb = io.BytesIO(); tex.save(jb, "JPEG", quality=86); T1.insert_clipped(m.page, m.frame, jb.getvalue(), m.rings(Uv))
    M["03_分隔島"].poly([g.intersection(VIEW) for g in medians()], fill=INK, stroke=(.5, .5, .5), width=.4)
    M["04_圓內公共建物線"].poly([g.intersection(V) for g in NL.PUB if g.intersects(V) and U.contains(g.representative_point())], stroke=(1, 1, 1), width=.35)
    M["05_圓內牆_開口側"].lines([g.intersection(VIEW) for g in wall_t], (1, 1, 1), .35)
    M["06_圓內牆_加厚"].lines([g.intersection(VIEW) for g in wall_b], (1, 1, 1), 1.0)
    M["07_既有牆"].lines([g.intersection(VIEW) for g in wall_o], (1, 1, 1), 1.4)
    M["08_古蹟"].poly([h["geom"] for h in H], fill=HER_C, stroke=(1, 1, 1), width=.6)
    m = M["09_十字路口圓"]
    for j in junctions(roads):
        sh = m.page.new_shape(); sh.draw_circle(m.tf(j["c"].x, j["c"].y), j["r"] * m.k); sh.finish(color=ORANGE, width=1.4); sh.commit()
    M["10_幹道虛線與路名"].finish(dash=(.6, .6, .6), dw=.8, dop=.9, lab_col=INK)
    return [(k, M[k].save(f"{name}_{k}")) for k in V6_LAYERS]


# P15 v7（2026-10-15 使用者）：圓內的牆改為建物輪廓並套樓層參數（黑底：越高越白，同 v5）；步行圈邊線淺灰虛線。其餘同 v6。
#   建物（諾利 PRIV＋PUB）以步行圈聯集切開：圈外部分白底灰階（越高越黑）、圈內部分黑底灰階（越高越白）
V7_LAYERS = ["01_圓外建物樓高", "02_圓內黑底材質", "03_圓內建物樓高", "04_分隔島", "05_既有牆", "06_古蹟", "07_十字路口圓", "08_步行圈邊線", "09_幹道虛線與路名"]


def draw_v7(name, U, H, wall_o, roads):
    M = {k: Map(VIEW, CW) for k in V7_LAYERS}
    V = VIEW.buffer(5); Uv = U.intersection(VIEW)
    blds = [g.intersection(V) for g in NL.PRIV + NL.PUB if g.intersects(V)]
    M["01_圓外建物樓高"].nolli(priv=None, pub=None)
    HO = height_layers([g.difference(U) for g in blds if not U.contains(g)])
    for k in sorted(HO):
        M["01_圓外建物樓高"].poly([unary_union(HO[k])], fill=h_gray_inv(k))
    m = M["02_圓內黑底材質"]
    tex = ImageOps.colorize(grain(int(m.frame.width * 2), int(m.frame.height * 2)), black=(0, 0, 0), white=(90, 90, 90))
    jb = io.BytesIO(); tex.save(jb, "JPEG", quality=86); T1.insert_clipped(m.page, m.frame, jb.getvalue(), m.rings(Uv))
    HI = height_layers([g.intersection(U) for g in blds if g.intersects(U)])
    for k in sorted(HI):
        M["03_圓內建物樓高"].poly([unary_union(HI[k])], fill=h_gray(k))
    M["04_分隔島"].poly([g.intersection(VIEW) for g in medians()], fill=INK, stroke=(.5, .5, .5), width=.4)
    M["05_既有牆"].lines([g.intersection(VIEW) for g in wall_o], (1, 1, 1), 1.4)
    M["06_古蹟"].poly([h["geom"] for h in H], fill=HER_C, stroke=(1, 1, 1), width=.6)
    m = M["07_十字路口圓"]
    for j in junctions(roads):
        sh = m.page.new_shape(); sh.draw_circle(m.tf(j["c"].x, j["c"].y), j["r"] * m.k); sh.finish(color=ORANGE, width=1.4); sh.commit()
    M["08_步行圈邊線"].poly([Uv], stroke=(.78, .78, .78), width=.9, dashes="[4 3] 0")
    M["09_幹道虛線與路名"].finish(dash=(.6, .6, .6), dw=.8, dop=.9, lab_col=INK)
    return [(k, M[k].save(f"{name}_{k}")) for k in V7_LAYERS]


def fig_membrane_walk(name="p15_membrane_v3", R=WALK_R, deform=True, aerial=False, wine=False, black=False, v6=False, v7=False):
    """wine（2026-10-15 使用者 A 配色）：圓外酒紅底＋顆粒紋理、建物黑；圓內空拍加強對比負片酒紅；圓內牆白線（開口側細、其餘加厚）；
    幹道虛線與路名加強；沿線十字路口畫圓（橘＝通行元素）"""
    wine = wine or black; aerial = aerial or wine   # black（v5）：圓外全黑材質＋樓高灰階，其餘同 wine
    """deform=False：不變形之幾何圓（2026-10-15 使用者另要 100／200／300 m 版）；aerial：聯集內底圖換成 2025 正射影像（黑白）"""
    D = R / 8; tag = ("" if R == WALK_R and deform else f"_{R}m") + ("" if deform else "_圓") + ("_黑" if black else "_酒紅" if wine else "")
    from shapely.ops import polygonize
    from shapely.strtree import STRtree
    roads = osm_roads()
    blocks = [b for b in polygonize(unary_union([g for g, p in roads if p["highway"] in BLOCK_HW])) if b.area > 100]
    btree = STRtree(blocks)
    H = [h for h in heritage_rings() if h["name"] not in HER_DROP]
    centers = [(h["name"], h["c"], h["geom"]) for h in H if h["name"] not in HER_DROP] + [(nm, p, None) for nm, p in HER_NONE if nm not in HER_DROP]
    shapes = [(nm, c) + (walk_shape(c, blocks, btree, R, D) if deform else (c.buffer(R, 128), [])) for nm, c, _ in centers]
    U = unary_union([s for _, _, s, _ in shapes])
    # 聯集內：建物挖空成牆
    blvd = unary_union([g for g, p in roads if "市民大道" in (p.get("name") or "")])
    lanes = [g for g, p in roads if p["highway"] in LANE_HW and "市民大道" not in (p.get("name") or "")]
    ltree = STRtree(lanes)
    V = VIEW.buffer(5)
    from shapely.ops import nearest_points
    allb = [g for g in NL.PRIV + NL.PUB if g.intersects(V)]; atree = STRtree(allb)

    def faces_blvd(g):   # 與市民大道之間 80 m 內無其他建物遮擋（第一排、面向大道）
        p1, p2 = nearest_points(g, blvd)
        if p1.distance(p2) > 80:
            return False
        seg = LineString([p1, p2]); seg = LineString([seg.interpolate(.5), p2]) if seg.length > .5 else seg
        return not any(allb[i] is not g and allb[i].intersects(seg) for i in atree.query(seg))

    keep_black, wall_b, wall_t, n_blvd, n_lane = [], [], [], 0, 0
    for g in NL.PRIV:
        if not g.intersects(V):
            continue
        if not U.contains(g.representative_point()):
            keep_black.append(g.intersection(V)); continue
        lane = lanes[ltree.nearest(g)]
        to_blvd = faces_blvd(g)
        if wine or v6:
            ws, wt, ok = hollow_split(g, blvd if to_blvd else lane); wall_t += wt
        else:
            ws, ok = hollow(g, blvd if to_blvd else lane)
        wall_b += ws; n_blvd += ok and to_blvd; n_lane += ok and not to_blvd
    wall_o = [g.intersection(U) for g, p in ((shape(f["geometry"]), f["properties"]) for f in gj(HERE / "data/osm_ways_EPSG3826.geojson"))
              if p["kind"] == "wall" and g.intersects(U)]
    # 繪圖
    if v6 or v7:
        print(f"半徑 {R} m；步行圈 {len(shapes)}；聯集 {U.area / 1e4:.0f} ha；挖空建物 {n_blvd + n_lane}（朝大道 {n_blvd}、朝巷道 {n_lane}）；既有牆 {len(wall_o)} 段")
        return draw_v7(name, U, H, wall_o, roads) if v7 else draw_v6(name, U, H, keep_black, wall_b, wall_t, wall_o, roads)
    m = Map(VIEW, CW)
    if wine:                                                             # 圓外：酒紅底＋紋理（black：全黑材質）
        outside = VIEW.difference(U)
        tex = ImageOps.colorize(grain(int(m.frame.width * 2), int(m.frame.height * 2)), black=(0, 0, 0), white=(90, 90, 90)) if black else wine_texture(int(m.frame.width * 2), int(m.frame.height * 2))
        jb = io.BytesIO(); tex.save(jb, "JPEG", quality=86)
        T1.insert_clipped(m.page, m.frame, jb.getvalue(), m.rings(outside))
    m.nolli(priv=None, pub=None if black else (0, 0, 0), hatch=(.45, .45, .45) if black else INK)   # 諾利底圖：公共建物線＋水域
    if black:                                                            # 聯集外建物（含公共建物）依樓高灰階
        pubs = [g.intersection(V) for g in NL.PUB if g.intersects(V) and not U.contains(g.representative_point())]
        HLY = height_layers(keep_black + pubs)
        for k in sorted(HLY):
            m.poly([unary_union(HLY[k])], fill=h_gray(k))
    else:
        m.poly(keep_black, fill=INK)                                     # 聯集外建物（黑）
    if aerial:                                                           # 聯集內底圖：空拍（剪裁於聯集）
        Ub = U.intersection(VIEW); b = Ub.bounds
        jb = io.BytesIO(); (ortho_wine(b) if wine else ortho_mosaic(b)).save(jb, "JPEG", quality=82)
        T1.insert_clipped(m.page, fitz.Rect(m.tf(b[0], b[3]), m.tf(b[2], b[1])), jb.getvalue(), m.rings(Ub))
    m.poly([g.intersection(VIEW) for g in medians()], fill=INK, stroke=(.5, .5, .5) if black else None, width=.4)   # 市民大道分隔島（黑；black 版加灰邊以免融入黑底）
    if wine:                                                             # 圓內牆：白線，開口側細、其餘加厚
        m.lines([g.intersection(VIEW) for g in wall_t], (1, 1, 1), .35)
        m.lines([g.intersection(VIEW) for g in wall_b], (1, 1, 1), 1.0)
        m.lines([g.intersection(VIEW) for g in wall_o], (1, 1, 1), 1.4)
        m.poly([h["geom"] for h in H], fill=HER_C, stroke=(1, 1, 1), width=.6)
        m.poly([U.intersection(VIEW)], stroke=(1, 1, 1), width=1.2)
        J = junctions(roads)                                             # 沿線十字路口圓（橘）
        for j in J:
            sh = m.page.new_shape(); sh.draw_circle(m.tf(j["c"].x, j["c"].y), j["r"] * m.k); sh.finish(color=ORANGE, width=1.4); sh.commit()
    else:
        m.lines([g.intersection(VIEW) for g in wall_b], WALL_C, .45)     # 聯集內建物挖空之牆（紅細）
        m.lines([g.intersection(VIEW) for g in wall_o], WALL_C, 1.1)     # 聯集內既有牆（紅粗）
        m.poly([h["geom"] for h in H], fill=HER_C)                       # 古蹟輪廓（紫）
        m.poly([U.intersection(VIEW)], stroke=HER_C, width=1.2)          # 步行圈聯集（紫）
    if deform:
        dots(m, [Point(q) for *_, cv in shapes for q in cv if VIEW.contains(Point(q)) and U.boundary.distance(Point(q)) <= 30], .9, None, HER_C)   # B-spline 控制點（聯集邊界附近者）
    if wine:                                                             # 路線圖層：幹道虛線與路名加強
        m.finish(dash=(1, 1, 1), dw=.9, dop=.85, lab_col=INK)
    else:
        m.finish(dash=(.6, .6, .6))
    # 參數與幾何輸出
    if wine:
        import csv as _csv
        with open(HERE / f"data/P15v4_十字路口圓{tag}.csv", "w", newline="", encoding="utf-8-sig") as fh:
            w = _csv.writer(fh); w.writerow(["路口", "單元", "橫交道路(OSM)", "圓心E", "圓心N", "大道寬_m", "行穿線面數", "半徑_m", "直徑_m"])
            for j in sorted(J, key=lambda j: j["c"].x):
                w.writerow(["／".join(sorted(j["names"])), "／".join(sorted(j["zones"])), j["road"], round(j["c"].x, 1), round(j["c"].y, 1),
                            j["span"], j["n_stripes"], round(j["r"], 1), round(2 * j["r"], 1)])
        print("十字路口圓", len(J), "處；半徑", round(min(j["r"] for j in J)), "–", round(max(j["r"] for j in J)), "m")
    import csv
    with open(HERE / f"data/P15v3_步行圈參數{tag}.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh); w.writerow(["古蹟", "中心E", "中心N", "中心依據", "控制點數", "控制點半徑_最小m", "控制點半徑_最大m", "變形圈面積_ha", "同半徑圓面積_ha"])
        for (nm, c, s, cv), (_, _, g0) in zip(shapes, centers):
            rr = [c.distance(Point(q)) for q in cv] or [R]   # 不變形：控制點 0，半徑＝R
            w.writerow([nm, round(c.x, 1), round(c.y, 1), "古蹟輪廓形心" if g0 is not None else "登錄點（無建物輪廓）", len(cv),
                        round(min(rr)), round(max(rr)), round(s.area / 1e4, 1), round(math.pi * R ** 2 / 1e4, 1)])
    json.dump({"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "EPSG:3826"}},
               "features": [{"type": "Feature", "geometry": mapping(s), "properties": {"kind": "walk", "name": nm}} for nm, c, s, cv in shapes]
               + [{"type": "Feature", "geometry": mapping(Point(q)), "properties": {"kind": "cv", "name": nm, "i": i}} for nm, c, s, cv in shapes for i, q in enumerate(cv)]
               + [{"type": "Feature", "geometry": mapping(U), "properties": {"kind": "union"}}]},
              open(HERE / f"data/P15v3_步行圈{tag}_EPSG3826.geojson", "w"), ensure_ascii=False)
    print(f"半徑 {R} m（" + (f"推拉 ±{D:.0f} m" if deform else "不變形") + f"）；街廓 {len(blocks)}；步行圈 {len(shapes)}；聯集 {U.area / 1e4:.0f} ha；挖空建物 {n_blvd + n_lane}（朝大道 {n_blvd}、朝巷道 {n_lane}）；"
          f"既有牆 {len(wall_o)} 段 {sum(g.length for g in wall_o):.0f} m")
    return m.save(name)


# ── 組頁 ────────────────────────────────────────────────
def build():
    figs = {}
    figs["cover"] = fig_nolli("cover", box(300876, 2769238, 307604, 2773022), SW)
    figs["p02"] = fig_nolli("p02", box(301300, 2770465, 304300, 2771835), CW)
    figs["p03"], n_x = fig_access()
    figs["p04"] = fig_periods()
    figs["p05"] = fig_heritage()
    figs["p10"] = clip_src(ROOT / "04_其他疊合與排版成果/CAD及官方平面疊合/urban_plan_review/南京仁愛沿線都市計畫範圍_20261006/市民大道_南京西至仁愛_C紅框範圍與公告當年航照_20261014.pdf", fitz.Rect(250, 370, 2130, 960), "p10")
    figs["p11"] = fig_rounds(1); figs["p12"] = fig_rounds(2); figs["p13"] = fig_rounds(3)
    figs["p15"], hs_, photos = fig_membrane2()
    cap = json.load(open(HERE / "scripts/slides_captions.json"))
    cap["p03"] = cap["p03"].replace("［N］", str(n_x))
    order = ["cover", "p02", "p03", "p04", "p05", "p10", "p11", "p12", "p13", "p15"]   # v4 使用者修改：刪 P06–P09、P14、P16、P17（P06–P08 併入 P04）
    L = {k: fitz.open() for k in ("bg", "fig", "txt")}
    for i, sid in enumerate(order):
        pg = {k: L[k].new_page(width=SW, height=SH) for k in L}
        pg["txt"].insert_font(fontname="hl", fontfile=FL); pg["txt"].insert_font(fontname="hm", fontfile=FM)
        sh = pg["bg"].new_shape(); sh.draw_rect(fitz.Rect(0, 0, SW, SH)); sh.finish(color=None, fill=BG); sh.commit()
        src = fitz.open(figs[sid]); r0 = src[0].rect
        if sid == "cover":
            dst = fitz.Rect(0, 0, SW, SH)
        else:
            s_ = min(CW / r0.width, (CBOT - CTOP) / r0.height); w, h = r0.width * s_, r0.height * s_
            cy = (CTOP + CBOT) / 2; dst = fitz.Rect((SW - w) / 2, cy - h / 2, (SW + w) / 2, cy + h / 2)
        pg["fig"].show_pdf_page(dst, src, 0)
        t = pg["txt"]
        if sid == "cover":   # 標題置中（v4：「至中」）
            title = "事件 · 痕跡 — 場域"; w = fm.text_length(title, fontsize=96)
            sh = t.new_shape(); sh.draw_rect(fitz.Rect((SW - w) / 2 - 64, SH / 2 - 100, (SW + w) / 2 + 64, SH / 2 + 60)); sh.finish(color=None, fill=BG); sh.commit()
            t.insert_text(((SW - w) / 2, SH / 2 + 16), title, fontsize=96, fontname="hm", color=INK)
        else:
            if cap.get(sid):
                t.insert_textbox(fitz.Rect(128, SH - 64 - 24 - 30, 128 + 1440, SH - 40), cap[sid], fontsize=24, fontname="hl", color=MUTED)
            no = f"{i + 1:02d}"; w = fm.text_length(no, fontsize=24); t.insert_text((SW - 128 - w, SH - 64), no, fontsize=24, fontname="hm", color=INK)
    for k, nm in (("bg", "00_底色"), ("fig", "01_圖"), ("txt", "02_文字")):
        L[k].subset_fonts(); L[k].save(OUT / "_ai_layers" / f"{nm}.pdf", garbage=4, deflate=True)
    src = {nm: fitz.open(OUT / "_ai_layers" / f"{nm}.pdf") for nm in ("00_底色", "01_圖", "02_文字")}
    comp = fitz.open()
    for i in range(len(order)):
        pg = comp.new_page(width=SW, height=SH)
        for nm in src:
            pg.show_pdf_page(pg.rect, src[nm], i)
    comp.set_metadata({"title": "事件 · 痕跡 — 場域"}); comp.save(OUT / "事件痕跡場域_簡報.pdf", garbage=4, deflate=True)
    for f in (OUT / "_預覽").glob("*.jpg"):
        f.unlink()
    for i, sid in enumerate(order):
        comp[i].get_pixmap(dpi=110).save(str(OUT / "_預覽" / f"{i + 1:02d}_{sid}.jpg"))
    json.dump({"order": order}, open(OUT / "_ai_layers" / "order.json", "w"))
    print("完成", len(order), "頁", OUT / "事件痕跡場域_簡報.pdf", round((OUT / "事件痕跡場域_簡報.pdf").stat().st_size / 1e6, 1), "MB")


def desktop_project():
    """P15 另存桌面編輯專案：分層 PDF＋照片＋說明，再由 Illustrator 組 AI"""
    D = Path.home() / "Desktop/膜_P15_編輯專案_20261014"; (D / "layers").mkdir(parents=True, exist_ok=True); (D / "照片").mkdir(exist_ok=True)
    layers = [("nolli", "01_諾利圖"), ("band", "02_高架兩側300m反黑"), ("photos", "03_孔內照片（黑白反白）"), ("rings", "04_孔外框"), ("roads", "05_幹道虛線與路名")]
    files = []
    for k, nm in layers:
        p, hs_, photos = fig_membrane2(only=k, name=f"p15_layer_{k}")
        q = D / "layers" / f"{nm}.pdf"; q.write_bytes(Path(p).read_bytes()); files.append([nm, str(q)])
    full, hs_, photos = fig_membrane2()
    (D / "膜_P15.pdf").write_bytes(Path(full).read_bytes())
    lines = ["孔｜單元｜大小｜中心 E,N｜照片"]
    for (z, c, r, kind), f in zip(hs_, photos):
        tag = f"{z}_{'大孔' if kind == 'big' else '小孔'}"
        if f:
            photo_inv(f, 1600).save(D / "照片" / f"{tag}_{Path(f).stem}_反白.jpg", quality=90)
            ImageOps.exif_transpose(Image.open(PHOTO_ROOT / f)).convert("RGB").save(D / "照片" / f"{tag}_{Path(f).stem}_原圖.jpg", quality=90)
        lines.append(f"{tag}｜{z}｜半徑 {r} m｜{c.x:.0f},{c.y:.0f}｜{f or '（無現場照片，待補）'}")
    b = VIEW.bounds
    (D / "說明.txt").write_text("膜 P15 編輯專案｜2026-10-14\n"
        "圖：諾利圖；市民高架（civic_elevated）兩側 300 m 內反黑（地黑、建物白）；圓孔＝Z1–Z8 主題——大孔（各段主角重心，半徑 170 m）、小孔（各段最長無平面穿越段 ≥ 300 m 之中點，半徑 60 m）；孔內現場照片先轉黑白再反白。\n"
        f"範圍 E{b[0]:.0f}–{b[2]:.0f}、N{b[1]:.0f}–{b[3]:.0f}｜比例：圖寬 1664 pt＝6,610 m（約 1:14,000）\n"
        "檔案：膜_P15.ai（分層：" + "／".join(nm for _, nm in layers) + "）、膜_P15.pdf、layers/（各層 PDF）、照片/（反白後與原圖）\n"
        "重現：07_簡報_斷裂與揭露_20261014/scripts/04_slides.py desktop → 06_make_ai_p15.sh\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
    json.dump({"w_mm": CW * 25.4 / 72, "h_mm": fitz.open(full)[0].rect.height * 25.4 / 72, "layers": files, "out": str(D / "膜_P15.ai"), "log": str(D / "layers/ai_log.txt")},
              open(HERE / "scripts/ai_job.json", "w"), ensure_ascii=False)
    print("桌面專案", D)


if __name__ == "__main__":
    if sys.argv[1:] == ["desktop"]:
        desktop_project()
    elif sys.argv[1:] == ["p15v2"]:
        print(fig_membrane3())
    elif sys.argv[1:2] == ["p15v3"]:
        R = int(sys.argv[2]) if sys.argv[2:] else WALK_R; deform = "circle" not in sys.argv[3:]; aerial = "aerial" in sys.argv[3:]   # p15v3 R [circle] [aerial]
        wine = "wine" in sys.argv[3:]; black = "black" in sys.argv[3:]   # p15v3 R [circle] [aerial] [wine] [black]
        nm = f"p15_membrane_v5_{R}m" if black else f"p15_membrane_v4_{R}m" if wine else ("p15_membrane_v3" if R == WALK_R and deform else f"p15_membrane_v3_{R}m") + ("" if deform else "_circle") + ("_aerial" if aerial else "")
        print(fig_membrane_walk(nm, R, deform, aerial, wine, black))
    else:
        build()
