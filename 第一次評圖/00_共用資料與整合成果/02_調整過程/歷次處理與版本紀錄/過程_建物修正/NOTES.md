# 建物主軸直角化概略修正版

範圍 A01-A10；模型公尺 1:1 / EPSG:3826，A1 1:1000。

依各建物自身主軸修正近直角邊，不強迫沿格網水平垂直。明顯斜邊及不規則形體保留。接受條件：主軸一致性 >= 0.75、至少 75% 邊接近主軸 15 度內、頂點位移最多 2m 且另依面積限縮、面積變化 <= 10%、對稱差面積 <= 18%、幾何有效。以上為製圖約束，不是測量精度。

黑粗線為直角化結果，灰粗線為保留輪廓，橙粗線為校正超限而保留待核。藍線仍為前版推定分隔島；Q 為前版分隔島局部留白。建物不是已核實的地面 50cm 外牆，屋頂投影與地面位置差異仍可能存在；不能用於施工。全段分隔島幾何保留不動，柱位未改。

已讀取 Blender 場景 CIVIC_PIER_XY_REVIEW_20260923，核對 BLOCK_*_CORE 與桌面 BlockFacades/buildings_selected.json 的座標及 0.19m 內縮核心差異。採用其 OSM 來源外輪廓，不採推定立面窗模組或內縮核心外緣；依模型基底與高度排除不穿過 0.5m 的建物部分，但高程並未實測。以 registration.json 相似變換轉 EPSG:3826。原歷史近似建物線全部替換，不與新來源重疊保留；來源缺漏不代表實際無建物。

{
  "building_faces": 1251,
  "reference_source_records": 2660,
  "same_source_supplemental_records": 703,
  "floor_excluded_records": 100,
  "preserved_courtyards": 25,
  "actions": {
    "RETAIN_ALREADY_REGULAR": 898,
    "ORTHOGONALIZED": 250,
    "REVIEW_LIMIT": 31,
    "RETAIN_IRREGULAR": 72
  },
  "max_accepted_vertex_shift_m": 1.748,
  "valid_building_union": true,
  "same_segment_duplicates": 0,
  "survey_verified": false,
  "reference_requested": "CIVIC_PIER_XY_REVIEW_20260923",
  "reference_used": true,
  "reference_geometry": "BlockFacades/buildings_selected.json; same source as scene BLOCK_*_CORE; ground-level filter by model metadata",
  "median_geometry_unchanged": true
}

逐棟原始與修正座標、主軸角度、位移與處置見 building_register.json。原檔、Blender 場景與前版均未覆寫。
