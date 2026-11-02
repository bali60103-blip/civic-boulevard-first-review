# P15 300 m 平面疊色（2026-10-15 使用者：再做成平面圖，把 R5 遇到的範圍都清掉、在外退一個巷道寬，然後在 R5 內堆疊紅色塊）
#   清除區＝使用者圖層 12（R5 外圍色塊）外擴 LANE m（一個巷道寬；建築技術規則最小巷寬 6 m）；區內底圖建物、幹道一律切除，留白。
#   R5 內由下而上不透明堆疊：R5（圖層 12）→ R3（圖層 13）→ R1（主角建築 16 ∪ 圖層 14）。區外：OSM 建物淺灰＋幹道 R6 70%。
#   另疊使用者大道紅線 R7（圖層 15）與路名、圖框（25）。幾何同 15_p15_exploded；使用者 AI 只讀不改。
#   2026-10-15 再改：各紅色彩度 × SAT（OKLab）、不透明度 ALPHA；最底層加很淡之黑白衛星圖（2025 正射，混白 fade）。
#   輸出 簡報/P15_平面疊色_300m.pdf、.ai（分層）。用法：python3 16_p15_plan_stack.py [lane=6] [sat=0.6] [fade=0.8] [ai]
import sys, json, math, shutil, subprocess, importlib.util
from pathlib import Path
import fitz
from shapely.geometry import box, shape
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "簡報"
LANE = next((float(a[5:]) for a in sys.argv[1:] if a.startswith("lane=")), 6.0)
MARK = "marker" in sys.argv[1:]; TEX = "texture" in sys.argv[1:]
NAME = "P15_平面疊色_麥克筆_300m" if MARK else "P15_平面疊色_紋理_300m" if TEX else "P15_平面疊色_300m"
D = OUT / "_ai_layers" / NAME.replace("P15_", "p15_"); D.mkdir(parents=True, exist_ok=True)
PAL = {"R1": (142, 27, 62), "R3": (170, 25, 55), "R5": (200, 19, 43), "R6": (215, 12, 34), "R7": (230, 0, 18)}
SAT = next((float(a[4:]) for a in sys.argv[1:] if a.startswith("sat=")), 0.6)      # 彩度倍率（使用者：透明度、彩度調低）
ALPHA = {"R7": .75, "R6": .45, "R5": .5, "R3": .55, "R1": .7}                         # 各紅色不透明度（疊越多越深）
SAT_FADE = next((float(a[5:]) for a in sys.argv[1:] if a.startswith("fade=")), 0.88)  # 衛星圖混白比例（越大越淡）


def _s2l(c):
    c /= 255; return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _l2s(c):
    c = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055; return max(0.0, min(1.0, c))


def desat(rgb, f):
    """OKLab 中保持明度、色相，彩度乘 f"""
    r, g, b = (_s2l(v) for v in rgb)
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3); m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    L, A, B = 0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s_, 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s_, 0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s_
    A, B = A * f, B * f
    l, m, s_ = (L + 0.3963377774 * A + 0.2158037573 * B) ** 3, (L - 0.1055613458 * A - 0.0638541728 * B) ** 3, (L - 0.0894841775 * A - 1.2914855480 * B) ** 3
    return tuple(_l2s(v) for v in (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s_, -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s_,
                                   -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s_))


C = lambda k: desat(PAL[k], SAT)


