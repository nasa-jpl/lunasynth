#!/bin/bash

# This script downloads the Lunar Orbiter Laser Altimeter (LOLA) data from the Planetary Geodynamics Laboratory (PGDA) website.

# Usage
# bash download_moon_data.sh <data_dir>
#
# Requirements:
# - curl must be installed and accessible in the PATH, `apt install curl` for Debian systems


# first argument is the data directory
DATA_DIR=$1

# check if the data directory is provided
if [ -z "$DATA_DIR" ]; then
  echo "Please provide the data directory"
  exit 1
fi

# crate the data directory if it does not exist
mkdir -p "$DATA_DIR"

download_file() {
  # Extracting the specific path and filename from the provided URL
  path="$1"
  filename=$(basename "$path")

  # Downloading the file using curl
  curl -o "$DATA_DIR/$filename" "$path" --create-dirs
  # check if the download was successful
  if [ $? -ne 0 ]; then
    echo "Failed to download $filename"
    # delete the file if it was partially downloaded
    rm -f "$DATA_DIR/$filename"
  fi
  echo "Downloaded $path to $DATA_DIR/$filename"
}

# gridded
# download_file "https://pgda.gsfc.nasa.gov/data/LOLA_PA/LDEM128_PA_pixel_202405.tif"

# # South Pole LOLA DEM Mosaic
# download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/87S/ldem_87s_5mpp.tif"

# High-Resolution LOLA Topography for Lunar South Pole Sites
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site01/Site01_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site04/Site04_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site06/Site06_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site07/Site07_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site11/Site11_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site20/Site20_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site20v2/Site20v2_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site23/Site23_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Site42/Site42_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Haworth/Haworth_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Shoemaker/Shoemaker_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/DM1/DM1_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/DM2/DM2_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/SL2/SL2_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/SL3/SL3_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/NPA/NPA_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/NPB/NPB_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/NPC/NPC_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/NPD/NPD_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/LM1/LM1_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/LM2/LM2_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/LM3/LM3_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/LM4/LM4_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/LM5/LM5_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/LM6/LM6_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/LM7/LM7_final_adj_5mpp_surf.tif"
download_file "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/LM8/LM8_final_adj_5mpp_surf.tif"