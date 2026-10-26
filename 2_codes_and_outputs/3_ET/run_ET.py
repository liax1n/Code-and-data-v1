import os
import re
import glob
import numpy as np
import matplotlib.pyplot as plt
import imageio
from parflow.tools.io import read_pfb

# ===== 0. 基本设置 =====
output_dir = './3_ET_mmday'
os.makedirs(output_dir, exist_ok=True)

dt = 3600.0        # s（1 hour）
n_days = 365
extent = [0, 330, 0, 200]

print("Path", os.getcwd())

# ===== 1. read data =====
all_files = sorted(glob.glob("run_1/mao.out.qflx_evap_tot.*.pfb"))

def extract_step_number(f):
    m = re.search(r'\.(\d{5})\.pfb$', f)
    return int(m.group(1)) if m else -1

all_files = [f for f in all_files if 1 <= extract_step_number(f) <= 8760]
all_files.sort(key=extract_step_number)

daily_groups = [all_files[i*24:(i+1)*24] for i in range(n_days)]
print(f"共处理 {len(daily_groups)} 天（24 h/day）")

# ===== 2. =====
sample_days = []

for group in daily_groups[:10]:
    daily_sum = np.zeros_like(read_pfb(group[0])[0, :, :])

    for f in group:
        data = read_pfb(f)
        daily_sum += data[0, :, :] * dt   # mm

    sample_days.append(daily_sum)

sample_stack = np.stack(sample_days)
vmin = np.percentile(sample_stack, 2)
vmax = np.percentile(sample_stack, 98)

print(f"📊（mm/day）：vmin={vmin:.2f}, vmax={vmax:.2f}")

# ===== 3. Calculating =====
daily_et_list = []
frames = []

for day_idx, group in enumerate(daily_groups, start=1):
    print(f" {day_idx} Day")

    daily_sum = np.zeros_like(read_pfb(group[0])[0, :, :])

    for f in group:
        data = read_pfb(f)
        daily_sum += data[0, :, :] * dt   # mm/hour → mm

    daily_sum_flipped = np.flipud(daily_sum)
    daily_et_list.append(daily_sum_flipped)

    fig, ax = plt.subplots()
    vmin = 0
    vmax = 2
    im = ax.imshow(
        daily_sum_flipped,
        cmap='turbo',
        extent=extent,
        vmin=vmin,
        vmax=vmax
    )
    plt.colorbar(im, ax=ax, label='ET (mm/day)', shrink=0.8)
    ax.set_title(f'Daily ET (Day {day_idx})')
    ax.set_xlabel('X')
    ax.set_ylabel('Y')

    png_path = os.path.join(output_dir, f'ET_mmday_{day_idx:03d}.png')
    plt.savefig(png_path, dpi=150)
    frames.append(imageio.v3.imread(png_path))
    plt.close()

# ===== 4. 保存结果 =====
et_stack = np.stack(daily_et_list)   # (365, ny, nx)
np.save(os.path.join(output_dir, 'ET_daily_mmday.npy'), et_stack)

gif_path = os.path.join(output_dir, 'ET_daily_mmday.gif')
imageio.mimsave(gif_path, frames, duration=0.6)

print("✅ ET（mm/day）已完成")
