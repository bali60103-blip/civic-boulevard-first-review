# P15 v3 古蹟標注（2026-10-15 使用者：200 m 圖上簡單標注）
#   讀 data/P15_沿線古蹟點位.csv 之圓心，於既有圖（_圖/<名>.pdf）上加圓心點與簡稱，另存 <名>_label.pdf，不覆蓋原圖。
#   標籤以貪婪法避讓：依擁擠程度排序，候選位置為圓心周圍 8 方向 × 5 圈，取第一個不與已放標籤／圓心點重疊者；離開第一圈者加引線。
#   用法：python3 08_label_heritage.py p15_membrane_v3_200m p15_membrane_v3_200m_circle
import sys, csv, math, importlib.util
from pathlib import Path
import fitz

HERE = Path(__file__).resolve().parents[1]
S4 = None   # 04_slides 延遲載入（10_p15_v6.py 呼叫 draw_labels 時由呼叫端傳入字型與顏色，不重複載入 04）


def _s4():
    global S4
    if S4 is None:
        spec = importlib.util.spec_from_file_location("s4", HERE / "scripts/04_slides.py")
        S4 = importlib.util.module_from_spec(spec); spec.loader.exec_module(S4)
    return S4

SHORT = {"臺灣總督府交通局鐵道部（廳舍等）": "鐵道部廳舍", "鐵道部臺北工場車輛修理工場": "鐵道部臺北工場", "臺北撫臺街洋樓": "撫臺街洋樓",
         "原大阪商船株式會社臺北支店": "原大阪商船", "臺北市政府舊廈（原建成小學校）": "市政府舊廈", "臺北市政府衛生局舊址": "衛生局舊址",
         "臺北酒廠": "臺北酒廠（華山）", "臺北工業學校紅樓": "工業學校紅樓"}
FS, PAD = 9, 2


def sites():
    rows = [r for r in csv.DictReader(open(HERE / "data/P15_沿線古蹟點位.csv", encoding="utf-8-sig")) if r.get("保留", "是").startswith("是")]
    out = {}
    for r in rows:
        k = (r["圓心E"], r["圓心N"])
        nm = SHORT.get(r["古蹟"], r["古蹟"])
        if k in out:     # 博愛路 2 號與 4、6、8 號同一輪廓
            out[k] = "博愛路店屋（2；4、6、8 號）"
        else:
            out[k] = nm
    return [(float(e), float(n), nm) for (e, n), nm in out.items()]


def label(name):
    S4 = _s4()
    src = fitz.open(S4.FIG / f"{name}.pdf"); page = src[0]
    b = S4.VIEW.bounds; k = page.rect.width / (b[2] - b[0]); my = 20
    tf = lambda x, y: fitz.Point((x - b[0]) * k, my + (b[3] - y) * k)
    frame = fitz.Rect(0, my, page.rect.width, page.rect.height - my)
    n, nl = draw_labels(page, tf, frame, S4.FL, S4.INK, S4.HER_C)
    out = S4.FIG / f"{name}_label.pdf"; src.subset_fonts(); src.save(out, garbage=3, deflate=True)
    print(out, f"標注 {n} 處（引線 {nl}）")


def draw_labels(page, tf, frame, fontfile, ink, her_c):
    """於 page 上畫圓心點與簡稱（tf：EPSG3826 → 頁面座標）；回傳（標注數, 引線數）"""
    fl = fitz.Font(fontfile=fontfile)
    page.insert_font(fontname="lbl", fontfile=fontfile)   # 不可用 hl：原圖路名已用 hl（子集字型）
    P = [(tf(e, n), nm) for e, n, nm in sites()]
    dots_ = [fitz.Rect(p.x - 4, p.y - 4, p.x + 4, p.y + 4) for p, _ in P]
    crowd = lambda p: sum(1 for q, _ in P if abs(q.x - p.x) < 80 and abs(q.y - p.y) < 40)
    placed, leaders = [], []
    for p, nm in sorted(P, key=lambda t: -crowd(t[0])):
        w = fl.text_length(nm, fontsize=FS)
        best = None
        for ring in (7, 20, 34, 50, 68):
            for ang in (0, 180, 90, 270, 45, 135, 225, 315):
                dx, dy = ring * math.cos(math.radians(ang)), -ring * math.sin(math.radians(ang))
                ax, ay = p.x + dx, p.y + dy
                x0 = ax if dx > .1 else ax - w if dx < -.1 else ax - w / 2
                r = fitz.Rect(x0 - PAD, ay - FS * .5 - PAD, x0 + w + PAD, ay + FS * .5 + PAD)
                if not frame.contains(r) or any(r.intersects(q) for q in placed) or any(r.intersects(d) for d in dots_):
                    continue
                best = (r, x0, ay, ring > 7); break
            if best:
                break
        if best is None:
            print("無位置：", nm); continue
        r, x0, ay, lead = best; placed.append(r)
        if lead:
            leaders.append((p, fitz.Point(min(max(p.x, r.x0), r.x1), min(max(p.y, r.y0), r.y1))))
        sh = page.new_shape(); sh.draw_rect(r); sh.finish(color=None, fill=(1, 1, 1), fill_opacity=.85); sh.commit()
        page.insert_text((x0, ay + FS * .36), nm, fontsize=FS, fontname="lbl", color=ink)
    sh = page.new_shape()
    for a, c in leaders:
        sh.draw_line(a, c)
    sh.finish(color=her_c, width=.5); sh.commit()
    sh = page.new_shape()
    for p, _ in P:
        sh.draw_circle(p, 2.4)
    sh.finish(color=(1, 1, 1), fill=her_c, width=.7); sh.commit()
    return len(placed), len(leaders)


if __name__ == "__main__":
    for n in sys.argv[1:]:
        label(n)
