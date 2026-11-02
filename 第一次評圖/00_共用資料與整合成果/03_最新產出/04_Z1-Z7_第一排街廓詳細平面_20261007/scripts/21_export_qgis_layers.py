# QGIS 匯出（一）：將「影響南北通行因素＋特性建築」各圖層整理成乾淨欄位之 GeoJSON（EPSG:3826，未轉正）＋參數表
#   輸出 QGIS_{Z}_南北通行因素與特性建築/_layers/*.geojson、params.json；再由 22_qgis_project.py（QGIS 內建 Python）
#   寫入 GeoPackage 並建立已設定樣式之 QGIS 專案。
import json, sys, importlib.util, shutil
from pathlib import Path
from shapely.geometry import shape, mapping, box
from shapely.ops import unary_union

H = Path(__file__).resolve().parents[1]
ZONE = sys.argv[1] if len(sys.argv) > 1 else 'Z1'
spec = importlib.util.spec_from_file_location('sheet', H / 'scripts/02_sheet.py')
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
S.VARIANT['full'] = True
OUT = H / f'QGIS_{ZONE}_南北通行因素與特性建築'; L = OUT / '_layers'
if L.exists(): shutil.rmtree(L)
L.mkdir(parents=True)
NF = json.load(open(H / f'data/{ZONE}_ns_factors_EPSG3826.geojson'))
FE = [(shape(f['geometry']), f['properties']) for f in NF['features']]
SLAB = shape(NF['slab']); CLIP = SLAB.buffer(15)
WB = box(*SLAB.buffer(1100).bounds)

DUMPED = []
def dump(name, rows, clip=True, skip_empty=False):
    feats = []
    for g, pr in rows:
        if clip: g = g.intersection(CLIP)
        if g.is_empty: continue
        feats.append({'type': 'Feature', 'geometry': mapping(g), 'properties': pr})
    if skip_empty and not feats: return
    DUMPED.append(name)
    json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'urn:ogc:def:crs:EPSG::3826'}}, 'features': feats},
              open(L / f'{name}.geojson', 'w'), ensure_ascii=False)
    print(name, len(feats))
def of(cls, *types): return [(g, p) for g, p in FE if p['cls'] == cls and (not types or p.get('type') in types)]

# 底圖
dump('00_單元範圍', [(SLAB, {'單元': ZONE, '起點': S.ZP[ZONE]['from'], '終點': S.ZP[ZONE]['to'], '主角': S.ZP[ZONE]['info'],
                            '軸線長_m': S.ZP[ZONE]['len_m']})], clip=False)
_um = [shape(f['geometry']) for f in NF['features'] if f['properties'].get('unmask')]   # Z6：使用者指定歸本單元之跨界場所（八德市場）不淡化
dump('01_範圍外淡化遮罩', [(WB.difference(unary_union([SLAB] + _um)), {'說明': '單元界線外：白色 70% 遮罩（前後段淡化）'})], clip=False)
k = int(ZONE[1:]); cuts = [shape(f['geometry']) for f in S.ZF if 'cut' in f['properties']]
cl = [(cuts[k - 1], {'路口': S.ZP[ZONE]['from']})] + ([(cuts[k], {'路口': S.ZP[ZONE]['to']})] if k < len(cuts) else [])
dump('02_單元界線', [(g.intersection(WB), p) for g, p in cl], clip=False)
REB = Path.home() / 'Desktop/Civic_Rebuild_20260909_201934/data'
_sw = [shape(f['geometry']).buffer(0) for f in json.load(open(REB / 'taipei-sidewalks.geojson'))['features']]
_fi = H / f'data/{ZONE}_road_islands_EPSG3826.geojson'   # 26 空照判讀補齊之碎塊
_fill = [shape(f['geometry']).buffer(.05) for f in json.load(open(_fi))['features'] if f['properties']['decision'] == 'fill'] if _fi.exists() else []
PATHS = unary_union([S.road.intersection(WB)] + [q.intersection(WB) for q in _sw if q.intersects(WB)] + _fill).difference(S.bld.intersection(WB.buffer(10)))
dump('03_路徑', [(PATHS, {'說明': '路徑＝整合後道路面 ∪ 新工處人行道範圍 ∪ 空照判讀補齊碎塊（26），淡灰'})], clip=False)
dump('06_路徑碎塊判讀', [(shape(f['geometry']), f['properties']) for f in json.load(open(_fi))['features'] if f['properties'].get('id')] if _fi.exists() else [], clip=False)
_repl = [g for g, p in FE if p['cls'] == 'replaced']          # 主角基地內現有建物（拆除改建，圖面不畫）
REPL = unary_union(_repl) if _repl else None
_bl = S.bld.intersection(WB)
if REPL is not None: _bl = _bl.difference(REPL.buffer(.3))
_vac = [g for g, p in FE if p['cls'] == 'char' and p.get('tier') == 'V']   # Z5：已拆除基地（空照為空地）不列建物（同 20）
if _vac: _bl = _bl.difference(unary_union(_vac).buffer(.2))
_bff = H / 'data/building_floors_EPSG3826.geojson'   # 2026-10-15：建物依樓高 5 級（42；臺北三維模型 2017）
if _bff.exists():
    _ex = unary_union(([REPL.buffer(.3)] if REPL is not None else []) + ([unary_union(_vac).buffer(.2)] if _vac else [])) if (REPL is not None or _vac) else None
    _rows = []
    for f in json.load(open(_bff))['features']:
        g = shape(f['geometry'])
        if not g.intersects(WB): continue
        g = g.intersection(WB)
        if _ex is not None and g.intersects(_ex): g = g.difference(_ex)
        if g.is_empty or g.area < .5: continue
        pr_ = f['properties']
        _rows.append((g, {'級': pr_['cls'], '樓高級距': pr_['label'], '估計層數': pr_['floors'], '樓高來源': pr_['src'], '面積_m2': round(g.area)}))
    dump('04_建物', _rows, clip=False)
