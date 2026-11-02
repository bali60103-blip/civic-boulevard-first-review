# 全段分隔島概略修正版

適用：現有 A01-A10，A1 / 1:1000，模型公尺 1:1，EPSG:3826。
1:1000 概略功能平面；實體類別依正射與街景，尺寸／位置為判讀推定，不是測量或真實 50 cm 剖切。不得把推定補繪稱為實測確認。

本版是修改後可編輯的島界線圖，不是把所有舊線換成待核顏色。黑線保留整理後的概略島界；藍線表示已補繪／改寬的推定幾何。兩者均非實測。
橋下位置及尺寸仍有推定，不能把街景支持某類實體存在解讀為每段輪廓均已定位確認。建國引道北側缺完整地面證據，未採用 N16-N18 對稱鏡射候選。
引道、沿路人行道重新分層；原柱位不在本次修正範圍，輸出暫隱藏，沒有以島界反推新柱位。原圖與前版均保留。

## 幾何處置

{
  "legacy_dispositions": {
    "REMOVE_AND_LOCAL_GAP": 7,
    "RETAIN_GENERALIZED_OUTLINE": 47,
    "REDRAW_WIDTH_ALIGNMENT": 11,
    "OUTSIDE_PREVIOUS_DRAWN_CORRIDOR": 8,
    "REMOVE_FALSE_ISLAND": 8,
    "RECLASSIFY": 4,
    "OUTSIDE": 7,
    "GAP": 10,
    "JOIN": 3
  },
  "legacy_total": 105,
  "new_inferred_components": 21,
  "local_gap_markers": 12,
  "same_segment_duplicates": 0,
  "median_geometry_valid": true,
  "survey_verified": false,
  "fresh_streetview_targets": 18,
  "median_boundary_length_m": 19618.5,
  "dxf_audit_errors": 0
}

原封閉候選中的非島項已移除。105 項包含原本不在實際繪製走廊的背景候選，這些沒有擴張加入。藍線中的寬度為人工判讀估值，不是從透視照片求得的量測結果。
同一實體採聯集外邊界，刪除相同座標重線，背景近重線以 0.25m 避讓；不代表所有不同位置的錯線都已消除。

## 留白局部（Q 圈只標示位置，不代表島界）

- Q01（M001）：西端路口矩形跨道路；未能定位實體島，刪除原封閉輪廓，只留疑義位置
- Q02（M011）：重慶南側施工區配置變動，不能沿舊長條島補實線
- Q03（M017）：承德南端公車導流與窄實體分隔交替，原大輪廓不能整體套用
- Q04（M018）：承德窄帶端部／導流區邊界不明，只留局部定位標記
- Q05（M041）：工區旁路口角島，街景受圍籬遮擋；不保留不明封閉島
- Q06（M084）：街景落在高架橋面，不能用橋面推認橋下島界
- Q07（M085）：東端高架交會處地面島端受遮蔽；刪除不明封閉輪廓
- Q08（D006 / D007）：林森北側線極窄且來源折返，未能分清標線／路緣，不補封閉島
- Q09（D008 / D009）：金山北側候選圈入車道；地面實體外緣不足，不直接封成島
- Q10（D012 / D013 / D014）：延吉路高架引道下候選混合島端／停車空間，僅局部保留疑義
- Q11（D018 / D019 / D020）：東端地面／高架層級混雜，不以橋面照片補島
- Q12（）：建國引道北側缺乏完整地面外緣證據；未採用對稱鏡射補繪，保留局部留白

## 逐項修改

