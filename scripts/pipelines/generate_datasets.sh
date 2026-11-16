#!/bin/bash

# make sure base.meshes is set to the correct path

# Directory where the dataset is written
OUTPUT_DIR="${OUTPUT_DIR:-tmp/datasets}"

python src/lunasynth/cli/generate_enhanced_moon_terrain_dataset.py \
    --dataset-config config/datasets/ortho_minimal.yaml \
    --set base_mesh.meshes=["assets/base_meshes/NPB_final_adj_5mpp_surf_piece_1km_2_12.tif"] \
            output.save_blender_file=true \
            output.output_root="$OUTPUT_DIR" \
            rendering.resolution_x=100 \
            rendering.resolution_y=100 \
            rendering.sampling_render=128