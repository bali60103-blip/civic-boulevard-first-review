# 地下街剪影（2026-10-11 使用者提供底圖）：依「台北車站全區位置圖及轉乘資訊」（Metro Taipei 站內告示，data/source_maps/）
#   手動描繪地下街、捷運站、機捷站、台北車站地下通廊之外框（像素座標），以路口控制點作薄板樣條（TPS）轉換至 EPSG:3826。
#   告示圖北向朝右（東＝下），為示意圖、比例不均（大道北側約 1.14 m/px、南側約 1.4 m/px），故用 TPS 而非單一仿射。
#   2026-10-11 增 Z2：控制點 12 → 16（中山北路 4 處），描繪捷運台北車站北端大廳、車站東側通廊、中山地下街 R區；各面加「樓層」屬性。
#   輸出 data/underground_traced_EPSG3826.geojson；19_ns_factors 以此取代 OSM 之地下街／站體面。
import json, sys
from pathlib import Path
import numpy as np
from scipy.interpolate import RBFInterpolator
from shapely.geometry import Polygon, mapping, Point

H = Path(__file__).resolve().parents[1]
SRC = H / 'data/source_maps/台北車站全區位置圖及轉乘資訊_MetroTaipei.webp'

# 控制點：告示圖像素（x 右＝北、y 下＝東）→ 地面 EPSG:3826（OSM 道路中心線交點；AXIS＝市民大道中心線）
CTRL = [
    ('長安西路×重慶北路一段', (553, 613), (301853.4, 2771587.9)),
    ('長安西路×太原路',       (553, 735), (302007.4, 2771554.3)),
    ('長安西路×承德路一段',   (553, 862), (302169.0, 2771514.3)),
    ('華陰街×重慶北路一段',   (462, 613), (301826.1, 2771482.5)),
    ('華陰街×太原路',         (462, 735), (301982.2, 2771446.2)),
    ('華陰街×承德路一段',     (462, 862), (302140.7, 2771404.4)),
    ('市民大道×塔城街',       (347, 390), (301511.3, 2771430.1)),
    ('市民大道×延平北路一段', (347, 497), (301657.9, 2771399.0)),
    ('市民大道×重慶北路一段', (347, 625), (301793.1, 2771353.6)),
    ('市民大道×太原路',       (347, 735), (301949.4, 2771319.3)),
    ('市民大道×承德路一段',   (349, 862), (302109.4, 2771279.1)),
    ('忠孝西路×重慶南路一段', (167, 662), (301790.2, 2771102.2)),
    # 2026-10-11 Z2 增補（承德路以東；告示圖上中山北路為斜線，像素依路名字列中心線量測）
    ('市民大道×中山北路一段', (389, 1229), (302543.9, 2771205.0)),
    ('華陰街×中山北路一段',   (460, 1239), (302571.0, 2771296.8)),
    ('長安西路×中山北路一段', (553, 1252), (302619.1, 2771401.8)),
    ('忠孝西路×中山北路一段', (141, 1195), (302424.8, 2770938.8)),
]
# 描繪外框（像素）：(名稱, 類型, 頂點)
TRACE = [
    ('北門站（松山新店線）', '捷運站', [(228, 378), (326, 378), (326, 356), (349, 356), (349, 440), (326, 440), (326, 402), (228, 402)]),
    ('台北地下街（Y區）', '地下街', [(333, 405), (362, 405), (362, 840), (373, 880), (373, 1035), (333, 1035)]),
    ('機場捷運 A1 台北車站（站體範圍）', '機捷站', [(261, 505), (333, 505), (333, 746), (269, 746), (269, 578), (261, 578)]),   # 東緣與 Y 區共邊
    ('機場捷運 A1 台北車站（月台）', '機捷站', [(300, 512), (323, 512), (323, 742), (297, 742), (297, 645), (300, 640)]),
    ('台北車站地下通廊（北側）', '車站地下通廊', [(240, 742), (335, 742), (335, 1040), (312, 1040), (312, 758), (240, 758)]),
    # Z2（2026-10-11）：捷運台北車站北端大廳（M1／M2／R1 交會，市民大道下）、台北車站東側通廊、中山地下街（R區，沿心中山向北）
    ('捷運台北車站（北端大廳）', '捷運站', [(332, 1034), (390, 1051), (385, 1076), (334, 1062)]),
    ('台北車站地下通廊（東側）', '車站地下通廊', [(230, 1030), (334, 1030), (334, 1040), (230, 1040)]),
    ('中山地下街（R區）', '地下街', [(390, 1051), (467, 1080), (520, 1097), (577, 1105), (623, 1102), (670, 1090), (723, 1082),
                                   (723, 1113), (670, 1120), (623, 1127), (577, 1130), (527, 1118), (470, 1102), (400, 1073), (385, 1076)]),
]
# 樓層（OSM level／layer）：台北地下街 level −2；中山地下街、捷運台北車站 level −1；機捷月台 B2；其餘站體、通廊 B1
LEVEL = {'台北地下街（Y區）': 'B2', '機場捷運 A1 台北車站（月台）': 'B2'}

