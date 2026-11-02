# -*- coding: utf-8 -*-
"""南京西路—仁愛路沿線｜都市計畫範圍 × 計畫願景 × 都更案（2026-10-06）。

底圖：A01_A10_Nanjing_Renai_20261005 第 1 頁線稿（移除 A01–A10 框線）＋各區通檢細部計畫範圍底色＋24 個案範圍（同《南京仁愛沿線都市計畫範圍_1-10000_A1》編號）。
疊加：都更案（剪影＋基地範圍，顏色＝推動階段，同《公共都更與公共建設編號圖》）、劃定更新地區（斜線）。
線稿四周：各計畫案願景／目標小字（摘自計畫書），下方：分段特性推估。
"""
import json, re, csv, collections, urllib.request, urllib.parse
from pathlib import Path
import fitz, os
A3 = os.environ.get("SHEET_A3") == "1"
from shapely.geometry import shape, Polygon, Point, LineString, box
from shapely.ops import unary_union, transform
from shapely import affinity
from pyproj import Transformer

ROOT = Path("/Users/ktlu/Desktop/第一次評圖/00_共用資料與整合成果")
EXP = ROOT / "03_最新產出/02_南京至仁愛擴幅_20261005"
SRC = ROOT / "04_其他疊合與排版成果/CAD及官方平面疊合/urban_plan_review/sources_current"
MASSING = ROOT / "02_調整過程/公共都更編號圖/公共案件量體與基地_EPSG3826.geojson"
OUT = Path(__file__).resolve().parents[1]
OUT_PDF = OUT / "市民大道_南京西至仁愛_都市計畫願景與都更案_20261006.pdf"
OUT_PNG = OUT / "市民大道_南京西至仁愛_都市計畫願景與都更案_20261006_預覽.png"
OUT_GEO = OUT / "都更案基地與剪影_U04-U09_EPSG3826.geojson"
FONT_L, FONT_M = "/System/Library/Fonts/STHeiti Light.ttc", "/System/Library/Fonts/STHeiti Medium.ttc"
LAND = "https://www.historygis.udd.gov.taipei/arcgis/rest/services/Urban/Land/MapServer/5/query"


def hex2rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


STATUS = {"plan": ("規劃中", "#4F79B5"), "prep": ("前期／招商", "#C08A1E"), "review": ("審議中", "#D9682B"),
          "approved": ("審議通過", "#7E57A6"), "build": ("施工中／展延", "#B8322A"), "done": ("已完成", "#2E8A57"),
          "closed": ("結案未續行", "#8C8C8C")}
STATUS_ORDER = ["plan", "prep", "review", "approved", "build", "done"]
INK, MUTED, RULE, RED = hex2rgb("#2B2B2B"), hex2rgb("#6B6B6B"), hex2rgb("#BDBDBD"), (.80, .05, .05)
DCOL = {"大同": (.95, .55, .20), "萬華": (.60, .45, .75), "中正": (.25, .55, .85), "中山": (.30, .70, .40),
        "大安": (.90, .75, .15), "松山": (.85, .35, .55), "信義": (.45, .75, .80)}
DIST = [("大同", "110002"), ("萬華", "110001"), ("中正", "111021"), ("中山", "110025"), ("大安", "110013"),
        ("松山", "108012"), ("信義", "112014")]

# ---------------- 資料 ----------------
meta = {}
for f in ["plan_metadata.json", "allplans.json"]:
    meta.update({m["projnum"]: m for m in json.load(open(SRC / f))})
cat = {r["計畫編號"][1:]: r["官方分類代碼"] for r in csv.DictReader(open(SRC / "../沿線歷年計畫索引_待效力核對.csv", encoding="utf-8-sig"))}
G, PER = collections.defaultdict(list), {}
for n in [0, 500, 1000, 1500, 2000, 2500, 3000]:
    for f in json.load(open(SRC / f"index_{n}.json"))["features"]:
        k = f["attributes"]["PROJNUM"]; PER[k] = f["attributes"]["PERIOD"]; r = f["geometry"]["rings"]
        G[k].append(Polygon(r[0], r[1:]).buffer(0))
U = {k: unary_union(v) for k, v in G.items()}
mask = shape(json.load(open(EXP / "ten_sheet_mask.geojson"))["features"][0]["geometry"])
base = lambda k: k.split("-")[0]
name = lambda k: meta.get(k, meta.get(base(k), {})).get("projname", "?")
kind = lambda k: cat.get(k, cat.get(base(k), "?"))

# 24 個案（與前圖相同之篩選與編號）
ks = [k for k in U if U[k].intersects(mask) and U[k].area < 3e6 and kind(k) in ("01", "02", "03", "05", "06", "?", "5")
      and int(PER[k]) >= 90 and not k.startswith("099039") and not k.startswith("101005") and not ("-" in k and base(k) in U)
      and U[k].intersection(mask).area >= 1000] + ["082023", "082022"]
groups = []
for k in sorted(ks, key=lambda k: (int(PER[k]), k)):
    for g in groups:
        a = U[g[0]]
        if a.intersection(U[k]).area / a.union(U[k]).area > 0.9:
            g.append(k); break
    else:
        groups.append([k])
items = []
for g in groups:
    geom = unary_union([U[k] for k in g]); rp = geom.intersection(mask).representative_point()
    dper = min([int(PER[c]) for _, c in DIST if U[c].contains(rp)] or [0])
    items.append(dict(codes=g, geom=geom, rp=rp, later=max(int(PER[k]) for k in g) >= dper))
