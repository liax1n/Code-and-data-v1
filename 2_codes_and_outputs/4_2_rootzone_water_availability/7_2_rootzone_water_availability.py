"""Calculate a root-zone water-availability proxy from ParFlow saturation.

The proxy is the thickness-weighted mean saturation within a prescribed soil
depth. It is dimensionless and does not represent volumetric water content,
water storage, or plant-available water derived from soil retention thresholds.

Assumptions: hourly outputs, bottom-to-top PFB layer indexing, and uniform
vertical discretisation across columns. Configure the actual model geometry
and an appropriate study-area mask before interpreting regional statistics.
"""

import csv
import re
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from parflow.tools.io import read_pfb


# 1. Specify input paths, the analysis period, and the simulation identifier.
RUN_DIR = Path('./run_1')
OUTPUT_DIR = Path('./7_2_rootzone_water_availability')
SCENARIO_NAME = 'current_scenario'
PREFIX = 'mao'
START_DATE = datetime(2018, 10, 1)
N_STEPS = 8760
FIRST_STEP = 1  # First hourly output; the initial-state output is excluded.

# Specify actual cell thicknesses (m), ordered from the surface downward.
# Values must match ComputationalGrid.DZ multiplied by the dzScale values.
LAYER_THICKNESSES_TOP_DOWN = np.array(
    [0.05, 0.10, 0.15, 0.30, 0.40, 1.00, 20.0, 30.0, 50.0, 98.0]
)
ROOT_ZONE_DEPTH_M = 1.0

# Optional 2-D NPY mask in the original PFB horizontal orientation.
# Positive finite values identify study-area cells; other cells are excluded.
# With None, every cell with valid root-zone saturation is included.
MASK_NPY = None
SATURATION_TOLERANCE = 1e-6


def root_zone_geometry(thickness, depth):
    """Derive PFB indices and layer overlaps with the prescribed root zone."""
    thickness = np.asarray(thickness, dtype=float)
    if (thickness.ndim != 1 or thickness.size == 0
            or not np.all(np.isfinite(thickness) & (thickness > 0))):
        raise ValueError('Layer thicknesses must be a nonempty positive finite vector.')
    if not np.isfinite(depth) or not 0 < depth <= thickness.sum():
        raise ValueError('Root-zone depth must lie within the configured model column.')
    layer_tops = np.r_[0.0, np.cumsum(thickness)[:-1]]
    overlaps = np.minimum(thickness, np.maximum(depth - layer_tops, 0.0))
    selected = np.flatnonzero(overlaps > 0)
    return thickness.size - 1 - selected, overlaps[selected]


def valid_mean(total, count):
    """Calculate temporal means using cell-specific valid-hour counts."""
    result = np.full(total.shape, np.nan, dtype=np.float64)
    np.divide(total, count, out=result, where=count > 0)
    return result


def root_zone_mean(saturation, indices, overlaps, mask):
    """Require valid saturation in every selected layer of each column."""
    selected = saturation[indices, :, :]
    outside_range = np.isfinite(selected) & (
        (selected < -SATURATION_TOLERANCE)
        | (selected > 1.0 + SATURATION_TOLERANCE)
    )
    if np.any(outside_range & mask[None, :, :]):
        raise ValueError('Saturation outside [0, 1] beyond tolerance within the study area.')
    # Do not renormalise over missing layers: the target soil depth stays fixed.
    valid = mask & np.all(np.isfinite(selected), axis=0)
    result = np.full(mask.shape, np.nan, dtype=np.float64)
    weighted = np.sum(selected * overlaps[:, None, None], axis=0) / overlaps.sum()
    result[valid] = weighted[valid]
    return result, valid


