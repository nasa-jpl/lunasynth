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
"""Write a self-contained HTML report of ``estimate_dem_craters.py``: usage, results on base DEMs, and references.

The report runs the detector on each base DEM, measures its recall and false detections on synthetic craters, and
embeds everything in one HTML file that can be opened offline. All figures are static SVG with embedded images, so the
report is complete without JavaScript; a small script only adds hover tooltips and the dark mode switch.

Example:
    uv run python src/data_tools/detector_report.py --output docs/detector_report.html
"""

import argparse
import base64
import html
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import jinja2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import estimate_dem_craters as detector
import lunasynth.craters as craters

REPO_ROOT = Path(__file__).resolve().parents[2]
# (file, label, smallest crater in pixels): the Shape-from-Shading DEM resolves smaller craters than the LOLA DEMs
DEFAULT_TILES = (
    ("assets/base_meshes/NPB_final_adj_5mpp_surf_piece_1km_2_12.tif", "LOLA 1 km (PGDA 78)", 10),
    ("assets/base_meshes/NPC_final_adj_5mpp_surf_piece_2km_2_1.tif", "LOLA 2 km (PGDA 78)", 10),
    (
        "assets/base_meshes/A310_SfS_5mpp_Leibnitz_Beta_piece_1km_r1600_c1200.tif",
        "Shape-from-Shading 1 km (PGDA 104)",
        4,
    ),
)
MIN_DEPTH_RATIO = 0.04
SURFACE_AGE_GA = 3.9

# Every reference was checked against Crossref (title, authors, journal, volume, pages).
REFERENCES = (
    (
        "Lindeberg, T. (1998). Feature detection with automatic scale selection. International Journal of Computer "
        "Vision 30, 79-116.",
        "10.1023/A:1008045108935",
        "Scale-normalized Laplacian of Gaussian used to find depressions at each scale.",
    ),
    (
        "Robbins, S. J., Antonenko, I., Kirchoff, M. R., et al. (2014). The variability of crater identification among "
        "expert and community crater analysts. Icarus 234, 109-131.",
        "10.1016/j.icarus.2014.02.022",
        "Craters smaller than ~10 pixels are unreliable to measure: the default smallest crater.",
    ),
    (
        "Zhang, M., Fa, W., Tong, J., Liu, Y. (2026). Degradation rate and lifetime of small impact craters on the "
        "Moon. AGU Advances 7, e2026AV002542.",
        "10.1029/2026AV002542",
        "Rim height as the mean of a ring at the rim; d/D > 0.04 visibility; diffusivities of the model curve.",
    ),
    (
        "Yang, X., Fa, W., Du, J., Xie, M., Liu, T. (2021). Effect of topographic degradation on small lunar craters: "
        "Implications for regolith thickness estimation. Geophysical Research Letters 48, e2021GL095537.",
        "10.1029/2021GL095537",
        "Crater shapes of the synthetic validation craters.",
    ),
    (
        "Neukum, G., Ivanov, B. A., Hartmann, W. K. (2001). Cratering records in the inner solar system in relation "
        "to the lunar reference system. Space Science Reviews 96, 55-86.",
        "10.1023/A:1011989004263",
        "Production and chronology functions of the model curve.",
    ),
    (
        "Gault, D. E. (1970). Saturation and equilibrium conditions for impact cratering on the lunar surface: "
        "Criteria and implications. Radio Science 5, 273-291.",
        "10.1029/RS005i002p00273",
        "Geometric saturation, N(>D) = 1.54 D^-2 (D in km).",
    ),
    (
        "Minton, D. A., Fassett, C. I., Hirabayashi, M., et al. (2019). The equilibrium size-frequency distribution "
        "of small craters reveals the effects of distal ejecta on lunar landscape morphology. Icarus 326, 63-87.",
        "10.1016/j.icarus.2019.02.021",
        "Small craters are in equilibrium at a few percent of geometric saturation.",
    ),
    (
        "Costello, E. S., Lucey, P. G. (2024). The age and evolution of lunar micro cold traps at the scale of surface "
        "exploration. Geophysical Research Letters 51, e2023GL105369.",
        "10.1029/2023GL105369",
        "Equilibrium as a fraction of geometric saturation.",
    ),
    (
        "Michael, G. G., Kneissl, T., Neesemann, A. (2016). Planetary surface dating from crater size-frequency "
        "distribution measurements: Poisson timing analysis. Icarus 277, 279-285.",
        "10.1016/j.icarus.2016.05.019",
        "Fitting crater counts with few craters; implemented in craterstats.",
    ),
    (
        "Silburt, A., Ali-Dib, M., Zhu, C., et al. (2019). Lunar crater identification via deep learning. Icarus 317, "
        "27-38.",
        "10.1016/j.icarus.2018.06.022",
        "Alternative: a deep-learning detector for DEMs (trained on kilometer-scale craters).",
    ),
    (
        "Zhuo, S., Wang, Y., Zhang, Z., et al. (2025). High-accuracy crater detection for complex planetary "
        "surfaces. IEEE Transactions on Geoscience and Remote Sensing 63, 1-14.",
        "10.1109/TGRS.2025.3560283",
        "Alternative: YOLO-based detector on images, used by Zhang et al. (2026).",
    ),
    (
        "Bertone, S., McKenna, T. E., Barker, M. K., Mazarico, E., Beyer, R. A., Petro, N. (2026). Enhanced "
        "topography models for selected lunar south pole regions with Shape-from-Shading. The Planetary Science "
        "Journal 7, 118.",
        "10.3847/PSJ/ae5b70",
        "Source of the Shape-from-Shading DEM (PGDA product 104, data: doi:10.5281/zenodo.17954508, CC BY 4.0).",
    ),
)


