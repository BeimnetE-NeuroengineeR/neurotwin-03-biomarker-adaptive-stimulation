import os
import re
import subprocess
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


def parse_summary(line: str) -> dict:
    match = re.search(
        r"Threshold=([0-9.]+)\s+Mean_Biomarker=([0-9.]+)\s+Duty_Cycle=([0-9.]+)\s+Mean_Stim=([0-9.]+)",
        line,
    )
    if not match:
        raise ValueError(f"Could not parse stimulation summary line: {line}")
    return {
        "Threshold": float(match.group(1)),
        "Mean_Biomarker": float(match.group(2)),
        "Duty_Cycle": float(match.group(3)),
        "Mean_Stim": float(match.group(4)),
    }


def main():
    print("Running Project 3: C++17 Biomarker Adaptive Stimulation Sweep...")
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cpp_src = os.path.join(repo_root, "src/adaptive_stimulation.cpp")
    cpp_bin = os.path.join(repo_root, "src/adaptive_stimulation")
    results_dir = os.path.join(repo_root, "results")
    figures_dir = os.path.join(repo_root, "figures")
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(figures_dir, exist_ok=True)

    subprocess.run(
        ["clang++", "-std=c++17", "-O2", cpp_src, "-o", cpp_bin],
        check=True,
    )

    thresholds = [0.06, 0.10, 0.14, 0.18, 0.22]
    rows = []

    for th in thresholds:
        proc = subprocess.run(
            [cpp_bin, str(th), "1.50", "400", "0.02"],
            capture_output=True,
            text=True,
            check=True,
        )
        rows.append(parse_summary(proc.stdout.strip()))

    df = pd.DataFrame(rows)
    sweep_csv = os.path.join(results_dir, "threshold_sweep.csv")
    df.to_csv(sweep_csv, index=False)

    traj_csv = os.path.join(results_dir, "trajectory_thresh0.14.csv")
    subprocess.run(
        [cpp_bin, "0.14", "1.50", "400", "0.02", traj_csv],
        capture_output=True,
        text=True,
        check=True,
    )
    tdf = pd.read_csv(traj_csv)
    time_s = tdf["Time_s"].to_numpy()
    biomarker = tdf["Biomarker_Level"].to_numpy()
    stim_drive = tdf["Stim_Drive"].to_numpy()

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), dpi=300)

    ax0 = axes[0]
    ax0.plot(df["Threshold"], df["Duty_Cycle"], marker="o", lw=1.8, label="Duty Cycle")
    ax0.plot(df["Threshold"], df["Mean_Stim"], marker="s", lw=1.8, linestyle="--", label="Mean Stimulation Drive")
    ax0.set_title("Adaptive Duty Cycle & Drive vs. Threshold")
    ax0.set_xlabel("Biomarker Threshold")
    ax0.set_ylabel("Fraction / Drive Amplitude")
    ax0.set_ylim(-0.02, 1.02)
    ax0.legend(loc="best")
    ax0.grid(True, linestyle=":", alpha=0.5)

    ax1 = axes[1]
    ax1.plot(time_s, biomarker, lw=1.8, label="Biomarker Level")
    ax1.plot(time_s, stim_drive, lw=1.6, linestyle="--", label="Adaptive Stim Drive")
    ax1.axhline(0.14, lw=1.1, linestyle=":", label="Threshold (0.14)")
    ax1.set_title("Closed-Loop Biomarker & Stimulation (Threshold = 0.14)")
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Amplitude")
    ax1.set_ylim(-0.02, 1.02)
    ax1.legend(loc="best")
    ax1.grid(True, linestyle=":", alpha=0.5)

    plt.tight_layout()
    out_png = os.path.join(figures_dir, "main_result.png")
    plt.savefig(out_png)

    print("\nBiomarker Threshold Sweep Results:")
    print(df.to_string(index=False))
    print("\nSaved sweep to results/threshold_sweep.csv and plot to figures/main_result.png!")


if __name__ == "__main__":
    main()
