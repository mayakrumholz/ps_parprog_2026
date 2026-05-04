#!/usr/bin/env python3

import csv
import statistics
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
CSV_PATH = RESULTS_DIR / "time_results.csv"
SUMMARY_CSV = RESULTS_DIR / "summary_stats.csv"
SUMMARY_TXT = RESULTS_DIR / "summary_report.txt"
PLOTS_DIR = RESULTS_DIR / "plots"
PLOT_PATH = PLOTS_DIR / "runtime_comparison.svg"


def load_rows() -> list[dict[str, object]]:
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "case": row["case"],
                "variant": row["variant"],
                "threads": int(row["threads"]),
                "run": int(row["run"]),
                "n": int(row["n"]),
                "seconds": float(row["seconds"]),
                "checksum": float(row["checksum"]),
                "aux": float(row["aux"]),
            }
            for row in reader
        ]


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, int], list[dict[str, object]]] = defaultdict(list)
    baseline: dict[str, float] = {}
    for row in rows:
        grouped[(str(row["case"]), str(row["variant"]), int(row["threads"]))].append(row)
        if row["variant"] == "original":
            baseline[str(row["case"])] = float(row["seconds"])

    summaries: list[dict[str, object]] = []
    for key in sorted(grouped):
        case_name, variant, threads = key
        times = [float(row["seconds"]) for row in grouped[key]]
        summaries.append(
            {
                "case": case_name,
                "variant": variant,
                "threads": threads,
                "runs": len(times),
                "mean_seconds": statistics.fmean(times),
                "median_seconds": statistics.median(times),
                "min_seconds": min(times),
                "max_seconds": max(times),
                "stdev_seconds": statistics.stdev(times) if len(times) > 1 else 0.0,
                "mean_checksum": statistics.fmean(float(row["checksum"]) for row in grouped[key]),
                "speedup_vs_original": baseline[case_name] / statistics.fmean(times),
            }
        )
    return summaries


def write_outputs(summaries: list[dict[str, object]]) -> None:
    with SUMMARY_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "case",
                "variant",
                "threads",
                "runs",
                "mean_seconds",
                "median_seconds",
                "min_seconds",
                "max_seconds",
                "stdev_seconds",
                "mean_checksum",
                "speedup_vs_original",
            ]
        )
        for summary in summaries:
            writer.writerow(
                [
                    summary["case"],
                    summary["variant"],
                    summary["threads"],
                    summary["runs"],
                    f"{summary['mean_seconds']:.6f}",
                    f"{summary['median_seconds']:.6f}",
                    f"{summary['min_seconds']:.6f}",
                    f"{summary['max_seconds']:.6f}",
                    f"{summary['stdev_seconds']:.6f}",
                    f"{summary['mean_checksum']:.12f}",
                    f"{summary['speedup_vs_original']:.6f}",
                ]
            )

    lines = ["Assignment 07 - Exercise 2 Summary", ""]
    for case_name in sorted({str(summary["case"]) for summary in summaries}):
        lines.append(case_name)
        for summary in [item for item in summaries if item["case"] == case_name]:
            lines.append(
                f"  {summary['variant']:8s} threads={summary['threads']:>2d} mean={summary['mean_seconds']:.6f}s speedup={summary['speedup_vs_original']:.3f}"
            )
        lines.append("")
    SUMMARY_TXT.write_text("\n".join(lines), encoding="utf-8")


def color_for(case_name: str) -> str:
    return {
        "case_a": "#2563eb",
        "case_b": "#dc2626",
        "case_c_twice0": "#059669",
        "case_c_twice1": "#7c3aed",
    }[case_name]


