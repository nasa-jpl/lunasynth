import os
import numpy as np
from PIL import Image
import rasterio
from rasterio.transform import from_origin
from osgeo import gdal

from scipy import ndimage

# Configuration
input_dir = "/home/anjashep-frog-lab/Research/LunarHD/lunasynth/generated_data/datasets/ortho_nominal_2025-09-01_13-54-26/mesh_NPB_final_adj_5mpp_surf_piece_0_0"
output_dir = "/home/anjashep-frog-lab/Research/LunarHD/lunasynth/generated_data/datasets/ortho_nominal_2025-09-01_13-54-26_out"
shadow_threshold = 0.1  # hillshade < threshold = shadow


def remove_small_regions(mask, min_size=10):
    """
    Remove connected regions in a binary mask smaller than min_size pixels.
    """
    labeled, num_features = ndimage.label(mask)
    sizes = ndimage.sum(mask, labeled, range(1, num_features + 1))
    
    cleaned_mask = np.zeros_like(mask, dtype=np.uint8)
    for i, size in enumerate(sizes):
        if size >= min_size:
            cleaned_mask[labeled == i + 1] = 1
    return cleaned_mask

def compute_hillshade_gdal(dem_array, azimuth=315, altitude=45):
    rows, cols = dem_array.shape
    driver = gdal.GetDriverByName('MEM')
    ds = driver.Create('', cols, rows, 1, gdal.GDT_Float32)
    ds.GetRasterBand(1).WriteArray(dem_array.astype(np.float32))

    hs_ds = gdal.DEMProcessing('', ds, 'hillshade',
                               computeEdges=True,
                               azimuth=azimuth,
                               altitude=altitude,
                               scale=1.0,
                               format='MEM')
    hillshade = hs_ds.GetRasterBand(1).ReadAsArray()
    hillshade = np.clip(hillshade.astype(np.float32) / 255.0, 0, 1)
    return hillshade

def process_depth_file(depth_path, output_dir):
    base_name = os.path.splitext(os.path.basename(depth_path))[0]

    # Load 16-bit depth image
    depth_img = Image.open(depth_path)  # preserve 16-bit
    depth_array = np.array(depth_img, dtype=np.uint16)

    # Original depth values (uint16)
    depth_array_uint16 = depth_array.astype(np.float32)  # keep full range
    depth_for_hillshade = depth_array_uint16.max() - depth_array_uint16
    hill = compute_hillshade_gdal(depth_for_hillshade)  # use raw values

    # Then normalize for DEM TIFF output
    depth_array = depth_array_uint16 / depth_array_uint16.max()

    # Shadow pixels = uncertain
    uncertainty_map = np.zeros_like(depth_array, dtype=np.uint8)
    uncertainty_map[hill < shadow_threshold] = 1
    
    # Remove small uncertain regions
    uncertainty_map = remove_small_regions(uncertainty_map, min_size=30)

    # Create output directories
    os.makedirs(output_dir, exist_ok=True)
    viz_dir = os.path.join(output_dir, "viz")
    os.makedirs(viz_dir, exist_ok=True)

    # Define arbitrary transform (not georeferenced)
    transform = from_origin(0, 0, 1, 1)

    # Save DEM TIFF
    dem_path = os.path.join(output_dir, f"{base_name}_dem.tif")
    with rasterio.open(
        dem_path,
        'w',
        driver='GTiff',
        height=depth_array.shape[0],
        width=depth_array.shape[1],
        count=1,
        dtype=np.float32,
        transform=transform
    ) as dst:
        dst.write(depth_array, 1)

    # Save uncertainty map TIFF
    uncertainty_path = os.path.join(output_dir, f"{base_name}_uncertainty.tif")
    with rasterio.open(
        uncertainty_path,
        'w',
        driver='GTiff',
        height=uncertainty_map.shape[0],
        width=uncertainty_map.shape[1],
        count=1,
        dtype=uncertainty_map.dtype,
        transform=transform
    ) as dst:
        dst.write(uncertainty_map, 1)

    # --------------------
    # Save visualization PNGs

    # DEM visualization: normalize 0-255 for display
    depth_min, depth_max = depth_array.min(), depth_array.max()
    if depth_max > depth_min:
        depth_viz = ((depth_array - depth_min) / (depth_max - depth_min) * 255).astype(np.uint8)
    else:
        depth_viz = np.zeros_like(depth_array, dtype=np.uint8)
    Image.fromarray(depth_viz).save(os.path.join(viz_dir, f"{base_name}_dem.png"))

    # Uncertainty visualization: scale 0/1 to 0/255
    uncertainty_viz = (uncertainty_map * 255).astype(np.uint8)
    Image.fromarray(uncertainty_viz).save(os.path.join(viz_dir, f"{base_name}_uncertainty.png"))

    # Hillshade visualization: scale 0-255
    hill_viz = (hill * 255).astype(np.uint8)
    Image.fromarray(hill_viz).save(os.path.join(viz_dir, f"{base_name}_hillshade.png"))

    print(f"Processed {depth_path} -> DEM, hillshade, uncertainty, and visualization saved")

def process_terrain_folder(terrain_path, output_base):
    terrain_name = os.path.basename(terrain_path)
    output_terrain_dir = os.path.join(output_base, terrain_name)
    os.makedirs(output_terrain_dir, exist_ok=True)

    for filename in sorted(os.listdir(terrain_path)):
        if filename.lower().startswith("depth") and filename.lower().endswith(".png"):
            depth_path = os.path.join(terrain_path, filename)
            process_depth_file(depth_path, output_terrain_dir)

def main():
    os.makedirs(output_dir, exist_ok=True)
    for terrain in sorted(os.listdir(input_dir)):
        terrain_path = os.path.join(input_dir, terrain)
        if os.path.isdir(terrain_path):
            process_terrain_folder(terrain_path, output_dir)

if __name__ == "__main__":
    main()
