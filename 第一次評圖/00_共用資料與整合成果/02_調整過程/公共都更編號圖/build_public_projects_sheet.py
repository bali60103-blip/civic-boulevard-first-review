# -*- coding: utf-8 -*-
"""A01-A10 全段索引底圖：公共都更案與公共建設編號標註（2026-10-06，v2 量體剪影版）。

底圖：03_最新產出/01_A01至A10統一清理_v2_20261004/pdf 第 1 頁（索引 1:10000）。
案件狀態沿用《市民大道_都市計畫都更_簡要標記_v2_20261004》查核內容，長安市民案依住都中心官網補至 2025-12。
量體：prep_project_massing.py 產生之「公共案件量體與基地_EPSG3826.geojson」，以 1:10000 真實比例繪入。
  有平面圖者：建築量體實色、敷地設計中透明、基地範圍淡色；無平面圖者：基地範圍概括（虛線外框）。
"""
import json
from pathlib import Path

import fitz
from shapely.geometry import shape
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BASE_PDF = ROOT / "03_最新產出/01_A01至A10統一清理_v2_20261004/pdf/A01_A10_A1_1000_unified_v2.pdf"
QA = ROOT / "03_最新產出/01_A01至A10統一清理_v2_20261004/qa.json"
MASSING = HERE / "公共案件量體與基地_EPSG3826.geojson"
OUT_DIR = ROOT / "04_其他疊合與排版成果/PDF補充成果"
OUT_PDF = OUT_DIR / "市民大道_A01-A10_公共都更與公共建設編號圖_20261006.pdf"
OUT_PNG = OUT_DIR / "市民大道_A01-A10_公共都更與公共建設編號圖_20261006_預覽.png"

FONT_L = "/System/Library/Fonts/STHeiti Light.ttc"
FONT_M = "/System/Library/Fonts/STHeiti Medium.ttc"

# ---- EPSG:3826 -> 索引頁座標（1:10000，A01 圖框為錨點） ----
PT_PER_M = 72 / 25.4 / 10.0  # 1 m 在 1:10000 紙上 = 0.1 mm
A01_PAGE_ORIGIN = (255.12, 490.39)  # A01 圖框左上角（頁面 pt），由底圖向量量得


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


def make_transform(a01_bounds):
    e0, _, _, n1 = a01_bounds
    ox, oy = A01_PAGE_ORIGIN

    def tf(e, n):
        return fitz.Point(ox + (e - e0) * PT_PER_M, oy + (n1 - n) * PT_PER_M)
    return tf


# ---- 狀態（依推動階段排序） ----
STATUS = {
    "plan":    ("規劃中",       "#4F79B5"),
    "prep":    ("前期／招商",   "#C08A1E"),
    "review":  ("審議中",       "#D9682B"),
    "approved": ("審議通過",     "#7E57A6"),
    "build":   ("施工中／展延", "#B8322A"),
    "done":    ("已完成",       "#2E8A57"),
    "closed":  ("結案未續行",   "#8C8C8C"),
}
STATUS_ORDER = ["plan", "prep", "review", "approved", "build", "done"]

# 圖層透明度：建築量體 > 敷地設計 > 基地範圍
OPACITY = {"building": 0.92, "landscape": 0.40, "site": 0.14, "boundary_only": 0.22}

