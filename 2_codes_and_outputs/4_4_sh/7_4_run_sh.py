import os
import re
import glob
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import imageio.v2 as imageio
from parflow.tools.io import read_pfb


# ============================================================
# 1. Configure input paths and the analysis period
# ============================================================

run_dir = './run_1'
scenario_name = 'current_scenario'
output_dir = './7_4_sh'
os.makedirs(output_dir, exist_ok=True)

n_steps = 8760
n_days = 365
extent = [0, 330, 0, 200]  # Grid coordinates, not longitude and latitude.

# Assumptions: consecutive hourly outputs beginning on 2018-10-01,
# with output 00001 representing the first hourly interval.
# Equal cell areas are assumed for regional means; no mask is applied.
# Input and time-averaged output units are W/m2. No factor of 3600 is needed.
print('Current working directory:', os.getcwd())
print('Output directory:', output_dir)
if n_steps != n_days * 24:
    raise ValueError('n_steps must equal n_days multiplied by 24.')

# ============================================================
# 2. Read and sort hourly sensible heat-flux files
# ============================================================


def extract_step_number(f):
    match = re.search(r'\.(\d+)\.pfb$', os.path.basename(f))
    return int(match.group(1)) if match else -1


all_sh_files = sorted(
    glob.glob(os.path.join(run_dir, 'mao.out.eflx_sh_tot.*.pfb')),
    key=extract_step_number
)
all_sh_files = [
    f for f in all_sh_files
    if 1 <= extract_step_number(f) <= n_steps
]
all_sh_files.sort(key=extract_step_number)

print(f'Number of hourly files: {len(all_sh_files)}')
expected_steps = set(range(1, n_steps + 1))
actual_steps = {extract_step_number(f) for f in all_sh_files}
missing_steps = sorted(expected_steps - actual_steps)
if missing_steps:
    raise FileNotFoundError(
        f'Missing {len(missing_steps)} hourly files; first 20: {missing_steps[:20]}'
    )
if len(all_sh_files) != n_steps:
    raise ValueError('Unexpected file count; check for duplicate numeric timesteps.')
all_sh_files = all_sh_files[:n_steps]

daily_groups = [
    all_sh_files[i * 24:(i + 1) * 24]
    for i in range(n_days)
]
print(f'Processing {len(daily_groups)} days, with 24 hourly outputs per day.')

# ============================================================
# 3. Determine colour limits from all hourly spatial fields
# ============================================================

sample_layers = []
for f in all_sh_files:
    data = np.asarray(read_pfb(f), dtype=np.float64)
    if data.ndim != 3 or data.shape[0] != 1:
        raise ValueError(f'Expected a single-layer CLM output: {f}, shape={data.shape}')
    if not sample_layers:
        expected_shape = data.shape
    if data.shape != expected_shape:
        raise ValueError(f'Inconsistent PFB shape: {f}, shape={data.shape}')
    data[~np.isfinite(data)] = np.nan
    sample_layers.append(data[0, :, :])

# Preserve the original full-year percentile calculation. This requires
# substantial memory, particularly while stacking the hourly arrays.
all_array = np.stack(sample_layers)
if not np.any(np.isfinite(all_array)):
    raise ValueError('No finite heat-flux values were found in the analysis period.')
vmin = np.nanpercentile(all_array, 2)
vmax = np.nanpercentile(all_array, 98)
if vmin == vmax:
    padding = max(abs(float(vmin)) * 0.01, 1e-6)
    vmin, vmax = vmin - padding, vmax + padding
print(f'Hourly-field colour limits: vmin={vmin:.2f}, vmax={vmax:.2f} W/m2')
# Release the colour-scale arrays before processing the daily fields.
del sample_layers, all_array, data

# ============================================================
# 4. Calculate daily means, GIF frames, and hourly regional means
# ============================================================

layer_list = []
frames = []
hourly_regional_mean_sh = []

