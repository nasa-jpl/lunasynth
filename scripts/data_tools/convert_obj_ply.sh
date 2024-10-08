#!/bin/bash

# Convert OBJ to PLY using meshlabserver
# Usage: ./convert_obj_ply.sh file1.obj file2.obj ... fileN.obj
# 
# Requirements:
# - meshlabserver (from MeshLab) must be installed and accessible in the PATH


# Check if at least one file is provided
if [ "$#" -lt 1 ]; then
    echo "Usage: $0 file1.obj file2.obj ... fileN.obj"
    exit 1
fi

# Loop through all provided OBJ files
for obj_file in "$@"; do
    # Check if the file exists
    if [ ! -f "$obj_file" ]; then
        echo "File $obj_file does not exist."
        continue
    fi

    # Extract the directory and filename without the extension
    directory=$(dirname "$obj_file")
    filename=$(basename -- "$obj_file")
    filename="${filename%.*}"
    
    # Define the output PLY file path in the same directory as the input OBJ file
    ply_file="$directory/${filename}.ply"
    
    # Convert OBJ to PLY using meshlabserver
    meshlabserver -i "$obj_file" -o "$ply_file"
    
    # Check if the conversion was successful
    if [ $? -eq 0 ]; then
        echo "Successfully converted $obj_file to $ply_file"
    else
        echo "Failed to convert $obj_file"
    fi
done