def fractal_terrain(n: int, relief_std: float, seed: int) -> np.ndarray:
    """Random rough terrain without craters, with a power-law spectrum."""
    rng = np.random.default_rng(seed)
    k2 = np.fft.fftfreq(n)[:, None] ** 2 + np.fft.fftfreq(n)[None, :] ** 2
    k2[0, 0] = 1.0
    spectrum = (rng.standard_normal((n, n)) + 1j * rng.standard_normal((n, n))) * k2**-0.9
    z = np.real(np.fft.ifft2(spectrum))
    return (z - z.mean()) / z.std() * relief_std if relief_std > 0 else np.zeros((n, n))


def validate(pixel_size: float = 5.0, n: int = 300, trials: int = 4) -> dict:
    """Recall, diameter error, and false detections on synthetic craters and crater-free terrain."""
    table = craters.profile_table()
    area_km2 = (n * pixel_size / 1000) ** 2
    synthetic = []
    for relief in (0.0, 1.0, 3.0):
        found = total = extra = 0
        ratios = []
        for trial in range(trials):
            rng = np.random.default_rng(trial)
            z = fractal_terrain(n, relief, 10 + trial)
            m = 20
            rows, cols = rng.uniform(40, n - 40, m), rng.uniform(40, n - 40, m)
            diameters = rng.uniform(12, 40, m) * pixel_size
            states = rng.uniform(0, 0.008, m) * diameters**2
            morphology = np.zeros(m, dtype=np.int64)
            craters.add_craters_to_dem(z, rows, cols, diameters, morphology, states, pixel_size, table)
            degraded = craters.lookup_degradation(table, morphology, diameters, states / diameters**2)
            visible = np.nonzero(degraded.depth_ratio >= MIN_DEPTH_RATIO)[0]
            detections = detector.detect_craters(z, pixel_size, 10, 60, MIN_DEPTH_RATIO)
            matched = set()
            for c in visible:
                if len(detections) == 0:
                    continue
                distance = np.hypot(detections[:, 1] - rows[c], detections[:, 0] - cols[c])
                best = int(distance.argmin())
                if distance[best] < 0.3 * diameters[c] / pixel_size:
                    found += 1
                    matched.add(best)
                    ratios.append(detections[best, 2] / (diameters[c] * degraded.rim_radius[c]))
            total += len(visible)
            extra += len(detections) - len(matched)
        synthetic.append(
            {
                "relief_std_m": relief,
                "recall": found / total,
                "n_visible": total,
                "false_per_km2": extra / (trials * area_km2),
                "diameter_ratio_median": float(np.median(ratios)),
                "diameter_ratio_p10": float(np.percentile(ratios, 10)),
                "diameter_ratio_p90": float(np.percentile(ratios, 90)),
            }
        )
    null = []
    for relief in (1.0, 3.0, 12.0):
        false = sum(
            len(detector.detect_craters(fractal_terrain(n, relief, 100 + t), pixel_size, 10, 60, MIN_DEPTH_RATIO))
            for t in range(trials)
        )
        null.append({"relief_std_m": relief, "false_per_km2": false / (trials * area_km2)})
    return {"synthetic": synthetic, "null": null, "trials": trials, "area_km2": area_km2}


