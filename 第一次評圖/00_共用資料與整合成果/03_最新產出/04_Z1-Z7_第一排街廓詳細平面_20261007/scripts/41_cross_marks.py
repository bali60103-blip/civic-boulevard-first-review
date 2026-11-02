# 可通過之路口標記（2026-10-14 使用者於 Z1 紙本以藍筆畫斜線標記：「在 Z1–Z8 每個可以通過的十字路口都做像我藍色筆跡這樣的標記」；
#   同日補充「我要你覆蓋整個十字路口」）
#   範圍：整個路口＝「十」字（兩矩形聯集，扣除建物）：
#     大道部分＝路緣至路緣（行穿線範圍，含中央分隔島）× 沿大道涵蓋側街寬（量測）＋兩側各 ARM；
#     側街部分＝自路緣跨過平行側車道（Z1 等）伸入側街 LEG × 側街寬（以量測段中點為中心）。
#     扣除建物與特性建築／主角場所（Z8 里程 5577 m 橫越範圍跨過臺北機廠）。
#     只保留與橫越行穿線相連之部分；同一路口兩處平面穿越（如 Z7 復興南路、敦化南路東西兩側）之標記合併為一。
#     路段中行人穿越道（無側街）：沿大道方向＝行穿線寬＋兩側各 ARM_MID。
#   位置：13 之平面穿越點（ns_factors 之 pass／crossing），以交工處行穿線（2024-07）驗證是否真的橫越大道：
#     只計橫越大道方向之行穿線（長軸與大道法線夾角 < 40°、距中心線 45 m 內）；跨越中心線或分布於中心線南北兩側者為真。
#     與大道平行者（橫越側街）不算——Z3 里程 1686 m、Z4 里程 2158 m、Z7 里程 5185 m 因此不標（13 誤判）。
#   輸出 data/{Z}_cross_marks_EPSG3826.geojson（name、s、n_stages、span_m、kind）；20 讀此檔（G_XMARK 圖層）。
#   2026-10-14 再修訂：20 只畫「本範圍 ∩ 路徑面」並以淺藍上色（使用者「只要留道路上色區域」），本範圍本身不再上圖。
#   執行：python3 scripts/41_cross_marks.py Z1 … 或 all
import sys, json, glob, importlib.util
from pathlib import Path
import numpy as np
import shapefile
from shapely.geometry import shape, mapping, Point, Polygon, LineString, box
from shapely.ops import unary_union, transform
from pyproj import Transformer

H = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sheet', H / 'scripts/02_sheet.py')
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
tf = Transformer.from_crs(4326, 3826, always_xy=True).transform
LEG, ARM, ARM_MID = 8.0, 8.0, 6.0   # m：伸入側街（量到側街處再外伸）、沿大道於側街兩側外伸、路段中行穿線兩側外伸
REB = Path.home() / 'Desktop/Civic_Rebuild_20260909_201934/data'
SW = [shape(f['geometry']).buffer(0) for f in json.load(open(REB / 'taipei-sidewalks.geojson'))['features']]

XW = []
for fp in glob.glob(str(H / 'data/source_taipei/crosswalk_202407121519/**/*.shp'), recursive=True):
    try: shs = list(shapefile.Reader(fp, encoding='utf-8').iterShapes())
    except Exception: shs = list(shapefile.Reader(fp, encoding='big5').iterShapes())
    for sh in shs:
        g = shape(sh.__geo_interface__)
        if g.is_empty: continue
        if abs(g.centroid.x) < 1000: g = transform(tf, g)
        g = g.buffer(0)
        if not g.is_empty and g.distance(S.center) < 60: XW.append(g)

def paths_local(z, wb):
    # 同 20 paths_geom：整合後道路面 ∪ 新工處人行道 ∪ 26 補齊碎塊 − 建物
    parts = [S.road.intersection(wb)] + [q.intersection(wb) for q in SW if q.intersects(wb)]
    fi = H / f'data/{z}_road_islands_EPSG3826.geojson'
    if fi.exists():
        parts += [shape(f['geometry']).buffer(.05) for f in json.load(open(fi))['features'] if f['properties']['decision'] == 'fill' and shape(f['geometry']).intersects(wb)]
    return unary_union(parts).difference(S.bld.intersection(wb.buffer(10)))

