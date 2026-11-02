# 匯出 DXF（EPSG:3826 公尺，未轉正，可與 02_南京至仁愛擴幅 線稿直接 XREF 疊合）
# 每單元內容裁至第一排街廓平面範圍；圖層前綴 FR_
import json, ezdxf, importlib.util
from pathlib import Path
from ezdxf import colors
from ezdxf.enums import TextEntityAlignment
from shapely.geometry import shape

H = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('sheet', H / 'scripts/02_sheet.py')
S = importlib.util.module_from_spec(spec); spec.loader.exec_module(S)  # 共用資料與各單元內容（不出圖）
S.VARIANT['full'] = True   # DXF 採完整版（Z4、Z6、Z7 不截斷）

doc = ezdxf.new('R2018', units=6); ms = doc.modelspace()
# 中文字型：Arial Unicode（Mac 內建、Windows Office 常見）；原線稿 Standard/txt 無法顯示中文
doc.styles.add('CJK', font='Arial Unicode.ttf').set_extended_font_data(family='Arial Unicode MS')
doc.linetypes.add('FR_DASH', pattern=[3.0, 2.0, -1.0], description='上方構造 __ __')
doc.linetypes.add('FR_DASHDOT', pattern=[12.0, 8.0, -2.0, 0.0, -2.0], description='截斷線 ____ . ____')
doc.linetypes.add('FR_LANE', pattern=[10.0, 4.0, -6.0], description='車道線 4 m 線 6 m 間（模型單位公尺）')
LAY = [('FR_REGION', 8, None), ('FR_BLOCK', 7, 50), ('FR_BLOCK_GROUND', (244, 242, 236), None), ('FR_BUILDING', 7, 18),
       ('FR_BUILDING_FILL', (201, 201, 201), None), ('FR_GREEN', (207, 229, 195), None), ('FR_ROAD_EDGE', 8, 25),
       ('FR_ELEVATED_DECK', 7, 50), ('FR_ELEVATED_CL', 8, 13), ('FR_RAMP', 7, 35), ('FR_CLIP_EDGE', 7, 35),
       ('FR_ZONE_CUT', (26, 155, 215), 50), ('FR_LABEL', 7, None), ('FR_ZONE_LABEL', (26, 155, 215), None)]
for n, c, lw in LAY:
    a = {'true_color': colors.rgb2int(c)} if isinstance(c, tuple) else {'color': c}
    if lw: a['lineweight'] = lw
    doc.layers.add(n, **a)
doc.layers.get('FR_ELEVATED_DECK').dxf.linetype = 'FR_DASH'
doc.layers.get('FR_RAMP').dxf.linetype = 'FR_DASH'
doc.layers.get('FR_CLIP_EDGE').dxf.linetype = 'FR_DASHDOT'
doc.layers.get('FR_REGION').off()

def polyline(g, L):
    for ln in S.lines(g):
        if len(ln) > 1: ms.add_lwpolyline([tuple(p) for p in ln], dxfattribs={'layer': L})

def hatch(g, L):
    for p in S.polys(g):
        h = ms.add_hatch(dxfattribs={'layer': L}); h.set_solid_fill(color=256)
        h.paths.add_polyline_path(list(p.exterior.coords), is_closed=True, flags=1)
        for r in p.interiors: h.paths.add_polyline_path(list(r.coords), is_closed=True, flags=16)

def text(s, x, y, hgt, L, rot=0):
    ms.add_text(s, height=hgt, rotation=rot, dxfattribs={'layer': L, 'style': 'CJK'}).set_placement((x, y), align=TextEntityAlignment.MIDDLE_CENTER)

for z in S.ZONES_USE:
    d = S.PZ(z); R = d['R']
    polyline(R, 'FR_REGION')
    for b in d['blocks']:
        hatch(b, 'FR_BLOCK_GROUND'); polyline(b.boundary if d.get('full') else b.boundary.difference(S.clip_e.buffer(.3)), 'FR_BLOCK')
    hatch(S.green.intersection(R), 'FR_GREEN')
    for g in d['bl']: hatch(g, 'FR_BUILDING_FILL')
    polyline(S.edges.intersection(R), 'FR_BUILDING')
    polyline(S.road.boundary.intersection(R), 'FR_ROAD_EDGE')
    dk = S.deck.intersection(R)
    if not dk.is_empty: polyline(dk.boundary.difference(R.boundary.buffer(.3)), 'FR_ELEVATED_DECK')
    polyline(S.elev.intersection(R), 'FR_ELEVATED_CL'); polyline(S.ramps.intersection(R), 'FR_RAMP')
    if not d.get('full'): polyline(S.clip_e.intersection(R.buffer(.5)), 'FR_CLIP_EDGE')
    for n, q in d['civ']: text(n, q.x, q.y, 4.0, 'FR_LABEL', d['ang'])
    for n, q, rot in d['streets']: text(n, q.x, q.y, 3.2, 'FR_LABEL', rot + d['ang'])
    for n, q in d['marks']: text(n, q.x, q.y, 3.0, 'FR_LABEL', d['ang'])
    zp = S.ZP[z]; c = R.centroid
    text(f"{z} {zp['from']}—{zp['to']}", c.x, R.bounds[3] + 25, 12, 'FR_ZONE_LABEL')
# 街道細部（04_street_detail.py）
DET = [('FR_SIDEWALK', 'sw', (234, 223, 196)), ('FR_SIDEWALK_SETBACK', 'sw_setback', (234, 223, 196)),
       ('FR_SIDEWALK_MARKED', 'sw_marked', (42, 157, 143)), ('FR_ARCADE_OFFICIAL', 'arcade_official', (94, 63, 168)),
       ('FR_ARCADE_EST', 'arcade_est', (176, 71, 143))]