items.sort(key=lambda it: it["rp"].x)
for i, it in enumerate(items, 1):
    it["no"] = i
by_code = {c: it for it in items for c in it["codes"]}

# 劃定更新地區
renew_area = unary_union([U[k] for k in U if U[k].intersects(mask) and (
    (kind(k) == "07" and U[k].area < 1e6) or k in ("089016", "097017"))]).intersection(mask)

# 市民大道中心線（OSM），用於判斷南北側
tr = Transformer.from_crs(4326, 3826, always_xy=True).transform
osm = json.load(open(EXP / "source/expanded_osm.geojson"))["features"]
civ = unary_union([transform(tr, shape(f["geometry"])) for f in osm
                   if f["properties"].get("highway") and f["geometry"]["type"] == "LineString"
                   and f["properties"].get("name", "").startswith("市民大道")])
osm_bld = {f["properties"].get("@id"): transform(tr, shape(f["geometry"])) for f in osm
           if "building" in f["properties"] and f["geometry"]["type"] in ("Polygon", "MultiPolygon")}


def civ_y(x):
    ln = LineString([(x, 2769000), (x, 2773000)]).intersection(civ)
    pts = [p for p in getattr(ln, "geoms", [ln]) if not p.is_empty]
    return sum(p.centroid.y for p in pts) / len(pts) if pts else 2771000


def north(pt):
    return pt.y > civ_y(pt.x)


# ---------------- 都更案 ----------------
massing = collections.defaultdict(list)
for f in json.load(open(MASSING))["features"]:
    p = f["properties"]; massing[p["case"]].append((p["layer"], p["basis"], shape(f["geometry"])))


LEAD_CACHE = OUT / "history_cache" / "lead_parcels.json"
_LEAD_CASE = {("AD0609", "175"): "U07", ("AD0704", "281"): "U08", ("AD0704", "454"): "U09"}


def lead(sect, lot):
    """主地號外界；先讀本地快取，其次舊輸出 GeoJSON，最後才查市府地籍 GIS（服務常 503）。"""
    key = f"{sect}-{lot}"
    cache = json.load(open(LEAD_CACHE)) if LEAD_CACHE.exists() else {}
    if key not in cache and OUT_GEO.exists():
        case = _LEAD_CASE.get((sect, lot))
        for f in json.load(open(OUT_GEO))["features"]:
            if f["properties"]["case"] == case and f["properties"]["layer"] == "site":
                cache[key] = f["geometry"]["coordinates"][0]
    if key not in cache:
        q = dict(where=f"SECTCODE='{sect}' AND LANDCODE='{lot}'", outFields="LANDCODE", f="json", outSR=3826, returnGeometry="true")
        fs = json.load(urllib.request.urlopen(LAND + "?" + urllib.parse.urlencode(q), timeout=90))["features"]
        cache[key] = fs[0]["geometry"]["rings"][0]
    LEAD_CACHE.parent.mkdir(exist_ok=True); json.dump(cache, open(LEAD_CACHE, "w"))
    return Polygon(cache[key])


def bld_in(site, frac=0.3, min_area=150):
    out = [b for b in osm_bld.values() if b.area > min_area and b.intersection(site).area > frac * min(b.area, site.area)]
    return unary_union(out) if out else None


u04_site = U["098027"]
u07_lead = lead("AD0609", "175"); u08_lead = lead("AD0704", "281"); u09_lead = lead("AD0704", "454")
private = {
    "U04": [("site", "parcel", u04_site), ("building", "osm", bld_in(u04_site, 0.5))],
    "U05": [("building", "osm", osm_bld["way/323685744"])],
    "U06": [("building", "osm", osm_bld["way/323665765"])],
    "U07": [("site", "parcel", u07_lead), ("building", "osm", bld_in(u07_lead))],
    "U08": [("site", "boundary_only", u08_lead), ("locator", "boundary_only", u08_lead.centroid.buffer(28))],
    "U09": [("site", "boundary_only", u09_lead), ("locator", "boundary_only", u09_lead.centroid.buffer(28))],
}
for k, v in private.items():
    massing[k] = [(l, b, g) for l, b, g in v if g is not None]
json.dump({"type": "FeatureCollection", "crs": {"type": "name", "properties": {"name": "EPSG:3826"}},
           "features": [{"type": "Feature", "properties": {"case": k, "layer": l, "basis": b},
                         "geometry": json.loads(json.dumps(g.__geo_interface__))} for k, v in private.items() for l, b, g in v if g is not None]},
          open(OUT_GEO, "w"), ensure_ascii=False)

