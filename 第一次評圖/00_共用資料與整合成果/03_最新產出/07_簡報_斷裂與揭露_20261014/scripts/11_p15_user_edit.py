# P15 v7 300 m 使用者手改 AI 之後續（2026-10-15）
#   使用者在 簡報/P15_膜_v7_300m.ai 自畫圖層 12（R5 帶）、13（R3 圖塊 8 塊）、14（R1 圖塊 3 塊）、15（R7 線）。指示：
#   1. 依使用者圖塊邊緣與建物輪廓新建下一層圖塊，建物僅限主角建築 → 「16_主角建築圖塊」＝各單元主角建築（workflow 第三節）∩ 圖層 13 圖塊，
#      填 R1 酒紅 #8E1B3E（同使用者圖層 14），不透明度 90%；置於圖層 15（紅線）之下。
#   2. 色表去除 → 刪「11_色票」圖層。
#   3. 圖面反黑看看 → 另存 P15_膜_v7_300m_反黑.ai：底部加「00_反黑底圖」（全圖黑材質＋建物樓高灰階，越高越白），隱藏 01、03 兩層樓高。
#   只動指定圖層；改前備份。AI 由 Illustrator 腳本（參數路徑寫死於臨時 jsx）修改，不重組整檔。
import sys, json, math, shutil, subprocess, importlib.util, time
from pathlib import Path
import fitz
from shapely.geometry import Polygon, shape, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "簡報"
AI = OUT / "P15_膜_v7_300m.ai"
D = OUT / "_ai_layers" / "p15v7_300m_編修"; D.mkdir(parents=True, exist_ok=True)
D4 = HERE.parents[0] / "04_Z1-Z7_第一排街廓詳細平面_20261007/data"
OSM = HERE.parents[0] / "06_市民大道諾利圖_20261014/data/osm_nolli_EPSG3826.geojson"
VB = (300935, 2770000, 307545, 2771910)          # 圖幅（02_trace_overlay_nolli VIEW）
MAP_XY, MW = (128, 128), 1664
K = MW / (VB[2] - VB[0])
R1 = (0x8E / 255, 0x1B / 255, 0x3E / 255)
NTUT = box(303800, 2770570, 304110, 2770800)     # 北科大校區（以 OSM 校舍名稱範圍框定；旅館、大廈另行排除）
NOT_NTUT = ("飯店", "大廈", "翔園", "忠泰", "明日博")


def to_page(x, y):
    return (MAP_XY[0] + (x - VB[0]) * K, MAP_XY[1] + 20 + (VB[3] - y) * K)


def to_world(px, py):
    return (VB[0] + (px - MAP_XY[0]) / K, VB[3] - (py - MAP_XY[1] - 20) / K)


def bez(p0, p1, p2, p3, n=12):
    return [((1 - t) ** 3 * p0.x + 3 * (1 - t) ** 2 * t * p1.x + 3 * (1 - t) * t * t * p2.x + t ** 3 * p3.x,
             (1 - t) ** 3 * p0.y + 3 * (1 - t) ** 2 * t * p1.y + 3 * (1 - t) * t * t * p2.y + t ** 3 * p3.y) for t in [i / n for i in range(1, n + 1)]]


def user_blocks(layer="圖層 13"):
    """讀使用者圖層之填色路徑 → EPSG3826 多邊形"""
    out = []
    for dr in fitz.open(AI)[0].get_drawings():
        if dr.get("layer") != layer or dr.get("fill") is None:
            continue
        pts = []
        for it in dr["items"]:
            if it[0] == "l":
                pts += [(it[1].x, it[1].y), (it[2].x, it[2].y)] if not pts else [(it[2].x, it[2].y)]
            elif it[0] == "c":
                if not pts:
                    pts.append((it[1].x, it[1].y))
                pts += bez(*it[1:5])
            elif it[0] == "re":
                r = it[1]; pts += [(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1)]
        if len(pts) >= 3:
            out.append(Polygon([to_world(*p) for p in pts]).buffer(0))
    return out