def injection_recall(elevation: np.ndarray, pixel_size: float, min_px: float, trials: int = 5) -> dict:
    """Recall of the detector on a real DEM, from craters of the model added to it."""
    from lunasynth.terrain_enhancement import CraterField

    d_min = min_px * pixel_size
    bare = detector.detect_craters(elevation, pixel_size, min_px, min(elevation.shape) / 5, MIN_DEPTH_RATIO)
    bare = bare[bare[:, 2] >= d_min]
    size = elevation.shape[0] * pixel_size
    added = gained = 0
    for trial in range(trials):
        crater_field = CraterField()
        crater_field.generate(
            size_x=size, size_y=size, surface_age_ga=SURFACE_AGE_GA, d_min=d_min, d_max=3 * d_min,
            kappa_800=1.0, phi=0.325, seed=100 + trial, x_init=-size / 2, y_init=-size / 2,
        )  # fmt: skip
        z = elevation.copy()
        half = size / 2 - pixel_size / 2
        crater_field.place_craters_dem(crater_field.craters, z, pixel_size, x_min=-half, y_max=half)
        found = detector.detect_craters(z, pixel_size, min_px, min(elevation.shape) / 5, MIN_DEPTH_RATIO)
        added += sum(1 for c in crater_field.craters if c.depth / c.diameter >= MIN_DEPTH_RATIO and c.diameter >= d_min)
        gained += np.sum(found[:, 2] >= d_min) - len(bare)
    recall = gained / added if added else float("nan")
    return {"bare": int(len(bare)), "injected": int(added), "recall": float(recall)}


# -- Rendering -------------------------------------------------------------------------------------------------
# All figures are static SVG built here, so the report shows everything without JavaScript. A small script only adds
# hover tooltips and the dark mode switch.


def hillshade_png(elevation: np.ndarray, pixel_size: float, max_pixels: int | None = None) -> str:
    """Hillshade of ``elevation`` as a base64 PNG data URI."""
    import matplotlib as mpl

    mpl.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LightSource

    shade = LightSource(azdeg=270, altdeg=20).hillshade(elevation, dx=pixel_size, dy=pixel_size)
    if max_pixels and max(shade.shape) > max_pixels:
        step = int(np.ceil(max(shade.shape) / max_pixels))
        shade = shade[::step, ::step]
    buffer = io.BytesIO()
    plt.imsave(buffer, shade, cmap="gray", vmin=0, vmax=1, format="png")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def crater_attributes(index: int, crater: dict) -> str:
    """Accessible label and tooltip data of a detected crater."""
    text = (
        f"Crater {index}: diameter {crater['d_m']} m, depth {crater['depth_m']} m, depth/diameter {crater['dd']}, "
        f"at ({crater['x_m']:.0f}, {crater['y_m']:.0f}) m"
    )
    rows = [
        [f"{crater['d_m']} m", "diameter"],
        [f"{crater['depth_m']} m", "depth"],
        [f"{crater['dd']}", "depth / diameter"],
        [f"({crater['x_m']:.0f}, {crater['y_m']:.0f}) m", "position"],
    ]
    return f'tabindex="0" role="img" aria-label="{html.escape(text)}" data-tip="{html.escape(json.dumps(rows))}"'


