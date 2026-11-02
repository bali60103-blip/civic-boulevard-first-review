# -*- coding: utf-8 -*-
"""南京西路—仁愛路沿線｜兩張圖（2026-10-09）
  A：計畫範圍（各區通檢底色）＋都市發展／都更案例（剪影＋基地）＋分段特性（結果）＋案例說明
  B：紅框範圍（24 個案全部編號）＋劃定更新地區＋各段更新意圖總結＋紅框一覽
資料載入沿用 build_vision_renewal_sheet.py。
"""
import sys, re, json
from pathlib import Path
import fitz
from shapely.geometry import Point, LineString, box
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_vision_renewal_sheet as vs

OUT = vs.OUT
STATUS, INK, MUTED, RULE, RED = vs.STATUS, vs.INK, vs.MUTED, vs.RULE, vs.RED
hex2rgb = vs.hex2rgb

# 分段（新生北路界線依華山計畫東界 E303772／P097017 西界 E303794 修正為 E303780）
SEG = [
    (300935, 302500, "S1 西端車站段", "環河北路—中山北路｜大同、中正",
     "以交通樞紐與鐵道文資為核心、由公部門大基地主導的再開發段。未來 10 年辦公、旅館與觀光人流增量最大，"
     "車站與北門一帶將成為新的城市門戶（「台北心軸線」之 Taipei Gateway）；跨市民大道空廊完成後，車站與心中山之間首度有連續步行連結；市民大道在此是車站南北兩側之間待縫合的縫隙。"),
    (302500, 303780, "S2 華山行政段", "中山北路—新生北路｜中正、中山",
     "南側中央行政與文創大街廓、北側六條通餐飲街區互補的段落。屬「台北心軸線」之 New Civic Hub，變動一次到位而非漸進；"
     "司法園區與台灣心 HUB 完工後，平日午間南北往返最集中。"),
    (303780, 304930, "S3 生活街區段", "新生北路—復興南路｜中山、大安",
     "老舊住宅逐棟更新的生活街區。強度不增、沿街一樓逐步活化，退縮開放空間零星出現並慢慢連成；"
     "人流屬漸進、全日的生活型。"),
    (304930, 306100, "S4 敦化辦公段", "復興南路—光復南路｜松山、大安",
     "辦公金融走廊與高密度住宅交會、已大致更新成熟的段落。變動小；敦化路口兩側既有更新成果"
     "是橋下銜接的現成樣本。"),
    (306100, 307545, "S5 文體與機廠段", "光復南路—基隆路｜信義、松山",
     "大型文化體育與商業設施主導、人流以活動散場為尖峰的段落。北側臺北機廠與南側大巨蛋形成南北軸，"
     "八德路以北小街廓更新正在啟動但整合不易。"),
]
INTENT = [  # 紅框：各段更新意圖總結
    "以特定專用區與聯合開發，把鐵路地下化釋出的公有地轉為交通、辦公與博物館複合核心；同時以古蹟活化（北門、鐵道工場、當代館、郵電大樓）重建歷史地景，並要求臨路帶狀開放空間緩衝高架。",
    "以整體規劃、整體開發重組華山：南側強化中央行政主體並保留文創大街廓，北側六條通升格商業但不增強度；行二行三以公辦都更兼顧原住戶安置，並禁止容積移入以維持環境品質。",
    "不增容積、只放寬使用組別並劃定更新地區，鼓勵老舊住宅自主改建；以開放空間、人行通道換取獎勵，搭配 TOD 於站點周邊適度加密，逐步形塑市民大道東西向景觀軸與人行空間。",
    "維持敦化南北路辦公金融特性，沿市民大道以住四之一（特）放寬支援性商業；更新以既有大型基地為主，TOD 引導忠孝復興站周邊加密。",
    "將菸廠、唐榮等工業遺址轉為文化體育與大型商業設施，並以新闢道路補強路網；八德路以北以老舊中低層社區專案與公辦都更推動小街廓更新，松山車站整合為東區轉運門戶。",
]
SHORT = {
    "108001": "E1／E2／D1 細部：博物館特專區，臨路 10 m 帶狀開放空間", "107017": "E1／E2／D1 主要：公設用地轉特專區、博物館特專區",
    "115011": "中興醫院：建蔽放寬，地下連通北門站", "093040": "北門站：捷運出入口＋劃定更新地區",
    "105006": "北門廣場：拆引道，重現北門城地景", "096016": "郵電大樓：古蹟保存，交大使用",
    "095016": "C1／D1 聯開（雙子星）：機捷站與聯合開發", "082022": "臺北車站特專區：交通運輸中心框架",
    "093053": "交九：轉運站立體共構", "091007": "當代館：舊市府古蹟活化",
    "111010": "行二行三：行政主體、附屬使用 ≤30%", "092029": "華山整體計畫：行政／文創專用區、六條通商三（特）",
    "114001": "工業區轉大學用地（待核）", "093013": "懷生段：開放空間換容積（臺北好好看）",
    "092003-07": "中油加油站：轉作住商或公園", "108006": "TOD：站點周邊開發許可加密",
    "091017": "敦化特專區：辦公金融單一分區", "099046": "松菸北側：工業區改道路",
    "092031": "松菸特專區：大巨蛋＋古蹟再利用", "097017": "市民大道兩側：放寬使用組別＋更新地區",
    "103018": "唐榮／京華城：商三（特）多目標、分 2 區", "109004": "西松段：老舊社區專案更新",
    "093038": "松山車站：東區轉運樞紐", "090031": "南港專案：鐵路地下化東延",
}

