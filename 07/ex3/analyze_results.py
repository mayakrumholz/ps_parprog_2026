#!/usr/bin/env python3

import csv
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
CSV_PATH = RESULTS_DIR / "time_results.csv"
SUMMARY_CSV = RESULTS_DIR / "summary_stats.csv"
SUMMARY_TXT = RESULTS_DIR / "summary_report.txt"
PLOTS_DIR = RESULTS_DIR / "plots"
PLOT_PATH = PLOTS_DIR / "runtime_bar.svg"


def load_rows() -> list[dict[str, object]]:
    with CSV_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [
            {
                "variant": row["variant"],
                "threads": int(row["threads"]),
                "run": int(row["run"]),
                "rows": int(row["rows"]),
                "cols": int(row["cols"]),
                "seconds": float(row["seconds"]),
                "checksum": float(row["checksum"]),
                "aux": float(row["aux"]),
            }
            for row in reader
        ]


def summarize(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    variants = sorted({str(row["variant"]) for row in rows})
    baseline = statistics.fmean(float(row["seconds"]) for row in rows if row["variant"] == "original")
    summaries = []
    for variant in variants:
        times = [float(row["seconds"]) for row in rows if row["variant"] == variant]
        summaries.append(
            {
                "variant": variant,
                "threads": next(int(row["threads"]) for row in rows if row["variant"] == variant),
                "runs": len(times),
                "mean_seconds": statistics.fmean(times),
                "median_seconds": statistics.median(times),
                "min_seconds": min(times),
                "max_seconds": max(times),
                "stdev_seconds": statistics.stdev(times) if len(times) > 1 else 0.0,
                "mean_checksum": statistics.fmean(float(row["checksum"]) for row in rows if row["variant"] == variant),
                "speedup_vs_original": baseline / statistics.fmean(times),
            }
        )
    return summaries


def write_outputs(summaries: list[dict[str, object]]) -> None:
    with SUMMARY_CSV.open("w", newline="", encoding="utf-8") as handle:
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
                "mean_checksum",
                "speedup_vs_original",
            ]
        )
        for summary in summaries:
            writer.writerow(
                [
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

    lines = ["Assignment 07 - Exercise 3 Summary", ""]
    for summary in summaries:
        lines.append(
            f"{summary['variant']:8s} threads={summary['threads']} mean={summary['mean_seconds']:.6f}s speedup={summary['speedup_vs_original']:.3f}"
        )
    SUMMARY_TXT.write_text("\n".join(lines), encoding="utf-8")


def write_plot(summaries: list[dict[str, object]]) -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    width = 900
    height = 640
    left = 120
    top = 110
    plot_w = 660
    plot_h = 380
    max_value = max(float(summary["mean_seconds"]) for summary in summaries) * 1.2
    bar_width = 180
    gap = 120
    colors = {"original": "#2563eb", "parallel": "#059669"}

    def y_map(value: float) -> float:
        return top + plot_h - (value / max_value) * plot_h

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#fffaf0"/>',
        "<style>",
        'text { font-family: Helvetica, Arial, sans-serif; fill: #1f2937; }',
        ".title { font-size: 24px; font-weight: 700; }",
        ".subtitle { font-size: 12px; fill: #6b7280; }",
        ".axis { stroke: #111827; stroke-width: 1.2; }",
        ".grid { stroke: #d1d5db; stroke-dasharray: 4 4; }",
        ".tick { font-size: 11px; fill: #4b5563; }",
        "</style>",
        '<text class="title" x="120" y="52">Exercise 3 Runtime Comparison</text>',
        '<text class="subtitle" x="120" y="74">Original nested loop versus parity-based parallel execution.</text>',
    ]

    for step in range(6):
        value = max_value * step / 5
        y = y_map(value)
        lines.append(f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}"/>')
        lines.append(f'<text class="tick" x="{left - 10}" y="{y + 4:.1f}" text-anchor="end">{value:.2f}</text>')

    lines.append(f'<line class="axis" x1="{left}" y1="{top + plot_h}" x2="{left + plot_w}" y2="{top + plot_h}"/>')
    lines.append(f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_h}"/>')

    for idx, summary in enumerate(summaries):
        x = left + 100 + idx * (bar_width + gap)
        y = y_map(float(summary["mean_seconds"]))
        bar_h = top + plot_h - y
        color = colors[str(summary["variant"])]
        lines.append(f'<rect x="{x}" y="{y:.1f}" width="{bar_width}" height="{bar_h:.1f}" fill="{color}" opacity="0.88"/>')
        lines.append(f'<text x="{x + bar_width / 2:.1f}" y="{top + plot_h + 24}" text-anchor="middle">{summary["variant"]}</text>')
        lines.append(f'<text x="{x + bar_width / 2:.1f}" y="{y - 10:.1f}" text-anchor="middle">{summary["mean_seconds"]:.3f}s</text>')

    lines.append(f'<text x="{left + plot_w / 2:.1f}" y="{height - 54}" text-anchor="middle">Variant</text>')
    lines.append(f'<text x="38" y="{top + plot_h / 2:.1f}" transform="rotate(-90 38 {top + plot_h / 2:.1f})" text-anchor="middle">Runtime [s]</text>')
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
