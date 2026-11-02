# -*- coding: utf-8 -*-
"""南京西路—仁愛路沿線｜影響穿越市民大道行人之計畫案與既有設施編號圖（2026-10-06）。

表現法沿用 02_調整過程/公共都更編號圖/build_public_projects_sheet.py：
顏色＝推動階段、圓形＝開發／都更案、方形＝公共建設／交通設施、編號由西向東、上方引線編號牌＋下方說明表。
既有設施（現況人流基準）以「已完成」綠色標記。
底圖：A01_A10_Nanjing_Renai_20261005.pdf 第 1 頁（1:10000），移除 A01–A10 粉色框線。
"""
import json, re
from pathlib import Path
import fitz
from shapely.geometry import shape, Point
from shapely.ops import unary_union

ROOT = Path("/Users/ktlu/Desktop/第一次評圖/00_共用資料與整合成果")
EXP = ROOT / "03_最新產出/02_南京至仁愛擴幅_20261005"
BASE_PDF = EXP / "pdf/A01_A10_Nanjing_Renai_20261005.pdf"
MASSING = ROOT / "02_調整過程/公共都更編號圖/公共案件量體與基地_EPSG3826.geojson"
SRC = ROOT / "04_其他疊合與排版成果/CAD及官方平面疊合/urban_plan_review/sources_current"
OUT = Path(__file__).resolve().parents[1]
OUT_PDF = OUT / "市民大道_南京西至仁愛_穿越行人相關計畫與既有設施編號圖_20261006.pdf"
OUT_PNG = OUT / "市民大道_南京西至仁愛_穿越行人相關計畫與既有設施編號圖_20261006_預覽.png"
FONT_L = "/System/Library/Fonts/STHeiti Light.ttc"
FONT_M = "/System/Library/Fonts/STHeiti Medium.ttc"


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


STATUS = {
    "plan": ("規劃中", "#4F79B5"), "prep": ("前期／招商", "#C08A1E"), "review": ("審議中", "#D9682B"),
    "approved": ("審議通過", "#7E57A6"), "build": ("施工中／展延", "#B8322A"), "done": ("已完成", "#2E8A57"),
    "closed": ("結案未續行", "#8C8C8C"),
}
STATUS_ORDER = ["plan", "prep", "review", "approved", "build", "done"]
OPACITY = {"building": 0.92, "landscape": 0.40, "site": 0.16, "boundary_only": 0.18}
INK, MUTED, RULE = hex2rgb("#2B2B2B"), hex2rgb("#6B6B6B"), hex2rgb("#BDBDBD")

# ---------- 幾何來源 ----------
index = {}
for n in [0, 500, 1000, 1500, 2000, 2500, 3000]:
    for f in json.load(open(SRC / f"index_{n}.json"))["features"]:
        from shapely.geometry import Polygon
        r = f["geometry"]["rings"]
        index.setdefault(f["attributes"]["PROJNUM"], []).append(Polygon(r[0], r[1:]).buffer(0))
index = {k: unary_union(v) for k, v in index.items()}
mask = shape(json.load(open(EXP / "ten_sheet_mask.geojson"))["features"][0]["geometry"])
massing = {}
for f in json.load(open(MASSING))["features"]:
    p = f["properties"]
    massing.setdefault(p["case"], []).append((p["layer"], p["basis"], shape(f["geometry"])))


def plan(*codes, clip=True):
    g = unary_union([index[c] for c in codes])
    return g.intersection(mask) if clip else g


