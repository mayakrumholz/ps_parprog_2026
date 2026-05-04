#!/usr/bin/env python3

import csv
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
CSV_PATH = RESULTS_DIR / "time_results.csv"
SUMMARY_CSV = RESULTS_DIR / "summary_stats.csv"
SUMMARY_TXT = RESULTS_DIR / "summary_report.txt"
PLOTS_DIR = RESULTS_DIR / "plots"
PLOT_PATH = PLOTS_DIR / "runtime_comparison.svg"


@dataclass
class Row:
    snippet: str
    variant: str
    threads: int
    run: int
    n: int
    seconds: float
    checksum: float
    aux: float


def load_rows() -> list[Row]:
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [
            Row(
                snippet=row["snippet"],
                variant=row["variant"],
                threads=int(row["threads"]),
                run=int(row["run"]),
                n=int(row["n"]),
                seconds=float(row["seconds"]),
                checksum=float(row["checksum"]),
                aux=float(row["aux"]),
            )
            for row in reader
        ]


def summarize(rows: list[Row]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, int], list[Row]] = defaultdict(list)
    baseline: dict[str, float] = {}

    for row in rows:
        grouped[(row.snippet, row.variant, row.threads)].append(row)
        if row.variant == "original":
            baseline[row.snippet] = row.seconds

    summaries: list[dict[str, object]] = []
    for key in sorted(grouped):
        snippet, variant, threads = key
        times = [row.seconds for row in grouped[key]]
        checksums = [row.checksum for row in grouped[key]]
        aux_values = [row.aux for row in grouped[key]]
        mean_seconds = statistics.fmean(times)
        speedup = baseline[snippet] / mean_seconds
        summaries.append(
            {
                "snippet": snippet,
                "variant": variant,
                "threads": threads,
                "runs": len(times),
                "mean_seconds": mean_seconds,
                "median_seconds": statistics.median(times),
                "min_seconds": min(times),
                "max_seconds": max(times),
                "stdev_seconds": statistics.stdev(times) if len(times) > 1 else 0.0,
                "mean_checksum": statistics.fmean(checksums),
                "mean_aux": statistics.fmean(aux_values),
                "speedup_vs_original": speedup,
            }
        )
    return summaries


def write_summary_csv(summaries: list[dict[str, object]]) -> None:
    with SUMMARY_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "snippet",
                "variant",
                "threads",
                "runs",
                "mean_seconds",
                "median_seconds",
                "min_seconds",
                "max_seconds",
                "stdev_seconds",
                "mean_checksum",
                "mean_aux",
                "speedup_vs_original",
            ]
        )
        for summary in summaries:
            writer.writerow(
                [
                    summary["snippet"],
                    summary["variant"],
                    summary["threads"],
                    summary["runs"],
                    f"{summary['mean_seconds']:.6f}",
                    f"{summary['median_seconds']:.6f}",
                    f"{summary['min_seconds']:.6f}",
                    f"{summary['max_seconds']:.6f}",
                    f"{summary['stdev_seconds']:.6f}",
                    f"{summary['mean_checksum']:.12f}",
                    f"{summary['mean_aux']:.12f}",
                    f"{summary['speedup_vs_original']:.6f}",
                ]
            )


def write_report(summaries: list[dict[str, object]]) -> None:
    lines = ["Assignment 07 - Exercise 1 Summary", ""]
    for snippet in sorted({summary["snippet"] for summary in summaries}):
        lines.append(snippet)
        for summary in [item for item in summaries if item["snippet"] == snippet]:
            lines.append(
                (
                    f"  {summary['variant']:8s} threads={summary['threads']:>2d} "
                    f"mean={summary['mean_seconds']:.6f}s "
                    f"speedup={summary['speedup_vs_original']:.3f} "
                    f"checksum={summary['mean_checksum']:.6f}"
                )
            )
        lines.append("")

    SUMMARY_TXT.write_text("\n".join(lines), encoding="utf-8")


def color_for(snippet: str) -> str:
    return {
        "snippet1": "#2563eb",
        "snippet2": "#d97706",
        "snippet3": "#059669",
    }[snippet]


