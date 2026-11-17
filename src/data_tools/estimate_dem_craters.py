#  Copyright (c) 2024. Jet Propulsion Laboratory. All rights reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Estimate the craters already present in a base DEM and compare them with the crater model.

LuNaSynth only adds craters smaller than what the base DEM resolves (``crater_field.resolvable_pixels``). This script
checks that the craters the base DEM does contain are consistent with the model used for the smaller ones.

Craters are detected as bowl-shaped depressions: scale-space maxima of the scale-normalized Laplacian of Gaussian of the
topography. After removing the regional slope, a candidate is kept if its depth / diameter is above a threshold, its
topography is close to axisymmetric (the radial profile explains most of its variance), which rejects most depressions
of rough terrain without craters, and its surroundings are not much more curved than its own depth, which rejects the
walls and floors of craters larger than the searched range. The script writes a CSV of the detections and a figure with
the cumulative size-frequency distribution of the detected craters, the model's visible craters for the same surface age
and terrain, the production function, and the geometric saturation.

On synthetic tests (fresh and degraded craters of 10-40 pixels on fractal terrain), the detector finds about half of
the visible craters with less than one false detection per km^2; on rough terrain it finds fewer. Isolated craters are
found with diameters within ~5%; craters overlapping a neighbor are usually missed.

Caveats:
- Craters smaller than ~10 pixels are not reliably measured (Robbins et al., 2014, Icarus 234, 109-131).
- LOLA polar DEMs (PGDA product 78) interpolate most pixels between altimetry tracks, so their effective resolution
  is coarser than the pixel size and varies across a tile. Detections are a lower bound of the craters, and
  interpolation artifacts can produce false detections.
- Simple depression detection can merge overlapping craters and miss very degraded ones.

Example:
    uv run python src/data_tools/estimate_dem_craters.py assets/base_meshes/NPB_final_adj_5mpp_surf_piece_1km_2_12.tif \
        --age 3.9 --terrain highland --output-dir tmp/dem_craters
