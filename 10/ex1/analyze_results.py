#!/usr/bin/env python3

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import escape


def read_rows(path):
    if not path.exists():
        return []

    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def mean(values):
    return sum(values) / float(len(values))


def sample_stddev(values):
    if len(values) < 2:
        return 0.0

    avg = mean(values)
    variance = sum((value - avg) ** 2 for value in values) / float(len(values) - 1)
    return math.sqrt(variance)


def summarize_time_rows(rows):
    grouped = defaultdict(list)

    for row in rows:
        grouped[(row["variant"], int(row["size"]))].append(float(row["elapsed_seconds"]))

    summary = []
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


def summarize_speedup(time_summary):
    baseline_means = {}
    auto_means = {}

    for row in time_summary:
        size = int(row["size"])
        mean_seconds = float(row["mean_seconds"])

        if row["variant"] == "baseline":
            baseline_means[size] = mean_seconds
        elif row["variant"] == "auto_vectorized":
            auto_means[size] = mean_seconds

    result = []
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


def summarize_perf_rows(rows):
    grouped = defaultdict(list)
    units = {}

    for row in rows:
        key = (row["variant"], int(row["size"]), row["metric"])
        grouped[key].append(float(row["value"]))
        units[key] = row["unit"]

    summary = []
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


def write_csv(path, rows, fieldnames):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary_table(path, time_summary, speedup_summary):
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
            "| {variant} | {size} | {runs} | {mean:.6f} | {stddev:.6f} | {minv:.6f} | {maxv:.6f} |".format(
                variant=row["variant"],
                size=row["size"],
                runs=row["runs"],
                mean=float(row["mean_seconds"]),
                stddev=float(row["stddev_seconds"]),
                minv=float(row["min_seconds"]),
                maxv=float(row["max_seconds"]),
            )
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
            "| {size} | {baseline:.6f} | {auto:.6f} | {speedup:.3f} |".format(
                size=row["size"],
                baseline=float(row["baseline_mean_seconds"]),
                auto=float(row["auto_mean_seconds"]),
                speedup=float(row["speedup"]),
            )
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_perf_table(path, perf_summary):
    lines = [
        "# Perf Summary",
        "",
        "| Variant | Size | Metric | Mean value | Stddev | Unit |",
        "| --- | ---: | --- | ---: | ---: | --- |",
    ]

    for row in perf_summary:
        lines.append(
            "| {variant} | {size} | {metric} | {meanv:.3f} | {stddev:.3f} | {unit} |".format(
                variant=row["variant"],
                size=row["size"],
                metric=row["metric"],
                meanv=float(row["mean_value"]),
                stddev=float(row["stddev_value"]),
                unit=row["unit"],
            )
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def svg_line_chart(path, title, x_label, y_label, series, y_reference=None):
    width = 900
    height = 520
    left = 90
    right = 30
    top = 60
    bottom = 80
    plot_width = width - left - right
    plot_height = height - top - bottom

    all_points = []
    for item in series:
        all_points.extend(item["points"])

    x_values = [point[0] for point in all_points]
    y_values = [point[1] for point in all_points]

    min_x = min(x_values)
    max_x = max(x_values)
    min_y = 0.0
    max_y = max(y_values + ([y_reference] if y_reference is not None else []))
    if max_y <= 0.0:
        max_y = 1.0
    max_y *= 1.1

    def x_to_svg(value):
        if max_x == min_x:
            return left + plot_width / 2.0
        return left + ((value - min_x) / float(max_x - min_x)) * plot_width

    def y_to_svg(value):
        return top + plot_height - ((value - min_y) / float(max_y - min_y)) * plot_height

    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="{0}" height="{1}" viewBox="0 0 {0} {1}">'.format(width, height),
        '<rect width="100%" height="100%" fill="#fffdf8"/>',
        '<text x="{0}" y="30" text-anchor="middle" font-size="22" font-family="Helvetica, Arial, sans-serif">{1}</text>'.format(
            width / 2.0, escape(title)
        ),
    ]

    for index in range(6):
        value = min_y + (max_y - min_y) * index / 5.0
        y = y_to_svg(value)
        lines.append('<line x1="{0}" y1="{1:.2f}" x2="{2}" y2="{1:.2f}" stroke="#d9d9d9" stroke-dasharray="4 4"/>'.format(left, y, width - right))
        lines.append('<text x="{0}" y="{1:.2f}" text-anchor="end" font-size="12" font-family="Helvetica, Arial, sans-serif">{2:.3f}</text>'.format(left - 10, y + 5, value))

    unique_x = sorted(set(x_values))
    for value in unique_x:
        x = x_to_svg(value)
        lines.append('<line x1="{0:.2f}" y1="{1}" x2="{0:.2f}" y2="{2}" stroke="#eeeeee"/>'.format(x, top, top + plot_height))
        lines.append('<text x="{0:.2f}" y="{1}" text-anchor="middle" font-size="12" font-family="Helvetica, Arial, sans-serif">{2:g}</text>'.format(x, height - 40, value))

    lines.append('<line x1="{0}" y1="{1}" x2="{0}" y2="{2}" stroke="#333333" stroke-width="2"/>'.format(left, top, top + plot_height))
    lines.append('<line x1="{0}" y1="{1}" x2="{2}" y2="{1}" stroke="#333333" stroke-width="2"/>'.format(left, top + plot_height, width - right))

    if y_reference is not None:
        y = y_to_svg(y_reference)
        lines.append('<line x1="{0}" y1="{1:.2f}" x2="{2}" y2="{1:.2f}" stroke="#9b2226" stroke-width="2" stroke-dasharray="8 5"/>'.format(left, y, width - right))

    for item in series:
        polyline = " ".join("{0:.2f},{1:.2f}".format(x_to_svg(x), y_to_svg(y)) for x, y in item["points"])
        color = item["color"]
        lines.append('<polyline fill="none" stroke="{0}" stroke-width="3" points="{1}"/>'.format(color, polyline))

        for x_value, y_value in item["points"]:
            x = x_to_svg(x_value)
            y = y_to_svg(y_value)
            lines.append('<circle cx="{0:.2f}" cy="{1:.2f}" r="4.5" fill="{2}" stroke="white" stroke-width="1.5"/>'.format(x, y, color))

    legend_x = width - right - 270
    legend_y = top + 10
    lines.append('<rect x="{0}" y="{1}" width="250" height="{2}" fill="#ffffff" stroke="#cccccc"/>'.format(legend_x, legend_y, 28 * len(series) + 14))
    for index, item in enumerate(series):
        y = legend_y + 24 + index * 28
        lines.append('<line x1="{0}" y1="{1}" x2="{2}" y2="{1}" stroke="{3}" stroke-width="3"/>'.format(legend_x + 12, y, legend_x + 42, item["color"]))
        lines.append('<text x="{0}" y="{1}" font-size="13" font-family="Helvetica, Arial, sans-serif">{2}</text>'.format(legend_x + 52, y + 5, escape(str(item["label"]))))

    lines.append('<text x="{0}" y="{1}" text-anchor="middle" font-size="14" font-family="Helvetica, Arial, sans-serif">{2}</text>'.format(width / 2.0, height - 10, escape(x_label)))
    lines.append('<text x="22" y="{0}" text-anchor="middle" font-size="14" font-family="Helvetica, Arial, sans-serif" transform="rotate(-90 22 {0})">{1}</text>'.format(height / 2.0, escape(y_label)))
    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def svg_grouped_bar_chart(path, title, x_label, y_label, categories, series):
    width = 1100
    height = 560
    left = 90
    right = 30
    top = 60
    bottom = 110
    plot_width = width - left - right
    plot_height = height - top - bottom

    max_y = 0.0
    for item in series:
        if item["values"]:
            max_y = max(max_y, max(item["values"]))
    if max_y <= 0.0:
        max_y = 1.0
    max_y *= 1.1

    def y_to_svg(value):
        return top + plot_height - (value / max_y) * plot_height

    group_width = plot_width / float(max(1, len(categories)))
    bar_width = min(40.0, group_width / float(max(2, len(series) + 1)))

    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="{0}" height="{1}" viewBox="0 0 {0} {1}">'.format(width, height),
        '<rect width="100%" height="100%" fill="#fffdf8"/>',
        '<text x="{0}" y="30" text-anchor="middle" font-size="22" font-family="Helvetica, Arial, sans-serif">{1}</text>'.format(
            width / 2.0, escape(title)
        ),
    ]

    for index in range(6):
        value = max_y * index / 5.0
        y = y_to_svg(value)
        lines.append('<line x1="{0}" y1="{1:.2f}" x2="{2}" y2="{1:.2f}" stroke="#d9d9d9" stroke-dasharray="4 4"/>'.format(left, y, width - right))
        lines.append('<text x="{0}" y="{1:.2f}" text-anchor="end" font-size="12" font-family="Helvetica, Arial, sans-serif">{2:.0f}</text>'.format(left - 10, y + 5, value))

    lines.append('<line x1="{0}" y1="{1}" x2="{0}" y2="{2}" stroke="#333333" stroke-width="2"/>'.format(left, top, top + plot_height))
    lines.append('<line x1="{0}" y1="{1}" x2="{2}" y2="{1}" stroke="#333333" stroke-width="2"/>'.format(left, top + plot_height, width - right))

    for cat_index, category in enumerate(categories):
        center_x = left + group_width * (cat_index + 0.5)
        for series_index, item in enumerate(series):
            values = item["values"]
            value = values[cat_index] if cat_index < len(values) else 0.0
            x = center_x + (series_index - (len(series) - 1) / 2.0) * (bar_width + 8) - bar_width / 2.0
            y = y_to_svg(value)
            height_value = top + plot_height - y
            lines.append('<rect x="{0:.2f}" y="{1:.2f}" width="{2:.2f}" height="{3:.2f}" fill="{4}"/>'.format(x, y, bar_width, height_value, item["color"]))

        lines.append('<text x="{0:.2f}" y="{1}" text-anchor="middle" font-size="11" font-family="Helvetica, Arial, sans-serif" transform="rotate(-25 {0:.2f} {1})">{2}</text>'.format(center_x, height - 60, escape(category)))

    legend_x = width - right - 220
    legend_y = top + 10
    lines.append('<rect x="{0}" y="{1}" width="200" height="{2}" fill="#ffffff" stroke="#cccccc"/>'.format(legend_x, legend_y, 28 * len(series) + 14))
    for index, item in enumerate(series):
        y = legend_y + 24 + index * 28
        lines.append('<rect x="{0}" y="{1}" width="20" height="14" fill="{2}"/>'.format(legend_x + 12, y - 11, item["color"]))
        lines.append('<text x="{0}" y="{1}" font-size="13" font-family="Helvetica, Arial, sans-serif">{2}</text>'.format(legend_x + 42, y, escape(str(item["label"]))))

    lines.append('<text x="{0}" y="{1}" text-anchor="middle" font-size="14" font-family="Helvetica, Arial, sans-serif">{2}</text>'.format(width / 2.0, height - 12, escape(x_label)))
    lines.append('<text x="22" y="{0}" text-anchor="middle" font-size="14" font-family="Helvetica, Arial, sans-serif" transform="rotate(-90 22 {0})">{1}</text>'.format(height / 2.0, escape(y_label)))
    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_runtime(path, time_summary):
    grouped = defaultdict(list)

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


def plot_speedup(path, speedup_summary):
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


def plot_perf(path, perf_summary):
    metric_labels = {
        "r0410:u": "SSE_FP",
        "r1010:u": "SSE_FP_PACKED",
        "r2010:u": "SSE_FP_SCALAR",
        "r4010:u": "SSE_SINGLE_PRECISION",
    }
    categories = []
    baseline_values = []
    auto_values = []

    sizes = sorted(set(int(row["size"]) for row in perf_summary))
    for size in sizes:
        for metric, label in metric_labels.items():
            categories.append("n={0} {1}".format(size, label))

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


def main():
    if len(sys.argv) not in (2, 3):
        print("usage: {0} TIME_CSV [PERF_CSV]".format(sys.argv[0]), file=sys.stderr)
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