# 都市發展／都更案例：依段落脈絡納入（不論現行或未來）
NEW = {
    "B02": dict(kind="B", status="plan", short="玉泉公園人本跨橋", who="公共工程｜水利處",
                desc="堤內外人行與自行車跨橋，含電梯、階梯與牽引道；把西端車站區接回淡水河水岸，尚非定案橋線。"),
    "TWIN": dict(kind="U", status="build", verify=True, short="臺北雙子星（C1／D1）", who="聯合開發｜機捷",
                 desc="機捷臺北站上方聯開，C1 55F 辦公商城、D1 74F 企業總部＋旅館＋觀景台，裙樓設國門客廳並跨重慶北路相連；預計 116 年完工。塔樓剪影取自 OSM 興建中輪廓（D1 約 3,340 ㎡、C1 約 2,480 ㎡）；跨重慶北路之連續裙樓依展覽模型推估。"),
    "BEIMEN": dict(kind="B", status="done", short="北門廣場", who="公共空間｜市府",
                   desc="忠孝橋引道拆除後重現北門城與城牆地景（2017）；與鐵道部、三井倉庫串成北門文資節點。"),
    "RAIL": dict(kind="B", status="done", short="鐵道部園區（鐵道博物館）", who="文資｜臺博館",
                 desc="臺灣總督府交通局鐵道部古蹟修復為鐵道歷史博物館（2020 開館）。"),
    "B03": dict(kind="B", status="done", short="心中山線形公園", who="公共空間｜北捷",
                desc="城市大道（Skywalk）計畫之公園段，2025-08 完工；捷運淡水線上方線形公園，南端 R1 出入口緊鄰市民大道。"),
    "SKY": dict(kind="B", status="prep", verify=True, short="跨市民大道空廊（Skywalk）", who="公共工程｜臺北捷運公司",
                desc="城市大道計畫之跨市民大道段（發包中）：連續空廊、大尺度行人穿越道與頂棚，自心中山南端跨越市民大道接臺北車站，模型顯示步行平台穿越高架橋下。位置依心中山軸線南延推估。"),
    "B01": dict(kind="B", status="build", short="華山司法園區", who="公共建設｜司法院",
                desc="華山行六用地司法機關遷建；2022 先期工程動土，期程展延。完工後南側新增大量公務人流。"),
    "H1914": dict(kind="B", status="done", short="華山 1914 文創園區", who="文資｜文化部",
                  desc="創意文化專用區內之酒廠古蹟群，假日文創人流核心。"),
    "DOME": dict(kind="B", status="done", short="臺北大巨蛋／松菸", who="BOT｜市府",
                 desc="松菸特專區之大巨蛋（2023 啟用）與松山文創園區；平日中等、活動散場為極端尖峰。"),
    "DEPOT": dict(kind="B", status="build", verify=True, short="臺北機廠（國家鐵道博物館）", who="文資｜文化部",
                  desc="國定古蹟臺北機廠轉為國家鐵道博物館園區，分期修復開放；與大巨蛋形成南北軸。"),
    "JHC": dict(kind="U", status="build", verify=True, short="京華城重建", who="私人｜威京",
                desc="原唐榮鐵工廠商三（特）基地重建為大型商業辦公；土地扣押中、變更設計待審，無公開配置。量體以基地內縮 8 m 示意（虛線）。"),
}
NEW_GEOM = {
    "B02": ("massing", "B02"), "B03": ("massing", "B03"), "B01": ("massing", "B01"),
    "TWIN": ("schematic", "095016"),
    "SKY": ("site", LineString([(302361, 2771268), (302292, 2771148)]).buffer(9, cap_style=2)),
    "BEIMEN": ("site+bld", vs.U["105006"].intersection(vs.mask), "way/238316480"),
    "RAIL": ("osmset", ["way/319875831", "way/550662349"]),
    "H1914": ("osmset", ["way/197752238", "way/197752239", "way/197752241", "way/197752242", "way/197752243", "way/197752244",
                         "way/197752246", "way/197752247", "way/197752248", "way/197752249", "way/197752250", "way/197752252",
                         "way/197755408", "way/1307690197", "way/1307690204", "way/1307690208", "way/1307690209", "way/1307690214",
                         "way/1307690215", "way/1307690217", "way/1307690218", "way/1307690219", "way/1307690220"]),
    "DOME": ("site+bld", vs.U["092044"].intersection(vs.mask), "way/442195153"),
    "DEPOT": ("osmset", [k for k in vs.osm_bld if k.startswith(("way/4779033", "way/5555133", "way/13426738", "way/15488300"))]
              + ["way/1342705709"]),
    "JHC": ("schematic", "103018"),
}