P = np.array([c[1] for c in CTRL], float); G = np.array([c[2] for c in CTRL], float)
fwd = RBFInterpolator(P, G, kernel='thin_plate_spline', smoothing=0.0)
inv = RBFInterpolator(G, P, kernel='thin_plate_spline', smoothing=0.0)
# 留一驗證（leave-one-out）：估計控制點間之轉換誤差
loo = []
for i in range(len(P)):
    m = np.arange(len(P)) != i
    f = RBFInterpolator(P[m], G[m], kernel='thin_plate_spline')
    loo.append(float(np.linalg.norm(f(P[i:i + 1])[0] - G[i])))
def densify(pts, step=3.0):
    out = []
    for a, b in zip(pts, pts[1:] + pts[:1]):
        a, b = np.array(a, float), np.array(b, float); n = max(1, int(np.linalg.norm(b - a) / step))
        out += [a + (b - a) * t / n for t in range(n)]
    return np.array(out)
# 改用 OSM 面者（2026-10-11 使用者指出「心中山沒對準圖面」）：告示圖之 R區 斜向廊帶無控制點可校正，TPS 後偏西 15–20 m、29% 落在建物上；
#   OSM 中山地下街面與 B03 心中山線形公園、空照廊帶吻合（落在建物上 6%），故以 OSM 幾何取代（像素描繪保留於 TRACE 供追溯）
OSM_REPLACE = {'中山地下街（R區）': '中山地下街'}
_osm_cache = {}
def osm_geom(nm):
    if not _osm_cache:
        from pyproj import Transformer
        from shapely.geometry import shape
        from shapely.ops import transform, unary_union
        t_ = Transformer.from_crs(4326, 3826, always_xy=True).transform
        src = H.parents[0] / '02_南京至仁愛擴幅_20261005/source/expanded_osm.geojson'
        for f in json.load(open(src))['features']:
            n_ = f['properties'].get('name')
            if n_ in OSM_REPLACE.values() and f['geometry']['type'] != 'LineString':
                _osm_cache.setdefault(n_, []).append(transform(t_, shape(f['geometry'])).buffer(0))
        for k in list(_osm_cache): _osm_cache[k] = unary_union(_osm_cache[k])
    return _osm_cache[nm]
feats = []
for name, typ, pts in TRACE:
    g = Polygon(fwd(densify(pts))).buffer(0); src_ = 'Metro Taipei 台北車站全區位置圖（站內告示照片）描繪＋TPS 對位'
    if name in OSM_REPLACE:
        g = osm_geom(OSM_REPLACE[name]); src_ = f'OSM {OSM_REPLACE[name]}（2026-09-08）；告示圖描繪偏西 15–20 m，改用 OSM（與 B03 線形公園、空照吻合）'
    feats.append({'type': 'Feature', 'geometry': mapping(g), 'properties': {'名稱': name, '類型': typ, '樓層': LEVEL.get(name, 'B1'), '面積_m2': round(g.area),
                  '來源': src_}})
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}}, 'features': feats,
           'control': [{'名稱': n, 'px': p, 'xy': g} for n, p, g in CTRL], 'loo_err_m': [round(e, 1) for e in loo]},
          open(H / 'data/underground_traced_EPSG3826.geojson', 'w'), ensure_ascii=False, indent=0)
for f in feats: print(f['properties']['名稱'], f['properties']['面積_m2'], 'm2')
print('leave-one-out error (m):', [round(e, 1) for e in loo], 'median', round(float(np.median(loo)), 1))

if len(sys.argv) > 1 and sys.argv[1] == 'check':      # 檢核：將告示圖整張轉到地面座標，疊 OSM 道路與描繪外框
    import importlib.util, matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from PIL import Image
    from scipy.ndimage import map_coordinates
    spec = importlib.util.spec_from_file_location('s', H / 'scripts/02_sheet.py'); S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)
    img = np.asarray(Image.open(SRC).convert('RGB')).astype(float)
    x0, x1, y0, y1 = [float(v) for v in sys.argv[3:7]] if len(sys.argv) > 6 else (301380, 302260, 2771020, 2771640)
    gx, gy = np.meshgrid(np.linspace(x0, x1, 880), np.linspace(y1, y0, 620))
    pp = inv(np.c_[gx.ravel(), gy.ravel()])
    rgb = np.dstack([map_coordinates(img[:, :, c], [pp[:, 1], pp[:, 0]], order=1, cval=255).reshape(gx.shape) for c in range(3)]) / 255
    fig, ax = plt.subplots(figsize=(16, 11.3))
    ax.imshow(np.clip(rgb, 0, 1), extent=(x0, x1, y0, y1), alpha=.85)
    from shapely.geometry import box
    v = box(x0, y0, x1, y1)
    for ln in S.lines(S.road.boundary.intersection(v)): ax.plot(ln[:, 0], ln[:, 1], color='b', lw=.5)
    for f in feats:
        g = Polygon(f['geometry']['coordinates'][0]); ax.plot(*g.exterior.xy, color='r', lw=1.4)
    ax.plot(G[:, 0], G[:, 1], 'g+', ms=12, mew=2)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
    fig.savefig(sys.argv[2], dpi=90, bbox_inches='tight')
