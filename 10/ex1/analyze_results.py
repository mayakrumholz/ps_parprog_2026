#!/usr/bin/env python3

from __future__ import annotations

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable
from xml.sax.saxutils import escape


def read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []

    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def sample_stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0

    avg = mean(values)
    variance = sum((value - avg) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def summarize_time_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, int], list[float]] = defaultdict(list)

    for row in rows:
        grouped[(row["variant"], int(row["size"]))].append(float(row["elapsed_seconds"]))

    summary: list[dict[str, object]] = []
    for (variant, size), values in sorted(grouped.items(), key=lambda item: (item[0][1], item[0][0])):
        summary.append(
            {
                "variant": variant,
                "size": size,
                "runs": len(values),
                "mean_seconds": mean(values),
                "stddev_seconds": sample_stddev(values),
                "min_seconds": min(values),
                "max_seconds": max(values),
            }
        )

    return summary


def summarize_speedup(time_summary: list[dict[str, object]]) -> list[dict[str, object]]:
    baseline_means: dict[int, float] = {}
    auto_means: dict[int, float] = {}

    for row in time_summary:
        size = int(row["size"])
        mean_seconds = float(row["mean_seconds"])

        if row["variant"] == "baseline":
            baseline_means[size] = mean_seconds
        elif row["variant"] == "auto_vectorized":
            auto_means[size] = mean_seconds

    result: list[dict[str, object]] = []
    for size in sorted(set(baseline_means) & set(auto_means)):
        result.append(
            {
                "size": size,
                "baseline_mean_seconds": baseline_means[size],
                "auto_mean_seconds": auto_means[size],
                "speedup": baseline_means[size] / auto_means[size],
            }
        )

    return result


