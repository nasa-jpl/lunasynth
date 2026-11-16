#!/bin/bash

set -e # Exit on error

# Run inside the lunasynth virtual environment. Check python pacakge lunasynth is installed
if ! python -c "import lunasynth" &> /dev/null; then
    echo "lunasynth is not installed"
    exit 1
fi

# Directory where all the outputs are written
OUTPUT_DIR="${OUTPUT_DIR:-tmp/pipelines}"

python src/lunasynth/generate_dummy_traj_landing.py --output-dir "$OUTPUT_DIR"

python src/lunasynth/cli/generate_traj_definition.py \
    --trajectory "$OUTPUT_DIR/trajectory.csv" \
    --scene config/sun_scene.yaml \
    --output "$OUTPUT_DIR/trajectory_scene.json"

python src/lunasynth/cli/process_traj_cases.py \
    assets/base_meshes/moon_mesh_LOLA_10km_10mpp.blend \
    --config "$OUTPUT_DIR/trajectory_scene.json" --dry-run \
    --output-dir "$OUTPUT_DIR/testing_viz"

python src/lunasynth/cli/visualize_cases_blender.py \
    --blend_file  assets/base_meshes/moon_mesh_LOLA_10km_10mpp.blend \
    --config "$OUTPUT_DIR/testing_viz/params.json" \
    --output-blend-file "$OUTPUT_DIR/moon_mesh_LOLA_10km_10mpp_cases.blend"

# blender "$OUTPUT_DIR/moon_mesh_LOLA_10km_10mpp_cases.blend"