for L, k, rgb in DET: doc.layers.add(L, true_color=colors.rgb2int(rgb))
doc.layers.add('FR_LANE_LINE', color=8, linetype='FR_LANE')
doc.layers.add('FR_CENTER_LINE', true_color=colors.rgb2int((224, 161, 0)), lineweight=35)
doc.layers.add('FR_LANE_SEP', color=8, lineweight=25)
doc.layers.add('FR_CROSSWALK', color=8)
REG_U = S.unary_union([S.PZ(z)['R'] for z in S.ZONES_USE])
for L, k, rgb in DET:
    for g, _ in S.SDK[k]:
        gi = g.intersection(REG_U)
        if gi.is_empty: continue
        hatch(gi, L); polyline(gi, L)
for L, k in (('FR_LANE_LINE', 'lane_line'), ('FR_CENTER_LINE', 'center_line'), ('FR_LANE_SEP', 'lane_sep')):
    for g, _ in S.SDK[k]: polyline(g.intersection(REG_U), L)
doc.layers.add('FR_TREE_PIT', color=7); doc.layers.add('FR_PLANTER', true_color=colors.rgb2int((127, 168, 106)))
doc.layers.add('FR_VENT', color=7); doc.layers.add('FR_MRT_ENTRANCE', color=7)
for L, k in (('FR_TREE_PIT', 'tree_pit'), ('FR_PLANTER', 'planter'), ('FR_VENT', 'vent')):
    for g, _ in S.SDK[k]:
        gi = g.intersection(REG_U)
        if gi.is_empty: continue
        polyline(gi, L)
        if k == 'vent':
            for pg in S.polys(gi):
                r = list(pg.minimum_rotated_rectangle.exterior.coords)
                ms.add_line(r[0], r[2], dxfattribs={'layer': L}); ms.add_line(r[1], r[3], dxfattribs={'layer': L})
for g, q in S.SDK['mrt_entrance']:
    if REG_U.contains(g):
        ms.add_circle((g.x, g.y), 1.0, dxfattribs={'layer': 'FR_MRT_ENTRANCE'})
        if q.get('ref'): text(q['ref'], g.x, g.y + 2.5, 2.0, 'FR_MRT_ENTRANCE')
for g, q in S.SDK['crosswalk_bar']:   # 行穿線白槓：具寬度之聚合線（寬＝槓寬 m）
    gi = g.intersection(REG_U)
    for ln in S.lines(gi):
        if len(ln) > 1: ms.add_lwpolyline([tuple(p) for p in ln], dxfattribs={'layer': 'FR_CROSSWALK', 'const_width': q['bar_w']})
# 照片判讀補繪（09_photo_features.py）與照片位置（10_photo_reading.py；僅 iPhone GPS 照片）
PL = [('PH_PIER', 7), ('PH_PIER_UNVERIFIED', 8), ('PH_PIER_CAP', 8), ('PH_MEDIAN_PLANTING', (127, 168, 106)), ('PH_MOTO_ROW', 8),
      ('PH_SHELTER', 7), ('PH_YOUBIKE', 7), ('PH_ARTWORK', 7), ('PH_PARKING_ENTRANCE', 7), ('PH_RAIL_DISUSED', 7), ('PH_STEPS', 7),
      ('PH_CAMERA', 1)]
for n, c in PL:
    doc.layers.add(n, **({'true_color': colors.rgb2int(c)} if isinstance(c, tuple) else {'color': c}))
doc.layers.get('PH_CAMERA').off()
LMAP = {'pier': 'PH_PIER', 'pier_cap': 'PH_PIER_CAP', 'median_planting': 'PH_MEDIAN_PLANTING', 'moto_row': 'PH_MOTO_ROW',
        'osm_shelter': 'PH_SHELTER', 'osm_bike_rental': 'PH_YOUBIKE', 'osm_artwork': 'PH_ARTWORK',
        'osm_parking_entrance': 'PH_PARKING_ENTRANCE', 'osm_rail_disused': 'PH_RAIL_DISUSED', 'osm_steps': 'PH_STEPS'}
for k, L0 in LMAP.items():
    for g, q in S.PFK[k]:
        gi = g.intersection(REG_U.buffer(3))
        if gi.is_empty: continue
        L = 'PH_PIER_UNVERIFIED' if k == 'pier' and q.get('unverified') else L0
        if gi.geom_type == 'Point':
            ms.add_circle((gi.x, gi.y), 1.2, dxfattribs={'layer': L})
            if q.get('name'): text(q['name'], gi.x, gi.y - 3, 1.8, L)
        else:
            if k in ('pier', 'median_planting', 'moto_row'): hatch(gi, L)
            polyline(gi, L)
import json as _j
for r in _j.load(open(S.H / 'data/photos/photo_index.json')):
    if 'x' not in r: continue
    ms.add_circle((r['x'], r['y']), 1.0, dxfattribs={'layer': 'PH_CAMERA'})
    import math as _m
    h = _m.radians(r['heading']); ms.add_line((r['x'], r['y']), (r['x'] + 8 * _m.sin(h), r['y'] + 8 * _m.cos(h)), dxfattribs={'layer': 'PH_CAMERA'})
    text(r['id'], r['x'] + 1.5, r['y'] + 1.5, 1.5, 'PH_CAMERA')
for f in S.ZF:
    if 'cut' in f['properties']:
        g = shape(f['geometry']).intersection(S.center.buffer(S.D_MAX + 30))
        polyline(g, 'FR_ZONE_CUT')
out = H / '市民大道_Z1-Z8_第一排街廓詳細平面_EPSG3826.dxf'
doc.saveas(out)
print(out.name, len(ms))
