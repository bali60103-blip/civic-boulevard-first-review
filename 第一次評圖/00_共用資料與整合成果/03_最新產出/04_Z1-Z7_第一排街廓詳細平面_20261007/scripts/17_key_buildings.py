# 重點建物判定（實驗：先做 Z1）— 依「市民高架沿線_設計介入單元分段_workflow_20261009_修訂1」之規則
#   A 主角構成：workflow 三「現行分段」該單元主角（Z1＝河岸門戶＋北門古蹟群＋台北雙子星，含 B02 跨堤橋、西寧國宅、鐵道部、三井倉庫），
#     及四「修訂紀錄」為不切穿而移動刀位所保護之基地（四-1 B02、西寧國宅；四-2 台北雙子星 C1／D1）。
#   B 公共案件基地：workflow 二-2 疊合之公共案件（02_調整過程/公共都更編號圖/公共案件量體與基地）。
#   C 界面大型建物：workflow 一-3 界面指標「第一排街廓（距高架軸線 120 m 內）大型建物 > 2,500 m²」，未列入 A、B 者。
#   範圍＝單元兩端分段界線之間（主角基地可在第一排以外，例：北門古蹟群距軸線 200–370 m）。
#   D 主角新增人口之目的地（Z3 起，使用者 2026-10-11 指定；Z3 不用 C）：主角公辦都更（U17）完成後新增之辦公與居住人口，
#     在本單元範圍內會走去之目的地建物，分兩色——商辦／政府機關、日常生活店家（餐飲、便利超市、生活服務＝06_industry「日常生活服務」族）。
#     主角基地內現有建物以「拆除改建」處理（kind＝replaced，圖面不畫），規劃量體以酒紅剪影表示。
#   S 源頭建築＋T 目的地（Z2，使用者 2026-10-11 指定）：流向台北車站之人群的源頭建築，限 Z2 範圍內（詳見 SRC_RULE）。
#   另輸出底圖用「市民高架分隔島」：道路面（已與官方人行道整合）以外、位於高架橋面投影下或高架車道中心線 18 m 內之島塊。
import json, sys, importlib.util
from pathlib import Path
import numpy as np
from shapely.geometry import shape, mapping, box, Polygon, Point
from shapely.ops import unary_union, transform
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
ZONE = sys.argv[1] if len(sys.argv) > 1 else 'Z1'
spec = importlib.util.spec_from_file_location('sheet', H / 'scripts/02_sheet.py')
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
S.VARIANT['full'] = True
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform
PUB = H.parents[1] / '02_調整過程/公共都更編號圖/公共案件量體與基地_EPSG3826.geojson'
LARGE = 2500; FRONT_D = 120
RULES = {'Z2': 'BS', 'Z3': 'ABD', 'Z4': 'ABHP', 'Z5': 'BK', 'Z6': 'ABY', 'Z7': 'N', 'Z8': 'ABY'}   # 各單元採用之規則（預設 ABC）；Z2＝基地＋源頭建築、Z3＝主角＋基地＋目的地（使用者 2026-10-11）
#   Z4＝主角＋基地＋住宅（H）＋運動場（P）：使用者 2026-10-12 指定「Z4 主軸＝運動生活空間，調查周圍住宅數量與運動場面積、運動種類」（30_sports_housing）
#   Z5＝基地＋商業空間主題（K）：使用者 2026-10-12 指定「Z5 主題＝商業空間之密集；找可用空地、既有商業空間、既有配套措施；建國啤酒廠歸古蹟」（31_commercial_space）
#   Z6＝主角（U02 規劃量體）＋基地＋滲透場所（Y）：使用者 2026-10-12 指定「忠泰美術館那塊、瑠公圳公園、懷生國小、八德市場——空地、學生、綠地，
#       適合在高架下方做改動加強地區之間的滲透性，一樣列為主角調查」；U03 現有建物（中崙球場）畫酒紅（33_z6_permeable）
#   Z7＝夜間餐飲（N）：使用者 2026-10-12 指定「全部餐飲建物依型態分色（居酒屋／燒肉串燒、酒吧／飲酒店、宵夜小吃、一般餐飲），只計一樓；
#       OSM 判型態與營業時間、稅籍補數量」；微風廣場不列為主角；Z7 無公共案件基地（34_z7_night_dining）
#   Z8＝基地（U10）＋主角三園區（Y，資料＝35_z8_parks）：使用者 2026-10-12 指定「南北兩側園區串連」——松山文創園區、臺北大巨蛋（南）、
#       國家鐵道博物館（北）之建物（酒紅）與戶外空間（淡酒紅）；不用 C（界面大型建物）
RULE = RULES.get(ZONE, 'ABC')

