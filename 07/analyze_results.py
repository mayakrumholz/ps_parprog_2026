#!/usr/bin/env python3

import csv
import os
import statistics
import sys
from collections import defaultdict


class RunResult:
    def __init__(self, bench_case, variant, n, repetitions, threads, run, elapsed_seconds, checksum):
        self.bench_case = bench_case
        self.variant = variant
        self.n = n
        self.repetitions = repetitions
        self.threads = threads
        self.run = run
        self.elapsed_seconds = elapsed_seconds
        self.checksum = checksum


class Summary:
    def __init__(
        self,
        bench_case,
        variant,
        threads,
        n,
        repetitions,
        runs,
        mean_seconds,
        median_seconds,
        stdev_seconds,
        speedup_vs_original_1t,
        efficiency_vs_original_1t,
    ):
        self.bench_case = bench_case
        self.variant = variant
        self.threads = threads
        self.n = n
        self.repetitions = repetitions
        self.runs = runs
        self.mean_seconds = mean_seconds
        self.median_seconds = median_seconds
        self.stdev_seconds = stdev_seconds
        self.speedup_vs_original_1t = speedup_vs_original_1t
        self.efficiency_vs_original_1t = efficiency_vs_original_1t


def load_results(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as handle:
        rows = []
        reader = csv.DictReader(handle)
        required = {"case", "variant", "n", "repetitions", "threads", "run", "elapsed_seconds", "checksum"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"{csv_path} misses required columns: {sorted(required)}")

        for row in reader:
            rows.append(RunResult(
                bench_case=row["case"],
                variant=row["variant"],
                n=int(row["n"]),
                repetitions=int(row["repetitions"]),
                threads=int(row["threads"]),
                run=int(row["run"]),
                elapsed_seconds=float(row["elapsed_seconds"]),
                checksum=float(row["checksum"]),
            ))

    if not rows:
        raise ValueError(f"{csv_path} contains no benchmark rows")
    return rows


def summarize(results):
    grouped = defaultdict(list)
    baselines = {}

    for result in results:
        grouped[(result.bench_case, result.variant, result.threads)].append(result)

    for (bench_case, variant, threads), runs in grouped.items():
        if variant == "original" and threads == 1:
            baselines[bench_case] = statistics.fmean(run.elapsed_seconds for run in runs)

    summaries = []
    for key in sorted(grouped):
        bench_case, variant, threads = key
        runs = grouped[key]
        times = [run.elapsed_seconds for run in runs]
        mean_seconds = statistics.fmean(times)
        baseline = baselines[bench_case]
        summaries.append(
            Summary(
                bench_case=bench_case,
                variant=variant,
                threads=threads,
                n=runs[0].n,
                repetitions=runs[0].repetitions,
                runs=len(runs),
                mean_seconds=mean_seconds,
                median_seconds=statistics.median(times),
                stdev_seconds=statistics.stdev(times) if len(times) > 1 else 0.0,
                speedup_vs_original_1t=baseline / mean_seconds,
                efficiency_vs_original_1t=(baseline / mean_seconds) / threads,
            )
        )

    return summaries


def write_summary_csv(path, summaries):
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "case",
                "variant",
                "threads",
                "n",
                "repetitions",
                "runs",
                "mean_seconds",
                "median_seconds",
                "stdev_seconds",
                "speedup_vs_original_1t",
                "efficiency_vs_original_1t",
            ]
        )
        for summary in summaries:
            writer.writerow(
                [
                    summary.bench_case,
                    summary.variant,
                    summary.threads,
                    summary.n,
                    summary.repetitions,
                    summary.runs,
                    f"{summary.mean_seconds:.6f}",
                    f"{summary.median_seconds:.6f}",
                    f"{summary.stdev_seconds:.6f}",
                    f"{summary.speedup_vs_original_1t:.6f}",
                    f"{summary.efficiency_vs_original_1t:.6f}",
                ]
            )