def axis(g):
    # 最小外接矩形之長軸（端點 a、b）
    r = list(g.minimum_rotated_rectangle.exterior.coords)[:4]
    e = [(np.hypot(r[i + 1][0] - r[i][0], r[i + 1][1] - r[i][1]), i) for i in range(3)]
    _, i = max(e); j = (i + 2) % 4
    a = ((r[i][0] + r[(i + 3) % 4][0]) / 2, (r[i][1] + r[(i + 3) % 4][1]) / 2)
    b = ((r[i + 1][0] + r[j][0]) / 2, (r[i + 1][1] + r[j][1]) / 2)
    return np.array(a), np.array(b)

def side(c, s):
    a = S.center.interpolate(s); b = S.center.interpolate(min(s + 5, S.center.length))
    return 1 if (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x) > 0 else -1

def obox(c, u, hu, hv, hu2=None):
    # 以 u 為軸之矩形：u 向 −hu2…+hu（hu2 缺省＝hu）、v 向 ±hv
    v = np.array([-u[1], u[0]]); hu2 = hu if hu2 is None else hu2
    return Polygon([tuple(c + a_ * u + b_ * v) for a_, b_ in ((-hu2, -hv), (hu, -hv), (hu, hv), (-hu2, hv))])

def leg(pth, c, u, sgn, half):
    # 側街：由路緣（half）往外逐一量測（8、14、20、28、36 m），沿大道方向之量測線與路徑面之交段（最接近軸線者）< 50 m＝進入兩側有街廓之側街。
    #   回傳（側街寬、量測距中點距離、側街中心之 v 座標）；量不到（側邊為整段人行道、平行道路、公園）回傳 None。
    #   Z1 等有平行側車道者，靠外側之量測線才落在側街。行穿線多畫在路口邊緣，故側街中心取量測段中點，不取行穿線軸。
    v = np.array([-u[1], u[0]])
    for off in (8, 14, 20, 28, 36):
        p0 = c + sgn * (half + off) * u
        seg = LineString([tuple(p0 - 60 * v), tuple(p0 + 60 * v)]).intersection(pth)
        segs = sorted((q for q in getattr(seg, 'geoms', [seg]) if q.geom_type == 'LineString' and q.length > 3), key=lambda q: q.distance(Point(p0)))
        if segs and segs[0].distance(Point(p0)) < 12 and segs[0].length < 50:
            m = np.array(segs[0].interpolate(.5, normalized=True).coords[0])
            return segs[0].length, half + off, float((m - c) @ v)
    return None

def uv_box(c, u, ua, ub, va, vb):
    v = np.array([-u[1], u[0]])
    return Polygon([tuple(c + a_ * u + b_ * v) for a_, b_ in ((ua, va), (ub, va), (ub, vb), (ua, vb))])

