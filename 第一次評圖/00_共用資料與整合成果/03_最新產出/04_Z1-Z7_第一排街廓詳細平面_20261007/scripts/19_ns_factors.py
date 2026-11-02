# 影響南北通行之因素（先做 Z1）＋該段特性建築 → data/{Z}_ns_factors_EPSG3826.geojson
#   可通行（pass）：平面穿越（交工處行穿線橫越大道者，13 之 supply／supply_stripe）、地下街廊道與出入口、地下連通道、
#                   捷運站體（地下）與出入口、人行天橋（OSM osm_ways.json 2026-09-09，bridge=yes 之 footway／steps）
#   阻隔（block）：高架下中央分隔島（17 判定；路段中無法穿越，需至路口）、分隔島內地下停車場車道出入口、
#                  大道旁圍牆／圍籬／綠籬（OSM，距中心線 60 m 內，排除 > 1 km 之堤防牆）、高架匝道、
#                  相鄰平面穿越間距 > 200 m 之「無平面穿越長段」
#   特性建築：17 判定之重點建物（A 主角構成、B 公共案件基地、C 界面大型建物）
import json, sys, re, importlib.util
from pathlib import Path
import numpy as np
from shapely.geometry import shape, mapping, LineString, Point, box
from shapely.ops import unary_union, transform, substring
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
ZONE = sys.argv[1] if len(sys.argv) > 1 else 'Z1'
spec = importlib.util.spec_from_file_location('sheet', H / 'scripts/02_sheet.py')
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
S.VARIANT['full'] = True
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform
PRE = H.parents[1] / '01_輸入資料/前處理資料'
GAP_LONG = 200
KB = json.load(open(H / f'data/{ZONE}_key_buildings_EPSG3826.geojson'))
SLAB = shape(KB['slab'])
DS = json.load(open(H / f'data/{ZONE}_demand_supply_EPSG3826.geojson'))
band = S.center.buffer(60).intersection(SLAB)
near = S.center.buffer(80).intersection(SLAB.buffer(30))   # 影響穿越大道之元素：距中心線 80 m 內
view = SLAB.buffer(30)
feats = []
def add(g, **pr):
    if g is not None and not g.is_empty: feats.append({'type': 'Feature', 'geometry': mapping(g), 'properties': pr})

# ---------- 可通行 ----------
sup = [(shape(f['geometry']), f['properties']) for f in DS['features'] if f['properties']['kind'] == 'supply']
for g, p in sup:
    if p['type'] == 'at_grade':
        add(g, cls='pass', type='crossing', name=p['name'].replace('一段', ''), s=p['s'], n_stages=p['n_stages'], span_m=p['span_m'],
            note=f"平面穿越：跨 {p['n_stages']} 段車道、南北總寬 {p['span_m']:.0f} m（含分隔島）")
for f in DS['features']:
    if f['properties']['kind'] == 'supply_stripe': add(shape(f['geometry']), cls='pass', type='crossing_stripe')
