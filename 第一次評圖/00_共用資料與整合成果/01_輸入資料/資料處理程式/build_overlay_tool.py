"""Stage 12 — assemble the single self-contained HTML tool.

Inlines output/bundle.json into the page so the result needs no server, no
network and no build step to open — the same standalone-HTML convention
tools/boundary_comparison.html and tools/boundary_overlay_map.html follow.
"""
import os

from config import OUTPUT, OVERLAY_TOOL_PATH

head = open("viz_head.html", encoding="utf-8").read()
body = open("viz_body.html", encoding="utf-8").read()
app = open("viz_app.js", encoding="utf-8").read()
bundle = open(f"{OUTPUT}/bundle.json", encoding="utf-8").read()

# The bundle rides in a <script type="application/json"> block rather than as a
# JS literal, so no escaping of the geometry integers or the Chinese strings is
# needed. build_bundle.py guarantees the JSON contains no "</script>".
assert "</script>" not in bundle, "bundle contains a script terminator"

page = (
    head + "\n" + body + "\n"
    + '<script type="application/json" id="bundle">' + bundle + "</script>\n"
    + "<script>\n"
    + "window.__BUNDLE__ = JSON.parse(document.getElementById('bundle').textContent);\n"
    + app + "\n</script>\n"
)

with open(OVERLAY_TOOL_PATH, "w", encoding="utf-8") as f:
    f.write(page)
print(f"wrote {OVERLAY_TOOL_PATH}: {os.path.getsize(OVERLAY_TOOL_PATH)/1e6:.2f} MB")
