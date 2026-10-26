import os
import re
import glob
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import imageio.v2 as imageio
from parflow.tools.io import read_pfb
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

# ===== 0. Configure output paths and temporal resolution =====
output_dir = './7_3_veg_trans_mmday'
os.makedirs(output_dir, exist_ok=True)

dt = 3600.0  # Duration represented by each hourly flux output (s).
n_days = 365
extent = [0, 330, 0, 200]  # Horizontal grid coordinates, not longitude/latitude.

# Assumptions: output 00001 represents the first hourly interval beginning
# on 2018-10-01; all subsequent outputs represent consecutive hourly intervals.
# Regional means include all finite grid cells; no study-area mask is applied.
print('Current working directory:', os.getcwd())

# ===== 1. Read and sort hourly vegetation-transpiration files =====
all_files = sorted(glob.glob('run_1/mao.out.qflx_tran_veg.*.pfb'))


def extract_step_number(f):
    m = re.search(r'\.(\d+)\.pfb$', os.path.basename(f))
    return int(m.group(1)) if m else -1


all_files = [f for f in all_files if 1 <= extract_step_number(f) <= n_days * 24]
all_files.sort(key=extract_step_number)

# Require a complete sequence to prevent missing hours from shifting day groups.
expected_steps = set(range(1, n_days * 24 + 1))
actual_steps = {extract_step_number(f) for f in all_files}
missing_steps = sorted(expected_steps - actual_steps)
if missing_steps:
    raise FileNotFoundError(
        f'Missing {len(missing_steps)} hourly files; first 20 missing indices: '
        f'{missing_steps[:20]}'
    )
if len(all_files) != n_days * 24:
    raise ValueError('Unexpected file count; check for duplicate numeric timesteps.')

daily_groups = [all_files[i*24:(i+1)*24] for i in range(n_days)]
print(f'Processing {len(daily_groups)} days, with 24 hourly outputs per day.')

# ===== 1.5. Define a consistent colour scale for all animation frames =====
vmin = 0
vmax = 2
print(f'GIF colour scale: vmin={vmin:.3f}, vmax={vmax:.3f} mm/day')
# Values outside this range retain their numerical values in all saved arrays.

# ===== 2. Calculate daily transpiration totals and generate GIF frames =====
daily_et_list = []
frames = []
daily_regional_mean_T = []

for day_idx, group in enumerate(daily_groups, start=1):
    print(f'Processing day {day_idx}/{n_days}')

    sample = read_pfb(group[0])
    if sample.ndim != 3 or sample.shape[0] != 1:
        raise ValueError(f'Expected a single-layer CLM output: {group[0]}, shape={sample.shape}')
    if day_idx == 1:
        expected_shape = sample.shape
    if sample.shape != expected_shape:
        raise ValueError(f'Inconsistent PFB shape: {group[0]}, shape={sample.shape}')
    daily_sum = np.zeros(sample.shape[1:], dtype=np.float64)

    for f in group:
        data = read_pfb(f)
        if data.shape != expected_shape:
            raise ValueError(f'Inconsistent PFB shape: {f}, shape={data.shape}')
        # Hourly transpiration rate (mm/s) multiplied by 3600 s gives mm.
        # Summing 24 hourly contributions yields a daily total (mm/day).
        daily_sum += data[0, :, :] * dt

    # Preserve the original script's flipped orientation in the daily NPY file.
    # Compare with other variables only after confirming identical orientation.
    daily_sum_flipped = np.flipud(daily_sum)

    daily_et_list.append(daily_sum_flipped)

    valid_daily = daily_sum_flipped[np.isfinite(daily_sum_flipped)]
    regional_mean_T = np.mean(valid_daily) if valid_daily.size else np.nan
    daily_regional_mean_T.append(regional_mean_T)

    # Generate an animation frame directly in memory without writing PNG files.
    fig, ax = plt.subplots(figsize=(6, 5))
    canvas = FigureCanvas(fig)

    im = ax.imshow(
        daily_sum_flipped,
        origin='upper',  # Consistent with the preceding vertical array flip.
        cmap='turbo',
        extent=extent,
        vmin=vmin,
        vmax=vmax
    )

    plt.colorbar(im, ax=ax, label='Transpiration (mm/day)', shrink=0.8, extend='both')
    ax.set_title(f'Daily vegetation transpiration (Day {day_idx})')
    ax.set_xlabel('X grid coordinate')
    ax.set_ylabel('Y grid coordinate')

    canvas.draw()
    frame = np.frombuffer(canvas.buffer_rgba(), dtype='uint8')
    frame = frame.reshape(canvas.get_width_height()[::-1] + (4,))
    # Retain an independent copy of the rendered image after closing the figure.
    frames.append(frame.copy())

    plt.close(fig)

