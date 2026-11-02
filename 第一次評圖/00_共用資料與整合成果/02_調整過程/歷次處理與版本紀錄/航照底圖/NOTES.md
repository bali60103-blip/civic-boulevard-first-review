# 逐張透明度與影像底圖

底圖為已快取的臺北市 Ortho_2025 正射航空影像，非即時衛星影像；確切拍攝日期未確認。原始影像 EPSG:3857，依世界檔逐像素轉換到 EPSG:3826，每张輸出 0.5 m/pixel，並非提升原始解析度。A01-A10 覆蓋率均為 100%。

sheet_parameters.json 的 sheets.A01 至 A10 分別設定 line_transparency、building_transparency、image_fade，範圍 0-90。透明度越高，線／建物越淡；image_fade 越高，影像越接近白色。A00 參數僅供 PDF 總圖使用。

PDF 是這些參數的輸出快照，不是可拖動的透明度介面。修改參數後執行 prepare_ortho_underlay.py，再執行 render_ground_outlines.py --ortho，可重出圖。DWG 中每張配置的線與建物使用視埠圖層透明度覆寫，底圖使用各張 ORTHO_Axx 圖層上的 IMAGE Fade。列印必須開啟列印透明度。

DWG 影像採相對路徑 images/Axx_Ortho2025_TWD97.png。移動檔案時需連同 images 資料夾一起帶走。原幾何、道路閉合狀態與建築輪廓未移動；航照屋頂偏移、樹蔭與高架遮蔽不代表已核實地面輪廓。
