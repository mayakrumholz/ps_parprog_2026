#!/usr/bin/env python3

import csv
import os
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass


@dataclass
class RunResult:
    variant: str
    threads: int
    run: int
    chunk: int
    elapsed_seconds: float
    image: str


@dataclass
class Summary:
    variant: str
    threads: int
    runs: int
    mean_seconds: float
    median_seconds: float
    min_seconds: float
    max_seconds: float
    stdev_seconds: float
    speedup_variant: float
    efficiency_variant: float


def load_results(csv_path: str) -> list[RunResult]:
    with open(csv_path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        required = {"variant", "threads", "run", "chunk", "elapsed_seconds", "image"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"{csv_path} misses required columns: {sorted(required)}")

        rows = [
            RunResult(
                variant=row["variant"],
                threads=int(row["threads"]),
                run=int(row["run"]),
                chunk=int(row["chunk"]),
                elapsed_seconds=float(row["elapsed_seconds"]),
                image=row["image"],
            )
            for row in reader
        ]

    if not rows:
        raise ValueError(f"{csv_path} does not contain any rows")

    return rows


def summarize(results: list[RunResult]) -> list[Summary]:
    grouped: dict[tuple[str, int], list[RunResult]] = defaultdict(list)
    baselines: dict[str, float] = {}

    for result in results:
        grouped[(result.variant, result.threads)].append(result)

    for (variant, threads), runs in grouped.items():
        if threads == 1:
            baselines[variant] = statistics.fmean(run.elapsed_seconds for run in runs)

    summaries = []
    for variant, threads in sorted(grouped):
        runs = grouped[(variant, threads)]
        times = [run.elapsed_seconds for run in runs]
        baseline = baselines[variant]
        mean_seconds = statistics.fmean(times)
        speedup = baseline / mean_seconds
        summaries.append(
            Summary(
                variant=variant,
                threads=threads,
                runs=len(runs),
                mean_seconds=mean_seconds,
                median_seconds=statistics.median(times),
                min_seconds=min(times),
                max_seconds=max(times),
                stdev_seconds=statistics.stdev(times) if len(times) > 1 else 0.0,
                speedup_variant=speedup,
                efficiency_variant=speedup / threads,
            )
        )

    return summaries


def write_summary_csv(path: str, summaries: list[Summary]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "variant",
                "threads",
                "runs",
                "mean_seconds",
                "median_seconds",
                "min_seconds",
                "max_seconds",
                "stdev_seconds",
                "speedup_vs_variant_1_thread",
                "efficiency_vs_variant_1_thread",
            ]
        )
        for summary in summaries:
            writer.writerow(
                [
                    summary.variant,
                    summary.threads,
                    summary.runs,
                    f"{summary.mean_seconds:.6f}",
                    f"{summary.median_seconds:.6f}",
                    f"{summary.min_seconds:.6f}",
                    f"{summary.max_seconds:.6f}",
                    f"{summary.stdev_seconds:.6f}",
                    f"{summary.speedup_variant:.6f}",
                    f"{summary.efficiency_variant:.6f}",
                ]
            )