def map_svg(tile: dict) -> str:
    """Hillshade of a tile with its detected craters circled and numbered."""
    size = 360
    scale = size / max(tile["width_m"], tile["height_m"])
    w, h = tile["width_m"] * scale, tile["height_m"] * scale
    left, top = 44, 6
    parts = [
        f'<svg viewBox="0 0 {w + left + 6:.0f} {h + top + 30:.0f}" class="map" role="group" '
        f'aria-label="Hillshade of {html.escape(tile["label"])} with {len(tile["craters"])} detected craters">',
        f'<image href="{tile["hillshade"]}" x="{left}" y="{top}" width="{w:.1f}" height="{h:.1f}" '
        'preserveAspectRatio="none"/>',
    ]
    for fraction in (0, 0.5, 1):
        parts.append(
            f'<text x="{left + fraction * w:.1f}" y="{top + h + 18:.1f}" text-anchor="middle">'
            f"{fraction * tile['width_m']:.0f} m</text>"
        )
        parts.append(
            f'<text x="{left - 6}" y="{top + fraction * h + 4:.1f}" text-anchor="end">'
            f"{fraction * tile['height_m']:.0f}</text>"
        )
    for index, crater in enumerate(tile["craters"], start=1):
        cx, cy = left + crater["x_m"] * scale, top + crater["y_m"] * scale
        r = max(crater["d_m"] / 2 * scale, 3)
        parts.append(
            f'<g class="hit" {crater_attributes(index, crater)}>'
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r + 8:.1f}" fill="transparent"/>'
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" class="ring-gap"/>'
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" class="ring"/>'
            f'<text x="{cx + r * 0.75 + 3:.1f}" y="{cy - r * 0.75 - 2:.1f}" class="ring-label">{index}</text></g>'
        )
    parts.append("</svg>")
    return "".join(parts)