def cases():
    out = []
    for r in vs.RENEW:
        desc = r["desc"]
        if r["id"] == "U17":
            desc = "住都中心公辦、冠德出資，基地 18,365 ㎡；辦公棟 22F（88.6 m）、住宅棟 24F（89.6 m），預計 2031 完工。現住戶原地安置；「台北心軸線」New Civic Hub 核心，與南側司法園區隔市民大道相對。"
        out.append(dict(id=r["id"], kind="U", status=r["status"], short=r["short"], who=r["who"], desc=desc,
                        verify=r.get("verify"), mask=r.get("mask"), geom=("massing", r["id"])))
    for k, d in NEW.items():
        out.append(dict(id=k, geom=NEW_GEOM[k], **d))
    return out


def setup(page, doc):
    q = json.load(open(vs.EXP / "qa.json")); bb = q["bounds"]; cx = (bb[0] + bb[2]) / 2; cy = (bb[1] + bb[3]) / 2
    H, W = page.rect.height, page.rect.width; K = 72 / 25.4
    for x in page.get_contents():
        b = doc.xref_stream(x)
        f0, f1 = b.find(b".4 .4 .4 rg\n"), b.find(b".18 .18 .18 RG")  # 移除原十幅內建物深灰填色，全圖建物一致只留輪廓
        if 0 <= f0 < f1:
            b = b[:f0] + b[f1:]
        i = b.find(b".78 .06 .4 RG")
        if i < 0:
            continue
        head, tail = b[:i], b[i:]
        tail = re.sub(rb"n [\d.]+ [\d.]+ 215\.4331 144\.5669 re S\n", b"", tail)
        tail = re.sub(rb"1 1 1 rg\nn [\d.]+ [\d.]+ 48\.18898 19\.84252 re f\*\n", b"", tail)
        tail = re.sub(rb"\.1 \.13 \.15 rg\nBT [^\n]*?\((A\d\d)[^\n]*?ET\n", b"", tail)
        doc.update_stream(x, head + tail)
    for r in [fitz.Rect(100, 90, 2150, 230), fitz.Rect(100, 1250, 1500, 1650)]:
        page.add_redact_annot(r)
    page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=fitz.PDF_REDACT_LINE_ART_NONE)
    s = page.new_shape(); s.draw_rect(fitz.Rect(1800, 1540, 2250, 1640)); s.finish(color=None, fill=(1, 1, 1)); s.commit()
    page.insert_font(fontname="hl", fontfile=vs.FONT_L); page.insert_font(fontname="hm", fontfile=vs.FONT_M)
    fl, fm = fitz.Font(fontfile=vs.FONT_L), fitz.Font(fontfile=vs.FONT_M)
    VIEW = box(*bb)

    class D:
        pass
    d = D(); d.page, d.W, d.bb, d.VIEW, d.fl, d.fm = page, W, bb, VIEW, fl, fm
    d.tf = lambda x, y: fitz.Point((420.5 + (x - cx) / 10) * K, H - (365 + (y - cy) / 10) * K)
    d.cy = cy

    def text(x, y, s_, size, font="hl", color=INK, align="L"):
        w = (fm if font == "hm" else fl).text_length(s_, fontsize=size)
        x = x - w if align == "R" else x - w / 2 if align == "C" else x
        page.insert_text((x, y), s_, fontsize=size, fontname=font, color=color); return w

    def wrap(s_, size, width):
        lines, cur = [], ""
        for ch in s_:
            if fl.text_length(cur + ch, fontsize=size) > width:
                lines.append(cur); cur = ch
            else:
                cur += ch
        return lines + ([cur] if cur else [])

    def rings(g):
        out = []
        for p in getattr(g, "geoms", [g]):
            if p.geom_type == "Polygon" and not p.is_empty:
                out += [[d.tf(*c[:2]) for c in r.coords] for r in [p.exterior] + list(p.interiors)]
        return out

    def draw(g, col, op, width, dashes=None, stroke=True, fill=None):
        if g is None or g.is_empty:
            return
        s_ = page.new_shape()
        for ring in rings(g):
            s_.draw_polyline(ring)
        s_.finish(color=col if stroke else None, fill=fill if fill is not None else col, fill_opacity=op, width=width,
                  dashes=dashes, closePath=True, even_odd=True); s_.commit()

    def hatch(g, col, step=14, width=0.35):
        g = g.intersection(VIEW); minx, miny, maxx, maxy = g.bounds; s_ = page.new_shape(); n = 0; h = maxy - miny
        for x0 in range(int(minx - h), int(maxx) + 1, step):
            seg = LineString([(x0, miny), (x0 + h, maxy)]).intersection(g)
            for l in getattr(seg, "geoms", [seg]):
                if l.geom_type == "LineString" and l.length > 0:
                    s_.draw_line(d.tf(*l.coords[0]), d.tf(*l.coords[-1])); n += 1
        if n:
            s_.finish(color=col, width=width, stroke_opacity=.75); s_.commit()

    def chip(x, y, key, size=10):
        label, col = STATUS[key]; w = fm.text_length(label, fontsize=size) + 14
        s_ = page.new_shape(); s_.draw_rect(fitz.Rect(x, y - size - 3, x + w, y + 4))
        if key == "closed":
            s_.finish(color=hex2rgb(col), fill=(1, 1, 1), width=1.0, dashes="[3 2] 0")
        else:
            s_.finish(color=None, fill=hex2rgb(col))
        s_.commit(); text(x + 7, y, label, size, "hm", hex2rgb(col) if key == "closed" else (1, 1, 1)); return w

    def badge(c, col, closed, r=8.5, kind="U"):
        s_ = page.new_shape()
        if kind == "U":
            s_.draw_circle(c, r)
        else:
            s_.draw_rect(fitz.Rect(c.x - r, c.y - r, c.x + r, c.y + r))
        if closed:
            s_.finish(color=col, fill=(1, 1, 1), width=1.5, dashes="[3 2] 0")
        else:
            s_.finish(color=(1, 1, 1), fill=col, width=1.0)
        s_.commit()

    def heading(x, y, t, size):
        w = fm.text_length(t, fontsize=size)
        s_ = page.new_shape(); s_.draw_rect(fitz.Rect(x - 4, y - size - 2, x + w + 8, y + 5)); s_.finish(color=None, fill=(1, 1, 1)); s_.commit()
        text(x, y, t, size, "hm")

    def rule(y, w=1.2):
        s_ = page.new_shape(); s_.draw_line(fitz.Point(115, y), fitz.Point(W - 115, y)); s_.finish(color=INK, width=w); s_.commit()

    d.text, d.wrap, d.draw, d.hatch, d.chip, d.badge, d.heading, d.rule = text, wrap, draw, hatch, chip, badge, heading, rule
    d.ytop, d.ybot = d.tf(0, bb[3]).y, d.tf(0, bb[1]).y
    d.SEGX = [(d.tf(e0, cy).x, d.tf(e1, cy).x) for e0, e1, *_ in SEG]
    return d


