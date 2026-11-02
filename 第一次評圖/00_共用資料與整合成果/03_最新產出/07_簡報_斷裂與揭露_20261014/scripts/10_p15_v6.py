# P15 v6（2026-10-15 使用者）：圓外反白、圓內反黑、取消圓內酒紅；色票放在圖旁空白處；出 PDF 與 AI（200 m、300 m）
#   build R：04_slides.fig_membrane_walk(v6=True) 分層地圖 → 1920×1080 頁之分層 PDF（＋古蹟標注、色票）→ 合成 PDF
#   ai R   ：以 Illustrator（06_assemble_layers.jsx）把分層 PDF 由下而上置入成具名圖層，存 AI
#   輸出：簡報/P15_膜_v6_{R}m.pdf、.ai；分層 簡報/_ai_layers/p15v6_{R}m/
#   用法：python3 10_p15_v6.py build 200；python3 10_p15_v6.py ai 200 300（加 v7：圓內建物輪廓套樓層、步行圈淺灰虛線；輸出 P15_膜_v7_*）
import sys, json, shutil, subprocess, importlib.util
from pathlib import Path
import fitz

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "簡報"
SW, SH = 1920, 1080
VER = 6
MAP_XY = (128, 128)                     # 地圖左上角（頁面 pt）；地圖 1664 × 520.8
FL, FM = "/System/Library/Fonts/STHeiti Light.ttc", "/System/Library/Fonts/STHeiti Medium.ttc"
INK, MUTED = (0.086, 0.086, 0.086), (0.42, 0.42, 0.40)
S_FL = fitz.Font(fontfile=FL)


def load(name, fn):
    spec = importlib.util.spec_from_file_location(name, HERE / "scripts" / fn)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def on_slide(src_pdf, dst_pdf, rect):
    doc = fitz.open(); pg = doc.new_page(width=SW, height=SH); pg.show_pdf_page(rect, fitz.open(src_pdf), 0)
    doc.save(dst_pdf, garbage=3, deflate=True)


def swatch_layer(dst_pdf, y0):
    """色票：酒紅→正紅 7 階（09_red_palette.py）＋圓外樓高灰階 8 級（越高越黑，同 04 h_gray_inv）"""
    P = load("pal", "09_red_palette.py")
    doc = fitz.open(); pg = doc.new_page(width=SW, height=SH)
    pg.insert_font(fontname="hl", fontfile=FL); pg.insert_font(fontname="hm", fontfile=FM)
    x0 = MAP_XY[0]
    pg.insert_text((x0, y0), "色票｜酒紅 → 正紅（OKLab 等距 7 階）", fontsize=14, fontname="hm", color=INK)
    sw, sh_ = 92, 56
    for i, (nm, hx, c, k, d) in enumerate(P.rows):
        x = x0 + i * (sw + 8)
        s = pg.new_shape(); s.draw_rect(fitz.Rect(x, y0 + 14, x + sw, y0 + 14 + sh_)); s.finish(color=None, fill=tuple(v / 255 for v in c)); s.commit()
        pg.insert_text((x, y0 + 14 + sh_ + 16), nm, fontsize=11, fontname="hm", color=INK)
        pg.insert_text((x, y0 + 14 + sh_ + 30), hx, fontsize=10, fontname="hl", color=MUTED)
        pg.insert_text((x, y0 + 14 + sh_ + 43), "RGB %d %d %d" % c, fontsize=9, fontname="hl", color=MUTED)
    gx = x0 + 7 * (sw + 8) + 56
    n = len(P.H_CLASSES); gw = (SW - MAP_XY[0] - gx) / n
    if VER >= 7:   # 圓外（白底，越高越黑）與圓內（黑底，越高越白）兩列；列名放在灰階左側欄
        pg.insert_text((gx, y0), "樓高（臺北三維模型 2017）", fontsize=14, fontname="hm", color=INK)
        hh, lx = 27, gx; gx = gx + 84; gw = (SW - MAP_XY[0] - gx) / n
        for row, (lab, inv) in enumerate((("圓外：越高越黑", True), ("圓內：越高越白", False))):
            yy = y0 + 14 + row * (hh + 2)
            for i in range(n):
                g_ = 0.14 + 0.86 * i / (n - 1); v = 1 - g_ if inv else g_; x = gx + i * gw
                s = pg.new_shape(); s.draw_rect(fitz.Rect(x, yy, x + gw - 6, yy + hh)); s.finish(color=(.6, .6, .6), width=.3, fill=(v, v, v)); s.commit()
            pg.insert_text((lx, yy + hh / 2 + 4), lab, fontsize=10, fontname="hl", color=INK)
        for i, (_, nm) in enumerate(P.H_CLASSES):
            pg.insert_text((gx + i * gw, y0 + 14 + 2 * hh + 2 + 16), nm.split("（")[0], fontsize=10, fontname="hl", color=INK)
        doc.subset_fonts(); doc.save(dst_pdf, garbage=3, deflate=True); return
    pg.insert_text((gx, y0), "樓高（圓外；臺北三維模型 2017，越高越黑）", fontsize=14, fontname="hm", color=INK)
    for i, (_, nm) in enumerate(P.H_CLASSES):
        v = 1 - (0.14 + 0.86 * i / (n - 1)); x = gx + i * gw
        s = pg.new_shape(); s.draw_rect(fitz.Rect(x, y0 + 14, x + gw - 6, y0 + 14 + sh_)); s.finish(color=(.6, .6, .6), width=.3, fill=(v, v, v)); s.commit()
        pg.insert_text((x, y0 + 14 + sh_ + 16), nm.split("（")[0], fontsize=10, fontname="hl", color=INK)
        pg.insert_text((x, y0 + 14 + sh_ + 30), "#%02X%02X%02X" % ((round(v * 255),) * 3), fontsize=9, fontname="hl", color=MUTED)
    doc.subset_fonts(); doc.save(dst_pdf, garbage=3, deflate=True)


