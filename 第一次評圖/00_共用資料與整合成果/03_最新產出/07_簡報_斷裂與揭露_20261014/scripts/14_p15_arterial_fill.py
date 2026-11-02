# P15 v7 300 m：幹道著色、線改透明（2026-10-15 使用者）
#   幹道＝01_trace_overlay.arterials（OSM 中心線；雙向分隔者兩條）。路面範圍：沿中心線每 SAMPLE m，向左右垂直打線至最近建物（諾利底圖），
#   各線各側排除 0 與未碰建物者後取中位數為寬（限 MIN–MAX m；建物用 OSM 單棟），單側緩衝後聯集＝街道空間（含人行道至建物立面；雙向分隔之中央一併填滿）。
#   填色＝紅色系統一單位（R5、不透明度 28%、色彩增值），無邊線。路名與圖框另成一層。
#   AI：刪「24_幹道與路名（紅）」，加「24_幹道（紅）」（置於視域三之下）與「25_路名與圖框」（置於圖層 15 之下）。改前備份。
import sys, json, math, time, shutil, importlib.util
from pathlib import Path
import numpy as np
import shapely
import fitz
from shapely.geometry import LineString, Point
from shapely.ops import unary_union
from shapely.strtree import STRtree

HERE = Path(__file__).resolve().parents[1]
SAMPLE, PROBE, MIN_W, MAX_W = 6, 50, 4, 30   # 各側：排除 0（中心線在高架／建物下）與 PROBE（路口、空地未碰建物）後取中位數


def load(name, fn):
    spec = importlib.util.spec_from_file_location(name, HERE / "scripts" / fn)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


V13 = load("v13", "13_p15_viewfield.py"); E = V13.E


def side_dist(line, blds, tree):
    """沿線各取樣點，左右垂直至最近建物之距離（無則 PROBE）；回傳左、右中位數"""
    L, R = [], []
    for t in np.arange(SAMPLE / 2, line.length, SAMPLE):
        p, q = line.interpolate(t), line.interpolate(min(t + 1, line.length))
        if q.equals(p):
            q = line.interpolate(max(t - 1, 0)); dx, dy = p.x - q.x, p.y - q.y
        else:
            dx, dy = q.x - p.x, q.y - p.y
        n = math.hypot(dx, dy) or 1; nx, ny = -dy / n, dx / n          # 左法向
        for sgn, acc in ((1, L), (-1, R)):
            ray = LineString([(p.x, p.y), (p.x + sgn * nx * PROBE, p.y + sgn * ny * PROBE)])
            hits = [blds[i] for i in tree.query(ray, predicate="intersects")]
            acc.append(min([d for d in (p.distance(ray.intersection(h)) for h in hits) if np.isfinite(d)], default=PROBE))   # 交集為空時距離為 NaN
    def med(a):
        v = [d for d in a if 0.5 < d < PROBE - 0.5]
        return float(np.median(v)) if len(v) >= 3 else MIN_W
    return med(L), med(R)


def road_surface_uniform(T1, VIEW):
    """精簡版（2026-10-15 使用者：有鋸齒狀的就刪掉）：每條幹道一個寬度 W＝各中心線（左＋右至建物距離）之長度加權中位數；
    雙向分隔者（同名另一條中心線在 60 m 內）扣兩線間距 s，各線緩衝 (W − s)／2，圓角接合 → 平順等寬帶。"""
    from shapely.geometry import shape
    OSM = HERE.parents[0] / "06_市民大道諾利圖_20261014/data/osm_nolli_EPSG3826.geojson"
    blds = [shape(f["geometry"]).buffer(0) for f in json.load(open(OSM))["features"] if f["properties"]["kind"] == "building"]
    blds = [g for g in blds if g.intersects(VIEW.buffer(PROBE))]; tree = STRtree(blds)
    polys, rep = [], []
    for key, g, *_ in T1.arterials(VIEW):
        lines = [l for l in getattr(g, "geoms", [g]) if l.geom_type == "LineString" and l.length >= 10]
        tot, wts = [], []
        for line in lines:
            l, r = side_dist(line, blds, tree)
            if l > MIN_W and r > MIN_W:
                tot.append(l + r); wts.append(line.length)
        if not tot:
            continue
        order = np.argsort(tot); cw = np.cumsum(np.array(wts)[order]); W = float(np.array(tot)[order][np.searchsorted(cw, cw[-1] / 2)])
        W = min(max(W, 12), 60)
        from shapely.ops import nearest_points
        ds = []                                                   # 對向車道間距（整條幹道一個值）：只算側向之同名線
        for line in lines:
            others = unary_union([o for o in lines if o is not line])
            if others.is_empty:
                continue
            for t in np.arange(5, line.length - 5, 15):
                p_ = line.interpolate(t); a_ = line.interpolate(max(t - 2, 0)); b_ = line.interpolate(min(t + 2, line.length))
                ux, uy = b_.x - a_.x, b_.y - a_.y; un = math.hypot(ux, uy) or 1
                q_ = nearest_points(p_, others)[1]; vx, vy = q_.x - p_.x, q_.y - p_.y; vn = math.hypot(vx, vy)
                if 3 < vn < 60 and abs(ux * vy - uy * vx) / (un * vn) > 0.8:
                    ds.append(vn)
        sep = float(np.median(ds)) if len(ds) >= 5 else 0.0
        d = max((W - sep) / 2, 4); c = sep / 2 + 4                # 閉合半徑：填滿分隔島、磨平接頭
        band_ = unary_union([l.buffer(d, cap_style="flat", join_style="round") for l in lines])
        polys.append(band_.buffer(c, join_style="round").buffer(-c, join_style="round"))
        rep.append((key, round(W)))
    surf = V13.inter(unary_union(polys).buffer(2).buffer(-2).simplify(0.5), VIEW)
    return surf, rep