def segments(d, y_end):
    for i, (e0, e1, nm, rng, _) in enumerate(SEG):
        x0, x1 = d.SEGX[i]
        if i:
            s_ = d.page.new_shape(); s_.draw_line(fitz.Point(x0, d.ytop - 4), fitz.Point(x0, y_end))
            s_.finish(color=INK, width=0.6, dashes="[4 3] 0", stroke_opacity=.55); s_.commit()
        s_ = d.page.new_shape(); s_.draw_line(fitz.Point(x0 + 3, d.ybot + 14), fitz.Point(x1 - 3, d.ybot + 14)); s_.finish(color=INK, width=1.2); s_.commit()
        d.text((x0 + x1) / 2, d.ybot + 10, nm, 11, "hm", INK, "C")
        d.text((x0 + x1) / 2, d.ybot + 27, rng.split("｜")[0], 9, "hl", MUTED, "C")


def seg_index(x):
    for i, (e0, e1, *_) in enumerate(SEG):
        if x < e1:
            return i
    return len(SEG) - 1


def scalebar(d, sx=1960, sy=222):
    for k in range(4):
        s_ = d.page.new_shape(); s_.draw_rect(fitz.Rect(sx + k * 70.866, sy, sx + (k + 1) * 70.866, sy + 7))
        s_.finish(color=INK, fill=INK if k % 2 == 0 else (1, 1, 1), width=.6); s_.commit()
    for k, t in [(0, "0"), (2, "500"), (4, "1000 m")]:
        d.text(sx + k * 70.866, sy + 19, t, 8.5, "hl", MUTED, "C" if k else "L")