| ID | 動作 | 說明 |
|---|---|---|
| M001 | REMOVE_AND_LOCAL_GAP | 西端路口矩形跨道路；未能定位實體島，刪除原封閉輪廓，只留疑義位置 |
| M002 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M003 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M004 | REDRAW_WIDTH_ALIGNMENT | 忠孝西路街景為低矮分隔帶；草稿偏北，向道路內側調整，寬度按比例推定 |
| M005 | OUTSIDE_PREVIOUS_DRAWN_CORRIDOR | 原盤點圖框內，但不在既有實際繪製島線中；不因此擴大出圖範圍 |
| M006 | OUTSIDE_PREVIOUS_DRAWN_CORRIDOR | 原盤點圖框內，但不在既有實際繪製島線中；不因此擴大出圖範圍 |
| M007 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M008 | REDRAW_WIDTH_ALIGNMENT | 同一路段公車分隔帶沿彎道續接；非北側街廓外緣，採概略帶寬 |
| M009 | OUTSIDE_PREVIOUS_DRAWN_CORRIDOR | 原盤點圖框內，但不在既有實際繪製島線中；不因此擴大出圖範圍 |
| M010 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M011 | REMOVE_AND_LOCAL_GAP | 重慶南側施工區配置變動，不能沿舊長條島補實線 |
| M012 | REDRAW_WIDTH_ALIGNMENT | 重慶北路街景中央植栽／設備島；縮減原過寬草稿，寬度推定 |
| M013 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M014 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M015 | REDRAW_WIDTH_ALIGNMENT | 重慶北路同向中央帶；依正射保留路口缺口，寬度推定 |
| M016 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M017 | REMOVE_AND_LOCAL_GAP | 承德南端公車導流與窄實體分隔交替，原大輪廓不能整體套用 |
| M018 | REMOVE_AND_LOCAL_GAP | 承德窄帶端部／導流區邊界不明，只留局部定位標記 |
| M019 | REMOVE_FALSE_ISLAND | 建築街廓，不是分隔島 |
| M020 | OUTSIDE_PREVIOUS_DRAWN_CORRIDOR | 原盤點圖框內，但不在既有實際繪製島線中；不因此擴大出圖範圍 |
| M021 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M022 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M023 | OUTSIDE_PREVIOUS_DRAWN_CORRIDOR | 原盤點圖框內，但不在既有實際繪製島線中；不因此擴大出圖範圍 |
| M024 | OUTSIDE_PREVIOUS_DRAWN_CORRIDOR | 原盤點圖框內，但不在既有實際繪製島線中；不因此擴大出圖範圍 |
| M025 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M026 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M027 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M028 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M029 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M030 | REDRAW_WIDTH_ALIGNMENT | 中山北路街景有樹木與灌木實體分隔，補回原窄縫缺失的帶寬 |
| M031 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M032 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M033 | REMOVE_FALSE_ISLAND | 街景為平面導流標線 |
| M034 | REMOVE_FALSE_ISLAND | 街景為平面導流標線 |
| M035 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M036 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M037 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M038 | REMOVE_FALSE_ISLAND | 正射輪廓跨越斑馬線／交會車道，不採封閉島形 |
| M039 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M040 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M041 | REMOVE_AND_LOCAL_GAP | 工區旁路口角島，街景受圍籬遮擋；不保留不明封閉島 |
| M042 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M043 | REMOVE_FALSE_ISLAND | 路口中央平面交通空間，不採草稿小三角島 |
| M044 | REMOVE_FALSE_ISLAND | 新生／松江路口街景為車道與斑馬線，不採矩形島 |
| M045 | RECLASSIFY | 街景為停車／地下引道側緣，移出分隔島；不以端蓋封住車行口 |
| M046 | RECLASSIFY | 街景為停車／地下引道側緣，移出分隔島；不以端蓋封住車行口 |
| M047 | REDRAW_WIDTH_ALIGNMENT | 松江街景為低矮混凝土分隔，不畫成寬植栽島 |
| M048 | OUTSIDE_PREVIOUS_DRAWN_CORRIDOR | 原盤點圖框內，但不在既有實際繪製島線中；不因此擴大出圖範圍 |
| M049 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M050 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M051 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M052 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M053 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M054 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M055 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M056 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M057 | REMOVE_FALSE_ISLAND | 建築街廓，不是分隔島 |
| M058 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M059 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M060 | OUTSIDE_PREVIOUS_DRAWN_CORRIDOR | 原盤點圖框內，但不在既有實際繪製島線中；不因此擴大出圖範圍 |
| M061 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M062 | REDRAW_WIDTH_ALIGNMENT | 復興路街景捷運橋墩位於植栽分隔帶，原 0.4m 窄縫改為概略植栽帶 |
| M063 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M064 | REMOVE_FALSE_ISLAND | 建築街廓，不是分隔島 |
| M065 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M066 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M067 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M068 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M069 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M070 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M071 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M072 | RECLASSIFY | 街景為沿路停車場人行外緣，移出分隔島 |
| M073 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M074 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M075 | REDRAW_WIDTH_ALIGNMENT | 光復南路街景窄植栽分隔帶，縮減原不均勻輪廓 |
| M076 | RECLASSIFY | 街景為停車／地下引道側緣，移出分隔島；不以端蓋封住車行口 |
| M077 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M078 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M079 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M080 | REDRAW_WIDTH_ALIGNMENT | 五段街景低矮混凝土分隔，非寬綠島 |
| M081 | REDRAW_WIDTH_ALIGNMENT | 五段東側樹木／灌木分隔帶；統一可辨識外緣，寬度為概略 |
| M082 | RETAIN_GENERALIZED_OUTLINE | 以已檢視正射定位，保留可用既有概略外緣並清理短折線；橋下功能參照既有街景紀錄。未聲稱尺寸或每個端點已測定。 |
| M083 | REDRAW_WIDTH_ALIGNMENT | 正射可见狹長分隔帶，去除尖刺及不均勻細縫，採概略帶寬 |
| M084 | REMOVE_AND_LOCAL_GAP | 街景落在高架橋面，不能用橋面推認橋下島界 |
| M085 | REMOVE_AND_LOCAL_GAP | 東端高架交會處地面島端受遮蔽；刪除不明封閉輪廓 |
| D002 | OUTSIDE | 原實際繪製走廊外，不新增線形 |
| D003 | OUTSIDE | 原實際繪製走廊外，不新增線形 |
| D004 | OUTSIDE | 原實際繪製走廊外，不新增線形 |
| D005 | OUTSIDE | 原實際繪製走廊外，不新增線形 |
| D006 | GAP | 林森北側線極窄且來源折返，未能分清標線／路緣，不補封閉島 |
| D007 | GAP | 林森北側線極窄且來源折返，未能分清標線／路緣，不補封閉島 |
| D008 | GAP | 金山北側候選圈入車道；地面實體外緣不足，不直接封成島 |
| D009 | GAP | 金山北側候選圈入車道；地面實體外緣不足，不直接封成島 |
| D010 | JOIN | 復興南側連續中央分隔帶兩側，合併來源切段並保留裁切端 |
| D011 | JOIN | 復興南側連續中央分隔帶兩側，合併來源切段並保留裁切端 |
| D012 | GAP | 延吉路高架引道下候選混合島端／停車空間，僅局部保留疑義 |
| D013 | GAP | 延吉路高架引道下候選混合島端／停車空間，僅局部保留疑義 |
| D014 | GAP | 延吉路高架引道下候選混合島端／停車空間，僅局部保留疑義 |
| D015 | OUTSIDE | 原實際繪製走廊外，不新增線形 |
| D016 | OUTSIDE | 原實際繪製走廊外，不新增線形 |
| D017 | JOIN | 光復南路中央實體分隔帶；裁切端不是路口島端 |
| D018 | GAP | 東端地面／高架層級混雜，不以橋面照片補島 |
| D019 | GAP | 東端地面／高架層級混雜，不以橋面照片補島 |
| D020 | GAP | 東端地面／高架層級混雜，不以橋面照片補島 |
| D001 | OUTSIDE | 原實際繪製走廊外，不新增線形 |
| N01 | ADD_APPROXIMATE_INTERPRETATION | 西段橋下植栽／設備帶；影像支持功能，連接長度及寬度概略推定 |
| N02 | ADD_APPROXIMATE_INTERPRETATION | 西段橋下長帶，依西段街景紀錄補原圖缺漏；非測量輪廓 |
| N03 | ADD_APPROXIMATE_INTERPRETATION | 太原路西側橋下設備島；保留路口開口 |
| N04 | ADD_APPROXIMATE_INTERPRETATION | 太原至承德橋下設備帶；保留路口開口 |
| N05 | ADD_APPROXIMATE_INTERPRETATION | 承德東側鋪面／設備島；thep 街景支持迴轉口，於口前收尾 |
| N06 | ADD_APPROXIMATE_INTERPRETATION | 公園中山停車場外側島界；內部車道／坡道不作島內填色 |
| N07 | ADD_APPROXIMATE_INTERPRETATION | 天津至林森停車場引道外圍狹長島，保持兩端開口 |
| N08 | ADD_APPROXIMATE_INTERPRETATION | 林森東側橋下植栽帶；端部留迴轉缺口 |
| N09 | ADD_APPROXIMATE_INTERPRETATION | 新生引道西段窄植栽／側緣；不是高架橋面護欄 |
| N10 | ADD_APPROXIMATE_INTERPRETATION | 新生引道南側可見長條植栽邊界的概略補繪；端部與中間通行口仍需局部註記 |
| N11 | ADD_APPROXIMATE_INTERPRETATION | 新生引道另一側窄帶，按街景雙帶形態推定；不拿整座高架投影當島 |
| N12 | ADD_APPROXIMATE_INTERPRETATION | 建國東側石牆／植栽外緣，與北側既有窄帶分開 |
| N13 | ADD_APPROXIMATE_INTERPRETATION | 建國引道南側窄帶；避開出入口 |
| N14 | ADD_APPROXIMATE_INTERPRETATION | 建國引道南側植栽邊，保留出入口及天橋鄰接缺口 |
| N15 | ADD_APPROXIMATE_INTERPRETATION | 建國至復興南側橋下窄植栽帶 |
| N19 | ADD_APPROXIMATE_INTERPRETATION | 復興東側服務設施／鋪面島，依街景保留整體外緣 |
| N20 | ADD_APPROXIMATE_INTERPRETATION | 復興至敦化橋下鋪面島；路口不跨接 |
| N21 | ADD_APPROXIMATE_INTERPRETATION | 敦化東側停車引道外側島界，內部坡道不填成實心島 |
| N22 | ADD_APPROXIMATE_INTERPRETATION | 延吉至光復側帶；中間車道保持開放，非大面積封閉島 |
| N23 | ADD_APPROXIMATE_INTERPRETATION | 延吉至光復另一侧窄帶；依雙設備帶街景概略定位 |
| N24 | ADD_APPROXIMATE_INTERPRETATION | 五段東側平面道路樹木分隔，補原圖兩段之間缺漏 |

