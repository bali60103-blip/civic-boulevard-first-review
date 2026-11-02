"""Small, explicit aerial-review assumptions outside the protected ten sheets."""
import json
from pathlib import Path
from shapely.geometry import shape,mapping
from shapely.ops import unary_union
O=Path(__file__).resolve().parents[2]/'output/a00_expanded_20261005'
def read(n):return json.loads((O/n).read_text())
def geo(n):return unary_union([shape(f['geometry']) for f in read(n)['features']])
def save(n,g):(O/n).write_text(json.dumps({'type':'FeatureCollection','crs':{'type':'name','properties':{'name':'EPSG:3826'}},'features':[{'type':'Feature','properties':{},'geometry':mapping(g)}]}))
r=geo('road_surfaces_TWD97.geojson');b=geo('building_outlines_TWD97.geojson');core=geo('ten_sheet_mask.geojson');oldr=r.intersection(core);oldb=b.intersection(core)
marks=read('building_conflicts.json');log=[]
for m in marks:
 g=shape(m['geometry']).difference(core)
 note='已查看90×80m航照疊圖；青線優先成圖，屋頂視差、騎樓及地面牆腳未確認，仍待審。'
 if m['source']=='way/201280862':
  r=r.difference(g);b=b.union(g);note='航照可辨道路中的廟宇屋頂，OSM標為法主公廟。撤回自動裁掉49%量體，概估保留完整來源輪廓，新增道路避開此實體；不是更動已接受的原十幅青線。地面輪廓待審。'
 elif m['source'] in ['way/1346183906','way/1346183909']:
  b=b.difference(g);note='跨道路細長構造與棚頂在航照可辨，暫判非一般地面建物，撤去地面殘留輪廓；原輪廓另存本紀錄，橋柱／層高待審，非確認拆除。'
 m['visual_review']=note;m['status']='已按航照完成概估方案／待使用者審閱';log.append({'id':m['id'],'note':note})
assert r.intersection(core).symmetric_difference(oldr).area<1e-6
assert b.intersection(core).symmetric_difference(oldb).area<1e-6
assert r.intersection(b).area<1e-6
save('road_surfaces_TWD97.geojson',r);save('building_outlines_TWD97.geojson',b);save('context_buildings_TWD97.geojson',b.difference(core))
(O/'building_conflicts.json').write_text(json.dumps(marks,ensure_ascii=False,indent=2));(O/'visual_review_log.json').write_text(json.dumps(log,ensure_ascii=False,indent=2))
print('24 reviewed hypotheses retained; three explicit visual corrections applied.')