def footer(d, extra=""):
    d.text(115, 1643, "資料：臺北市都發局歷年計畫索引與計畫書（查詢 2026-10-05）；案件階段沿用《簡要標記 v2》《公共都更與公共建設編號圖》（查核 2026-10-04）；地號：臺北市地籍 GIS；現況建物：OSM。"
           + extra + "分段特性為規劃觀察，非法定判定。底圖 © OpenStreetMap contributors / ODbL｜100% 列印勿縮放", 9.5, "hl", MUTED)


# =============================== A：計畫範圍 ===============================
def sheet_a():
    src = fitz.open(vs.EXP / "pdf/A01_A10_Nanjing_Renai_20261005.pdf"); doc = fitz.open(); doc.insert_pdf(src, from_page=0, to_page=0)
    d = setup(doc[0], doc); page = d.page
    for nm, k in vs.DIST:
        g = vs.U[k].intersection(d.VIEW)
        if not g.is_empty:
            d.draw(g, vs.DCOL[nm], 0.12, 0.35 * 72 / 25.4)
    for nm, k in vs.DIST:
        g = vs.U[k].intersection(d.VIEW); c = g.centroid if nm == "萬華" else g.representative_point(); pt = d.tf(c.x, c.y)
        w = d.fm.text_length(nm + "區", fontsize=12) + 8
        s_ = page.new_shape(); s_.draw_rect(fitz.Rect(pt.x - 4, pt.y - 13, pt.x + w, pt.y + 4))
        s_.finish(color=vs.DCOL[nm], fill=(1, 1, 1), width=1.0, fill_opacity=.9); s_.commit()
        d.text(pt.x, pt.y, nm + "區", 12, "hm", tuple(v * .6 for v in vs.DCOL[nm]))

    OP = {"building": 0.92, "landscape": 0.40, "site": 0.18, "boundary_only": 0.20}
    CS = cases(); anchor = {}
    for c in CS:
        col = hex2rgb(STATUS[c["status"]][1]); typ = c["geom"][0]
        if typ == "massing":
            lyr = vs.massing[c["geom"][1]]; sites = [g for l, _, g in lyr if l == "site"]
            if c.get("mask"):
                for g in sites:
                    d.draw(g, None, 1.0, 0, stroke=False, fill=(1, 1, 1))
            for l, b, g in lyr:
                if l == "site":
                    d.draw(g, col, OP["boundary_only"] if b == "boundary_only" else OP["site"], 1.3 if b == "boundary_only" else 0.8,
                           "[3 1.6] 0" if b == "boundary_only" else None)
                elif l == "locator":
                    d.draw(g, col, 0, 1.3, "[2.5 1.5] 0")
            for ln in ("landscape", "building"):
                for l, b, g in lyr:
                    if l == ln:
                        d.draw(g, col, OP[ln], 0.4)
            u = unary_union([g for _, _, g in lyr])
        elif typ == "schematic":  # 無公開配置圖：依基地範圍與公開資料推估之示意量體
            site = vs.U[c["geom"][1]]
            d.draw(site, col, OP["site"] if c["id"] != "TWIN" else 0.0, 0.8)
            parts = sorted(getattr(site, "geoms", [site]), key=lambda q: q.area, reverse=True)
            if c["id"] == "TWIN":   # 依展覽模型（IMG_4905／4906／4929）：裙樓為一連續量體跨重慶北路；塔樓為圓角方形，位於各街廓中段偏南
                west, east = sorted(parts, key=lambda q: q.centroid.x)
                bridge = box(west.bounds[2] - 6, 2771262, east.bounds[0] + 6, 2771300)
                podium = unary_union([west.buffer(-5, join_style=2).buffer(-6).buffer(6),
                                      east.buffer(-5, join_style=2).buffer(-6).buffer(6), bridge])
                d.draw(podium, col, OP["landscape"], 0.6)
                # 塔樓：OSM 興建中建物輪廓「台北雙星 D1／C1」（實際施工範圍）
                for k in ("way/1502280746", "way/1502280687"):
                    d.draw(vs.osm_bld[k], col, OP["building"], 0.6)
            else:                   # 京華城：無塔樓資訊，僅以基地內縮 8 m 示意整體量體
                d.draw(parts[0].buffer(-8, join_style=2), col, 0.7, 0.5, "[2 1.2] 0")
            u = site
        elif typ == "osmset":
            blds = [vs.osm_bld[k] for k in c["geom"][1] if k in vs.osm_bld]
            u = unary_union(blds)
            site = u.buffer(18, join_style=2).buffer(-12, join_style=2)
            d.draw(site, col, OP["site"], 0.8)
            d.draw(u, col, OP["building"], 0.4)
        elif typ == "point":
            u = Point(*c["geom"][1]); d.draw(u.buffer(32), col, 0.12, 1.3, "[2.5 1.5] 0")
            pt = d.tf(*c["geom"][1]); s_ = page.new_shape(); s_.draw_circle(pt, 3.5); s_.finish(color=None, fill=col); s_.commit()
        else:
            g = c["geom"][1]; d.draw(g, col, OP["site"], 0.9); u = g
            if typ == "site+bld":
                d.draw(vs.osm_bld[c["geom"][2]], col, OP["building"], 0.4)
        anchor[c["id"]] = u
        c["seg"] = seg_index(u.centroid.x)

    order = sorted(CS, key=lambda c: anchor[c["id"]].centroid.x)
    placed = []
    for c in order:
        col = hex2rgb(STATUS[c["status"]][1]); u = anchor[c["id"]]; ce = u.centroid; ns = vs.north(ce)
        a = d.tf(ce.x, u.bounds[3] if ns else u.bounds[1])
        lab = c["short"] + (" ★" if c.get("verify") else "")
        if c["id"].startswith("U"):
            lab = c["id"] + " " + lab
        lw = d.fm.text_length(lab, fontsize=9.5) + 24
        for k in range(12):
            dy = (-30 - 19 * k) if ns else (30 + 19 * k)
            rect = fitz.Rect(a.x - 9, a.y + dy - 9, a.x + lw, a.y + dy + 9)
            if not any(rect.intersects(r_) for r_ in placed):
                break
        placed.append(rect)
        bc = fitz.Point(a.x, a.y + dy)
        s_ = page.new_shape(); s_.draw_line(a, fitz.Point(bc.x, bc.y + (8 if ns else -8)))
        s_.finish(color=col, width=0.9, dashes="[2 1.5] 0" if c["status"] == "closed" else None); s_.commit()
        wbg = d.fm.text_length(lab, fontsize=9.5)
        s_ = page.new_shape(); s_.draw_rect(fitz.Rect(bc.x + 10, bc.y - 7.5, bc.x + 15 + wbg, bc.y + 5.5)); s_.finish(color=None, fill=(1, 1, 1), fill_opacity=.85); s_.commit()
        d.badge(bc, col, c["status"] == "closed", 7.5, c["kind"])
        d.text(bc.x + 12, bc.y + 3.4, lab, 9.5, "hm")

    Y_END = 1626
    segments(d, Y_END)
    d.text(115, 118, "南京西路—仁愛路沿線｜計畫範圍 × 都市發展與都更案例", 30, "hm")
    d.text(115, 144, "底圖：A01_A10_Nanjing_Renai_20261005 第 1 頁線稿（1:10000，已移除 A01–A10 框線與框內建物填色）＋各區通盤檢討細部計畫範圍。"
           "案例依各段都市發展脈絡納入，不論現行或未來；剪影＋基地範圍表示，顏色＝推動階段。個案紅框另見《紅框範圍》圖。", 11.5, "hl", MUTED)
    x, y = 115, 176
    d.text(x, y, "推動階段", 11, "hm", MUTED); x += 60
    for i, key in enumerate(vs.STATUS_ORDER):
        x += d.chip(x, y, key)
        if i < 5:
            d.text(x + 5, y, "→", 11, "hl", MUTED); x += 20
    x += 22; x += d.chip(x, y, "closed") + 26
    d.badge(fitz.Point(x + 8, y - 4), INK, False, 7, "U"); x += 20 + d.text(x + 20, y, "都更／開發案", 11) + 16
    d.badge(fitz.Point(x + 8, y - 4), INK, False, 7, "B"); x += 20 + d.text(x + 20, y, "公共建設／公共空間／文資", 11) + 22
    for op, dashed, lab in [(0.92, False, "建物剪影"), (0.18, False, "基地範圍"), (0.2, True, "基地概括／定位（虛線）"), (0.6, True, "示意量體（無公開配置，推估）")]:
        s_ = page.new_shape(); s_.draw_rect(fitz.Rect(x, y - 10, x + 22, y + 3))
        s_.finish(color=INK, fill=INK, fill_opacity=op, width=1 if dashed else .5, dashes="[3 2] 0" if dashed else None); s_.commit()
        x += 30 + d.text(x + 30, y, lab, 11) + 18
    x, y = 115, 200
    d.text(x, y, "計畫範圍", 11, "hm", MUTED); x += 60
    for nm, k in vs.DIST:
        s_ = page.new_shape(); s_.draw_rect(fitz.Rect(x, y - 10, x + 18, y + 3)); s_.finish(color=vs.DCOL[nm], fill=vs.DCOL[nm], fill_opacity=.3, width=.8); s_.commit()
        x += 24 + d.text(x + 24, y, f"{nm}區通檢 P{k}", 11) + 14
    d.text(x + 10, y, "★ 推定待核", 11, "hl", MUTED)
    scalebar(d)

    PAD = 8; y0 = 985
    d.heading(115, y0 - 16, "分段特性", 16); d.rule(y0 - 8, 1.4)
    sb = y0
    for i, (_, _, nm, rng, txt) in enumerate(SEG):
        x0, x1 = d.SEGX[i]; cw = x1 - x0 - 2 * PAD
        d.text(x0 + PAD, y0 + 12, nm, 13, "hm"); d.text(x0 + PAD, y0 + 27, rng, 9.5, "hl", MUTED)
        ls = d.wrap(txt, 10.5, cw)
        for j, ln in enumerate(ls):
            d.text(x0 + PAD, y0 + 46 + j * 14, ln, 10.5)
        sb = max(sb, y0 + 46 + len(ls) * 14)
    ty = sb + 30
    d.heading(115, ty - 14, "都市發展與都更案例｜依所在分段排列（U 編號同《簡要標記 v2》）", 14); d.rule(ty - 6, 1.0)
    yb = []
    for i in range(len(SEG)):
        x0, x1 = d.SEGX[i]; cw = x1 - x0 - 2 * PAD; yy = ty + 8
        for c in [c for c in order if c["seg"] == i]:
            col = hex2rgb(STATUS[c["status"]][1])
            d.badge(fitz.Point(x0 + PAD + 6, yy + 3), col, c["status"] == "closed", 6, c["kind"])
            head = (c["id"] + " " if c["id"].startswith("U") else "") + c["short"] + (" ★" if c.get("verify") else "")
            d.text(x0 + PAD + 17, yy + 7, head, 10, "hm")
            w = d.chip(x0 + PAD + 17 + d.fm.text_length(head, fontsize=10) + 8, yy + 7, c["status"], 8)
            ls = d.wrap(c["who"] + "｜" + c["desc"], 9.2, cw)
            for j, ln in enumerate(ls):
                d.text(x0 + PAD, yy + 22 + j * 11.8, ln, 9.2)
            yy += 22 + len(ls) * 11.8 + 7
        yb.append(yy)
    assert max(yb) < Y_END, max(yb)
    footer(d, "雙子星裙樓、台灣心 HUB 規模、Skywalk 計畫取自展覽模型與展板（2026-10-04 拍攝）；U05 對應建物依路口象限與樓高推定；鐵道部、華山 1914、臺北機廠剪影取自 OSM 現況建物，基地範圍為建物群外包。")
    p = OUT / "市民大道_南京西至仁愛_A計畫範圍與都更案例_20261009.pdf"
    doc.set_metadata({"title": "南京西路—仁愛路沿線 計畫範圍 × 都市發展與都更案例"}); doc.save(p, garbage=3, deflate=True)
    fitz.open(p)[0].get_pixmap(dpi=72).save(str(p).replace(".pdf", "_預覽.png"))
    return order