else:
    dump('04_建物', [(g, {'面積_m2': round(g.area)}) for g in S.polys(_bl)], clip=False)
dump('07_基地內現有建物_拆除改建', [(g, {'說明': '主角公辦都更基地內現有建物（依方案拆除改建，圖面不畫）', '面積_m2': round(g.area)}) for g in _repl],
     clip=False, skip_empty=True)
dump('05_市民高架中心線', [(S.elev.intersection(WB), {'說明': '市民高架主線車道中心線（OSM）'})], clip=False)
_xef = H / f'data/{ZONE}_elev_extra_EPSG3826.geojson'   # Z6 起：建國高架主線（33；使用者 2026-10-12 同意比照市民高架）
if _xef.exists(): dump('10_建國高架中心線', [(unary_union([shape(f['geometry']) for f in json.load(open(_xef))['features']]).intersection(WB), {'說明': '建國高架（建國快速道路）主線車道中心線（OSM）'})], clip=False)
_rpf = H / f'data/{ZONE}_ramps_EPSG3826.geojson'   # Z8 起：市民高架匝道（35；使用者 2026-10-12「匝道畫出來」）——高架段 +1、落地段 ±0
if _rpf.exists():
    _rpd = json.load(open(_rpf))['features']
    for _nm, _kd in (('16_+1_市民高架匝道_高架段', 'ramp_elev'), ('17_地面_市民高架匝道_落地段', 'ramp_grade')):
        dump(_nm, [(shape(f['geometry']), {k: v for k, v in f['properties'].items() if k != 'kind'}) for f in _rpd if f['properties']['kind'] == _kd], clip=False, skip_empty=True)
# 通行元素（同一圖層；紅色半透明，重疊處較深）
# 通行元素依高程分層（與 20 / AI 相同）；十字路口不上圖
def level_of(p):
    t, n = p['type'], p.get('name', '')
    if p.get('level') and t in ('地下街', '捷運／車站站體', '車站地下通廊'): return p['level']   # 23 描繪之樓層（同 20）
    if t == '地下街' or (t == '捷運／車站站體' and '月台' in n): return 'B2'
    if t in ('捷運／車站站體', '車站地下通廊'): return 'B1'
    if t in ('地下連通道', '地下街廊道'): return None     # 連通道不上圖（使用者 2026-10-11）
    if t.startswith('人行天橋'): return 'U1'
    if t == '出入口': return 'G'
    if t == '行人穿越道': return 'X'                 # Z6 起：非路口之行人穿越道（使用者 2026-10-12）
    if t == '行穿線': return 'X'                     # Z8 起：交工處行穿線全部上圖（使用者 2026-10-12「行穿線畫出來」）
    if t == '地下停車場': return 'B1'               # Z7 起：市民大道地下停車場分段包絡（使用者 2026-10-12「算做剪影」）
    return None
UGN = {'Z1': ('11_B2_台北地下街_機捷月台', '12_B1_北門站_車站地下通廊_機捷站體'),
       'Z2': ('11_B2_台北地下街Y區', '12_B1_車站地下通廊_捷運台北車站_中山地下街R區'),
       'Z7': ('11_B2_捷運站體_單元外淡化', '12_B1_市民大道地下停車場_捷運站體')}.get(ZONE, ('11_B2_地下二層通行元素', '12_B1_地下一層通行元素'))
for lv, nm in (('B2', UGN[0]), ('B1', UGN[1]), ('G', '13_地面_捷運地下街出入口'), ('U1', '14_+1_人行天橋'), ('X', '15_地面_行人穿越道')):
    dump(nm, [(g, {'類型': p['type'], '名稱': p.get('name', ''), '高程': lv}) for g, p in of('pass_area') if level_of(p) == lv], clip=False,
         skip_empty=ZONE != 'Z1')
# 可通過之路口（41 標記範圍 ∩ 路徑面；2026-10-14 三修：路徑較深灰、與路徑同層；20 G_PATH 同）
_xmf = H / f'data/{ZONE}_cross_marks_EPSG3826.geojson'
if _xmf.exists():
    _xr = []
    for f in json.load(open(_xmf))['features']:
        g_ = shape(f['geometry']).intersection(PATHS)
        _xr += [(q, {'路口': f['properties']['name'], '里程_m': f['properties']['s'], '段數': f['properties']['n_stages'],
                     '跨距_m': f['properties']['span_m'], '類型': f['properties']['kind']}) for q in getattr(g_, 'geoms', [g_]) if q.geom_type == 'Polygon' and q.area > 1]
    dump('18_地面_可通過路口_路徑較深', _xr, clip=False, skip_empty=True)   # 多塊者拆開（GeoPackage 單一 Polygon 型別）
