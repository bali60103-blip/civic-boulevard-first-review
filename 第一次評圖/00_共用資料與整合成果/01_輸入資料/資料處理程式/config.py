"""Shared configuration for the 市民大道 north/south severance analysis.

Asks whether the elevated expressway **severs** the city north from south,
judged against five parallel arterials run through identical code.

SCOPE. Severance is a property of the elevated structure, not of any one
section, so this pipeline covers the whole
6,533 m elevated deck, 忠孝橋/環河北路 to 基隆路一段 (NOT to 光復南路,
which sits at chainage 5,188 m, 1.3 km short of the east end). 市民大道 as a street runs 13.6 km,
but 六～八段 (toward 南港) has no elevated deck and is therefore outside the
barrier hypothesis.

NO NETWORK ACCESS IS REQUIRED. CLAUDE.md records that data.taipei,
overpass-api.de and nominatim are all blocked by egress policy. Every input
here is a local file, so the whole pipeline runs offline.

Paths are relative to this directory: run scripts with `cd src`.
"""

import os

# --- inputs (local files; none of these are fetched over the network) -------
# Whole-Taiwan OSM extract. Read with pyosmium and clipped to the corridor
# bbox in extract_osm.py.
OSM_PBF = os.path.expanduser("~/Downloads/taiwan-260908.osm.pbf")

# The Blender site model the user builds by hand. register_blend_model.py
# solves its georeference; it is NOT assumed.
BLEND_MODEL = os.path.expanduser("~/Desktop/site model 市民大道new.blend")

# --- clip window for the OSM extract ---------------------------------------
# Generous: 市民大道 runs ~121.500–121.625; ±0.020 deg of latitude is ~2.2 km,
# comfortably past the widest analysis band (600 m) and the control corridors.
BBOX = (121.480, 25.020, 121.640, 25.075)   # W, S, E, N

# --- coordinate systems ----------------------------------------------------
# Every distance, buffer and nearest-neighbour computation happens in metres.
CRS_COMPUTE = "EPSG:3826"   # TWD97 TM2
CRS_DISPLAY = "EPSG:4326"   # WGS84, for storage and display

# --- analysis parameters ---------------------------------------------------
SEG_LEN_M = 200.0     # along-axis analysis segment
PROBE_STEP_M = 100.0  # spacing of detour probe pairs
PROBE_OFFSET_M = 150.0  # perpendicular offset of each probe point
BAND_M = 300.0        # industry-composition band each side of the axis
GRADIENT_RANGE_M = 600.0  # extent of the cross-section density profile
GRADIENT_BIN_M = 25.0

# Parallel E–W arterials used as controls, clipped to the same easting window
# as the axis and run through identical code. Without these, a number like
# "1.7x detour" means nothing.
CONTROL_CORRIDORS = ["八德路", "忠孝東路", "南京東路", "長安東路", "民生東路"]

# --- the design proposal's three 潛力節點 -----------------------------------
# 市民高架都市空間活化論述_1150610.pdf p10 names each zone's extent by cross
# street. Those street names were converted to chainage by intersecting the
# reconstructed axis with the OSM ways of the same name, so these bounds are
# derived, not eyeballed off the drawing:
#   林森北路 2040 m · 新生北路 2740 m · 建國南路 3398 m
#   復興南路 4095 m · 敦化南路 4641 m · 光復南路 5188 m
PDF_ZONES = [
    ("A 街頭競演", "林森北—新生高架", 2040, 2740),
    ("B 藝文通學", "建國高架—復興南北", 3398, 4095),
    ("C 夜間漫步", "復興南北—敦化南北", 4095, 4641),
]

# --- output paths ----------------------------------------------------------
DATA_RAW = "../data/raw"
DATA_PROCESSED = "../data/processed"
DATA_BLEND = "../data/blend"
OUTPUT = "../output"
# The interactive tool ships next to the project's other standalone tools.
OVERLAY_TOOL_PATH = "../tools/civic_blvd_severance.html"