def satellite(dst, vb, E):
    """最底層：臺北市 2025 正射影像（02_南京至仁愛擴幅 imagery，九張）拼接 → 黑白 → 混白 SAT_FADE（很淡）"""
    from PIL import Image, ImageOps
    import io
    Image.MAX_IMAGE_PIXELS = None
    O = HERE.parents[0] / "02_南京至仁愛擴幅_20261005"; px = 1.0
    x0, y0, x1, y1 = vb; out = Image.new("RGB", (int((x1 - x0) / px), int((y1 - y0) / px)), "white")
    for mm in json.load(open(O / "imagery_manifest.json"))["images"]:
        bx = mm["bbox"]; cx0, cx1, cy0, cy1 = max(x0, bx[0]), min(x1, bx[2]), max(y0, bx[1]), min(y1, bx[3])
        if cx0 >= cx1 or cy0 >= cy1:
            continue
        im = Image.open(O / "imagery" / mm["file"]).convert("RGB"); sx = im.width / (bx[2] - bx[0]); sy = im.height / (bx[3] - bx[1])
        c = im.crop((int((cx0 - bx[0]) * sx), int((bx[3] - cy1) * sy), int((cx1 - bx[0]) * sx), int((bx[3] - cy0) * sy)))
        out.paste(c.resize((max(1, round((cx1 - cx0) / px)), max(1, round((cy1 - cy0) / px))), Image.LANCZOS), (round((cx0 - x0) / px), round((y1 - cy1) / px)))
    g = Image.blend(ImageOps.autocontrast(out.convert("L"), cutoff=1), Image.new("L", out.size, 255), SAT_FADE)
    jb = io.BytesIO(); g.save(jb, "JPEG", quality=80)
    doc = fitz.open(); pg = doc.new_page(width=1920, height=1080)
    pg.insert_image(fitz.Rect(fitz.Point(*E.to_page(x0, y1)), fitz.Point(*E.to_page(x1, y0))), stream=jb.getvalue())
    doc.save(dst, garbage=3, deflate=True)


def load(name, fn):
    spec = importlib.util.spec_from_file_location(name, HERE / "scripts" / fn)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m



# ── 麥克筆手繪質感（2026-10-15 使用者：紅色區域上麥克筆手繪的 texture）──
#   紅色區域改以半透明平行筆觸塗滿（向量，可在 AI 編輯）。筆寬 W、行距 0.72 W（相鄰重疊 → 重疊處較深）；
#   筆觸短（每筆 70–200 m，接筆處重疊 3–8 m）、微抖動、每筆角度 ±1.5°；頭尾對邊界隨機超出／短少、約 4% 漏塗。
#   方向：細長者（最小外接矩形短邊 < max(3W, 70 m)，如幹道、大道線、單棟建物）切成 150 m 小塊、每塊沿自身長軸塗（順著彎曲）；
#   其餘（R5 帶、R3 圖塊）一律 35° 斜塗。深層多塗幾遍（passes，每遍偏轉 spread 度）＝麥克筆疊色。
#   MARKER：筆寬 m、遍數、每筆不透明度、頭尾超出範圍（×W）、疊色偏轉角
MARKER = {"R6": (10, 1, .42, (-.3, .25), 0), "R5": (20, 1, .40, (-.3, .25), 0), "R3": (14, 2, .32, (-.3, .25), 20),
          "R1": (7, 2, .40, (-.12, .08), 12), "R7": (6, 1, .65, (-.2, .15), 0)}
CELL, BASE_ANG = 150.0, 35.0


def _axis(g):
    cs = list(g.minimum_rotated_rectangle.exterior.coords)
    if len(cs) < 4:
        return BASE_ANG, 0, 0
    L1, L2 = math.dist(cs[0], cs[1]), math.dist(cs[1], cs[2])
    a, b = (cs[0], cs[1]) if L1 >= L2 else (cs[1], cs[2])
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])), max(L1, L2), min(L1, L2)


