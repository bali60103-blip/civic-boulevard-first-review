#!/bin/sh
# Run the whole severance pipeline in dependency order.
# The last two stages feed measured values into the other two standalone tools
# (boundary_comparison.html, boundary_overlay_map.html), so one rerun keeps all
# three tools consistent with the same numbers.
#   cd src && sh run_all.sh
# Every stage is independently re-runnable; each writes JSON to
# ../data/processed/ so a later stage can be verified on its own.
#
# NOT included here: the two Blender export scripts under blender/. Those must
# run inside Blender and only need re-running when the .blend model changes:
#   /Applications/Blender.app/Contents/MacOS/Blender -b "$BLEND_MODEL" \
#       --python blender/export_site_model.py
set -e

# Create the (gitignored) output tree up front. A fresh clone has none of it,
# and it has already been wiped once by a clean that included ignored files.
mkdir -p ../data/raw ../data/processed ../data/blend ../tools ../output

# data/blend/ is NOT produced here — it comes from the two scripts under
# blender/, which must run inside Blender. Fail early with the command to run
# rather than nine stages later with a confusing missing-file error.
if [ ! -f ../data/blend/buildings_parts.npy ]; then
  echo "ERROR: ../data/blend is empty. Run the Blender exports first — see README.md:" >&2
  echo '  export BLEND_OUT="$PWD/../data/blend"' >&2
  echo '  /Applications/Blender.app/Contents/MacOS/Blender -b "$HOME/Desktop/site model 市民大道new.blend" \' >&2
  echo '      --python blender/export_site_model.py' >&2
  echo '  (then again with blender/export_site_model_part2.py)' >&2
  exit 1
fi

for stage in \
  extract_osm \
  build_axis \
  measure_permeability \
  measure_detour \
  measure_structure \
  measure_industry \
  measure_gradient \
  register_blend_model \
  measure_blend_model \
  build_verdict \
  build_bundle \
  build_overlay_tool \
  build_boundary_rows \
  build_overlay_strip
do
  echo "=== $stage ==="
  python3 "$stage.py"
done