def write_markdown_summary(path: str, summaries: list[Summary]) -> None:
    lines = [
        "# Exercise 2 Benchmark Summary",
        "",
        "| Variant | Threads | Runs | Mean [s] | Median [s] | Stddev [s] | Speedup | Efficiency |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for summary in summaries:
        lines.append(
            f"| {summary.variant} | {summary.threads} | {summary.runs} | "
            f"{summary.mean_seconds:.6f} | {summary.median_seconds:.6f} | {summary.stdev_seconds:.6f} | "
            f"{summary.speedup_variant:.3f} | {summary.efficiency_variant:.3f} |"
        )

    with open(path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def svg_header(width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">',
        '<rect width="100%" height="100%" fill="#faf8f3"/>',
        "<style>",
        'text { font-family: "Helvetica", "Arial", sans-serif; fill: #1f2937; }',
        ".title { font-size: 22px; font-weight: 700; }",
        ".subtitle { font-size: 12px; fill: #4b5563; }",
        ".axis { stroke: #374151; stroke-width: 1.2; }",
        ".grid { stroke: #d1d5db; stroke-width: 1; stroke-dasharray: 4 4; }",
        ".label { font-size: 12px; }",
        ".tick { font-size: 11px; fill: #4b5563; }",
        ".legend { font-size: 12px; }",
        "</style>",
    ]


def map_x(index: int, count: int, left: float, width: float) -> float:
    if count <= 1:
        return left + width / 2.0
    return left + index * width / (count - 1)


def map_y(value: float, max_value: float, top: float, height: float) -> float:
    if max_value <= 0.0:
        return top + height
    return top + height - (value / max_value) * height


def add_axes(elements: list[str], left: float, top: float, width: float, height: float) -> None:
    elements.append(
        f'<line class="axis" x1="{left:.1f}" y1="{top + height:.1f}" x2="{left + width:.1f}" y2="{top + height:.1f}"/>'
    )
    elements.append(
        f'<line class="axis" x1="{left:.1f}" y1="{top:.1f}" x2="{left:.1f}" y2="{top + height:.1f}"/>'
    )


def add_y_grid(elements: list[str], left: float, top: float, width: float, height: float, max_value: float) -> None:
    for step in range(6):
        value = max_value * step / 5.0
        y = map_y(value, max_value, top, height)
        elements.append(
            f'<line class="grid" x1="{left:.1f}" y1="{y:.1f}" x2="{left + width:.1f}" y2="{y:.1f}"/>'
        )
        elements.append(
            f'<text class="tick" x="{left - 8:.1f}" y="{y + 4:.1f}" text-anchor="end">{value:.2f}</text>'
        )


def write_runtime_svg(summaries: list[Summary], output_path: str) -> None:
    width, height = 1220, 780
    left, top = 90.0, 100.0
    plot_width, plot_height = 1000.0, 520.0
    thread_counts = sorted({s.threads for s in summaries})
    variants = sorted({s.variant for s in summaries})
    grouped = {(s.variant, s.threads): s for s in summaries}
    colors = ["#2563eb", "#b45309", "#059669", "#dc2626", "#7c3aed", "#0f766e", "#4b5563"]
    color_map = {variant: colors[index % len(colors)] for index, variant in enumerate(variants)}
    max_value = max(s.mean_seconds + s.stdev_seconds for s in summaries)

    elements = svg_header(width, height)
    elements.append('<text class="title" x="90" y="50">Mandelbrot Runtime by Schedule</text>')
    elements.append('<text class="subtitle" x="90" y="72">Each line shows the mean runtime for one OpenMP schedule.</text>')

    add_y_grid(elements, left, top, plot_width, plot_height, max_value * 1.1)
    add_axes(elements, left, top, plot_width, plot_height)

    for index, thread_count in enumerate(thread_counts):
        x = map_x(index, len(thread_counts), left, plot_width)
        elements.append(f'<text class="tick" x="{x:.1f}" y="{top + plot_height + 24:.1f}" text-anchor="middle">{thread_count}</text>')

    for variant in variants:
        points = []
        for index, thread_count in enumerate(thread_counts):
            x = map_x(index, len(thread_counts), left, plot_width)
            summary = grouped[(variant, thread_count)]
            y = map_y(summary.mean_seconds, max_value * 1.1, top, plot_height)
            points.append(f"{x:.1f},{y:.1f}")
            elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{color_map[variant]}"/>')
        elements.append(f'<polyline fill="none" stroke="{color_map[variant]}" stroke-width="3" points="{" ".join(points)}"/>')

    elements.append(f'<text class="label" x="{left + plot_width / 2:.1f}" y="{height - 46:.1f}" text-anchor="middle">Threads</text>')
    elements.append(f'<text class="label" x="28" y="{top + plot_height / 2:.1f}" transform="rotate(-90 28 {top + plot_height / 2:.1f})" text-anchor="middle">Runtime [s]</text>')

    legend_x = 760
    legend_y = 54
    for idx, variant in enumerate(variants):
        y = legend_y + idx * 22
        elements.append(f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 28}" y2="{y}" stroke="{color_map[variant]}" stroke-width="3"/>')
        elements.append(f'<circle cx="{legend_x + 14}" cy="{y}" r="4.5" fill="{color_map[variant]}"/>')
        elements.append(f'<text class="legend" x="{legend_x + 38}" y="{y + 4}">{variant}</text>')

    elements.append("</svg>")
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(elements))


def write_speedup_svg(summaries: list[Summary], output_path: str) -> None:
    width, height = 1220, 780
    left, top = 90.0, 100.0
    plot_width, plot_height = 1000.0, 520.0
    thread_counts = sorted({s.threads for s in summaries})
    variants = sorted({s.variant for s in summaries})
    grouped = {(s.variant, s.threads): s for s in summaries}
    colors = ["#2563eb", "#b45309", "#059669", "#dc2626", "#7c3aed", "#0f766e", "#4b5563"]
    color_map = {variant: colors[index % len(colors)] for index, variant in enumerate(variants)}
    max_value = max(max(s.speedup_variant for s in summaries), float(max(thread_counts)))

    elements = svg_header(width, height)
    elements.append('<text class="title" x="90" y="50">Mandelbrot Speedup by Schedule</text>')
    elements.append('<text class="subtitle" x="90" y="72">Gray dashed line shows ideal linear speedup.</text>')

    add_y_grid(elements, left, top, plot_width, plot_height, max_value * 1.1)
    add_axes(elements, left, top, plot_width, plot_height)

    ideal_points = []
    for index, thread_count in enumerate(thread_counts):
        x = map_x(index, len(thread_counts), left, plot_width)
        y = map_y(float(thread_count), max_value * 1.1, top, plot_height)
        ideal_points.append(f"{x:.1f},{y:.1f}")
        elements.append(f'<text class="tick" x="{x:.1f}" y="{top + plot_height + 24:.1f}" text-anchor="middle">{thread_count}</text>')
    elements.append(f'<polyline fill="none" stroke="#9ca3af" stroke-dasharray="8 6" stroke-width="2" points="{" ".join(ideal_points)}"/>')

    for variant in variants:
        points = []
        for index, thread_count in enumerate(thread_counts):
            x = map_x(index, len(thread_counts), left, plot_width)
            summary = grouped[(variant, thread_count)]
            y = map_y(summary.speedup_variant, max_value * 1.1, top, plot_height)
            points.append(f"{x:.1f},{y:.1f}")
            elements.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="{color_map[variant]}"/>')
        elements.append(f'<polyline fill="none" stroke="{color_map[variant]}" stroke-width="3" points="{" ".join(points)}"/>')

    elements.append(f'<text class="label" x="{left + plot_width / 2:.1f}" y="{height - 46:.1f}" text-anchor="middle">Threads</text>')
    elements.append(f'<text class="label" x="28" y="{top + plot_height / 2:.1f}" transform="rotate(-90 28 {top + plot_height / 2:.1f})" text-anchor="middle">Speedup vs. same schedule at 1 thread</text>')
    elements.append("</svg>")

    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(elements))


def main() -> int:
    csv_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join("results", "time_results.csv")
    results = load_results(csv_path)
    summaries = summarize(results)

    results_dir = os.path.dirname(csv_path) or "."
    plots_dir = os.path.join(results_dir, "plots")
    ensure_dir(plots_dir)

    write_summary_csv(os.path.join(results_dir, "summary_stats.csv"), summaries)
    write_markdown_summary(os.path.join(results_dir, "summary_table.md"), summaries)
    write_runtime_svg(summaries, os.path.join(plots_dir, "runtime_by_schedule.svg"))
    write_speedup_svg(summaries, os.path.join(plots_dir, "speedup_by_schedule.svg"))

    print(f"Analyzed {len(results)} runs from {csv_path}")
    print(f"Wrote summary CSV to {os.path.join(results_dir, 'summary_stats.csv')}")
    print(f"Wrote summary table to {os.path.join(results_dir, 'summary_table.md')}")
    print(f"Wrote plots to {plots_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