for day_index, group in enumerate(daily_groups, start=1):
    daily_layers = []
    for file in group:
        data = np.asarray(read_pfb(file), dtype=np.float64)
        if data.shape != expected_shape:
            raise ValueError(f'Inconsistent PFB shape: {file}, shape={data.shape}')
        data[~np.isfinite(data)] = np.nan
        sh_layer = data[0, :, :]
        valid_values = sh_layer[np.isfinite(sh_layer)]
        hourly_regional_mean_sh.append(
            np.mean(valid_values) if valid_values.size else np.nan
        )
        daily_layers.append(sh_layer)

    # An arithmetic mean is appropriate for uniformly spaced hourly outputs.
    # Missing hourly values are excluded cellwise, as in the original script.
    day_avg = np.nanmean(np.stack(daily_layers), axis=0)
    day_avg_flipped = np.flipud(day_avg)
    layer_list.append(day_avg_flipped)

    # Saved NPY and CSV spatial arrays retain this vertical flip.
    fig, ax = plt.subplots()

    im = ax.imshow(
        day_avg_flipped,
        origin='upper',
        cmap='turbo',
        extent=extent,
        vmin=vmin,
        vmax=vmax
    )
    plt.colorbar(im, ax=ax, label='Sensible heat flux (W m$^{-2}$)',
                 shrink=0.8, extend='both')
    ax.set_title(f'Daily mean sensible heat flux (Day {day_index})')
    ax.set_xlabel('X grid coordinate')
    ax.set_ylabel('Y grid coordinate')
    # Preserve the original SH workflow: save each daily PNG before reading it.
    png_path = os.path.join(output_dir, f'eflx_sh_tot_day_{day_index:03d}.png')
    plt.savefig(png_path, dpi=300)
    frames.append(imageio.imread(png_path))
    plt.close(fig)
    if day_index % 30 == 0 or day_index == n_days:
        print(f'Processed {day_index}/{n_days} days')

# ============================================================
# 5. Save the daily spatial array and GIF animation
# ============================================================

sh_stack = np.stack(layer_list)  # Shape: (n_days, ny, nx); vertically flipped.
npy_path = os.path.join(output_dir, 'eflx_sh_tot_daily_mean.npy')
np.save(npy_path, sh_stack)
gif_path = os.path.join(output_dir, 'eflx_sh_tot.gif')
# GIF-PIL interprets duration in seconds; display each frame for 0.6 s.
imageio.mimsave(gif_path, frames, format='GIF-PIL', duration=0.6, loop=0)

# ============================================================
# 6. Calculate annual and seasonal mean spatial heat-flux fields
# ============================================================

# For 2018-10-01 to 2019-09-30, October-June spans 273 days and
# July-September spans 92 days. These periods are not equal-length halves.
# Array indices 272 and 273 correspond to June 30 and July 1, respectively.
split_day = 273
if not 0 < split_day < n_days:
    raise ValueError('The seasonal boundary must lie within the analysis period.')
nonflood_stack = sh_stack[:split_day, :, :]
flood_stack = sh_stack[split_day:, :, :]

# These are mean fluxes (W/m2), not time-integrated energy (J/m2).
# With missing values, seasonal fields are equal-weight means of valid daily
# means, which may differ from means over all valid hourly observations.
annual_spatial_sh = np.nanmean(sh_stack, axis=0)
nonflood_spatial_sh = np.nanmean(nonflood_stack, axis=0)
flood_spatial_sh = np.nanmean(flood_stack, axis=0)

annual_spatial_csv = os.path.join(
    output_dir, f'{scenario_name}_annual_spatial_sensible_heat_flux_Wm2.csv'
)
nonflood_spatial_csv = os.path.join(
    output_dir, f'{scenario_name}_nonflood_spatial_sensible_heat_flux_Wm2.csv'
)
flood_spatial_csv = os.path.join(
    output_dir, f'{scenario_name}_flood_spatial_sensible_heat_flux_Wm2.csv'
)
np.savetxt(annual_spatial_csv, annual_spatial_sh, delimiter=',', fmt='%.6f')
np.savetxt(nonflood_spatial_csv, nonflood_spatial_sh, delimiter=',', fmt='%.6f')
np.savetxt(flood_spatial_csv, flood_spatial_sh, delimiter=',', fmt='%.6f')

# ============================================================
# 7. Summarise annual and seasonal mean spatial fields
# ============================================================

hourly_regional_mean_sh = np.array(hourly_regional_mean_sh)
# Export the hourly time series already calculated in Section 4.
hourly_mean_npy = os.path.join(output_dir, 'hourly_regional_mean_sensible_heat_flux_Wm2.npy')
hourly_mean_csv = os.path.join(output_dir, 'hourly_regional_mean_sensible_heat_flux_Wm2.csv')
np.save(hourly_mean_npy, hourly_regional_mean_sh)
np.savetxt(hourly_mean_csv, hourly_regional_mean_sh, delimiter=',',
           header='hourly_regional_mean_sensible_heat_flux_Wm2', comments='', fmt='%.6f')