def marks(z):
    d = json.load(open(H / f'data/{z}_ns_factors_EPSG3826.geojson'))
    slab = shape(d['slab'])
    # 特性建築與主角場所（建物、開放地；不含不上圖之基地範圍）：標記不覆蓋（Z8 地面道路偏離高架，橫越範圍跨過臺北機廠）
    CHARU = unary_union([shape(f['geometry']).buffer(.3) for f in d['features'] if f['properties'].get('cls') == 'char' and not f['properties'].get('site')
                         and shape(f['geometry']).geom_type in ('Polygon', 'MultiPolygon')])
    out, log = [], []
    for f in d['features']:
        p = f['properties']
        if p.get('cls') != 'pass' or p.get('type') != 'crossing': continue   # crossing_false（19 判為巷口）已排除
        s = p['s']; c0 = S.center.interpolate(s)
        if not slab.buffer(5).contains(c0): continue
        a0 = S.center.interpolate(max(s - 5, 0)); a1 = S.center.interpolate(min(s + 5, S.center.length))
        t = np.array([a1.x - a0.x, a1.y - a0.y]); t /= np.linalg.norm(t); nrm = np.array([-t[1], t[0]])
        cand = []
        for g in XW:
            if abs(S.center.project(g.centroid) - s) > 45 or g.distance(S.center) > 45: continue   # 45 m：Z8 地面市民大道五段偏離高架中心線
            a, b = axis(g); ax_ = (b - a) / max(np.linalg.norm(b - a), 1e-6)
            if abs(float(ax_ @ nrm)) < np.cos(np.radians(40)): continue      # 非橫越大道方向（橫越側街者）
            cand.append(g)
        ok = any(g.intersects(S.center) for g in cand) or len({side(g.centroid, s) for g in cand}) == 2
        if not ok:
            log.append(f'{z} {p.get("name")} s={s:.0f}: 無橫越大道之行穿線，不標'); continue
        core = [g for g in cand if abs(S.center.project(g.centroid) - s) <= 20] or cand   # 路口 20 m 內之橫越行穿線
        xw = unary_union(core); a, b = axis(xw.convex_hull)
        u = (b - a) / np.linalg.norm(b - a); span = float(np.linalg.norm(b - a)); mid = (a + b) / 2
        wb = box(mid[0] - 150, mid[1] - 150, mid[0] + 150, mid[1] + 150); pth = paths_local(z, wb)
        lp, lm = leg(pth, mid, u, 1, span / 2), leg(pth, mid, u, -1, span / 2)
        legs = [l for l in (lp, lm) if l]
        kind = '十字路口' if legs else '路段中行人穿越道'
        v = np.array([-u[1], u[0]]); vx = [float((np.array(q) - mid) @ v) for q in xw.convex_hull.exterior.coords]
        if legs:   # 大道部分：路緣至路緣 × 涵蓋側街（及行穿線）兩側各 ARM
            va = min([l[2] - l[0] / 2 for l in legs] + [min(vx)]) - ARM; vb = max([l[2] + l[0] / 2 for l in legs] + [max(vx)]) + ARM
        else:
            va, vb = min(vx) - ARM_MID, max(vx) + ARM_MID
        parts = [uv_box(mid, u, -span / 2 - 1, span / 2 + 1, va, vb)]
        for l, sg in ((lp, 1), (lm, -1)):   # 側街部分：自路緣跨過平行側車道、伸入側街 LEG
            if l: parts.append(uv_box(mid, u, sg * (span / 2), sg * (l[1] + LEG), l[2] - l[0] / 2, l[2] + l[0] / 2))
        reg = unary_union(parts).difference(S.bld.intersection(wb)).difference(CHARU.intersection(wb))
        reg = unary_union([q for q in getattr(reg, 'geoms', [reg]) if q.geom_type == 'Polygon' and q.buffer(1).intersects(xw)])
        reg = reg.buffer(.6, join_style=2).buffer(-.6, join_style=2)   # 去除細縫
        out.append({'geom': reg, 'blvd': parts[0], 'props': {'name': p.get('name') or '', 's': round(s, 1), 'n_stages': p.get('n_stages'), 'span_m': round(span, 1),
                                           'kind': kind, 'leg_w_m': round(max(l[0] for l in legs), 1) if legs else None, 'n_xw': len(cand)}})
    # 同一路口兩處平面穿越（側街兩側各一，如 Z7 復興南路、敦化南路）：標記相疊、或同名且相距 40 m 內者合併為一，
    #   並以兩者大道部分之凸包補滿中間（敦化南路中央林蔭帶），覆蓋整個路口
    merged = []
    for m in out:
        hit = next((k for k in merged if k['geom'].intersects(m['geom']) or
                    (m['props']['name'] and k['props']['name'] == m['props']['name'] and k['geom'].distance(m['geom']) < 40)), None)
        if hit is None: merged.append(m); continue
        bridge = unary_union([hit['blvd'], m['blvd']]).convex_hull.difference(S.bld)
        hit['geom'] = unary_union([hit['geom'], m['geom'], bridge]); hit['blvd'] = unary_union([hit['blvd'], m['blvd']])
        hit['props']['s2'] = m['props']['s']; hit['props']['span_m'] = max(hit['props']['span_m'], m['props']['span_m'])
    feats = [{'type': 'Feature', 'geometry': mapping(m['geom']), 'properties': m['props']} for m in merged]
    json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': feats,
               'params': {'LEG': LEG, 'ARM': ARM, 'ARM_MID': ARM_MID}, 'source': '交工處行穿線 2024-07＋13 平面穿越＋路徑面（同 20）'},
              open(H / f'data/{z}_cross_marks_EPSG3826.geojson', 'w'), ensure_ascii=False)
    print(z, f'{len(out)} 處平面穿越 → {len(feats)} 個路口標記：', '、'.join((f['properties']['name'] or '（未具名）') + ('' if f['properties']['kind'] == '十字路口' else '＊') +
                                                               ('（兩處合併）' if 's2' in f['properties'] else '') for f in feats))
    for l in log: print('  ', l)

if __name__ == '__main__':
    zs = ['Z%d' % i for i in range(1, 9)] if (len(sys.argv) < 2 or sys.argv[1] == 'all') else sys.argv[1:]
    for z in zs: marks(z)