# 行穿線（Z6 起，使用者 2026-10-12「十字路口的行穿線不用特意畫，但給行人的行穿線要做路徑剪影」）：
#   交工處行穿線（data/source_taipei/crosswalk）中距大道中心線 40 m 內者逐塊判定——
#     十字路口＝距具名道路（非巷弄；S.streets，且該路接近大道 40 m 內）30 m 內；其餘（巷口、路段中）＝行人用行穿線，以朱紅剪影上圖。
#   平面穿越驗證：13 之 at_grade 須有行穿線跨越中心線或分布於中心線南北兩側（橫越大道）；否則為巷口行穿線（13 誤判），不計入平面穿越與間距。
PED_XING = {'Z6'}
XING_CHECK = {'Z7'}   # Z7 起：只做平面穿越驗證（13 誤判之巷口行穿線不計入），行穿線一律不上圖（使用者 2026-10-12「行穿線不做」）
ALL_XING = {'Z8'}   # Z8 起：交工處行穿線全部上圖（十字路口與巷口；使用者 2026-10-12「行穿線畫出來」），並做平面穿越驗證
XW = []; XW_ALL = []   # XW_ALL：Z8 圖框內全部行穿線（繪圖用）
if ZONE in PED_XING or ZONE in XING_CHECK or ZONE in ALL_XING:
    import glob, shapefile
    for fp in glob.glob(str(H / 'data/source_taipei/crosswalk_202407121519/**/*.shp'), recursive=True):
        try: shs = list(shapefile.Reader(fp, encoding='utf-8').iterShapes())
        except Exception: shs = list(shapefile.Reader(fp, encoding='big5').iterShapes())
        for sh in shs:
            g_ = shape(sh.__geo_interface__)
            if g_.is_empty: continue
            if abs(g_.centroid.x) < 1000: g_ = transform(tf, g_)
            g_ = g_.buffer(0)
            if ZONE in ALL_XING and g_.intersects(S.center.buffer(450).intersection(SLAB.buffer(900)).envelope): XW_ALL.append(g_)   # 圖框約略範圍
            if g_.distance(S.center) < 40 and g_.intersects(SLAB.buffer(60)): XW.append(g_)
    _JS = [g for g in S.streets.values() if g.distance(S.center) < 40]
    def _side(g_):
        c = g_.centroid; d = S.center.project(c); a_ = S.center.interpolate(d); b_ = S.center.interpolate(min(d + 5, S.center.length))
        return 1 if (b_.x - a_.x) * (c.y - a_.y) - (b_.y - a_.y) * (c.x - a_.x) > 0 else -1
    XW = [(g_, 'junction' if any(st.distance(g_) < 30 for st in _JS) else 'ped') for g_ in XW]
    # 使用者於 AI 修改（2026-10-12 12:06 存檔，備份 _使用者修改版/…_使用者修改_20261012-1206.ai）：「把空橋剪影修了一下」——
    #   懷生國小西側天橋南北兩端之行人穿越道剪影改接天橋端點（北端微延長、南端東移約 13 m 接天橋）；圖紙 mm 經 20 sheet_to_world 換算 EPSG:3826
    USER_XW = {'Z6': [[[304576.39, 2770843.09], [304576.22, 2770839.77], [304569.39, 2770839.32], [304569.36, 2770842.52]],   # 北端（圖紙 472.5–475.3, 302.1–303.6 mm）
                      [[304574.67, 2770809.53], [304574.46, 2770805.8], [304566.36, 2770806.15], [304566.42, 2770810.42]]]}   # 南端（圖紙 471.4–474.7, 315.2–317.0 mm）
    if USER_XW.get(ZONE):
        from shapely.geometry import Polygon as _Poly
        _fb = Point(304577, 2770825)   # 天橋中點：其 30 m 內之原行穿線剪影由使用者修改版取代
        XW = [(g_, k_) for g_, k_ in XW if not (k_ == 'ped' and g_.distance(_fb) < 30)] + [(_Poly(c), 'ped') for c in USER_XW[ZONE]]
    for f in feats:
        p_ = f['properties']
        if p_.get('type') != 'crossing': continue
        nr = [g_ for g_, _ in XW if abs(S.center.project(g_.centroid) - p_['s']) < 45]
        ok = any(g_.intersects(S.center) for g_ in nr) or len({_side(g_) for g_ in nr}) == 2
        p_['xing'] = ('十字路口' if any(st.distance(S.center.interpolate(p_['s'])) < 30 for st in _JS) else '行人穿越道（橫越大道）') if ok else '未橫越大道（巷口行穿線；13 誤判，不計）'
        if not ok: p_['type'] = 'crossing_false'
    sup = [(g, p) for g, p in sup if not (p['type'] == 'at_grade' and any(f['properties'].get('type') == 'crossing_false' and f['properties']['s'] == p['s'] for f in feats))]
def short_exit(r):
    m = re.search(r'台北地下街 (Y\d+)', r)
    if m: return m.group(1)
    m = re.search(r'(北門站|台北車站) ?(\d+)?號?', r)
    if m: return ('北門' if m.group(1) == '北門站' else '北車') + (m.group(2) or '')
    return r[:4]
