import csv
import os
import subprocess


def test_adaptive_stimulation_gate():
    print("Running Project 3 Sanity Check: C++17 Biomarker Adaptive Stimulation Engine...")
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    cpp_src = os.path.join(repo_root, "src/adaptive_stimulation.cpp")
    cpp_bin = os.path.join(repo_root, "src/adaptive_stimulation")
    out_csv = os.path.join(repo_root, "results/gate_stimulation.csv")
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)

    assert os.path.isfile(cpp_src), f"Missing C++ source at {cpp_src}"

    subprocess.run(
        ["clang++", "-std=c++17", "-O2", cpp_src, "-o", cpp_bin],
        check=True,
    )

    proc = subprocess.run(
        [cpp_bin, "0.14", "1.50", "300", "0.02", out_csv],
        capture_output=True,
        text=True,
        check=True,
    )
    print(proc.stdout.strip())

    assert os.path.isfile(out_csv), "Adaptive stimulation trajectory CSV was not created"
    with open(out_csv, newline="") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == 300, f"Expected 300 time steps, got {len(rows)}"
    for r in rows:
        for col in ("Biomarker_Level", "Stim_Drive", "Mean_State"):
            val = float(r[col])
            assert 0.0 <= val <= 1.0, f"{col} out of bounds: {val}"
        active_val = int(r["Active"])
        assert active_val in (0, 1), f"Invalid Active flag: {active_val}"

    os.remove(out_csv)
    print("Biomarker adaptive stimulation gate passed! All 300 trajectory samples valid.")


if __name__ == "__main__":
    test_adaptive_stimulation_gate()