# 單元範圍（兩端分段界線之間）
CUTS = [shape(f['geometry']) for f in S.ZF if 'cut' in f['properties']]
k = int(ZONE[1:])
def slab_of(k):
    L = list(CUTS[k - 1].coords)
    if k < len(CUTS):
        R_ = list(CUTS[k].coords)[::-1]
    else:
        ex = S.center.coords[-1][0]; R_ = [(ex, 2773000), (ex, 2769000)]
        _ec = H / f'data/Z{k}_east_cut_EPSG3826.geojson'   # Z8 起：東界＝基隆路中心線（35；workflow 三「光復南路—基隆路」）；無檔則維持中心線終點
        if _ec.exists(): R_ = list(shape(json.load(open(_ec))['features'][0]['geometry']).coords)[::-1]
    return Polygon([(L[0][0], 2769000)] + L + [(L[-1][0], 2773000), (R_[0][0], 2773000)] + R_ + [(R_[-1][0], 2769000)]).buffer(0)
SLAB = slab_of(k).intersection(box(300935, 2770000, 307545, 2771910))

# OSM 建物名稱 → 線稿建物輪廓
osm = json.load(open(S.BASE / 'source/expanded_osm.geojson'))['features']
OSMB = []
for f in osm:
    p = f['properties']
    if f['geometry']['type'] == 'LineString' or 'building' not in p or not p.get('name'): continue
    g = transform(tf, shape(f['geometry'])).buffer(0)
    if g.intersects(SLAB.buffer(50)): OSMB.append((g, p))
BL = list(S.bld.geoms)
def bld_of(name):
    gs = [g for g, p in OSMB if p['name'] == name]
    out = []
    for g in gs:
        for b in BL:
            if b.intersects(g) and (b.intersection(g).area > .3 * b.area or b.intersection(g).area > .5 * g.area): out.append(b)
    return unary_union(out) if out else (unary_union(gs) if gs else None), None
def tags_of(name):
    return next((p for g, p in OSMB if p['name'] == name), {})

# ---------- 規則 A：主角構成（依單元設定）----------
KEY_A = {
 'Z1': [
  # (群組, 顯示名稱, OSM 名稱或 PUB, 依據, 備註)
  ('河岸門戶', 'B02 跨堤橋（規劃）', 'PUB:B02', 'workflow 三 Z1 主角「河岸門戶」；四-1 起點由環河北路移至淡水河堤，以免切開 B02（E301060–301226）',
   '水利處公開規劃配置圖描繪，3 點視覺對位，非核定工程界線'),
  ('河岸門戶', '西寧國宅', '西寧國宅', 'workflow 三 Z1 主角（含西寧國宅）；四-1 同上，起點移至淡水河堤以免切開國宅',
   '大型集合住宅，距軸線約 255 m，位於第一排之後'),
  ('河岸門戶', '忠孝抽水站', '忠孝抽水站', '河岸門戶起點之堤防內側公共設施（主角基地類型：公共建設，一-1）',
   '市政防洪抽水站，仍在使用（03 工業倉儲調查 S07）'),
  ('北門古蹟群', '臺北府城北門', '臺北府城北門', 'workflow 三 Z1 主角「北門古蹟群」', 'OSM heritage=2（國定古蹟），距軸線約 250 m'),
  ('北門古蹟群', '臺北郵局', '臺北郵局', 'workflow 三 Z1 主角「北門古蹟群」', 'OSM historic=monument，距軸線約 310 m'),
  ('北門古蹟群', '三井物產株式會社舊倉庫', '三井物產株式會社舊倉庫', 'workflow 三 Z1 主角（含三井倉庫）', 'OSM historic=building，距軸線約 205 m'),
  ('北門古蹟群', '撫臺街洋樓', '撫臺街洋樓', 'workflow 三 Z1 主角「北門古蹟群」', 'OSM tourism=museum，距軸線約 365 m'),
  ('北門古蹟群', '鐵道部園區（主廳舍、八角樓、工場群）', 'BLOCK:主廳舍', 'workflow 三 Z1 主角（含鐵道部）',
   '國立臺灣博物館鐵道部園區：主廳舍所在街廓內全部建物（使用者 2026-10-11 於 AI 補標工場群）；第一排，距軸線約 110 m'),
  ('北門古蹟群', '原臺北鐵道工場（台鐵舊禮堂）', '原臺北鐵道工場（台鐵舊禮堂）', 'workflow 三 Z1 主角「北門古蹟群」（鐵道部周邊產業遺構）',
   'OSM historic=monument；第一排臨大道，距軸線約 45 m'),
  ('北門古蹟群', '原專賣局台北後站倉庫', '原專賣局台北後站倉庫', 'workflow 三 Z1 主角「北門古蹟群」（日治產業遺構）',
   'OSM building=construction（修復中），未標古蹟等級；第一排臨大道'),
  ('台北雙子星', '台北雙子星 C1／D1（興建中）', ['台北雙星C1', '台北雙星D1'], 'workflow 三 Z1 主角「台北雙子星」；四-2 承德路切點避開 C1／D1（約 E301600–301950）',
   '交通樞紐型開發（主角基地類型：交通樞紐，一-1），位於機場捷運台北車站（A1）上方；OSM building=construction'),
 ],
 'Z3': [
  ('主角', '行二行三公辦都更 U17（規劃中）', 'PUB:U17:building', 'workflow 三 Z3 主角「行政院行二行三公辦都更（U17）」',
   '2024 公聽會公開方案描圖（行政辦公主體、住宅 A／B 棟），非已核定施工圖；基地內現有建物以拆除改建處理'),
 ],
 'Z6': [
  ('主角：U02', 'U02 長安段公辦都更（規劃中）', 'PUB:U02:building', 'workflow 三 Z6 主角「長安段公辦都更（U02／U03）」',
   '住都中心 1141212 公辦公聽會簡報 p.33 方案描圖（23 層住宅，1 樓托嬰中心＋店鋪），非已核定施工圖；基地內現有建物以拆除改建處理'),
 ],
 'Z4': [
  ('主角', 'B01 華山司法園區（規劃中）', 'PUB:B01:building', 'workflow 三 Z4 主角「華山（司法園區 B01＋華山1914＋大草原）」',
   '司法院 2023-03-20 公開設計方案描圖（西、東、南側法院主體＋華山貨運站保存建物），最新施工版本未驗證'),
  ('主角', '華山1914文化創意產業園區', 'LU:產業遺構／文創再利用', 'workflow 三 Z4 主角「華山（…華山1914…）」',
   '本單元內土地使用為「產業遺構／文創再利用」之建物（原台北酒廠，03 工業倉儲調查 S02）；大草原（中央藝文公園）為公園、非建物，不上色'),
 ]}