# ===== 3. Save the daily spatial array =====
et_stack = np.stack(daily_et_list)  # Shape: (n_days, ny, nx); vertically flipped.

# Treat nonfinite daily totals as missing, without rescaling incomplete days.
# A NaN in any hourly contribution makes that cell's daily total missing.
et_stack[~np.isfinite(et_stack)] = np.nan

npy_path = os.path.join(output_dir, 'daily_mmday.npy')
np.save(npy_path, et_stack)

# ===== 4. Save the daily regional mean transpiration time series =====
daily_regional_mean_T = np.array(daily_regional_mean_T)

daily_mean_npy = os.path.join(
    output_dir,
    'daily_regional_mean_transpiration_mmday.npy'
)

daily_mean_csv = os.path.join(
    output_dir,
    'daily_regional_mean_transpiration_mmday.csv'
)

np.save(daily_mean_npy, daily_regional_mean_T)

np.savetxt(
    daily_mean_csv,
    daily_regional_mean_T,
    delimiter=',',
    header='daily_regional_mean_transpiration_mmday',
    comments=''
)

# ===== 5. Save the GIF animation =====
gif_path = os.path.join(output_dir, 'daily_mmday.gif')
# GIF-PIL interprets duration in seconds; each frame is displayed for 0.6 s.
imageio.mimsave(gif_path, frames, format='GIF-PIL', duration=0.6, loop=0)

# ============================================================
# 6. Calculate annual and seasonal mean spatial transpiration
# ============================================================

# For 2018-10-01 to 2019-09-30: October-June spans 273 days and
# July-September spans 92 days. These periods are not equal-length halves.
split_day = 273
if not 0 < split_day < n_days:
    raise ValueError('The seasonal boundary must lie within the simulation period.')

nonflood_stack = et_stack[:split_day, :, :]
flood_stack = et_stack[split_day:, :, :]

# Calculate the temporal mean of daily totals at each grid cell (mm/day).
# These fields represent mean daily rates rather than cumulative totals (mm).
annual_spatial_T = np.nanmean(et_stack, axis=0)
nonflood_spatial_T = np.nanmean(nonflood_stack, axis=0)
flood_spatial_T = np.nanmean(flood_stack, axis=0)

# Save the annual and seasonal mean spatial fields as CSV files.
annual_csv = os.path.join(
    output_dir,
    'annual_spatial_transpiration_mmday.csv'
)

nonflood_csv = os.path.join(
    output_dir,
    'nonflood_spatial_transpiration_mmday.csv'
)

flood_csv = os.path.join(
    output_dir,
    'flood_spatial_transpiration_mmday.csv'
)

np.savetxt(annual_csv, annual_spatial_T, delimiter=',', fmt='%.6f')
np.savetxt(nonflood_csv, nonflood_spatial_T, delimiter=',', fmt='%.6f')
np.savetxt(flood_csv, flood_spatial_T, delimiter=',', fmt='%.6f')

# ============================================================
# 7. Summarise annual and seasonal mean spatial fields
# ============================================================


def calc_stats(arr):
    # Spatial extrema and equal-cell means of temporally averaged fields.
    # These extrema are not the maximum and minimum daily transpiration.
    values = arr[np.isfinite(arr)]
    if values.size == 0:
        return np.full(3, np.nan)
    return np.array([np.min(values), np.max(values), np.mean(values)])


annual_stats = calc_stats(annual_spatial_T)
nonflood_stats = calc_stats(nonflood_spatial_T)
flood_stats = calc_stats(flood_spatial_T)

print('\n==============================')
print('Vegetation transpiration statistics')
print('==============================')

