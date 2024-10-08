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

# Generate rock field
python src/lunasynth/cli/create_rock_field.py \
    --CFA 0.04 \
    --size_x 1000 \
    --size_y 1000 \
    --h_min 0.6 \
    --h_max 10.0

# Load rock field into blender
python src/lunasynth/cli/load_rocks.py \
    --blend-file assets/base_meshes/moon_mesh_LOLA_10km_10mpp.blend \
    --rock-field-file moon_rock_field.csv

# Render rock field using generated blend file, and render job file
python src/lunasynth/cli/process_sampling_cases.py \
    --blend_file assets/base_meshes/moon_mesh_LOLA_10km_10mpp.blend \
    --config config/render_distributions/hover_render.yaml  \
    --cases 2