def csfd_svg(tile: dict, model: dict) -> str:
    """Cumulative size-frequency distribution of a tile's detections, the model, and geometric saturation."""
    width, height = 420, 300
    m_left, m_right, m_top, m_bottom = 52, 12, 10, 36
    plot_w, plot_h = width - m_left - m_right, height - m_top - m_bottom
    x_min, x_max, y_min, y_max = 4.0, 400.0, 0.05, 1e5

    def lx(v):
        return m_left + (np.log10(v) - np.log10(x_min)) / (np.log10(x_max) - np.log10(x_min)) * plot_w

    def ly(v):
        return m_top + plot_h - (np.log10(v) - np.log10(y_min)) / (np.log10(y_max) - np.log10(y_min)) * plot_h

    def path(xs, ys):
        points = [(x, y) for x, y in zip(xs, ys) if x_min <= x <= x_max and y_min < y < y_max]
        return "M" + "L".join(f"{lx(x):.1f},{ly(y):.1f}" for x, y in points)

    parts = [
        f'<svg viewBox="0 0 {width} {height}" class="chart" role="group" '
        f'aria-label="Cumulative crater size-frequency distribution of {html.escape(tile["label"])}">'
    ]
    for v in (10, 100):
        parts.append(f'<line x1="{lx(v):.1f}" x2="{lx(v):.1f}" y1="{m_top}" y2="{m_top + plot_h}" class="grid-line"/>')
    for v in (0.1, 1, 10, 100, 1000, 10000):
        label = f"{v / 1000:g}K" if v >= 1000 else f"{v:g}"
        parts.append(
            f'<line x1="{m_left}" x2="{m_left + plot_w}" y1="{ly(v):.1f}" y2="{ly(v):.1f}" class="grid-line"/>'
        )
        parts.append(f'<text x="{m_left - 6}" y="{ly(v) + 4:.1f}" text-anchor="end">{label}</text>')
    for v in (5, 10, 20, 50, 100, 200):
        parts.append(f'<text x="{lx(v):.1f}" y="{m_top + plot_h + 16}" text-anchor="middle">{v}</text>')
    parts.append(
        f'<line x1="{m_left}" x2="{m_left + plot_w}" y1="{m_top + plot_h}" y2="{m_top + plot_h}" class="axis-line"/>'
        f'<text x="{m_left + plot_w / 2}" y="{height - 4}" text-anchor="middle">crater diameter (m)</text>'
        f'<text x="12" y="{m_top + plot_h / 2}" text-anchor="middle" '
        f'transform="rotate(-90 12 {m_top + plot_h / 2})">cumulative craters per km²</text>'
    )
    d_min = tile["d_min"]
    parts.append(
        f'<line x1="{lx(d_min):.1f}" x2="{lx(d_min):.1f}" y1="{m_top}" y2="{m_top + plot_h}" class="axis-line"/>'
        f'<text x="{lx(d_min) + 4:.1f}" y="{m_top + 12}">detection limit {d_min:g} m</text>'
    )
    parts.append(f'<path d="{path(model["d_m"], model["saturation"])}" class="series series-3"/>')
    parts.append(f'<path d="{path(model["d_m"], model["highland"])}" class="series series-2"/>')

    # cumulative count at each distinct diameter: craters of the same diameter share one point
    ordered = sorted(tile["craters"], key=lambda c: -c["d_m"])
    points = []
    for i, crater in enumerate(ordered):
        if i + 1 < len(ordered) and ordered[i + 1]["d_m"] == crater["d_m"]:
            continue
        points.append((crater["d_m"], (i + 1) / tile["area_km2"], i + 1))
    if len(points) > 1:
        step = f"M{lx(points[0][0]):.1f},{ly(points[0][1]):.1f}"
        for d, n, _ in points[1:]:
            step += f"H{lx(d):.1f}V{ly(n):.1f}"
        parts.append(f'<path d="{step}" class="series series-1"/>')
    for d, n, count in points:
        if d < x_min or n <= y_min:
            continue
        model_n = float(np.exp(np.interp(np.log(d), np.log(model["d_m"]), np.log(model["highland"]))))
        rows = [[f"{n:.1f} /km²", f"detected N(≥{d:g} m), {count} craters", "series-1"],
                [f"{model_n:.1f} /km²", "model, highland", "series-2"]]  # fmt: skip
        label = f"{count} craters of {d:g} m or more: {n:.1f} per km², model {model_n:.1f} per km²"
        parts.append(
            f'<g class="hit" tabindex="0" role="img" aria-label="{html.escape(label)}" '
            f'data-tip="{html.escape(json.dumps(rows))}">'
            f'<circle cx="{lx(d):.1f}" cy="{ly(n):.1f}" r="12" fill="transparent"/>'
            f'<circle cx="{lx(d):.1f}" cy="{ly(n):.1f}" r="4.5" class="dot"/></g>'
        )
    parts.append("</svg>")
    return "".join(parts)