def marker_layer(g, dst, col, key, seed=1):
    import random
    from shapely.geometry import LineString, box as _box
    from shapely.ops import substring
    W, passes, op, (o0, o1), spread = MARKER[key]; rnd = random.Random(seed)
    pieces = []                                                        # (多邊形, 角度)
    for part in getattr(g, "geoms", [g]):
        if part.geom_type != "Polygon" or part.area < 4:
            continue
        ang, Lmax, Lmin = _axis(part)
        if Lmin < max(3 * W, 70):                                      # 細長：切 150 m 小塊，各沿自身長軸
            b = part.bounds; ox, oy = rnd.uniform(0, CELL), rnd.uniform(0, CELL)
            x = b[0] - ox
            while x < b[2]:
                y = b[1] - oy
                while y < b[3]:
                    pc = part.intersection(_box(x, y, x + CELL, y + CELL))
                    for q in getattr(pc, "geoms", [pc]):
                        if q.geom_type == "Polygon" and q.area > 2:
                            pieces.append((q, _axis(q)[0]))
                    y += CELL
                x += CELL
        else:
            pieces.append((part, BASE_ANG))
    lines = []
    for poly, base in pieces:
        c = poly.centroid; bb = poly.bounds; R = math.hypot(bb[2] - bb[0], bb[3] - bb[1]) / 2 + W
        for ps in range(passes):
            ang = base + (0 if ps == 0 else rnd.choice((-1, 1)) * spread * rnd.uniform(.8, 1.2))
            t = -R + rnd.uniform(0, W * .72)
            while t < R:
                if rnd.random() < .04:
                    t += W * .72; continue
                a = math.radians(ang + rnd.uniform(-1.5, 1.5)); ux, uy, nx, ny = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
                n = max(2, int(2 * R / 20)); wob = 0.0; pts = []
                for k in range(n + 1):
                    s_ = -R + 2 * R * k / n; wob = .7 * wob + rnd.uniform(-.05, .05) * W
                    pts.append((c.x + ux * s_ + nx * (t + wob), c.y + uy * s_ + ny * (t + wob)))
                seg = LineString(pts).intersection(poly)
                for l in getattr(seg, "geoms", [seg]):
                    if l.geom_type != "LineString" or l.length < W * .4:
                        continue
                    pos = 0.0                                          # 分成短筆，接筆處重疊
                    while pos < l.length - 1e-6:
                        ln = rnd.uniform(70, 200); end = min(l.length, pos + ln)
                        if l.length - end < 25:
                            end = l.length
                        sub = substring(l, pos, end)
                        if sub.length >= W * .4:
                            p0, p1 = sub.coords[0], sub.coords[-1]; d = math.dist(p0, p1) or 1; vx, vy = (p1[0] - p0[0]) / d, (p1[1] - p0[1]) / d
                            e0 = rnd.uniform(o0, o1) * W if pos == 0 else rnd.uniform(2, 6)
                            e1_ = rnd.uniform(o0, o1) * W if end >= l.length else rnd.uniform(1, 4)
                            q = [(p0[0] - vx * e0, p0[1] - vy * e0)] + list(sub.coords)[1:-1] + [(p1[0] + vx * e1_, p1[1] + vy * e1_)]
                            if math.dist(q[0], q[-1]) > W * .3:
                                lines.append(q)
                        pos = end
                t += W * .72 * rnd.uniform(.85, 1.15)
    doc = fitz.open(); pg = doc.new_page(width=1920, height=1080); sh = pg.new_shape()
    E_ = _E()
    for q in lines:
        sh.draw_polyline([fitz.Point(*E_.to_page(*xy)) for xy in q])
    sh.finish(color=col, width=W * E_.K, stroke_opacity=op, lineCap=0, lineJoin=1); sh.commit()
    doc.save(dst, garbage=3, deflate=True); return len(lines)



# ── 紋理（2026-10-15 使用者：紅色區域上紋理就好、不要麥克筆）──
#   紅色平塗不變，另加一層紋理（紙張顆粒＋低頻斑駁＋淡纖維紋，灰階 205–255），裁切於全部紅色範圍之聯集，
#   以「色彩增值」疊上（白＝透明，不用 SMask：macOS 預覽 SMask 不顯示）。TEX_DEPTH＝最深處壓暗量。
TEX_DEPTH = next((float(a[4:]) for a in sys.argv[1:] if a.startswith("tex=")), 0.22)