# geom 型式：("massing", ref) 用既有編號圖量體；("site", geom) 計畫範圍；("boundary", geom) 概括虛線；("point", (E,N))
# tier：F＝未來變動、B＝現況基準、C＝對照
P = [
    dict(kind="U", status="review", tier="F", short="臺北車站 E1／E2", geom=("massing", "U01"),
         name="臺北車站 E1／E2 公有地都更", codes="P107017／P108001｜原索引 U01",
         where="北門—鄭州路，市民大道北側",
         note="鐵道博物館特專區＋商業開發；與南側車站之間在塔城街—重慶北路形成過街，假日觀光型人流為主。仍在都更審議。"),
    dict(kind="B", status="done", tier="B", short="北門站出入口", geom=("site", plan("093040")),
         name="捷運北門站（G14）出入口", codes="P093040",
         where="塔城街×市民大道兩側",
         note="出入口位置決定塔城街一帶實際穿越點；現況通勤人流基準。"),
    dict(kind="U", status="build", tier="F", verify=True, short="臺北雙子星 C1／D1", geom=("site", plan("095016")),
         name="臺北車站 C1／D1 東半聯開（雙子星）", codes="P095016／P095018",
         where="市民大道×重慶北路南側",
         note="大型辦公＋旅館＋機捷站；上班族午餐北向穿越至京站、承德路、太原路，與通勤尖峰疊加。"),
    dict(kind="B", status="done", tier="B", short="京站／臺北轉運站", geom=("site", plan("093053")),
         name="京站／臺北轉運站（交九）", codes="P093053",
         where="市民大道一段北側，承德路口",
         note="西段北側最大人流源與餐飲目的地；雙子星完工後午餐人流主要去處之一。"),
    dict(kind="B", status="done", tier="B", short="心中山線形公園", geom=("massing", "B03"),
         name="心中山線形公園（南端節點）", codes="原索引 B03",
         where="長安西路口北側",
         note="南北向步行廊帶的南端，導引人流至市民大道；2025 南段改造完成。"),
    dict(kind="U", status="approved", tier="F", short="台灣心 HUB", geom=("massing", "U17"), mask=True,
         name="台灣心 HUB｜行二行三公辦都更", codes="P111010｜原索引 U17",
         where="市民大道二段北側，天津街—林森北路",
         note="機關辦公＋住宅＋開放廣場；放寬附屬零售餐飲 30%。北側新增全日生活人流，與司法園區隔路相對。"),
    dict(kind="B", status="build", tier="F", short="華山司法園區", geom=("massing", "B01"), mask=True,
         name="華山司法園區", codes="P092029／P092034｜原索引 B01",
         where="市民大道二段南側，華山行六",
         note="完工後大量公務人流；北側六條通已劃商三（特），形成中午南→北穿越吃飯尖峰（林森北路—新生北路橋下）。"),
    dict(kind="B", status="plan", tier="F", verify=True, short="北科大擴校", geom=("site", plan("114001")),
         name="中山區工業區變更大學用地", codes="P114001（114 公告）",
         where="市民大道北側，北科大校本部對側",
         note="若為北科大向北擴校，將出現校區間課間高頻穿越（每小時一波）；計畫書文字待核。"),
    dict(kind="U", status="approved", tier="F", short="市民大道兩側住三之一（特）", geom=("boundary", plan("097017")),
         name="市民大道兩側使用組別調整＋更新地區", codes="P097017（97 公告）",
         where="新生北路—基隆路兩側",
         note="容積不變、開放支援性商業並劃更新地區；隨逐棟更新沿街一樓活化，路段中間穿越需求漸增。已實施、逐步發生。"),
    dict(kind="U", status="review", tier="F", short="長安市民公辦都更", geom=("massing", "U02"), mask=True,
         name="長安市民公辦都更", codes="原索引 U02",
         where="八德路二段 210 巷口",
         note="23 層住宅，1F 托嬰＋店鋪，臨市民大道退縮約 17 m 開放空間；新增住戶接送與店鋪人流。"),
    dict(kind="U", status="prep", tier="F", short="中油中山公辦都更", geom=("massing", "U03"),
         name="中油中山公辦都更", codes="P092003／P093011｜原索引 U03",
         where="八德路 218 巷—安東街",
         note="原加油站用地；2026-05 選定公辦都更。需留意市民大道與八德路間南北穿越。"),
    dict(kind="U", status="plan", tier="F", verify=True, short="TOD 可申請開發地區", geom=("boundary", plan("108006")),
         name="大眾運輸導向可申請開發許可地區", codes="P108006（108 公告）",
         where="北門、中山、忠孝新生、忠孝復興站周邊",
         note="大基地可申請容積獎勵；何處何時開發不確定，作為站點周邊可能加密之情境清單。", anchor=(303700, 2770600)),
    dict(kind="B", status="done", tier="B", short="大巨蛋／松菸", geom=("site", plan("092044")),
         name="臺北文化體育園區（大巨蛋、松菸）", codes="P092031／P092044、P099046",
         where="市民大道南側，光復南路東",
         note="平日中等、活動散場極端尖峰；橋下需承受偶發大量疏散。北側道路（P099046）為車行配套。"),
    dict(kind="B", status="build", tier="F", verify=True, short="臺北機廠鐵道博物館", geom=("point", (306850, 2770922)),
         name="臺北機廠（國家鐵道博物館園區）", codes="國定古蹟（非都市計畫個案）",
         where="市民大道北側，正對大巨蛋",
         note="完全開放後與大巨蛋形成南北向過街軸線（假日＋活動日）。無計畫範圍，以煙囪位置定點。"),
    dict(kind="U", status="build", tier="F", verify=True, short="京華城重建", geom=("site", plan("103018", "107003")),
         name="原唐榮／京華城重建（第三種商業區（特））", codes="P103018／P107003",
         where="八德路四段—市民大道間",
         note="大型商業辦公重建；完工後人流南向穿越至松菸、巨蛋、忠孝敦化。"),
    dict(kind="U", status="closed", tier="C", short="機廠北側 7599 案", geom=("massing", "U10"),
         name="機廠北側 7599 公辦都更", codes="原索引 U10",
         where="八德路四段 204 巷",
         note="2025-10 結案，不列為推動中；保留對照。"),
]