for f in DS['features']:
    p = f['properties']
    if p.get('cat') == 'transit':
        typ = 'mall_exit' if '地下街' in p['reason'] else 'mrt_exit'
        add(shape(f['geometry']), cls='pass', type=typ, name=p['reason'], label=short_exit(p['reason']), side=p['side'])
osm = json.load(open(S.BASE / 'source/expanded_osm.geojson'))['features']
for f in osm:
    p = f['properties']
    if p.get('building') != 'transportation' or f['geometry']['type'] == 'LineString': continue
    g = transform(tf, shape(f['geometry'])).buffer(0)
    if g.intersection(SLAB).area < .3 * g.area or not g.intersects(band): continue
    under = str(p.get('layer', '0')).startswith('-') or p.get('location') == 'underground'
    add(g, cls='pass', type='station', name=p.get('name', '') + ('（地下站體）' if under else '（站體）'), under=under)
WAYS = json.load(open(PRE / 'osm_ways.json'))
mall = []
for w in WAYS:
    t = w.get('t', {}); hw = t.get('highway')
    if hw not in ('footway', 'steps', 'pedestrian', 'corridor', 'path'): continue
    line = LineString([tf(*c) for c in w['c']])
    if not line.intersects(near): continue
    br = t.get('bridge') == 'yes'
    if br and hw != 'steps' and line.length < 15: continue   # 短於 15 m 之步道小橋（如 Z2 北平西路側 7.5 m）非跨街天橋
    un = t.get('tunnel') == 'yes' or str(t.get('layer', '0')).startswith('-') or str(t.get('level', '')).startswith('-')
    if br:
        nm = t.get('name') or ('承德路天橋' if line.distance(Point(302130, 2771270)) < 60 else '光華數位新天地—三創空橋' if line.distance(Point(303640, 2770905)) < 30 else '跨堤人行橋' if ZONE == 'Z1' else '懷生國小西側・OSM 未具名' if line.distance(Point(304577, 2770825)) < 30 else '人行天橋（OSM 未具名）')
        add(line, cls='pass', type='footbridge' if hw != 'steps' else 'footbridge_steps', name=nm, osm=w['id'])
    elif un and line.intersection(near).length > 3:
        nm = t.get('name', '')
        typ = 'mall' if nm == '台北地下街' or (hw == 'corridor' and str(t.get('level', '')) == '-2') else 'underpass'
        add(line.intersection(near.buffer(40)), cls='pass', type=typ, name=nm or ('地下街廊道' if typ == 'mall' else '地下通道'), osm=w['id'])

# ---------- 阻隔 ----------
for g, p in [(shape(f['geometry']), f['properties']) for f in KB['features']]:
    if p['kind'] == 'median' and g.intersects(SLAB):
        add(g, cls='block', type='median', area=p['area'], note='高架下／旁中央分隔島：路段中無法穿越，須至路口')
for f in json.load(open(H / 'data/osm_furniture_4326.geojson'))['features']:
    p = f['properties']; g = transform(tf, shape(f['geometry']))
    if not g.intersects(band): continue
    if p['kind'].startswith('barrier_') and g.length < 1000:
        add(g.intersection(band.buffer(10)), cls='block', type='barrier', name={'barrier_wall': '圍牆', 'barrier_fence': '圍籬', 'barrier_hedge': '綠籬'}.get(p['kind'], '障礙'),
            note=f"OSM {p['tags'].get('barrier')}，長 {g.intersection(band.buffer(10)).length:.0f} m")
    elif p['kind'] == 'parking_entrance' and S.center.distance(g) < 12:
        add(g, cls='block', type='parking_ramp', name=(p['name'] or '地下停車場') + ' 車道出入口',
            note='位於大道分隔島內之汽車坡道出入口（OSM parking_entrance）')