# kind: U = 公共都更案（圓形編號），B = 公共建設（方形編號）
# level: 編號牌高度層（0 最低）；side: 名稱在編號牌左／右；dx: 編號牌相對量體水平偏移
# mask: 先以白色遮去基地內既有建物（新設計取代現況者）
PROJECTS = [
    dict(no=1, ref="B02", kind="B", status="plan", level=0, side="L", dx=0, mask=False,
         short="玉泉人本跨橋",
         name="玉泉公園堤內外人本跨橋",
         where="A01 西端｜玉泉公園—環河北路、淡水河水岸",
         type="公共工程｜人行與自行車銜接",
         basis="平面圖描繪｜水利處規劃配置（3 點對位）",
         note="市府水岸環境營造計畫已列入跨橋，規劃含電梯、階梯及自行車牽引道；尚非定案橋線。",
         src="N06、N07"),
    dict(no=2, ref="U01", kind="U", status="review", level=0, side="R", dx=0, mask=False,
         short="臺北車站 E1／E2",
         name="臺北車站 E1／E2 公有土地都更",
         where="A01｜玉泉段二小段 371 等 17 筆，北門—車站西側",
         type="公有地都更｜交通部鐵道局",
         basis="基地範圍概括｜無公開配置圖，繪 E1／E2 特專區街廓",
         note="2023-10 報核，2024-01 公開展覽及公辦公聽會，仍在審議；2026 鐵道局記載考古試掘及文資修復同步進行。",
         src="S10、S11"),
    dict(no=3, ref="B03", kind="B", status="done", level=0, side="L", dx=0, mask=False,
         short="心中山線形公園",
         name="心中山線形公園（南端節點）",
         where="A03 北側｜長安西路口；北段至民生西路在圖外",
         type="公共空間｜捷運上方街區再生",
         basis="平面圖描繪｜北捷前期評估平面（非竣工版）",
         note="2025 南段改造完成；現行廊帶約 800 m（長安西路—民生西路）。底圖僅含南端銜接段。",
         src="N08、N09"),
    dict(no=4, ref="U17", kind="U", status="approved", level=1, side="L", dx=0, mask=True,
         short="台灣心 HUB",
         name="台灣心 HUB｜行二行三公辦都更",
         where="A03｜市民大道二段、天津街、林森北路、北平東路街廓",
         type="公辦都更｜住都中心／跨區權利變換",
         basis="平面圖描繪｜2024 公聽會配置（4 點對位）",
         note="2022 與冠德簽約；2024-12 完成都市更新審議。基地為官方 46 筆地號（約 1.84 ha）；臨沂段基地在圖外。",
         src="N03–N05"),
    dict(no=5, ref="B01", kind="B", status="build", level=2, side="R", dx=0, mask=True,
         short="華山司法園區",
         name="華山司法園區",
         where="A04｜市民大道二段南側，華山行六用地",
         type="公共建設｜司法機關遷建",
         basis="平面圖描繪｜司法院 2023-03 公開方案",
         note="2022 先期工程動土；2023 討論月台保存；2024 立法院預算評估指期程展延；不推定主體已完工。",
         src="N01、N02"),
    dict(no=6, ref="U02", kind="U", status="review", level=0, side="L", dx=-75, mask=True,
         short="長安市民公辦都更",
         name="長安市民公辦都更",
         where="A06｜長安段二小段 596 等 5 筆，八德路二段 210 巷口",
         type="公辦都更｜住都中心／潤泰創新",
         basis="平面圖描繪｜2025-12 公聽會一層配置（4 點對位）",
         note="2023-12 簽約；2025-04 報核、2025-11 公展、2025-12 公辦公聽會，審議中。23 層住宅，1F 托嬰中心及店鋪，臨市民大道退縮約 17 m 開放空間。",
         src="S12、S13"),
    dict(no=7, ref="U03", kind="U", status="prep", level=0, side="R", dx=75, mask=False,
         short="中油中山公辦都更",
         name="中油中山公辦都更",
         where="A06｜長安段二小段 576 等 4 筆，八德路 218 巷—安東街",
         type="公辦都更｜前期作業",
         basis="基地範圍概括｜尚無配置方案",
         note="2026-05-05 選定為公辦都更，基地約 4,107 ㎡，進入招商準備；需留意市民大道與八德路間南北穿越。",
         src="S14"),
    dict(no=8, ref="U10", kind="U", status="closed", level=1, side="R", dx=0, mask=False,
         short="機廠北側 7599 案",
         name="機廠北側 7599 公辦都更",
         where="A10｜西松段三小段 58 等 33 筆，八德路四段 204 巷",
         type="公辦都更｜已停止",
         basis="基地範圍概括｜結案，無配置方案",
         note="2025-10 因所有權人參與意願未達門檻結案，基地約 3,900 ㎡；不列為推動中案件，保留供對照。",
         src="S18"),
]

INK = hex2rgb("#2B2B2B")
MUTED = hex2rgb("#6B6B6B")
RULE = hex2rgb("#BDBDBD")