feats = []
def add(g, **pr):
    if g is not None and not g.is_empty: feats.append({'type': 'Feature', 'geometry': mapping(g), 'properties': pr})
pub = json.load(open(PUB))['features']
n = 0; used = []

# ---------- 單元別判準：源頭建築（使用者 2026-10-11 指定 Z2：找出流向台北車站之人群的源頭建築，限 Z2 範圍內）----------
#   目的地＝臺北車站站房（主角之一；tier T，不列為源頭，圖上淡酒紅）；源頭＝tier S。源頭＝本單元建物（歸屬依 workflow 五-4：跨界者歸重疊面積最大之單元）中
#   總樓地板面積 ≥ SRC_MIN_FA 者；樓地板＝逐量體加總（臺北三維模型 2017 各量體 高度÷3.3 取整 × 該量體與建物重疊面積），
#   三維模型未覆蓋部分以 OSM／土地使用判讀之樓層計；轉乘設施（ALWAYS）不設門檻。用途不限，停車場、施工中建物除外。
SRC_RULE = {'Z2': {'dest': ['臺北車站'], 'always': ['臺北轉運站'], 'min_fa': 10000,
                   'rule': 'Z2 判準（使用者 2026-10-11）：流向台北車站之人群的源頭建築，限 Z2 範圍內；總樓地板 ≥ 1 萬㎡，轉乘設施不設門檻'}}
def source_buildings(cfg):
    import collections
    from shapely.strtree import STRtree
    LU = H.parents[0] / '03_南京至仁愛_沿線土地使用分析_20261006/data'
    BZ = {f['properties']['bid']: f['properties']['zone'] for f in json.load(open(LU / 'drawing_buildings_zone_EPSG3826.geojson'))['features']}
    T3 = []
    for f_ in json.load(open(H.parents[1] / '02_調整過程/歷次處理與版本紀錄/過程_臺北三維參照/civic_approximate_buildings_wgs84.geojson'))['features']:
        g_ = transform(tf, shape(f_['geometry'])).buffer(0)
        if not g_.is_empty and f_['properties'].get('height'): T3.append((g_, float(f_['properties']['height'])))
    t3 = STRtree([g_ for g_, _ in T3])
    agg = collections.defaultdict(lambda: {'lv': 0, 'cls': collections.Counter(), 'names': collections.Counter()})
    for f_ in json.load(open(LU / 'landuse_pieces_EPSG3826.geojson'))['features']:
        p_ = f_['properties']
        if BZ.get(p_['bid']) != ZONE: continue
        a_ = agg[p_['bid']]; a_['cls'][p_['cls_zh']] += p_['area']
        if p_['levels']: a_['lv'] = max(a_['lv'], p_['levels'])
        if p_['name']: a_['names'][p_['name']] += p_['area']
    OSMA = [(transform(tf, shape(f['geometry'])).buffer(0), f['properties']) for f in osm
            if f['geometry']['type'] != 'LineString' and 'building' in f['properties']]
    OSMA = [(g, p) for g, p in OSMA if g.intersects(SLAB.buffer(50))]
    USE = {'交通／停車': '交通', '商業（零售／餐飲／旅館）': '商業', '一樓店面（住宅／街屋）': '店面＋住宅', '住宅': '住宅', '辦公': '辦公',
           '政府機關／公共服務': '機關', '文教（學校／文化）': '文教', '醫療': '醫療'}
    out = []
    for bid, z_ in BZ.items():
        if z_ != ZONE: continue
        b = BL[bid]; a_ = agg[bid]
        parts = [(T3[j][0].intersection(b), T3[j][1]) for j in t3.query(b)]
        parts = [(q, h) for q, h in parts if not q.is_empty and q.area > 1]
        cov = unary_union([q for q, _ in parts]) if parts else Point(0, 0).buffer(0)
        fa_3d = sum(q.area * max(1, round(h / 3.3)) for q, h in parts)
        lv_o = a_['lv'] or 1
        fa = fa_3d + b.difference(cov).area * lv_o
        lv = max([lv_o] + [round(h / 3.3) for _, h in parts])
        osm_ = sorted([(g.intersection(b).area, p) for g, p in OSMA if g.intersects(b) and g.intersection(b).area > .3 * min(g.area, b.area)],
                      key=lambda t: -t[0])
        names = [p['name'] for _, p in osm_ if p.get('name')] or [k for k, _ in a_['names'].most_common(1)]
        btag = next((p.get('building') for _, p in osm_ if p.get('building') not in (None, 'yes')), '')
        if any(p.get('building') == 'construction' for _, p in osm_): continue
        side = 'N' if S.center.interpolate(S.center.project(b.representative_point())).y < b.representative_point().y else 'S'
        out.append(dict(bid=bid, g=b, fa=fa, lv=int(lv), names=names, btag=btag, side=side,
                        use=USE.get(a_['cls'].most_common(1)[0][0], '其他') if a_['cls'] else '其他'))
    return out
