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


def summarize_ex3_rows(rows):
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


def load_reference_means(root):
    ref = defaultdict(dict)

    ex1 = read_rows(root / "ex1" / "results" / "summary_stats.csv")
    for row in ex1:
        ref[int(row["size"])][row["variant"]] = float(row["mean_seconds"])

    ex2 = read_rows(root / "ex2" / "results" / "summary_stats.csv")
    for row in ex2:
        if row["variant"] == "omp_simd_float":
            ref[2048]["omp_simd_float"] = float(row["mean_seconds"])

    return ref


def summarize_comparison(ex3_summary, ref_means):
    rows = []
    for row in ex3_summary:
        size = int(row["size"])
        intrinsics = float(row["mean_seconds"])
        baseline = ref_means.get(size, {}).get("baseline")
        auto = ref_means.get(size, {}).get("auto_vectorized")
        omp = ref_means.get(size, {}).get("omp_simd_float") if size == 2048 else None
        rows.append(
            {
                "size": size,
                "intrinsics_mean_seconds": intrinsics,
                "baseline_mean_seconds": baseline,
                "auto_mean_seconds": auto,
                "omp_mean_seconds": omp,
                "speedup_vs_baseline": (baseline / intrinsics) if baseline else None,
                "speedup_vs_auto": (auto / intrinsics) if auto else None,
                "speedup_vs_omp": (omp / intrinsics) if omp else None,
            }
        )
    return rows


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


