import os
import numpy as np
import re
import glob
import matplotlib.pyplot as plt
import imageio
from parflow.tools.io import read_pfb
from parflow.tools.hydrology import calculate_water_table_depth

# ===== 1. working path =====
#os.chdir("run_1")
dz = np.array([98.00, 50.00, 30.00, 20.00, 1.00, 0.40, 0.30, 0.15, 0.10, 0.05])

output_dir = '1_wtd_outputs'
os.makedirs(output_dir, exist_ok=True)
print("Path", os.getcwd())

# ===== 2. read pfb files =====
pressure_files = sorted(glob.glob('run_1/mao.out.press.*.pfb'))
saturation_files = sorted(glob.glob('run_1/mao.out.satur.*.pfb'))

def extract_step_number(f):
    match = re.search(r'\.(\d{5})\.pfb$', f)
    return int(match.group(1)) if match else -1

pressure_files = sorted(pressure_files, key=extract_step_number)
saturation_files = sorted(saturation_files, key=extract_step_number)

pressure_files = pressure_files[1:]
saturation_files = saturation_files[1:]

print(f"Pressure file number: {len(pressure_files)}, Saturation file number: {len(saturation_files)}")
assert len(pressure_files) >= 8760 and len(saturation_files) >= 8760, "file number ＜ 8760 对"

# ===== 3. initialization =====
n_days = 365
extent = [0, 330, 0, 200]
vmin, vmax = 0, 200
daily_wtd_list = []
frames = []

# ===== 4. The main loop processes the daily WTD =====
for day in range(n_days):
    print(f" {day+1} ")

    wtd_24h = []
    for hour in range(24):
        idx = day * 24 + hour
        press_file = pressure_files[idx]
        satur_file = saturation_files[idx]

        pressure = read_pfb(press_file)
        saturation = read_pfb(satur_file)

        assert pressure.shape[0] == dz.shape[0], f"{press_file} The number of layers does not match dz"
        wtd = calculate_water_table_depth(pressure, saturation, dz)
        wtd_24h.append(wtd)

    # Daily average
    wtd_day = np.mean(np.stack(wtd_24h), axis=0)
    wtd_day_flipped = np.flipud(wtd_day)
    daily_wtd_list.append(wtd_day_flipped)

    fig, ax = plt.subplots()
    im = ax.imshow(wtd_day_flipped, cmap='turbo', extent=extent, vmin=vmin, vmax=vmax)
    plt.colorbar(im, ax=ax, label='Water Table Depth (m)')
    ax.set_title(f'WTD Day {day+1}')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    fig.canvas.draw()

    frame = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
    frame = frame.reshape(fig.canvas.get_width_height()[::-1] + (3,))
    frames.append(frame)
    plt.close()

# ===== 5. Save the.npy and.gif files =====
wtd_stack = np.stack(daily_wtd_list)  # (365, ny, nx)
np.save(os.path.join(output_dir, 'WTD_daily_all.npy'), wtd_stack)

gif_path = os.path.join(output_dir, 'WTD_daily.gif')
imageio.mimsave(gif_path, frames, duration=0.8)

print("✅ finished")
#os.chdir("..")