if 'S' in RULE:
    cfg = SRC_RULE[ZONE]
    _cands = source_buildings(cfg)
    json.dump([{'bid': r['bid'], 'fa': round(r['fa']), 'levels': r['lv'], 'names': r['names'], 'use': r['use'], 'side': r['side'], 'btag': r['btag']}
               for r in sorted(_cands, key=lambda r: -r['fa'])], open(H / f'data/{ZONE}_source_candidates.json', 'w'), ensure_ascii=False, indent=0)   # 27 判讀依據 A4 用
    LBL = {'apartments': '集合住宅', 'hotel': '旅館', 'office': '辦公', 'commercial': '商業', 'house': '住宅', 'residential': '住宅'}
    for r in sorted(_cands, key=lambda r: -r['fa']):
        is_dest = any(nm in cfg['dest'] for nm in r['names'])
        is_always = any(nm in cfg['always'] for nm in r['names'])
        if not is_dest and not is_always and r['fa'] < cfg['min_fa']: continue
        if not is_dest and r['use'] == '交通' and not is_always: continue          # 停車場等交通建物不列為源頭
        nm = '／'.join(dict.fromkeys(r['names'])) or f"{LBL.get(r['btag'], r['use'])}（OSM 未具名）"
        if not any('\u4e00' <= c <= '\u9fff' for c in nm): nm += f"（{LBL.get(r['btag'], r['use'])}）"   # 僅英文名者補用途
        use = '轉乘＋商業' if is_always else ({'hotel': '旅館', 'office': '辦公'}.get(r['btag']) or r['use'])
        n += 1; used.append(r['g'])
        side_t = '北側：往車站須穿越市民大道' if r['side'] == 'N' else '南側：不須穿越市民大道'
        if is_dest:
            add(r['g'], kind='key', id=n, tier='T', group='目的地（主角）', name=nm, rule=cfg['rule'], use='交通', side=r['side'],
                fa=round(r['fa']), levels=r['lv'], note=f"台鐵／高鐵站房（主角）；樓地板約 {r['fa'] / 1e4:.1f} 萬㎡", planned=False,
                dist_m=round(S.center.distance(r['g'])))
        else:
            add(r['g'], kind='key', id=n, tier='S', group=use, name=nm, rule=cfg['rule'], use=use, side=r['side'],
                fa=round(r['fa']), levels=r['lv'], note=f"樓地板約 {r['fa'] / 1e4:.1f} 萬㎡（{r['lv']} 層）；{side_t}" + ('；轉乘設施不設門檻' if is_always else ''),
                planned=False, dist_m=round(S.center.distance(r['g'])))
