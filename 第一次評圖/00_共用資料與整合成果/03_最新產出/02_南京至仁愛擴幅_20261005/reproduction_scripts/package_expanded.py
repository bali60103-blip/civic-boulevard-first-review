import json,shutil,hashlib,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2];O=R/'output/a00_expanded_20261005';S=R/'output/a01_a10_unified_v2_20261004'
if sys.argv[1]=='prepare':
 from shapely.geometry import shape
 from shapely.ops import unary_union
 def geo(p):return unary_union([shape(f['geometry']) for f in json.loads(p.read_text())['features']])
 q=json.loads((O/'qa.json').read_text());core=geo(O/'ten_sheet_mask.geojson');r=geo(O/'road_surfaces_TWD97.geojson');b=geo(O/'building_outlines_TWD97.geojson')
 for k,v in {'protected_core_road_difference_m2':r.intersection(core).symmetric_difference(geo(S/'road_surfaces_TWD97.geojson')).area,'protected_core_building_difference_m2':b.intersection(core).symmetric_difference(geo(S/'building_outlines_TWD97.geojson')).area,'fill_outside_ten_sheets_m2':geo(O/'building_fill_TWD97.geojson').difference(core).area,'road_building_overlap_m2':r.intersection(b).area}.items():assert v<1e-6;q[k]=v
 log=(O/'audit_native_output.txt').read_text(errors='replace');assert 'Total errors found 0 fixed 0' in log and 'QA_OPEN_OUTLINES=0' in log
 q.update({'native_audit_errors':0,'native_open_complete_rings':0,'visual_review_panels':6,'visual_review_markers':24,'new_markers_accepted':0,'existing_pending_ids':211})
 (O/'qa.json').write_text(json.dumps(q,ensure_ascii=False,indent=2))
 shutil.copyfile(R/'reconstruction/道路平面圖清理_workflow.txt',O/'道路平面圖清理_workflow_修訂25.txt')
 shutil.copyfile(R/'output/review_acceptance_20261004_710R010_012/user_decisions.json',O/'existing_user_decisions.json')
 (O/'reproduction_scripts').mkdir(exist_ok=True)
 for n in ['expanded_export.py','expanded_visual_adjust.py','build_expanded_index.py','extract_expanded_osm.py','fetch_expanded_aerial.py','package_expanded.py']:shutil.copyfile(Path(__file__).parent/n,O/'reproduction_scripts'/n)
 (O/'SHA256.txt').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(O)) for p in sorted(O.rglob('*')) if p.is_file() and p.name!='SHA256.txt')+'\n')
 print('Final geometry and native audit verified; package ready.')
elif sys.argv[1]=='desktop':
 dest=Path('/Users/ktlu/Desktop/市民大道_南京仁愛擴幅_20261005');assert not dest.exists()
 shutil.copytree(O,dest,ignore=shutil.ignore_patterns('*.bak','*.dwl','*.dwl2','index_only.pdf'))
 # Quarantine failed network response rather than presenting it as GIS data.
 failed=dest/'source/boundary_roads.json'
 if failed.exists() and failed.read_text(errors='replace').lstrip().startswith('<'):
  (dest/'source/failed_requests').mkdir(exist_ok=True);failed.rename(dest/'source/failed_requests/overpass_error.html')
 for n in ['A01_A10_Nanjing_Renai_20261005.dwg','pdf/A01_A10_Nanjing_Renai_20261005.pdf']:
  assert hashlib.sha256((O/n).read_bytes()).digest()==hashlib.sha256((dest/n).read_bytes()).digest()
 (dest/'SHA256.txt').write_text('\n'.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(dest)) for p in sorted(dest.rglob('*')) if p.is_file() and p.name!='SHA256.txt')+'\n')
 print(dest)
