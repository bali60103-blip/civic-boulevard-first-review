# P15 v7 300 m 白底（不反黑）：色彩增值改為「進入大街廓的視域擴展」（2026-10-15 使用者）
#   紅色系統＝同一單位淡紅（R5 #C8132B，不透明度 ALPHA，色彩增值）逐層疊加，疊越多越深；最淺＝使用者最外圍色塊（圖層 12），
#   最深＝建物輪廓（使用者圖層 14 與 16_主角建築圖塊，R1 不透明）。中間各層（皆裁於圖層 12 之內）：
#     圖層 13（使用者 R3 圖塊）＋1；20_現有基地（公共案件基地 tier B、園區戶外空間 tier O、公共案件 site）＋1；
#     21／22／23 視域（視覺步深，自市民大道起算）：大街廓（OSM 平面道路圍成、≥ BIG_HA 公頃）內，站在市民大道（每 STEP m 一視點）看得見者＝一層；
#       走入一層範圍後（其內每 GRID m 一視點，至多 500 點）新增可見者＝二層；再走入＝三層。累加：21＝一＋二＋三、22＝二＋三、23＝三，
#       越深入街廓越深。遮擋＝諾利底圖建物（私有＋公共）；視線長 RAY m、每點 NRAY 條。
#   幹道納入紅色系統：24_幹道與路名（紅）＝幹道中心線 R5 實線，路名同原；隱藏 09_幹道虛線與路名。
#   只動指定圖層；改前備份。AI 由 Illustrator 腳本修改（路徑寫死於臨時 jsx）。
import sys, json, math, shutil, subprocess, importlib.util, time, random
from pathlib import Path
import numpy as np
import shapely, shapely.prepared
import fitz
from shapely.geometry import Point, LineString, Polygon, box, shape
from shapely.ops import unary_union, polygonize
from shapely.strtree import STRtree

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "簡報"; AI = OUT / "P15_膜_v7_300m.ai"
D = OUT / "_ai_layers" / "p15v7_300m_編修"; D.mkdir(parents=True, exist_ok=True)
D4 = HERE.parents[0] / "04_Z1-Z7_第一排街廓詳細平面_20261007/data"
PUB = HERE.parents[1] / "02_調整過程/公共都更編號圖/公共案件量體與基地_EPSG3826.geojson"
BIG_HA, STEP, GRID, RAY, NRAY, ALPHA = 2.0, 12, 18, 220, 144, 28
R5 = (0xC8 / 255, 0x13 / 255, 0x2B / 255)


def load(name, fn):
    spec = importlib.util.spec_from_file_location(name, HERE / "scripts" / fn)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


E = load("e11", "11_p15_user_edit.py")      # user_blocks、to_page、poly_layer、OPEN_DOC


def isovists(pts, blds, tree):
    """各視點之可視多邊形：每點 NRAY 條射線，以 STRtree 找出射線碰到之建物，取最近命中距離（向量化）"""
    out = []
    ang = np.linspace(0, 2 * math.pi, NRAY, endpoint=False); ca, sa = np.cos(ang), np.sin(ang)
    for p in pts:
        if len(tree.query(p, predicate="intersects")):
            continue
        rays = shapely.linestrings(np.stack([np.stack([np.full(NRAY, p.x), np.full(NRAY, p.y)], 1),
                                             np.stack([p.x + RAY * ca, p.y + RAY * sa], 1)], 1))
        ri, bi = tree.query(rays, predicate="intersects")
        d = np.full(NRAY, float(RAY))
        if len(ri):
            np.minimum.at(d, ri, shapely.distance(p, shapely.intersection(rays[ri], blds[bi])))
        out.append(Polygon(np.stack([p.x + d * ca, p.y + d * sa], 1)).buffer(0))
    return clean(unary_union(out)) if out else Polygon()


