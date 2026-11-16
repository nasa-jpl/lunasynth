#!/bin/bash

set -e # Exit on error

# Run inside the lunasynth virtual environment. Check python pacakge lunasynth is installed
check_lunasynth() {
    if ! python -c "import lunasynth" &> /dev/null; then
        echo "lunasynth is not installed"
        exit 1
    fi
}

check_lunasynth

# Directory where all the outputs are written
OUTPUT_DIR="${OUTPUT_DIR:-tmp/pipelines}"

# Generate rock field
python src/lunasynth/cli/create_rock_field.py \
    --CFA 0.04 \
    --size_x 1000 \
    --size_y 1000 \
    --h_min 0.6 \
    --h_max 10.0 \
    --output "$OUTPUT_DIR/moon_rock_field"

# Load rock field into blender
python src/lunasynth/cli/load_rocks.py \
    --blend-file assets/base_meshes/moon_mesh_LOLA_10km_10mpp.blend \
    --rock-field-file "$OUTPUT_DIR/moon_rock_field.csv" \
    --output-blend-file "$OUTPUT_DIR/moon_mesh_LOLA_10km_10mpp_rocks.blend"

# Render rock field using generated blend file, and render job file
python src/lunasynth/cli/process_sampling_cases.py \
    --blend_file assets/base_meshes/moon_mesh_LOLA_10km_10mpp.blend \
    --config config/render_distributions/hover_render.yaml  \
    --cases 2 \
    --output-dir "$OUTPUT_DIR/hover_render"