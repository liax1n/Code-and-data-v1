import os
import re
import glob
import numpy as np
import matplotlib.pyplot as plt
from parflow.tools.io import read_pfb

# ============================================================
# 1. Basic settings: process only the current scenario
# ============================================================

run_dir = './run_1'
scenario_name = 'current_scenario'

output_dir = '7_1_gradient_darcy'
os.makedirs(output_dir, exist_ok=True)

n_steps = 8760

# File layers 7 and 6
layer7_idx = 6
layer6_idx = 5

# Layer-center depths: 0.40 m and 0.75 m below the land surface
z_layer7 = -0.40
z_layer6 = -0.75
dz_between_layers = abs(z_layer7 - z_layer6)

print("Current working directory:", os.getcwd())
print("Output directory:", output_dir)


def extract_step_number(f):
    match = re.search(r'\.(\d{5})\.pfb$', f)
    return int(match.group(1)) if match else -1


# ============================================================
# 2. Read pressure files for the current scenario
# ============================================================

pressure_files = sorted(
    glob.glob(os.path.join(run_dir, 'mao.out.press.*.pfb')),
    key=extract_step_number
)

# Exclude the initial output at timestep 00000
pressure_files = [f for f in pressure_files if extract_step_number(f) > 0]

print(f"Number of pressure files: {len(pressure_files)}")
assert len(pressure_files) >= n_steps, f"Fewer than {n_steps} files available"

pressure_files = pressure_files[:n_steps]


# ============================================================
# 3. Initialize arrays
# ============================================================

sample = read_pfb(pressure_files[0])
nz, ny, nx = sample.shape

sum_press_layer7 = np.zeros((ny, nx), dtype=np.float64)
sum_press_layer6 = np.zeros((ny, nx), dtype=np.float64)

# Retain values for statistical analysis without exporting the time series
hourly_regional_mean_gradient = []


# ============================================================
# 4. Accumulate pressure heads in layers 7 and 6 over all timesteps
#    and calculate the hourly regional mean upward gradient
# ============================================================

for i, f in enumerate(pressure_files):
    press = read_pfb(f)

    press_layer7 = press[layer7_idx, :, :]
    press_layer6 = press[layer6_idx, :, :]

    sum_press_layer7 += press_layer7
    sum_press_layer6 += press_layer6

    # Calculate hourly total hydraulic heads
    total_head_layer7_hourly = press_layer7 + z_layer7
    total_head_layer6_hourly = press_layer6 + z_layer6

    # Calculate the hourly total-head gradient
    total_head_gradient_hourly = (
        total_head_layer7_hourly - total_head_layer6_hourly
    ) / (z_layer7 - z_layer6)

    # Positive values indicate an upward hydraulic driving force
    upward_gradient_hourly = -total_head_gradient_hourly

    # Calculate the hourly regional mean for statistical analysis
    hourly_regional_mean_gradient.append(
        np.nanmean(upward_gradient_hourly)
    )

    if (i + 1) % 500 == 0:
        print(f"Processed {i + 1}/{len(pressure_files)} files")


# ============================================================
# 5. Calculate annual mean pressure heads
# ============================================================

mean_press_layer7 = sum_press_layer7 / len(pressure_files)
mean_press_layer6 = sum_press_layer6 / len(pressure_files)


# ============================================================
# 6. Calculate the annual mean total-head gradient
# ============================================================
# press = pressure head ψ
# total head h = ψ + z

total_head_layer7 = mean_press_layer7 + z_layer7
total_head_layer6 = mean_press_layer6 + z_layer6

# dh/dz = (h_upper - h_lower) / (z_upper - z_lower)
total_head_gradient = (
    total_head_layer7 - total_head_layer6
) / (z_layer7 - z_layer6)

# Define positive values as indicating an upward hydraulic driving force
upward_hydraulic_gradient_proxy = -total_head_gradient


# ============================================================
# 7. Export one three-layer NPY array and three CSV files
# ============================================================

stacked_output = np.stack(
    [
        mean_press_layer7,
        mean_press_layer6,
        upward_hydraulic_gradient_proxy
    ],
    axis=0
)

npy_path = os.path.join(
    output_dir,
    f'{scenario_name}_annual_head_gradient_3layers.npy'
)

np.save(npy_path, stacked_output)

csv_layer7 = os.path.join(
    output_dir,
    f'{scenario_name}_mean_press_layer7_center_0p40m.csv'
)

csv_layer6 = os.path.join(
    output_dir,
    f'{scenario_name}_mean_press_layer6_center_0p75m.csv'
)

csv_gradient = os.path.join(
    output_dir,
    f'{scenario_name}_upward_hydraulic_gradient_proxy.csv'
)

np.savetxt(csv_layer7, mean_press_layer7, delimiter=',')
np.savetxt(csv_layer6, mean_press_layer6, delimiter=',')
np.savetxt(csv_gradient, upward_hydraulic_gradient_proxy, delimiter=',')


# ============================================================
# 8. Generate spatial maps
# ============================================================

def plot_map(data, title, out_png, cmap='RdBu_r', symmetric=True):
    plt.figure(figsize=(8, 5))

    if symmetric:
        vmax = np.nanpercentile(np.abs(data), 98)
        vmin = -vmax
    else:
        vmin = np.nanpercentile(data, 2)
        vmax = np.nanpercentile(data, 98)

    im = plt.imshow(
        data,
        origin='lower',
        cmap=cmap,
        vmin=vmin,
        vmax=vmax
    )

    plt.colorbar(im, shrink=0.8, label='Upward hydraulic gradient proxy')
    plt.title(title)
    plt.xlabel('X grid')
    plt.ylabel('Y grid')
    plt.tight_layout()
    plt.savefig(out_png, dpi=300)
    plt.close()


