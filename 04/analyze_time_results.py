#!/usr/bin/env python3

import csv
import os
import statistics
import sys
from dataclasses import dataclass
from typing import Iterable


@dataclass
class RunResult:
    thread_count: int
    run: int
    real: float
    user: float
    sys_time: float
    image: str


@dataclass
class ThreadStats:
    thread_count: int
    runs: int
    mean_real: float
    median_real: float
    min_real: float
    max_real: float
    stdev_real: float
    mean_user: float
    mean_sys: float
    speedup_vs_1: float
    efficiency_vs_1: float


def load_results(csv_path: str) -> list[RunResult]:
    with open(csv_path, newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        required_columns = {"threads", "run", "real", "user", "sys", "image"}
        if reader.fieldnames is None or not required_columns.issubset(reader.fieldnames):
            raise ValueError(
                f"CSV file {csv_path} is missing required columns: {sorted(required_columns)}"
            )

        results = []
        for row in reader:
            results.append(
                RunResult(
                    thread_count=int(row["threads"]),
                    run=int(row["run"]),
                    real=float(row["real"]),
                    user=float(row["user"]),
                    sys_time=float(row["sys"]),
                    image=row["image"],
                )
            )

    if not results:
        raise ValueError(f"CSV file {csv_path} does not contain any benchmark rows")

    return results


def summarize(results: Iterable[RunResult]) -> list[ThreadStats]:
    grouped: dict[int, list[RunResult]] = {}
    for result in results:
        grouped.setdefault(result.thread_count, []).append(result)

    if 1 not in grouped:
        raise ValueError("Need measurements for 1 thread to compute speedup and efficiency")

    baseline_mean = statistics.fmean(result.real for result in grouped[1])
    summaries = []

    for thread_count in sorted(grouped):
        runs = grouped[thread_count]
        real_times = [result.real for result in runs]
        user_times = [result.user for result in runs]
        sys_times = [result.sys_time for result in runs]
        mean_real = statistics.fmean(real_times)
        speedup = baseline_mean / mean_real
        summaries.append(
            ThreadStats(
                thread_count=thread_count,
                runs=len(runs),
                mean_real=mean_real,
                median_real=statistics.median(real_times),
                min_real=min(real_times),
                max_real=max(real_times),
                stdev_real=statistics.stdev(real_times) if len(real_times) > 1 else 0.0,
                mean_user=statistics.fmean(user_times),
                mean_sys=statistics.fmean(sys_times),
                speedup_vs_1=speedup,
                efficiency_vs_1=speedup / thread_count,
            )
        )

    return summaries


def ensure_directory(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_summary_csv(output_dir: str, summaries: list[ThreadStats]) -> str:
    summary_path = os.path.join(output_dir, "summary.csv")
    with open(summary_path, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            [
                "threads",
                "runs",
                "mean_real",
                "median_real",
                "min_real",
                "max_real",
                "stdev_real",
                "mean_user",
                "mean_sys",
                "speedup_vs_1",
                "efficiency_vs_1",
            ]
        )
        for summary in summaries:
            writer.writerow(
                [
                    summary.thread_count,
                    summary.runs,
                    f"{summary.mean_real:.6f}",
                    f"{summary.median_real:.6f}",
                    f"{summary.min_real:.6f}",
                    f"{summary.max_real:.6f}",
                    f"{summary.stdev_real:.6f}",
                    f"{summary.mean_user:.6f}",
                    f"{summary.mean_sys:.6f}",
                    f"{summary.speedup_vs_1:.6f}",
                    f"{summary.efficiency_vs_1:.6f}",
                ]
            )
    return summary_path


def write_summary_markdown(output_dir: str, summaries: list[ThreadStats]) -> str:
    summary_path = os.path.join(output_dir, "summary.md")
    with open(summary_path, "w", encoding="utf-8") as md_file:
        md_file.write("# Benchmark Summary\n\n")
        md_file.write(
            "| Threads | Runs | Mean real [s] | Median [s] | Stddev [s] | Min [s] | Max [s] | Speedup | Efficiency |\n"
        )
        md_file.write(
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |\n"
        )
        for summary in summaries:
            md_file.write(
                f"| {summary.thread_count} | {summary.runs} | {summary.mean_real:.4f} | "
                f"{summary.median_real:.4f} | {summary.stdev_real:.4f} | {summary.min_real:.4f} | "
                f"{summary.max_real:.4f} | {summary.speedup_vs_1:.3f} | {summary.efficiency_vs_1:.3f} |\n"
            )
    return summary_path


def escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def svg_header(width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img">',
        '<rect width="100%" height="100%" fill="#fcfbf7"/>',
        '<style>',
        'text { font-family: "Helvetica", "Arial", sans-serif; fill: #1f2937; }',
        '.title { font-size: 22px; font-weight: 700; }',
        '.subtitle { font-size: 12px; fill: #4b5563; }',
        '.axis { stroke: #374151; stroke-width: 1.3; }',
        '.grid { stroke: #d1d5db; stroke-width: 1; stroke-dasharray: 4 4; }',
        '.label { font-size: 12px; }',
        '.tick { font-size: 11px; fill: #4b5563; }',
        '.legend { font-size: 12px; }',
        '</style>',
    ]


def map_x(index: int, count: int, left: float, width: float) -> float:
    if count <= 1:
        return left + width / 2.0
    return left + (index * width) / (count - 1)


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


def add_y_grid(
    elements: list[str], left: float, top: float, width: float, height: float, max_value: float
) -> None:
    for step in range(6):
        value = (max_value * step) / 5.0
        y = map_y(value, max_value, top, height)
        elements.append(
            f'<line class="grid" x1="{left:.1f}" y1="{y:.1f}" x2="{left + width:.1f}" y2="{y:.1f}"/>'
        )
        elements.append(
            f'<text class="tick" x="{left - 10:.1f}" y="{y + 4:.1f}" text-anchor="end">{value:.2f}</text>'
        )


def write_runtime_svg(
    output_dir: str, results: list[RunResult], summaries: list[ThreadStats]
) -> str:
    path = os.path.join(output_dir, "runtime_by_threads.svg")
    width = 1100
    height = 700
    left = 90.0
    top = 90.0
    plot_width = 920.0
    plot_height = 480.0

    grouped: dict[int, list[RunResult]] = {}
    for result in results:
        grouped.setdefault(result.thread_count, []).append(result)

    max_value = max(max(result.real for result in results), max(s.mean_real + s.stdev_real for s in summaries))
    elements = svg_header(width, height)
    elements.append('<text class="title" x="90" y="46">Mandelbrot Runtime by Thread Count</text>')
    elements.append(
        '<text class="subtitle" x="90" y="68">Gray dots show individual runs, orange line shows mean runtime, vertical bars show ±1 standard deviation.</text>'
    )

    add_y_grid(elements, left, top, plot_width, plot_height, max_value * 1.1)
    add_axes(elements, left, top, plot_width, plot_height)

    thread_counts = [summary.thread_count for summary in summaries]
    mean_points = []

    for index, thread_count in enumerate(thread_counts):
        x = map_x(index, len(thread_counts), left, plot_width)
        elements.append(
            f'<text class="tick" x="{x:.1f}" y="{top + plot_height + 24:.1f}" text-anchor="middle">{thread_count}</text>'
        )
        for run_index, result in enumerate(sorted(grouped[thread_count], key=lambda item: item.run)):
            jitter = (run_index - (len(grouped[thread_count]) - 1) / 2.0) * 3.5
            y = map_y(result.real, max_value * 1.1, top, plot_height)
            elements.append(
                f'<circle cx="{x + jitter:.1f}" cy="{y:.1f}" r="4.2" fill="#9ca3af" fill-opacity="0.85"/>'
            )

        summary = next(summary for summary in summaries if summary.thread_count == thread_count)
        mean_y = map_y(summary.mean_real, max_value * 1.1, top, plot_height)
        std_top = map_y(summary.mean_real + summary.stdev_real, max_value * 1.1, top, plot_height)
        std_bottom = map_y(max(summary.mean_real - summary.stdev_real, 0.0), max_value * 1.1, top, plot_height)
        elements.append(
            f'<line x1="{x:.1f}" y1="{std_top:.1f}" x2="{x:.1f}" y2="{std_bottom:.1f}" stroke="#c2410c" stroke-width="2.2"/>'
        )
        elements.append(
            f'<line x1="{x - 10:.1f}" y1="{std_top:.1f}" x2="{x + 10:.1f}" y2="{std_top:.1f}" stroke="#c2410c" stroke-width="2.2"/>'
        )
        elements.append(
            f'<line x1="{x - 10:.1f}" y1="{std_bottom:.1f}" x2="{x + 10:.1f}" y2="{std_bottom:.1f}" stroke="#c2410c" stroke-width="2.2"/>'
        )
        mean_points.append(f"{x:.1f},{mean_y:.1f}")
        elements.append(f'<circle cx="{x:.1f}" cy="{mean_y:.1f}" r="5.3" fill="#ea580c"/>')

    elements.append(
        f'<polyline fill="none" stroke="#ea580c" stroke-width="3" points="{" ".join(mean_points)}"/>'
    )
    elements.append(
        f'<text class="label" x="{left + plot_width / 2:.1f}" y="{height - 40:.1f}" text-anchor="middle">Threads</text>'
    )
    elements.append(
        f'<text class="label" x="28" y="{top + plot_height / 2:.1f}" transform="rotate(-90 28 {top + plot_height / 2:.1f})" text-anchor="middle">Real runtime [s]</text>'
    )
    elements.append('<circle cx="820" cy="56" r="4.2" fill="#9ca3af" fill-opacity="0.85"/>')
    elements.append('<text class="legend" x="834" y="60">Single run</text>')
    elements.append('<line x1="930" y1="56" x2="962" y2="56" stroke="#ea580c" stroke-width="3"/>')
    elements.append('<circle cx="946" cy="56" r="5.3" fill="#ea580c"/>')
    elements.append('<text class="legend" x="972" y="60">Mean runtime</text>')
    elements.append("</svg>")

    with open(path, "w", encoding="utf-8") as svg_file:
        svg_file.write("\n".join(elements))
    return path


def write_speedup_svg(output_dir: str, summaries: list[ThreadStats]) -> str:
    path = os.path.join(output_dir, "speedup_efficiency.svg")
    width = 1100
    height = 700
    left = 90.0
    top = 90.0
    plot_width = 920.0
    plot_height = 480.0
    max_value = max(
        max(summary.speedup_vs_1 for summary in summaries),
        max(summary.thread_count for summary in summaries),
        1.0,
    )

    elements = svg_header(width, height)
    elements.append('<text class="title" x="90" y="46">Speedup and Efficiency</text>')
    elements.append(
        '<text class="subtitle" x="90" y="68">Blue line shows measured speedup relative to 1 thread, red bars show parallel efficiency.</text>'
    )

    add_y_grid(elements, left, top, plot_width, plot_height, max_value * 1.1)
    add_axes(elements, left, top, plot_width, plot_height)

    speedup_points = []
    for index, summary in enumerate(summaries):
        x = map_x(index, len(summaries), left, plot_width)
        elements.append(
            f'<text class="tick" x="{x:.1f}" y="{top + plot_height + 24:.1f}" text-anchor="middle">{summary.thread_count}</text>'
        )

        ideal_y = map_y(float(summary.thread_count), max_value * 1.1, top, plot_height)
        measured_y = map_y(summary.speedup_vs_1, max_value * 1.1, top, plot_height)
        efficiency_height = (summary.efficiency_vs_1 / 1.0) * (plot_height * 0.55)
        bar_top = top + plot_height - efficiency_height

        elements.append(
            f'<line x1="{x:.1f}" y1="{ideal_y:.1f}" x2="{x:.1f}" y2="{measured_y:.1f}" stroke="#93c5fd" stroke-width="2"/>'
        )
        elements.append(
            f'<rect x="{x - 17:.1f}" y="{bar_top:.1f}" width="34" height="{efficiency_height:.1f}" fill="#dc2626" fill-opacity="0.72"/>'
        )
        speedup_points.append(f"{x:.1f},{measured_y:.1f}")
        elements.append(f'<circle cx="{x:.1f}" cy="{measured_y:.1f}" r="5.2" fill="#2563eb"/>')
        elements.append(
            f'<text class="tick" x="{x:.1f}" y="{bar_top - 8:.1f}" text-anchor="middle">{summary.efficiency_vs_1:.2f}</text>'
        )

    ideal_points = []
    for index, summary in enumerate(summaries):
        x = map_x(index, len(summaries), left, plot_width)
        ideal_y = map_y(float(summary.thread_count), max_value * 1.1, top, plot_height)
        ideal_points.append(f"{x:.1f},{ideal_y:.1f}")

    elements.append(
        f'<polyline fill="none" stroke="#2563eb" stroke-width="3" points="{" ".join(speedup_points)}"/>'
    )
    elements.append(
        f'<polyline fill="none" stroke="#6b7280" stroke-width="2" stroke-dasharray="8 6" points="{" ".join(ideal_points)}"/>'
    )
    elements.append(
        f'<text class="label" x="{left + plot_width / 2:.1f}" y="{height - 40:.1f}" text-anchor="middle">Threads</text>'
    )
    elements.append(
        f'<text class="label" x="28" y="{top + plot_height / 2:.1f}" transform="rotate(-90 28 {top + plot_height / 2:.1f})" text-anchor="middle">Speedup</text>'
    )
    elements.append('<line x1="752" y1="56" x2="784" y2="56" stroke="#2563eb" stroke-width="3"/>')
    elements.append('<circle cx="768" cy="56" r="5.2" fill="#2563eb"/>')
    elements.append('<text class="legend" x="794" y="60">Measured speedup</text>')
    elements.append('<line x1="915" y1="56" x2="947" y2="56" stroke="#6b7280" stroke-width="2" stroke-dasharray="8 6"/>')
    elements.append('<text class="legend" x="957" y="60">Ideal speedup</text>')
    elements.append('<rect x="752" y="86" width="34" height="18" fill="#dc2626" fill-opacity="0.72"/>')
    elements.append('<text class="legend" x="794" y="100">Efficiency (0..1, scaled bar)</text>')
    elements.append("</svg>")

    with open(path, "w", encoding="utf-8") as svg_file:
        svg_file.write("\n".join(elements))
    return path


def write_index(output_dir: str, generated_files: list[str]) -> str:
    path = os.path.join(output_dir, "index.html")
    file_names = [os.path.basename(file_path) for file_path in generated_files]
    links = "\n".join(
        f'    <li><a href="{escape_xml(file_name)}">{escape_xml(file_name)}</a></li>'
        for file_name in file_names
    )
    content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Benchmark Visualization</title>
  <style>
    body {{ font-family: Helvetica, Arial, sans-serif; margin: 32px; background: #fcfbf7; color: #1f2937; }}
    h1 {{ margin-bottom: 8px; }}
    p {{ max-width: 820px; line-height: 1.5; }}
    img {{ max-width: 100%; border: 1px solid #d1d5db; background: white; margin: 18px 0 30px; }}
  </style>
</head>
<body>
  <h1>Benchmark Visualization</h1>
  <p>Generated from <code>results/time_results.csv</code>. The overview files are listed below and the SVG charts are embedded directly for quick inspection.</p>
  <ul>
{links}
  </ul>
  <h2>Runtime by Thread Count</h2>
  <img src="runtime_by_threads.svg" alt="Runtime by thread count">
  <h2>Speedup and Efficiency</h2>
  <img src="speedup_efficiency.svg" alt="Speedup and efficiency">
</body>
</html>
"""
    with open(path, "w", encoding="utf-8") as html_file:
        html_file.write(content)
    return path


def main() -> int:
    csv_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join("results", "time_results.csv")
    output_dir = (
        sys.argv[2] if len(sys.argv) > 2 else os.path.join("results", "visualization")
    )

    try:
        results = load_results(csv_path)
        summaries = summarize(results)
        ensure_directory(output_dir)
        generated_files = [
            write_summary_csv(output_dir, summaries),
            write_summary_markdown(output_dir, summaries),
            write_runtime_svg(output_dir, results, summaries),
            write_speedup_svg(output_dir, summaries),
        ]
        generated_files.append(write_index(output_dir, generated_files))
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(f"Read benchmark data from {csv_path}")
    print(f"Wrote visualization files to {output_dir}")
    for file_path in generated_files:
        print(f" - {file_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