for grp, disp, src, rule, note in KEY_A.get(ZONE, []):
    if isinstance(src, str) and src.startswith('BLOCK:'):
        anchor = [g for g, p in OSMB if p['name'] == src[6:]][0]
        blk_ = [q for q in box(300935, 2770000, 307545, 2771910).difference(S.road).geoms if q.contains(anchor.representative_point())][0]
        others = unary_union([bld_of(nm_)[0] for _, _, s2, _, _ in KEY_A.get(ZONE, []) if isinstance(s2, str) and not s2.startswith(('PUB:', 'BLOCK:'))
                              for nm_ in [s2] if bld_of(nm_)[0] is not None and blk_.contains(bld_of(nm_)[0].representative_point())] or [Point(0, 0).buffer(0)])
        g = unary_union([b for b in BL if blk_.contains(b.representative_point()) and b.intersection(others).area < .5 * b.area])
        planned = False
    elif isinstance(src, str) and src.startswith('LU:'):   # 本單元內（五-4 歸屬）主要土地使用為指定類別之建物
        import collections as _co
        _LUD = H.parents[0] / '03_南京至仁愛_沿線土地使用分析_20261006/data'
        _bz = {f['properties']['bid']: f['properties']['zone'] for f in json.load(open(_LUD / 'drawing_buildings_zone_EPSG3826.geojson'))['features']}
        _cls = _co.defaultdict(_co.Counter)
        for f_ in json.load(open(_LUD / 'landuse_pieces_EPSG3826.geojson'))['features']:
            if _bz.get(f_['properties']['bid']) == ZONE: _cls[f_['properties']['bid']][f_['properties']['cls_zh']] += f_['properties']['area']
        g = unary_union([BL[b] for b, c in _cls.items() if c.most_common(1)[0][0] == src[3:]] or [Point(0, 0).buffer(0)])
        planned = False
    elif isinstance(src, str) and src.startswith('PUB:'):
        case, _, lyr = src[4:].partition(':')
        lyrs = (lyr,) if lyr else ('landscape', 'building')
        g = unary_union([shape(f['geometry']) for f in pub if f['properties']['case'] == case and f['properties']['layer'] in lyrs
                         and '廣場' not in f['properties']['label']])
        planned = True
    else:
        names = src if isinstance(src, list) else [src]
        g = unary_union([bld_of(nm)[0] for nm in names if bld_of(nm)[0] is not None])
        planned = False
    if g is None or g.is_empty: print('not found', disp); continue
    n += 1; used.append(g)
    add(g, kind='key', id=n, tier='A', group=grp, name=disp, rule=rule, note=note, planned=planned,
        dist_m=round(S.center.distance(g.representative_point())))
# ---------- 規則 B：公共案件基地 ----------
for f in pub:
    pr = f['properties']
    if pr['layer'] != 'site': continue
    g = shape(f['geometry'])
    if g.intersection(SLAB).area < .5 * g.area: continue
    if any(pr['case'] == u for u in ('B02',)): continue
    n += 1
    lab = {'U01': 'U01 E1／E2 特定專用區（公辦都更）', 'B03': 'B03 心中山線形公園（前期評估基地範圍）', 'U17': 'U17 基地範圍',
           'B01': 'B01 司法園區基地範圍'}.get(pr['case'], f"{pr['case']} {pr['label']}")
    add(g, kind='key', id=n, tier='B', group='公共案件基地', name=lab, rule='workflow 二-2 疊合公共案件基地（公辦都更）',
        note=pr['label'] + '；' + pr['source'], planned=False, site=True, dist_m=round(S.center.distance(g.representative_point())))
# ---------- 規則 C：界面大型建物（第一排、距軸線 120 m 內、> 2,500 m²）----------
if 'C' not in RULE: BL_C = []
else: BL_C = BL
FB = [shape(f['geometry']) for fn in ('frontage_blocks_EPSG3826.geojson', 'frontage_blocks_full_EPSG3826.geojson')
      for f in json.load(open(H / 'data' / fn))['features'] if f['properties']['zone'] == ZONE]
_ds = H / f'data/{ZONE}_demand_supply_EPSG3826.geojson'
DS = [(shape(f['geometry']), f['properties']['name']) for f in json.load(open(_ds))['features']
      if f['properties'].get('cat') == 'bulk' and f['properties'].get('name')] if _ds.exists() else []
fbu = unary_union(FB); usedu = unary_union(used) if used else Point(0, 0).buffer(0)
for b in sorted(BL_C, key=lambda b: -b.area):
    if b.area <= LARGE or not b.intersects(SLAB) or not b.intersects(fbu) or S.center.distance(b) > FRONT_D: continue
    if b.intersection(usedu).area > .3 * b.area: continue
    nm = next((p['name'] for g, p in OSMB if g.intersection(b).area > .3 * min(g.area, b.area)), '')
    tg = next((p for g, p in [(transform(tf, shape(f['geometry'])), f['properties']) for f in osm
                              if f['geometry']['type'] != 'LineString' and 'building' in f['properties']] if g.intersection(b).area > .3 * b.area), {})
    if not nm:   # 院區等具名用地面（OSM 非建物面）包含本棟者
        nm = next((f['properties']['name'] for f in osm if f['geometry']['type'] != 'LineString' and f['properties'].get('name')
                   and 'building' not in f['properties'] and transform(tf, shape(f['geometry'])).buffer(0).contains(b.representative_point())), '')
    if not nm and DS:   # 13 穿越需求之大量體點（30 m 內）
        nm = next((nm_ for g_, nm_ in DS if g_.distance(b) < 30), '')
    if not nm:
        nm = {'school': '學校建物（OSM 未具名）'}.get(tg.get('building'), '大型建物（OSM 未具名）')
    n += 1
    add(b, kind='key', id=n, tier='C', group='界面大型建物', name=nm,
        rule=f'workflow 一-3 界面指標：第一排、距高架軸線 {FRONT_D} m 內、建築面積 > {LARGE:,} 平方公尺',
        note=f'建築面積 {b.area:,.0f} 平方公尺（線稿）；距軸線 {S.center.distance(b):.0f} m', planned=False, dist_m=round(S.center.distance(b)))

