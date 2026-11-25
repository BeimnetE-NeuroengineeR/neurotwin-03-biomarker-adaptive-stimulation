#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <string>
#include <vector>

namespace fs = std::filesystem;

struct SimSample {
    int step;
    double time_s;
    double biomarker;
    double stim_drive;
    double mean_state;
    int active;
};

struct SweepMetrics {
    double mean_biomarker;
    double duty_cycle;
    double mean_stim;
    std::vector<SimSample> samples;
};

static double clamp_val(double v, double lo, double hi) {
    return std::max(lo, std::min(hi, v));
}

static SweepMetrics run_adaptive_simulation(
    double threshold,
    double stim_gain,
    int num_steps,
    double dt
) {
    const int steps = std::max(50, num_steps);
    const int n_units = 12;
    std::vector<double> state(n_units, 0.45);
    for (int i = 0; i < n_units; ++i) {
        state[i] = clamp_val(0.45 + 0.14 * std::sin(0.8 * i), 0.0, 1.0);
    }

    const double target_state = 0.45;
    double sum_biomarker = 0.0;
    double sum_stim = 0.0;
    int active_steps = 0;
    std::vector<SimSample> samples;
    samples.reserve(steps);

    for (int t = 0; t < steps; ++t) {
        const double time_s = t * dt;
        const double mean_s = [&]() {
            double acc = 0.0;
            for (double v : state) acc += v;
            return acc / static_cast<double>(n_units);
        }();

        // Biomarker captures excess deviation from target operating state + synchrony spread
        double variance = 0.0;
        for (double v : state) {
            const double d = v - mean_s;
            variance += d * d;
        }
        variance /= static_cast<double>(n_units);
        const double biomarker = clamp_val(std::abs(mean_s - target_state) + 1.8 * std::sqrt(variance), 0.0, 1.0);

        double stim_drive = 0.0;
        int is_active = 0;
        if (biomarker > threshold) {
            stim_drive = clamp_val(stim_gain * (biomarker - threshold), 0.0, 0.80);
            is_active = 1;
            ++active_steps;
        }

        // Periodic physiological/pathological perturbation bursts
        const double burst = 0.22 * std::sin(2.0 * 3.14159265358979323846 * 0.65 * time_s) *
                             (0.5 + 0.5 * std::sin(2.0 * 3.14159265358979323846 * 0.15 * time_s));

        std::vector<double> next_state(n_units, 0.0);
        for (int i = 0; i < n_units; ++i) {
            const double prev = state[(i + n_units - 1) % n_units];
            const double next = state[(i + 1) % n_units];
            const double coupling = 0.25 * (prev + next - 2.0 * state[i]);
            const double drive_sign = (state[i] >= target_state) ? -1.0 : 1.0;
            const double ds = -0.35 * (state[i] - target_state) + coupling + burst + drive_sign * stim_drive;
            next_state[i] = clamp_val(state[i] + ds * dt, 0.0, 1.0);
        }
        state.swap(next_state);

        samples.push_back(SimSample{t, time_s, biomarker, stim_drive, mean_s, is_active});
        sum_biomarker += biomarker;
        sum_stim += stim_drive;
    }

    SweepMetrics out;
    out.mean_biomarker = sum_biomarker / static_cast<double>(steps);
    out.duty_cycle = static_cast<double>(active_steps) / static_cast<double>(steps);
    out.mean_stim = sum_stim / static_cast<double>(steps);
    out.samples = std::move(samples);
    return out;
}

static void write_trajectory_csv(const std::vector<SimSample>& samples, const std::string& out_csv) {
    const fs::path p(out_csv);
    if (p.has_parent_path()) {
        fs::create_directories(p.parent_path());
    }
    std::ofstream ofs(out_csv);
    ofs << "Step,Time_s,Biomarker_Level,Stim_Drive,Mean_State,Active\n";
    ofs << std::fixed << std::setprecision(6);
    for (const auto& s : samples) {
        ofs << s.step << ","
            << std::setprecision(5) << s.time_s << ","
            << std::setprecision(6) << s.biomarker << ","
            << s.stim_drive << ","
            << s.mean_state << ","
            << s.active << "\n";
    }
}

int main(int argc, char** argv) {
    const double threshold = (argc >= 2) ? std::atof(argv[1]) : 0.14;
    const double stim_gain = (argc >= 3) ? std::atof(argv[2]) : 1.50;
    const int num_steps = (argc >= 4) ? std::atoi(argv[3]) : 400;
    const double dt = (argc >= 5) ? std::atof(argv[4]) : 0.02;
    const std::string out_csv = (argc >= 6) ? argv[5] : "";

    const SweepMetrics res = run_adaptive_simulation(threshold, stim_gain, num_steps, dt);

    std::printf(
        "Threshold=%.3f Mean_Biomarker=%.4f Duty_Cycle=%.4f Mean_Stim=%.4f\n",
        threshold,
        res.mean_biomarker,
        res.duty_cycle,
        res.mean_stim
    );

    if (!out_csv.empty()) {
        write_trajectory_csv(res.samples, out_csv);
    }
    return 0;
}
