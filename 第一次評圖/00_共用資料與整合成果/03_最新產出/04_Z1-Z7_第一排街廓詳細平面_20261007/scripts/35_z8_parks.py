# Z8 南北兩側園區串連（使用者 2026-10-12 指定）：
#   要表達的問題＝「Z8 三個主角被市民大道分在兩岸——松山文創園區、臺北大巨蛋（文化體育園區）在南，國家鐵道博物館（臺北機廠）在北；
#     兩大文化園區隔大道對望，正對之段無平面穿越、無天橋或地下道，又是匝道進出之段落」；匝道、行穿線畫出來。
#   主角（workflow 三，不改寫）：松山文創＋大巨蛋＋國家鐵道博物館（含 U10）。各園區：
#     建物＝園區範圍內之線稿建物（代表點落於範圍內）→ tier A（酒紅剪影）；線稿缺漏而 OSM 有之建物（與線稿重疊 < 30%）以 OSM 輪廓補（note 註明）。
#     開放地＝園區範圍扣除路徑（整合後道路面 ∪ 新工處人行道）與建物 → tier O（淡酒紅）。
#     園區範圍：OSM 面——松山文創園區（landuse=recreation_ground）、臺北文化體育園區（landuse=commercial，扣除與松菸重疊）、
#       臺北機廠鐵道博物館園區（landuse=industrial、historic=heritage）＋臺北機廠縫紉工場舊址（大道南側，historic=heritage，併入鐵博群組）。
#   另輸出（20 讀取）：data/Z8_ramps_EPSG3826.geojson——市民高架匝道（OSM highway=trunk_link、名稱含「匝道」）展成面：
#     寬＝車道數（lanes，缺者 1）× 3.5 m＋1.0 m（路肩示意）；bridge=yes 為高架段（+1），其餘為落地段（地面阻隔，±0）。
#   OSM 來源：臺灣 PBF 2026-09-08（~/Downloads/taiwan-260908.osm.pbf），首次執行擷取後快取於 data/osm_z8_pbf_cache_EPSG3826.geojson。
import json, sys, importlib.util
from pathlib import Path
from shapely.geometry import shape, mapping, box, Point, LineString
from shapely.ops import unary_union, transform
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
ZONE = 'Z8'
spec = importlib.util.spec_from_file_location('sheet', H / 'scripts/02_sheet.py')
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
S.VARIANT['full'] = True
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform
PBF = Path.home() / 'Downloads/taiwan-260908.osm.pbf'
CACHE = H / 'data/osm_z8_pbf_cache_EPSG3826.geojson'
REB = Path.home() / 'Desktop/Civic_Rebuild_20260909_201934/data'
SITES = ('臺北機廠鐵道博物館園區', '臺北機廠縫紉工場舊址', '松山文創園區', '臺北文化體育園區')
BB = (305900, 2770300, 307700, 2771500)          # 擷取範圍（EPSG:3826）

# ---------- OSM 擷取（快取）：園區面、範圍內建物面、匝道線 ----------
if not CACHE.exists() or set(json.load(open(CACHE)).get('names', [])) != set(SITES):
    import osmium
    from shapely import wkb
    inv = Transformer.from_crs(3826, 4326, always_xy=True).transform
    L0, A0 = inv(BB[0], BB[1]); L1, A1 = inv(BB[2], BB[3])
    fab = osmium.geom.WKBFactory(); out = []
    for o in osmium.FileProcessor(str(PBF)).with_locations().with_areas():
        t = dict(o.tags); nm = t.get('name', '')
        site = o.is_area() and nm in SITES
        bld = o.is_area() and 'building' in t
        ramp = o.is_way() and t.get('highway') == 'trunk_link' and '匝道' in nm
        if not (site or bld or ramp): continue
        try:
            g = wkb.loads(fab.create_multipolygon(o), hex=True) if o.is_area() else LineString([(n.lon, n.lat) for n in o.nodes])
        except Exception: continue
        c = g.representative_point()
        if not (L0 < c.x < L1 and A0 < c.y < A1): continue
        out.append({'type': 'Feature', 'geometry': mapping(transform(tf, g)),
                    'properties': {'kind': 'site' if site else 'building' if bld else 'ramp', 'osm': f"{'a' if o.is_area() else 'w'}{o.id}", **t}})
    json.dump({'type': 'FeatureCollection', 'source': 'OSM 臺灣 PBF 2026-09-08（taiwan-260908.osm.pbf）', 'names': list(SITES), 'features': out},
              open(CACHE, 'w'), ensure_ascii=False)