def calc_stats(arr):
    # Spatial extrema of temporally averaged fields, not hourly extrema.
    values = arr[np.isfinite(arr)]
    if values.size == 0:
        return np.nan, np.nan, np.nan
    return np.min(values), np.max(values), np.mean(values)


annual_stats = calc_stats(annual_spatial_sh)
nonflood_stats = calc_stats(nonflood_spatial_sh)
flood_stats = calc_stats(flood_spatial_sh)

print('\nSensible heat-flux statistics (W/m2)')
print('Annual: spatial min, max, mean =', annual_stats)
print('Non-flood season (October-June): spatial min, max, mean =', nonflood_stats)
print('Flood season (July-September): spatial min, max, mean =', flood_stats)

# Save the text summary.
stats_txt = os.path.join(
    output_dir, f'{scenario_name}_regional_sensible_heat_flux_statistics.txt'
)
with open(stats_txt, 'w', encoding='utf-8') as f:
    f.write('Sensible heat-flux statistics\n')
    f.write('Variable: eflx_sh_tot; unit: W/m2.\n')
    f.write('Simulation period: 2018-10-01 to 2019-09-30.\n')
    f.write('Daily means are calculated from uniformly spaced hourly outputs.\n')
    f.write('Spatial statistics describe annual or seasonal mean fields, not hourly extrema.\n')
    f.write('Missing values are excluded; seasonal fields average valid daily means equally.\n')
    f.write('Spatial arrays are vertically flipped relative to the original PFB arrays.\n')
    f.write('No study-area mask is applied; regional means give equal weights to finite cells.\n')
    f.write('GIF limits are the 2nd and 98th percentiles of all hourly spatial values.\n')
    f.write('Colour limits affect visualisation only; negative fluxes are retained.\n\n')
    f.write('Annual\n')
    f.write(f'min  = {annual_stats[0]:.6f} W/m2\n')
    f.write(f'max  = {annual_stats[1]:.6f} W/m2\n')
    f.write(f'mean = {annual_stats[2]:.6f} W/m2\n\n')
    f.write('Non-flood season (October-June; 273 days)\n')
    f.write(f'min  = {nonflood_stats[0]:.6f} W/m2\n')
    f.write(f'max  = {nonflood_stats[1]:.6f} W/m2\n')
    f.write(f'mean = {nonflood_stats[2]:.6f} W/m2\n\n')
    f.write('Flood season (July-September; 92 days)\n')
    f.write(f'min  = {flood_stats[0]:.6f} W/m2\n')
    f.write(f'max  = {flood_stats[1]:.6f} W/m2\n')
    f.write(f'mean = {flood_stats[2]:.6f} W/m2\n')

# Save named rows for the annual and seasonal statistics.
stats_csv = os.path.join(
    output_dir, f'{scenario_name}_regional_sensible_heat_flux_statistics.csv'
)
stats_table = np.array([annual_stats, nonflood_stats, flood_stats])
np.savetxt(
    stats_csv,
    np.column_stack((['annual', 'nonflood', 'flood'], stats_table)),
    delimiter=',',
    header='period,spatial_min_Wm2,spatial_max_Wm2,spatial_mean_Wm2',
    comments='',
    fmt='%s'
)

# ============================================================
# 8. Report numerical checks and output paths
# ============================================================

print('\nCalculation completed.')
print('Daily mean eflx_sh_tot: spatial-temporal min:', np.nanmin(sh_stack))
print('Daily mean eflx_sh_tot: spatial-temporal max:', np.nanmax(sh_stack))
print('Daily mean eflx_sh_tot: spatial-temporal mean:', np.nanmean(sh_stack))
print('Annual mean sensible heat flux: spatial min:', annual_stats[0])
print('Annual mean sensible heat flux: spatial max:', annual_stats[1])
print('Annual mean sensible heat flux: spatial mean:', annual_stats[2])
print('\nOutput files:')
print(npy_path)
print(gif_path)
print(annual_spatial_csv)
print(nonflood_spatial_csv)
print(flood_spatial_csv)
print(stats_txt)
print(stats_csv)
print(hourly_mean_npy)
print(hourly_mean_csv)