## 證據

正射：臺北市都市發展局 Ortho_2025；全段 A01-A10 均已目視對照。
橋下既有紀錄：reconstruction/reports/underbridge_0922/full_corridor_observations.json、west_streetview_notes.json；這些是部分地面視角，不是完整測量覆蓋。

本次重新開啟的街景：
- M022 / 2025-05: [raised curb, U-turn opening](https://www.google.com/maps/@25.048353,121.5183957,3a,90y,90t/data=!3m4!1e1!3m2!1sthep3S5iPBSW9exGL5CO_g!2e0)
- M030 / 2025-05: [planted median with trees](https://www.google.com/maps/@25.0491871,121.5211501,3a,90y,90t/data=!3m4!1e1!3m2!1s6TPB4d-ONt_2PfAPR6wSmQ!2e0)
- M049 M050 / 2025-04: [separate planted strips, rounded nose, open lane between](https://www.google.com/maps/@25.0452729,121.5330776,3a,90y,90t/data=!3m4!1e1!3m2!1smg8uGWmROsxmOz9X-JTgZQ!2e0)
- M062 / 2025-05: [metro pier in planted median](https://www.google.com/maps/@25.0455432,121.5438074,3a,90y,90t/data=!3m4!1e1!3m2!1sFiAuH2_WYJteXysPIxLFCg!2e0)
- M080 / 2025-01: [low narrow concrete divider](https://www.google.com/maps/@25.0463656,121.5605868,3a,90y,90t/data=!3m4!1e1!3m2!1sqPXPdnQ2g8461_pjGwlepg!2e0)
- M071 / 2025-02: [large landscaped traffic island and pavement around edge](https://www.google.com/maps/@25.0440325,121.5535411,3a,90y,90t/data=!3m4!1e1!3m2!1suJj_8PV86O1kGT1blAVpkA!2e0)
- M072 / 2025-04: [parking frontage pedestrian edge, not a central median](https://www.google.com/maps/@25.0437291,121.5541954,3a,90y,90t/data=!3m4!1e1!3m2!1sI8oXVtJrJ8P-mK0ow4CbwA!2e0)
- M084 M085 / 2025-01: [elevated deck only; rejected as ground evidence](https://www.google.com/maps/@25.0485162,121.5688957,3a,90y,90t/data=!3m4!1e1!3m2!1stB8auJOoD5arQR6wRE9haw!2e0)
- M003 / 2025-02: [raised landscape and retaining edge under bridge](https://www.google.com/maps/@25.0505603,121.5085822,3a,90y,90t/data=!3m4!1e1!3m2!1siiAl2_pq4XeDFWGOMYBNbg!2e0)
- M012 M015 / 2025-02: [planted centre island with equipment](https://www.google.com/maps/@25.0502955,121.5134742,3a,90y,90t/data=!3m4!1e1!3m2!1sbhA5sDHqSscqoe5Coie22g!2e0)
- M017 M018 / 2025-05: [mixed painted bus approach and narrow median; incomplete ends](https://www.google.com/maps/@25.0494378,121.516497,3a,90y,90t/data=!3m4!1e1!3m2!1shgZqh3XedS5W1HTMBkJAQw!2e0)
- M047 / 2025-01: [low concrete divider](https://www.google.com/maps/@25.0465118,121.5330266,3a,90y,90t/data=!3m4!1e1!3m2!1s__x2iyJAomL5KPiB99fjHQ!2e0)
- M004 M008 / 2024-12: [low bus/carriageway divider south of camera](https://www.google.com/maps/@25.0484516,121.5087061,3a,90y,90t/data=!3m4!1e1!3m2!1sozWEGrfjb1BODToiDgmGgQ!2e0)
- M045 M046 / 2025-04: [screened central ramp sidewalls](https://www.google.com/maps/@25.0448703,121.5328168,3a,90y,90t/data=!3m4!1e1!3m2!1sOiC_yGfOaPWQxzc4eLTScA!2e0)
- M075 / 2025-01: [narrow planted divider with lamps](https://www.google.com/maps/@25.0465812,121.5577278,3a,90y,90t/data=!3m4!1e1!3m2!1sJLSKV7V6G0SDUF4-UB-kIQ!2e0)
- M043 M044 / 2025-04: [open junction and zebra crossing](https://www.google.com/maps/@25.0456322,121.5327017,3a,90y,90t/data=!3m4!1e1!3m2!1s4DhvHcVjSgT923UaLVR2mA!2e0)
- M051 / 2025-05: [grass island nose separate from hatched paint](https://www.google.com/maps/@25.0456084,121.5354275,3a,90y,90t/data=!3m4!1e1!3m2!1sgk47SX_ybpbe8IWJS9dFFg!2e0)
- M076 D017 / 2025-01: [parking ramp wall left and planted concrete median right](https://www.google.com/maps/@25.0441356,121.5578482,3a,90y,90t/data=!3m4!1e1!3m2!1sXqjY_bY4d4cJ_lyikzlrIw!2e0)