# ---------- 規則 D：主角新增人口之目的地建物（使用者 2026-10-11 指定，Z3 起）----------
#   起點＝主角公辦都更基地；範圍＝本單元多邊形（高架兩側 300 m；跨單元建物歸重疊面積最大之單元，同 workflow 五-4）。
#   店家＝06_industry 之 OSM 店家點（industry_pois）；建物用途＝01_classify 土地使用（landuse_pieces）。
#   商辦／政府機關：含「商辦金融」店家點，或土地使用以「辦公」「政府機關／公共服務」為主；
#   日常生活店家：含「餐飲」「便利超市」「生活服務」店家點（06_industry「日常生活服務」族）。
#   兩者兼有：比家數（土地使用為辦公／政府機關者商辦加 1），多者為準；同數依建物土地使用（辦公／政府機關→商辦，其餘→日常）。
#   員工餐廳（不對外）不計。
DEST_CASE = {'Z3': 'U17'}
LIFE = ('餐飲', '便利超市', '生活服務'); OFFICE_POI = ('商辦金融',); OFFICE_LU = ('辦公', '政府機關／公共服務')
if 'D' in RULE:
    case = DEST_CASE[ZONE]
    site = unary_union([shape(f['geometry']) for f in pub if f['properties']['case'] == case and f['properties']['layer'] == 'site'])
    for b in BL:   # 主角基地內現有建物：拆除改建（不上圖）
        if b.intersection(site).area > .5 * b.area: add(b, kind='replaced', case=case, area=round(b.area))
    replaced = unary_union([shape(f['geometry']) for f in feats if f['properties']['kind'] == 'replaced'] or [Point(0, 0).buffer(0)])
    ZP_ = {f['properties']['id']: shape(f['geometry']) for f in S.ZF if 'id' in f['properties']}
    zpoly = ZP_[ZONE]
    def in_zone(b):
        a = b.intersection(zpoly).area
        return a > 0 and all(a >= b.intersection(g).area for z_, g in ZP_.items() if z_ != ZONE)
    BZ = [b for b in BL if b.intersects(zpoly) and in_zone(b) and b.intersection(replaced).area < .5 * b.area]
    from shapely.strtree import STRtree
    tree = STRtree(BZ)
    LUD = H.parents[0] / '03_南京至仁愛_沿線土地使用分析_20261006/data'
    import collections
    poi = collections.defaultdict(collections.Counter); poi_nm = collections.defaultdict(list)
    for f in json.load(open(LUD / 'industry_pois_EPSG3826.geojson'))['features']:
        ind = f['properties']['ind']
        if ind not in LIFE + OFFICE_POI or '員工餐廳' in (f['properties'].get('name') or ''): continue
        pt = shape(f['geometry'])
        if not zpoly.buffer(10).contains(pt): continue
        idx = [i for i in tree.query(pt) if BZ[i].contains(pt)]
        if not idx:   # 店家點多在騎樓或入口：6 m 內最近建物
            near_ = [(BZ[i].distance(pt), i) for i in tree.query(pt.buffer(6))]
            idx = [min(near_)[1]] if near_ else []
        for i in idx[:1]:
            poi[i][ind] += 1
            if f['properties'].get('name'): poi_nm[i].append(f['properties']['name'])
    lu = collections.defaultdict(collections.Counter)
    for f in json.load(open(LUD / 'landuse_pieces_EPSG3826.geojson'))['features']:
        g = shape(f['geometry'])
        if not g.intersects(zpoly): continue
        for i in tree.query(g):
            a = BZ[i].intersection(g).area
            if a > .5: lu[i][f['properties']['cls_zh']] += a
    side_site = S.center.interpolate(S.center.project(site.centroid))
    def side(g):
        c = g.representative_point(); s_ = S.center.project(c); a_ = S.center.interpolate(s_); b_ = S.center.interpolate(min(s_ + 1, S.center.length))
        return '北' if (b_.x - a_.x) * (c.y - a_.y) - (b_.y - a_.y) * (c.x - a_.x) > 0 else '南'
    s_site = side(site)
    for i, b in enumerate(BZ):
        c = poi[i]; n_life = sum(c[k] for k in LIFE); n_off = sum(c[k] for k in OFFICE_POI)
        lu_main = lu[i].most_common(1)[0][0] if lu[i] else ''
        off_score = n_off + (1 if lu_main in OFFICE_LU else 0)
        if n_life == 0 and off_score == 0: continue
        grp = '日常生活店家' if n_life > off_score or (n_life == off_score and lu_main not in OFFICE_LU) else '商辦／政府機關'
        nm = next((p['name'] for g, p in OSMB if g.intersection(b).area > .3 * min(g.area, b.area)), '')
        sd = side(b)
        detail = '、'.join(f'{k} {c[k]}' for k in LIFE + OFFICE_POI if c[k]) + (f'；土地使用 {lu_main}' if lu_main else '')
        n += 1
        add(b, kind='key', id=n, tier='D', group=grp, name=nm, side=sd, cross=(sd != s_site), n_life=n_life, n_office=n_off, lu=lu_main,
            shops='、'.join(dict.fromkeys(poi_nm[i]))[:120],
            rule=f'主角 {case} 新增人口之目的地（{grp}）', note=detail + f'；距 {case} 基地 {b.distance(site):.0f} m',
            planned=False, dist_m=round(S.center.distance(b)), d_site=round(b.distance(site)))