# =============================== B：紅框範圍 ===============================
def sheet_b():
    src = fitz.open(vs.EXP / "pdf/A01_A10_Nanjing_Renai_20261005.pdf"); doc = fitz.open(); doc.insert_pdf(src, from_page=0, to_page=0)
    d = setup(doc[0], doc); page = d.page
    for nm, k in vs.DIST:  # 行政區界僅細線
        g = vs.U[k].intersection(d.VIEW)
        if not g.is_empty:
            d.draw(g, (.55, .55, .55), 0.0, 0.5, "[1 2] 0")
    d.hatch(vs.renew_area, (.35, .35, .35))
    for it in vs.items:
        d.draw(it["geom"].intersection(d.VIEW), RED, 0.07, 1.0)
    for it in vs.items:
        pt = d.tf(it["rp"].x, it["rp"].y); s_ = page.new_shape(); s_.draw_circle(pt, 6.2)
        s_.finish(color=RED, fill=(1, 1, 1), width=0.8); s_.commit()
        d.text(pt.x, pt.y + 2.9, str(it["no"]), 7.8, "hm", RED, "C")
    Y_END = 1626
    segments(d, Y_END)
    d.text(115, 118, "南京西路—仁愛路沿線｜紅框範圍：都市計畫個案與更新意圖", 30, "hm")
    d.text(115, 144, "底圖：A01_A10_Nanjing_Renai_20261005 第 1 頁線稿（1:10000，已移除 A01–A10 框線與框內建物填色）。紅框＝沿線 24 個都市計畫個案範圍（民國 90 年後公告、與原十幅相交者及臺北車站特專區），"
           "編號由西向東；斜線＝劃定更新地區。下方依分段總結更新意圖。", 11.5, "hl", MUTED)
    x, y = 115, 182
    s_ = page.new_shape(); s_.draw_rect(fitz.Rect(x, y - 10, x + 22, y + 3)); s_.finish(color=RED, fill=RED, fill_opacity=.08, width=1.1); s_.commit()
    x += 30 + d.text(x + 30, y, "都市計畫個案範圍", 11) + 22
    s_ = page.new_shape()
    for k in range(5):
        s_.draw_line(fitz.Point(x + k * 5, y + 3), fitz.Point(x + k * 5 + 10, y - 10))
    s_.finish(color=(.35, .35, .35), width=.5); s_.commit()
    x += 30 + d.text(x + 30, y, "劃定更新地區（P089016、P097017、獎勵更新地區等）", 11) + 22
    s_ = page.new_shape(); s_.draw_line(fitz.Point(x, y - 4), fitz.Point(x + 22, y - 4)); s_.finish(color=(.55, .55, .55), width=.6, dashes="[1 2] 0"); s_.commit()
    d.text(x + 30, y, "行政區通檢範圍界", 11)
    scalebar(d)

    PAD = 8; y0 = 985
    d.heading(115, y0 - 16, "各段更新意圖", 16); d.rule(y0 - 8, 1.4)
    sb = y0
    for i, (_, _, nm, rng, _) in enumerate(SEG):
        x0, x1 = d.SEGX[i]; cw = x1 - x0 - 2 * PAD
        d.text(x0 + PAD, y0 + 12, nm, 13, "hm"); d.text(x0 + PAD, y0 + 27, rng, 9.5, "hl", MUTED)
        ls = d.wrap(INTENT[i], 10.5, cw)
        for j, ln in enumerate(ls):
            d.text(x0 + PAD, y0 + 46 + j * 14, ln, 10.5)
        sb = max(sb, y0 + 46 + len(ls) * 14)
    ty = sb + 30
    d.heading(115, ty - 14, "紅框一覽｜依所在分段排列（計畫書全文與願景摘要見整合文字檔）", 14); d.rule(ty - 6, 1.0)
    yb = []
    for i in range(len(SEG)):
        x0, x1 = d.SEGX[i]; cw = x1 - x0 - 2 * PAD - 22; yy = ty + 8
        for it in [it for it in vs.items if seg_index(it["rp"].x) == i]:
            key = next(c for c in it["codes"] if c in SHORT)
            c_ = fitz.Point(x0 + PAD + 7, yy + 3); s_ = page.new_shape(); s_.draw_circle(c_, 6.6)
            s_.finish(color=RED, fill=(1, 1, 1), width=.8); s_.commit()
            d.text(c_.x, c_.y + 3, str(it["no"]), 8, "hm", RED, "C")
            codes = "／".join("P" + c for c in it["codes"][:2])
            ls = d.wrap(codes + "　" + SHORT[key], 9.6, cw)
            for j, ln in enumerate(ls):
                d.text(x0 + PAD + 20, yy + 7 + j * 12, ln, 9.6, "hl")
            yy += 7 + len(ls) * 12 + 7
        yb.append(yy)
    assert max(yb) < Y_END, max(yb)
    footer(d)
    p = OUT / "市民大道_南京西至仁愛_B紅框範圍與更新意圖_20261009.pdf"
    doc.set_metadata({"title": "南京西路—仁愛路沿線 紅框範圍：都市計畫個案與更新意圖"}); doc.save(p, garbage=3, deflate=True)
    fitz.open(p)[0].get_pixmap(dpi=72).save(str(p).replace(".pdf", "_預覽.png"))


