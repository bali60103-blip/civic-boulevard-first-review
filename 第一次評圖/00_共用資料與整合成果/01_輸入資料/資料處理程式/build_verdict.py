"""Stage 10 — assemble the evidence table for 「市民大道造成南北分隔」.

Each line states the measurement, the value, the comparison it is judged
against, and a verdict: SUPPORTS / NEUTRAL / CONTRADICTS. Lines that came out
against the hypothesis stay in the table.
"""
import json
import numpy as np

a1 = json.load(open("../data/processed/a1_crossings.json"))
b  = json.load(open("../data/processed/b_detour.json"))
c  = json.load(open("../data/processed/c_structure.json"))
f  = json.load(open("../data/processed/f_industry.json"))
g  = json.load(open("../data/processed/g_gradient.json"))
h  = json.load(open("../data/processed/h_blend.json"))

CTRL = ["八德路","忠孝東路","南京東路","長安東路","民生東路"]
ev = []

# --- E1 density trough ------------------------------------------------------
ct = [g[k]["active"]["trough_depth"] for k in CTRL if k in g]
civ = g["市民大道"]["active"]["trough_depth"]
ev.append({
 "id":"E1","title":"街道邊緣的商業活動：市民大道是凹陷，其他幹道是隆起",
 "metric":"active-frontage POI density trough depth at the centreline "
          "(1 - density within ±50 m / density at 200-400 m)",
 "value":f"市民大道 +{civ*100:.1f}%",
 "compare":"控制組 " + ", ".join(f"{k} {g[k]['active']['trough_depth']*100:+.0f}%" for k in CTRL if k in g),
 "detail":f"市民大道中線 ±50 m 的活躍店面密度 {g['市民大道']['active']['inner_density']:.2f}/ha，"
          f"控制組 {min(g[k]['active']['inner_density'] for k in CTRL if k in g):.2f}–"
          f"{max(g[k]['active']['inner_density'] for k in CTRL if k in g):.2f}/ha",
 "verdict":"SUPPORTS","weight":"決定性",
 "why":"符號相反。一般街道把商業吸到路緣（隆起），市民大道把商業推開（凹陷）。"
       "這個判準不需要定義「穿越點」，因此不受 OSM 標記方式影響。",
})

# --- E2 detour --------------------------------------------------------------
cd = {k["label"]:k for k in b["controls"]}
ev.append({
 "id":"E2","title":"行人繞路成本：跨越市民大道平均多走 209 公尺",
 "metric":"pedestrian network detour: route between points 150 m north and "
          "150 m south, every 100 m of axis (straight need = 300 m)",
 "value":f"平均 {b['civic']['detour_mean']:.2f}x（多走 {b['civic']['extra_walk_mean_m']:.0f} m），"
         f"p90 {b['civic']['detour_p90']:.2f}x，最差 {b['civic']['detour_max']:.2f}x",
 "compare":"控制組 " + ", ".join(f"{k} {cd[k]['detour_mean']:.2f}x/{cd[k]['extra_walk_mean_m']:.0f}m" for k in CTRL if k in cd),
 "detail":f"{b['civic']['share_over_2x']*100:.0f}% 的取樣點繞路超過 2 倍（控制組 "
          f"{min(cd[k]['share_over_2x'] for k in CTRL if k in cd)*100:.0f}–"
          f"{max(cd[k]['share_over_2x'] for k in CTRL if k in cd)*100:.0f}%）。"
          f"多走的距離幾乎與取樣距離無關（offset 100/150/250 m → "
          + "/".join(str(int(b['civic_offsets'][str(o)]['extra_walk_mean_m'] if str(o) in b['civic_offsets'] else b['civic_offsets'][o]['extra_walk_mean_m'])) for o in (100,150,250))
          + " m），這是線狀障礙的特徵：不論從哪裡出發都要付固定的「找閘口」代價。",
 "verdict":"SUPPORTS","weight":"強",
 "why":"直接以公尺計價，且在五條平行幹道中最差。",
})

# --- E3 grade-separated crossing supply -------------------------------------
ob = h["obstruction"]
ev.append({
 "id":"E3","title":"立體穿越供給：6.53 公里只有 3 座人行天橋、0 座地下道",
 "metric":"footbridges / pedestrian underpasses within 150 m of the axis "
          "(from the Blender site model's real object inventory)",
 "value":f"{ob['footbridges_near_axis']} 座天橋 + {ob['underpasses_near_axis']} 座地下道 "
         f"→ 平均每 {6532.5/max(ob['footbridges_near_axis']+ob['underpasses_near_axis'],1)/1000:.2f} 公里一處",
 "compare":f"模型全域共有 {ob['infra']['footbridges']['total']} 座天橋、"
           f"{ob['infra']['underpasses']['total']} 座地下道，但幾乎都不在市民大道沿線",
 "detail":f"同一段軸線上卻有 {ob['infra']['ramps']['within_150m_of_axis']} 條車行匝道。"
          f"立體穿越供給是給車的，不是給人的。",
 "verdict":"SUPPORTS","weight":"強",
 "why":"平面穿越受阻時，立體穿越是唯一替代；供給密度低到每 2.2 公里一處。",
})