print('\nAnnual')
print(f'min  = {annual_stats[0]:.6f} mm/day')
print(f'max  = {annual_stats[1]:.6f} mm/day')
print(f'mean = {annual_stats[2]:.6f} mm/day')

print('\nNon-flood season (October-June)')
print(f'min  = {nonflood_stats[0]:.6f} mm/day')
print(f'max  = {nonflood_stats[1]:.6f} mm/day')
print(f'mean = {nonflood_stats[2]:.6f} mm/day')

print('\nFlood season (July-September)')
print(f'min  = {flood_stats[0]:.6f} mm/day')
print(f'max  = {flood_stats[1]:.6f} mm/day')
print(f'mean = {flood_stats[2]:.6f} mm/day')

# Save definitions, spatial-statistic descriptions, and numerical summaries.
stats_txt = os.path.join(output_dir, 'regional_transpiration_statistics.txt')

with open(stats_txt, 'w', encoding='utf-8') as f:
    f.write('Vegetation transpiration statistics\n')
    f.write('Variable: vegetation transpiration (qflx_tran_veg).\n')
    f.write('Hourly input unit: mm/s; daily integration: sum(rate * 3600 s).\n')
    f.write('Spatial-field unit: mm/day (mean daily transpiration).\n')
    f.write('Simulation period: 2018-10-01 to 2019-09-30.\n')
    f.write('Statistics: spatial minimum, maximum, and equal-cell mean of each time-averaged field.\n')
    f.write('Arrays are vertically flipped relative to the original PFB arrays.\n')
    f.write('No study-area mask is applied; all finite cells are included.\n')
    f.write('Nonfinite daily totals are excluded from temporal averages.\n')
    f.write('GIF colour limits affect visualisation only.\n\n')

    f.write('Annual\n')
    f.write(f'min  = {annual_stats[0]:.6f} mm/day\n')
    f.write(f'max  = {annual_stats[1]:.6f} mm/day\n')
    f.write(f'mean = {annual_stats[2]:.6f} mm/day\n\n')

    f.write('Non-flood season (October-June; 273 days)\n')
    f.write(f'min  = {nonflood_stats[0]:.6f} mm/day\n')
    f.write(f'max  = {nonflood_stats[1]:.6f} mm/day\n')
    f.write(f'mean = {nonflood_stats[2]:.6f} mm/day\n\n')

    f.write('Flood season (July-September; 92 days)\n')
    f.write(f'min  = {flood_stats[0]:.6f} mm/day\n')
    f.write(f'max  = {flood_stats[1]:.6f} mm/day\n')
    f.write(f'mean = {flood_stats[2]:.6f} mm/day\n')

# Save named rows to identify the annual and seasonal statistics explicitly.
stats_csv = os.path.join(output_dir, 'regional_transpiration_statistics.csv')

stats_table = np.array([
    annual_stats,
    nonflood_stats,
    flood_stats
])

np.savetxt(
    stats_csv,
    np.column_stack((['annual', 'nonflood', 'flood'], stats_table)),
    delimiter=',',
    header='period,spatial_min_mmday,spatial_max_mmday,spatial_mean_mmday',
    comments='',
    fmt='%s'
)

# ============================================================
# 8. Report numerical checks and output paths
# ============================================================

print('\nCalculation completed.')
print('Annual mean transpiration: spatial minimum:', annual_stats[0])
print('Annual mean transpiration: spatial maximum:', annual_stats[1])
print('Annual mean transpiration: spatial mean:', annual_stats[2])

print('\nOutput files:')
print(npy_path)
print(daily_mean_npy)
print(daily_mean_csv)
print(gif_path)
print(annual_csv)
print(nonflood_csv)
print(flood_csv)
print(stats_txt)
print(stats_csv)

print('\nSaved daily spatial transpiration array: daily_mmday.npy')
print('Saved daily regional mean transpiration time series.')
print('Saved annual mean spatial transpiration CSV.')
print('Saved non-flood-season mean spatial transpiration CSV.')
print('Saved flood-season mean spatial transpiration CSV.')
print('Saved regional_transpiration_statistics.txt')
print('Saved regional_transpiration_statistics.csv')
