# 巷道優先概算版

先固定既有道路模型，再恢復有前版線位支持的街廓邊界，最後修整建物。不以建物裁道路。

既有道路面來自 OSM 模型，寬度為概算，不是新取得的現況實測。本輪未新增衛星或街景核實，不能宣稱已對準實況。

建物與道路交集超過 0.25 平方公尺且不超過建物面積 20% 者，沿既有路面界修整；超過 20% 的衝突不硬裁，橙 L 圈標示。20% 是保守編圖門檻，不是法規或測量標準。內院保留。透明度 40% 等於不透明度 60%，填色在所有線條下方。

柱位、分隔島與引道保留前版。本輪沒有調整 Blender、產權線或推定未知巷寬。

{
  "buildings_in_sheets": 2080,
  "trimmed_buildings": 182,
  "large_conflict_reviews": 142,
  "restored_ground_length_m": 1470.9906050429634,
  "remaining_building_road_overlap_m2": 14461.94109370067,
  "fill_transparency": 0.4,
  "road_source": "existing OSM_Major_Roads / OSM_Minor_Roads mesh, approximate widths, NOT verified current survey"
}
