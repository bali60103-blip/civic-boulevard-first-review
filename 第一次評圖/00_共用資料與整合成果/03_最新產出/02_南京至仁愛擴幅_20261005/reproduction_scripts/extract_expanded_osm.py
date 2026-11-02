import json,hashlib
from pathlib import Path
import osmium
from shapely import wkb
from shapely.geometry import box,mapping
from pyproj import Transformer
R=Path(__file__).resolve().parents[2];O=R/'output/a00_expanded_20261005';P=Path('/Users/ktlu/Downloads/taiwan-260908.osm.pbf')
T=Transformer.from_crs(3826,4326,always_xy=True);pts=[T.transform(x,y) for x in [300835,307645] for y in [2769700,2772650]];B=box(min(x for x,y in pts),min(y for x,y in pts),max(x for x,y in pts),max(y for x,y in pts));xmin,ymin,xmax,ymax=B.bounds
fac=osmium.geom.WKBFactory();features=[]
class Extract(osmium.SimpleHandler):
 def way(self,w):
  if not w.tags.get('highway'):return
  try:
   pts=[(n.lon,n.lat) for n in w.nodes]
   if not any(xmin<=x<=xmax and ymin<=y<=ymax for x,y in pts):return
   g=wkb.loads(fac.create_linestring(w),hex=True)
   if g.intersects(B):features.append({'type':'Feature','properties':{**dict(w.tags),'@id':f'way/{w.id}','@nodes':[n.ref for n in w.nodes]},'geometry':mapping(g)})
  except osmium.InvalidLocationError:pass
 def area(self,a):
  if not a.tags.get('building') and not a.tags.get('building:part'):return
  try:
   pts=[(n.lon,n.lat) for ring in a.outer_rings() for n in ring]
   if not any(xmin<=x<=xmax and ymin<=y<=ymax for x,y in pts):return
   g=wkb.loads(fac.create_multipolygon(a),hex=True)
   if g.intersects(B):features.append({'type':'Feature','properties':{**dict(a.tags),'@id':('way/' if a.from_way() else 'relation/')+str(a.orig_id())},'geometry':mapping(g)})
  except osmium.InvalidLocationError:pass
Extract().apply_file(str(P),locations=True,idx='flex_mem')
(O/'source/expanded_osm.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features},ensure_ascii=False))
(O/'source/local_osm_manifest.json').write_text(json.dumps({'source':str(P),'source_filename_date':'2026-09-08','extracted':'2026-10-05','bbox4326':list(B.bounds),'features':len(features),'sha256':hashlib.sha256(P.read_bytes()).hexdigest(),'note':'Offline source; not claimed current. Public Overpass failed, no missing-data substitution.'},ensure_ascii=False,indent=2))
print('Extracted',len(features),flush=True)
