import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
import glob

stations = ["1shenmu", "2gaojiabao", "3zhaoshiyao", "4hanjiamao", "5hengshan", "6dianshi"]
base_dir = "./2_q_outputs/"
obs_file = "./2_q_observation.csv"

df_obs = pd.read_csv(obs_file, encoding='gb18030')

for st in stations:
    station_dir = os.path.join(base_dir, st)

    txt_files = glob.glob(os.path.join(station_dir, "*.txt"))

    print(f"\n📁 处理站点: {st} (找到 {len(txt_files)} 个txt文件)")

    for txt_path in txt_files:
        file_basename = os.path.splitext(os.path.basename(txt_path))[0]

        print(f"   处理文件: {file_basename}.txt")

        df_txt = pd.read_csv(txt_path, sep=None, engine='python')
        df_txt.columns = df_txt.columns.str.strip()

        if 'Flow(cms)' in df_txt.columns:
            col_name = 'Flow(cms)'
        else:
            col_name = df_txt.columns[0]

        sim_values = df_txt[col_name].astype(float)[1:].reset_index(drop=True)

        hours_per_day = 24
        n_days = len(sim_values) // hours_per_day
        sim_daily_avg = sim_values[:n_days * hours_per_day].values.reshape(n_days, hours_per_day).mean(axis=1)

        obs_values = df_obs[st].iloc[0:n_days].astype(float).reset_index(drop=True)

        df_out = pd.DataFrame({
            'Day': np.arange(1, n_days + 1),
            'obs': obs_values,
            'sim': sim_daily_avg
        })
        csv_out_path = os.path.join(station_dir, f"{file_basename}.csv")
        df_out.to_csv(csv_out_path, index=False, encoding='utf-8-sig')

        obs = df_out['obs'].values
        sim = df_out['sim'].values

        # Bias
        bias = np.mean(sim - obs)

        # Pearson
        pearson_r = np.corrcoef(obs, sim)[0, 1] if np.std(obs) > 0 and np.std(sim) > 0 else np.nan

        # Spearman
        srho, _ = spearmanr(obs, sim)

        # RSR = RMSE / std(obs)
        rmse = np.sqrt(np.mean((sim - obs) ** 2))
        rsr = rmse / np.std(obs) if np.std(obs) > 0 else np.nan

        plt.figure(figsize=(10, 4))
        plt.plot(df_out['Day'], df_out['obs'], label='Obs', color='blue')
        plt.plot(df_out['Day'], df_out['sim'], label='Sim', color='red')
        plt.xlabel('Day')
        plt.ylabel('Flow (cms)')
        plt.title(f'{st} - {file_basename} Daily Average')
        plt.grid(True)
        plt.legend()

        text_str = (f"Bias = {bias:.3f}\n"
                    f"Pearson r = {pearson_r:.3f}\n"
                    f"Spearman ρ = {srho:.3f}\n"
                    f"RSR = {rsr:.3f}")
        plt.text(0.02, 0.95, text_str, transform=plt.gca().transAxes,
                 fontsize=11, verticalalignment="top",
                 bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.7))

        plt.tight_layout()
        png_out_path = os.path.join(station_dir, f"{file_basename}.png")
        plt.savefig(png_out_path, dpi=150)
        plt.close()

        print(f"     ✓ 已生成: {file_basename}.csv 和 {file_basename}.png")

print("\n✅ 所有站点的所有txt文件处理完成！")