def plot_map(field, title, path):
    """Use a common physical colour scale for seasonal and scenario comparisons."""
    if not np.any(np.isfinite(field)):
        print(f'Skipping map without valid cells: {path.name}')
        return
    fig, ax = plt.subplots(figsize=(8, 5))
    im = ax.imshow(field, origin='lower', cmap='viridis', vmin=0.0, vmax=1.0)
    fig.colorbar(im, ax=ax, shrink=0.8,
                 label='Thickness-weighted root-zone saturation (-)')
    ax.set(title=title, xlabel='X grid index', ylabel='Y grid index')
    fig.tight_layout()
    fig.savefig(path, dpi=300)
    plt.close(fig)


def main():
    """Validate hourly inputs, aggregate saturation, and export diagnostics."""
    if not isinstance(N_STEPS, int) or N_STEPS <= 0:
        raise ValueError('N_STEPS must be a positive integer.')
    if not isinstance(FIRST_STEP, int) or FIRST_STEP < 1:
        raise ValueError('FIRST_STEP must be a positive output index.')
    if not np.isfinite(SATURATION_TOLERANCE) or SATURATION_TOLERANCE < 0:
        raise ValueError('SATURATION_TOLERANCE must be finite and nonnegative.')
    indices, overlaps = root_zone_geometry(
        LAYER_THICKNESSES_TOP_DOWN, ROOT_ZONE_DEPTH_M
    )
    pattern = re.compile(rf'^{re.escape(PREFIX)}\.out\.satur\.(\d+)\.pfb$')
    indexed = {}
    for path in RUN_DIR.glob(f'{PREFIX}.out.satur.*.pfb'):
        match = pattern.fullmatch(path.name)
        if match:
            step = int(match.group(1))
            if step in indexed:
                raise ValueError(f'Duplicate numeric timestep: {step}')
            indexed[step] = path
    expected = range(FIRST_STEP, FIRST_STEP + N_STEPS)
    missing = [step for step in expected if step not in indexed]
    if missing:
        raise FileNotFoundError(
            f'Missing {len(missing)} hourly files; first 20 missing indices: {missing[:20]}'
        )
    files = [indexed[step] for step in expected]
    sample = np.asarray(read_pfb(str(files[0])))
    if sample.ndim != 3 or sample.shape[0] != len(LAYER_THICKNESSES_TOP_DOWN):
        raise ValueError(f'PFB shape {sample.shape} is inconsistent with the configured layers.')
    shape = sample.shape[1:]
    mask = np.ones(shape, dtype=bool)
    if MASK_NPY is not None:
        raw_mask = np.load(MASK_NPY)
        if raw_mask.shape != shape:
            raise ValueError('The mask must have the same horizontal shape as the PFB files.')
        mask = np.isfinite(raw_mask) & (raw_mask > 0)
    else:
        print('No study-area mask supplied: all cells with valid saturation are included.')
    if not mask.any():
        raise ValueError('The mask contains no study-area cells.')

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    periods = ('annual', 'nonflood', 'flood')
    totals = {p: np.zeros(shape, dtype=np.float64) for p in periods}
    counts = {p: np.zeros(shape, dtype=np.int32) for p in periods}
    period_hours = {p: 0 for p in periods}
    depth_label = f'0-{ROOT_ZONE_DEPTH_M:g} m'
    depth_tag = f'0_{ROOT_ZONE_DEPTH_M:g}m'.replace('.', 'p')
    print(f'PFB shape: {sample.shape}')
    print(f'Root-zone PFB indices (surface downward): {indices.tolist()}')
    print(f'Layer overlap thicknesses (m): {overlaps.tolist()}')
    print(f'Root-zone depth: {overlaps.sum():.6f} m')

    # Stream hourly results to CSV; retain only spatial sums and valid counts.
    hourly_path = OUTPUT_DIR / f'{SCENARIO_NAME}_hourly_rootzone_saturation_{depth_tag}.csv'
    with hourly_path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['interval_start', 'regional_mean_saturation', 'valid_cell_count'])
        for i, path in enumerate(files):
            saturation = sample if i == 0 else np.asarray(read_pfb(str(path)))
            if saturation.shape != sample.shape:
                raise ValueError(f'Inconsistent PFB shape in {path.name}: {saturation.shape}')
            try:
                field, valid = root_zone_mean(saturation, indices, overlaps, mask)
            except ValueError as exc:
                raise ValueError(f'{path.name}: {exc}') from exc
            interval_start = START_DATE + timedelta(hours=i)
            season = 'flood' if interval_start.month in (7, 8, 9) else 'nonflood'
            for period in ('annual', season):
                totals[period] += np.where(valid, field, 0.0)
                counts[period] += valid
                period_hours[period] += 1
            regional_mean = float(np.mean(field[valid])) if valid.any() else np.nan
            writer.writerow([interval_start.isoformat(), regional_mean, int(valid.sum())])
            if (i + 1) % 500 == 0 or i + 1 == N_STEPS:
                print(f'Processed {i + 1}/{N_STEPS} hourly files')

    statistics = []
    for period in periods:
        mean_field = valid_mean(totals[period], counts[period])
        stem = OUTPUT_DIR / f'{SCENARIO_NAME}_{period}_rootzone_water_availability_{depth_tag}'
        # Saved fields are saturation-based proxies and retain PFB orientation.
        np.save(f'{stem}.npy', mean_field)
        np.savetxt(f'{stem}.csv', mean_field, delimiter=',', fmt='%.8g')
        np.save(f'{stem}_valid_hour_count.npy', counts[period])
        plot_map(mean_field, f'{period.capitalize()} mean root-zone saturation ({depth_label})',
                 Path(f'{stem}.png'))
        values = mean_field[np.isfinite(mean_field)]
        stats = (float(values.min()), float(values.max()), float(values.mean())) if values.size else (np.nan,) * 3
        statistics.append((period, *stats, int(values.size), period_hours[period]))
    stats_base = OUTPUT_DIR / f'{SCENARIO_NAME}_regional_rootzone_water_availability_statistics'
    with open(f'{stats_base}.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['period', 'spatial_min', 'spatial_max', 'spatial_mean',
                         'valid_cell_count', 'expected_hours'])
        writer.writerows(statistics)
    with open(f'{stats_base}.txt', 'w', encoding='utf-8') as f:
        f.write('Root-zone water-availability proxy: saturation-based diagnostics\n')
        f.write(f'Analysis period: {START_DATE.isoformat()} to {(START_DATE + timedelta(hours=N_STEPS)).isoformat()} (exclusive)\n')
        f.write('Each file is assumed to represent one consecutive hourly output.\n')
        f.write('Non-flood season: October-June; flood season: July-September.\n')
        f.write(f'Root zone: {depth_label}; PFB indices: {indices.tolist()}\n')
        f.write(f'Layer overlap thicknesses (m): {overlaps.tolist()}\n')
        f.write('Definition: S_RZ = sum(S_k * overlap_k) / root_zone_depth.\n')
        f.write('Unit: dimensionless saturation.\n')
        f.write('This proxy is not volumetric water content or plant-available water.\n')
        f.write('Columns with any missing selected-layer value are excluded for that hour.\n')
        f.write('Finite out-of-range saturation beyond tolerance triggers an error; values are not clipped.\n')
        f.write(f'Saturation tolerance: {SATURATION_TOLERANCE:g}; mask: {MASK_NPY}\n')
        f.write('Arrays retain the original PFB horizontal orientation.\n')
        f.write('Spatial statistics describe time-averaged fields, not hourly extrema.\n')
        f.write('Regional means use equal weights for valid cells, assuming equal cell areas.\n')
        f.write('Valid-hour-count arrays document temporal coverage in each cell.\n\n')
        for row in statistics:
            f.write(f'{row[0]}: min={row[1]:.8g}, max={row[2]:.8g}, mean={row[3]:.8g}, valid_cells={row[4]}, expected_hours={row[5]}\n')
    for row in statistics:
        print(f'{row[0]}: spatial mean={row[3]:.6f}; valid cells={row[4]}; hours={row[5]}')
    print(f'Analysis completed. Results written to: {OUTPUT_DIR.resolve()}')


if __name__ == '__main__':
    main()