# ---------- 規則 H 住宅、P 運動場（Z4 起，使用者 2026-10-12 指定「運動生活空間」；資料＝30_sports_housing）----------
#   H：本單元內主要用途為住宅或一樓店面（住宅／街屋）之建物（藍）；戶數＝官方村里戶數依住宅樓地板分配（30 摘要，不逐棟）。
#   P：OSM 運動設施（球場、跑道、體健設施、兒童遊戲場），空照核對；範圍內＋鄰近 150 m（adj＝True，不參與地圖定框）；不開放者不上圖。
if 'H' in RULE or 'P' in RULE:
    for f in json.load(open(H / f'data/{ZONE}_sports_housing_EPSG3826.geojson'))['features']:
        p = f['properties']; g = shape(f['geometry'])
        if p['kind'] == 'housing' and 'H' in RULE:
            n += 1
            add(g, kind='key', id=n, tier='H', group='住宅', name='', side={'N': '北', 'S': '南'}[p['side']], use=p['main'], fa=p['res_fa'],
                village=p['village'], rule='Z4 判準：運動生活空間——本單元內住宅建物', note=f"{p['main']}｜{p['village']}｜住宅樓地板約 {p['res_fa']:,} ㎡",
                planned=False, dist_m=round(S.center.distance(g)))
        elif p['kind'] == 'sport' and 'P' in RULE and p['scope'] == '範圍內' and p['public']:   # 只列範圍內（使用者 2026-10-12：範圍內有幾類就顯示幾類）；鄰近只存 30 後台 CSV
            n += 1
            add(g, kind='key', id=n, tier='P', group=p['typ'], name=p['host'] or p['typ'], pid=p['id'], area=p['area'], scope=p['scope'], adj=p['scope'] != '範圍內',
                public=p['public'], point=p['point'], owner=p['owner'], host_kind=p['host_kind'], side={'N': '北', 'S': '南'}[p['side']],
                rule='Z4 判準：運動生活空間——運動場（OSM＋Ortho_2025 空照核對）', note=f"{p['typ']}｜{p['scope']}（{p['owner']}）｜{p['aerial']}：{p['aerial_note']}",
                planned=False, dist_m=p['dist'])

# ---------- 規則 K 商業空間主題（Z5 起，使用者 2026-10-12 指定；資料＝31_commercial_space）----------
#   tier M 商業空間（大型商場／市場、商業大樓／旅館、騎樓店面、臨街店面）、R 古蹟（建國啤酒廠）、
#   V 空地圖層＝可用空地（空地、平面停車場；空照判讀）＋步行區、廣場、綠地（使用者 2026-10-12 併入空地圖層，減少圖面顏色）；
#   F 配套措施點（停車場、公車站、YouBike、公廁）：使用者 2026-10-12 刪除，不上圖（nomap；QGIS 保留隱藏層）。
#   施工中基地不上圖（31 列於 A4）。點狀配套（adj＝True）不參與地圖定框。
if 'K' in RULE:
    _TK = {'commerce': 'M', 'heritage': 'R', 'support': 'F', 'vacant': 'V'}
    for f in json.load(open(H / f'data/{ZONE}_commercial_EPSG3826.geojson'))['features']:
        p = f['properties']; g = shape(f['geometry'])
        if p['cat'] not in _TK: continue
        n += 1
        tr = 'V' if p['cat'] == 'support' and g.geom_type != 'Point' else _TK[p['cat']]   # 使用者 2026-10-12：步行區、廣場、綠地併入空地圖層；配套點不上圖（tier F 僅 QGIS 隱藏層）
        add(g, kind='key', id=n, tier=tr, group=p['group'], name=p.get('name') or '', planned=False, adj=g.geom_type == 'Point', nomap=tr == 'F',
            rule='Z5 判準：商業空間之密集——' + {'M': '商業空間', 'R': '古蹟（使用者指定）', 'F': '既有配套措施（不上圖）',
                                              'V': '空地圖層：可用空地（空照判讀）' if p['cat'] == 'vacant' else '空地圖層：步行區、廣場、綠地'}[tr],
            note=p.get('reason') or p.get('note') or p.get('top') or '', dist_m=round(S.center.distance(g)),
            **{k: p[k] for k in ('side', 'area', 'n_front', 'n_official', 'n_osm', 'n_3c', 'arcade', 'car', 'moto', 'op', 'addr', 'cap', 'id_scan', 'bid') if k in p})