rp = S.ramps.intersection(band)
if not rp.is_empty: add(rp, cls='block', type='ramp', name='市民高架匝道', note='匝道落地段兩側不可穿越')
# 無平面穿越長段
st = DS['stats']; s_list = sorted([p['s'] for g, p in sup if p['type'] == 'at_grade'])
marks = [st['s0']] + s_list + [st['s1']]
for a, b in zip(marks, marks[1:]):
    if b - a > GAP_LONG and a in s_list and b in s_list:
        seg = substring(S.center, a, b)
        add(seg, cls='block', type='gap', length=round(b - a), note=f'相鄰平面穿越間距 {b - a:.0f} m（> {GAP_LONG} m）')
# ---------- 通行元素合一圖層（2026-10-11 使用者指定：同一圖層、紅色半透明色塊，重疊處較深）----------
#   面：平面穿越行穿線（交工處）、台北地下街（OSM shop=mall，level -2）、捷運／機捷站體（OSM building=transportation／train_station）；
#   線→面：地下街廊道 5 m 寬、地下連通道 4 m（北門機捷連通道 6 m）、人行天橋 3.5 m（梯道 3 m）；點→面：出入口 5 m 方塊
CLIP = SLAB.buffer(4)    # 通行元素面只留本段（界線外 4 m 內）
def pa(g, typ, name='', level=None):
    g = g.intersection(CLIP)
    if not g.is_empty and g.area > .5:
        if level: add(g, cls='pass_area', type=typ, name=name, level=level)   # 告示圖描繪之樓層（23「樓層」）；無則 20 依類型判定
        else: add(g, cls='pass_area', type=typ, name=name)
for f in DS['features']:
    if f['properties']['kind'] == 'supply_stripe' and ZONE not in PED_XING and ZONE not in ALL_XING: pa(shape(f['geometry']), '平面穿越行穿線')
for g_, k_ in (XW if ZONE in PED_XING else []): pa(g_, '行人穿越道' if k_ == 'ped' else '平面穿越行穿線')   # Z6 起：交工處行穿線逐塊（十字路口不上圖、行人用上圖）
for g_ in XW_ALL: add(g_, cls='pass_area', type='行穿線', name='交工處行穿線', inside=bool(g_.intersects(SLAB)))   # Z8：十字路口與巷口皆上圖、不裁切（單元外由淡化遮罩處理）
# 地下街、捷運站、機捷站、台北車站地下通廊：改用告示圖描繪剪影（23_trace_underground.py；2026-10-11 使用者提供底圖），
#   取代 OSM 面；OSM 地下街廊道線落在地下街剪影內，不另畫（避免假性重疊）
_ug = H / 'data/underground_traced_EPSG3826.geojson'
UG_TYPE = {'地下街': '地下街', '捷運站': '捷運／車站站體', '機捷站': '捷運／車站站體', '車站地下通廊': '車站地下通廊'}
_ugf = [f for f in json.load(open(_ug))['features'] if shape(f['geometry']).intersects(near)] if _ug.exists() else []
USE_TRACED = bool(_ugf)          # 告示圖描繪只涵蓋台北車站一帶；本段無描繪者改用 OSM
for f in _ugf:
    pr = f['properties']; pa(shape(f['geometry']), UG_TYPE.get(pr['類型'], pr['類型']), pr['名稱'], pr.get('樓層'))
if not USE_TRACED:
    for f in osm:
        p = f['properties']
        if f['geometry']['type'] == 'LineString': continue
        g = transform(tf, shape(f['geometry'])).buffer(0)
        if not g.intersects(near): continue
        if p.get('shop') == 'mall' and str(p.get('layer', '0')).startswith('-'): pa(g, '地下街', p.get('name', ''))
        elif p.get('building') in ('transportation', 'train_station') and not (p.get('historic') or p.get('heritage')):   # 保存之舊站房（如華山車站）非通行元素
            pa(g, '捷運／車站站體', p.get('name', ''))
_mc = H / f'data/{ZONE}_mrt_ctx_EPSG3826.geojson'   # Z6 起：周邊捷運站體（33；單元外者亦列、不裁切，由範圍外淡化遮罩處理——使用者 2026-10-12）
if _mc.exists():
    for f in json.load(open(_mc))['features']:
        if shape(f['geometry']).distance(SLAB) > 450: continue       # 圖框外之站體（如忠孝敦化）不列
        add(shape(f['geometry']), cls='pass_area', type='捷運／車站站體', name=f['properties']['name'], level=f['properties']['level'], ctx=True)
