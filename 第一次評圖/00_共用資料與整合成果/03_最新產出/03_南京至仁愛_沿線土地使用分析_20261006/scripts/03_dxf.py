# 匯出 DXF（EPSG:3826 公尺）：每類一圖層，實心填色＋邊線；高架、匝道、距離帶另層
import json, ezdxf
from pathlib import Path
from ezdxf import colors
from shapely.geometry import shape
H = Path(__file__).resolve().parents[1]
src = (H / 'scripts/01_classify.py').read_text()
CLASSES = eval(src[src.index('CLASSES = [') + 10: src.index(']\nCODE') + 1])
doc = ezdxf.new('R2018', units=6); ms = doc.modelspace()
for k, n, c in CLASSES:
    rgb = tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))
    doc.layers.add(f'LU_{k}_{n.split("（")[0].replace("／", "_")}', true_color=colors.rgb2int(rgb))
lname = {k: f'LU_{k}_{n.split("（")[0].replace("／", "_")}' for k, n, c in CLASSES}
for f in json.load(open(H / 'data/landuse_pieces_EPSG3826.geojson'))['features']:
    g = shape(f['geometry']); L = lname[f['properties']['cls']]
    for p in getattr(g, 'geoms', [g]):
        if p.geom_type != 'Polygon': continue
        h = ms.add_hatch(dxfattribs={'layer': L}); h.set_solid_fill(color=256)
        if not f['properties']['zone']: h.transparency = 0.7  # 300 m 範圍外（未被範圍線切到）之建物淡化
        h.paths.add_polyline_path(list(p.exterior.coords), is_closed=True, flags=1)
        for r in p.interiors: h.paths.add_polyline_path(list(r.coords), is_closed=True, flags=16)
civ = json.load(open(H / 'data/civic_elevated_EPSG3826.json'))
for L, key, col in (('CIVIC_ELEVATED', 'elevated', 7), ('CIVIC_RAMPS', 'ramps', 8)):
    doc.layers.add(L, color=col)
    g = shape(civ[key])
    for ln in getattr(g, 'geoms', [g]): ms.add_lwpolyline(list(ln.coords), dxfattribs={'layer': L})
doc.layers.add('BUFFER_100_200_300', color=8)
el = shape(civ['elevated'])
for d in (100, 200, 300):
    b = el.buffer(d, resolution=24)
    for p in getattr(b, 'geoms', [b]):
        ms.add_lwpolyline(list(p.exterior.coords), close=True, dxfattribs={'layer': 'BUFFER_100_200_300'})
doc.layers.add('ZONE_CUT', true_color=colors.rgb2int((26, 155, 215)), lineweight=70)
doc.layers.add('ZONE_AREA', true_color=colors.rgb2int((26, 155, 215))).off()
doc.layers.add('ZONE_LABEL', true_color=colors.rgb2int((26, 155, 215)))
for f in json.load(open(H / 'data/zones_EPSG3826.geojson'))['features']:
    g = shape(f['geometry']); pr = f['properties']
    if 'cut' in pr:
        for ln in getattr(g, 'geoms', [g]): ms.add_lwpolyline(list(ln.coords), dxfattribs={'layer': 'ZONE_CUT'})
        continue
    for pg in getattr(g, 'geoms', [g]):
        ms.add_lwpolyline(list(pg.exterior.coords), close=True, dxfattribs={'layer': 'ZONE_AREA'})
    c = g.centroid
    ms.add_text(f"{pr['id']} {pr['from']}—{pr['to'].split('／')[0]}", height=25,
                dxfattribs={'layer': 'ZONE_LABEL'}).set_placement((c.x, g.bounds[3] + 30), align=ezdxf.enums.TextEntityAlignment.BOTTOM_CENTER)
def hatch_poly(g, L):
    for pg in getattr(g, 'geoms', [g]):
        if pg.geom_type != 'Polygon': continue
        h = ms.add_hatch(dxfattribs={'layer': L}); h.set_solid_fill(color=256)
        h.paths.add_polyline_path(list(pg.exterior.coords), is_closed=True, flags=1)
        for r in pg.interiors: h.paths.add_polyline_path(list(r.coords), is_closed=True, flags=16)
for k, L, rgb in (('PARK', 'GREEN_公園', (140, 201, 124)), ('GRASS', 'GREEN_草地樹林', (207, 231, 193)), ('SPORT', 'GREEN_運動場遊戲場', (178, 219, 160))):
    doc.layers.add(L, true_color=colors.rgb2int(rgb))
    for f in json.load(open(H / 'data/green_EPSG3826.geojson'))['features']:
        if f['properties']['kind'] == k: hatch_poly(shape(f['geometry']), L)
