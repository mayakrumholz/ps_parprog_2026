#!/usr/bin/env python3

import csv
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
            row["threads"] = int(row["threads"])
            row["run"] = int(row["run"])
            row["n"] = int(row["n"])
            row["cutoff"] = int(row["cutoff"])
            row["elapsed_seconds"] = float(row["elapsed_seconds"])
            rows.append(row)

    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["mode"], row["threads"], row["n"], row["cutoff"])].append(row)

    seq_baseline = {}
    summaries = []

    for key, group in sorted(grouped.items()):
        mode, threads, n, cutoff = key
        elapsed_values = [entry["elapsed_seconds"] for entry in group]
        summary = {
            "mode": mode,
            "threads": threads,
            "n": n,
            "cutoff": cutoff,
            "runs": len(group),
            "elapsed_mean": mean(elapsed_values),
            "elapsed_median": median(elapsed_values),
            "elapsed_stdev": stdev(elapsed_values),
            "result": group[0]["result"],
            "expected": group[0]["expected"],
        }
        if mode == "seq":
            seq_baseline[n] = summary["elapsed_mean"]
        summaries.append(summary)

    for summary in summaries:
        baseline = seq_baseline.get(summary["n"])
        if baseline is None or summary["elapsed_mean"] == 0.0:
            summary["speedup_vs_seq"] = ""
        else:
            summary["speedup_vs_seq"] = baseline / summary["elapsed_mean"]

    with summary_csv.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "mode",
                "threads",
                "n",
                "cutoff",
                "runs",
                "elapsed_mean",
                "elapsed_median",
                "elapsed_stdev",
                "speedup_vs_seq",
                "result",
                "expected",
            ]
        )
        for summary in summaries:
            writer.writerow(
                [
                    summary["mode"],
                    summary["threads"],
                    summary["n"],
                    summary["cutoff"],
                    summary["runs"],
                    f"{summary['elapsed_mean']:.6f}",
                    f"{summary['elapsed_median']:.6f}",
                    f"{summary['elapsed_stdev']:.6f}",
                    "" if summary["speedup_vs_seq"] == "" else f"{summary['speedup_vs_seq']:.6f}",
                    summary["result"],
                    summary["expected"],
                ]
            )

    with summary_md.open("w") as handle:
        handle.write("| Mode | Threads | N | Runs | Mean [s] | Median [s] | Stdev [s] | Speedup vs seq | Result |\n")
        handle.write("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n")
        for summary in summaries:
            speedup = "-" if summary["speedup_vs_seq"] == "" else f"{summary['speedup_vs_seq']:.3f}"
            handle.write(
                f"| {summary['mode']} | {summary['threads']} | {summary['n']} | {summary['runs']} | "
                f"{summary['elapsed_mean']:.6f} | {summary['elapsed_median']:.6f} | {summary['elapsed_stdev']:.6f} | "
                f"{speedup} | {summary['result']} |\n"
            )

    print(f"Wrote {summary_csv}")
    print(f"Wrote {summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