RENEW = [  # 同《簡要標記 v2》U 編號；west→east 於繪圖時排序
    dict(id="U01", desc="鐵道局公有地都更，更新單元 17 筆約 1.6 ha，位於北門與車站西側；2023 報核、2024 公展，考古試掘與文資修復同步進行。未來為博物館特專區＋商業，臨鄭州路留 10 m 帶狀開放空間。", status="review", short="臺北車站 E1／E2", who="公有地都更｜鐵道局", note="2023 報核、2024 公展；考古試掘與文資修復同步"),
    dict(id="U17", desc="住都中心公辦、冠德實施，行二行三 46 筆約 1.84 ha；2024-12 完成都更審議。配置行政辦公主體＋住宅 A–C 棟＋中庭與開放廣場，現住戶原地安置；與南側司法園區隔市民大道相對。", status="approved", short="台灣心 HUB（行二行三）", who="公辦｜住都中心／冠德", note="2024-12 完成都更審議；行政辦公＋住宅＋中庭廣場", mask=True),
    dict(id="U04", desc="「臺北好好看」專案，市民大道三段×建國南路，東西兩基地約 0.9 ha，2016 完成；以廣場式開放空間、地面人行通道換取容積獎勵，是沿線少數已兌現的地面開放空間樣本。", status="done", short="明日博／懷生段931", who="私人｜「臺北好好看」", note="2016 完成；東西兩基地，廣場式開放空間＋地面人行通道"),
    dict(id="U02", desc="住都中心公辦、潤泰創新實施，5 筆約 0.45 ha；2025-11 公展、12 月公辦公聽會，審議中。23 層住宅，1F 托嬰中心＋店鋪，臨市民大道退縮約 17 m 開放空間（建蔽約 35%）。", status="review", short="長安市民公辦都更", who="公辦｜住都中心／潤泰", note="2025-11 公展；23F 住宅，1F 托嬰＋店鋪，臨市民大道退縮約 17 m", mask=True),
    dict(id="U03", desc="原中油加油站用地（P092003／P093011 變更），4 筆約 0.41 ha；2026-05 選定公辦都更，招商準備中、尚無配置。位於市民大道與八德路之間，可能改變南北穿越路徑。", status="prep", short="中油中山公辦都更", who="公辦｜前期", note="2026-05 選定；原加油站，4,107 ㎡"),
    dict(id="U05", desc="德杰案，延吉段三小段 831-1 等，敦化×市民東北角；已完成並成果備查。剪影以東北角 22F 敦南樞苑推定，待核。", status="done", short="德杰（敦化×市民 東北）", who="私人", note="完成成果備查；剪影以東北角 22F 敦南樞苑推定★", verify=True),
    dict(id="U06", desc="富邦案，仁愛段六小段 245-2 等，敦化×市民東南角；已完成（富邦敦南大樓）。與 U05 分屬道路兩側，可比較不同退縮與商業介面。", status="done", short="富邦（敦化×市民 東南）", who="私人", note="完成成果備查；剪影＝富邦敦南大樓"),
    dict(id="U07", desc="麗寶案，延吉段一小段 175 等，光復×市民西北角；已完成並成果備查，代表光復節點既有更新成果。", status="done", short="麗寶（光復×市民 西北）", who="私人", note="完成成果備查；主地號 175＋所在建物"),
    dict(id="U08", desc="青園案，西松段三小段 281 等 18 筆，光復南路 13、17 巷；2026 申請審查、尚未核定。後續看更新範圍與巷道通行設計。", status="review", short="青園（光復 13、17 巷）", who="私人｜申請審查", note="2026 申請審查；僅主地號定位（虛線圈）"),
    dict(id="U09", desc="馗豐案，西松段三小段 454 等 43 筆，八德路 72、106 巷；2026-06 申請審查，舊事業概要與本次申請需分開辨識。", status="review", short="馗豐（八德 72、106 巷）", who="私人｜申請審查", note="2026-06 申請審查；僅主地號定位（虛線圈）"),
    dict(id="U10", desc="公辦案，西松段三小段 58 等 33 筆約 0.39 ha，臺北機廠北側；2025-10 因所有權人意願未達門檻結案。保留對照，顯示小街廓整合困難。", status="closed", short="機廠北側 7599", who="公辦｜已停止", note="2025-10 結案；保留對照"),
]

