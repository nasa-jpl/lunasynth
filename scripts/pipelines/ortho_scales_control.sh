#!/bin/bash

python src/lunasynth/cli/generate_enhanced_moon_terrain_dataset.py \
    --dataset-config config/datasets/ortho_scales.yaml \
    --set \
    name=ortho_scales_control \
    base_mesh.meshes=["assets/base_meshes/NPB_final_adj_5mpp_surf_piece_1km_2_12.tif"] \
    terrain.add_rocks=false \
    terrain.add_craters=false \
    rendering.resolution_x=100 \
    rendering.resolution_y=100 \
    rendering.sampling_render=128