def protagonists():
    """各單元主角建築（workflow 第三節；只取建物）"""
    G = []
    def kb(z, pred):
        return [shape(f["geometry"]) for f in json.load(open(D4 / f"Z{z}_key_buildings_EPSG3826.geojson"))["features"] if pred(f["properties"])]
    nm = lambda p: p.get("name") or ""
    G += kb(1, lambda p: p.get("tier") == "A")                                   # 河岸門戶＋北門古蹟群＋台北雙子星
    G += kb(2, lambda p: p.get("tier") == "T" or "京站" in nm(p))                 # 臺北車站、京站／轉運站（心中山為公園，不計）
    G += kb(3, lambda p: p.get("tier") == "A")                                   # U17
    G += kb(4, lambda p: p.get("tier") == "A")                                   # 司法園區 B01、華山1914
    G += kb(5, lambda p: p.get("group") in ("古蹟", "大型商場／市場"))             # 建國啤酒廠、光華
    G += [shape(f["geometry"]).buffer(0) for f in json.load(open(OSM))["features"]  # 北科大校舍
          if f["properties"]["kind"] == "building" and NTUT.contains(shape(f["geometry"]).centroid)
          and not any(s in (f["properties"].get("name") or "") for s in NOT_NTUT)]
    G += kb(6, lambda p: p.get("tier") == "A")                                   # U02／U03 與滲透場所
    G += kb(7, lambda p: p.get("tier") == "N")                                   # 夜間餐飲帶
    G += kb(8, lambda p: p.get("tier") == "A")                                   # 鐵道博物館、松菸、大巨蛋
    return [g.buffer(0) for g in G if not g.is_empty]


def poly_layer(polys, dst, fill, opacity):
    doc = fitz.open(); pg = doc.new_page(width=1920, height=1080); sh = pg.new_shape(); n = 0
    for g in polys:
        for p in getattr(g, "geoms", [g]):
            if p.geom_type != "Polygon" or p.is_empty:
                continue
            for r in [p.exterior] + list(p.interiors):
                sh.draw_polyline([fitz.Point(*to_page(*c)) for c in r.coords]); n += 1
    sh.finish(color=None, fill=fill, fill_opacity=opacity, even_odd=True, closePath=True); sh.commit()
    doc.save(dst, garbage=3, deflate=True); return n


def run_jsx(body, tag):
    log = D / f"{tag}_log.txt"
    if log.exists():
        log.unlink()
    jsx = D / f"{tag}.jsx"
    jsx.write_text("#target illustrator\n(function () {\n    app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;\n    var out = [];\n    try {\n"   # try／finally：中止（return）或出錯時仍寫 log
                   + body + f"\n    }} catch (err) {{ out.push('ERROR: ' + err + ' line ' + err.line); }} finally {{\n    var lf = new File({json.dumps(str(log))}); lf.encoding = 'UTF-8'; lf.open('w'); lf.write(out.join('\\n')); lf.close();\n    }}\n}})();\n",
                   encoding="utf-8")
    subprocess.run(["osascript", "-e", f'tell application "Adobe Illustrator" to do javascript (POSIX file "{jsx}")'], timeout=900)
    return log.read_text(encoding="utf-8") if log.exists() else "（無 log）"


OPEN_DOC = r'''
    var f = new File(%s), doc = null, opened = false;
    for (var i = 0; i < app.documents.length; i++) { try { if (app.documents[i].fullName.fsName == f.fsName) doc = app.documents[i]; } catch (e) {} }
    if (doc && !doc.saved) { out.push('ABORT: unsaved edits open in Illustrator'); return; }
    if (!doc) { doc = app.open(f); opened = true; }
    function L(n) { for (var j = 0; j < doc.layers.length; j++) if (doc.layers[j].name == n) return doc.layers[j]; return null; }
    function place(name, pdf) {
        var ab = doc.artboards[0].artboardRect; var NL = doc.layers.add(); NL.name = name;
        var p = NL.placedItems.add(); p.file = new File(pdf); p.position = [ab[0], ab[1]]; p.embed(); return NL;
    }
'''
CLOSE_DOC = r'''
    doc.save();
    var po = new PDFSaveOptions(); po.preserveEditability = false; po.viewAfterSaving = false;
    doc.saveAs(new File(%s), po);
    var names = []; for (var k = 0; k < doc.layers.length; k++) names.push(doc.layers[k].name + (doc.layers[k].visible ? '' : ' (隱藏)'));
    out.push('---'); out.push(names.join('\n'));
    doc.close(SaveOptions.DONOTSAVECHANGES);
    if (!opened) app.open(new File(%s));
'''