def texture_image(w, h, seed=11):
    import numpy as np
    from scipy.ndimage import gaussian_filter
    from PIL import Image
    rng = np.random.default_rng(seed)
    low = gaussian_filter(rng.standard_normal((h, w)), 22); low = (low - low.min()) / (np.ptp(low) or 1)      # 斑駁
    grain = gaussian_filter(rng.standard_normal((h, w)), .7); grain = (grain - grain.min()) / (np.ptp(grain) or 1)  # 顆粒
    fib = gaussian_filter(rng.standard_normal((h, w)), (0.6, 9)); fib = (fib - fib.min()) / (np.ptp(fib) or 1)       # 橫向纖維
    v = .45 * low + .4 * grain + .15 * fib                                                            # 0–1，越大越深
    v = np.clip((v - .25) / .6, 0, 1)
    return Image.fromarray((255 * (1 - TEX_DEPTH * v)).astype("uint8"))


def texture_layer(region, dst):
    import io
    E_ = _E(); x0, y0, x1, y1 = E_.VB
    rect = fitz.Rect(fitz.Point(*E_.to_page(x0, y1)), fitz.Point(*E_.to_page(x1, y0)))
    im = texture_image(int(rect.width * 2), int(rect.height * 2)); jb = io.BytesIO(); im.save(jb, "JPEG", quality=88)
    doc = fitz.open(); pg = doc.new_page(width=1920, height=1080)
    xref = pg.insert_image(rect, stream=jb.getvalue())
    name = [x[7] for x in pg.get_images(full=True) if x[0] == xref][0].encode()
    rings = [[fitz.Point(*E_.to_page(*c)) for c in r.coords] for p in getattr(region, "geoms", [region]) if p.geom_type == "Polygon"
             for r in [p.exterior] + list(p.interiors)]
    path = b"".join(b"%.3f %.3f m " % (r[0].x, 1080 - r[0].y) + b"".join(b"%.3f %.3f l " % (q.x, 1080 - q.y) for q in r[1:]) + b"h\n" for r in rings)
    gs = doc.get_new_xref(); doc.update_object(gs, "<</Type/ExtGState/BM/Multiply/ca 1/CA 1>>")
    res = doc.xref_get_key(pg.xref, "Resources")
    rx = int(res[1].split()[0]) if res[0] == "xref" else pg.xref
    key = "ExtGState/GSmul" if res[0] == "xref" else "Resources/ExtGState/GSmul"
    doc.xref_set_key(rx, key, f"{gs} 0 R")
    for cx in reversed(pg.get_contents()):
        st = doc.xref_stream(cx); i = st.rfind(b"/" + name + b" Do")
        if i < 0:
            continue
        qpos = st.rfind(b"q", 0, i)
        doc.update_stream(cx, st[:qpos + 1] + b"\n/GSmul gs\n" + path + b"W* n\n" + st[qpos + 1:]); break
    doc.save(dst, garbage=3, deflate=True)

_E_cache = []


def _E():
    if not _E_cache:
        _E_cache.append(load("e11", "11_p15_user_edit.py"))
    return _E_cache[0]

