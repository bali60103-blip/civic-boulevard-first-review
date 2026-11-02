# P15 300 m 爆炸軸測圖（2026-10-15 使用者：轉 45 度做爆炸圖，主要建物用虛線暗示，由淺紅往上到深紅）
#   平面逆時針轉 45°、垂直壓 SQ 倍（平行軸測），各層等距上移 DZ。由下而上：
#     00 底圖（OSM 建物淺灰＋使用者大道紅線 R7）→ 01 幹道 R6 → 02 外圍色塊 R5（使用者圖層 12）→ 03 圖塊 R3（使用者圖層 13）
#     → 04 現有基地 R2 → 05 主角建築 R1（16 ∪ 使用者圖層 14）。
#   主要建物（主角建築）：00–04 各層畫虛線輪廓暗示；各主角建築群自底層至頂層畫垂直虛線。每層只畫細灰邊（白色透明板會洗淡下層紅色，2026-10-15 改）。
#   幾何來源同 P15 v7 300 m 編修（11／13／14 腳本）；使用者 AI 只讀不改。輸出 簡報/P15_爆炸圖_300m.pdf、.ai（分層）。
import sys, json, math, importlib.util, subprocess
from pathlib import Path
import fitz
from shapely.geometry import box, shape, Polygon
from shapely.ops import unary_union
from shapely import affinity

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "簡報"
SW, SH = 1920, 1080
ANG, SQ = 45, 0.5
for a_ in sys.argv[1:]:                       # 參數：ang=0 sq=1（90 度：平面不轉，兩軸保持直角）
    if a_.startswith("ang="): ANG = float(a_[4:])
    if a_.startswith("sq="): SQ = float(a_[3:])
ARTBASE = "artbase" in sys.argv[1:]
NOSITES = "nosites" in sys.argv[1:]
GAP = next((float(a_[4:]) for a_ in sys.argv[1:] if a_.startswith("gap=")), None)   # 90 度版板間空隙（使用者「彼此之間近一點」）          # 幹道併入底圖（90 度版預設）
TAG = "" if (ANG, SQ) == (45, 0.5) else f"_{int(90 - ANG) if ANG in (0, 45) else int(ANG)}度" + ("" if SQ == 1 else f"_壓{SQ:g}")
D = OUT / "_ai_layers" / f"p15_爆炸圖_300m{TAG}"; D.mkdir(parents=True, exist_ok=True)
PAL = {"R1": (142, 27, 62), "R2": (156, 27, 59), "R3": (170, 25, 55), "R5": (200, 19, 43), "R6": (215, 12, 34), "R7": (230, 0, 18)}
C = lambda k: tuple(v / 255 for v in PAL[k])
GREY, INK = (0.78, 0.78, 0.78), (0.086, 0.086, 0.086)


def load(name, fn):
    spec = importlib.util.spec_from_file_location(name, HERE / "scripts" / fn)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def geoms():
    V13 = load("v13", "13_p15_viewfield.py"); E = V13.E; A14 = load("a14", "14_p15_arterial_fill.py"); T1 = A14.load("t1", "01_trace_overlay.py")
    L12, L13, L14, L15 = (unary_union(E.user_blocks(f"圖層 {n}")) for n in (12, 13, 14, 15))
    crop = box(*L12.buffer(120).bounds)
    P = E.protagonists(); prot = unary_union([g.intersection(L13) for g in P if g.intersects(L13)])
    main = unary_union([prot, L14])
    art, _ = A14.road_surface_uniform(T1, box(*E.VB))
    sites = V13.sites(L12)
    OSM = HERE.parents[0] / "06_市民大道諾利圖_20261014/data/osm_nolli_EPSG3826.geojson"
    blds = [shape(f["geometry"]).buffer(0) for f in json.load(open(OSM))["features"] if f["properties"]["kind"] == "building"]
    blds = unary_union([g.intersection(crop) for g in blds if g.intersects(crop)])
    return crop, dict(base=blds, line=L15.intersection(crop), art=art.intersection(crop), band=L12, blob=L13, sites=sites, main=main)