def summarize_perf_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, int, str], list[float]] = defaultdict(list)
    units: dict[tuple[str, int, str], str] = {}

    for row in rows:
        key = (row["variant"], int(row["size"]), row["metric"])
        grouped[key].append(float(row["value"]))
        units[key] = row["unit"]

    summary: list[dict[str, object]] = []
    for (variant, size, metric), values in sorted(grouped.items(), key=lambda item: (item[0][1], item[0][0], item[0][2])):
        summary.append(
            {
                "variant": variant,
                "size": size,
                "metric": metric,
                "unit": units[(variant, size, metric)],
                "mean_value": mean(values),
                "stddev_value": sample_stddev(values),
            }
        )

    return summary


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary_table(path: Path, time_summary: list[dict[str, object]], speedup_summary: list[dict[str, object]]) -> None:
    lines = [
        "# Exercise 1 Summary",
        "",
        "## Runtime Summary",
        "",
        "| Variant | Size | Runs | Mean [s] | Stddev [s] | Min [s] | Max [s] |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for row in time_summary:
        lines.append(
            f"| {row['variant']} | {row['size']} | {row['runs']} | "
            f"{float(row['mean_seconds']):.6f} | {float(row['stddev_seconds']):.6f} | "
            f"{float(row['min_seconds']):.6f} | {float(row['max_seconds']):.6f} |"
        )

    lines.extend(
        [
            "",
            "## Speedup Summary",
            "",
            "| Size | Baseline mean [s] | Auto-vectorized mean [s] | Speedup |",
            "| --- | ---: | ---: | ---: |",
        ]
    )

    for row in speedup_summary:
        lines.append(
            f"| {row['size']} | {float(row['baseline_mean_seconds']):.6f} | "
            f"{float(row['auto_mean_seconds']):.6f} | {float(row['speedup']):.3f} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_perf_table(path: Path, perf_summary: list[dict[str, object]]) -> None:
    lines = [
        "# Perf Summary",
        "",
        "| Variant | Size | Metric | Mean value | Stddev | Unit |",
        "| --- | ---: | --- | ---: | ---: | --- |",
    ]

    for row in perf_summary:
        lines.append(
            f"| {row['variant']} | {row['size']} | {row['metric']} | "
            f"{float(row['mean_value']):.3f} | {float(row['stddev_value']):.3f} | {row['unit']} |"
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def svg_line_chart(
    path: Path,
    title: str,
    x_label: str,
    y_label: str,
    series: list[dict[str, object]],
    y_reference: float | None = None,
) -> None:
    width = 900
    height = 520
    left = 90
    right = 30
    top = 60
    bottom = 80
    plot_width = width - left - right
    plot_height = height - top - bottom

    all_points = [point for item in series for point in item["points"]]
    x_values = [point[0] for point in all_points]
    y_values = [point[1] for point in all_points]

    min_x = min(x_values)
    max_x = max(x_values)
    min_y = 0.0
    max_y = max(y_values + ([y_reference] if y_reference is not None else []))
    if max_y <= 0.0:
        max_y = 1.0
    max_y *= 1.1

    def x_to_svg(value: float) -> float:
        if max_x == min_x:
            return left + plot_width / 2
        return left + ((value - min_x) / (max_x - min_x)) * plot_width

    def y_to_svg(value: float) -> float:
        return top + plot_height - ((value - min_y) / (max_y - min_y)) * plot_height

    lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fffdf8"/>',
        f'<text x="{width / 2}" y="30" text-anchor="middle" font-size="22" font-family="Helvetica, Arial, sans-serif">{escape(title)}</text>',
    ]

    for index in range(6):
        value = min_y + (max_y - min_y) * index / 5
        y = y_to_svg(value)
        lines.append(f'<line x1="{left}" y1="{y:.2f}" x2="{width - right}" y2="{y:.2f}" stroke="#d9d9d9" stroke-dasharray="4 4"/>')
        lines.append(f'<text x="{left - 10}" y="{y + 5:.2f}" text-anchor="end" font-size="12" font-family="Helvetica, Arial, sans-serif">{value:.3f}</text>')

    unique_x = sorted(set(x_values))
    for value in unique_x:
        x = x_to_svg(value)
        lines.append(f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{top + plot_height}" stroke="#eeeeee"/>')
        lines.append(f'<text x="{x:.2f}" y="{height - 40}" text-anchor="middle" font-size="12" font-family="Helvetica, Arial, sans-serif">{value:g}</text>')

    lines.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#333333" stroke-width="2"/>')
    lines.append(f'<line x1="{left}" y1="{top + plot_height}" x2="{width - right}" y2="{top + plot_height}" stroke="#333333" stroke-width="2"/>')

    if y_reference is not None:
        y = y_to_svg(y_reference)
        lines.append(f'<line x1="{left}" y1="{y:.2f}" x2="{width - right}" y2="{y:.2f}" stroke="#9b2226" stroke-width="2" stroke-dasharray="8 5"/>')

    for item in series:
        points = item["points"]
        polyline = " ".join(f"{x_to_svg(x):.2f},{y_to_svg(y):.2f}" for x, y in points)
        color = str(item["color"])
        lines.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{polyline}"/>')

        for x_value, y_value in points:
            x = x_to_svg(x_value)
            y = y_to_svg(y_value)
            lines.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.5" fill="{color}" stroke="white" stroke-width="1.5"/>')

    legend_x = width - right - 270
    legend_y = top + 10
    lines.append(f'<rect x="{legend_x}" y="{legend_y}" width="250" height="{28 * len(series) + 14}" fill="#ffffff" stroke="#cccccc"/>')
    for index, item in enumerate(series):
        y = legend_y + 24 + index * 28
        lines.append(f'<line x1="{legend_x + 12}" y1="{y}" x2="{legend_x + 42}" y2="{y}" stroke="{item["color"]}" stroke-width="3"/>')
        lines.append(f'<text x="{legend_x + 52}" y="{y + 5}" font-size="13" font-family="Helvetica, Arial, sans-serif">{escape(str(item["label"]))}</text>')

    lines.append(f'<text x="{width / 2}" y="{height - 10}" text-anchor="middle" font-size="14" font-family="Helvetica, Arial, sans-serif">{escape(x_label)}</text>')
    lines.append(
        f'<text x="22" y="{height / 2}" text-anchor="middle" font-size="14" font-family="Helvetica, Arial, sans-serif" transform="rotate(-90 22 {height / 2})">{escape(y_label)}</text>'
    )
    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def svg_grouped_bar_chart(
    path: Path,
    title: str,
    x_label: str,
    y_label: str,
    categories: list[str],
    series: list[dict[str, object]],
) -> None:
    width = 1100
    height = 560
    left = 90
    right = 30
    top = 60
    bottom = 110
    plot_width = width - left - right
    plot_height = height - top - bottom

    max_y = max((max((value for value in item["values"]), default=0.0) for item in series), default=0.0)
    if max_y <= 0.0:
        max_y = 1.0
    max_y *= 1.1

    def y_to_svg(value: float) -> float:
        return top + plot_height - (value / max_y) * plot_height

    group_width = plot_width / max(1, len(categories))
    bar_width = min(40.0, group_width / max(2, len(series) + 1))

    lines: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fffdf8"/>',
        f'<text x="{width / 2}" y="30" text-anchor="middle" font-size="22" font-family="Helvetica, Arial, sans-serif">{escape(title)}</text>',
    ]

    for index in range(6):
        value = max_y * index / 5
        y = y_to_svg(value)
        lines.append(f'<line x1="{left}" y1="{y:.2f}" x2="{width - right}" y2="{y:.2f}" stroke="#d9d9d9" stroke-dasharray="4 4"/>')
        lines.append(f'<text x="{left - 10}" y="{y + 5:.2f}" text-anchor="end" font-size="12" font-family="Helvetica, Arial, sans-serif">{value:.0f}</text>')

    lines.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#333333" stroke-width="2"/>')
    lines.append(f'<line x1="{left}" y1="{top + plot_height}" x2="{width - right}" y2="{top + plot_height}" stroke="#333333" stroke-width="2"/>')

    for cat_index, category in enumerate(categories):
        center_x = left + group_width * (cat_index + 0.5)
        for series_index, item in enumerate(series):
            values = item["values"]
            value = values[cat_index] if cat_index < len(values) else 0.0
            x = center_x + (series_index - (len(series) - 1) / 2) * (bar_width + 8) - bar_width / 2
            y = y_to_svg(value)
            height_value = top + plot_height - y
            lines.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{height_value:.2f}" fill="{item["color"]}"/>')

        lines.append(f'<text x="{center_x:.2f}" y="{height - 60}" text-anchor="middle" font-size="11" font-family="Helvetica, Arial, sans-serif" transform="rotate(-25 {center_x:.2f} {height - 60})">{escape(category)}</text>')

    legend_x = width - right - 220
    legend_y = top + 10
    lines.append(f'<rect x="{legend_x}" y="{legend_y}" width="200" height="{28 * len(series) + 14}" fill="#ffffff" stroke="#cccccc"/>')
    for index, item in enumerate(series):
        y = legend_y + 24 + index * 28
        lines.append(f'<rect x="{legend_x + 12}" y="{y - 11}" width="20" height="14" fill="{item["color"]}"/>')
        lines.append(f'<text x="{legend_x + 42}" y="{y}" font-size="13" font-family="Helvetica, Arial, sans-serif">{escape(str(item["label"]))}</text>')

    lines.append(f'<text x="{width / 2}" y="{height - 12}" text-anchor="middle" font-size="14" font-family="Helvetica, Arial, sans-serif">{escape(x_label)}</text>')
    lines.append(
        f'<text x="22" y="{height / 2}" text-anchor="middle" font-size="14" font-family="Helvetica, Arial, sans-serif" transform="rotate(-90 22 {height / 2})">{escape(y_label)}</text>'
    )
    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_runtime(path: Path, time_summary: list[dict[str, object]]) -> None:
    grouped: dict[str, list[tuple[int, float]]] = defaultdict(list)

    for row in time_summary:
        grouped[str(row["variant"])].append((int(row["size"]), float(row["mean_seconds"])))

    svg_line_chart(
        path,
        "Runtime of a[i] += b[i] * c[i]",
        "Vector length",
        "Mean runtime [s]",
        [
            {
                "label": "baseline (-O1, no vectorization)",
                "color": "#9b2226",
                "points": sorted(grouped["baseline"]),
            },
            {
                "label": "auto-vectorized (-O1 -ftree-vectorize)",
                "color": "#005f73",
                "points": sorted(grouped["auto_vectorized"]),
            },
        ],
    )


def plot_speedup(path: Path, speedup_summary: list[dict[str, object]]) -> None:
    svg_line_chart(
        path,
        "Speedup due to compiler auto-vectorization",
        "Vector length",
        "Speedup baseline / auto-vectorized",
        [
            {
                "label": "speedup",
                "color": "#005f73",
                "points": [(int(row["size"]), float(row["speedup"])) for row in speedup_summary],
            }
        ],
        y_reference=1.0,
    )


def plot_perf(path: Path, perf_summary: list[dict[str, object]]) -> None:
    metric_labels = {
        "r0410": "SSE_FP",
        "r1010": "SSE_FP_PACKED",
        "r2010": "SSE_FP_SCALAR",
        "r4010": "SSE_SINGLE_PRECISION",
    }
    categories: list[str] = []
    baseline_values: list[float] = []
    auto_values: list[float] = []

    sizes = sorted({int(row["size"]) for row in perf_summary})
    for size in sizes:
        for metric, label in metric_labels.items():
            categories.append(f"n={size} {label}")

            baseline_match = next(
                (
                    row
                    for row in perf_summary
                    if row["variant"] == "baseline" and int(row["size"]) == size and row["metric"] == metric
                ),
                None,
            )
            auto_match = next(
                (
                    row
                    for row in perf_summary
                    if row["variant"] == "auto_vectorized" and int(row["size"]) == size and row["metric"] == metric
                ),
                None,
            )
            baseline_values.append(float(baseline_match["mean_value"]) if baseline_match else 0.0)
            auto_values.append(float(auto_match["mean_value"]) if auto_match else 0.0)

    svg_grouped_bar_chart(
        path,
        "Perf vector event counts",
        "Metric group",
        "Mean event count",
        categories,
        [
            {"label": "baseline", "color": "#9b2226", "values": baseline_values},
            {"label": "auto_vectorized", "color": "#005f73", "values": auto_values},
        ],
    )


def main() -> int:
    if len(sys.argv) not in {2, 3}:
        print(f"usage: {sys.argv[0]} TIME_CSV [PERF_CSV]", file=sys.stderr)
        return 1

    time_csv = Path(sys.argv[1])
    perf_csv = Path(sys.argv[2]) if len(sys.argv) == 3 else Path("results/perf_results.csv")
    results_dir = time_csv.resolve().parent
    plots_dir = results_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    time_rows = read_rows(time_csv)
    time_summary = summarize_time_rows(time_rows)
    speedup_summary = summarize_speedup(time_summary)

    write_csv(
        results_dir / "summary_stats.csv",
        time_summary,
        ["variant", "size", "runs", "mean_seconds", "stddev_seconds", "min_seconds", "max_seconds"],
    )
    write_csv(
        results_dir / "speedup_stats.csv",
        speedup_summary,
        ["size", "baseline_mean_seconds", "auto_mean_seconds", "speedup"],
    )
    write_summary_table(results_dir / "summary_table.md", time_summary, speedup_summary)

    if time_summary:
        plot_runtime(plots_dir / "runtime_by_size.svg", time_summary)
    if speedup_summary:
        plot_speedup(plots_dir / "speedup_by_size.svg", speedup_summary)

    perf_rows = read_rows(perf_csv)
    perf_summary = summarize_perf_rows(perf_rows)
    if perf_summary:
        write_csv(
            results_dir / "perf_summary.csv",
            perf_summary,
            ["variant", "size", "metric", "unit", "mean_value", "stddev_value"],
        )
        write_perf_table(results_dir / "perf_summary.md", perf_summary)
        plot_perf(plots_dir / "perf_vector_events.svg", perf_summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