def write_summary_table(path, ex3_summary, comparison_summary):
    lines = [
        "# Exercise 3 Summary",
        "",
        "## Intrinsics Runtime Summary",
        "",
        "| Variant | Size | Runs | Mean [s] | Stddev [s] | Min [s] | Max [s] |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for row in ex3_summary:
        lines.append(
            "| {variant} | {size} | {runs} | {meanv:.6f} | {stddev:.6f} | {minv:.6f} | {maxv:.6f} |".format(
                variant=row["variant"],
                size=row["size"],
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
            "## Comparison Summary",
            "",
            "| Size | Baseline [s] | Auto [s] | OMP SIMD [s] | Intrinsics [s] | Speedup vs baseline | Speedup vs auto | Speedup vs OMP |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )

    for row in comparison_summary:
        def fmt(value):
            return "-" if value is None else "{0:.6f}".format(value)
        def fmt_speed(value):
            return "-" if value is None else "{0:.3f}".format(value)

        lines.append(
            "| {size} | {baseline} | {auto} | {omp} | {intrinsics} | {svb} | {sva} | {svo} |".format(
                size=row["size"],
                baseline=fmt(row["baseline_mean_seconds"]),
                auto=fmt(row["auto_mean_seconds"]),
                omp=fmt(row["omp_mean_seconds"]),
                intrinsics=fmt(row["intrinsics_mean_seconds"]),
                svb=fmt_speed(row["speedup_vs_baseline"]),
                sva=fmt_speed(row["speedup_vs_auto"]),
                svo=fmt_speed(row["speedup_vs_omp"]),
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


def svg_line_chart(path, title, y_label, series, y_reference=None):
    width = 920
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

    x_values = [p[0] for p in all_points]
    y_values = [p[1] for p in all_points]
    min_x = min(x_values)
    max_x = max(x_values)
    max_y = max(y_values + ([y_reference] if y_reference is not None else []))
    if max_y <= 0.0:
        max_y = 1.0
    max_y *= 1.1

    def x_to_svg(value):
        if max_x == min_x:
            return left + plot_width / 2.0
        return left + ((value - min_x) / float(max_x - min_x)) * plot_width

    def y_to_svg(value):
        return top + plot_height - (value / max_y) * plot_height

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

    for value in sorted(set(x_values)):
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
        lines.append('<polyline fill="none" stroke="{0}" stroke-width="3" points="{1}"/>'.format(item["color"], polyline))
        for x, y in item["points"]:
            lines.append('<circle cx="{0:.2f}" cy="{1:.2f}" r="4.5" fill="{2}" stroke="white" stroke-width="1.5"/>'.format(x_to_svg(x), y_to_svg(y), item["color"]))

    legend_x = width - right - 290
    legend_y = top + 10
    lines.append('<rect x="{0}" y="{1}" width="270" height="{2}" fill="#ffffff" stroke="#cccccc"/>'.format(legend_x, legend_y, 28 * len(series) + 14))
    for index, item in enumerate(series):
        y = legend_y + 24 + index * 28
        lines.append('<line x1="{0}" y1="{1}" x2="{2}" y2="{1}" stroke="{3}" stroke-width="3"/>'.format(legend_x + 12, y, legend_x + 42, item["color"]))
        lines.append('<text x="{0}" y="{1}" font-size="13" font-family="Helvetica, Arial, sans-serif">{2}</text>'.format(legend_x + 52, y + 5, escape(item["label"])))

    lines.append('<text x="22" y="{0}" text-anchor="middle" font-size="14" font-family="Helvetica, Arial, sans-serif" transform="rotate(-90 22 {0})">{1}</text>'.format(height / 2.0, escape(y_label)))
    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def plot_runtime(path, comparison_summary):
    baseline_points = []
    auto_points = []
    intr_points = []

    for row in comparison_summary:
        size = int(row["size"])
        if row["baseline_mean_seconds"] is not None:
            baseline_points.append((size, float(row["baseline_mean_seconds"])))
        if row["auto_mean_seconds"] is not None:
            auto_points.append((size, float(row["auto_mean_seconds"])))
        intr_points.append((size, float(row["intrinsics_mean_seconds"])))

    svg_line_chart(
        path,
        "Runtime comparison: baseline vs auto vs intrinsics",
        "Mean runtime [s]",
        [
            {"label": "baseline (-O1, no vectorization)", "color": "#9b2226", "points": baseline_points},
            {"label": "auto-vectorized", "color": "#0a9396", "points": auto_points},
            {"label": "intrinsics", "color": "#005f73", "points": intr_points},
        ],
    )


def plot_speedup(path, comparison_summary):
    baseline_points = []
    auto_points = []
    for row in comparison_summary:
        size = int(row["size"])
        if row["speedup_vs_baseline"] is not None:
            baseline_points.append((size, float(row["speedup_vs_baseline"])))
        if row["speedup_vs_auto"] is not None:
            auto_points.append((size, float(row["speedup_vs_auto"])))

    svg_line_chart(
        path,
        "Intrinsics speedup relative to previous variants",
        "Speedup",
        [
            {"label": "baseline / intrinsics", "color": "#9b2226", "points": baseline_points},
            {"label": "auto / intrinsics", "color": "#005f73", "points": auto_points},
        ],
        y_reference=1.0,
    )


def plot_perf(path, perf_summary, root):
    ex1_perf = read_rows(root / "ex1" / "results" / "perf_summary.csv")
    ex2_perf = read_rows(root / "ex2" / "results" / "perf_summary.csv")

    wanted = ["r1010:u", "r2010:u", "r4010:u"]
    series_map = {
        "baseline": {},
        "auto": {},
        "omp": {},
        "intrinsics": {},
    }

    for row in ex1_perf:
        if row["metric"] in wanted and int(row["size"]) == 2048:
            if row["variant"] == "baseline":
                series_map["baseline"][row["metric"]] = float(row["mean_value"])
            elif row["variant"] == "auto_vectorized":
                series_map["auto"][row["metric"]] = float(row["mean_value"])

    for row in ex2_perf:
        if row["metric"] in wanted and row["variant"] == "omp_simd_float":
            series_map["omp"][row["metric"]] = float(row["mean_value"])

    for row in perf_summary:
        if row["metric"] in wanted and int(row["size"]) == 2048:
            series_map["intrinsics"][row["metric"]] = float(row["mean_value"])

    categories = ["SSE_FP_PACKED", "SSE_FP_SCALAR", "SSE_SINGLE_PRECISION"]
    metric_map = {"SSE_FP_PACKED": "r1010:u", "SSE_FP_SCALAR": "r2010:u", "SSE_SINGLE_PRECISION": "r4010:u"}

    width = 1100
    height = 560
    left = 90
    right = 30
    top = 60
    bottom = 110
    plot_width = width - left - right
    plot_height = height - top - bottom
    group_width = plot_width / float(len(categories))
    series_order = [("baseline", "#9b2226"), ("auto", "#0a9396"), ("omp", "#94d2bd"), ("intrinsics", "#005f73")]
    max_y = 0.0
    for name, _color in series_order:
        for cat in categories:
            max_y = max(max_y, series_map[name].get(metric_map[cat], 0.0))
    if max_y <= 0.0:
        max_y = 1.0
    max_y *= 1.1

    def y_to_svg(value):
        return top + plot_height - (value / max_y) * plot_height

    bar_width = min(36.0, group_width / float(len(series_order) + 1))

    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="{0}" height="{1}" viewBox="0 0 {0} {1}">'.format(width, height),
        '<rect width="100%" height="100%" fill="#fffdf8"/>',
        '<text x="{0}" y="30" text-anchor="middle" font-size="22" font-family="Helvetica, Arial, sans-serif">{1}</text>'.format(width / 2.0, "Perf event comparison at size 2048"),
    ]

    for idx in range(6):
        value = max_y * idx / 5.0
        y = y_to_svg(value)
        lines.append('<line x1="{0}" y1="{1:.2f}" x2="{2}" y2="{1:.2f}" stroke="#d9d9d9" stroke-dasharray="4 4"/>'.format(left, y, width - right))
        lines.append('<text x="{0}" y="{1:.2f}" text-anchor="end" font-size="12" font-family="Helvetica, Arial, sans-serif">{2:.0f}</text>'.format(left - 10, y + 5, value))

    lines.append('<line x1="{0}" y1="{1}" x2="{0}" y2="{2}" stroke="#333333" stroke-width="2"/>'.format(left, top, top + plot_height))
    lines.append('<line x1="{0}" y1="{1}" x2="{2}" y2="{1}" stroke="#333333" stroke-width="2"/>'.format(left, top + plot_height, width - right))

    for cat_index, category in enumerate(categories):
        center_x = left + group_width * (cat_index + 0.5)
        for series_index, (name, color) in enumerate(series_order):
            value = series_map[name].get(metric_map[category], 0.0)
            x = center_x + (series_index - (len(series_order) - 1) / 2.0) * (bar_width + 8) - bar_width / 2.0
            y = y_to_svg(value)
            lines.append('<rect x="{0:.2f}" y="{1:.2f}" width="{2:.2f}" height="{3:.2f}" fill="{4}"/>'.format(x, y, bar_width, top + plot_height - y, color))
        lines.append('<text x="{0:.2f}" y="{1}" text-anchor="middle" font-size="12" font-family="Helvetica, Arial, sans-serif">{2}</text>'.format(center_x, height - 50, category))

    legend_x = width - right - 230
    legend_y = top + 10
    lines.append('<rect x="{0}" y="{1}" width="210" height="{2}" fill="#ffffff" stroke="#cccccc"/>'.format(legend_x, legend_y, 28 * len(series_order) + 14))
    for index, (name, color) in enumerate(series_order):
        y = legend_y + 24 + index * 28
        lines.append('<rect x="{0}" y="{1}" width="20" height="14" fill="{2}"/>'.format(legend_x + 12, y - 11, color))
        lines.append('<text x="{0}" y="{1}" font-size="13" font-family="Helvetica, Arial, sans-serif">{2}</text>'.format(legend_x + 42, y, escape(name)))

    lines.append("</svg>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    if len(sys.argv) not in (2, 3):
        print("usage: {0} TIME_CSV [PERF_CSV]".format(sys.argv[0]), file=sys.stderr)
        return 1

    time_csv = Path(sys.argv[1])
    perf_csv = Path(sys.argv[2]) if len(sys.argv) == 3 else Path("results/perf_results.csv")
    results_dir = time_csv.resolve().parent
    ex_root = results_dir.parent.parent
    plots_dir = results_dir / "plots"
    plots_dir.mkdir(parents=True, exist_ok=True)

    ex3_rows = read_rows(time_csv)
    ex3_summary = summarize_ex3_rows(ex3_rows)
    ref_means = load_reference_means(ex_root)
    comparison_summary = summarize_comparison(ex3_summary, ref_means)

    write_csv(results_dir / "summary_stats.csv", ex3_summary, ["variant", "size", "runs", "mean_seconds", "stddev_seconds", "min_seconds", "max_seconds"])
    write_csv(results_dir / "comparison_stats.csv", comparison_summary, ["size", "intrinsics_mean_seconds", "baseline_mean_seconds", "auto_mean_seconds", "omp_mean_seconds", "speedup_vs_baseline", "speedup_vs_auto", "speedup_vs_omp"])
    write_summary_table(results_dir / "summary_table.md", ex3_summary, comparison_summary)

    if comparison_summary:
        plot_runtime(plots_dir / "runtime_comparison.svg", comparison_summary)
        plot_speedup(plots_dir / "speedup_comparison.svg", comparison_summary)

    perf_rows = read_rows(perf_csv)
    perf_summary = summarize_perf_rows(perf_rows)
    if perf_summary:
        write_csv(results_dir / "perf_summary.csv", perf_summary, ["variant", "size", "metric", "unit", "mean_value", "stddev_value"])
        write_perf_table(results_dir / "perf_summary.md", perf_summary)
        plot_perf(plots_dir / "perf_event_comparison.svg", perf_summary, ex_root)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