png_layer7 = os.path.join(
    output_dir,
    f'{scenario_name}_mean_press_layer7_0p40m.png'
)

png_layer6 = os.path.join(
    output_dir,
    f'{scenario_name}_mean_press_layer6_0p75m.png'
)

png_gradient = os.path.join(
    output_dir,
    f'{scenario_name}_upward_hydraulic_gradient_proxy.png'
)

plot_map(
    mean_press_layer7,
    'Annual mean pressure head at layer 7 center depth 0.40 m',
    png_layer7,
    cmap='viridis',
    symmetric=False
)

plot_map(
    mean_press_layer6,
    'Annual mean pressure head at layer 6 center depth 0.75 m',
    png_layer6,
    cmap='viridis',
    symmetric=False
)

plot_map(
    upward_hydraulic_gradient_proxy,
    'Annual mean upward hydraulic gradient proxy',
    png_gradient,
    cmap='RdBu_r',
    symmetric=True
)


# ============================================================
# 9. Calculate annual, non-flood-season, and flood-season statistics
#    and export TXT and CSV summaries
# ============================================================

hourly_regional_mean_gradient = np.array(hourly_regional_mean_gradient)

split_hour = len(hourly_regional_mean_gradient) // 2

annual_arr = hourly_regional_mean_gradient
non_flood_arr = hourly_regional_mean_gradient[:split_hour]
flood_arr = hourly_regional_mean_gradient[split_hour:]


def calc_stats(arr):
    return (
        np.nanmin(arr),
        np.nanmax(arr),
        np.nanmean(arr)
    )


annual_stats = calc_stats(annual_arr)
nonflood_stats = calc_stats(non_flood_arr)
flood_stats = calc_stats(flood_arr)

print("\n==============================")
print("Upward hydraulic gradient proxy statistics")
print("==============================")

print("\nAnnual")
print(f"min  = {annual_stats[0]:.6f}")
print(f"max  = {annual_stats[1]:.6f}")
print(f"mean = {annual_stats[2]:.6f}")

print("\nNon-flood season (first half of the simulation period)")
print(f"min  = {nonflood_stats[0]:.6f}")
print(f"max  = {nonflood_stats[1]:.6f}")
print(f"mean = {nonflood_stats[2]:.6f}")

print("\nFlood season (second half of the simulation period)")
print(f"min  = {flood_stats[0]:.6f}")
print(f"max  = {flood_stats[1]:.6f}")
print(f"mean = {flood_stats[2]:.6f}")

# ---------- Export the TXT summary ----------
stats_txt = os.path.join(
    output_dir,
    f'{scenario_name}_regional_upward_hydraulic_gradient_statistics.txt'
)

with open(stats_txt, 'w', encoding='utf-8') as f:
    f.write("Upward hydraulic gradient proxy statistics\n")
    f.write("Variable: vertical total-head gradient between 0.40 m and 0.75 m\n")
    f.write("Definition: positive values indicate stronger upward hydraulic driving force\n")
    f.write("Unit: dimensionless hydraulic gradient\n\n")

    f.write("Annual\n")
    f.write(f"min  = {annual_stats[0]:.6f}\n")
    f.write(f"max  = {annual_stats[1]:.6f}\n")
    f.write(f"mean = {annual_stats[2]:.6f}\n\n")

    f.write("Non-flood season (first half of the simulation period)\n")
    f.write(f"min  = {nonflood_stats[0]:.6f}\n")
    f.write(f"max  = {nonflood_stats[1]:.6f}\n")
    f.write(f"mean = {nonflood_stats[2]:.6f}\n\n")

    f.write("Flood season (second half of the simulation period)\n")
    f.write(f"min  = {flood_stats[0]:.6f}\n")
    f.write(f"max  = {flood_stats[1]:.6f}\n")
    f.write(f"mean = {flood_stats[2]:.6f}\n")

# ---------- Export the CSV summary ----------
stats_csv = os.path.join(
    output_dir,
    f'{scenario_name}_regional_upward_hydraulic_gradient_statistics.csv'
)

stats_table = np.array([
    annual_stats,
    nonflood_stats,
    flood_stats
])

np.savetxt(
    stats_csv,
    stats_table,
    delimiter=',',
    header='min,max,mean',
    comments=''
)


# ============================================================
# 10. Report numerical checks and output paths
# ============================================================

print("\nCalculation completed.")
print("mean_press_layer7 (annual mean pressure head: minimum and maximum):",
      np.nanmin(mean_press_layer7), np.nanmax(mean_press_layer7))
print("mean_press_layer6 (annual mean pressure head: minimum and maximum):",
      np.nanmin(mean_press_layer6), np.nanmax(mean_press_layer6))
print("upward_hydraulic_gradient_proxy (annual mean field: spatial minimum and maximum):",
      np.nanmin(upward_hydraulic_gradient_proxy),
      np.nanmax(upward_hydraulic_gradient_proxy))
print("Gradient spatial mean:",
      np.nanmean(upward_hydraulic_gradient_proxy))

print("\nOutput files:")
print(npy_path)
print(csv_layer7)
print(csv_layer6)
print(csv_gradient)
print(png_layer7)
print(png_layer6)
print(png_gradient)
print(stats_txt)
print(stats_csv)

print("\n✅ Saved the annual mean upward hydraulic gradient spatial field.")
print("✅ Saved regional_upward_hydraulic_gradient_statistics.txt")
print("✅ Saved regional_upward_hydraulic_gradient_statistics.csv")