def road_surface(T1, VIEW):
    from shapely.geometry import shape
    OSM = HERE.parents[0] / "06_市民大道諾利圖_20261014/data/osm_nolli_EPSG3826.geojson"
    blds = [shape(f["geometry"]).buffer(0) for f in json.load(open(OSM))["features"] if f["properties"]["kind"] == "building"]
    blds = [g for g in blds if g.intersects(VIEW.buffer(PROBE))]; tree = STRtree(blds)
    polys, rep = [], []
    for key, g, *_ in T1.arterials(VIEW):
        for line in getattr(g, "geoms", [g]):
            if line.geom_type != "LineString" or line.length < 10:
                continue
            l, r = side_dist(line, blds, tree)
            l, r = (min(max(v, MIN_W), MAX_W) for v in (l, r))
            polys += [line.buffer(l, single_sided=True, cap_style="flat"), line.buffer(-r, single_sided=True, cap_style="flat")]
            rep.append((key, round(l + r)))
    surf = V13.inter(unary_union(polys).buffer(1).buffer(-1), VIEW)   # 不扣建物（扣了邊緣成鋸齒）；寬度已取至建物立面
    return surf, rep


if __name__ == "__main__":
    from shapely.geometry import box
    T1 = load("t1", "01_trace_overlay.py"); VIEW = box(*E.VB)
    surf, rep = (road_surface_uniform if "uniform" in sys.argv else road_surface)(T1, VIEW)
    import collections
    agg = collections.defaultdict(list)
    for k, w in rep:
        agg[k].append(w)
    print("幹道路面", round(surf.area / 1e4, 1), "ha；各幹道寬（中位數，m）", {k: int(np.median(v)) for k, v in agg.items()})
    E.poly_layer([surf], E.D / "24_幹道（紅）.pdf", V13.R5, 1.0)
    if not (E.D / "25_路名與圖框.pdf").exists():                              # 只留路名與圖框（線透明）；需 04_slides（載入約 2.5 分）
        S4 = load("s4", "04_slides.py"); m = S4.Map(S4.VIEW, S4.CW); m.finish(dash=None, lab_col=S4.INK)
        mp = m.save("p15_v7_300m_路名"); doc = fitz.open(); pg = doc.new_page(width=1920, height=1080); src = fitz.open(mp)
        pg.show_pdf_page(fitz.Rect(E.MAP_XY[0], E.MAP_XY[1], E.MAP_XY[0] + src[0].rect.width, E.MAP_XY[1] + src[0].rect.height), src, 0)
        doc.save(E.D / "25_路名與圖框.pdf", garbage=3, deflate=True); Path(mp).unlink()
    if "dry" in sys.argv:
        d = fitz.open(E.AI); p = d[0]; p.show_pdf_page(p.rect, fitz.open(E.D / "24_幹道（紅）.pdf"), 0)
        p.get_pixmap(dpi=70).save(E.D / "_dry_art.png"); print("dry"); sys.exit()
    shutil.copy2(E.AI, E.OUT / f"P15_膜_v7_300m_備份_{time.strftime('%H%M')}.ai")
    body = (E.OPEN_DOC % json.dumps(str(E.AI))) + f'''
    var locks = []; for (var j = 0; j < doc.layers.length; j++) {{ locks.push([doc.layers[j].name, doc.layers[j].locked]); doc.layers[j].locked = false; }}
    var old = L('24_幹道與路名（紅）'); if (old) {{ old.remove(); out.push('removed old 24'); }}
    var A = place('24_幹道（紅）', {json.dumps(str(E.D / "24_幹道（紅）.pdf"))}); A.move(L('23_視域三'), ElementPlacement.PLACEAFTER);
    for (var k = 0; k < A.pageItems.length; k++) {{ A.pageItems[k].opacity = {V13.ALPHA}; A.pageItems[k].blendingMode = BlendModes.MULTIPLY; }}
    var N = place('25_路名與圖框', {json.dumps(str(E.D / "25_路名與圖框.pdf"))}); N.move(L('圖層 15'), ElementPlacement.PLACEAFTER);
    for (var q = 0; q < locks.length; q++) {{ var LL = L(locks[q][0]); if (LL) LL.locked = locks[q][1]; }}
''' + (E.CLOSE_DOC % (json.dumps(str(E.OUT / "P15_膜_v7_300m_編修.pdf")), json.dumps(str(E.AI))))
    print(E.run_jsx(body, "arterial"))