def gallery_html(tile: dict, elevation: np.ndarray, pixel_size: float) -> str:
    """Close-up hillshade of every detection, with its rim circle and radial profile."""
    cells = []
    order = sorted(range(len(tile["craters"])), key=lambda i: -tile["craters"][i]["d_m"])
    for number, crater in ((i + 1, tile["craters"][i]) for i in order):
        radius_px = crater["d_m"] / 2 / pixel_size
        # show the crater at the same size in every close-up, with 1.6 radii around it
        half = max(int(np.ceil(1.6 * radius_px)), 4)
        row, col = int(round(crater["y_m"] / pixel_size)), int(round(crater["x_m"] / pixel_size))
        r0, r1 = max(row - half, 0), min(row + half + 1, elevation.shape[0])
        c0, c1 = max(col - half, 0), min(col + half + 1, elevation.shape[1])
        patch = elevation[r0:r1, c0:c1]
        image = hillshade_png(patch, pixel_size)
        size = 132
        scale = size / max(patch.shape)
        w, h = patch.shape[1] * scale, patch.shape[0] * scale
        cx, cy = (col - c0 + 0.5) * scale, (row - r0 + 0.5) * scale
        # azimuthally averaged profile out to 1.6 radii
        rr, cc = np.mgrid[r0:r1, c0:c1]
        distance = np.hypot(rr - row, cc - col) / radius_px
        bins = np.minimum((distance / 0.1).astype(int), 15)
        counts = np.bincount(bins.ravel(), minlength=16)
        profile = np.bincount(bins.ravel(), patch.ravel(), minlength=16) / np.maximum(counts, 1)
        valid = counts[:16] > 0
        radii = (np.arange(16) + 0.5) * 0.1
        prof = profile[:16][valid] - profile[:16][valid].max()
        span = max(np.ptp(prof), 1e-6)
        pw, ph = 120, 44
        line = "M" + "L".join(
            f"{r / 1.6 * pw:.1f},{4 + (-p) / span * (ph - 8):.1f}" for r, p in zip(radii[valid], prof)
        )
        rim_x = 1.0 / 1.6 * pw
        cells.append(
            f'<figure class="crater" {crater_attributes(number, crater)}>'
            f'<svg viewBox="0 0 {w:.0f} {h:.0f}" class="zoom" aria-hidden="true">'
            f'<image href="{image}" width="{w:.1f}" height="{h:.1f}" preserveAspectRatio="none"/>'
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius_px * scale:.1f}" class="ring-gap"/>'
            f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{radius_px * scale:.1f}" class="ring"/></svg>'
            f'<svg viewBox="0 0 {pw} {ph}" class="profile" aria-hidden="true">'
            f'<line x1="{rim_x:.1f}" x2="{rim_x:.1f}" y1="0" y2="{ph}" class="axis-line"/>'
            f'<path d="{line}" class="series series-1"/></svg>'
            f'<figcaption><strong>#{number}</strong> {crater["d_m"]:g} m<br>depth {crater["depth_m"]:g} m &middot; '
            f'd/D {crater["dd"]:g}</figcaption></figure>'
        )
    if not cells:
        return '<p class="muted">No craters detected.</p>'
    caption = (
        '<p class="muted gallery-note">Each close-up spans 1.6 crater radii around the detection, so craters of all '
        "sizes look alike; the curve below is the azimuthally averaged elevation from the center (left) to 1.6 radii, "
        "with the rim marked.</p>"
    )
    return caption + '<div class="gallery">' + "".join(cells) + "</div>"


def crater_table(tile: dict) -> str:
    rows = "".join(
        "<tr>"
        + "".join(
            f'<td class="num">{v}</td>' for v in (i, f"{c['x_m']:.0f}", f"{c['y_m']:.0f}", c["d_m"], c["depth_m"])
        )
        + f'<td class="num">{c["dd"]:g}</td></tr>'
        for i, c in enumerate(tile["craters"], start=1)
    )
    return (
        '<details class="table-view"><summary>Table view</summary><table><thead><tr><th class="num">#</th>'
        '<th class="num">x (m)</th><th class="num">y (m)</th><th class="num">diameter (m)</th>'
        '<th class="num">depth (m)</th><th class="num">d/D</th></tr></thead><tbody>'
        f"{rows}</tbody></table></details>"
    )