SHOW_UNDERBRIDGE = False  # 橋下空間暫不輸出；改 True 即恢復
if SHOW_UNDERBRIDGE:
    doc.layers.add('UNDERBRIDGE_橋下空間', true_color=colors.rgb2int((247, 182, 207)))
    doc.layers.add('UNDERBRIDGE_OUTLINE', true_color=colors.rgb2int((194, 24, 91)))
    doc.layers.add('UNDERBRIDGE_LABEL', true_color=colors.rgb2int((194, 24, 91)))
    for f in json.load(open(H / 'data/underbridge_EPSG3826.geojson'))['features']:
        g = shape(f['geometry']); pr = f['properties']
        hatch_poly(g, 'UNDERBRIDGE_橋下空間')
        for pg in getattr(g, 'geoms', [g]):
            for r in [pg.exterior, *pg.interiors]:
                ms.add_lwpolyline(list(r.coords), close=True, dxfattribs={'layer': 'UNDERBRIDGE_OUTLINE'})
        if pr['kind'] == '主線橋下':
            c = g.representative_point()
            ms.add_text(f"{pr['id']} 橋下 {pr['len_m']}m x {pr['avg_w_m']:.0f}m {pr['area_m2']}m2", height=8,
                        dxfattribs={'layer': 'UNDERBRIDGE_LABEL'}).set_placement((c.x, c.y - 25), align=ezdxf.enums.TextEntityAlignment.TOP_CENTER)
# 交通停車（07_parking.py，來源：本機 Blender 重建專案）
doc.layers.add('PARKING_地下停車場分段_假設包絡', color=8); doc.layers.add('PARKING_出入口候選', color=7); doc.layers.add('STREETVIEW_查核點', color=2)
for f in json.load(open(H / 'data/parking_streetview_EPSG3826.geojson'))['features']:
    pr = f['properties']; g = shape(f['geometry'])
    if pr['kind'] == 'section':
        ms.add_lwpolyline(list(g.exterior.coords), close=True, dxfattribs={'layer': 'PARKING_地下停車場分段_假設包絡'})
        ms.add_text(f"{pr['name']} B{pr['levels']}", height=8, dxfattribs={'layer': 'PARKING_地下停車場分段_假設包絡'}).set_placement((g.centroid.x, g.centroid.y))
    elif pr['kind'] == 'entrance':
        ms.add_circle((g.x, g.y), 3, dxfattribs={'layer': 'PARKING_出入口候選'})
    else:
        ms.add_circle((g.x, g.y), 5, dxfattribs={'layer': 'STREETVIEW_查核點'})
        ms.add_text(pr['name'], height=6, dxfattribs={'layer': 'STREETVIEW_查核點'}).set_placement((g.x + 6, g.y + 6))
# 停車供給（08_parking_fetch.py，北市好停車）
doc.layers.add('PARKING_PMA_路外停車場', color=8); doc.layers.add('PARKING_PMA_路邊汽車格', true_color=colors.rgb2int((230, 126, 34)))
for f in json.load(open(H / 'data/parking_pma_EPSG3826.geojson'))['features']:
    pr = f['properties']; x, y = f['geometry']['coordinates']
    if pr['kind'] == 'lot' and pr['car'] > 0:
        ms.add_circle((x, y), max(3, pr['car'] ** .5 * .8), dxfattribs={'layer': 'PARKING_PMA_路外停車場'})
        ms.add_text(f"{pr['name']} 汽{pr['car']}／機{pr['moto']}", height=4, dxfattribs={'layer': 'PARKING_PMA_路外停車場'}).set_placement((x + 4, y + 4))
    elif pr['kind'] == 'curb' and pr['car']:
        ms.add_point((x, y), dxfattribs={'layer': 'PARKING_PMA_路邊汽車格'})
doc.layers.add('PARKING_停車場建物', true_color=colors.rgb2int((58, 120, 181)))
for f in json.load(open(H / 'data/parking_buildings_EPSG3826.geojson'))['features']:
    hatch_poly(shape(f['geometry']), 'PARKING_停車場建物')
    c = shape(f['geometry']).representative_point()
    ms.add_text(f"P 汽{f['properties']['car']}／機{f['properties']['moto']}", height=4, dxfattribs={'layer': 'PARKING_停車場建物'}).set_placement((c.x, c.y))
SHOW_POI_INDUSTRY = False  # 店家點產業圖已改為逐色提取，點位不輸出；改 True 即恢復
if SHOW_POI_INDUSTRY:
    # 產業分布點（06_industry.py）：每產業別一層
    src6 = (H / 'scripts/06_industry.py').read_text()
    FAMILIES = eval(src6[src6.index('FAMILIES = [') + 11: src6.index(']\nIND') + 1])
    for fk, fname, items in FAMILIES:
        for n, c in items:
            doc.layers.add(f'IND_{fk}_{n}', true_color=colors.rgb2int(tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))))
    FK = {n: fk for fk, _, items in FAMILIES for n, _ in items}
    for f in json.load(open(H / 'data/industry_pois_EPSG3826.geojson'))['features']:
        n = f['properties']['ind']
        ms.add_circle(f['geometry']['coordinates'], 2.0, dxfattribs={'layer': f'IND_{FK[n]}_{n}'})
# 平面停車場地面範圍、未對到範圍之平面停車場點（10_parking_landuse.py）
doc.layers.add('PARKING_平面停車場', true_color=colors.rgb2int((110, 110, 110)))
for f in json.load(open(H / 'data/surface_parking_EPSG3826.geojson'))['features']:
    g = shape(f['geometry'])
    if f['properties']['kind'] == 'surface':
        for pg in getattr(g, 'geoms', [g]):
            if pg.geom_type == 'Polygon': ms.add_lwpolyline(list(pg.exterior.coords), close=True, dxfattribs={'layer': 'PARKING_平面停車場'})
    else:
        ms.add_circle((g.x, g.y), 4, dxfattribs={'layer': 'PARKING_平面停車場'})
out = H / '市民高架沿線_建物現況使用_EPSG3826.dxf'; doc.saveas(out); print(out)
