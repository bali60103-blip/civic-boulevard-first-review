# P15 v7 300 m「反黑」＋參考圖圖層邏輯（2026-10-15 使用者：反黑看看；依參考圖〔Paris, Caratteri morfologici / Sistema idrografico〕之圖層邏輯處理）
#   參考圖邏輯：黑底＋白色建物肌理（大型開放地全黑）→ 主體以不透明紅粗帶 → 分區以半透明紅色系「色彩增值」疊上（黑仍黑、白色建物染紅）
#               → 細紅線為線性元素 → 圖面除紅色系外不用他色 → 比例尺、指北針。
#   對應：00_反黑底圖（黑材質，建物樓高越高越白；11_p15_user_edit.py 產生）置底，隱藏 01／03 白底樓高；
#         使用者圖層 12／13／14 與 16_主角建築圖塊 改色彩增值（不透明度沿用使用者設定）；圖層 15 紅線維持不透明；
#         06_古蹟（紫）隱藏；新增 17_比例尺與指北。
#   輸入 簡報/P15_膜_v7_300m.ai（使用者手改版，不動），輸出 簡報/P15_膜_v7_300m_反黑.ai／.pdf（由輸入複製後修改）
import json, shutil, subprocess
from pathlib import Path
import fitz

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "簡報"
SRC, DST = OUT / "P15_膜_v7_300m.ai", OUT / "P15_膜_v7_300m_反黑.ai"
D = OUT / "_ai_layers" / "p15v7_300m_編修"
FL = "/System/Library/Fonts/STHeiti Light.ttc"
K = 1664 / (307545 - 300935)                    # pt／m
MAP_R, MAP_B = 128 + 1664, 128 + 520.82          # 地圖右緣、下緣（頁面 pt）
INK = (0.086, 0.086, 0.086)


def scale_north(dst):
    doc = fitz.open(); pg = doc.new_page(width=1920, height=1080); pg.insert_font(fontname="hl", fontfile=FL)
    y = MAP_B + 52; x1 = MAP_R - 40; x0 = x1 - 1000 * K
    sh = pg.new_shape(); sh.draw_line((x0, y), (x1, y))
    for m_ in (0, 250, 500, 1000):
        x = x0 + m_ * K; sh.draw_line((x, y - (5 if m_ in (0, 500, 1000) else 3)), (x, y))
    sh.finish(color=INK, width=.6); sh.commit()
    for m_, t in ((0, "0"), (500, "500"), (1000, "1 km")):
        w = fitz.Font(fontfile=FL).text_length(t, fontsize=8); pg.insert_text((x0 + m_ * K - w / 2, y - 8), t, fontsize=8, fontname="hl", color=INK)
    cx, cy, r = MAP_R - 12, y - 2, 9                 # 指北：圓＋直線（同參考圖）
    sh = pg.new_shape(); sh.draw_circle((cx, cy), r); sh.draw_line((cx, cy + r - 3), (cx, cy - r - 4)); sh.finish(color=INK, width=.7); sh.commit()
    doc.subset_fonts(); doc.save(dst, garbage=3, deflate=True)


JSX = r'''#target illustrator
(function () {
    app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS;
    var out = [], f = new File(%(dst)s);
    for (var i = app.documents.length - 1; i >= 0; i--) { try { if (app.documents[i].fullName.fsName == f.fsName) { app.documents[i].close(SaveOptions.DONOTSAVECHANGES); out.push('closed stale window'); } } catch (e) {} }   // 本檔為程式產生之複本，殘留視窗不存
    var doc = app.open(f);
    function L(n) { for (var j = 0; j < doc.layers.length; j++) if (doc.layers[j].name == n) return doc.layers[j]; return null; }
    var locks = []; for (var j = 0; j < doc.layers.length; j++) { locks.push([doc.layers[j], doc.layers[j].locked]); doc.layers[j].locked = false; }
    function place(name, pdf) {
        var ab = doc.artboards[0].artboardRect; var NL = doc.layers.add(); NL.name = name;
        var p = NL.placedItems.add(); p.file = new File(pdf); p.position = [ab[0], ab[1]]; p.embed(); return NL;
    }
    var B = place('00_反黑底圖', %(base)s); B.zOrder(ZOrderMethod.SENDTOBACK); out.push('00 at back');
    var hide = ['01_圓外建物樓高', '03_圓內建物樓高', '06_古蹟', '02_圓內黑底材質'];
    for (var h = 0; h < hide.length; h++) { var x = L(hide[h]); if (x) x.visible = false; }
    var mul = ['圖層 12', '圖層 13', '圖層 14', '16_主角建築圖塊'];
    for (var m = 0; m < mul.length; m++) { var y = L(mul[m]); if (!y) { out.push('missing ' + mul[m]); continue; }
        for (var k = 0; k < y.pageItems.length; k++) y.pageItems[k].blendingMode = BlendModes.MULTIPLY;
        out.push(mul[m] + ' multiply x' + y.pageItems.length); }
    var S = place('17_比例尺與指北', %(scale)s); out.push('17 placed');
    for (var q = 0; q < locks.length; q++) try { locks[q][0].locked = locks[q][1]; } catch (e) {}
    doc.save();
    var po = new PDFSaveOptions(); po.preserveEditability = false; doc.saveAs(new File(%(pdf)s), po);
    var names = []; for (var z = 0; z < doc.layers.length; z++) names.push(doc.layers[z].name + (doc.layers[z].visible ? '' : ' (隱藏)'));
    out.push('---'); out.push(names.join('\n'));
    doc.close(SaveOptions.DONOTSAVECHANGES);
    var lf = new File(%(log)s); lf.encoding = 'UTF-8'; lf.open('w'); lf.write(out.join('\n')); lf.close();
})();
'''

if __name__ == "__main__":
    assert (D / "00_反黑底圖.pdf").exists(), "先跑 11_p15_user_edit.py 產生 00_反黑底圖.pdf"
    scale_north(D / "17_比例尺與指北.pdf")
    shutil.copy2(SRC, DST)
    log = D / "ref_style_log.txt"
    if log.exists():
        log.unlink()
    jsx = D / "ref_style.jsx"
    jsx.write_text(JSX % {k: json.dumps(str(v)) for k, v in dict(dst=DST, base=D / "00_反黑底圖.pdf", scale=D / "17_比例尺與指北.pdf",
                                                                   pdf=OUT / "P15_膜_v7_300m_反黑.pdf", log=log).items()}, encoding="utf-8")
    r = subprocess.run(["osascript", "-e", f'tell application "Adobe Illustrator" to do javascript (POSIX file "{jsx}")'], capture_output=True, text=True, timeout=900)
    print(r.stderr.strip()[:300]); print(log.read_text(encoding="utf-8") if log.exists() else "（無 log）")