def write_text(order):
    L = ["市民大道｜南京西路—仁愛路沿線　整合文字（A 計畫範圍 × 都市發展與都更案例｜B 紅框範圍與更新意圖）", "2026-10-09", "",
         "分段特性為規劃觀察，非法定判定；願景為計畫書文字摘要，非逐字引用；★＝推定待核。", ""]
    for i, (e0, e1, nm, rng, txt) in enumerate(SEG):
        L += ["=" * 60, f"{nm}｜{rng}", "=" * 60, "", "【分段特性】", txt, "", "【更新意圖（紅框總結）】", INTENT[i], "", "【都市發展與都更案例】"]
        for c in [c for c in order if c["seg"] == i]:
            L.append(f"{(c['id'] + ' ') if c['id'].startswith('U') else ''}{c['short']}{' ★' if c.get('verify') else ''}｜{STATUS[c['status']][0]}｜{c['who']}")
            L.append("  " + c["desc"])
        L += ["", "【紅框個案】"]
        for it in [it for it in vs.items if seg_index(it["rp"].x) == i]:
            key = next(c for c in it["codes"] if c in SHORT); vkey = next((c for c in it["codes"] if c in vs.VISION), None)
            L.append(f"#{it['no']} {'／'.join('P' + c for c in it['codes'])}｜{vs.name(it['codes'][-1])}")
            L.append("  簡述：" + SHORT[key])
            if vkey:
                L.append("  願景／目標：" + vs.VISION[vkey])
        L.append("")
    (OUT / "市民大道_南京西至仁愛_整合文字_20261009.txt").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    order = sheet_a()
    sheet_b()
    write_text(order)
    print("done")