# 特性建築：剪影（建物，含規劃中 B02）；基地範圍（U01，不上圖）
TIER = {'A': '主角構成', 'B': '公辦都更基地', 'C': '界面大型建物', 'D': '主角新增人口之目的地', 'S': '源頭建築', 'T': '目的地（主角）',
        'O': '主角開放地', 'H': '住宅建物', 'P': '運動場', 'M': '商業空間', 'R': '古蹟', 'F': '配套措施', 'V': '可用空地', 'N': '夜間餐飲建物'}
def cattr(p):
    a = {'編號': p['id'], '名稱': p['name'], '層級': p['tier'], '類別': TIER.get(p['tier'], p['tier']), '群組': p['group'], '規劃中': bool(p.get('planned')),
         '距軸線_m': p.get('dist_m'), '依據': p['rule'], '說明': p['note']}
    if p['tier'] in ('S', 'T'):   # Z2 源頭建築／目的地（使用者 2026-10-11）
        a.update({'側': {'N': '北', 'S': '南'}.get(p.get('side'), p.get('side')), '需跨越市民大道': p.get('side') == 'N' and p['tier'] == 'S',
                  '用途': p.get('use'), '樓地板_m2': p.get('fa'), '層數': p.get('levels')})
    if p['tier'] == 'D':
        a.update({'側': p.get('side'), '需跨越市民大道': bool(p.get('cross')), '日常店家數': p.get('n_life'), '商辦金融數': p.get('n_office'),
                  '土地使用': p.get('lu'), '店家': p.get('shops'), '距主角基地_m': p.get('d_site')})
    if p['tier'] == 'H':   # Z4 起：運動生活空間（使用者 2026-10-12）
        a.update({'側': p.get('side'), '用途': p.get('use'), '住宅樓地板_m2': p.get('fa'), '里': p.get('village')})
    if p['tier'] == 'P':
        a.update({'運動種類': p['group'], '面積_m2': p.get('area'), '範圍': p.get('scope'), '歸屬單元': p.get('owner'), '所在類型': p.get('host_kind'),
                  '開放': bool(p.get('public')), '點位示意': bool(p.get('point')), '側': p.get('side'), '30編號': p.get('pid')})
    if p['tier'] in ('M', 'R', 'F', 'V'):   # Z5 起：商業空間之密集（使用者 2026-10-12；31_commercial_space）
        a.update({k2: p.get(k1) for k1, k2 in (('side', '側'), ('area', '面積_m2'), ('n_front', '實際店面數'), ('n_official', '稅籍店面數'), ('n_osm', 'OSM店家數'),
                  ('n_3c', '3C店面數'), ('arcade', '騎樓'), ('car', '汽車格'), ('moto', '機車格'), ('op', '經營'), ('addr', '地址'), ('cap', 'YouBike柱數'),
                  ('id_scan', '空地候選編號'), ('bid', '線稿建物編號')) if p.get(k1) is not None})
    if p['tier'] == 'N':   # Z7 起：夜間餐飲（使用者 2026-10-12；34_z7_night_dining）
        a.update({'側': p.get('side'), '面積_m2': p.get('area'), '一樓餐飲店家數': p.get('n_shops'), 'OSM店家數': p.get('n_osm'), '僅稅籍店家數': p.get('n_tax_only'),
                  '型態店家數': json.dumps(p.get('by_type', {}), ensure_ascii=False), '營業時段店家數': json.dumps(p.get('by_hours', {}), ensure_ascii=False), '線稿建物編號': p.get('bid')})
    return a
dump('30_特性建築剪影', [(g, cattr(p)) for g, p in of('char') if not p.get('site') and p['tier'] in ('A', 'B', 'C')], clip=False, skip_empty=ZONE != 'Z1')
dump('50_主角開放地_空地校園公園', [(g, cattr(p)) for g, p in of('char') if p['tier'] == 'O'], clip=False, skip_empty=True)   # Z6 起
dump('31_特性基地範圍_不上圖', [(g, cattr(p)) for g, p in of('char') if p.get('site')], clip=False)
DEST_L = {'32_目的地_商辦政府機關': ('商辦／政府機關', '#2F6FD0'), '33_目的地_日常生活店家': ('日常生活店家', '#12A594')}   # 同 20 DEST_C
for nm, (grp, _) in DEST_L.items():
    dump(nm, [(g, cattr(p)) for g, p in of('char') if p['tier'] == 'D' and p['group'] == grp], clip=False, skip_empty=True)
SRC_L = {'34_源頭建築剪影': ('S', '#8E1B3E'), '35_目的地_臺北車站': ('T', '#E9A3BD')}   # Z2：同 20 MAG／MAG_LT
for nm, (tr, _) in SRC_L.items():
    dump(nm, [(g, cattr(p)) for g, p in of('char') if p['tier'] == tr], clip=False, skip_empty=True)