# ---------- 規則 Y 滲透場所（Z6，使用者 2026-10-12 指定；資料＝33_z6_permeable）----------
#   tier A＝場所建物（酒紅剪影）；tier O＝場所開放地：空地、校園、公園綠地、U02 方案法定空地（淡酒紅）；U02 基地內現有建物＝replaced（不畫）
if 'Y' in RULE:
    for f in json.load(open(H / f'data/{ZONE}_permeable_EPSG3826.geojson'))['features']:
        p = f['properties']; g = shape(f['geometry'])
        if p['kind'] == 'replaced': add(g, kind='replaced', case=p['case'], area=p['area']); continue
        n += 1
        add(g, kind='key', id=n, tier=p['tier'], group=p['group'], name=p['name'], rule=p['rule'], note=p['note'], planned=False,
            side=p['side'], area=p['area'], dist_m=p['dist_m'], **({'unmask': True} if p.get('unmask') else {}))

# ---------- 規則 N 夜間餐飲（Z7，使用者 2026-10-12 指定；資料＝34_z7_night_dining）----------
#   tier N＝本單元內有一樓餐飲店家之建物；group＝建物型態（店家中最特定者：居酒屋／燒肉串燒 > 酒吧／飲酒店 > 宵夜小吃 > 一般餐飲），酒紅色階
if 'N' in RULE:
    for f in json.load(open(H / f'data/{ZONE}_night_dining_EPSG3826.geojson'))['features']:
        p = f['properties']; n += 1
        add(shape(f['geometry']), kind='key', id=n, tier='N', group=p['group'], name=p['names'][:40], planned=False, side=p['side'], area=p['area'],
            n_shops=p['n_shops'], n_osm=p['n_osm'], n_tax_only=p['n_tax_only'], by_type=p['by_type'], by_hours=p['by_hours'], bid=p['bid'],
            rule='Z7 判準：夜間餐飲——餐飲建物依型態分色（一樓店面；OSM 判型態與營業時間、稅籍補數量）',
            note='、'.join(f'{k} {v}' for k, v in p['by_type'].items()) + '｜營業時段 ' + '、'.join(f'{k} {v}' for k, v in p['by_hours'].items()), dist_m=p['dist_m'])

# ---------- 底圖：市民高架分隔島 ----------
W_ = box(*SLAB.buffer(900).bounds).intersection(box(300935, 2770000, 307545, 2771910))
isl = W_.difference(S.road)
near = unary_union([S.deck.buffer(4), S.elev.buffer(18), S.ramps.buffer(10)])
for p in getattr(isl, 'geoms', [isl]):
    if p.geom_type != 'Polygon' or p.area < 12 or p.area > 12000: continue
    if 2 * p.area / p.length > 40: continue
    if not p.intersects(near) or p.intersection(near).area < .3 * p.area: continue
    if p.intersection(S.bld).area > .25 * p.area: continue
    add(p, kind='median', area=round(p.area), under_deck=bool(p.intersection(S.deck).area > .5 * p.area))
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': feats,
           'slab': mapping(SLAB)}, open(H / f'data/{ZONE}_key_buildings_EPSG3826.geojson', 'w'), ensure_ascii=False)
for f in feats:
    p = f['properties']
    if p['kind'] == 'key' and p['tier'] not in ('D', 'H', 'P', 'M', 'R', 'F', 'V', 'N'): print(p['id'], p['tier'], p['group'], p['name'], p['dist_m'], 'm')
if 'H' in RULE or 'P' in RULE:
    import collections as _c2
    print('住宅建物', sum(1 for f in feats if f['properties'].get('tier') == 'H'),
          '｜運動場', dict(_c2.Counter((f['properties']['scope'], f['properties']['group']) for f in feats if f['properties'].get('tier') == 'P')))
if 'K' in RULE:
    import collections as _c3
    print('Z5 商業空間主題', dict(_c3.Counter((f['properties']['tier'], f['properties']['group']) for f in feats if f['properties'].get('tier') in ('M', 'R', 'F', 'V'))))
if 'N' in RULE:
    import collections as _c4
    print('Z7 夜間餐飲建物', dict(_c4.Counter((f['properties']['group'], f['properties']['side']) for f in feats if f['properties'].get('tier') == 'N')))
if 'D' in RULE:
    import collections as _c
    D_ = [f['properties'] for f in feats if f['properties'].get('tier') == 'D']
    print('目的地', dict(_c.Counter((p['group'], p['side']) for p in D_)), '｜具名', [p['name'] for p in D_ if p['name']])
    print('拆除改建', sum(1 for f in feats if f['properties']['kind'] == 'replaced'))
print('medians', sum(1 for f in feats if f['properties']['kind'] == 'median'))