def polys(g):
    """只留面（精度化後可能產生線、點之退化部分，疊合運算不接受混合維度）"""
    ps = [q for q in shapely.get_parts(g) if q.geom_type in ("Polygon", "MultiPolygon") and not q.is_empty]
    ps = [r for q in ps for r in shapely.get_parts(q)]
    return shapely.MultiPolygon(ps) if ps else Polygon()


def clean(g):
    return polys(shapely.set_precision(polys(g).buffer(0), 0.05))


GS = 0.05   # 疊合運算精度網格（避免 TopologyException）
inter = lambda a, b: polys(shapely.intersection(clean(a), clean(b), grid_size=GS))
diff = lambda a, b: polys(shapely.difference(clean(a), clean(b), grid_size=GS))


def grid_in(area, step, cap=500, seed=1):
    if area.is_empty:
        return []
    b = area.bounds; pts = []; pa = shapely.prepared.prep(area)
    for x in np.arange(b[0] + step / 2, b[2], step):
        for y in np.arange(b[1] + step / 2, b[3], step):
            q = Point(x, y)
            if pa.contains(q):
                pts.append(q)
    random.Random(seed).shuffle(pts); return pts[:cap]


def viewfields(S4, band):
    """視覺步深（space syntax visual step depth）自市民大道起算，只取大街廓內：
    一層＝站在市民大道（平面道路中心線，每 STEP m 一視點）看得進大街廓之範圍；二層＝走入一層範圍後新看見者；三層＝再走入。"""
    roads = S4.osm_roads()
    blocks = [b for b in polygonize(unary_union([g for g, p in roads if p["highway"] in S4.BLOCK_HW])) if b.area >= BIG_HA * 1e4 and b.intersects(band)]
    BLK = inter(clean(unary_union(blocks)), clean(band))
    blds = np.array([g.buffer(0) for g in S4.NL.PRIV + S4.NL.PUB if g.intersects(band.buffer(RAY))]); tree = STRtree(blds)
    free = diff(BLK, clean(unary_union(list(blds))))
    blvd = [g for g, p in roads if "市民大道" in (p.get("name") or "") and g.intersects(band.buffer(30))]
    pts0 = [l.interpolate(t) for g in blvd for l in getattr(g, "geoms", [g]) for t in np.arange(0, l.length, STEP)]
    print(f"大街廓 {len(blocks)} 個（≥ {BIG_HA} ha，{BLK.area / 1e4:.1f} ha 在色塊內）；市民大道視點 {len(pts0)}")
    s1 = inter(isovists(pts0, blds, tree), free)
    s2 = diff(inter(isovists(grid_in(s1, GRID), blds, tree), free), s1)
    s12 = polys(shapely.union(clean(s1), clean(s2), grid_size=GS))
    s3 = diff(inter(isovists(grid_in(s2, GRID, seed=2), blds, tree), free), s12)
    return blocks, s1, s2, s3


def sites(band):
    G = []
    for z in range(1, 9):
        G += [shape(f["geometry"]) for f in json.load(open(D4 / f"Z{z}_key_buildings_EPSG3826.geojson"))["features"] if f["properties"].get("tier") in ("B", "O")]
    G += [shape(f["geometry"]) for f in json.load(open(PUB))["features"] if f["properties"].get("layer") == "site"]
    return unary_union([g.buffer(0) for g in G]).intersection(band)


def arterial_layer(S4, dst):
    m = S4.Map(S4.VIEW, S4.CW)
    m.finish(dash=R5, dw=1.0, dop=1.0, lab_col=S4.INK, dpat=None)
    mp = m.save("p15_v7_300m_幹道紅")
    doc = fitz.open(); pg = doc.new_page(width=1920, height=1080); src = fitz.open(mp)
    pg.show_pdf_page(fitz.Rect(E.MAP_XY[0], E.MAP_XY[1], E.MAP_XY[0] + src[0].rect.width, E.MAP_XY[1] + src[0].rect.height), src, 0)
    doc.save(dst, garbage=3, deflate=True); Path(mp).unlink()