def legend_html() -> str:
    return (
        '<div class="legend"><span><span class="key-dot" style="background: var(--series-1)"></span>detected in DEM'
        '</span><span><span class="key-line" style="background: var(--series-2)"></span>model, highland 3.9 Gyr, '
        'd/D &gt; 0.04</span><span><span class="key-line" style="background: var(--series-3)"></span>geometric '
        "saturation</span></div>"
    )


def tile_section(tile: dict, model: dict) -> str:
    title = f"{html.escape(tile['label'])}: {len(tile['craters'])} craters of {tile['d_min']:g} m or more"
    return (
        f'<div class="card"><h3>{title}<span class="file">{html.escape(tile["file"])}</span></h3>'
        '<div class="tile">'
        '<div><div class="legend"><span><span class="key-ring"></span>detected crater (rim diameter, numbered)'
        f"</span></div>{map_svg(tile)}</div>"
        f"<div>{legend_html()}{csfd_svg(tile, model)}</div></div>"
        f'<h4>Detections, largest first</h4>{tile["gallery"]}{crater_table(tile)}</div>'
    )


def analyze_tiles(tiles) -> list[dict]:
    import rasterio

    results = []
    for path, label, min_px in tiles:
        with rasterio.open(REPO_ROOT / path) as src:
            elevation = src.read(1).astype(float)
            pixel_size = src.res[0]
        detections = detector.detect_craters(
            elevation, pixel_size, min_px, min(elevation.shape) / 5, min_depth_ratio=MIN_DEPTH_RATIO
        )
        detections = detections[detections[:, 2] >= min_px * pixel_size]
        area_km2 = elevation.size * pixel_size**2 / 1e6
        d_min = min_px * pixel_size
        model = detector.model_visible_craters(
            np.array([d_min]), SURFACE_AGE_GA, craters.DIFFUSIVITY["highland"], MIN_DEPTH_RATIO
        )[0]
        fitted = None
        if len(detections) >= 5:
            fitted = detector.fit_diffusivity(
                len(detections) / area_km2, d_min, SURFACE_AGE_GA, craters.DIFFUSIVITY["highland"], MIN_DEPTH_RATIO
            ).kappa_800
        tile = {
            "file": path,
            "label": label,
            "pixel_m": pixel_size,
            "width_m": elevation.shape[1] * pixel_size,
            "height_m": elevation.shape[0] * pixel_size,
            "area_km2": area_km2,
            "min_px": min_px,
            "d_min": d_min,
            "density": len(detections) / area_km2,
            "model_density": float(model),
            "kappa_800": fitted,
            "injection": injection_recall(elevation, pixel_size, min_px) if "Shape" in label else None,
            "hillshade": hillshade_png(elevation, pixel_size, max_pixels=720),
            "craters": [
                {
                    "x_m": float(x * pixel_size),
                    "y_m": float(y * pixel_size),
                    "d_m": round(float(diameter), 1),
                    "depth_m": round(float(depth), 2),
                    "dd": round(float(depth / diameter), 3),
                }
                for x, y, diameter, depth in detections
            ],
        }
        tile["gallery"] = gallery_html(tile, elevation, pixel_size)
        results.append(tile)
        print(f"{path}: {len(detections)} craters")
    return results


def example_output(dem: str) -> str:
    """Terminal output of ``estimate_dem_craters.py`` on ``dem``, as printed for a user."""
    with tempfile.TemporaryDirectory() as work:
        result = subprocess.run(
            [sys.executable, str(Path(detector.__file__)), str(REPO_ROOT / dem), "--output-dir", work],
            capture_output=True,
            text=True,
            check=True,
            cwd=REPO_ROOT,
            env={**os.environ, "LUNASYNTH_LOG_DIR": work},
        )
    lines = [line for line in result.stdout.splitlines() if not line.startswith("Saved ")]
    return "\n".join(lines).replace(str(REPO_ROOT) + "/", "")