# --- E4 administrative boundary ---------------------------------------------
ev.append({
 "id":"E4","title":"制度上的分隔：72.5% 的軸線同時是里界或區界",
 "metric":"share of the axis within 35 m of an OSM administrative boundary "
          "line (admin_level 7 = 區, 9 = 里)",
 "value":f"{c['admin_share_pct']}% of 6,533 m",
 "compare":f"區界（admin_level=7）{c['admin_boundary_len_by_level'].get('7',0):,.0f} m、"
           f"里界（admin_level=9）{c['admin_boundary_len_by_level'].get('9',0):,.0f} m 落在 35 m 走廊內",
 "detail":"具名的界線包括「大同區/中正區」（143 m）與「中山/大安區界」（788 m），"
          "以及多條里界。南北兩側在行政上屬於不同單位，資源、里長、"
          "學區與統計邊界都在此斷開。",
 "verdict":"SUPPORTS","weight":"中（制度性佐證）",
 "why":"若市府自己的行政幾何都以此為界，分隔就不只是物理感受。",
})

# --- E5 historical ----------------------------------------------------------
ev.append({
 "id":"E5","title":"分隔早於道路：69.8% 的軸線下方仍是縱貫線鐵路",
 "metric":"share of the axis within 120 m of the (undergrounded) 縱貫線 railway",
 "value":f"{c['rail_axis_share_pct']}%（{c['rail_near_axis_m'].get('rail|縱貫線',0):,.0f} m 的縱貫線路段在 120 m 內）",
 "compare":"—",
 "detail":"市民大道是鐵路地下化後蓋在原鐵道廊帶上的。南北分隔是這條廊帶"
          "自 1891 年就在的屬性，道路繼承並強化了它，而不是憑空創造。"
          "這解釋了為什麼分隔如此頑固：街廓紋理是照鐵路兩側各自長出來的。",
 "verdict":"SUPPORTS","weight":"中（成因解釋）",
 "why":"把「為什麼會這樣」補上，也說明為何單靠拆除高架不會自動縫合。",
})

# --- E6 massing asymmetry ---------------------------------------------------
bb = h["massing"]["by_band_real_height"]
b0 = bb[0]; b1 = bb[1]; b3 = bb[-1]
ev.append({
 "id":"E6","title":"貼線的兩側量體完全不同：北側高、南側低，200 m 外反轉",
 "metric":"mean building height by side and distance band, real-height subset "
          "(19,592 separated masses from the site model)",
 "value":f"0–50 m：北 {b0['north']:.1f} m vs 南 {b0['south']:.1f} m（N/S {b0['ratio']:.2f}）；"
         f"50–100 m：{b1['ratio']:.2f}",
 "compare":f"200–400 m 反轉為 N/S {b3['ratio']:.2f}（北 {b3['north']:.1f} m vs 南 {b3['south']:.1f} m）",
 "detail":f"缺值率兩側幾乎相同（北 30.4%、南 29.7%），所以這不是資料涵蓋造成的假訊號。"
          f"貼著市民大道的 100 公尺內，北側是高樓背面、南側是低矮街廓；"
          f"到了 200 公尺外關係反轉，說明「差異」是走廊自己的性質，不是行政區的整體差異。",
 "verdict":"SUPPORTS","weight":"中",
 "why":"兩側的建築回應方式不同，且差異只出現在貼線帶，正是障礙效應的空間指紋。",
})

# --- E7 obstruction under the deck ------------------------------------------
ev.append({
 "id":"E7","title":"橋下被結構物填滿：241 支橋柱、13.3 ha 連續分隔島",
 "metric":"pier columns within 30 m of the centreline; kerbed median area; "
          "deck area (site model)",
 "value":f"{ob['n_columns_under_deck']} 支橋柱佔去 {ob['ground_taken_under_deck_m2']:,.0f} m² 地面；"
         f"分隔島 {ob['median_area_m2']/1e4:.1f} ha；橋面覆蓋 {ob['deck_area_m2']/1e4:.1f} ha",
 "compare":f"橋墩排（bent）中位間距 {ob['bent_spacing_median_m']:.1f} m，最密 {ob['bent_spacing_min_m']:.1f} m",
 "detail":f"橋面淨空僅 {ob['deck_soffit_z_m']:.1f} m，護欄 {ob['guardrail_height_m']:.1f} m 高、"
          f"總長 {ob['guardrail_run_m']/1000:.1f} km（沿 4 條橋緣連續）。"
          f"平面層的 13.3 ha 分隔島本身就是一道連續的實體牆，"
          f"這正是 PDF 所述「橋下設施將南北都市空間分割」的量化版本。",
 "verdict":"SUPPORTS","weight":"中",
 "why":"把設計論述裡的定性描述換成可查證的數量與尺寸。",
})

