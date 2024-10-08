#!/bin/bash

set -e # Exit on error

# Run inside the lunasynth virtual environment. Check python pacakge lunasynth is installed
if ! python -c "import lunasynth" &> /dev/null; then
    echo "lunasynth is not installed"
    exit 1
fi

python src/lunasynth/generate_dummy_traj_landing.py

python src/lunasynth/cli/generate_traj_definition.py \
    --trajectory trajectory.csv \
    --scene config/sun_scene.yaml

python src/lunasynth/cli/process_traj_cases.py \
    assets/base_meshes/moon_mesh_LOLA_10km_10mpp.blend \
    --config trajectory_scene.json --dry-run \
    --output-dir testing_viz

python src/lunasynth/cli/visualize_cases_blender.py \
    --blend_file  assets/base_meshes/moon_mesh_LOLA_10km_10mpp.blend \
    --config testing_viz/params.json

# blender assets/base_meshes/moon_mesh_LOLA_10km_10mpp_cases_testing_viz/params.json.blend