# ---------------- 願景小字（摘自各案計畫書；代表編號 → 文字） ----------------
VISION = {
    "108001": "文資保存與都更並進，引入博物館與特專區；沿市民大道與車站特專區打造東西向風廊、綠廊；臨鄭州路留 10 m 帶狀開放空間，舒緩高架壓迫感。",
    "115011": "中興院區升級重度級急救責任醫院；建蔽放寬至 55%，預留與捷運北門站地下緊急醫療連通。",
    "093040": "捷運松山線 G14 出入口、通風設施；同案劃定都市更新地區。",
    "105006": "忠孝橋引道拆除後重現北門城與城牆地景，改設廣場用地並調整忠孝西路永久路型。",
    "095016": "C1／D1 聯合開發區（捷）：機捷臺北站及軌道、服務設施，可兼供高鐵、臺鐵使用。",
    "082022": "建設臺北車站為都會主要交通運輸中心，促進市中心商業區發展並創造都市景觀。",
    "093053": "交九：長途客運、公車轉運、停車與行控中心立體共構，南北留設類通路。",
    "091007": "舊市府古蹟活化，國中用地改機關用地供美術藝文（當代館）。",
    "111010": "維護行政主體性並保障現住戶原地安置；整體都更後可設文康、餐飲零售等附屬設施 ≤30%，不得移入容積。",
    "092029": "鐵路地下化後貨運站騰空，整體規劃、整體開發；強化中央行政主體性，六條通指定商三（特）塑造商圈。",
    "114001": "部分工業區變更為大學用地及道路用地（計畫書文字待核）。",
    "093013": "「臺北好好看」老舊社區再生：廣場式開放空間、地面人行通道、挑空室內開放空間容積獎勵。",
    "108006": "TOD：捷運站周邊可申請開發許可，以容積獎勵引導站點周邊大基地加密。",
    "091017": "敦化南北路特專區：全市辦公、金融發展潛力地區，單一分區管制。",
    "097017": "市民大道為東西向重要景觀軸線：住宅為主、引入支援性商業；劃定更新地區加速老舊改建，以都市設計塑造人行空間與東西軸線意象。",
    "099046": "因應文體園區交通，北側工業區改道路，接市民大道並為臺北機廠再發展預留路網。",
    "092031": "大型室內多功能體育館＋菸廠古蹟保存再利用；文化體育為主、商業休閒為輔。",
    "103018": "原唐榮鐵工廠多目標開發（購物中心、旅館、辦公等 6 類）；刪除大街廓整體開發，改 2 區開發。",
    "109004": "老舊中低層社區專案更新：住三（特），總容積上限 2 倍法定容積。",
    "093038": "鐵路地下化後整合台鐵、捷運之東區轉運樞紐；鐵路用地改交通用地、打通東西向道路。",
    "096016": "臺北郵電大樓古蹟保存，郵政電信用地改學校及郵政用地供交通大學撥用；古蹟不得新增建。",
    "107017": "臺鐵資產活化：D1 西半、E1、E2 由商業、交通用地變更為特定專用區、博物館特定專用區及道路用地（約 4.5 ha），重現鐵道工業遺構價值。",
    "092003-07": "中油十六處加油站用地依區位轉作商三（特）、住宅區、公園或停車場；沿線一處現為中油中山公辦都更（U03）。",
    "090031": "鐵路地下化東延南港：沿線土地改交通用地，地下供隧道與連續壁、地面作平面道路或綠地。",
}
PRINCIPLE = {  # 紅框原則（保留編號者）
    "108001": "文資保存與特專區開發並行；臨鄭州路留 10 m 帶狀開放空間，沿市民大道塑造東西向風廊、綠廊。",
    "107017": "鐵路相關公設用地轉為博物館特專區與特專區；須劃設不低於轉用面積 10% 之公園、綠地或廣場。",
    "095016": "商業用地改聯合開發區（捷）：軌道與車站設施優先，可兼供高鐵、臺鐵使用。",
    "111010": "維持行政專用區之行政主體；整體都更才放寬附屬使用 ≤30%，並禁止移入容積。",
    "092029": "整體規劃、整體開發：南側行政／創意文化專用區；北側六條通改商三（特），但維持原住宅強度。",
    "093013": "劃定更新單元；以廣場式開放空間、地面人行通道、挑空空間換取容積獎勵，東西基地容積可調配。",
    "108006": "捷運站周邊大基地可申請開發許可，以公共貢獻換容積獎勵，引導站點加密。",
    "092031": "工業區改特定專用區：文化體育為主、商業休閒為輔；建蔽原則 ≤60%，開發須經都審。",
    "097017": "容積不變、只放寬使用組別（住三之一／住四之一（特））；劃更新地區並以都市設計管制人行空間與退縮。",
    "103018": "商三（特）限 6 類使用，原規定捐地 30% 作公園廣場；取消大街廓整體開發，改 2 區開發。",
}
KEEP = set(PRINCIPLE)

DVISION = {"中正": "中正區通檢：市民大道以南設行政專用區（強化中央行政主體）、資訊產業專用區、創意文化專用區（華山）。"}

SEG = [  # (起 E, 迄 E, 名稱, 範圍, 特性推估)
    (300935, 302570, "S1 西端車站段", "環河北路—中山北路｜大同、中正",
     "計畫屬性：臺北車站特定專用區＋多件交通／文資個案（雙子星、E1／E2、交九、北門廣場、當代館）。都更：公有地都更（U01）為主，私人都更幾乎不存在。"
     "推估：由「交通樞紐＋文資」主導，土地多為公有、變動大且集中；未來 10 年增量最大的是辦公、旅館與觀光人流，市民大道在此是車站南北兩側的縫。"),
    (302570, 303400, "S2 華山行政段", "中山北路—新生北路｜中正、中山",
     "計畫屬性：華山整體計畫（行政專用區、創意文化專用區）＋行二行三修訂。都更：台灣心 HUB 公辦都更（U17）。"
     "推估：南側為中央行政與文創大街廓、北側為六條通商三（特）餐飲街區，形成「南側機關／北側餐飲」的互補；司法園區與 HUB 完工後平日午間跨越最集中。"),
    (303400, 304930, "S3 生活街區段", "新生北路—復興南路｜中山、大安",
     "計畫屬性：P097017 兩側住三之一（特）＋更新地區、TOD 站點（忠孝新生）、北科擴校、懷生段臺北好好看。都更：公辦 U02、U03 審議／招商中，U04 已完成。"
     "推估：沿線最典型的「老舊住宅逐棟更新」段；容積不增但開放支援性商業，未來變化是沿街一樓活化與退縮開放空間逐步連成，屬漸進型、生活型人流。"),
    (304930, 306100, "S4 敦化辦公段", "復興南路—光復南路｜松山、大安",
     "計畫屬性：敦化南北路特專區、兩側住四之一（特）、TOD（忠孝復興）。都更：U05、U06 已完成，敦化路口兩側已有更新成果。"
     "推估：辦公金融走廊與高密度住宅交會，現況已相對成熟、變動小；可用 U05／U06 比較兩側不同退縮與商業介面，作為橋下銜接的既有樣本。"),
    (306100, 307545, "S5 文體與機廠段", "光復南路—基隆路｜信義、松山",
     "計畫屬性：松菸特專區（大巨蛋）、北側道路、唐榮（京華城）、松山車站（東界外延）。都更：U07 已完成，U08、U09 申請審查，U10 結案。"
     "推估：由大型文化體育與商業設施主導，人流呈「活動散場」型尖峰；北側臺北機廠與南側巨蛋形成南北軸，八德路以北小街廓都更正在啟動但整合不易。"),
]


