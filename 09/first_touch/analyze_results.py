#!/usr/bin/env python3

import csv
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def mean(values):
    return sum(values) / len(values)


def median(values):
    return statistics.median(values)


def stdev(values):
    return statistics.stdev(values) if len(values) > 1 else 0.0


def fmt(value):
    return f"{value:.6f}"


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <time_results.csv>", file=sys.stderr)
        return 1

    csv_path = Path(sys.argv[1])
    results_dir = csv_path.parent
    summary_csv = results_dir / "summary_stats.csv"
    summary_md = results_dir / "summary_table.md"

    rows = []
    with csv_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            row["allocation_seconds"] = float(row["allocation_seconds"])
            row["initialization_seconds"] = float(row["initialization_seconds"])
            row["computation_seconds"] = float(row["computation_seconds"])
            row["deallocation_seconds"] = float(row["deallocation_seconds"])
            row["threads"] = int(row["threads"])
            row["run"] = int(row["run"])
            row["n"] = int(row["n"])
            row["total_seconds"] = (
                row["allocation_seconds"]
                + row["initialization_seconds"]
                + row["computation_seconds"]
                + row["deallocation_seconds"]
            )
            rows.append(row)

    grouped = defaultdict(list)
    for row in rows:
        key = (row["case"], row["init_mode"], row["schedule"], row["threads"], row["n"])
        grouped[key].append(row)

    summary_rows = []
    baseline_key = ("first_touch_bad", "serial", "static", 12, 40000)
    baseline = None

    for key, group in sorted(grouped.items()):
        computation_values = [entry["computation_seconds"] for entry in group]
        total_values = [entry["total_seconds"] for entry in group]
        summary = {
            "case": key[0],
            "init_mode": key[1],
            "schedule": key[2],
            "threads": key[3],
            "n": key[4],
            "runs": len(group),
            "allocation_mean": mean([entry["allocation_seconds"] for entry in group]),
            "initialization_mean": mean([entry["initialization_seconds"] for entry in group]),
            "computation_mean": mean(computation_values),
            "computation_median": median(computation_values),
            "computation_stdev": stdev(computation_values),
            "total_mean": mean(total_values),
        }
        if key == baseline_key:
            baseline = summary["computation_mean"]
        summary_rows.append(summary)

    if baseline is None:
        baseline = math.nan

    for row in summary_rows:
        if math.isnan(baseline) or row["computation_mean"] == 0.0:
            row["comparison_to_bad_static"] = math.nan
        else:
            row["comparison_to_bad_static"] = baseline / row["computation_mean"]

    with summary_csv.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "case",
                "init_mode",
                "schedule",
                "threads",
                "n",
                "runs",
                "allocation_mean",
                "initialization_mean",
                "computation_mean",
                "computation_median",
                "computation_stdev",
                "total_mean",
                "comparison_to_bad_static",
            ]
        )
        for row in summary_rows:
            writer.writerow(
                [
                    row["case"],
                    row["init_mode"],
                    row["schedule"],
                    row["threads"],
                    row["n"],
                    row["runs"],
                    fmt(row["allocation_mean"]),
                    fmt(row["initialization_mean"]),
                    fmt(row["computation_mean"]),
                    fmt(row["computation_median"]),
                    fmt(row["computation_stdev"]),
                    fmt(row["total_mean"]),
                    "" if math.isnan(row["comparison_to_bad_static"]) else fmt(row["comparison_to_bad_static"]),
                ]
            )

    with summary_md.open("w") as handle:
        handle.write("| Case | Init | Schedule | Threads | N | Runs | Init mean [s] | Compute mean [s] | Compute median [s] | Compute stdev [s] | Total mean [s] | Relative to bad static |\n")
        handle.write("| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n")
        for row in summary_rows:
            relative = "-" if math.isnan(row["comparison_to_bad_static"]) else f"{row['comparison_to_bad_static']:.3f}"
            handle.write(
                f"| {row['case']} | {row['init_mode']} | {row['schedule']} | {row['threads']} | {row['n']} | {row['runs']} | "
                f"{row['initialization_mean']:.6f} | {row['computation_mean']:.6f} | {row['computation_median']:.6f} | "
                f"{row['computation_stdev']:.6f} | {row['total_mean']:.6f} | {relative} |\n"
            )

    print(f"Wrote {summary_csv}")
    print(f"Wrote {summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