if __name__ == "__main__":
    dry = "dry" in sys.argv
    band = unary_union(E.user_blocks("圖層 12"))
    S4 = load("s4", "04_slides.py")
    t0 = time.time()
    blocks, v1, v2, v3 = viewfields(S4, band)
    st = sites(band)
    print(f"大街廓 {len(blocks)} 個（≥ {BIG_HA} ha）；視域一 {v1.area / 1e4:.1f}、二 {v2.area / 1e4:.1f}、三 {v3.area / 1e4:.1f} ha；現有基地 {st.area / 1e4:.1f} ha；{time.time() - t0:.0f}s")
    L = {"20_現有基地": st, "21_視域一": unary_union([v1, v2, v3]), "22_視域二": unary_union([v2, v3]), "23_視域三": v3}
    for k, g in L.items():
        E.poly_layer([g], D / f"{k}.pdf", R5, 1.0)
    arterial_layer(S4, D / "24_幹道與路名（紅）.pdf")
    if dry:
        doc = fitz.open(AI); pg = doc[0]
        for k in list(L) + ["24_幹道與路名（紅）"]:
            pg.show_pdf_page(pg.rect, fitz.open(D / f"{k}.pdf"), 0)
        pg.get_pixmap(dpi=80).save(D / "_dry.png"); print("dry", D / "_dry.png"); sys.exit()
    shutil.copy2(AI, OUT / f"P15_膜_v7_300m_備份_{time.strftime('%H%M')}.ai")
    places = "".join(f"    place('{k}', {json.dumps(str(D / (k + '.pdf')))});\n" for k in L)
    body = (E.OPEN_DOC % json.dumps(str(AI))) + places + f'''
    var locks = []; for (var j = 0; j < doc.layers.length; j++) {{ locks.push([doc.layers[j].name, doc.layers[j].locked]); doc.layers[j].locked = false; }}   // 使用者鎖定之圖層：暫解，最後還原
    var t14 = L('圖層 14');
    var order = ['23_視域三', '22_視域二', '21_視域一', '20_現有基地'];
    for (var o = 0; o < order.length; o++) {{ var x = L(order[o]); x.move(t14, ElementPlacement.PLACEAFTER);
        for (var k = 0; k < x.pageItems.length; k++) {{ x.pageItems[k].opacity = {ALPHA}; x.pageItems[k].blendingMode = BlendModes.MULTIPLY; }} }}
    var A = place('24_幹道與路名（紅）', {json.dumps(str(D / "24_幹道與路名（紅）.pdf"))}); A.move(L('圖層 15'), ElementPlacement.PLACEAFTER);
    var old = L('09_幹道虛線與路名'); if (old) old.visible = false;
    var tiers = ['圖層 12', '圖層 13'];
    for (var t = 0; t < tiers.length; t++) {{ var y = L(tiers[t]); var lk = y.locked; y.locked = false;
        for (var k = 0; k < y.pageItems.length; k++) {{ out.push(tiers[t] + ' item ' + k + ' opacity ' + Math.round(y.pageItems[k].opacity) + ' -> {ALPHA} multiply');
            y.pageItems[k].opacity = {ALPHA}; y.pageItems[k].blendingMode = BlendModes.MULTIPLY; }} y.locked = lk; }}
    var deep = ['圖層 14', '16_主角建築圖塊'];
    for (var t = 0; t < deep.length; t++) {{ var y = L(deep[t]); var lk = y.locked; y.locked = false;
        for (var k = 0; k < y.pageItems.length; k++) {{ y.pageItems[k].opacity = 100; y.pageItems[k].blendingMode = BlendModes.NORMAL; }} y.locked = lk; }}
    for (var q = 0; q < locks.length; q++) {{ var LL = L(locks[q][0]); if (LL) LL.locked = locks[q][1]; }}
''' + (E.CLOSE_DOC % (json.dumps(str(OUT / "P15_膜_v7_300m_編修.pdf")), json.dumps(str(AI)))).replace("    if (!opened) app.open", "    app.open")
    print(E.run_jsx(body, "viewfield"))