def main():
    q = json.load(open(EXP / "qa.json")); bb = q["bounds"]; cx = (bb[0] + bb[2]) / 2; cy = (bb[1] + bb[3]) / 2
    VIEW = box(*bb)
    src = fitz.open(EXP / "pdf/A01_A10_Nanjing_Renai_20261005.pdf"); doc = fitz.open(); doc.insert_pdf(src, from_page=0, to_page=0)
    page = doc[0]; H, W = page.rect.height, page.rect.width; K = 72 / 25.4

    def tf(x, y):
        return fitz.Point((420.5 + (x - cx) / 10) * K, H - (365 + (y - cy) / 10) * K)

    for x in page.get_contents():  # 移除 A01–A10 框線
        b = doc.xref_stream(x); i = b.find(b".78 .06 .4 RG")
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

    page.insert_font(fontname="hl", fontfile=FONT_L); page.insert_font(fontname="hm", fontfile=FONT_M)
    fl, fm = fitz.Font(fontfile=FONT_L), fitz.Font(fontfile=FONT_M)

    def text(x, y, s_, size, font="hl", color=INK, align="L"):
        w = (fm if font == "hm" else fl).text_length(s_, fontsize=size)
        x = x - w if align == "R" else x - w / 2 if align == "C" else x
        page.insert_text((x, y), s_, fontsize=size, fontname=font, color=color); return w

    def wrap(s_, size, width, font=None):
        f = font or fl; lines, cur = [], ""
        for ch in s_:
            if f.text_length(cur + ch, fontsize=size) > width:
                lines.append(cur); cur = ch
            else:
                cur += ch
        return lines + ([cur] if cur else [])

    def rings(g):
        out = []
        for p in getattr(g, "geoms", [g]):
            if p.geom_type == "Polygon" and not p.is_empty:
                out += [[tf(*c[:2]) for c in r.coords] for r in [p.exterior] + list(p.interiors)]
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
        g = g.intersection(VIEW); minx, miny, maxx, maxy = g.bounds; s_ = page.new_shape(); n = 0
        d = maxy - miny
        for x0 in range(int(minx - d), int(maxx) + 1, step):
            seg = LineString([(x0, miny), (x0 + d, maxy)]).intersection(g)
            for l in getattr(seg, "geoms", [seg]):
                if l.geom_type == "LineString" and l.length > 0:
                    s_.draw_line(tf(*l.coords[0]), tf(*l.coords[-1])); n += 1
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

    def badge(c, label, col, closed, r=11, shape_="U", fs=None):
        s_ = page.new_shape()
        if shape_ == "U":
            s_.draw_circle(c, r)
        else:
            s_.draw_rect(fitz.Rect(c.x - r, c.y - r, c.x + r, c.y + r))
        if closed:
            s_.finish(color=col, fill=(1, 1, 1), width=1.5, dashes="[3 2] 0")
        else:
            s_.finish(color=(1, 1, 1), fill=col, width=1.0)
        s_.commit(); fs = fs or r * 0.95
        text(c.x, c.y + fs * 0.36, label, fs, "hm", col if closed else (1, 1, 1), "C")

    # ---------- 1. 計畫範圍底圖 ----------
    for nm, k in DIST:
        g = U[k].intersection(VIEW)
        if not g.is_empty:
            draw(g, DCOL[nm], 0.11, 0.35 * K)
    for nm, k in DIST:
        g = U[k].intersection(VIEW); c = g.centroid if nm == "萬華" else g.representative_point(); pt = tf(c.x, c.y)
        w = fm.text_length(nm + "區", fontsize=12) + 8
        s_ = page.new_shape(); s_.draw_rect(fitz.Rect(pt.x - 4, pt.y - 13, pt.x + w, pt.y + 4))
        s_.finish(color=DCOL[nm], fill=(1, 1, 1), width=1.0, fill_opacity=.9); s_.commit()
        text(pt.x, pt.y, nm + "區", 12, "hm", tuple(v * .6 for v in DCOL[nm]))
    hatch(renew_area, (.35, .35, .35))
    for it in items:
        draw(it["geom"].intersection(VIEW), RED, 0.05, 1.1 if it["later"] else 0.8, None if it["later"] else "[3 1.5] 0")
    for it in items:
        it["key"] = next((c for c in it["codes"] if c in KEEP), None)
        if not it["key"]:
            continue
        pt = tf(it["rp"].x, it["rp"].y); s_ = page.new_shape(); s_.draw_circle(pt, 5.6)
        s_.finish(color=RED, fill=(1, 1, 1), width=0.8); s_.commit()
        text(pt.x, pt.y + 2.6, str(it["no"]), 7.2, "hm", RED, "C")

    # ---------- 2. 都更案：剪影＋基地範圍 ----------
    OP = {"building": 0.92, "landscape": 0.40, "site": 0.16, "boundary_only": 0.20}
    ranchor = {}
    for r in RENEW:
        col = hex2rgb(STATUS[r["status"]][1]); lyr = massing[r["id"]]
        sites = [g for l, _, g in lyr if l == "site"]
        if r.get("mask"):
            for g in sites:
                draw(g, None, 1.0, 0, stroke=False, fill=(1, 1, 1))
        for l, b, g in lyr:
            if l == "site":
                if b == "boundary_only":
                    draw(g, col, OP["boundary_only"], 1.3, "[3 1.6] 0")
                else:
                    draw(g, col, OP["site"], 0.8)
            elif l == "locator":
                draw(g, col, 0.0, 1.3, "[2.5 1.5] 0")
        for lname in ("landscape", "building"):
            for l, b, g in lyr:
                if l == lname:
                    draw(g, col, OP[lname], 0.4)
        u = unary_union([g for _, _, g in lyr]); ranchor[r["id"]] = u
    # 都更編號牌：北側案向上、南側案向下，各自一層錯開
    order = sorted(RENEW, key=lambda r: ranchor[r["id"]].centroid.x)
    last = {True: [-1e9, -1e9], False: [-1e9, -1e9]}
    for r in order:
        col = hex2rgb(STATUS[r["status"]][1]); u = ranchor[r["id"]]; c = u.centroid; nside = north(c)
        a = tf(c.x, u.bounds[3] if nside else u.bounds[1])
        lab = r["id"] + " " + r["short"] + (" ★" if r.get("verify") else "")
        lw = fm.text_length(lab, fontsize=9.5) + 30
        lvl = 0 if last[nside][0] < a.x - 12 else 1
        last[nside][lvl] = a.x + lw
        dy = (-34 - 22 * lvl) if nside else (34 + 22 * lvl)
        bc = fitz.Point(a.x, a.y + dy)
        s_ = page.new_shape(); s_.draw_line(a, fitz.Point(bc.x, bc.y + (9 if nside else -9)))
        s_.finish(color=col, width=0.9, dashes="[2 1.5] 0" if r["status"] == "closed" else None); s_.commit()
        wbg = fm.text_length(lab, fontsize=9.5)
        s_ = page.new_shape(); s_.draw_rect(fitz.Rect(bc.x + 11, bc.y - 7.5, bc.x + 16 + wbg, bc.y + 5.5))
        s_.finish(color=None, fill=(1, 1, 1), fill_opacity=.85); s_.commit()
        badge(bc, "", col, r["status"] == "closed", 8.5)
        text(bc.x + 13, bc.y + 3.4, lab, 9.5, "hm", INK)

    # ---------- 3. 分段刻度（垂直線延伸至下方文字欄） ----------
    ytop, ybot = tf(0, bb[3]).y, tf(0, bb[1]).y
    SEGX = [(tf(e0, cy).x, tf(e1, cy).x) for e0, e1, *_ in SEG]
    Y_END = 1626
    for i, (e0, e1, nm, rng, _) in enumerate(SEG):
        x0, x1 = SEGX[i]
        if i:
            s_ = page.new_shape(); s_.draw_line(fitz.Point(x0, ytop - 4), fitz.Point(x0, Y_END))
            s_.finish(color=INK, width=0.6, dashes="[4 3] 0", stroke_opacity=.55); s_.commit()
        s_ = page.new_shape(); s_.draw_line(fitz.Point(x0 + 3, ybot + 14), fitz.Point(x1 - 3, ybot + 14)); s_.finish(color=INK, width=1.2); s_.commit()
        text((x0 + x1) / 2, ybot + 10, nm, 11, "hm", INK, "C")
        text((x0 + x1) / 2, ybot + 27, rng.split("｜")[0], 9, "hl", MUTED, "C")

    # ---------- 5. 標題、圖例 ----------
    text(115, 118, "南京西路—仁愛路沿線｜都市計畫範圍 × 計畫願景 × 都更案", 30, "hm")
    text(115, 144, "底圖：A01_A10_Nanjing_Renai_20261005 第 1 頁線稿（" + ("A3 縮印，約 1:20000，以比例尺為準" if A3 else "1:10000") + "，已移除 A01–A10 框線）＋各區通檢細部計畫範圍底色＋沿線 24 個案範圍（紅框，編號同《南京仁愛沿線都市計畫範圍》）。"
         "紅框僅保留與都更、分段判斷直接相關之 10 個編號（原則見下方），其餘紅框只示範圍；24 案願景摘要見文字檔；都更案以剪影與基地範圍表示，顏色＝推動階段；下方文字欄以圖上分段垂直線劃分。", 11.5, "hl", MUTED)
    x, y = 115, 176
    text(x, y, "都更推動階段", 11, "hm", MUTED); x += 76
    for i, key in enumerate(STATUS_ORDER):
        x += chip(x, y, key)
        if i < len(STATUS_ORDER) - 1:
            text(x + 5, y, "→", 11, "hl", MUTED); x += 20
    x += 22; x += chip(x, y, "closed") + 26
    for op, dashed, lab in [(0.92, False, "建物剪影（公開方案描繪或現況建物）"), (0.16, False, "都更基地（地號外界）"), (0.2, True, "基地概括／主地號定位（虛線）")]:
        s_ = page.new_shape(); s_.draw_rect(fitz.Rect(x, y - 10, x + 22, y + 3))
        s_.finish(color=INK, fill=INK, fill_opacity=op, width=1 if dashed else .5, dashes="[3 2] 0" if dashed else None); s_.commit()
        x += 30 + text(x + 30, y, lab, 11) + 22
    x, y = 115, 200
    text(x, y, "計畫範圍", 11, "hm", MUTED); x += 76
    for nm, _ in DIST:
        s_ = page.new_shape(); s_.draw_rect(fitz.Rect(x, y - 10, x + 18, y + 3)); s_.finish(color=DCOL[nm], fill=DCOL[nm], fill_opacity=.3, width=.8); s_.commit()
        x += 24 + text(x + 24, y, nm, 11) + 12
    x += 10
    s_ = page.new_shape(); s_.draw_rect(fitz.Rect(x, y - 10, x + 22, y + 3)); s_.finish(color=RED, fill=RED, fill_opacity=.08, width=1.1); s_.commit()
    x += 30 + text(x + 30, y, "個案範圍（實線晚於該區通檢／虛線早於，效力待核）", 11) + 22
    s_ = page.new_shape(); s_.draw_rect(fitz.Rect(x, y - 10, x + 22, y + 3)); s_.finish(color=RULE, width=.5); s_.commit()
    hatch_demo = box(0, 0, 1, 1)
    s_ = page.new_shape()
    for k in range(5):
        s_.draw_line(fitz.Point(x + k * 5, y + 3), fitz.Point(x + k * 5 + 10, y - 10))
    s_.finish(color=(.35, .35, .35), width=.5); s_.commit()
    x += 30 + text(x + 30, y, "劃定更新地區（P089016、P097017、獎勵更新地區等）", 11) + 22
    text(x, y, "★ 推定待核", 11, "hl", MUTED)
    sx, sy = 1960, 222   # 比例尺
    for k in range(4):
        s_ = page.new_shape(); s_.draw_rect(fitz.Rect(sx + k * 70.866, sy, sx + (k + 1) * 70.866, sy + 7))
        s_.finish(color=INK, fill=INK if k % 2 == 0 else (1, 1, 1), width=.6); s_.commit()
    for k, t in [(0, "0"), (2, "500"), (4, "1000 m")]:
        text(sx + k * 70.866, sy + 19, t, 8.5, "hl", MUTED, "C" if k else "L")

    # ---------- 6. 分段特性（欄位＝分段垂直線） ----------
    y0 = 985
    def heading(x, y, t, size):
        w = fm.text_length(t, fontsize=size)
        s_ = page.new_shape(); s_.draw_rect(fitz.Rect(x - 4, y - size - 2, x + w + 8, y + 5)); s_.finish(color=None, fill=(1, 1, 1)); s_.commit()
        text(x, y, t, size, "hm")
    heading(115, y0 - 16, "分段特性｜以都市計畫與都更案推估（規劃觀察，非法定判定）", 16)
    s_ = page.new_shape(); s_.draw_line(fitz.Point(115, y0 - 8), fitz.Point(W - 115, y0 - 8)); s_.finish(color=INK, width=1.4); s_.commit()
    PAD = 8
    seg_bottom = y0
    for i, (_, _, nm, rng, txt) in enumerate(SEG):
        x0, x1 = SEGX[i]; cw = x1 - x0 - 2 * PAD
        text(x0 + PAD, y0 + 12, nm, 13, "hm"); text(x0 + PAD, y0 + 27, rng, 9.5, "hl", MUTED)
        lines = wrap(txt, 10, cw)
        for j, ln in enumerate(lines):
            text(x0 + PAD, y0 + 45 + j * 13.4, ln, 10)
        seg_bottom = max(seg_bottom, y0 + 45 + len(lines) * 13.4)

    # ---------- 6b. 紅框原則（欄位＝分段垂直線） ----------
    py = seg_bottom + 30
    heading(115, py - 14, "紅框原則｜保留編號之都市計畫個案，其管制原則簡述（其餘紅框僅示範圍，見文字檔）", 14)
    s_ = page.new_shape(); s_.draw_line(fitz.Point(115, py - 6), fitz.Point(W - 115, py - 6)); s_.finish(color=INK, width=1.0); s_.commit()
    pb = []
    for i, (e0, e1, *_r) in enumerate(SEG):
        x0, x1 = SEGX[i]; cw = x1 - x0 - 2 * PAD; yy = py + 8
        sel = [it for it in items if it.get("key") and (e0 <= it["rp"].x < e1 or (i == 0 and it["rp"].x < e0) or (i == len(SEG) - 1 and it["rp"].x >= e1))]
        for it in sel:
            c = fitz.Point(x0 + PAD + 6, yy + 3); s_ = page.new_shape(); s_.draw_circle(c, 6.2); s_.finish(color=RED, fill=(1, 1, 1), width=.8); s_.commit()
            text(c.x, c.y + 2.9, str(it["no"]), 7.6, "hm", RED, "C")
            text(x0 + PAD + 17, yy + 7, "／".join("P" + c_ for c_ in it["codes"][:2]), 9.5, "hm", RED)
            lines = wrap(PRINCIPLE[it["key"]], 9.6, cw)
            for j, ln in enumerate(lines):
                text(x0 + PAD, yy + 21 + j * 12.4, ln, 9.6)
            yy += 21 + len(lines) * 12.4 + 8
        pb.append(yy)
    seg_bottom = max(pb)

    # ---------- 7. 都更案小解釋（依所在分段歸欄） ----------
    ty = seg_bottom + 30
    heading(115, ty - 16, "都更案說明｜依所在分段排列（U 編號同《市民大道_都市計畫都更_簡要標記_v2》；U11–U16 位於圖外東段）", 14)
    s_ = page.new_shape(); s_.draw_line(fitz.Point(115, ty - 8), fitz.Point(W - 115, ty - 8)); s_.finish(color=INK, width=1.0); s_.commit()
    def seg_of(r):
        x = ranchor[r["id"]].centroid.x
        return next(i for i, (e0, e1, *_) in enumerate(SEG) if (e0 <= x < e1) or i == len(SEG) - 1)
    yb = []
    for i in range(len(SEG)):
        x0, x1 = SEGX[i]; cw = x1 - x0 - 2 * PAD; yy = ty + 8
        for r in [r for r in order if seg_of(r) == i]:
            col = hex2rgb(STATUS[r["status"]][1])
            badge(fitz.Point(x0 + PAD + 7, yy + 3), "", col, r["status"] == "closed", 7)
            head = r["id"] + " " + r["short"] + (" ★" if r.get("verify") else "")
            text(x0 + PAD + 19, yy + 7, head, 10.5, "hm")
            cwid = chip(x0 + PAD + 19, yy + 23, r["status"], 8.5)
            text(x0 + PAD + 25 + cwid, yy + 23, r["who"], 9, "hl", MUTED)
            lines = wrap(r["desc"], 9.6, cw)
            for j, ln in enumerate(lines):
                text(x0 + PAD, yy + 38 + j * 12.4, ln, 9.6)
            yy += 38 + len(lines) * 12.4 + 10
        yb.append(yy)
    assert max(yb) < Y_END, max(yb)
    text(115, 1643, "資料：臺北市都發局歷年計畫索引與計畫書（查詢 2026-10-05）；都更階段沿用《簡要標記 v2》《公共都更與公共建設編號圖》（查核 2026-10-04）；地號：臺北市地籍 GIS；現況建物：OSM。"
         "U05 對應建物係依路口象限與樓高推定。底圖 © OpenStreetMap contributors / ODbL｜100% 列印勿縮放", 9.5, "hl", MUTED)

    if not A3:
        write_text(order, seg_of)
    doc.set_metadata({"title": "南京西路—仁愛路沿線 都市計畫範圍 × 計畫願景 × 都更案", "creationDate": "D:20261006"})
    if A3:  # A1 → A3：向量等比縮 0.5（841×594 → 420×297 mm）
        a3 = fitz.open(); W3, H3 = fitz.paper_size("a3-l")
        a3.new_page(width=W3, height=H3).show_pdf_page(fitz.Rect(0, 0, W3, H3), doc, 0)
        a3.set_metadata(doc.metadata)
        out = OUT_PDF.with_name(OUT_PDF.stem + "_A3.pdf")
        a3.save(out, garbage=3, deflate=True); a3[0].get_pixmap(dpi=150).save(out.with_suffix(".png"))
        print(out); return
    doc.save(OUT_PDF, garbage=3, deflate=True)
    fitz.open(OUT_PDF)[0].get_pixmap(dpi=72).save(OUT_PNG)
    print(OUT_PDF)