# Z4 起：運動生活空間——住宅建物（藍）、運動場（青綠，同 20 HOUSE_C／SPORT_C）；不開放之機關球場另層、預設關閉
LIV_L = {'36_住宅建物': ('#FDD856', lambda p: p['tier'] == 'H'), '37_運動場': ('#4D8C3E', lambda p: p['tier'] == 'P' and p.get('public', True)),
         '38_運動場_不開放_不上圖': ('#BDBDBD', lambda p: p['tier'] == 'P' and not p.get('public', True))}
for nm, (_, fn) in LIV_L.items():
    dump(nm, [(g, cattr(p)) for g, p in of('char') if fn(p)], clip=False, skip_empty=True)
# Z4 起：純綠地（淡綠）＋公園步道（淡灰）——32_green_paths（使用者 2026-10-12）
_gpf = H / f'data/{ZONE}_green_paths_EPSG3826.geojson'
GP_L = {'08_純綠地': ('#91D099', 'green'), '09_公園步道': ('#E3E3E3', 'parkpath'), '10_公園鋪面_廣場停車': ('#E3E3E3', 'parkpave')}
if _gpf.exists():
    _gpd = json.load(open(_gpf))['features']
    for nm, (_, kd) in GP_L.items():
        dump(nm, [(shape(f['geometry']), {k: v for k, v in f['properties'].items() if k != 'kind'}) for f in _gpd if f['properties']['kind'] == kd], clip=False, skip_empty=True)
# Z5 起：商業空間之密集——商業空間四形式（酒紅色階）、古蹟（紫）、配套措施（藍面；停車場、公車站等點）、可用空地（橄欖黃）；色同 20 COM_C 等
COM_L = {'40_商業空間_大型商場市場': ('#8E1B3E', '大型商場／市場'), '41_商業空間_商業大樓旅館': ('#A4435F', '商業大樓／旅館'),
         '42_商業空間_騎樓店面': ('#B95F7D', '騎樓店面'), '43_商業空間_臨街店面': ('#D2779C', '臨街店面')}
for nm, (_, grp) in COM_L.items():
    dump(nm, [(g, cattr(p)) for g, p in of('char') if p['tier'] == 'M' and p['group'] == grp], clip=False, skip_empty=True)
Z5_L = {'44_古蹟_建國啤酒廠': ('#5E3C99', lambda g, p: p['tier'] == 'R'),
        '48_空地_可用空地_步行區廣場綠地': ('#91D099', lambda g, p: p['tier'] == 'V')}   # 使用者 2026-10-12：步行區、廣場、綠地併入空地圖層
for nm, (_, fn) in Z5_L.items():
    dump(nm, [(g, cattr(p)) for g, p in of('char') if fn(g, p)], clip=False, skip_empty=True)
dump('46_配套_停車場_不上圖', [(g, cattr(p)) for g, p in of('char') if p['tier'] == 'F' and p['group'] == '停車場'], clip=False, skip_empty=True)
dump('47_配套_公車站_YouBike_公廁_不上圖', [(g, cattr(p)) for g, p in of('char') if p['tier'] == 'F' and g.geom_type == 'Point' and p['group'] != '停車場'], clip=False, skip_empty=True)
# Z7 起：夜間餐飲——一樓有餐飲店家之建物依型態（酒紅色階；同 20 NIGHT_C）
NIGHT_L = {'60_夜間餐飲_居酒屋燒肉串燒': ('#8E1B3E', '居酒屋／燒肉串燒'), '61_夜間餐飲_酒吧飲酒店': ('#A4435F', '酒吧／飲酒店'),
           '62_夜間餐飲_宵夜小吃': ('#B95F7D', '宵夜小吃'), '63_夜間餐飲_一般餐飲': ('#D2779C', '一般餐飲')}
for nm, (_, grp) in NIGHT_L.items():
    dump(nm, [(g, cattr(p)) for g, p in of('char') if p['tier'] == 'N' and p['group'] == grp], clip=False, skip_empty=True)
_cmf = H / f'data/{ZONE}_commercial_EPSG3826.geojson'
if _cmf.exists() and any(p['tier'] in ('M', 'R', 'F', 'V') for _, p in of('char')):
    dump('49_施工中_不上圖', [(shape(f['geometry']), {'名稱': f['properties']['name'], '面積_m2': f['properties'].get('area'), '說明': '施工中基地（OSM landuse=construction），不列為可用空地'})
                          for f in json.load(open(_cmf))['features'] if f['properties']['cat'] == 'construction'], clip=False, skip_empty=True)
