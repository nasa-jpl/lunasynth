import os
import glob
import rasterio
import numpy as np
from rasterio.windows import Window
from rasterio.enums import Resampling
from skimage.transform import resize


def downsample_raster(array, profile, scale_factor=2, resampling=Resampling.bilinear):
    """Downsample a raster array by an integer factor without CRS requirements."""
    bands, height, width = array.shape
    new_height = height // scale_factor
    new_width = width // scale_factor

    # Map rasterio's Resampling to skimage order
    if resampling == Resampling.nearest:
        order = 0
    elif resampling == Resampling.bilinear:
        order = 1
    else:
        order = 1  # fallback

    out = np.empty((bands, new_height, new_width), dtype=array.dtype)
    for b in range(bands):
        out[b] = resize(
            array[b],
            (new_height, new_width),
            order=order,
            preserve_range=True,
            anti_aliasing=True if order > 0 else False
        ).astype(array.dtype)

    new_profile = profile.copy()
    new_profile.update({
        "height": new_height,
        "width": new_width,
        "transform": profile["transform"] * rasterio.Affine.scale(scale_factor)
    })

    return out, new_profile


def create_tiles_from_folder(input_folder, output_folder, tile_size):
    """
    Cut DEM and uncertainty TIFs in a folder into square tiles,
    saving into global category-based subfolders instead of per dataset.

    Args:
        input_folder (str): Path to folder containing *_dem.tif and *_uncertainty.tif files.
        output_folder (str): Path to folder where tiles will be saved.
        tile_size (int): Tile size in pixels.
    """
    # Prepare four global output folders
    out_dirs = {
        "dem_high": os.path.join(output_folder, "high_res_dem"),
        "dem_low": os.path.join(output_folder, "low_res_dem"),
        "unc_high": os.path.join(output_folder, "high_res_uncertainty"),
        "unc_low": os.path.join(output_folder, "low_res_uncertainty"),
    }
    for path in out_dirs.values():
        os.makedirs(path, exist_ok=True)

    dem_files = glob.glob(os.path.join(input_folder, "*_dem.tif"))
    if not dem_files:
        raise FileNotFoundError("No *_dem.tif files found in the input folder.")

    for dem_path in dem_files:
        base_name = os.path.splitext(os.path.basename(dem_path))[0].replace("_dem", "")
        unc_path = os.path.join(input_folder, f"{base_name}_uncertainty.tif")
        has_unc = os.path.exists(unc_path)

        with rasterio.open(dem_path) as src_dem:
            width, height = src_dem.width, src_dem.height
            count = 0

            src_unc = rasterio.open(unc_path) if has_unc else None
            if src_unc and (src_unc.width != width or src_unc.height != height):
                raise ValueError(f"DEM and uncertainty must have same dimensions ({base_name})")

            for j in range(0, height - tile_size + 1, tile_size):
                for i in range(0, width - tile_size + 1, tile_size):
                    window = Window(i, j, tile_size, tile_size)

                    profile = src_dem.profile.copy()
                    profile.update({
                        "width": tile_size,
                        "height": tile_size,
                        "transform": rasterio.windows.transform(window, src_dem.transform)
                    })

                    # --- DEM ---
                    dem_data = src_dem.read(window=window)
                    dem_tile_name = f"{base_name}_tile{count}_dem.tif"
                    dem_low_name = f"{base_name}_tile{count}_dem_low.tif"

                    with rasterio.open(os.path.join(out_dirs["dem_high"], dem_tile_name), "w", **profile) as dst:
                        dst.write(dem_data)

                    dem_low, dem_profile_low = downsample_raster(dem_data, profile, scale_factor=2)
                    with rasterio.open(os.path.join(out_dirs["dem_low"], dem_low_name), "w", **dem_profile_low) as dst:
                        dst.write(dem_low)

                    # --- UNCERTAINTY (if available) ---
                    if src_unc:
                        unc_data = src_unc.read(window=window)
                        unc_tile_name = f"{base_name}_tile{count}_uncertainty.tif"
                        unc_low_name = f"{base_name}_tile{count}_uncertainty_low.tif"

                        with rasterio.open(os.path.join(out_dirs["unc_high"], unc_tile_name), "w", **profile) as dst:
                            dst.write(unc_data)

                        unc_low, unc_profile_low = downsample_raster(
                            unc_data, profile, scale_factor=2, resampling=Resampling.nearest
                        )
                        with rasterio.open(os.path.join(out_dirs["unc_low"], unc_low_name), "w", **unc_profile_low) as dst:
                            dst.write(unc_low)

                    count += 1

            if src_unc:
                src_unc.close()

        print(f"Saved {count} tiles (+low-res) for {base_name}")


create_tiles_from_folder("/home/anjashep-frog-lab/Research/LunarHD/lunasynth/generated_data/datasets/ortho_nominal_2025-09-01_13-54-26_out/terrain_00/", "/home/anjashep-frog-lab/Research/LunarHD/lunasynth/generated_data/datasets/ortho_nominal_2025-09-01_13-54-26_tiles", tile_size=128)