def render(tiles: list[dict], validation: dict, example: str) -> str:
    grid = np.geomspace(4, 400, 60)
    highland = detector.model_visible_craters(grid, SURFACE_AGE_GA, craters.DIFFUSIVITY["highland"], MIN_DEPTH_RATIO)
    model = {"d_m": grid, "highland": highland, "saturation": craters.geometric_saturation(grid)}
    synthetic_rows = "\n".join(
        f"<tr><td>{v['relief_std_m']:g} m</td><td class=\"num\">{v['n_visible']}</td>"
        f"<td class=\"num\">{100 * v['recall']:.0f}%</td>"
        f"<td>{v['diameter_ratio_median']:.2f} ({v['diameter_ratio_p10']:.2f}-{v['diameter_ratio_p90']:.2f})</td>"
        f"<td class=\"num\">{v['false_per_km2']:.1f}</td></tr>"
        for v in validation["synthetic"]
    )
    null_rows = "\n".join(
        f"<tr><td>{v['relief_std_m']:g} m</td><td class=\"num\">{v['false_per_km2']:.1f}</td></tr>"
        for v in validation["null"]
    )
    references = "\n".join(
        f'<li><span class="cite">{html.escape(text)}</span> '
        f'<a href="https://doi.org/{html.escape(doi)}">doi:{html.escape(doi)}</a>'
        f'<span class="why">{html.escape(why)}</span></li>'
        for text, doi, why in REFERENCES
    )
    summary_rows = []
    for t in tiles:
        injection = t["injection"]
        corrected = (
            f"{t['density'] / injection['recall']:.0f} (recall {100 * injection['recall']:.0f}%)"
            if injection and injection["recall"] > 0
            else "&ndash;"
        )
        kappa = f"{t['kappa_800']:.2g}" if t["kappa_800"] else "&ndash; (fewer than 5 craters)"
        summary_rows.append(
            f"<tr><td>{html.escape(t['label'])}</td><td>{t['width_m'] / 1000:g} &times; {t['height_m'] / 1000:g}</td>"
            f"<td>{t['d_min']:.0f} m ({t['min_px']} px)</td><td class=\"num\">{len(t['craters'])}</td>"
            f"<td class=\"num\">{t['density']:.1f}</td><td class=\"num\">{corrected}</td>"
            f"<td class=\"num\">{t['model_density']:.1f}</td><td class=\"num\">{kappa}</td></tr>"
        )
    sfs = next((t for t in tiles if t["injection"]), None)
    sfs_recall = f"{100 * sfs['injection']['recall']:.0f}%" if sfs else "n/a"
    sfs_injected = str(sfs["injection"]["injected"]) if sfs else "n/a"
    tile_sections = "\n".join(tile_section(t, model) for t in tiles)
    environment = jinja2.Environment(
        loader=jinja2.FileSystemLoader(Path(__file__).resolve().parent),
        undefined=jinja2.StrictUndefined,  # a missing value is an error, not an empty string
        autoescape=False,  # values are HTML built and escaped by this module
        keep_trailing_newline=True,
    )
    page = environment.get_template("detector_report.html.j2").render(
        example=html.escape(example),
        summary_rows="\n".join(summary_rows),
        tiles=tile_sections,
        sfs_recall=sfs_recall,
        sfs_injected=sfs_injected,
        synthetic_rows=synthetic_rows,
        null_rows=null_rows,
        references=references,
    )
    if "{{" in page or "{%" in page:
        msg = "Unrendered template placeholder in the report"
        raise RuntimeError(msg)
    return page


def main():
    parser = argparse.ArgumentParser(description="Write an HTML report of the crater detector.")
    parser.add_argument("--output", default="tmp/detector_report.html", help="Output HTML file.")
    args = parser.parse_args()
    tiles = analyze_tiles(DEFAULT_TILES)
    validation = validate()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    example = example_output("assets/base_meshes/NPC_final_adj_5mpp_surf_piece_2km_2_1.tif")
    output.write_text(render(tiles, validation, example), encoding="utf-8")
    print(f"Saved {output} ({output.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