# 參數表（判定門檻與統計）
gaps = NF['stats']['gaps']
PARAMS_Z1 = [
 ('單元', ZONE, '', f"{S.ZP[ZONE]['from']}—{S.ZP[ZONE]['to']}；主角：{S.ZP[ZONE]['info']}", 'workflow 三'),
 ('比例尺（出圖）', '1:2500', '', 'A1；本 QGIS 專案預設視圖同此範圍', '05／20'),
 ('圖面元素', '建物、路徑（道路＋人行道）、市民高架中心線、單元界線、通行元素、特性建築剪影', '', '不上圖：街廓輪廓、註解、十字路口（平面穿越）、中央分隔島、圍牆圍籬綠籬、停車場車道出入口、高架匝道、無平面穿越長段、U01 基地範圍', '使用者 2026-10-11'),
 ('通行元素不透明度', 1.0, '', '不透明（使用者 2026-10-11 指定）；十字路口（平面穿越行穿線）不上圖', '20 PA_ALPHA'),
 ('通行元素：地下街、捷運站、機捷站、台北車站地下通廊', '告示圖描繪', '', 'Metro Taipei「台北車站全區位置圖」站內告示，12 個路口控制點 TPS 對位（留一驗證中位誤差約 7 m）', '23'),
 ('通行元素：地下連通道寬（示意）', '4（北門機捷連通道 6）', 'm', 'OSM tunnel／indoor 展成面', '19'),
 ('通行元素：人行天橋寬（示意）', '3.5（梯道 3）', 'm', 'OSM bridge=yes 展成面', '19'),
 ('通行元素：出入口（示意）', '5 × 5', 'm', 'OSM 出入口點展成方塊', '19'),
 ('通行元素範圍', 80, 'm', '距大道中心線 80 m 內之地下廊道、連通道、天橋、站體', '19 near'),
 ('平面穿越合併距離', 45, 'm', '同路口行穿線 45 m 內合併為一處', '13'),
 ('特性建築：界面大型建物', '> 2,500 m2，距軸線 120 m 內', '', 'workflow 一-3', '17'),
 ('統計：平面穿越處數', len(NF['stats']['crossings']), '處', '', '19'),
 ('統計：平面穿越間距（西→東）', '／'.join(str(v) for v in gaps), 'm', '', '19'),
 ('統計：特性建築', len(of('char')), '項', '剪影 ' + str(sum(1 for _, p in of('char') if not p.get('site'))) + '、基地範圍（不上圖）' + str(sum(1 for _, p in of('char') if p.get('site'))), '17'),
 ('色彩：建物', '#A4A4A4／#7E7E7E／#585858／#353535／#141414', '', '依樓高 5 級灰：0–5／6–11／12–19／20–29／30 層以上（臺北三維模型 2017，高度 ÷ 3.3 m；2026-10-15）', '42／20'),
 ('色彩：路徑', '#E3E3E3', '', '淡灰（道路＋人行道）', '20'),
 ('色彩：通行元素', '#DF9134', '', '橘（與酒紅區隔），不透明；2026-10-13 降彩度', '20'),
 ('色彩：特性建築剪影', '#8E1B3E', '', '酒紅實心、無外框', '20'),
]
crs_ = sorted(NF['stats']['crossings'])
PARAMS_GEN = [
 ('單元', ZONE, '', f"{S.ZP[ZONE]['from']}—{S.ZP[ZONE]['to']}；主角：{S.ZP[ZONE]['info']}", 'workflow 三'),
 ('比例尺（出圖）', '1:2500', '', 'A1；本 QGIS 專案預設視圖同此範圍', '20'),
 ('圖面元素', '建物、路徑（道路＋人行道）、市民高架中心線、單元界線、通行元素、主角剪影、目的地建物', '', '不上圖：街廓輪廓、註解、十字路口（平面穿越）、中央分隔島、圍牆圍籬綠籬、停車場車道出入口、高架匝道、無平面穿越長段、基地範圍、主角基地內現有建物', '使用者 2026-10-11'),
 ('統計：平面穿越處數', len(crs_), '處', '', '13／19'),
 ('統計：平面穿越間距（西→東）', '／'.join(str(v) for v in gaps), 'm', '', '19'),
 ('色彩：建物', '#A4A4A4／#7E7E7E／#585858／#353535／#141414', '', '依樓高 5 級灰：0–5／6–11／12–19／20–29／30 層以上（臺北三維模型 2017，高度 ÷ 3.3 m；2026-10-15）', '42／20'),
 ('色彩：路徑', '#E3E3E3', '', '淡灰（道路＋人行道）', '20'),
 ('色彩：通行元素', '#DF9134', '', '橘，不透明', '20'),
 ('色彩：主角剪影', '#8E1B3E', '', '酒紅實心、無外框', '20'),
]
if any(p['tier'] == 'D' for _, p in of('char')):
    D_ = [p for _, p in of('char') if p['tier'] == 'D']
    PARAMS_GEN += [
     ('特性建築判準', '主角新增人口之目的地（RULES D）', '', '主角公辦都更完成後新增之辦公與居住人口，在本單元範圍內會走去之目的地建物（使用者 2026-10-11）', '17'),
     ('目的地：商辦／政府機關', sum(1 for p in D_ if p['group'] == '商辦／政府機關'), '棟', '含 OSM 商辦金融店家點，或土地使用以辦公、政府機關／公共服務為主', '17'),
     ('目的地：日常生活店家', sum(1 for p in D_ if p['group'] == '日常生活店家'), '棟', '含餐飲、便利超市、生活服務店家點（06_industry「日常生活服務」族）', '17'),
     ('目的地：兩者兼有', '比家數', '', '辦公／政府機關用途商辦加 1；同數依土地使用；員工餐廳不計', '17'),
     ('目的地：需跨越市民大道', sum(1 for p in D_ if p.get('cross')), '棟', '與主角基地位於大道不同側者', '17'),
     ('色彩：目的地 商辦／政府機關', '#2F6FD0', '', '藍（色覺辨識驗證）', '20'),
     ('色彩：目的地 日常生活店家', '#12A594', '', '青綠（色覺辨識驗證）', '20'),
    ]
