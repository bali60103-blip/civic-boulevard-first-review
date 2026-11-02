# 文化部文化資產局 國家文化資產網開放資料（https://nchdb.boch.gov.tw；API https://data.boch.gov.tw/opendata/v2/assetsCase/{類別}.json）
# 1.1 古蹟、1.2 歷史建築、1.3 聚落建築群、1.4 紀念建築；篩出本圖幅（EPSG:3826）範圍內者 → data/文資登錄_圖幅內.json
import json, urllib.request
from pathlib import Path
from pyproj import Transformer
H = Path(__file__).resolve().parents[1]
tf = Transformer.from_crs(4326, 3826, always_xy=True)
out = []
for code, lab in [('1.1', '古蹟'), ('1.2', '歷史建築'), ('1.3', '聚落建築群'), ('1.4', '紀念建築')]:
    data = json.load(urllib.request.urlopen(f'https://data.boch.gov.tw/opendata/v2/assetsCase/{code}.json', timeout=180))
    for x in data:
        if not x.get('longitude'): continue
        e, n = tf.transform(float(x['longitude']), float(x['latitude']))
        if 300935 <= e <= 307545 and 2770000 <= n <= 2771910:
            out.append({'caseId': x['caseId'], 'name': x['caseName'], 'type': lab, 'grade': x.get('assetsClassifyName'),
                        'kinds': [t['name'] for t in x.get('assetsTypes') or []], 'E': round(e, 1), 'N': round(n, 1),
                        'url': x.get('caseUrl'), 'gov': x.get('govInstitutionName')})
json.dump({'source': 'data.boch.gov.tw opendata v2 assetsCase 1.1–1.4', 'fetched': '2026-10-13', 'cases': out},
          open(H / 'data/文資登錄_圖幅內.json', 'w'), ensure_ascii=False, indent=1)
print(len(out))