def svg_plot(summaries: list[dict[str, object]]) -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    width = 1200
    height = 760
    left = 90
    top = 110
    plot_w = 980
    plot_h = 500

    ordered = [s for s in summaries if s["variant"] == "parallel"]
    max_value = max(float(s["mean_seconds"]) for s in summaries) * 1.1
    threads = sorted({int(s["threads"]) for s in ordered})

    def x_map(index: int) -> float:
        if len(threads) == 1:
            return left + plot_w / 2
        return left + index * plot_w / (len(threads) - 1)

    def y_map(value: float) -> float:
        return top + plot_h - (value / max_value) * plot_h

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#faf8f3"/>',
        "<style>",
        'text { font-family: Helvetica, Arial, sans-serif; fill: #1f2937; }',
        ".title { font-size: 24px; font-weight: 700; }",
        ".subtitle { font-size: 12px; fill: #4b5563; }",
        ".axis { stroke: #111827; stroke-width: 1.2; }",
        ".grid { stroke: #d1d5db; stroke-dasharray: 4 4; }",
        ".tick { font-size: 11px; fill: #4b5563; }",
        ".legend { font-size: 12px; }",
        "</style>",
        '<text class="title" x="90" y="52">Exercise 1 Runtime Comparison</text>',
        '<text class="subtitle" x="90" y="74">Parallel variants are compared against the serial baseline of each snippet.</text>',
    ]

    for step in range(6):
        value = max_value * step / 5
        y = y_map(value)
        lines.append(f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}"/>')
        lines.append(f'<text class="tick" x="{left - 10}" y="{y + 4:.1f}" text-anchor="end">{value:.2f}</text>')

    lines.append(f'<line class="axis" x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}"/>')
    lines.append(f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}"/>')

    for idx, thread in enumerate(threads):
        x = x_map(idx)
        lines.append(f'<text class="tick" x="{x:.1f}" y="{top + plot_h + 24}" text-anchor="middle">{thread}</text>')

    for snippet in sorted({s["snippet"] for s in ordered}):
        points = []
        color = color_for(snippet)
        baseline = next(s for s in summaries if s["snippet"] == snippet and s["variant"] == "original")
        baseline_y = y_map(float(baseline["mean_seconds"]))
        lines.append(
            f'<line x1="{left}" y1="{baseline_y:.1f}" x2="{left + plot_w}" y2="{baseline_y:.1f}" '
            f'stroke="{color}" stroke-dasharray="8 6" stroke-width="1.5" opacity="0.55"/>'
        )

        for idx, thread in enumerate(threads):
            summary = next(
                s for s in ordered if s["snippet"] == snippet and int(s["threads"]) == thread
            )
            x = x_map(idx)
            y = y_map(float(summary["mean_seconds"]))
            stdev = float(summary["stdev_seconds"])
            y_top = y_map(float(summary["mean_seconds"]) + stdev)
            y_bottom = y_map(max(float(summary["mean_seconds"]) - stdev, 0.0))
            lines.append(f'<line x1="{x:.1f}" y1="{y_top:.1f}" x2="{x:.1f}" y2="{y_bottom:.1f}" stroke="{color}" stroke-width="2"/>')
            lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{color}"/>')
            points.append(f"{x:.1f},{y:.1f}")

        lines.append(f'<polyline fill="none" stroke="{color}" stroke-width="3" points="{" ".join(points)}"/>')

    lines.append(f'<text x="{left + plot_w / 2:.1f}" y="{height - 46}" text-anchor="middle">Threads</text>')
    lines.append(
        f'<text x="28" y="{top + plot_h / 2:.1f}" transform="rotate(-90 28 {top + plot_h / 2:.1f})" text-anchor="middle">Runtime [s]</text>'
    )

    legend_x = 810
    legend_y = 58
    for idx, snippet in enumerate(sorted({s["snippet"] for s in ordered})):
        color = color_for(snippet)
        y = legend_y + idx * 24
        lines.append(f'<line x1="{legend_x}" y1="{y}" x2="{legend_x + 28}" y2="{y}" stroke="{color}" stroke-width="3"/>')
        lines.append(f'<circle cx="{legend_x + 14}" cy="{y}" r="5" fill="{color}"/>')
        lines.append(f'<text class="legend" x="{legend_x + 38}" y="{y + 4}">{snippet}</text>')

    lines.append("</svg>")
    PLOT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    rows = load_rows()
    summaries = summarize(rows)
    write_summary_csv(summaries)
    write_report(summaries)
    svg_plot(summaries)
    print(f"Wrote {SUMMARY_CSV}")
    print(f"Wrote {SUMMARY_TXT}")
    print(f"Wrote {PLOT_PATH}")


if __name__ == "__main__":
    main()
