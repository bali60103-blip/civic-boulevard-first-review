# civic — 市民大道南北分隔假設檢驗

檢驗一件事：**市民大道高架把台北切成南北兩半嗎？**

**結論：成立。** 十項可查證量測、五條平行幹道對照，7 項支持、1 項反證、2 項不採用。
不利於假設的結果一併列在產出頁面上。

## 決定性的判準不是穿越點，是路緣活動

一般街道把商業吸到路緣，市民大道把商業推開。同一套判準算六條路：

| 幹道 | 路緣凹陷深度 | 中線活躍店面密度 |
|---|---|---|
| **市民大道** | **+67%**（凹陷） | **2.73 /ha** |
| 八德路 | −93%（隆起） | 8.52 /ha |
| 忠孝東路 | −107% | 7.33 /ha |
| 南京東路 | −99% | 11.29 /ha |
| 長安東路 | −68% | 10.63 /ha |
| 民生東路 | −19% | 5.27 /ha |

凹陷深度 = 1 −（中線 ±50 m 密度 ÷ 200–400 m 密度）。**只有市民大道是正值，符號相反。**
這個判準不需要定義「什麼算一個穿越點」，所以不受 OSM 標記方式影響。

其他支持項：行人**平均多走 209 m**（對照組 145–173 m），而且多走的公尺數與取樣距離幾乎無關
（±100/150/250 m → 201/208/194 m），這是線狀障礙的指紋；6.53 km 只有 **3 座人行天橋、
0 座地下道**，同段卻有 32 條車行匝道；**72.5% 的軸線同時是里界或區界**；
**69.8% 的軸線下方仍是縱貫線**（分隔早於道路）；貼線 100 m 內北側建物高 1.5 倍，200 m 外反轉。

## 反證與不採用（保留在表上）

- **產業組成的南北差異不算證據。** placebo 檢定：偏移 ±300／±450 m 的假想線（整條都在同一側）
  分歧度 0.145–0.263，真實軸線 0.213 落在區間內。「兩側不一樣」在市中心是常態。
- **斷頭路密度**市民大道 15.2/km，忠孝東路 21.7/km 更高 → 不採用。
- **幾何穿越點計數**反而顯示市民大道更通透，查明是被捷運隧道與人行道碎片污染 → 改用網路繞路係數。

## 跑起來

**完全不需要網路。** 讀本機的 `.osm.pbf`，不打任何 API。

```bash
pip install -r requirements.txt
cd src && sh run_all.sh          # 14 階段，約 4 分鐘
```

輸入檔（路徑在 `src/config.py`）：

| 檔案 | 用途 |
|---|---|
| `~/Downloads/taiwan-260908.osm.pbf` | 路網、POI、建物、行政界線、鐵路 |
| `~/Desktop/site model 市民大道new.blend` | 橋墩、護欄、建物量體、樹木位置 |

`data/blend/` 由 Blender 匯出產生，只有基地模型變更時才需要重跑（在 Blender 裡跑，不是 python3）。
`run_all.sh` 偵測到缺少時會提早報錯並印出指令：

```bash
export BLEND_OUT="$PWD/../data/blend"
/Applications/Blender.app/Contents/MacOS/Blender -b "$HOME/Desktop/site model 市民大道new.blend" \
    --python blender/export_site_model.py
/Applications/Blender.app/Contents/MacOS/Blender -b "$HOME/Desktop/site model 市民大道new.blend" \
    --python blender/export_site_model_part2.py
```

## 產出

- `tools/civic_blvd_severance.html` — 主要成果。24 個可疊圖層 + 真實地理底圖、沿線剖面、
  橫斷面、證據表。單一自帶檔，離線可開。**不在版控裡**（1.83 MB），跑 pipeline 產生。
- `tools/boundary_comparison.html` — 南北分界指數表。六項實測、四項無資料留白且不計入指數。
- `tools/boundary_overlay_map.html` — 拉直後的走廊剖圖（橫軸里程、縱軸南北距離），四層實測。

## 階段

| 腳本 | 做什麼 |
|---|---|
| `extract_osm.py` | 從 .osm.pbf 裁切走廊：37,005 way / 62,732 node / 60,723 面 |
| `build_axis.py` | 由 30 條高架橋面 way 重建 6,533 m 軸線（彎曲率 1.030） |
| `measure_permeability.py` | 幾何穿越點計數（＋五條對照） |
| `measure_detour.py` | **繞路係數**：116,736 節點人行網路圖上的最短路徑 |
| `measure_structure.py` | 斷頭路、行政界線、縱貫線 |
| `measure_industry.py` | 產業組成 ＋ **placebo 對照**（得出反證） |
| `measure_gradient.py` | **路緣活動凹陷**（決定性判準） |
| `register_blend_model.py` | 把基地模型配準到 EPSG:3826 |
| `measure_blend_model.py` | 橋墩／護欄、建物量體、樹冠（判定不可用） |
| `build_verdict.py` | 證據表 |
| `build_bundle.py` / `build_overlay_tool.py` | 打包 ＋ 組出主要成果 |
| `build_boundary_rows.py` / `build_overlay_strip.py` | 餵實測值給另外兩個工具 |

## 已知限制

- **樹冠資料不可用**：基地模型的 10,000 個樹冠是完全一致的佔位幾何（各維度標準差 4e-06）→
  樹冠面積／體積沒有計算，也不報數字。可用的只有樹木位置。
- **建物高度是推算值**：`building:levels` × 3.2 m，42.4% 落在 12.0 m 預設值 →
  高度統計同時報「全部」與「排除預設值」。兩側缺值率相近（北 30.4%、南 29.7%）。
- **連鎖品牌只有 16.2% 覆蓋率**：只能標「已知連鎖門市在哪」，不能算連鎖／獨立比例。
- **1 組取樣點無法計算**（里程 6,100 m）：該處北側 90 m 內沒有已繪製人行網路，標為資料缺口。
- **分界指數不等於因果**：南北數值差得開只證明兩側不一樣（見上面的 placebo）。
- **只涵蓋高架段 6,533 m**（忠孝橋／環河北路 → 基隆路一段）。市民大道全段 13.6 km，
  六～八段無高架，不在假設範圍內。
- 座標：所有量測在 **EPSG:3826**（TWD97 TM2，公尺）進行，儲存與顯示為 EPSG:4326。

## 這條線原本住在哪

原本是 `bali60103-blip/desktop-tutorial` 的 `src/severance/`（commit `db6215e`、`7b90077`、
`8cc1c35`）。2026-09-09 搬到這個獨立 repo。**那邊還留著一份拷貝**，以這裡為準。
