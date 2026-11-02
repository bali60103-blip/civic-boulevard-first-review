"""Expanded context model; protect all original ten sheets and fill only their buildings."""
import json,re,math,collections
from pathlib import Path
import numpy as np,shapefile
from pyproj import Transformer
from shapely.geometry import shape,mapping,box,LineString,Point
from shapely.ops import unary_union,transform,substring
from shapely import make_valid
from shapely.strtree import STRtree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
R=Path(__file__).resolve().parents[2];O=R/'output/a00_expanded_20261005';S=R/'output/a01_a10_unified_v2_20261004'
read=lambda p:json.loads(p.read_text())
def dump(n,x):(O/n).write_text(json.dumps(x,ensure_ascii=False,indent=2))
def parts(g,kind='Polygon'):
 if g.is_empty:return
 if g.geom_type==kind:yield g
 elif hasattr(g,'geoms'):
  for p in g.geoms:yield from parts(p,kind)
def clean(g):return unary_union([p for p in parts(make_valid(g)) if p.area>1e-6])
def geo(p):return unary_union([shape(f['geometry']) for f in read(p)['features']])
def savegeo(n,g):dump(n,{'type':'FeatureCollection','crs':{'type':'name','properties':{'name':'EPSG:3826'}},'features':[{'type':'Feature','properties':{},'geometry':mapping(g)}]})
q=read(S/'qa.json');core=unary_union([box(*s['bounds']) for s in q['sheets']]);oldroad=geo(S/'road_surfaces_TWD97.geojson');oldbuild=geo(S/'building_outlines_TWD97.geojson')
BB=[300935,2770000,307545,2771910];CLIP=box(*BB);EXT=CLIP.difference(core);T=Transformer.from_crs(4326,3826,always_xy=True)
allowed={'trunk','trunk_link','primary','primary_link','secondary','secondary_link','tertiary','tertiary_link','unclassified','residential','service','living_street'}
def ground(p):return p.get('bridge','no') in ['no',''] and p.get('tunnel','no') in ['no',''] and str(p.get('layer','0')) in ['0',''] and p.get('location')!='underground' and p.get('indoor')!='yes'
def number(v):
 m=re.search(r'-?\d+(?:\.\d+)?',str(v));return float(m.group()) if m else 0
roads=[];buildings=[];refs=[];boundaries=[]
for f in read(O/'source/expanded_osm.geojson')['features']:
 p=f['properties'];g=make_valid(transform(T.transform,shape(f['geometry'])))
 if not g.intersects(CLIP.buffer(60)):continue
 id=p['@id'];name=p.get('name','')
 if 'highway' in p:
  if re.fullmatch('(南京東路|南京西路|仁愛路)[一二三四五六七八]?段?',name):boundaries.append({'name':name,'geometry':mapping(g.intersection(CLIP))})
  if p['highway'] not in allowed or not ground(p) or g.geom_type!='LineString':refs.append({'source':id,'reason':'非地面車行線，不畫作道路外緣','tags':p,'geometry':mapping(g.intersection(CLIP))});continue
  if not g.intersects(EXT.buffer(40)):continue
  fn='幹道' if p['highway'] in ['trunk','primary','secondary'] else '支線' if p['highway'].startswith('tertiary') else '服務通道' if p['highway']=='service' else '巷道'
  roads.append({'id':'XH'+id.split('/')[-1],'source':id,'tags':p,'g':g,'function':fn,'anchors':[]})
 else:
  if not g.intersects(EXT):continue
  if not ground(p) or p.get('building') in ['roof','no'] or number(p.get('building:min_level',0))>0 or number(p.get('min_height',0))>0 or ('building' not in p and p.get('building:part')=='roof'):
   refs.append({'source':id,'reason':'非地面或棚頂投影，不填為地面建物','tags':p,'geometry':mapping(g.intersection(EXT))});continue
  buildings.append({'source':id,'tags':p,'g':clean(g.intersection(EXT))})