_pk = H / f'data/{ZONE}_ug_parking_EPSG3826.geojson'   # Z7 起：市民大道地下停車場分段包絡（34；使用者 2026-10-12「算做剪影」）——B1，單元外者淡化、不裁切至單元
if _pk.exists():
    # 著色限於中央分隔島範圍（使用者 2026-10-12「把停車場著色的區域限制在分隔島的範圍」）：
    #   分段包絡 ∩ 17 市民高架分隔島（kind＝median）− 路徑（同 20 paths_geom：整合後道路面 ∪ 新工處人行道 ∪ 26 補齊碎塊）− 建物
    #   ※ 讀 26 之補齊碎塊：首次建圖時 26 apply 後須重跑 19
    _med = unary_union([shape(f['geometry']) for f in KB['features'] if f['properties']['kind'] == 'median'])
    _REB = Path.home() / 'Desktop/Civic_Rebuild_20260909_201934/data'
    _sw = [shape(f['geometry']).buffer(0) for f in json.load(open(_REB / 'taipei-sidewalks.geojson'))['features']]
    _fi = H / f'data/{ZONE}_road_islands_EPSG3826.geojson'
    _fill = [shape(f['geometry']).buffer(.05) for f in json.load(open(_fi))['features'] if f['properties']['decision'] == 'fill'] if _fi.exists() else []
    for f in json.load(open(_pk))['features']:
        env = shape(f['geometry']); wb_ = env.buffer(30)
        paths_ = unary_union([S.road.intersection(wb_)] + [q.intersection(wb_) for q in _sw if q.intersects(wb_)] + [q for q in _fill if q.intersects(wb_)])
        g = env.intersection(_med).difference(paths_).difference(S.bld)
        g = unary_union([q for q in getattr(g, 'geoms', [g]) if q.geom_type == 'Polygon' and q.area >= 2])
        if g.is_empty: continue
        add(g, cls='pass_area', type='地下停車場', name=f['properties']['name'], level='B1', ctx=True, levels=f['properties']['levels'],
            env_area=round(env.area), median_only=True)
for g, p in [(shape(f['geometry']), f['properties']) for f in feats if f['properties'].get('cls') == 'pass']:
    t = p.get('type')
    if t == 'mall' and not USE_TRACED: pa(g.buffer(2.5, cap_style='flat'), '地下街廊道', p.get('name', ''))
    elif t == 'underpass': pa(g.buffer(3.0 if p.get('name') == '北門機捷連通道' else 2.0, cap_style='flat'), '地下連通道', p.get('name', ''))
    elif t == 'footbridge': pa(g.buffer(1.75, cap_style='flat'), '人行天橋', p.get('name', ''))
    elif t == 'footbridge_steps': pa(g.buffer(1.5, cap_style='flat'), '人行天橋梯道', p.get('name', ''))
    elif t in ('mall_exit', 'mrt_exit'): pa(g.buffer(2.5, cap_style='square'), '出入口', p.get('name', ''))

# ---------- 特性建築（含目的地建物 tier D）；主角基地內拆除改建之現有建物 ----------
for f in KB['features']:
    if f['properties']['kind'] == 'key':
        feats.append({'type': 'Feature', 'geometry': f['geometry'], 'properties': {'cls': 'char', **f['properties']}})
    elif f['properties']['kind'] == 'replaced':
        feats.append({'type': 'Feature', 'geometry': f['geometry'], 'properties': {'cls': 'replaced', **f['properties']}})
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': feats,
           'slab': KB['slab'], 'stats': {'gaps': [round(b - a) for a, b in zip(s_list, s_list[1:])], 'crossings': s_list}},
          open(H / f'data/{ZONE}_ns_factors_EPSG3826.geojson', 'w'), ensure_ascii=False)
import collections
print(collections.Counter((f['properties']['cls'], f['properties'].get('type', f['properties'].get('tier'))) for f in feats))
print('gaps', [round(b - a) for a, b in zip(s_list, s_list[1:])])