def main():
    qa = json.loads(QA.read_text(encoding="utf-8"))
    tf = make_transform(qa["sheets"][0]["bounds"])
    massing = json.loads(MASSING.read_text(encoding="utf-8"))["features"]

    src = fitz.open(BASE_PDF)
    doc = fitz.open()
    doc.insert_pdf(src, from_page=0, to_page=0)
    page = doc[0]
    W = page.rect.width

    # 移除底圖下方十列「分幅說明」文字，騰出表格區（只刪文字，不動線條）
    page.add_redact_annot(fitz.Rect(100, 1080, 1700, 1330))
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                          graphics=fitz.PDF_REDACT_LINE_ART_NONE)

    page.insert_font(fontname="hl", fontfile=FONT_L)
    page.insert_font(fontname="hm", fontfile=FONT_M)
    fl, fm = fitz.Font(fontfile=FONT_L), fitz.Font(fontfile=FONT_M)

    def text(x, y, s, size, font="hl", color=INK, align="L"):
        w = (fm if font == "hm" else fl).text_length(s, fontsize=size)
        if align == "R":
            x -= w
        elif align == "C":
            x -= w / 2
        page.insert_text((x, y), s, fontsize=size, fontname=font, color=color)
        return w

    def wrap(s, size, width):
        lines, cur = [], ""
        for ch in s:
            if fl.text_length(cur + ch, fontsize=size) > width:
                lines.append(cur)
                cur = ch
            else:
                cur += ch
        if cur:
            lines.append(cur)
        return lines

    def chip(x, y, key, size=10.5):
        label, col = STATUS[key]
        w = fm.text_length(label, fontsize=size) + 16
        r = fitz.Rect(x, y - size - 4, x + w, y + 5)
        sh = page.new_shape()
        sh.draw_rect(r)
        if key == "closed":
            sh.finish(color=hex2rgb(col), fill=(1, 1, 1), width=1.0, dashes="[3 2] 0")
        else:
            sh.finish(color=None, fill=hex2rgb(col))
        sh.commit()
        text(x + 8, y, label, size, "hm", hex2rgb(col) if key == "closed" else (1, 1, 1))
        return w

    def badge(c, no, kind, col, closed):
        sh = page.new_shape()
        r = 15
        if kind == "U":
            sh.draw_circle(c, r)
        else:
            sh.draw_rect(fitz.Rect(c.x - r, c.y - r, c.x + r, c.y + r))
        if closed:
            sh.finish(color=col, fill=(1, 1, 1), width=1.8, dashes="[3 2] 0")
        else:
            sh.finish(color=(1, 1, 1), fill=col, width=1.2)
        sh.commit()
        text(c.x, c.y + 6.3, str(no), 17, "hm", col if closed else (1, 1, 1), "C")

    def rings_of(geom):
        polys = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        return [[tf(*xy) for xy in p.exterior.coords] for p in polys if not p.is_empty]

    def draw_geom(geom, col, fill_op, width, dashes=None, stroke=True, fill=None):
        sh = page.new_shape()
        for ring in rings_of(geom):
            sh.draw_polyline(ring)
        sh.finish(color=col if stroke else None, fill=fill or col, fill_opacity=fill_op,
                  width=width, dashes=dashes, closePath=True, even_odd=True)
        sh.commit()

    def swatch(x, y, op, dashed=False, label=""):
        sh = page.new_shape()
        sh.draw_rect(fitz.Rect(x, y - 11, x + 24, y + 3))
        sh.finish(color=INK, fill=INK, fill_opacity=op, width=1.1 if dashed else 0.5,
                  dashes="[3 2] 0" if dashed else None)
        sh.commit()
        return 32 + text(x + 32, y, label, 12, "hl")

    # ---- 標題 ----
    text(115, 232, "公共都更案與公共建設｜沿線編號定位及量體剪影", 30, "hm")
    text(115, 262, "以 A01–A10 全段索引（統一清理 v2，1:10000）為底圖；有公開平面圖者描出建築量體與敷地設計並依真實比例套入，"
         "無平面圖者以基地範圍概括。顏色＝推動階段，編號由西向東，對應下方說明表。", 12.5, "hl", MUTED)

    # 圖例第一列：推動階段
    x, y = 115, 302
    text(x, y, "推動階段", 12, "hm", MUTED)
    x += 64
    for i, key in enumerate(STATUS_ORDER):
        x += chip(x, y, key)
        if i < len(STATUS_ORDER) - 1:
            text(x + 6, y, "→", 12, "hl", MUTED)
            x += 24
    x += 30
    text(x, y, "另列", 12, "hm", MUTED)
    x += 36
    x += chip(x, y, "closed") + 34
    text(x, y, "編號", 12, "hm", MUTED)
    x += 40
    badge(fitz.Point(x + 9, y - 4), "", "U", INK, False)
    x += 26 + text(x + 26, y, "公共都更案", 12)
    x += 18
    badge(fitz.Point(x + 9, y - 4), "", "B", INK, False)
    text(x + 26, y, "公共建設／公共空間", 12)

    # 圖例第二列：透明度＝圖面依據
    x, y = 115, 330
    text(x, y, "圖面依據", 12, "hm", MUTED)
    x += 64
    x += swatch(x, y, OPACITY["building"], label="建築量體剪影（依官方平面圖描繪）") + 26
    x += swatch(x, y, OPACITY["landscape"], label="敷地設計（廣場、綠地、步道、橋面）") + 26
    x += swatch(x, y, OPACITY["site"], label="基地範圍（地號外界）") + 26
    x += swatch(x, y, OPACITY["boundary_only"], dashed=True, label="無平面圖：基地範圍概括（虛線）") + 26
    text(x, y, "比例同底圖 1:10000；套繪前先遮去新案基地內既有建物。", 12, "hl", MUTED)

    # ---- 地圖：量體與基地 ----
    by_case = {}
    for f in massing:
        p = f["properties"]
        by_case.setdefault(p["case"], []).append((p["layer"], p["basis"], shape(f["geometry"])))

    LEVEL_Y = [452, 410, 372]
    for proj in PROJECTS:
        col = hex2rgb(STATUS[proj["status"]][1])
        closed = proj["status"] == "closed"
        items = by_case[proj["ref"]]
        sites = [g for lyr, _, g in items if lyr == "site"]
        boundary_only = all(b == "boundary_only" for _, b, _ in items)

        if proj["mask"]:
            for g in sites:
                draw_geom(g, (1, 1, 1), 1.0, 0, stroke=False, fill=(1, 1, 1))
        if boundary_only:
            for g in sites:
                draw_geom(g, col, OPACITY["boundary_only"], 1.4, dashes="[3 1.6] 0")
        else:
            for g in sites:
                draw_geom(g, col, OPACITY["site"], 0.7)
            for lyr in ("landscape", "building"):
                for l2, _, g in items:
                    if l2 == lyr:
                        draw_geom(g, col, OPACITY[lyr], 0.35 if lyr == "building" else 0.4)

        # 引線：由量體最北點拉至編號牌
        union = unary_union([g for _, _, g in items])
        cx = tf(union.centroid.x, union.centroid.y).x
        top_n = union.bounds[3]
        anchor = fitz.Point(cx, tf(union.centroid.x, top_n).y)
        by = LEVEL_Y[proj["level"]]
        bc = fitz.Point(cx + proj["dx"], by)
        if proj["dx"] < 0:  # 編號牌偏左者，引線改由量體西北角拉出，避免與鄰案交疊
            minx, _, _, maxy = union.bounds
            anchor = tf(minx, maxy)
        sh = page.new_shape()
        sh.draw_line(anchor, fitz.Point(bc.x, by + 15))
        sh.finish(color=col, width=1.0, dashes="[2 1.5] 0" if closed else None)
        sh.draw_circle(anchor, 1.8)
        sh.finish(color=None, fill=col)
        sh.commit()
        badge(bc, proj["no"], proj["kind"], col, closed)
        if proj["side"] == "R":
            text(bc.x + 22, by + 5, proj["short"], 14, "hm")
        else:
            text(bc.x - 22, by + 5, proj["short"], 14, "hm", INK, "R")

    # ---- 說明表 ----
    X0, X1 = 115, W - 115
    cols = [  # (標題, 寬)
        ("編號", 64), ("項目", 280), ("分幅／位置", 330), ("類型", 220),
        ("目前狀態", 140), ("圖面依據", 290), ("查得進度與說明", 740), ("來源", 90),
    ]
    xs = [X0]
    for _, w in cols:
        xs.append(xs[-1] + w)
    assert abs(xs[-1] - X1) < 1, xs[-1]

    ty = 880
    text(X0, ty - 22, "編號說明｜各公共都更案與公共建設目前狀態", 18, "hm")
    text(X1, ty - 22, "查核日 2026-10-04（長安市民案補至 2025-12 公聽會）；來源代碼同《市民大道_都市計畫都更_簡要標記_v2》末頁來源索引",
         11, "hl", MUTED, "R")
    sh = page.new_shape()
    sh.draw_line(fitz.Point(X0, ty - 12), fitz.Point(X1, ty - 12))
    sh.finish(color=INK, width=1.6)
    sh.commit()
    hy = ty + 8
    for (h, _), x in zip(cols, xs):
        text(x + 8, hy, h, 11.5, "hm", MUTED)
    y = hy + 10
    sh = page.new_shape()
    sh.draw_line(fitz.Point(X0, y), fitz.Point(X1, y))
    sh.finish(color=RULE, width=0.8)
    sh.commit()

    ROW_PAD = 8
    for p in PROJECTS:
        col = hex2rgb(STATUS[p["status"]][1])
        closed = p["status"] == "closed"
        cell = {i: wrap(s, 11.5, cols[i][1] - 16) for i, s in
                ((2, p["where"]), (3, p["type"]), (6, p["note"]))}
        basis_kind, basis_src = p["basis"].split("｜")
        basis_lines = wrap(basis_src, 10.5, cols[5][1] - 16)
        nlines = max(2, 1 + len(basis_lines), *(len(v) for v in cell.values()))
        rh = ROW_PAD * 2 + nlines * 15.5
        base = y + ROW_PAD + 12
        badge(fitz.Point(xs[0] + 22, y + rh / 2), p["no"], p["kind"], col, closed)
        text(xs[1] + 8, base, p["name"], 13, "hm")
        text(xs[1] + 8, base + 16, f"原索引 {p['ref']}", 10.5, "hl", MUTED)
        for i, lines in cell.items():
            for k, ln in enumerate(lines):
                text(xs[i] + 8, base + k * 15.5, ln, 11.5)
        chip(xs[4] + 8, base, p["status"])
        op = OPACITY["boundary_only"] if basis_kind.startswith("基地") else OPACITY["building"]
        sh = page.new_shape()
        sh.draw_rect(fitz.Rect(xs[5] + 8, base - 10, xs[5] + 24, base + 2))
        sh.finish(color=col, fill=col, fill_opacity=op, width=0.9,
                  dashes="[2 1.2] 0" if basis_kind.startswith("基地") else None)
        sh.commit()
        text(xs[5] + 30, base, basis_kind, 11.5, "hm")
        for k, ln in enumerate(basis_lines):
            text(xs[5] + 8, base + 15.5 * (k + 1), ln, 10.5, "hl", MUTED)
        text(xs[7] + 8, base, p["src"], 11.5, "hl", MUTED)
        y += rh
        sh = page.new_shape()
        sh.draw_line(fitz.Point(X0, y), fitz.Point(X1, y))
        sh.finish(color=RULE, width=0.6)
        sh.commit()

    note_y = y + 20
    text(X0, note_y, "註：量體為公開方案平面描繪（送審／公聽會版本，非核定施工圖）；對位殘差約 0.3–0.6 m，於 1:10000 圖面不可辨。"
         "地號外界取自臺北市地籍 GIS。U10 官網列舉漏 72 地號，依公告面積補入。U01 更新單元 17 筆未逐筆比對，以 E1／E2 街廓概括。",
         11, "hl", MUTED)
    text(X0, note_y + 18, "私人實施之已完成或申請中都更案（v2 索引 U04–U09）與圖外東段公辦案（兒福 A1／A2、南港調車場等）不列入本圖。"
         "量體及地號 GeoJSON（EPSG:3826）見 02_調整過程／公共都更編號圖。", 11, "hl", MUTED)
    assert note_y + 18 < 1395, f"表格高度超出：{note_y}"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    doc.set_metadata({"title": "市民大道 A01–A10 公共都更與公共建設編號圖", "creationDate": "D:20261006"})
    doc.save(OUT_PDF, garbage=3, deflate=True)
    doc.close()
    fitz.open(OUT_PDF)[0].get_pixmap(dpi=72).save(OUT_PNG)
    print(OUT_PDF)
    print("table bottom", note_y)


if __name__ == "__main__":
    main()