def write_plot(summaries: list[dict[str, object]]) -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    width = 1240
    height = 780
    left = 90
    top = 110
    plot_w = 1020
    plot_h = 520
    parallel = [s for s in summaries if s["variant"] == "parallel"]
    threads = sorted({int(s["threads"]) for s in parallel})
    max_value = max(float(s["mean_seconds"]) for s in summaries) * 1.1

    def x_map(index: int) -> float:
        if len(threads) == 1:
            return left + plot_w / 2
        return left + index * plot_w / (len(threads) - 1)

    def y_map(value: float) -> float:
        return top + plot_h - (value / max_value) * plot_h

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        "<style>",
        'text { font-family: Helvetica, Arial, sans-serif; fill: #0f172a; }',
        ".title { font-size: 24px; font-weight: 700; }",
        ".subtitle { font-size: 12px; fill: #475569; }",
        ".axis { stroke: #0f172a; stroke-width: 1.2; }",
        ".grid { stroke: #cbd5e1; stroke-dasharray: 4 4; }",
        ".tick { font-size: 11px; fill: #475569; }",
        ".legend { font-size: 12px; }",
        "</style>",
        '<text class="title" x="90" y="52">Exercise 2 Runtime Comparison</text>',
        '<text class="subtitle" x="90" y="74">Each transformed loop version is benchmarked against the original serial dependency-carrying code.</text>',
    ]

    for step in range(6):
        value = max_value * step / 5
        y = y_map(value)
        lines.append(f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}"/>')
        lines.append(f'<text class="tick" x="{left - 10}" y="{y + 4:.1f}" text-anchor="end">{value:.2f}</text>')

    lines.append(f'<line class="axis" x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}"/>')
    lines.append(f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}"/>')

    for idx, thread in enumerate(threads):
        lines.append(f'<text class="tick" x="{x_map(idx):.1f}" y="{top + plot_h + 24}" text-anchor="middle">{thread}</text>')

    case_names = sorted({str(s["case"]) for s in parallel})
    for case_name in case_names:
        color = color_for(case_name)
        baseline = next(s for s in summaries if s["case"] == case_name and s["variant"] == "original")
        base_y = y_map(float(baseline["mean_seconds"]))
        lines.append(
            f'<line x1="{left}" y1="{base_y:.1f}" x2="{left + plot_w}" y2="{base_y:.1f}" stroke="{color}" stroke-dasharray="8 6" stroke-width="1.5" opacity="0.55"/>'
        )
        points = []
        for idx, thread in enumerate(threads):
            summary = next(s for s in parallel if s["case"] == case_name and int(s["threads"]) == thread)
            x = x_map(idx)
            y = y_map(float(summary["mean_seconds"]))
            y_top = y_map(float(summary["mean_seconds"]) + float(summary["stdev_seconds"]))
            y_bottom = y_map(max(float(summary["mean_seconds"]) - float(summary["stdev_seconds"]), 0.0))
            lines.append(f'<line x1="{x:.1f}" y1="{y_top:.1f}" x2="{x:.1f}" y2="{y_bottom:.1f}" stroke="{color}" stroke-width="2"/>')
            lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{color}"/>')
            points.append(f"{x:.1f},{y:.1f}")
        lines.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{" ".join(points)}"/>')

    lines.append(f'<text x="{left + plot_w / 2:.1f}" y="{height - 44}" text-anchor="middle">Threads</text>')
    lines.append(f'<text x="28" y="{top + plot_h / 2:.1f}" transform="rotate(-90 28 {top + plot_h / 2:.1f})" text-anchor="middle">Runtime [s]</text>')

    legend_x = 850
    legend_y = 58
    for idx, case_name in enumerate(case_names):
        color = color_for(case_name)
        y = legend_y + idx * 24
        lines.append(f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 28}" y2="{y}" stroke="{color}" stroke-width="3"/>')
        lines.append(f'<circle cx="{legend_x + 14}" cy="{y}" r="5" fill="{color}"/>')
        lines.append(f'<text class="legend" x="{legend_x + 38}" y="{y + 4}">{case_name}</text>')

    lines.append("</svg>")
    PLOT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    rows = load_rows()
    summaries = summarize(rows)
    write_outputs(summaries)
    write_plot(summaries)
    print(f"Wrote {SUMMARY_CSV}")
    print(f"Wrote {SUMMARY_TXT}")
    print(f"Wrote {PLOT_PATH}")


if __name__ == "__main__":
    main()