if any(p['tier'] == 'S' for _, p in of('char')):
    S_ = [p for _, p in of('char') if p['tier'] == 'S']; N_ = [p for p in S_ if p.get('side') == 'N']
    fa = lambda L: sum(p.get('fa') or 0 for p in L)
    PARAMS_GEN += [
     ('特性建築判準', '流向台北車站之人群的源頭建築（RULES S＋T）', '', '限本單元範圍內（使用者 2026-10-11）；目的地＝臺北車站（主角之一）', '17'),
     ('源頭門檻：總樓地板', '≥ 10,000', 'm2', '臺北三維模型（2017）量體高度÷3.3 取整 × 量體面積逐一加總；臺北轉運站（轉乘設施）不設門檻；停車場、施工中除外', '17 SRC_RULE'),
     ('源頭建築', len(S_), '棟', f"北側 {len(N_)} 棟（往車站須穿越市民大道）、南側 {len(S_) - len(N_)} 棟", '17'),
     ('源頭樓地板合計', round(fa(S_)), 'm2', f"北側 {round(fa(N_))}（{fa(N_) / max(fa(S_), 1):.0%}）", '17'),
     ('色彩：源頭建築', '#8E1B3E', '', '酒紅實心', '20'),
     ('色彩：目的地（臺北車站）', '#E9A3BD', '', '淡酒紅（酒紅 35%＋白）', '20'),
    ]
_shf = H / f'data/{ZONE}_sports_housing_summary.json'
if any(p['tier'] in ('H', 'P') for _, p in of('char')) and _shf.exists():   # Z4 起：運動生活空間（30_sports_housing）
    sh = json.load(open(_shf))
    PARAMS_GEN += [
     ('特性建築判準', '運動生活空間（RULES H＋P）', '', '調查周圍之住宅數量，以及運動場面積涵蓋之運動種類（使用者 2026-10-12）', '17／30'),
     ('住宅戶數', sh['households'], '戶', f"人口 {sh['population']}；北 {sh['hh_N']}／南 {sh['hh_S']}；四種權重區間 {sh['households_range'][0]}–{sh['households_range'][1]}", '30'),
     ('戶數來源', f"內政部村里戶數 {sh['households_ym']}", '', '× 各里住宅樓地板（住宅＋一樓店面扣一樓＋未標示）落在本單元之比例；里界＝內政部 114 年版', '30'),
     ('65 歲以上人口比例', sh['age_share']['65+'], '', '各里單一年齡人口依同權重加總', '30'),
     ('住宅建物', sh['res_buildings'], '棟', f"北 {sh['res_buildings_N']}／南 {sh['res_buildings_S']}；主要用途為住宅或一樓店面（住宅／街屋）", '30'),
     ('運動場（範圍內，不含兒童遊戲場）', sh['sport_in_area'], 'm2', '、'.join(f"{t} {a}" for t, n, a, _, _ in sh['sport_types'] if a and t != '兒童遊戲場'), '30'),
     ('兒童遊戲場（範圍內）', sh['playground_in_area'], 'm2', '另有點位（無面積）', '30'),
     ('運動場顯示範圍', '只列範圍內', '', '範圍內有幾類就列幾類（使用者 2026-10-12）；單元外之學校、橋下運動場只存 data/Z4_運動場_明細.csv', '17／20'),
     ('色彩：住宅建物', '#FDD856', '', '黃（2026-10-13 統一：原藍與 Z3 商辦撞色）', '20'),
     ('色彩：運動場', '#4D8C3E', '', '綠（2026-10-13 統一：原青綠與 Z3 日常生活店家撞色）', '20'),
    ]
    _gps = H / f'data/{ZONE}_green_paths_summary.json'
    if _gps.exists():
        gs_ = json.load(open(_gps))
        PARAMS_GEN += [
         ('純綠地（範圍內）', gs_['green_m2'], 'm2', f"公園綠地 {gs_['cand_m2']} m2 之 {gs_['green_share_of_cand']:.0%}；扣除硬鋪面、步道、運動設施、建物；草地、樹冠、裸土皆算綠地", '32'),
         ('公園內硬鋪面（範圍內）', gs_.get('pave_m2'), 'm2', 'Ortho_2025 灰色成片 ≥ 40 m2 且與步道或公園邊界相連（廣場、停車），淡灰', '32'),
         ('公園步道（範圍內）', gs_['path_m'], 'm', f"OSM footway／path 等，依寬度展成面 {gs_['path_m2']} m2", '32'),
         ('色彩：純綠地', '#91D099', '', '淡綠＝開放空間（與 Z5 空地圖層同色；2026-10-13 統一）', '20'),
        ]