class Axon:
    def __init__(s, crop, n_planes):
        s.c = crop.centroid
        R = affinity.scale(affinity.rotate(crop, ANG, origin=s.c), 1, SQ, origin=s.c)
        b = R.bounds; w, h = b[2] - b[0], b[3] - b[1]
        if ANG == 0:                                                                       # 90 度：平面水平全寬，層距填滿版面高
            s.k = min(1664 / w, (SH - 160) / (h * 1.6)); s.dz = (SH - 160 - h * s.k) / (n_planes - 1)
            if s.dz < h * s.k + 12:                                                          # 層板重疊：改縮比例使各板間留 12 px
                s.k = min(s.k, (SH - 160 - 12 * (n_planes - 1)) / (h * n_planes)); s.dz = h * s.k + 12
                s.x0 = (SW - w * s.k) / 2 - b[0] * s.k
            s.x0 = (SW - w * s.k) / 2 - b[0] * s.k
            if GAP is not None:                                                              # 指定板間空隙（px）：層距＝板高＋GAP，整組垂直置中
                s.dz = h * s.k + GAP
        else:
            s.k = min(1150 / w, (SH - 120) / (h + (n_planes - 1) * 0.16 * h * 1.0))      # 平面高之 16% 為層距
            s.dz = 0.16 * h * s.k
            s.x0 = (SW - w * s.k) / 2 - 120 - b[0] * s.k                                     # 右側留標注空間
        s.y0 = SH - 60 - (s.dz * 0)
        if ANG == 0 and GAP is not None:
            s.y0 = (SH + h * s.k + (n_planes - 1) * s.dz) / 2
        s.b = b

    def tf(s, x, y, lev):
        p = affinity.scale(affinity.rotate(Polygon([(x, y), (x + 1e-6, y), (x, y + 1e-6)]), ANG, origin=s.c), 1, SQ, origin=s.c).exterior.coords[0]
        return fitz.Point(s.x0 + p[0] * s.k, s.y0 - (p[1] - s.b[1]) * s.k - lev * s.dz)

    def geom(s, g):
        return affinity.scale(affinity.rotate(g, ANG, origin=s.c), 1, SQ, origin=s.c)

    def pt(s, x, y, lev):
        return fitz.Point(s.x0 + x * s.k, s.y0 - (y - s.b[1]) * s.k - lev * s.dz)


def draw_polys(page, ax, g, lev, fill=None, stroke=None, width=.4, dashes=None, fo=1.0, so=1.0):
    g = ax.geom(g); sh = page.new_shape(); n = 0
    for p in getattr(g, "geoms", [g]):
        if p.geom_type != "Polygon" or p.is_empty:
            continue
        for r in [p.exterior] + list(p.interiors):
            sh.draw_polyline([ax.pt(x, y, lev) for x, y in r.coords]); n += 1
    if n:
        sh.finish(color=stroke, fill=fill, width=width, dashes=dashes, fill_opacity=fo, stroke_opacity=so, even_odd=True, closePath=True); sh.commit()


