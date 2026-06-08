#!/usr/bin/env python3
import csv
import statistics
import sys
from pathlib import Path


def median(values):
    return statistics.median(float(value) for value in values)


def main():
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} results/time_results.csv", file=sys.stderr)
        return 2

    csv_path = Path(sys.argv[1])
    out_dir = csv_path.parent
    rows = list(csv.DictReader(csv_path.open(newline="")))

    grouped = {}
    for row in rows:
        key = (row["variant"], int(row["threads"]))
        grouped.setdefault(key, []).append(row)

    summary_rows = []
    serial_time = median(row["wall_seconds"] for row in grouped[("serial", 1)])

    for key in sorted(grouped, key=lambda item: (item[0], item[1])):
        variant, threads = key
        values = grouped[key]
        wall = median(row["wall_seconds"] for row in values)
        benchmark = median(row["benchmark_seconds"] for row in values)
        speedup = serial_time / wall
        efficiency = speedup / threads
        summary_rows.append({
            "variant": variant,
            "threads": threads,
            "runs": len(values),
            "median_benchmark_seconds": benchmark,
            "median_wall_seconds": wall,
            "speedup_vs_serial_wall": speedup,
            "efficiency_vs_serial_wall": efficiency,
        })

    summary_path = out_dir / "summary.csv"
    with summary_path.open("w", newline="") as handle:
        fieldnames = [
            "variant",
            "threads",
            "runs",
            "median_benchmark_seconds",
            "median_wall_seconds",
            "speedup_vs_serial_wall",
            "efficiency_vs_serial_wall",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary_rows)

    markdown_path = out_dir / "summary.md"
    with markdown_path.open("w") as handle:
        handle.write("# Exercise 2 Results\n\n")
        handle.write("| Variant | Threads | Runs | Median benchmark time [s] | Median wall time [s] | Speedup | Efficiency |\n")
        handle.write("|---|---:|---:|---:|---:|---:|---:|\n")
        for row in summary_rows:
            handle.write(
                f"| {row['variant']} | {row['threads']} | {row['runs']} | "
                f"{row['median_benchmark_seconds']:.6f} | {row['median_wall_seconds']:.6f} | "
                f"{row['speedup_vs_serial_wall']:.3f} | {row['efficiency_vs_serial_wall']:.3f} |\n"
            )

    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print(f"Wrote {summary_path} and {markdown_path}. matplotlib is not available, skipping plots.")
        return 0

    openmp_rows = [row for row in summary_rows if row["variant"] == "openmp"]
    labels = ["serial"] + [f"omp {row['threads']}" for row in openmp_rows]
    wall_times = [serial_time] + [row["median_wall_seconds"] for row in openmp_rows]
    speedups = [1.0] + [row["speedup_vs_serial_wall"] for row in openmp_rows]
    efficiencies = [1.0] + [row["efficiency_vs_serial_wall"] for row in openmp_rows]

    plt.figure(figsize=(8, 4.5))
    plt.bar(labels, wall_times, color=["#4c566a"] + ["#2a9d8f"] * len(openmp_rows))
    plt.ylabel("Median wall time [s]")
    plt.xlabel("Configuration")
    plt.title("Assignment 12 Exercise 2: Wall Time")
    plt.tight_layout()
    plt.savefig(out_dir / "wall_time.png", dpi=160)
    plt.close()

    plt.figure(figsize=(8, 4.5))
    plt.plot(labels, speedups, marker="o", color="#264653", label="measured")
    ideal = [1.0] + [row["threads"] for row in openmp_rows]
    plt.plot(labels, ideal, linestyle="--", color="#8d99ae", label="ideal")
    plt.ylabel("Speedup vs. serial wall time")
    plt.xlabel("Configuration")
    plt.title("Assignment 12 Exercise 2: Speedup")
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_dir / "speedup.png", dpi=160)
    plt.close()

    plt.figure(figsize=(8, 4.5))
    plt.plot(labels, efficiencies, marker="o", color="#e76f51")
    plt.ylabel("Parallel efficiency")
    plt.xlabel("Configuration")
    plt.title("Assignment 12 Exercise 2: Efficiency")
    plt.ylim(bottom=0.0)
    plt.tight_layout()
    plt.savefig(out_dir / "efficiency.png", dpi=160)
    plt.close()

    print(f"Wrote {summary_path}, {markdown_path}, wall_time.png, speedup.png and efficiency.png.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