if any(p['tier'] in ('M', 'R', 'F', 'V') for _, p in of('char')) and _cmf.exists():   # Z5 起：商業空間之密集（31_commercial_space）
    st5 = json.load(open(_cmf))['stats']; C_ = [p for _, p in of('char') if p['tier'] == 'M']; V_ = [p for _, p in of('char') if p['tier'] == 'V' and p['group'] in ('空地', '平面停車場')]
    PARAMS_GEN += [
     ('特性建築判準', '商業空間之密集（RULES K）', '', '標出各種形式的商業空間、既有配套措施與可用空地；建國啤酒廠歸類古蹟（使用者 2026-10-12）', '17／31'),
     ('商業空間（四形式）', len(C_), '棟', '、'.join(f"{g} {sum(1 for p in C_ if p['group'] == g)}" for g in ('大型商場／市場', '商業大樓／旅館', '騎樓店面', '臨街店面')), '31'),
     ('實際店面', st5['storefronts'], '家', f"稅籍登記店面型行業（一樓／地下／未載；大型商場不限樓層；同址 ≥ 3 家不計）與 OSM 店家點取多者；3C {st5['n_3c']} 家", '31'),
     ('騎樓判定', '3.64', 'm', '停管處機車退出騎樓路段＋臨主要道路貼齊（≤ 1.5 m）推估；第二排以後依 04 同規則補判', '31'),
     ('可用空地', len(V_), '處', f"約 {sum(p.get('area', 0) for p in V_)} m2；開放地 ≥ 100 m2＋OSM 平面停車場＋已拆除基地，Ortho_2025 逐塊判讀（候選 {st5['vacant_candidates']} 塊）", '31'),
     ('路外停車場', f"汽 {st5['parking_car']}／機 {st5['parking_moto']}", '格', f"北市好停車；路邊汽車格 {st5['curb_spaces']} 格（不上圖）；圓面積＝1.2 m2／格", '08／31'),
     ('色彩：商業空間', '#8E1B3E／#A4435F／#B95F7D／#D2779C', '', '大型商場→臨街店面（酒紅色階）', '20'),
     ('空地圖層', '可用空地＋步行區、廣場、綠地', '', '使用者 2026-10-12 將步行區、廣場、綠地併入空地圖層（同色），配套措施刪除不上圖', '17／20'),
     ('色彩：古蹟／空地', '#5E3C99／#91D099', '', '紫／淡綠＝開放空間（同 Z4 純綠地；2026-10-13 統一）', '20'),
    ]
_ndf = H / f'data/{ZONE}_night_dining_summary.json'
if any(p['tier'] == 'N' for _, p in of('char')) and _ndf.exists():   # Z7 起：夜間餐飲（34_z7_night_dining）
    nd = json.load(open(_ndf))
    PARAMS_GEN += [
     ('特性建築判準', '夜間餐飲（RULES N）', '', '一樓有餐飲店家之建物依型態分色；OSM 判型態與營業時間、稅籍補數量；晚餐也列入；微風廣場不列為主角（使用者 2026-10-12）', '17／34'),
     ('夜間餐飲建物', nd['buildings'], '棟', '、'.join(f"{t} {v}" for t, v in nd['buildings_by_type'].items()), '34'),
     ('一樓餐飲店家', nd['shops'], '家', f"北 {nd['shops_N']}／南 {nd['shops_S']}；來源 " + '、'.join(f"{k} {v}" for k, v in nd['by_source'].items()), '34'),
     ('營業時間已知', nd['hours_known'], '家', f"宵夜（至 23 點後）{nd['late']}、晚餐（涵蓋 18–20 點）{nd['dinner']}；其餘不明", '34'),
     ('店家歸屬建物', 15, 'm', '店家點落在建物內，否則 15 m 內最近之本單元建物', '34'),
     ('地下停車場（通行元素）', '分段包絡 ∩ 中央分隔島', '', '市民大道地下停車場建復、復敦、敦延、延吉段，寬 24 m 比較用外框（非實測），B1；使用者 2026-10-12「算做剪影」，著色限於分隔島範圍（扣除路徑與建物）', '19／34'),
     ('行穿線', '不上圖', '', '十字路口與巷口行穿線皆不畫（使用者 2026-10-12）；平面穿越經行穿線核對後列表', '19'),
     ('色彩：夜間餐飲', '#8E1B3E／#A4435F／#B95F7D／#D2779C', '', '居酒屋／燒肉串燒 → 酒吧／飲酒店 → 宵夜小吃 → 一般餐飲（同 Z5 已驗證酒紅色階）', '20'),
    ]
if ZONE == 'Z8' and _rpf.exists():   # Z8 起：南北兩側園區串連（35_z8_parks）
    _O8 = [p for _, p in of('char') if p['tier'] in ('A', 'O') and not p.get('site')]
    PARAMS_GEN += [
     ('要表達的問題', '南北兩側園區串連', '', '松山文創園區、臺北大巨蛋（南）與國家鐵道博物館（北）隔市民大道對望，正對之段無平面穿越、天橋或地下道，又為匝道進出段（使用者 2026-10-12）', '35'),
     ('主角三園區', len({p['group'] for p in _O8}), '處', '建物（酒紅）＝園區範圍內線稿建物＋OSM 補缺漏；戶外空間（淡酒紅）＝範圍扣除路徑與建物', '35／17 Y'),
     ('行穿線', '全部上圖', '', '交工處行穿線中距大道中心線 40 m 內者（十字路口與巷口；使用者 2026-10-12「行穿線畫出來」）', '19 ALL_XING'),
     ('市民高架匝道', '高架段 +1／落地段 ±0', '', 'OSM trunk_link（名稱含匝道）展成面：寬＝車道數 × 3.5 m＋1.0 m（使用者 2026-10-12「匝道畫出來」）', '35'),
     ('色彩：主角戶外空間', '#E9A3BD', '', '淡酒紅（同 Z6 主角開放地）', '20'),
     ('色彩：匝道', '白底斜線 #666666／#333333', '', '高架段 ////、落地段 ××（地面阻隔）；2026-10-15 由兩灰改斜線，避開建物樓高灰', '20'),
    ]
