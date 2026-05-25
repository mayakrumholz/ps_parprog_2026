#!/usr/bin/env python3

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path
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
        grouped[(row["variant"], row["type"])].append(float(row["elapsed_seconds"]))

    summary = []
    for (variant, type_name), values in sorted(grouped.items()):
        summary.append(
            {
                "variant": variant,
                "type": type_name,
                "runs": len(values),
                "mean_seconds": mean(values),
                "stddev_seconds": sample_stddev(values),
                "min_seconds": min(values),
                "max_seconds": max(values),
            }
        )

    return summary


def summarize_perf_rows(rows):
    grouped = defaultdict(list)
    units = {}

    for row in rows:
        key = (row["variant"], row["type"], row["metric"])
        grouped[key].append(float(row["value"]))
        units[key] = row["unit"]

    summary = []
    for (variant, type_name, metric), values in sorted(grouped.items()):
        summary.append(
            {
                "variant": variant,
                "type": type_name,
                "metric": metric,
                "unit": units[(variant, type_name, metric)],
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


def compute_comparisons(time_summary):
    mean_map = {}

    for row in time_summary:
        mean_map[row["variant"]] = float(row["mean_seconds"])

    comparisons = []

    if "baseline_float" in mean_map and "auto_float" in mean_map:
        comparisons.append(
            {
                "comparison": "float auto vs baseline",
                "reference": "baseline_float",
                "candidate": "auto_float",
                "speedup": mean_map["baseline_float"] / mean_map["auto_float"],
            }
        )

    if "baseline_float" in mean_map and "omp_simd_float" in mean_map:
        comparisons.append(
            {
                "comparison": "float omp simd vs baseline",
                "reference": "baseline_float",
                "candidate": "omp_simd_float",
                "speedup": mean_map["baseline_float"] / mean_map["omp_simd_float"],
            }
        )

    if "auto_float" in mean_map and "omp_simd_float" in mean_map:
        comparisons.append(
            {
                "comparison": "float omp simd vs auto",
                "reference": "auto_float",
                "candidate": "omp_simd_float",
                "speedup": mean_map["auto_float"] / mean_map["omp_simd_float"],
            }
        )

    if "baseline_double" in mean_map and "omp_simd_double" in mean_map:
        comparisons.append(
            {
                "comparison": "double omp simd vs baseline",
                "reference": "baseline_double",
                "candidate": "omp_simd_double",
                "speedup": mean_map["baseline_double"] / mean_map["omp_simd_double"],
            }
        )

    return comparisons


def write_summary_table(path, time_summary, comparisons):
    lines = [
        "# Exercise 2 Summary",
        "",
        "## Runtime Summary",
        "",
        "| Variant | Type | Runs | Mean [s] | Stddev [s] | Min [s] | Max [s] |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    for row in time_summary:
        lines.append(
            "| {variant} | {type_name} | {runs} | {meanv:.6f} | {stddev:.6f} | {minv:.6f} | {maxv:.6f} |".format(
                variant=row["variant"],
                type_name=row["type"],
                runs=row["runs"],
                meanv=float(row["mean_seconds"]),
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
            "| Comparison | Reference | Candidate | Speedup |",
            "| --- | --- | --- | ---: |",
        ]
    )

    for row in comparisons:
        lines.append(
            "| {comparison} | {reference} | {candidate} | {speedup:.3f} |".format(
                comparison=row["comparison"],
                reference=row["reference"],
                candidate=row["candidate"],
                speedup=float(row["speedup"]),
            )
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_perf_table(path, perf_summary):
    lines = [
        "# Perf Summary",
        "",
        "| Variant | Type | Metric | Mean value | Stddev | Unit |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]

    for row in perf_summary:
        lines.append(
            "| {variant} | {type_name} | {metric} | {meanv:.3f} | {stddev:.3f} | {unit} |".format(
                variant=row["variant"],
                type_name=row["type"],
                metric=row["metric"],
                meanv=float(row["mean_value"]),
                stddev=float(row["stddev_value"]),
                unit=row["unit"],
            )
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def svg_grouped_bar_chart(path, title, y_label, categories, series):
    width = 1000
    height = 560
    left = 90
    right = 30
    top = 60
    bottom = 120
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
    bar_width = min(70.0, group_width / float(max(2, len(series) + 1)))

    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="{0}" height="{1}" viewBox="0 0 {0} {1}">'.format(width, height),
        '<rect width="100%" height="100%" fill="#fffdf8"/>',
        '<text x="{0}" y="30" text-anchor="middle" font-size="22" font-family="Helvetica, Arial, sans-serif">{1}</text>'.format(width / 2.0, escape(title)),
    ]

    for index in range(6):
        value = max_y * index / 5.0
        y = y_to_svg(value)
        lines.append('<line x1="{0}" y1="{1:.2f}" x2="{2}" y2="{1:.2f}" stroke="#d9d9d9" stroke-dasharray="4 4"/>'.format(left, y, width - right))
        lines.append('<text x="{0}" y="{1:.2f}" text-anchor="end" font-size="12" font-family="Helvetica, Arial, sans-serif">{2:.3f}</text>'.format(left - 10, y + 5, value))

    lines.append('<line x1="{0}" y1="{1}" x2="{0}" y2="{2}" stroke="#333333" stroke-width="2"/>'.format(left, top, top + plot_height))
    lines.append('<line x1="{0}" y1="{1}" x2="{2}" y2="{1}" stroke="#333333" stroke-width="2"/>'.format(left, top + plot_height, width - right))

    for cat_index, category in enumerate(categories):
        center_x = left + group_width * (cat_index + 0.5)
        for series_index, item in enumerate(series):
            value = item["values"][cat_index] if cat_index < len(item["values"]) else 0.0
            x = center_x + (series_index - (len(series) - 1) / 2.0) * (bar_width + 8) - bar_width / 2.0
            y = y_to_svg(value)
            lines.append('<rect x="{0:.2f}" y="{1:.2f}" width="{2:.2f}" height="{3:.2f}" fill="{4}"/>'.format(x, y, bar_width, top + plot_height - y, item["color"]))

        lines.append('<text x="{0:.2f}" y="{1}" text-anchor="middle" font-size="12" font-family="Helvetica, Arial, sans-serif" transform="rotate(-18 {0:.2f} {1})">{2}</text>'.format(center_x, height - 65, escape(category)))

    legend_x = width - right - 240
    legend_y = top + 10
    lines.append('<rect x="{0}" y="{1}" width="220" height="{2}" fill="#ffffff" stroke="#cccccc"/>'.format(legend_x, legend_y, 28 * len(series) + 14))
    for index, item in enumerate(series):
        y = legend_y + 24 + index * 28
        lines.append('<rect x="{0}" y="{1}" width="20" height="14" fill="{2}"/>'.format(legend_x + 12, y - 11, item["color"]))
        lines.append('<text x="{0}" y="{1}" font-size="13" font-family="Helvetica, Arial, sans-serif">{2}</text>'.format(legend_x + 42, y, escape(item["label"])))

    lines.append('<text x="22" y="{0}" text-anchor="middle" font-size="14" font-family="Helvetica, Arial, sans-serif" transform="rotate(-90 22 {0})">{1}</text>'.format(height / 2.0, escape(y_label)))
    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_runtime(path, time_summary):
    categories = [row["variant"] for row in time_summary]
    values = [float(row["mean_seconds"]) for row in time_summary]
    series = [{"label": "mean runtime", "color": "#005f73", "values": values}]
    svg_grouped_bar_chart(path, "Runtime comparison for Exercise 2", "Mean runtime [s]", categories, series)


def plot_float_comparison(path, time_summary):
    mean_map = {}
    for row in time_summary:
        mean_map[row["variant"]] = float(row["mean_seconds"])

    categories = ["baseline_float", "auto_float", "omp_simd_float"]
    values = [mean_map.get(name, 0.0) for name in categories]
    series = [{"label": "float runtime", "color": "#9b2226", "values": values}]
    svg_grouped_bar_chart(path, "Float variants at size 2048", "Mean runtime [s]", categories, series)


def plot_perf(path, perf_summary):
    metric_labels = ["r1010:u", "r2010:u", "r4010:u", "r8010:u"]
    categories = []
    series_map = {}

    for row in perf_summary:
        series_map.setdefault(row["variant"], {})[row["metric"]] = float(row["mean_value"])

    for variant in ["baseline_float", "auto_float", "omp_simd_float", "baseline_double", "omp_simd_double"]:
        if variant in series_map:
            for metric in metric_labels:
                categories.append("{0} {1}".format(variant, metric))

    baseline_vals = []
    omp_vals = []
    auto_vals = []

    for metric in metric_labels:
        baseline_vals.append(series_map.get("baseline_float", {}).get(metric, 0.0))
        auto_vals.append(series_map.get("auto_float", {}).get(metric, 0.0))
        omp_vals.append(series_map.get("omp_simd_float", {}).get(metric, 0.0))
    for metric in metric_labels:
        baseline_vals.append(series_map.get("baseline_double", {}).get(metric, 0.0))
        auto_vals.append(0.0)
        omp_vals.append(series_map.get("omp_simd_double", {}).get(metric, 0.0))

    display_categories = []
    for metric in metric_labels:
        display_categories.append("float {0}".format(metric))
    for metric in metric_labels:
        display_categories.append("double {0}".format(metric))

    svg_grouped_bar_chart(
        path,
        "Perf event comparison for Exercise 2",
        "Mean event count",
        display_categories,
        [
            {"label": "baseline", "color": "#9b2226", "values": baseline_vals},
            {"label": "auto/omp reference", "color": "#94d2bd", "values": auto_vals},
            {"label": "omp simd", "color": "#005f73", "values": omp_vals},
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
    comparisons = compute_comparisons(time_summary)
    write_csv(
        results_dir / "summary_stats.csv",
        time_summary,
        ["variant", "type", "runs", "mean_seconds", "stddev_seconds", "min_seconds", "max_seconds"],
    )
    write_csv(
        results_dir / "speedup_stats.csv",
        comparisons,
        ["comparison", "reference", "candidate", "speedup"],
    )
    write_summary_table(results_dir / "summary_table.md", time_summary, comparisons)
    if time_summary:
        plot_runtime(plots_dir / "runtime_variants.svg", time_summary)
        plot_float_comparison(plots_dir / "float_variant_comparison.svg", time_summary)

    perf_rows = read_rows(perf_csv)
    perf_summary = summarize_perf_rows(perf_rows)
    if perf_summary:
        write_csv(
            results_dir / "perf_summary.csv",
            perf_summary,
            ["variant", "type", "metric", "unit", "mean_value", "stddev_value"],
        )
        write_perf_table(results_dir / "perf_summary.md", perf_summary)
        plot_perf(plots_dir / "perf_variant_events.svg", perf_summary)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