if __name__ == "__main__":
    crop, G = geoms()
    planes = [("00_底圖", None), ("01_幹道 R6", "art"), ("02_外圍色塊 R5", "band"), ("03_圖塊 R3", "blob"), ("04_現有基地 R2", "sites"), ("05_主角建築 R1", "main")]
    if NOSITES:                                                     # 現有基地（建物輪廓下一層）不放進圖面（2026-10-15 使用者）
        planes = [p_ for p_ in planes if p_[1] != "sites"]
    if ARTBASE:                                                     # 幹道壓在諾利底圖上（2026-10-15 使用者）：不另成一層
        planes = [("00_底圖＋幹道 R6", None)] + [(f"{i:02d}_{n_.split('_', 1)[1]}", k_) for i, (n_, k_) in enumerate(planes[2:], 1)]
    col = {"art": "R6", "band": "R5", "blob": "R3", "sites": "R2", "main": "R1"}
    ax = Axon(crop, len(planes))
    layers = []
    for lev, (nm, key) in enumerate(planes):
        doc = fitz.open(); pg = doc.new_page(width=SW, height=SH)
        draw_polys(pg, ax, crop, lev, stroke=GREY, width=.5)                                     # 層板（只畫邊，不加白色透明板：會洗淡下層紅色）
        if key is None:
            draw_polys(pg, ax, G["base"], lev, fill=(.72, .72, .72))
            if ARTBASE:
                draw_polys(pg, ax, G["art"], lev, fill=C("R6"), fo=.7)         # 幹道疊在建物上（70%，建物隱約透出）
            draw_polys(pg, ax, G["line"], lev, fill=C("R7"))
        else:
            draw_polys(pg, ax, G[key], lev, fill=C(col[key]), fo=1.0 if key == "main" else .85)
        if key != "main":                                                                       # 主要建物虛線暗示
            draw_polys(pg, ax, G["main"], lev, stroke=C("R1") if key is None else (1, 1, 1), width=.5, dashes="[2 1.5] 0")
        q = D / f"{nm}.pdf"; doc.save(q, garbage=3, deflate=True); layers.append((nm, q))
    # 垂直虛線：各主角建築群（30 m 內合併）代表點，自底層至頂層
    doc = fitz.open(); pg = doc.new_page(width=SW, height=SH); sh = pg.new_shape(); n = 0
    groups = [g for g in getattr(G["main"].buffer(30).buffer(-30), "geoms", [G["main"].buffer(30).buffer(-30)]) if g.area > 2000]
    for g in groups:
        p = ax.geom(g.representative_point())
        sh.draw_line(ax.pt(p.x, p.y, 0), ax.pt(p.x, p.y, len(planes) - 1)); n += 1
    sh.finish(color=C("R1"), width=.5, dashes="[3 2] 0"); sh.commit()
    vn = f"{len(planes):02d}_主要建物垂直虛線"; q = D / f"{vn}.pdf"; doc.save(q, garbage=3, deflate=True); layers.append((vn, q))
    comp = fitz.open(); pg = comp.new_page(width=SW, height=SH)
    for _, q in layers:
        pg.show_pdf_page(pg.rect, fitz.open(q), 0)
    out = OUT / f"P15_爆炸圖_300m{TAG}.pdf"; comp.save(out, garbage=4, deflate=True)
    comp[0].get_pixmap(dpi=72).save(OUT / "_預覽" / f"P15_爆炸圖_300m{TAG}.jpg")
    print(out, "主角建築群", n, "；層", [k for k, _ in layers])
    json.dump({"w_mm": SW * 25.4 / 72, "h_mm": SH * 25.4 / 72, "layers": [[k, str(q)] for k, q in layers],
               "out": str(OUT / f"P15_爆炸圖_300m{TAG}.ai"), "log": str(D / "ai_log.txt")}, open(D / "ai_job.json", "w"), ensure_ascii=False)
    if "ai" in sys.argv:
        src = (HERE / "scripts/06_assemble_layers.jsx").read_text(encoding="utf-8")
        old = "new File($.fileName.replace(/[^\\/]+$/, '') + 'ai_job.json')"
        assert src.count(old) == 1
        jsx = D / "assemble.jsx"; jsx.write_text(src.replace(old, json.dumps(str(D / "ai_job.json")).join(["new File(", ")"])), encoding="utf-8")
        subprocess.run(["osascript", "-e", f'tell application "Adobe Illustrator" to do javascript (POSIX file "{jsx}")'], timeout=900)
        print((D / "ai_log.txt").read_text() if (D / "ai_log.txt").exists() else "（無 ai_log）")
