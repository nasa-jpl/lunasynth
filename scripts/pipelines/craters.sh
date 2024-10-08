#!/bin/bash

set -e # Exit on error

# Run inside the lunasynth virtual environment. Check python pacakge lunasynth is installed
if ! python -c "import lunasynth" &> /dev/null; then
    echo "lunasynth is not installed"
    exit 1
fi

# Generate crater field
python src/lunasynth/cli/create_crater_field.py \
    --CFA 0.6 \
    --size_x 40 \
    --size_y 40 \
    --h_min 2.0 \
    --h_max 20.0 \
    --output moon_crater_field.csv

# Load crater field into blender using a blend file
python src/lunasynth/cli/add_craters_mesh.py \
    --mesh-file assets/base_meshes/inclined_200m_100k.blend \
    --crater-field-file moon_crater_field.csv \
    --output-blend-file moon_craters_mesh.blend

# Load crater field into blender using a tif file
python src/lunasynth/cli/add_craters_mesh.py \
    --mesh-file assets/base_meshes/NPB_final_adj_5mpp_surf_piece_1km_2_12.tif \
    --crater-field-file moon_crater_field.csv \
    --output-blend-file moon_craters_tif.blend