if __name__ == "__main__":
    V13 = load("v13", "13_p15_viewfield.py"); E = V13.E; A14 = load("a14", "14_p15_arterial_fill.py"); T1 = A14.load("t1", "01_trace_overlay.py")
    VIEW = box(*E.VB)
    L12, L13, L14, L15 = (unary_union(E.user_blocks(f"圖層 {n}")) for n in (12, 13, 14, 15))
    P = E.protagonists(); main = unary_union([unary_union([g.intersection(L13) for g in P if g.intersects(L13)]), L14])
    clear = L12.buffer(LANE, join_style="round")
    OSM = HERE.parents[0] / "06_市民大道諾利圖_20261014/data/osm_nolli_EPSG3826.geojson"
    blds = [shape(f["geometry"]).buffer(0) for f in json.load(open(OSM))["features"] if f["properties"]["kind"] == "building"]
    blds = V13.diff(unary_union([g.intersection(VIEW) for g in blds if g.intersects(VIEW)]), clear)
    art, _ = A14.road_surface_uniform(T1, VIEW); art = V13.diff(art, clear)
    layers = []
    q = D / "00_衛星圖（黑白淡）.pdf"; satellite(q, E.VB, E); layers.append(("00_衛星圖（黑白淡）", q))
    ring = V13.diff(clear, L12)                                                          # 巷道寬退縮帶：白，蓋住衛星圖以保留留白
    for nm, g, col, fo in (("01_巷道寬退縮（白）", ring, (1, 1, 1), 1.0), ("02_底圖建物", blds, (.72, .72, .72), 1.0), ("03_幹道 R6", art, C("R6"), ALPHA["R6"]),
                           ("04_外圍色塊 R5", L12, C("R5"), ALPHA["R5"]), ("05_圖塊 R3", L13, C("R3"), ALPHA["R3"]),
                           ("06_主角建築 R1", main, C("R1"), ALPHA["R1"]), ("07_大道紅線 R7", L15, C("R7"), ALPHA["R7"])):
        q = D / f"{nm}.pdf"
        rk = nm.split()[-1] if nm.split()[-1] in MARKER else None
        if MARK and rk:
            nl = marker_layer(g, q, col, rk, seed=len(layers)); nm = nm + "（麥克筆）"; print(" ", nm, "筆觸", nl)
        else:
            E.poly_layer([g], q, col, fo)
        layers.append((nm, q))
    if TEX:                                                          # 紋理（色彩增值），裁於紅色範圍聯集
        q = D / "08_紅色紋理（色彩增值）.pdf"; texture_layer(unary_union([L12, L13, main, L15, art]), q); layers.append(("08_紅色紋理（色彩增值）", q))
    nn = f"{len(layers):02d}_路名與圖框"; q = D / f"{nn}.pdf"; shutil.copy2(E.D / "25_路名與圖框.pdf", q); layers.append((nn, q))
    comp = fitz.open(); pg = comp.new_page(width=1920, height=1080)
    for _, q in layers:
        pg.show_pdf_page(pg.rect, fitz.open(q), 0)
    out = OUT / f"{NAME}.pdf"; comp.save(out, garbage=4, deflate=True)
    comp[0].get_pixmap(dpi=72).save(OUT / "_預覽" / f"{NAME}.jpg")
    print(out, f"清除區＝R5 外擴 {LANE:g} m；R5 {L12.area / 1e4:.1f} ha、R3 {L13.area / 1e4:.1f} ha、R1 {main.area / 1e4:.1f} ha")
    json.dump({"w_mm": 1920 * 25.4 / 72, "h_mm": 1080 * 25.4 / 72, "layers": [[k, str(q)] for k, q in layers],
               "out": str(OUT / f"{NAME}.ai"), "log": str(D / "ai_log.txt")}, open(D / "ai_job.json", "w"), ensure_ascii=False)
    if "ai" in sys.argv:
        src = (HERE / "scripts/06_assemble_layers.jsx").read_text(encoding="utf-8")
        old = "new File($.fileName.replace(/[^\\/]+$/, '') + 'ai_job.json')"
        assert src.count(old) == 1
        jsx = D / "assemble.jsx"; jsx.write_text(src.replace(old, json.dumps(str(D / "ai_job.json")).join(["new File(", ")"])), encoding="utf-8")
        subprocess.run(["osascript", "-e", f'tell application "Adobe Illustrator" to do javascript (POSIX file "{jsx}")'], timeout=900)
        print((D / "ai_log.txt").read_text() if (D / "ai_log.txt").exists() else "（無 ai_log）")