PARAMS = PARAMS_Z1 if ZONE == 'Z1' else PARAMS_GEN
json.dump([{'項目': a, '數值': str(b), '單位': c, '說明': d, '來源': e} for a, b, c, d, e in PARAMS], open(L / 'params.json', 'w'), ensure_ascii=False, indent=1)
VIEW = unary_union([S.PZ(ZONE)['R']] + [g for g, _ in of('char')]).buffer(60).intersection(SLAB.buffer(60))   # 預設視圖：第一排範圍＋特性建築
# 圖層群組（由上而下＝高程由高至低）：22 依此建立 QGIS 圖層樹；只列出本單元實際輸出之圖層
GROUPS = [('單元範圍與界線', ['01_範圍外淡化遮罩', '02_單元界線', '00_單元範圍']),
          ('+2 高架', ['05_市民高架中心線', '10_建國高架中心線']),
          ('+1 天橋', ['14_+1_人行天橋', '16_+1_市民高架匝道_高架段']),
          ('±0 地面', ['17_地面_市民高架匝道_落地段', '60_夜間餐飲_居酒屋燒肉串燒', '61_夜間餐飲_酒吧飲酒店', '62_夜間餐飲_宵夜小吃', '63_夜間餐飲_一般餐飲', '44_古蹟_建國啤酒廠', '40_商業空間_大型商場市場', '41_商業空間_商業大樓旅館',
                      '42_商業空間_騎樓店面', '43_商業空間_臨街店面', '34_源頭建築剪影', '35_目的地_臺北車站', '30_特性建築剪影', '36_住宅建物', '32_目的地_商辦政府機關', '33_目的地_日常生活店家', '31_特性基地範圍_不上圖',
                      '37_運動場', '38_運動場_不開放_不上圖',
                      '07_基地內現有建物_拆除改建', '04_建物', '48_空地_可用空地_步行區廣場綠地', '49_施工中_不上圖', '46_配套_停車場_不上圖', '47_配套_公車站_YouBike_公廁_不上圖',
                      '13_地面_捷運地下街出入口', '15_地面_行人穿越道', '50_主角開放地_空地校園公園', '09_公園步道', '10_公園鋪面_廣場停車', '08_純綠地', '18_地面_可通過路口_路徑較深', '03_路徑']),
          ('檢核', ['06_路徑碎塊判讀']),
          ('B1 地下一層', [UGN[1]]),
          ('B2 地下二層', [UGN[0]])]
GROUPS = [(g, [n for n in ns if n in DUMPED]) for g, ns in GROUPS]
json.dump({'zone': ZONE, 'view': list(VIEW.bounds),
           'groups': [[g, ns] for g, ns in GROUPS if ns] + [['參數', ['90_參數']]],
           'hidden': ['31_特性基地範圍_不上圖', '00_單元範圍', '06_路徑碎塊判讀', '13_地面_捷運地下街出入口', '07_基地內現有建物_拆除改建', '38_運動場_不開放_不上圖', '49_施工中_不上圖', '46_配套_停車場_不上圖', '47_配套_公車站_YouBike_公廁_不上圖'],
           'fills': {nm: c for nm, (_, c) in DEST_L.items()} | {nm: c for nm, (_, c) in SRC_L.items()} | {nm: c for nm, (c, _) in LIV_L.items()}
                    | {nm: c for nm, (c, _) in COM_L.items()} | {nm: c for nm, (c, _) in Z5_L.items()} | {'49_施工中_不上圖': '#BDBDBD', '50_主角開放地_空地校園公園': '#E9A3BD', '15_地面_行人穿越道': '#DF9134',
                       '16_+1_市民高架匝道_高架段': '#929292', '17_地面_市民高架匝道_落地段': '#666666'}
                    | {nm: c for nm, (c, _) in GP_L.items()} | {nm: c for nm, (c, _) in NIGHT_L.items()}
                    | {UGN[0]: '#DF9134', UGN[1]: '#DF9134', '07_基地內現有建物_拆除改建': '#BDBDBD'},
           # 點狀記號（Z5 起）：停車場＝空心圓（直徑依 汽＋機車格 資料定義，1:2500 下 mm）；公車站／YouBike／公廁依群組分記號
           'markers': {'46_配套_停車場_不上圖': {'shape': 'circle', 'color': '#4D4D4D', 'hollow': True,
                                         'size_expr': '2 * sqrt((coalesce("汽車格", 0) + coalesce("機車格", 0)) * 1.2 / pi()) / 2.5'},
                       '47_配套_公車站_YouBike_公廁_不上圖': {'by': '群組', 'color': '#1479B0', 'shapes': {'公車站': 'square', 'YouBike': 'triangle', '公廁': 'diamond'}, 'size': 2.4}}},
          open(L / 'meta.json', 'w'), ensure_ascii=False, indent=1)
print('params', len(PARAMS))