if __name__ == "__main__":
    stamp = time.strftime("%H%M")
    shutil.copy2(AI, OUT / f"P15_膜_v7_300m_備份_{stamp}.ai")
    # 1. 主角建築圖塊
    blocks = user_blocks("圖層 13")
    U = unary_union(blocks)
    P = protagonists()
    T = [g.intersection(U) for g in P if g.intersects(U)]
    T = [g for g in T if g.area >= 5]
    n = poly_layer([unary_union(T)], D / "16_主角建築圖塊.pdf", R1, .9)
    print(f"使用者 R3 圖塊 {len(blocks)} 塊；主角建築 {len(P)} 棟，落在圖塊內 {len(T)} 片、{sum(g.area for g in T) / 1e4:.2f} ha；路徑 {n}")
    # 2+1. 修改使用者 AI：加 16（置於圖層 15 之下）、刪 11_色票
    body = (OPEN_DOC % json.dumps(str(AI))) + f'''
    var NL = place('16_主角建築圖塊', {json.dumps(str(D / "16_主角建築圖塊.pdf"))});
    var top = L('圖層 15'); if (top) NL.move(top, ElementPlacement.PLACEAFTER); out.push('16 placed below 圖層 15');
    var sw = L('11_色票'); if (sw) {{ sw.locked = false; sw.visible = true; sw.remove(); out.push('11_色票 removed'); }} else out.push('11_色票 not found');
''' + (CLOSE_DOC % (json.dumps(str(OUT / "P15_膜_v7_300m_編修.pdf")), json.dumps(str(AI))))
    print(run_jsx(body, "edit_main"))
    # 3. 反黑版：複製後加底圖、隱藏 01／03
    S4 = importlib.util.module_from_spec(spec := importlib.util.spec_from_file_location("s4", HERE / "scripts/04_slides.py")); spec.loader.exec_module(S4)
    m = S4.Map(S4.VIEW, S4.CW)
    tex = S4.ImageOps.colorize(S4.grain(int(m.frame.width * 2), int(m.frame.height * 2)), black=(0, 0, 0), white=(90, 90, 90))
    import io
    jb = io.BytesIO(); tex.save(jb, "JPEG", quality=86); m.page.insert_image(m.frame, stream=jb.getvalue())
    V = S4.VIEW.buffer(5)
    HL = S4.height_layers([g.intersection(V) for g in S4.NL.PRIV + S4.NL.PUB if g.intersects(V)])
    for k in sorted(HL):
        m.poly([unary_union(HL[k])], fill=S4.h_gray(k))
    mp = m.save("p15_v7_300m_反黑底圖")
    doc = fitz.open(); pg = doc.new_page(width=1920, height=1080)
    src = fitz.open(mp); pg.show_pdf_page(fitz.Rect(MAP_XY[0], MAP_XY[1], MAP_XY[0] + src[0].rect.width, MAP_XY[1] + src[0].rect.height), src, 0)
    doc.save(D / "00_反黑底圖.pdf", garbage=3, deflate=True); Path(mp).unlink()
    BL = OUT / "P15_膜_v7_300m_反黑.ai"
    shutil.copy2(AI, BL)
    body = (OPEN_DOC % json.dumps(str(BL))) + f'''
    var NL = place('00_反黑底圖', {json.dumps(str(D / "00_反黑底圖.pdf"))});
    NL.move(doc.layers[doc.layers.length - 1], ElementPlacement.PLACEAFTER); out.push('00 placed at bottom');
    var a = L('01_圓外建物樓高'); if (a) a.visible = false;
    var b = L('03_圓內建物樓高'); if (b) b.visible = false;
''' + (CLOSE_DOC % (json.dumps(str(OUT / "P15_膜_v7_300m_反黑.pdf")), json.dumps("")))
    body = body.replace("    if (!opened) app.open(new File(\"\"));\n", "")
    print(run_jsx(body, "edit_black"))