def main():
    q = json.load(open(EXP / "qa.json"))
    bb = q["bounds"]; cx = (bb[0] + bb[2]) / 2; cy = (bb[1] + bb[3]) / 2
    src = fitz.open(BASE_PDF); doc = fitz.open(); doc.insert_pdf(src, from_page=0, to_page=0); page = doc[0]
    H, W = page.rect.height, page.rect.width; K = 72 / 25.4

    def tf(x, y):
        return fitz.Point((420.5 + (x - cx) / 10) * K, H - (365 + (y - cy) / 10) * K)

    # 移除 A01–A10 框線、編號牌與分幅文字
    for x in page.get_contents():
        b = doc.xref_stream(x); i = b.find(b".78 .06 .4 RG")
        if i < 0:
            continue
        head, tail = b[:i], b[i:]
        tail = re.sub(rb"n [\d.]+ [\d.]+ 215\.4331 144\.5669 re S\n", b"", tail)
        tail = re.sub(rb"1 1 1 rg\nn [\d.]+ [\d.]+ 48\.18898 19\.84252 re f\*\n", b"", tail)
        tail = re.sub(rb"\.1 \.13 \.15 rg\nBT [^\n]*?\((A\d\d)[^\n]*?ET\n", b"", tail)
        doc.update_stream(x, head + tail)
    # 刪除原標題、說明文字（只刪文字）；比例尺與頁尾另以白底覆蓋後重畫
    for r in [fitz.Rect(100, 90, 2150, 230), fitz.Rect(100, 1250, 1500, 1650)]:
        page.add_redact_annot(r)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)
    sh = page.new_shape(); sh.draw_rect(fitz.Rect(1800, 1540, 2250, 1640)); sh.finish(color=None, fill=(1, 1, 1)); sh.commit()

    page.insert_font(fontname="hl", fontfile=FONT_L); page.insert_font(fontname="hm", fontfile=FONT_M)
    fl, fm = fitz.Font(fontfile=FONT_L), fitz.Font(fontfile=FONT_M)

    def text(x, y, s, size, font="hl", color=INK, align="L"):
        w = (fm if font == "hm" else fl).text_length(s, fontsize=size)
        x = x - w if align == "R" else x - w / 2 if align == "C" else x
        page.insert_text((x, y), s, fontsize=size, fontname=font, color=color)
        return w

    def wrap(s, size, width):
        lines, cur = [], ""
        for ch in s:
            if fl.text_length(cur + ch, fontsize=size) > width:
                lines.append(cur); cur = ch
            else:
                cur += ch
        return lines + ([cur] if cur else [])

    def chip(x, y, key, size=10.5):
        label, col = STATUS[key]; w = fm.text_length(label, fontsize=size) + 16
        s = page.new_shape(); s.draw_rect(fitz.Rect(x, y - size - 4, x + w, y + 5))
        if key == "closed":
            s.finish(color=hex2rgb(col), fill=(1, 1, 1), width=1.0, dashes="[3 2] 0")
        else:
            s.finish(color=None, fill=hex2rgb(col))
        s.commit(); text(x + 8, y, label, size, "hm", hex2rgb(col) if key == "closed" else (1, 1, 1))
        return w

    def badge(c, no, kind, col, closed, r=13):
        s = page.new_shape()
        if kind == "U":
            s.draw_circle(c, r)
        else:
            s.draw_rect(fitz.Rect(c.x - r, c.y - r, c.x + r, c.y + r))
        if closed:
            s.finish(color=col, fill=(1, 1, 1), width=1.8, dashes="[3 2] 0")
        else:
            s.finish(color=(1, 1, 1), fill=col, width=1.2)
        s.commit(); text(c.x, c.y + r * 0.42, str(no), r * 1.1, "hm", col if closed else (1, 1, 1), "C")

    def rings(g):
        polys = list(getattr(g, "geoms", [g]))
        return [[tf(*xy[:2]) for xy in p.exterior.coords] for p in polys if p.geom_type == "Polygon" and not p.is_empty]

    def draw(g, col, op, width, dashes=None, stroke=True, fill=None):
        s = page.new_shape()
        for ring in rings(g):
            s.draw_polyline(ring)
        s.finish(color=col if stroke else None, fill=fill or col, fill_opacity=op, width=width,
                 dashes=dashes, closePath=True, even_odd=True)
        s.commit()

    def swatch(x, y, op, dashed=False, label=""):
        s = page.new_shape(); s.draw_rect(fitz.Rect(x, y - 11, x + 24, y + 3))
        s.finish(color=INK, fill=INK, fill_opacity=op, width=1.1 if dashed else 0.5, dashes="[3 2] 0" if dashed else None)
        s.commit(); return 32 + text(x + 32, y, label, 12)

    # ---- 標題與圖例 ----
    text(115, 128, "南京西路—仁愛路沿線｜影響穿越市民大道行人之計畫案與既有設施", 30, "hm")
    text(115, 156, "底圖：A01_A10_Nanjing_Renai_20261005 第 1 頁線稿（1:10000，已移除 A01–A10 框線）。顏色＝推動階段；既有設施以「已完成」標記，作為現況人流基準；"
         "其餘為現在到未來可能改變穿越人流之案件。編號由西向東，對應下方說明表。", 12.5, "hl", MUTED)
    x, y = 115, 192
    text(x, y, "推動階段", 12, "hm", MUTED); x += 64
    for i, key in enumerate(STATUS_ORDER):
        x += chip(x, y, key)
        if i < len(STATUS_ORDER) - 1:
            text(x + 6, y, "→", 12, "hl", MUTED); x += 24
    x += 30; text(x, y, "另列", 12, "hm", MUTED); x += 36; x += chip(x, y, "closed") + 34
    text(x, y, "編號", 12, "hm", MUTED); x += 40
    badge(fitz.Point(x + 9, y - 4), "", "U", INK, False, 11); x += 26 + text(x + 26, y, "開發／都更案", 12) + 18
    badge(fitz.Point(x + 9, y - 4), "", "B", INK, False, 11); x += 26 + text(x + 26, y, "公共建設／交通設施", 12) + 34
    text(x, y, "★ 待核：推動階段依公開資訊推定，尚未逐案查證", 12, "hl", MUTED)
    x, y = 115, 218
    text(x, y, "圖面依據", 12, "hm", MUTED); x += 64
    x += swatch(x, y, OPACITY["building"], label="建築量體剪影（公開方案描繪）") + 26
    x += swatch(x, y, OPACITY["landscape"], label="敷地設計") + 26
    x += swatch(x, y, OPACITY["site"], label="基地／計畫範圍（官方歷年計畫索引或地號外界）") + 26
    x += swatch(x, y, OPACITY["boundary_only"], dashed=True, label="範圍概括或分散地區（虛線）") + 26
    text(x, y, "計畫範圍裁至原十幅內；非地籍核對界線。", 12, "hl", MUTED)

    # ---- 地圖 ----
    anchors = []
    for p in P:
        col = hex2rgb(STATUS[p["status"]][1]); closed = p["status"] == "closed"
        typ, g = p["geom"]
        if typ == "massing":
            items = massing[g]; sites = [x for l, _, x in items if l == "site"]
            if p.get("mask"):
                for s_ in sites:
                    draw(s_, (1, 1, 1), 1.0, 0, stroke=False, fill=(1, 1, 1))
            if all(b == "boundary_only" for _, b, _ in items):
                for s_ in sites:
                    draw(s_, col, OPACITY["boundary_only"], 1.4, "[3 1.6] 0")
            else:
                for s_ in sites:
                    draw(s_, col, OPACITY["site"], 0.7)
                for lyr in ("landscape", "building"):
                    for l2, _, s_ in items:
                        if l2 == lyr:
                            draw(s_, col, OPACITY[lyr], 0.35 if lyr == "building" else 0.4)
            u = unary_union([x for _, _, x in items])
        elif typ == "site":
            draw(g, col, OPACITY["site"] + 0.1, 0.9); u = g
        elif typ == "boundary":
            draw(g, col, OPACITY["boundary_only"], 1.2, "[3 1.6] 0"); u = g
        else:
            u = Point(*g)
            c = tf(*g); s = page.new_shape(); s.draw_circle(c, 6); s.finish(color=(1, 1, 1), fill=col, width=1.2); s.commit()
        if p.get("anchor"):
            a = Point(*p["anchor"]); a = u.interiors if False else a
            near = min(getattr(u, "geoms", [u]), key=lambda q: q.distance(a))
            ap = near.representative_point(); ax_, ay_ = ap.x, near.bounds[3]
        elif typ == "point":
            ax_, ay_ = g
        else:
            big = max(getattr(u, "geoms", [u]), key=lambda q: q.area)
            ax_, ay_ = big.centroid.x, big.bounds[3]
        anchors.append(tf(ax_, ay_))

    order = sorted(range(len(P)), key=lambda i: anchors[i].x)
    for no, i in enumerate(order, 1):
        P[i]["no"] = no
    LEVELS = [356, 324, 292, 260]
    occupied = [-1e9] * len(LEVELS)
    for i in order:
        p = P[i]; col = hex2rgb(STATUS[p["status"]][1]); closed = p["status"] == "closed"
        a = anchors[i]; bx = a.x
        lw = fm.text_length(p["short"] + (" ★" if p.get("verify") else ""), fontsize=13) + 40
        lv = next((k for k in range(len(LEVELS)) if occupied[k] < bx - 16), len(LEVELS) - 1)
        occupied[lv] = bx + lw
        by = LEVELS[lv]; bc = fitz.Point(bx, by)
        s = page.new_shape(); s.draw_line(a, fitz.Point(bx, by + 13))
        s.finish(color=col, width=1.0, dashes="[2 1.5] 0" if closed else None)
        s.draw_circle(a, 1.8); s.finish(color=None, fill=col); s.commit()
        badge(bc, p["no"], p["kind"], col, closed)
        text(bx + 19, by + 5, p["short"] + (" ★" if p.get("verify") else ""), 13, "hm")

    # 比例尺移到右上
    sx, sy = 1960, 205
    for k in range(4):
        s = page.new_shape(); s.draw_rect(fitz.Rect(sx + k * 70.866, sy, sx + (k + 1) * 70.866, sy + 8.5))
        s.finish(color=INK, fill=INK if k % 2 == 0 else (1, 1, 1), width=0.6); s.commit()
    for k, t in [(0, "0"), (2, "500"), (4, "1000 m")]:
        text(sx + k * 70.866, sy + 22, t, 9, "hl", MUTED, "C" if k else "L")

    # ---- 說明表 ----
    X0, X1 = 115, W - 115
    cols = [("編號", 52), ("項目", 330), ("位置", 270), ("層級", 120), ("目前狀態", 130),
            ("對穿越市民大道行人的影響（多為間接）", 1252)]
    xs = [X0]
    for _, w in cols:
        xs.append(xs[-1] + w)
    assert abs(xs[-1] - X1) < 1, xs[-1]
    ty = 975
    text(X0, ty - 22, "編號說明｜各案目前狀態與對穿越人流的影響", 18, "hm")
    text(X1, ty - 22, "計畫範圍：臺北市都發局歷年計畫索引（查詢 2026-10-05）；量體與 U／B 原索引同《市民大道_A01-A10_公共都更與公共建設編號圖》；查核日 2026-10-06",
         11, "hl", MUTED, "R")
    s = page.new_shape(); s.draw_line(fitz.Point(X0, ty - 12), fitz.Point(X1, ty - 12)); s.finish(color=INK, width=1.6); s.commit()
    hy = ty + 6
    for (h, _), x in zip(cols, xs):
        text(x + 8, hy, h, 11, "hm", MUTED)
    y = hy + 8
    s = page.new_shape(); s.draw_line(fitz.Point(X0, y), fitz.Point(X1, y)); s.finish(color=RULE, width=0.8); s.commit()
    TIER = {"F": "未來變動", "B": "現況基準", "C": "對照"}
    LH = 13.5
    for p in sorted(P, key=lambda p: p["no"]):
        col = hex2rgb(STATUS[p["status"]][1]); closed = p["status"] == "closed"
        note = wrap(p["note"], 11, cols[5][1] - 16); where = wrap(p["where"], 11, cols[2][1] - 16)
        n = max(2, len(note), len(where))
        rh = 10 + n * LH; base = y + 5 + 10.5
        badge(fitz.Point(xs[0] + 20, y + rh / 2), p["no"], p["kind"], col, closed, 11)
        text(xs[1] + 8, base, p["name"], 12, "hm")
        text(xs[1] + 8, base + LH, p["codes"], 10, "hl", MUTED)
        for k, ln in enumerate(where):
            text(xs[2] + 8, base + k * LH, ln, 11)
        text(xs[3] + 8, base, TIER[p["tier"]], 11.5, "hm", hex2rgb(STATUS["done"][1]) if p["tier"] == "B" else INK)
        chip(xs[4] + 8, base, p["status"], 10)
        if p.get("verify"):
            text(xs[4] + 8, base + LH + 1, "★ 待核", 10, "hl", MUTED)
        for k, ln in enumerate(note):
            text(xs[5] + 8, base + k * LH, ln, 11)
        y += rh
        s = page.new_shape(); s.draw_line(fitz.Point(X0, y), fitz.Point(X1, y)); s.finish(color=RULE, width=0.6); s.commit()
    ny = y + 18
    text(X0, ny, "篩選：由沿線 24 個都市計畫個案中保留會改變或構成穿越人流者；已完成且與過街無關者（北門廣場、郵政大樓、當代館、加油站以外個案、敦化特專區、松山車站、南港專案等）不列。"
         "懷生段（市民大道×建國南路）完工狀態未確認，暫不標。", 10.5, "hl", MUTED)
    text(X0, ny + 16, "人流影響為依計畫內容與區位推論之間接效果，未經實測；★ 項之施工／開放階段依公開資訊推定，需再查證。底圖 © OpenStreetMap contributors / ODbL｜100% 列印勿縮放", 10.5, "hl", MUTED)
    assert ny + 16 < 1650, ny

    doc.set_metadata({"title": "南京西路—仁愛路沿線 穿越行人相關計畫與既有設施編號圖", "creationDate": "D:20261006"})
    doc.save(OUT_PDF, garbage=3, deflate=True)
    fitz.open(OUT_PDF)[0].get_pixmap(dpi=72).save(OUT_PNG)
    print(OUT_PDF, "table bottom", ny + 16)
    for p in sorted(P, key=lambda p: p["no"]):
        print(p["no"], p["short"], p["status"])


if __name__ == "__main__":
    main()