OC = json.load(open(CACHE))['features']
def osm_site(nm):
    gs = [shape(f['geometry']).buffer(0) for f in OC if f['properties']['kind'] == 'site' and f['properties'].get('name') == nm]
    return unary_union(gs) if gs else None

# ---------- 路徑（同 20 paths_geom 之底）與建物 ----------
WB = box(*BB)
sw = unary_union([g for g in (shape(f['geometry']).buffer(0) for f in json.load(open(REB / 'taipei-sidewalks.geojson'))['features']) if g.intersects(WB)])
PATHS = unary_union([S.road.intersection(WB), sw.intersection(WB)])
BL = [b for b in S.bld.geoms if b.intersects(WB)]
OB = [(shape(f['geometry']).buffer(0), f['properties']) for f in OC if f['properties']['kind'] == 'building']
def side(g):
    c = g.representative_point(); d = S.center.project(c); a = S.center.interpolate(d); b = S.center.interpolate(min(d + 5, S.center.length))
    return '北' if (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x) > 0 else '南'
feats = []
def add(g, **pr):
    g = g.buffer(0)
    if g.is_empty or g.area < 1: return
    pr.setdefault('side', side(g)); pr.setdefault('area', round(g.area)); pr['dist_m'] = round(S.center.distance(g))
    feats.append({'type': 'Feature', 'geometry': mapping(g), 'properties': pr})
RULE_TXT = 'Z8 判準（使用者 2026-10-12）：南北兩側園區串連——主角三園區之建物與戶外空間'
def place(grp, name, extent, note):
    # 園區：線稿建物（代表點落於範圍內）＋線稿缺漏之 OSM 建物 → tier A；範圍扣除路徑與建物 → tier O
    bs = [b for b in BL if extent.contains(b.representative_point())]
    lu = unary_union(bs) if bs else Point(0, 0).buffer(0)
    ad = [(g, p) for g, p in OB if extent.contains(g.representative_point()) and g.intersection(lu).area < .3 * g.area and g.area > 30]
    bu = unary_union(bs + [g for g, _ in ad]) if (bs or ad) else None
    if bu is not None:
        add(bu, kind='key', tier='A', group=grp, name=name, rule=RULE_TXT,
            note=note + f"；建物 {len(bs)} 棟（線稿）" + (f"＋OSM 補 {len(ad)} 棟（{'、'.join(p.get('name', '未具名') for _, p in ad if p.get('name'))[:60] or '未具名'}；線稿缺漏）" if ad else '')
                 + f"，投影 {bu.area:,.0f} ㎡")
    op = extent.difference(PATHS)
    if bu is not None: op = op.difference(bu.buffer(.3))
    op = unary_union([q for q in getattr(op, 'geoms', [op]) if q.geom_type == 'Polygon' and q.area > 20])
    if not op.is_empty: add(op, kind='key', tier='O', group=grp, name=name + '：戶外空間', rule=RULE_TXT,
                            note=note + f"；戶外空間 {op.area:,.0f} ㎡（範圍扣除路徑與建物：廣場、花園、空地、生態池等）")
    return bu, op

# 1 國家鐵道博物館（臺北機廠）——大道北側；縫紉工場舊址（大道南側）併入同群組
rw = osm_site('臺北機廠鐵道博物館園區')
place('國家鐵道博物館（臺北機廠）', '國家鐵道博物館（臺北機廠）', rw,
      f'OSM 臺北機廠鐵道博物館園區（landuse=industrial、historic=heritage）{rw.area:,.0f} ㎡；2013 年遷廠，2025-07-31 第一階段開放，其餘修復中（03 工業倉儲調查 S11）')
sew = osm_site('臺北機廠縫紉工場舊址')
if sew is not None:
    place('國家鐵道博物館（臺北機廠）', '臺北機廠縫紉工場舊址', sew, f'OSM historic=heritage、{sew.area:,.0f} ㎡；位於大道南側，與機廠本體隔大道')