roads.sort(key=lambda x:int(x['source'].split('/')[-1]));tree=STRtree([x['g'] for x in roads]);widths=[]
for fid,sr in enumerate(shapefile.Reader('/Users/ktlu/Downloads/路寬檔_提供 (1) 2/roadsize2',encoding='utf-8').iterShapeRecords()):
 g=shape(sr.shape.__geo_interface__)
 if g.geom_type!='LineString' or not g.intersects(EXT):continue
 w=number(sr.record['road_width']);a=np.array(g.coords[0]);b=np.array(g.coords[-1]);v=b-a
 if not 2<=w<=60 or np.linalg.norm(v)<.01:continue
 v/=np.linalg.norm(v);mid=Point((a+b)/2);cand=[]
 for i in tree.query(g.buffer(1.5)):
  r=roads[i]['g'];s=r.project(mid);pt=r.interpolate(s);t=np.array(r.interpolate(min(r.length,s+2)).coords[0])-np.array(r.interpolate(max(0,s-2)).coords[0])
  if np.linalg.norm(t)<.001 or abs(np.dot(v,t/np.linalg.norm(t)))>.35 or pt.distance(g)>1.5 or r.intersection(g).geom_type=='MultiPoint':continue
  cand.append((int(i),s))
 loc=[roads[i]['g'].interpolate(s) for i,s in cand];good=bool(loc) and max((a.distance(b) for a in loc for b in loc),default=0)<2
 widths.append({'fid':fid,'raw_width_m':w,'status':'MATCHED' if good else 'MULTI_AXIS' if cand else 'UNMATCHED','candidates':[roads[i]['id'] for i,s in cand]})
 if good:
  for i,s in cand:roads[i]['anchors'].append({'station':s,'width':w,'fid':fid})
surfaces=[];segments=[];deg=collections.Counter()
for r in roads:
 for xy in r['g'].coords:deg[tuple(round(v,3) for v in xy)]+=1
for r in roads:
 g=r['g'];p=r['tags'];cuts={0.,g.length};cuts.update(g.project(Point(x)) for x in g.coords[1:-1] if deg[tuple(round(v,3) for v in x)]>1)
 for a in r['anchors']:cuts.update([max(0,a['station']-60),a['station'],min(g.length,a['station']+60)])
 cuts=sorted(cuts)
 for j,(a,b) in enumerate(zip(cuts,cuts[1:])):
  line=substring(g,a,b)
  if line.length<.1 or not line.intersects(EXT):continue
  explicit=re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)\s*m?',str(p.get('width','')).strip());lanes=number(p.get('lanes',0));one=p.get('oneway') in ['yes','1','-1'];anc=min(r['anchors'],key=lambda x:abs(x['station']-(a+b)/2)) if r['anchors'] else None
  if explicit and 1<=float(explicit.group(1))<=40:w=float(explicit.group(1));reason='OSM width，語義未實測核定'
  elif one and r['function']=='幹道':w=max(4,lanes*3+1) if lanes else 8;reason='分向道路概估，不重複套全路寬'
  elif anc and abs(anc['station']-(a+b)/2)<=60 and anc['width']<=24:w=anc['width'];reason='同軸路寬檔局部支持，定義待審'
  elif lanes:w=lanes*3+(2 if lanes>=2 else .5);reason='OSM車道標籤概估，未逐車道核定'
  else:w={'幹道':14,'支線':7,'巷道':4.5,'服務通道':3.5}[r['function']];reason='道路功能暫定概估，非固定實測寬度'
  surf=line.buffer(w/2,cap_style=2,join_style=1)
  for xy in [line.coords[0],line.coords[-1]]:
   if deg[tuple(round(v,3) for v in xy)]>1:surf=surf.union(Point(xy).buffer(w/2,quad_segs=8))
  surfaces.append(surf.intersection(EXT));segments.append({'id':r['id']+f'-S{j:03}','source':r['source'],'name':p.get('name','未命名'),'function':r['function'],'width_m':w,'reason':reason,'lane_count_source':lanes or None,'lane_count_verified':False,'node_ids':p.get('@nodes'),'geometry':mapping(line.intersection(EXT)),'status':'已概估成圖／待審'})