def write_summary_markdown(path, summaries):
    lines = [
        "# Exercise 2 Benchmark Summary",
        "",
    ]
    for bench_case in sorted({summary.bench_case for summary in summaries}):
        lines.extend(
            [
                f"## Case {bench_case}",
                "",
                "| Variant | Threads | n | Repetitions | Runs | Mean [s] | Median [s] | Stddev [s] | Speedup | Efficiency |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for summary in [item for item in summaries if item.bench_case == bench_case]:
            lines.append(
                f"| {summary.variant} | {summary.threads} | {summary.n} | {summary.repetitions} | {summary.runs} | "
                f"{summary.mean_seconds:.6f} | {summary.median_seconds:.6f} | {summary.stdev_seconds:.6f} | "
                f"{summary.speedup_vs_original_1t:.3f} | {summary.efficiency_vs_original_1t:.3f} |"
            )
        lines.append("")

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def svg_header(width, height):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        '<rect width="100%" height="100%" fill="#f6f3ee"/>',
        "<style>",
        'text { font-family: "Helvetica", "Arial", sans-serif; fill: #1f2937; }',
        ".title { font-size: 22px; font-weight: 700; }",
        ".subtitle { font-size: 12px; fill: #4b5563; }",
        ".axis { stroke: #374151; stroke-width: 1.2; }",
        ".grid { stroke: #d1d5db; stroke-width: 1; stroke-dasharray: 4 4; }",
        ".tick { font-size: 11px; fill: #4b5563; }",
        ".label { font-size: 12px; }",
        ".legend { font-size: 12px; }",
        "</style>",
    ]


def map_x(index, count, left, width):
    if count <= 1:
        return left + width / 2.0
    return left + index * width / (count - 1)


def map_y(value, max_value, top, height):
    if max_value <= 0.0:
        return top + height
    return top + height - (value / max_value) * height


def write_case_plot(summaries, bench_case, output_path, field, title, ylabel):
    width, height = 980, 620
    left, top = 80.0, 90.0
    plot_width, plot_height = 760.0, 420.0
    thread_counts = sorted({summary.threads for summary in summaries if summary.bench_case == bench_case})
    variants = ["original", "parallel"]
    grouped = {(summary.variant, summary.threads): summary for summary in summaries if summary.bench_case == bench_case}
    colors = {"original": "#b45309", "parallel": "#2563eb"}
    values = [getattr(grouped[(variant, threads)], field) for variant in variants for threads in thread_counts]
    max_value = max(values) * 1.1

    elements = svg_header(width, height)
    elements.append(f'<text class="title" x="80" y="48">{title}</text>')
    elements.append(f'<text class="subtitle" x="80" y="68">Case {bench_case}</text>')

    for step in range(6):
        value = max_value * step / 5.0
        y = map_y(value, max_value, top, plot_height)
        elements.append(f'<line class="grid" x1="{left:.1f}" y1="{y:.1f}" x2="{left + plot_width:.1f}" y2="{y:.1f}"/>')
        elements.append(f'<text class="tick" x="{left - 8:.1f}" y="{y + 4:.1f}" text-anchor="end">{value:.2f}</text>')

    elements.append(f'<line class="axis" x1="{left:.1f}" y1="{top + plot_height:.1f}" x2="{left + plot_width:.1f}" y2="{top + plot_height:.1f}"/>')
    elements.append(f'<line class="axis" x1="{left:.1f}" y1="{top:.1f}" x2="{left:.1f}" y2="{top + plot_height:.1f}"/>')

    for idx, threads in enumerate(thread_counts):
        x = map_x(idx, len(thread_counts), left, plot_width)
        elements.append(f'<text class="tick" x="{x:.1f}" y="{top + plot_height + 24:.1f}" text-anchor="middle">{threads}</text>')

    for variant in variants:
        points = []
        for idx, threads in enumerate(thread_counts):
            x = map_x(idx, len(thread_counts), left, plot_width)
            value = getattr(grouped[(variant, threads)], field)
            y = map_y(value, max_value, top, plot_height)
            points.append(f"{x:.1f},{y:.1f}")
            elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{colors[variant]}"/>')
        elements.append(f'<polyline fill="none" stroke="{colors[variant]}" stroke-width="3" points="{" ".join(points)}"/>')

    elements.append(f'<text class="label" x="{left + plot_width / 2:.1f}" y="{height - 40:.1f}" text-anchor="middle">Threads</text>')
    elements.append(f'<text class="label" x="26" y="{top + plot_height / 2:.1f}" transform="rotate(-90 26 {top + plot_height / 2:.1f})" text-anchor="middle">{ylabel}</text>')

    legend_x = 700
    legend_y = 48
    for idx, variant in enumerate(variants):
        y = legend_y + idx * 22
        elements.append(f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 28}" y2="{y}" stroke="{colors[variant]}" stroke-width="3"/>')
        elements.append(f'<circle cx="{legend_x + 14}" cy="{y}" r="4.5" fill="{colors[variant]}"/>')
        elements.append(f'<text class="legend" x="{legend_x + 38}" y="{y + 4}">{variant}</text>')

    elements.append("</svg>")
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(elements))


def main():
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <results/time_results.csv>", file=sys.stderr)
        return 1

    csv_path = sys.argv[1]
    results = load_results(csv_path)
    summaries = summarize(results)
    results_dir = os.path.dirname(csv_path)
    plots_dir = os.path.join(results_dir, "plots")
    ensure_dir(plots_dir)

    write_summary_csv(os.path.join(results_dir, "summary_stats.csv"), summaries)
    write_summary_markdown(os.path.join(results_dir, "summary_table.md"), summaries)

    for bench_case in sorted({summary.bench_case for summary in summaries}):
        write_case_plot(
            summaries,
            bench_case,
            os.path.join(plots_dir, f"{bench_case}_runtime.svg"),
            "mean_seconds",
            "Runtime by Thread Count",
            "Runtime [s]",
        )
        write_case_plot(
            summaries,
            bench_case,
            os.path.join(plots_dir, f"{bench_case}_speedup.svg"),
            "speedup_vs_original_1t",
            "Speedup vs Original 1 Thread",
            "Speedup",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
