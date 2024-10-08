#!/bin/bash

set -e

# Usage: from root of the repository run ./scripts/setup_blender_addons.sh

#  Check blender is installed
if ! command -v blender &> /dev/null; then
    echo "Blender is not installed or not accessible in the PATH"
    exit 1
fi

# check blender version
blender_version=$(blender -v| grep "Blender" | awk '{print $2}')
blender_version_major_minor=$(echo "$blender_version" | awk -F. '{print $1 "." $2}')

# Paths
DEV_FOLDER="$PWD/src/lunasynth/blender_addons"
BLENDER_CONFIG_ROOT="$HOME/.config/blender/$blender_version_major_minor"
BLENDER_ADDON_FOLDER="$BLENDER_CONFIG_ROOT/scripts/addons"

# make sure the blender config root exits, exit if not
if [ ! -d "$BLENDER_CONFIG_ROOT" ]; then
    echo "Blender config root not found: $BLENDER_CONFIG_ROOT"
    exit 1
fi

# create blender_addons folder if it doesn't exist
if [ ! -d "$BLENDER_ADDON_FOLDER" ]; then
    mkdir -p "$BLENDER_ADDON_FOLDER"
    echo "Created folder: $BLENDER_ADDON_FOLDER"
fi

# Loop through all files and directories in the development folder
for item in "$DEV_FOLDER"/*; do
    item_name=$(basename "$item")
    target="$BLENDER_ADDON_FOLDER/$item_name"
    
    # Create symbolic link
    if [ -e "$target" ]; then
        echo "Skipping existing item: $target"
    else
        ln -s "$item" "$target"
        echo "Linked $item to $target"
    fi
done

echo "Symbolic links created."