newroad=clean(unary_union(surfaces));road=clean(newroad.union(oldroad))
sourcebuild=clean(unary_union([b['g'] for b in buildings]));newbuild=clean(sourcebuild.difference(road));build=clean(newbuild.union(oldbuild))
conf=[]
for b in buildings:
 g=b['g'];cut=g.intersection(road).area
 if g.area>0 and cut/g.area>.35 and cut>5:conf.append({'id':'XB'+b['source'].replace('/','-'),'source':b['source'],'removed_m2':cut,'ratio':cut/g.area,'geometry':mapping(g),'status':'青線優先裁切假設／待審，非已證實拆除'})
assert build.intersection(road).area<1e-5
assert build.intersection(core).symmetric_difference(oldbuild).area<1e-5
assert road.intersection(core).symmetric_difference(oldroad).area<1e-5
savegeo('road_surfaces_TWD97.geojson',road);savegeo('building_outlines_TWD97.geojson',build);savegeo('building_fill_TWD97.geojson',oldbuild);savegeo('context_buildings_TWD97.geojson',newbuild);savegeo('ten_sheet_mask.geojson',core)
dump('segment_decisions.json',segments);dump('width_matching.json',widths);dump('source_references.json',refs);dump('building_conflicts.json',conf);dump('boundary_roads.json',boundaries)
dump('qa.json',{'date':'2026-10-05','bounds':BB,'sheets':q['sheets'],'source_date':'2026-09-08 filename date','scale':10000,'source_road_ways':len(roads),'new_segments':len(segments),'source_buildings':len(buildings),'major_cut_marks':len(conf),'width_matches':dict(collections.Counter(w['status'] for w in widths)),'road_building_overlap_m2':build.intersection(road).area,'protected_core_road_difference_m2':road.intersection(core).symmetric_difference(oldroad).area,'protected_core_building_difference_m2':build.intersection(core).symmetric_difference(oldbuild).area,'fill_outside_ten_sheets_m2':oldbuild.difference(core).area,'lane_count_verified':False,'streetview_verified':False,'section_50cm_verified':False})
manifest=read(O/'imagery_manifest.json')['images'];views=[]
for col in range(3):
 for row in range(2):
  b=[BB[0]+col*(BB[2]-BB[0])/3,BB[1]+row*955,BB[0]+(col+1)*(BB[2]-BB[0])/3,BB[1]+(row+1)*955];id=f'REVIEW_{col+1}{row+1}';views.append({'id':id,'bounds':b})
  fig,ax=plt.subplots(figsize=(18,8),dpi=120)
  for im in manifest:
   v=im['bbox']
   if box(*b).intersects(box(*v)):ax.imshow(Image.open(O/'imagery'/im['file']),extent=[v[0],v[2],v[1],v[3]])
  clip=box(*b)
  for g,color in [(road,'cyan'),(build,'#ffdc35')]:
   for p in parts(g.intersection(clip)):
    for ring in [p.exterior]+list(p.interiors):ax.plot(*ring.xy,color=color,lw=.35)
  for s in q['sheets']:
   for p in parts(box(*s['bounds']).intersection(clip)):ax.plot(*p.exterior.xy,color='#ff3090',lw=1)
  ax.set_xlim(b[0],b[2]);ax.set_ylim(b[1],b[3]);ax.axis('off');ax.set_title(id+' | cyan road / yellow building / pink existing sheet extents');fig.tight_layout();fig.savefig(O/(id+'.png'));plt.close(fig)
dump('review_views.json',views);print('Built expanded context',len(roads),len(segments),len(buildings),len(conf),flush=True)
