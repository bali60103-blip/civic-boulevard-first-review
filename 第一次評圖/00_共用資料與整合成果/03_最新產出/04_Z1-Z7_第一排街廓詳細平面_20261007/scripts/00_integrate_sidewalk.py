# 街廓線與官方人行道整合（2026-10-09）：以市府新工處人行道範圍修正線稿道路面（路緣），使街廓外框＝人行道外緣（路緣）
#   線稿道路面（02_南京至仁愛擴幅 road_surfaces）寬度依 OSM 車道數推估；官方人行道與之常錯開：
#   一、人行道凸入道路面（線稿路寬偏寬）：該段人行道併入相鄰街廓（只接觸一個街廓者；跨巷口連到兩街廓者不併，以免街廓相連）。
#   二、人行道內縮、與路緣間留有窄縫（線稿路寬偏窄）：路面∪人行道做 5 m 閉運算所補之窄縫，位於街廓內且同時貼路面與人行道者 → 改為道路面。
#   輸出 data/road_surfaces_integrated_EPSG3826.geojson，01、02、04、09 改讀此檔；人行道繪製以整合後路緣裁切。
import json
from pathlib import Path
from shapely.geometry import shape, mapping, box
from shapely.ops import unary_union
from shapely.strtree import STRtree

H = Path(__file__).resolve().parents[1]
ROOT = H.parents[1]
BASE = ROOT / '03_最新產出/02_南京至仁愛擴幅_20261005'
REB = Path.home() / 'Desktop/Civic_Rebuild_20260909_201934/data'
CLOSE = 2.5          # 閉運算半徑（補 ≤ 5 m 窄縫）
GAP_W = 5.0          # 窄縫平均寬上限（2A/P）
TOUCH = 0.3

frame = box(300935, 2770000, 307545, 2771910)
road = shape(json.load(open(BASE / 'road_surfaces_TWD97.geojson'))['features'][0]['geometry']).buffer(0)
sw = [shape(f['geometry']).buffer(0) for f in json.load(open(REB / 'taipei-sidewalks.geojson'))['features']]
S = unary_union([g for g in sw if g.intersects(frame)]).intersection(frame)
blocks = [g for g in frame.difference(road).geoms if g.area > 1]
bld = shape(json.load(open(BASE / 'building_outlines_TWD97.geojson'))['features'][0]['geometry']).buffer(0)
btree = STRtree(blocks)

# 一、凸入道路面之人行道
spill = S.intersection(road)
add, skip = [], []
for p in getattr(spill, 'geoms', [spill]):
    if p.geom_type != 'Polygon' or p.area < 0.5: continue
    near = [i for i in btree.query(p.buffer(TOUCH), predicate='intersects')]
    (add if len(near) == 1 else skip).append(p)
# 二、人行道內縮之窄縫
closed = unary_union([road, S]).buffer(CLOSE, join_style='mitre').buffer(-CLOSE, join_style='mitre')
gap_all = closed.difference(road).difference(S)
blk_u = unary_union(blocks)
gaps = []
for p in getattr(gap_all, 'geoms', [gap_all]):
    if p.geom_type != 'Polygon' or p.area < 1: continue
    if 2 * p.area / p.length > GAP_W: continue
    if p.intersection(blk_u).area < .8 * p.area: continue
    if p.distance(road) > TOUCH or p.distance(S) > TOUCH: continue
    p = p.difference(bld)          # 窄縫不得壓到建物
    if p.area >= .5: gaps.append(p)
road_new = unary_union([road.difference(unary_union(add)), unary_union(gaps)]).buffer(0)
json.dump({'type': 'FeatureCollection', 'crs': {'type': 'name', 'properties': {'name': 'EPSG:3826'}},
           'features': [{'type': 'Feature', 'geometry': mapping(road_new),
                         'properties': {'source': 'road_surfaces_TWD97 + 新工處人行道範圍整合', 'spill_added_m2': round(sum(p.area for p in add)),
                                        'spill_skipped_m2': round(sum(p.area for p in skip)), 'gap_to_road_m2': round(sum(p.area for p in gaps))}}]},
          open(H / 'data/road_surfaces_integrated_EPSG3826.geojson', 'w'))
print('sidewalk spill into road → merged to blocks:', len(add), round(sum(p.area for p in add)), 'm2;',
      'skipped (crossing / floating):', len(skip), round(sum(p.area for p in skip)), 'm2')
print('gaps between curb and inset sidewalk → road:', len(gaps), round(sum(p.area for p in gaps)), 'm2')
print('road area', round(road.area), '→', round(road_new.area))
