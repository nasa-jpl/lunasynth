#!/bin/bash
#
# Usage: (lunasynth root) bash scripts/gdal_create.sh <input_geo_tiff_file>
#
# This script creates a hillshade, color relief, slope, and a combined hillshade and color relief map from a given input geotiff file.
# The script also creates a histogram of the elevation and slope maps, a render image.
#
# The script uses the following tools:
# - gdaldem: to create hillshade, color relief, and slope maps, from gdal
# - gdal_translate: to compress the tif files and convert them to png, from gdal
# - convert: to resize the png files, from imagemagick
#
# You need the following packages installed:
# - gdal
# - imagemagick
#
# To execute the python scripts, you need to have installed the python packages listed in the pyproject.toml file. 
# Call this file from an environemtn with the required packages installed. For example, with poetry you can use:
# `poetry run bash scripts/gdal_create.sh <input_geo_tiff_file>`, or
# `poetry shell`, then just call `bash scripts/gdal_create.sh <input_geo_tiff_file>`


# It is convenient to use it with xargs to process multiple files in parallel.
# For example, to process all the _surf.tif files in a directory, you can use the following command:
# ls -d "$PWD/../moon_data/pgda/"*_surf_.tif | xargs -I{} -P 4 bash scripts/gdal_create.sh {}
# 
# $PWD is the current directory.
# The -d option tells ls to list directories themselves, not their contents. Using it with $PWD ensures that the full path is listed.
# The | operator pipes the output of the ls command to the xargs command.
# The xargs command reads the input from the pipe and runs the bash script with the input file as an argument.
# The -I{} option tells xargs to replace {} with the input file.
# The -P 4 option tells xargs to use 4 parallel processes.


set -e

input_file=$1

# check if the input file is provided
if [ -z "$input_file" ]; then
  echo "Please provide the input file"
  exit 1
fi

input_file_name_no_extension="${input_file%.*}"

lowres_height=200

echo "Creating histogram elevation"
python src/data_tools/histogram_tif.py $input_file $input_file_name_no_extension"_histogram.png" --label "Elevation"

echo "Creating color relief hillshade"
gdaldem hillshade $1 $input_file_name_no_extension"_hillshade.tif"
gdal_translate -co COMPRESS=DEFLATE $input_file_name_no_extension"_hillshade.tif" $input_file_name_no_extension"_hillshade_compressed.tif"
gdal_translate -of PNG $input_file_name_no_extension"_hillshade_compressed.tif" $input_file_name_no_extension"_hillshade.png"

echo "Creating color relief"
gdaldem color-relief $1 config/lola_colors.txt $input_file_name_no_extension"_color_relief.tif"
gdal_translate -co COMPRESS=DEFLATE $input_file_name_no_extension"_color_relief.tif" $input_file_name_no_extension"_color_relief_compressed.tif"
gdal_translate -of PNG $input_file_name_no_extension"_color_relief_compressed.tif" $input_file_name_no_extension"_color_relief.png"

echo "Create slope map"
gdaldem slope $1 $input_file_name_no_extension"_slope.tif"
gdal_translate -co COMPRESS=DEFLATE $input_file_name_no_extension"_slope.tif" $input_file_name_no_extension"_slope_compressed.tif"
gdal_translate -of PNG $input_file_name_no_extension"_slope_compressed.tif" $input_file_name_no_extension"_slope.png"
convert -brightness-contrast 80x80 $input_file_name_no_extension"_slope.png" $input_file_name_no_extension"_slope_bright.png"
convert -resize "$lowres_height"x  $input_file_name_no_extension"_slope_bright.png"  $input_file_name_no_extension"_slope_bright_lowres.png"

python src/data_tools/histogram_tif.py $input_file_name_no_extension"_slope.tif" $input_file_name_no_extension"_slope_histogram.png" --label "Slope"

python src/data_tools/combine_tifs.py --tif1 $input_file_name_no_extension"_hillshade.tif" --tif2 $input_file_name_no_extension"_color_relief.tif"  --alpha 0.7
gdal_translate -co COMPRESS=DEFLATE $input_file_name_no_extension"_hillshade_blended.tif" $input_file_name_no_extension"_hillshade_color_relief_compressed.tif"
gdal_translate -of PNG $input_file_name_no_extension"_hillshade_color_relief_compressed.tif" $input_file_name_no_extension"_hillshade_color_relief.png"
convert -resize "$lowres_height"x  $input_file_name_no_extension"_hillshade_color_relief.png"  $input_file_name_no_extension"_hillshade_color_relief_lowres.png"

python src/data_tools/combine_tifs.py --tif1 $input_file_name_no_extension"_slope.tif" --tif2 $input_file_name_no_extension"_color_relief.tif"  --alpha 0.7
gdal_translate -co COMPRESS=DEFLATE $input_file_name_no_extension"_slope_blended.tif" $input_file_name_no_extension"_slope_color_relief_compressed.tif"
gdal_translate -of PNG $input_file_name_no_extension"_slope_color_relief_compressed.tif" $input_file_name_no_extension"_slope_color_relief.png"
convert -resize "$lowres_height"x  $input_file_name_no_extension"_slope_color_relief.png"  $input_file_name_no_extension"_slope_color_relief_lowres.png"

echo "Creating render maps"
python src/lunasynth/cli/render_geotiff.py  $input_file --sun-hour $(seq -1.0 .2 1.0) --sun-season -1.0 --overlay
convert -resize "$lowres_height"x  $input_file_name_no_extension"_rendered_sun_hour_0.0_sun_season_-1.0.png"  $input_file_name_no_extension"_rendered_max_elevation_lowres.png"

# delete all the auxiliary files in the directory
rm -f $input_file_name_no_extension*_compressed.tif
rm -f $input_file_name_no_extension*.aux.xml