# 2 松山文創園區（大道南側）
ss = osm_site('松山文創園區')
place('松山文創園區', '松山文創園區', ss, f'OSM 松山文創園區（原松山菸廠，landuse=recreation_ground）{ss.area:,.0f} ㎡；1998 年停產（03 工業倉儲調查 S10）')
# 3 臺北大巨蛋（臺北文化體育園區，扣除與松菸重疊）
dome = osm_site('臺北文化體育園區').difference(ss.buffer(.5))
dome = unary_union([q for q in getattr(dome, 'geoms', [dome]) if q.area > 200])
place('臺北大巨蛋（文化體育園區）', '臺北大巨蛋（臺北文化體育園區）', dome,
      f'OSM 臺北文化體育園區（landuse=commercial）扣除與松菸重疊後 {dome.area:,.0f} ㎡；含臺北大巨蛋（2023-12 啟用）、遠雄巨蛋大樓')
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': feats,
           'source': 'OSM 臺灣 PBF 2026-09-08；02 線稿建物；路徑＝整合後道路面 ∪ 新工處人行道', 'date': '2026-10-12'},
          open(H / f'data/{ZONE}_permeable_EPSG3826.geojson', 'w'), ensure_ascii=False)

# ---------- 市民高架匝道（高架段＋落地段）----------
rp = []
for f in OC:
    p = f['properties']
    if p['kind'] != 'ramp': continue
    ln = shape(f['geometry'])
    if not ln.intersects(box(305800, 2770300, 307700, 2771500)): continue   # 圖框範圍（單元外者由淡化遮罩處理）
    try: lanes = max(1, int(str(p.get('lanes', '1')).split(';')[0]))
    except ValueError: lanes = 1
    w = 3.5 * lanes + 1.0
    elev = p.get('bridge') == 'yes'
    rp.append({'type': 'Feature', 'geometry': mapping(ln.buffer(w / 2, cap_style='flat')),
               'properties': {'name': p['name'], 'kind': 'ramp_elev' if elev else 'ramp_grade', 'lanes': lanes, 'width_m': w, 'len_m': round(ln.length),
                              'layer': p.get('layer', '0'), 'osm': p['osm'], 'side': side(ln), 'dist_m': round(S.center.distance(ln))}})
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': rp,
           'note': '使用者 2026-10-12：Z8 匝道畫出來。OSM trunk_link（名稱含匝道）展成面：寬＝車道數 × 3.5 m＋1.0 m；bridge=yes＝高架段，其餘＝落地段'},
          open(H / f'data/{ZONE}_ramps_EPSG3826.geojson', 'w'), ensure_ascii=False)

# ---------- 東界：基隆路中心線（workflow 三「光復南路—基隆路」；五-1 走廊內〔軸線兩側 340 m〕沿路口中心線、走廊外垂直延伸）----------
#   S.center（02）止於 E307105（高架轉向基隆路處），05 之 Z8 東端原為中心線終點；主題圖改依 workflow 以基隆路為界（使用者 2026-10-12 Z8）
import numpy as np
KL = S.streets['基隆路一段']; ax_y = S.center.coords[-1][1]
pts = []
for y in np.arange(ax_y - 340, ax_y + 341, 10):
    hit = KL.intersection(LineString([(306500, y), (307800, y)]))
    xs = [q.x for q in getattr(hit, 'geoms', [hit]) if q.geom_type == 'Point']
    if xs: pts.append((float(np.mean(xs)), float(y)))
xs_ = np.convolve([p[0] for p in pts], np.ones(5) / 5, mode='same'); xs_[:2] = [p[0] for p in pts[:2]]; xs_[-2:] = [p[0] for p in pts[-2:]]
line = [(pts[0][0], 2769000.0)] + [(float(x), y) for x, (_, y) in zip(xs_, pts)] + [(pts[-1][0], 2773000.0)]
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}},
           'features': [{'type': 'Feature', 'geometry': mapping(LineString(line)), 'properties': {'name': '基隆路一段（Z8 東界）', 'from': '光復南路', 'to': '基隆路'}}],
           'note': '雙向車道中心線取平均、5 點移動平均；走廊外垂直延伸；由南而北'}, open(H / f'data/{ZONE}_east_cut_EPSG3826.geojson', 'w'), ensure_ascii=False)
print('東界 基隆路', len(pts), '點', [round(v) for v in LineString(line[1:-1]).bounds])

import collections
for f in feats:
    p = f['properties']; print(p['tier'], p['group'], p['name'], p['side'], p['area'], '㎡', p['dist_m'], 'm')
print('匝道', collections.Counter((f['properties']['name'], f['properties']['kind']) for f in rp))
