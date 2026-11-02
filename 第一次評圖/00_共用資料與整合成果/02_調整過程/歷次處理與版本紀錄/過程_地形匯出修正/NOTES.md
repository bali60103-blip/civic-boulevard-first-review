# 使用者 DXF 局部整合版

D31E15 為中央藝文公園區段，9BAE16 為建國啤酒廠區段；配準後只更新 A03-A06 相交區域。A01、A02、A07-A10 幾何保持不變。

採用建物 HATCH 的外框與內院路徑組成外緣，保留 DXF 原形，不再批次正交化；替換來源範圍內舊建物線。兩檔重疊區聯集去重，輸出裁切邊不當外牆。原分隔島與柱位不改。

道路輪廓混合步道、道路軸線加寬與高架等不同用途，不能直接認定為地面路緣。REF_TOPO_ROADS 及 REF_TOPO_GREEN 為關閉且不列印的參考層；不將公園步道併為人行道。陰影、道路中線、等高線、樹木符號、高度／面積文字未混入主圖。

配準以共同建物形狀匹配及保留樣本驗證完成。接近毫米的同源資料吻合不代表測量精度，並未取得地面控制點。原 DXF 表頭經緯度為預設值，未採用。詳細轉換與檢核見 registration.json。

來源授權：兩份附帶 LICENSE.txt 標示建物及道路等來源為 Overture Maps Foundation 2026 / ODbL；Topoexport 為匯出工具，不是地籍測量資料。建物高度預設與屋頂／地面差异仍可能存在。新圖仍為概略平面，非實測 50cm 剖切。

B 編號保留原待核位置；覆蓋區雖換成新來源輪廓，不代表疑義已經街景核實。Q 編號與前版分隔島留白相同。

{
  "affected_sheets": [
    3,
    4,
    5,
    6
  ],
  "unchanged_sheets": [
    1,
    2,
    7,
    8,
    9,
    10
  ],
  "adopted_source_building_hatches": 1208,
  "invalid_source_paths": 0,
  "elevated_source_matches_excluded": 24,
  "same_segment_duplicates": 0,
  "valid_building_union": true,
  "median_unchanged": true,
  "road_contours_adopted_as_curbs": false,
  "source_note": "Topoexport supplied LICENSE.txt: Overture Maps Foundation Buildings/Transportation/Base 2026, ODbL. Not a cadastral or survey product."
}