def relayout(R):
    """只重做色票層與合成頁（地圖各層沿用）"""
    D = OUT / "_ai_layers" / f"p15v{VER}_{R}m"; job = json.load(open(D / "ai_job.json"))
    swatch_layer(Path(next(q for k, q in job["layers"] if k.endswith("_色票"))), MAP_XY[1] + 520.82 + 64)
    comp = fitz.open(); pg = comp.new_page(width=SW, height=SH)
    for _, q in job["layers"]:
        pg.show_pdf_page(pg.rect, fitz.open(q), 0)
    out = OUT / f"P15_膜_v{VER}_{R}m.pdf"; comp.set_metadata({"title": f"P15 膜 v{VER} {R} m"}); comp.save(out, garbage=4, deflate=True)
    comp[0].get_pixmap(dpi=72).save(OUT / "_預覽" / f"P15_膜_v{VER}_{R}m.jpg"); print(out)


def build(R):
    S4 = load("s4", "04_slides.py"); L8 = load("l8", "08_label_heritage.py")
    D = OUT / "_ai_layers" / f"p15v{VER}_{R}m"; D.mkdir(parents=True, exist_ok=True)
    maps = S4.fig_membrane_walk(f"p15_membrane_v{VER}_{R}m", R, deform=False, v6=VER == 6, v7=VER == 7)
    mw, mh = fitz.open(maps[0][1])[0].rect.width, fitz.open(maps[0][1])[0].rect.height
    rect = fitz.Rect(MAP_XY[0], MAP_XY[1], MAP_XY[0] + mw, MAP_XY[1] + mh)
    layers = []
    for k, p in maps:
        q = D / f"{k}.pdf"; on_slide(p, q, rect); Path(p).unlink(); layers.append((k, q))
    # 古蹟標注（地圖座標）
    lab = fitz.open(); pg = lab.new_page(width=mw, height=mh)
    b = S4.VIEW.bounds; kk = mw / (b[2] - b[0])
    n, nl = L8.draw_labels(pg, lambda x, y: fitz.Point((x - b[0]) * kk, 20 + (b[3] - y) * kk), fitz.Rect(0, 20, mw, mh - 20), S4.FL, S4.INK, S4.HER_C)
    tmp = D / "_lab_map.pdf"; lab.subset_fonts(); lab.save(tmp)
    nl_ = f"{len(layers) + 1:02d}_古蹟標注"; q = D / f"{nl_}.pdf"; on_slide(tmp, q, rect); tmp.unlink(); layers.append((nl_, q))
    ns_ = f"{len(layers) + 1:02d}_色票"; q = D / f"{ns_}.pdf"; swatch_layer(q, rect.y1 + 64); layers.append((ns_, q))
    comp = fitz.open(); pg = comp.new_page(width=SW, height=SH)
    for _, q in layers:
        pg.show_pdf_page(pg.rect, fitz.open(q), 0)
    out = OUT / f"P15_膜_v{VER}_{R}m.pdf"; comp.set_metadata({"title": f"P15 膜 v{VER} {R} m"}); comp.save(out, garbage=4, deflate=True)
    comp[0].get_pixmap(dpi=72).save(OUT / "_預覽" / f"P15_膜_v{VER}_{R}m.jpg")
    json.dump({"w_mm": SW * 25.4 / 72, "h_mm": SH * 25.4 / 72, "layers": [[k, str(q)] for k, q in layers],
               "out": str(OUT / f"P15_膜_v{VER}_{R}m.ai"), "log": str(D / "ai_log.txt")}, open(D / "ai_job.json", "w"), ensure_ascii=False)
    print(out, f"標注 {n}（引線 {nl}）；圖層 {len(layers)}")