def write_text(order, seg_of):
    L = ["市民大道｜南京西路—仁愛路沿線　都市計畫範圍 × 計畫願景 × 都更案　整合文字", "2026-10-06", "",
         "資料：臺北市都發局歷年計畫索引與計畫書（查詢 2026-10-05）；都更階段沿用《市民大道_都市計畫都更_簡要標記_v2》"
         "《公共都更與公共建設編號圖》（查核 2026-10-04）；地號：臺北市地籍 GIS；現況建物：OSM。",
         "分段特性為規劃觀察，非法定判定；願景為計畫書文字摘要，非逐字引用；★＝推定待核。", ""]
    for i, (e0, e1, nm, rng, txt) in enumerate(SEG):
        L += ["=" * 60, f"{nm}｜{rng}", "=" * 60, "", "【分段特性】", txt, "", "【都更案】"]
        rs = [r for r in order if seg_of(r) == i]
        for r in rs:
            L.append(f"{r['id']} {r['short']}{' ★' if r.get('verify') else ''}｜{STATUS[r['status']][0]}｜{r['who']}")
            L.append("  " + r["desc"])
        if not rs:
            L.append("（無）")
        L += ["", "【沿線都市計畫個案（圖上紅框編號）】"]
        for it in items:
            if e0 <= it["rp"].x < e1 or (i == len(SEG) - 1 and it["rp"].x >= e1) or (i == 0 and it["rp"].x < e0):
                code = next((c for c in it["codes"] if c in VISION), None)
                L.append(f"#{it['no']} {'／'.join('P' + c for c in it['codes'])}｜{name(it['codes'][-1])}")
                L.append("  願景／目標：" + (VISION[code] if code else "（見計畫名稱）"))
                if it.get("key"):
                    L.append("  管制原則（圖上保留編號）：" + PRINCIPLE[it["key"]])
        L.append("")
    L += ["=" * 60, "行政區通盤檢討（底色）", "=" * 60]
    for nm, k in DIST:
        L.append(f"{nm}區｜P{k}｜{name(k)}")
    for nm, t in DVISION.items():
        L.append("  " + t)
    (OUT / "市民大道_南京西至仁愛_都市計畫願景與都更案_整合文字_20261006.txt").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    main()