"""

import argparse
import csv
from pathlib import Path

import lunasynth.craters as craters
import matplotlib.pyplot as plt
import numpy as np
import rasterio
from scipy import ndimage

# Ratio between a fresh crater's diameter and the scale (sigma) at which the normalized Laplacian of Gaussian of its
# topography peaks, calibrated on synthetic craters of 8 to 30 pixels.
DIAMETER_TO_SIGMA = 5.2


def detect_craters(
    elevation: np.ndarray,
    pixel_size: float,
    min_diameter_px: float = 10.0,
    max_diameter_px: float = 80.0,
    min_depth_ratio: float = 0.02,
    min_axisymmetry: float = 0.6,
) -> np.ndarray:
    """Detect bowl-shaped depressions in a DEM.

    Args:
        elevation: Elevation in meters.
        pixel_size: Pixel size in meters.
        min_diameter_px: Smallest crater diameter to search for, in pixels.
        max_diameter_px: Largest crater diameter to search for, in pixels.
        min_depth_ratio: Smallest depth / diameter of a crater.
        min_axisymmetry: Smallest fraction of the variance of the topography within 1.5 radii explained by its
            radial profile.

    Returns:
        Array with one row per crater: x (column, px), y (row, px), diameter (m), depth (m).

    """
    elevation = np.asarray(elevation, dtype=float)
    # one extra scale at each end, so maxima at min_diameter_px and max_diameter_px can be found
    n_scales = 16
    step = (max_diameter_px / min_diameter_px) ** (1 / (n_scales - 1))
    sigmas = np.geomspace(min_diameter_px / step, max_diameter_px * step, n_scales + 2) / DIAMETER_TO_SIGMA
    stack = np.stack([s**2 * ndimage.gaussian_laplace(elevation, s) for s in sigmas])
    peaks = (stack == ndimage.maximum_filter(stack, size=(3, 5, 5))) & (stack > 0)
    # maxima at the first or last scale are features outside the searched size range
    peaks[0] = peaks[-1] = False
    rows_all, cols_all = np.mgrid[0 : elevation.shape[0], 0 : elevation.shape[1]]

    detections = []
    for k, i, j in zip(*np.nonzero(peaks)):
        radius = sigmas[k] * DIAMETER_TO_SIGMA / 2
        reach = int(np.ceil(2.5 * radius))
        if i < reach or j < reach or i + reach >= elevation.shape[0] or j + reach >= elevation.shape[1]:
            continue  # not fully inside the DEM
        window = (slice(i - reach, i + reach + 1), slice(j - reach, j + reach + 1))
        z = elevation[window]
        rr, cc = rows_all[window] - i, cols_all[window] - j
        distance = np.hypot(rr, cc) / radius
        # remove the regional slope with a plane fitted outside the ejecta
        outside = (distance >= 1.5) & (distance <= 2.5)
        design = np.column_stack([rr[outside], cc[outside], np.ones(outside.sum())])
        plane, *_ = np.linalg.lstsq(design, z[outside], rcond=None)
        z = z - (plane[0] * rr + plane[1] * cc + plane[2])
        # the rim crest of the azimuthally averaged profile refines the radius given by the Laplacian scale
        bins = np.minimum((distance / 0.05).astype(int), 49)
        mean_profile = np.bincount(bins.ravel(), z.ravel(), 50) / np.maximum(np.bincount(bins.ravel(), None, 50), 1)
        crest = 0.05 * (np.argmax(mean_profile[10:30]) + 10.5)  # between 0.5 and 1.5 radii
        radius *= crest
        distance /= crest
        # rim height as in Zhang et al. (2026): mean elevation of a thin ring at the rim, at least a pixel wide
        half_width = max(0.1, 0.5 / radius)
        rim = z[np.abs(distance - 1.0) <= half_width].mean()
        floor = z[distance <= max(0.3, 0.5 / radius)].min()
        depth = rim - floor
        diameter = 2 * radius * pixel_size
        if depth / diameter < min_depth_ratio:
            continue
        inside = distance <= 1.5
        bins = np.minimum((distance[inside] / 0.1).astype(int), 14)
        radial_profile = np.bincount(bins, z[inside]) / np.maximum(np.bincount(bins), 1)
        axisymmetry = 1 - np.var(z[inside] - radial_profile[bins]) / max(np.var(z[inside]), 1e-12)
        if axisymmetry < min_axisymmetry:
            continue
        # the walls of a crater larger than the searched range curve the surroundings (a parabola instead of a
        # plane); a crater's own depth is much larger than that curvature across it
        quadratic = np.column_stack([rr[outside] ** 2, cc[outside] ** 2, rr[outside] * cc[outside], design])
        coefficients, *_ = np.linalg.lstsq(quadratic, z[outside], rcond=None)
        bowl = (coefficients[0] * rr**2 + coefficients[1] * cc**2 + coefficients[2] * rr * cc)[distance <= 1.0]
        if np.ptp(bowl) > 0.5 * depth:
            continue
        detections.append((j, i, diameter, depth, stack[k, i, j]))
    return _suppress_overlaps(np.array(detections, dtype=float).reshape(-1, 5), pixel_size)[:, :4]


def _suppress_overlaps(detections: np.ndarray, pixel_size: float) -> np.ndarray:
    """Keep the strongest of detections whose centers are within the radius of a stronger one.

    The same depression is found at several neighboring scales and positions.
    """
    keep = []
    for index in np.argsort(detections[:, 4])[::-1]:
        x, y, diameter = detections[index, :3]
        radius_px = diameter / 2 / pixel_size
        if all(np.hypot(x - detections[k, 0], y - detections[k, 1]) > radius_px for k in keep):
            keep.append(index)
    return detections[sorted(keep)]


def model_visible_craters(
    diameters: np.ndarray,
    surface_age_ga: float,
    diffusivity: craters.Diffusivity,
    visibility_depth_ratio: float,
) -> np.ndarray:
    """Expected cumulative number of visible craters per km^2 for the crater model of LuNaSynth."""
    table = craters.profile_table()
    production = craters.ProductionModel()
    # degradation state at which normal craters become invisible
    normal = table.depth_ratio[craters.NORMAL].mean(axis=0)
    state_invisible = np.interp(-visibility_depth_ratio, -normal, table.degradation_states)
    # integrate to 10 km so the cumulative count includes all larger craters, whatever diameters are asked
    grid = np.geomspace(min(diameters.min(), 1.0) / 2, 10_000.0, 4000)
    lifetime_ga = state_invisible * grid**2 / diffusivity(grid) / 1000.0
    differential = -np.gradient(production.cumulative_shape(grid), grid)
    visible = differential * production.n1(np.minimum(lifetime_ga, surface_age_ga))
    cumulative = np.concatenate([np.cumsum((visible[1:] + visible[:-1])[::-1] / 2 * np.diff(grid)[::-1])[::-1], [0]])
    return np.interp(diameters, grid, cumulative)


def fit_diffusivity(
    density: float, diameter: float, surface_age_ga: float, diffusivity: craters.Diffusivity, visibility: float
) -> craters.Diffusivity:
    """Diffusivity, scaled from ``diffusivity``, for which the model has ``density`` craters above ``diameter``."""
    low, high = -6.0, 6.0  # log of the scale factor
    for _ in range(60):
        middle = (low + high) / 2
        trial = craters.Diffusivity(diffusivity.kappa_800 * np.exp(middle), diffusivity.phi)
        model = model_visible_craters(np.array([diameter]), surface_age_ga, trial, visibility)[0]
        # fewer visible craters with faster degradation
        low, high = (middle, high) if model > density else (low, middle)
    return craters.Diffusivity(diffusivity.kappa_800 * np.exp((low + high) / 2), diffusivity.phi)


def main():
    parser = argparse.ArgumentParser(description="Estimate the craters in a base DEM and compare with the model.")
    parser.add_argument("dem", type=str, help="Base DEM GeoTIFF.")
    parser.add_argument("--age", type=float, default=3.9, help="Surface age for the model curve, Gyr.")
    parser.add_argument("--terrain", choices=sorted(craters.DIFFUSIVITY), default="highland")
    parser.add_argument("--min-diameter-px", type=float, default=10.0, help="Smallest crater to detect, pixels.")
    parser.add_argument("--min-depth-ratio", type=float, default=0.04, help="Smallest depth / diameter.")
    parser.add_argument("--output-dir", type=str, default="tmp/dem_craters", help="Folder for the CSV and figure.")
    args = parser.parse_args()

    with rasterio.open(args.dem) as src:
        elevation = src.read(1)
        pixel_size = src.res[0]
    area_km2 = elevation.size * pixel_size**2 / 1e6
    max_diameter_px = min(elevation.shape) / 5
    detections = detect_craters(
        elevation, pixel_size, args.min_diameter_px, max_diameter_px, min_depth_ratio=args.min_depth_ratio
    )
    # the rim crest refinement can move diameters below the searched range
    detections = detections[detections[:, 2] >= args.min_diameter_px * pixel_size]

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    name = Path(args.dem).stem
    with open(output_dir / f"{name}_craters.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["column_px", "row_px", "diameter_m", "depth_m"])
        writer.writerows(detections.tolist())

    d_min = args.min_diameter_px * pixel_size
    diffusivity = craters.DIFFUSIVITY[args.terrain]
    print(f"{args.dem}: {len(detections)} craters of {d_min:g} m or more with d/D > {args.min_depth_ratio:g}")
    print(f"area {area_km2:.2f} km^2, pixel size {pixel_size:g} m")
    grid = np.geomspace(d_min, max_diameter_px * pixel_size, 6)
    model = model_visible_craters(grid, args.age, diffusivity, args.min_depth_ratio)
    for diameter, expected in zip(grid, model):
        observed = np.sum(detections[:, 2] >= diameter) / area_km2 if len(detections) else 0.0
        print(f"  N(>{diameter:6.1f} m): detected {observed:8.1f} /km^2, model {expected:8.1f} /km^2")
    fitted = None
    if len(detections) >= 5:
        observed = len(detections) / area_km2
        fitted = fit_diffusivity(observed, d_min, args.age, diffusivity, args.min_depth_ratio)
        print(
            f"The model matches the detected N(>{d_min:g} m) with kappa_800 = {fitted.kappa_800:.3g} m^2/Myr "
            f"(phi = {fitted.phi:.3g}; {args.terrain} default {diffusivity.kappa_800:.3g}). Detections miss part of "
            "the craters, so the true density is higher and the matching diffusivity lower. To use it, set in the "
            f"dataset configuration: crater_field: {{kappa_800: {fitted.kappa_800:.3g}, phi: {fitted.phi:.3g}}}"
        )

    fig, ax = plt.subplots(figsize=(6, 5))
    curve = np.geomspace(1.0, max_diameter_px * pixel_size, 200)
    production = craters.ProductionModel()
    ax.loglog(
        curve, model_visible_craters(curve, args.age, diffusivity, args.min_depth_ratio), label=f"model, {args.terrain}"
    )
    if fitted is not None:
        ax.loglog(
            curve,
            model_visible_craters(curve, args.age, fitted, args.min_depth_ratio),
            label=f"model, kappa_800 = {fitted.kappa_800:.2g}",
        )
    ax.loglog(curve, production.cumulative(curve, args.age), "--", label=f"production, {args.age:g} Gyr")
    ax.loglog(curve, craters.geometric_saturation(curve), ":", label="geometric saturation")
    if len(detections):
        sizes = np.sort(detections[:, 2])[::-1]
        ax.loglog(sizes, np.arange(1, len(sizes) + 1) / area_km2, "o", markersize=3, label="detected in DEM")
    ax.axvline(d_min, color="gray", linewidth=0.8)
    ax.set_xlabel("Crater diameter (m)")
    ax.set_ylabel("Cumulative number per km$^2$")
    ax.set_title(f"{name}\n{args.terrain}, {args.age:g} Gyr, d/D > {args.min_depth_ratio:g}", fontsize=9)
    ax.legend(fontsize=8)
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / f"{name}_csfd.png", dpi=150)
    print(f"Saved {output_dir / f'{name}_craters.csv'} and {output_dir / f'{name}_csfd.png'}")


if __name__ == "__main__":
    main()