def ai(R):
    # 06_assemble_layers.jsx 固定讀同目錄 ai_job.json（桌面 P15 專案用）；此處另寫一份把參數檔路徑寫死的 jsx，絕不落回預設檔
    D = OUT / "_ai_layers" / f"p15v{VER}_{R}m"
    # 使用者會直接在產出的 AI 上加圖層（2026-10-15 300 m 加了圖層 12–15）：AI 在上次組裝之後被改過，就另存「_新版」，不覆蓋
    job = json.load(open(D / "ai_job.json")); ai_ = Path(job["out"]).with_name(Path(job["out"]).name.replace("_新版", ""))
    stamp = D / "ai_built.txt"
    if ai_.exists() and (not stamp.exists() or ai_.stat().st_mtime > stamp.stat().st_mtime + 5):
        job["out"] = str(ai_.with_name(ai_.stem + "_新版.ai")); print("AI 已被手動修改，另存", job["out"])
    else:
        job["out"] = str(ai_)
    json.dump(job, open(D / "ai_job.json", "w"), ensure_ascii=False)
    src = (HERE / "scripts/06_assemble_layers.jsx").read_text(encoding="utf-8")
    old = "new File($.fileName.replace(/[^\\/]+$/, '') + 'ai_job.json')"
    assert src.count(old) == 1, "06_assemble_layers.jsx 參數檔那行已變更"
    # json.dumps 預設以 \uXXXX 跳脫中文路徑，免 ExtendScript 讀檔編碼問題
    jsx = D / "assemble.jsx"; jsx.write_text(src.replace(old, json.dumps(str(D / "ai_job.json")).join(["new File(", ")"])), encoding="utf-8")
    r = subprocess.run(["osascript", "-e", f'tell application "Adobe Illustrator" to do javascript (POSIX file "{jsx}")'], capture_output=True, text=True, timeout=900)
    print(R, "osascript", r.returncode, r.stderr.strip()[:300])
    log = D / "ai_log.txt"; print(log.read_text() if log.exists() else "（無 ai_log）")
    if Path(job["out"]) == ai_ and ai_.exists():
        stamp.write_text(str(ai_.stat().st_mtime))


if __name__ == "__main__":
    args = sys.argv[1:]
    if "v7" in args:
        VER = 7; args.remove("v7")
    cmd, *Rs = args
    for R in map(int, Rs):
        {"build": build, "ai": ai, "relayout": relayout}[cmd](R)
