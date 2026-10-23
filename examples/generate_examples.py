"""Reproduce the large synthetic CSV examples; requires only NumPy."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

SEED = 20261023
N = 5000
HARMONICS = [1, 3, 10]
PHASE_OFFSETS = [0.0, 0.4, 0.8]
PERIOD = 1000

CURVE_SPECS = [
    {"column": "slow_rising_snr20", "intercept": 10, "slope": 0.006, "amplitudes": [4, 1.8, 0.9], "phase": 0.0, "snr_db": 20},
    {"column": "fast_rising_snr12", "intercept": 25, "slope": 0.009, "amplitudes": [5, 2.4, 1.2], "phase": 0.5, "snr_db": 12},
    {"column": "falling_snr6", "intercept": 55, "slope": -0.005, "amplitudes": [4.5, 1.8, 1.0], "phase": 1.0, "snr_db": 6},
    {"column": "flat_snr10", "intercept": 65, "slope": 0.0, "amplitudes": [3, 1.5, 0.8], "phase": 0.8, "snr_db": 10},
    {"column": "gentle_rising_snr16", "intercept": 80, "slope": 0.002, "amplitudes": [5, 2.0, 1.0], "phase": 1.5, "snr_db": 16},
]

DISTRIBUTION_SPECS = [
    {"column": "single_peak", "weights": [0.7, 0.3], "means": [20, 22], "stds": [2, 3]},
    {"column": "bimodal", "weights": [0.55, 0.45], "means": [30, 39], "stds": [1.8, 2.4]},
    {"column": "trimodal", "weights": [0.30, 0.45, 0.25], "means": [44, 51, 58], "stds": [1.4, 1.8, 1.6]},
    {"column": "right_skewed", "weights": [0.8, 0.2], "means": [64, 73], "stds": [1.8, 3.0]},
    {"column": "heavy_tail", "weights": [0.9, 0.1], "means": [83, 83], "stds": [1.8, 7.0]},
]


def summaries(columns: list[str], data: np.ndarray) -> dict:
    result = {}
    for column, values in zip(columns, data.T):
        q1, median, q3 = np.quantile(values, [0.25, 0.5, 0.75])
        result[column] = {
            "n": int(values.size), "mean": float(values.mean()),
            "std_sample": float(values.std(ddof=1)), "min": float(values.min()),
            "q1": float(q1), "median": float(median), "q3": float(q3), "max": float(values.max()),
        }
    return result


def build_datasets() -> tuple[list[dict], dict]:
    rng = np.random.default_rng(SEED)
    row = np.arange(1, N + 1)
    t = row - 1
    curves = [row]
    measured_snr = {}
    for spec in CURVE_SPECS:
        harmonic = sum(
            amplitude * np.sin(2 * np.pi * k * t / PERIOD + k * spec["phase"] + offset)
            for k, amplitude, offset in zip(HARMONICS, spec["amplitudes"], PHASE_OFFSETS)
        )
        noise = rng.normal(size=N)
        noise -= noise.mean()
        signal_power = np.mean(harmonic ** 2)
        noise *= np.sqrt(signal_power / (10 ** (spec["snr_db"] / 10) * np.mean(noise ** 2)))
        values = spec["intercept"] + spec["slope"] * t + harmonic + noise
        values = np.round(values, 6)
        curves.append(values)
        residual = values - spec["intercept"] - spec["slope"] * t - harmonic
        measured_snr[spec["column"]] = float(10 * np.log10(signal_power / np.mean(residual ** 2)))
    curve_data = np.column_stack(curves)

    rng = np.random.default_rng(SEED + 1)
    distributions = []
    for spec in DISTRIBUTION_SPECS:
        counts = np.rint(np.asarray(spec["weights"]) * N).astype(int)
        assert counts.sum() == N
        values = np.concatenate([
            rng.normal(mean, std, size=int(count))
            for count, mean, std in zip(counts, spec["means"], spec["stds"])
        ])
        rng.shuffle(values)
        distributions.append(np.round(values, 6))
    distribution_data = np.column_stack(distributions)
    curve_columns = ["row"] + [spec["column"] for spec in CURVE_SPECS]
    distribution_columns = [spec["column"] for spec in DISTRIBUTION_SPECS]
    datasets = [
        {"path": "csvPLOT/experiment_curves.csv", "columns": curve_columns, "data": curve_data.tolist(), "integer_first_column": True},
        {"path": "csvFIG/experiment_distributions.csv", "columns": distribution_columns, "data": distribution_data.tolist(), "integer_first_column": False},
    ]
    metadata = {
        "synthetic": True, "rows_per_csv": N, "rounding_decimals": 6,
        "curves": {
            "path": datasets[0]["path"], "seed": SEED, "index": "row = 1..5000; t = row - 1",
            "model": "y = intercept + slope*t + sum(A_k*sin(2*pi*k*t/1000 + k*phase + phase_offset_k)) + noise",
            "harmonics": HARMONICS, "phase_offsets_rad": PHASE_OFFSETS, "fundamental_period_rows": PERIOD,
            "noise": "Gaussian noise, centered and scaled to the specified finite-sample power ratio",
            "snr_definition": "10*log10(mean(harmonic**2)/mean(noise**2)); excludes linear trend and intercept",
            "specifications": CURVE_SPECS, "measured_snr_db_after_rounding": measured_snr,
            "summary": summaries(curve_columns[1:], curve_data[:, 1:]),
        },
        "distributions": {
            "path": datasets[1]["path"], "seed": SEED + 1,
            "model": "Gaussian mixtures with exact component counts (weight*5000), independently shuffled per column",
            "row_meaning": "Each column is an independent population; rows do not identify paired subjects",
            "specifications": DISTRIBUTION_SPECS,
            "summary": summaries(distribution_columns, distribution_data),
        },
    }
    return datasets, metadata


def write_datasets(output: Path) -> None:
    datasets, metadata = build_datasets()
    for dataset in datasets:
        path = output / dataset["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(dataset["columns"])
            for row in dataset["data"]:
                writer.writerow([
                    str(int(value)) if index == 0 and dataset["integer_first_column"] else f"{value:.6f}"
                    for index, value in enumerate(row)
                ])
        print(f"Wrote {path}: {N} rows, {len(dataset['columns'])} columns")
    (output / "dataset_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--json", action="store_true", help="Emit numeric matrices and metadata without writing CSV files.")
    args = parser.parse_args()
    if args.json:
        datasets, metadata = build_datasets()
        print(json.dumps({"datasets": datasets, "metadata": metadata}))
    else:
        write_datasets(args.output_dir)


if __name__ == "__main__":
    main()