# --- E8 industry mix: NEGATIVE ----------------------------------------------
pl = f["placebos"]
mx = max(p["js"] for p in pl)
ev.append({
 "id":"E8","title":"產業「組成」的南北差異，並未超過任意平行線的差異",
 "metric":"Jensen-Shannon distance between north and south industry-sector "
          "shares, versus placebo lines offset ±300/±450 m",
 "value":f"市民大道 JS = {f['overall_js']:.4f}（chi² p = {f['chi2_p']:.1e}）",
 "compare":"placebo " + ", ".join(f"{p['offset_m']:+.0f} m JS={p['js']:.4f}" for p in pl),
 "detail":f"軸線的 JS（{f['overall_js']:.3f}）落在 placebo 區間 "
          f"{min(p['js'] for p in pl):.3f}–{mx:.3f} 之中，+300 m 的假想線甚至更分歧。"
          f"所以「南北產業結構不同」雖然統計上顯著，卻與市中心任何兩條相鄰街帶的差異"
          f"無法區分——不能拿來當市民大道造成分隔的證據。",
 "verdict":"CONTRADICTS","weight":"—（反證，保留）",
 "why":"沒有 placebo 對照的話，這條會被誤讀為強證據。列出來是為了不讓結論被高估。",
})

# --- E9 severed streets: NEUTRAL --------------------------------------------
sc = {x["label"]:x for x in c["severed_controls"]}
ev.append({
 "id":"E9","title":"斷頭路密度：市民大道並非最高",
 "metric":"N-S streets whose end dies within 60 m of the axis without crossing",
 "value":f"市民大道 {c['severed_civic']['per_km']}/km",
 "compare":", ".join(f"{k} {sc[k]['per_km']}/km" for k in CTRL if k in sc),
 "detail":"忠孝東路（21.7/km）明顯高於市民大道（15.2/km）。這個指標混入了大量"
          "服務性巷弄與停車出入口，對「行人是否能穿越」的解釋力低，因此不列為證據。",
 "verdict":"NEUTRAL","weight":"—（不採用）",
 "why":"指標本身雜訊太大；誠實記錄它沒有支持假設。",
})

# --- E10 geometric crossing count: NEUTRAL ----------------------------------
ev.append({
 "id":"E10","title":"幾何穿越點計數：反而比控制組多，但這個計數不可信",
 "metric":"ways geometrically crossing the axis, clustered into locations",
 "value":f"市民大道 {a1['civic']['walkable_per_km']}/km",
 "compare":", ".join(f"{x['label']} {x['walkable_per_km']}/km" for x in a1["controls"]),
 "detail":"檢查明細後發現計數被污染：捷運與縱貫線隧道（載的是列車不是人）、"
          "以及 28 處無名的人行道碎片被平滑後的中線切到，都被算成「穿越點」。"
          "這正是改用網路繞路係數（E2）的原因。",
 "verdict":"NEUTRAL","weight":"—（不採用）",
 "why":"保留下來說明方法為何要換，避免別人重蹈。",
})

sup = [e for e in ev if e["verdict"]=="SUPPORTS"]
print("="*78)
print("南北分隔假設的證據表")
print("="*78)
for e in ev:
    mark = {"SUPPORTS":"✓ 支持","CONTRADICTS":"✗ 反證","NEUTRAL":"· 中性"}[e["verdict"]]
    print(f"\n[{e['id']}] {mark}   權重 {e['weight']}")
    print(f"  {e['title']}")
    print(f"  值    : {e['value']}")
    print(f"  對照  : {e['compare']}")
print(f"\n{'='*78}\n支持 {len(sup)} 項 / 反證 1 項 / 中性 2 項")
json.dump({"evidence": ev,
           "n_supports": len(sup),
           "n_contradicts": sum(1 for e in ev if e["verdict"]=="CONTRADICTS"),
           "n_neutral": sum(1 for e in ev if e["verdict"]=="NEUTRAL")},
          open("../data/processed/verdict.json","w"), ensure_ascii=False, indent=1)
print("wrote data/processed/verdict.json")
