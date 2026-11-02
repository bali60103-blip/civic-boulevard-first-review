"""OSM tag -> industry sector. Classification is by TAG, never by guessing from
the shop name, so every assignment is reproducible from the raw data."""

SECTORS = [
    ("餐飲",     "Food & drink"),
    ("夜生活",   "Nightlife"),
    ("零售",     "Retail"),
    ("便利超市", "Convenience / supermarket"),
    ("商辦",     "Office"),
    ("旅宿",     "Lodging"),
    ("修配製造", "Repair / trade / making"),
    ("汽機車",   "Motor vehicle"),
    ("金融",     "Finance"),
    ("醫療",     "Health"),
    ("教育",     "Education"),
    ("文化公共", "Culture & civic"),
    ("運動休閒", "Sport & recreation"),
    ("綠地",     "Green space"),
    ("停車",     "Parking"),
]
SECTOR_KEYS = [s for s, _ in SECTORS]

_A = {
 "restaurant":"餐飲","cafe":"餐飲","fast_food":"餐飲","food_court":"餐飲",
 "ice_cream":"餐飲","bubble_tea":"餐飲","canteen":"餐飲",
 "bar":"夜生活","pub":"夜生活","nightclub":"夜生活","biergarten":"夜生活",
 "stripclub":"夜生活","casino":"夜生活","gambling":"夜生活",
 "bank":"金融","atm":"金融","bureau_de_change":"金融",
 "clinic":"醫療","hospital":"醫療","doctors":"醫療","dentist":"醫療",
 "pharmacy":"醫療","veterinary":"醫療","nursing_home":"醫療",
 "school":"教育","kindergarten":"教育","college":"教育","university":"教育",
 "library":"教育","language_school":"教育","driving_school":"教育","music_school":"教育",
 "place_of_worship":"文化公共","community_centre":"文化公共","theatre":"文化公共",
 "arts_centre":"文化公共","cinema":"文化公共","townhall":"文化公共",
 "police":"文化公共","fire_station":"文化公共","post_office":"文化公共",
 "courthouse":"文化公共","social_facility":"文化公共","public_building":"文化公共",
 "marketplace":"零售",
 "parking":"停車","parking_entrance":"停車","parking_space":"停車","fuel":"汽機車",
 "car_wash":"汽機車","car_rental":"汽機車","car_sharing":"汽機車",
 "motorcycle_parking":"停車","bicycle_parking":"停車","charging_station":"汽機車",
}
_S = {
 "convenience":"便利超市","supermarket":"便利超市","department_store":"零售",
 "mall":"零售","wholesale":"零售",
 "bakery":"餐飲","confectionery":"餐飲","deli":"餐飲","butcher":"餐飲",
 "greengrocer":"餐飲","seafood":"餐飲","tea":"餐飲","coffee":"餐飲",
 "alcohol":"夜生活","beverages":"餐飲",
 "car":"汽機車","car_repair":"汽機車","car_parts":"汽機車","motorcycle":"汽機車",
 "motorcycle_repair":"汽機車","tyres":"汽機車","truck":"汽機車",
 "hardware":"修配製造","doityourself":"修配製造","trade":"修配製造",
 "building_materials":"修配製造","paint":"修配製造","electrical":"修配製造",
 "plumbing":"修配製造","tool_hire":"修配製造","machinery":"修配製造",
 "locksmith":"修配製造","metal":"修配製造","glaziery":"修配製造",
 "bicycle":"修配製造","sewing":"修配製造","fabric":"修配製造",
 "bank":"金融","insurance":"金融","money_lender":"金融","pawnbroker":"金融",
 "chemist":"醫療","optician":"醫療","medical_supply":"醫療","herbalist":"醫療",
 "hearing_aids":"醫療",
 "sports":"運動休閒","outdoor":"運動休閒","fishing":"運動休閒",
}
_L = {
 "park":"綠地","garden":"綠地","nature_reserve":"綠地","common":"綠地",
 "pitch":"運動休閒","playground":"運動休閒","sports_centre":"運動休閒",
 "fitness_centre":"運動休閒","fitness_station":"運動休閒","stadium":"運動休閒",
 "swimming_pool":"運動休閒","track":"運動休閒","sports_hall":"運動休閒",
 "dance":"運動休閒","golf_course":"運動休閒","bowling_alley":"運動休閒",
 "adult_gaming_centre":"夜生活","amusement_arcade":"夜生活","hackerspace":"文化公共",
}
_T = {
 "hotel":"旅宿","hostel":"旅宿","guest_house":"旅宿","motel":"旅宿",
 "apartment":"旅宿","love_hotel":"旅宿",
 "museum":"文化公共","gallery":"文化公共","artwork":"文化公共",
 "attraction":"文化公共","information":"文化公共",
}

def classify(t):
    """Return a sector key or None. Order = specificity."""
    if "office" in t and t["office"] not in ("no",):
        return "商辦"
    if "craft" in t:
        return "修配製造"
    if "healthcare" in t:
        return "醫療"
    s = t.get("shop")
    if s:
        return _S.get(s, "零售")
    a = t.get("amenity")
    if a in _A:
        return _A[a]
    l = t.get("leisure")
    if l in _L:
        return _L[l]
    tu = t.get("tourism")
    if tu in _T:
        return _T[tu]
    if t.get("landuse") in ("grass","forest","meadow","village_green","recreation_ground"):
        return "綠地"
    if t.get("landuse") in ("industrial",):
        return "修配製造"
    if t.get("natural") in ("wood","scrub","grassland"):
        return "綠地"
    if a:
        return "文化公共" if a in ("toilets","drinking_water","shelter","bench") else None
    return None
