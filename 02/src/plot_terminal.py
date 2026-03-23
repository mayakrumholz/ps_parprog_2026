# Mit ChatGPT generiert
#!/usr/bin/env python3

import argparse
import re
from dataclasses import dataclass
from html import escape
from pathlib import Path
from statistics import mean, stdev


COMMAND_RE = re.compile(r"OMP_NUM_THREADS=(\d+)\s+\./(\w+)")
CFLAGS_RE = re.compile(r"^CFLAGS\s*=\s*(.+)$")
RUN_RE = re.compile(r"^Run\s+(\d+):")
TIME_RE = re.compile(r"time:\s*([0-9]*\.?[0-9]+)\s+seconds")
COLORS = ["#5283a6", "#d62728", "#2ca02c", "#ff7f0e", "#9467bd", "#8c564b"]


@dataclass(frozen=True)
class Measurement:
    cflags: str
    run: int
    program: str
    threads: int
    time_seconds: float


def sanitize_label(label: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", label.strip())
    return cleaned.strip("_") or "default"


def parse_layout(lines: list[str]) -> tuple[list[str], list[int]]:
    commands: list[tuple[str, int]] = []
    seen = False

    for raw_line in lines:
        line = raw_line.strip()
        if CFLAGS_RE.match(line):
            break
        match = COMMAND_RE.match(line)
        if not match:
            if seen and line:
                break
            continue
        seen = True
        threads = int(match.group(1))
        program = match.group(2)
        commands.append((program, threads))

    if not commands:
        raise ValueError("Keine OMP_NUM_THREADS-Kommandos in terminal.txt gefunden.")

    programs: list[str] = []
    threads_by_program: dict[str, list[int]] = {}
    for program, threads in commands:
        if program not in threads_by_program:
            programs.append(program)
            threads_by_program[program] = []
        threads_by_program[program].append(threads)

    first_threads = threads_by_program[programs[0]]
    for program in programs[1:]:
        if threads_by_program[program] != first_threads:
            raise ValueError("Die Thread-Reihenfolge ist nicht fuer alle Programme identisch.")

    return programs, first_threads


def parse_measurements(lines: list[str], programs: list[str], threads: list[int]) -> list[Measurement]:
    expected_per_run = len(programs) * len(threads)
    measurements: list[Measurement] = []
    current_cflags: str | None = None
    current_run: int | None = None
    run_values: list[float] = []

    def flush_run() -> None:
        nonlocal run_values, current_run, current_cflags
        if current_cflags is None or current_run is None:
            run_values = []
            return
        if not run_values:
            return
        if len(run_values) != expected_per_run:
            raise ValueError(
                f"Run {current_run} fuer '{current_cflags}' hat {len(run_values)} Werte, "
                f"erwartet werden {expected_per_run}."
            )
        index = 0
        for program in programs:
            for thread_count in threads:
                measurements.append(
                    Measurement(
                        cflags=current_cflags,
                        run=current_run,
                        program=program,
                        threads=thread_count,
                        time_seconds=run_values[index],
                    )
                )
                index += 1
        run_values = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        cflags_match = CFLAGS_RE.match(line)
        if cflags_match:
            flush_run()
            current_cflags = cflags_match.group(1).strip()
            current_run = None
            continue

        run_match = RUN_RE.match(line)
        if run_match:
            flush_run()
            current_run = int(run_match.group(1))
            continue

        time_match = TIME_RE.search(line)
        if time_match and current_cflags is not None and current_run is not None:
            run_values.append(float(time_match.group(1)))

    flush_run()

    if not measurements:
        raise ValueError("Keine Messwerte in terminal.txt gefunden.")

    return measurements


def mean_stddev(values: list[float]) -> tuple[float, float]:
    avg = mean(values)
    if len(values) < 2:
        return avg, 0.0
    return avg, stdev(values)


def smallest_positive_time(grouped: dict[str, dict[int, list[float]]]) -> float:
    candidates = [
        value
        for by_threads in grouped.values()
        for values in by_threads.values()
        for value in values
        if value > 0.0
    ]
    return min(candidates) if candidates else 1e-9


def safe_average(values: list[float], floor: float) -> float:
    return max(mean(values), floor)


def group_measurements(
    measurements: list[Measurement],
) -> dict[str, dict[str, dict[int, list[float]]]]:
    grouped: dict[str, dict[str, dict[int, list[float]]]] = {}
    for item in measurements:
        grouped.setdefault(item.cflags, {}).setdefault(item.program, {}).setdefault(item.threads, []).append(
            item.time_seconds
        )
    return grouped


def svg_text(x: float, y: float, text: str, size: int = 14, anchor: str = "middle", weight: str = "normal") -> str:
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" text-anchor="{anchor}" '
        f'font-family="Helvetica, Arial, sans-serif" font-weight="{weight}">{escape(text)}</text>'
    )


def svg_line(x1: float, y1: float, x2: float, y2: float, color: str = "#333", width: float = 1.5, dash: str = "") -> str:
    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
        f'stroke="{color}" stroke-width="{width}"{dash_attr}/>'
    )


def svg_circle(x: float, y: float, r: float, color: str) -> str:
    return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r}" fill="{color}"/>'


def svg_rect(x: float, y: float, width: float, height: float, stroke: str = "#333", fill: str = "none") -> str:
    return (
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" '
        f'stroke="{stroke}" fill="{fill}" stroke-width="1.5"/>'
    )


def svg_polyline(points: list[tuple[float, float]], color: str, width: float = 2.5) -> str:
    serialized = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return f'<polyline fill="none" stroke="{color}" stroke-width="{width}" points="{serialized}"/>'


def quantile(sorted_values: list[float], q: float) -> float:
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = (len(sorted_values) - 1) * q
    lower = int(pos)
    upper = min(lower + 1, len(sorted_values) - 1)
    fraction = pos - lower
    return sorted_values[lower] + (sorted_values[upper] - sorted_values[lower]) * fraction


def build_chart_frame(
    width: int,
    height: int,
    title: str,
    x_label: str,
    y_label: str,
    x_ticks: list[int],
    y_min: float,
    y_max: float,
    y_ticks: int = 6,
) -> tuple[list[str], callable, dict[str, float]]:
    margin_left = 90
    margin_right = 30
    margin_top = 60
    margin_bottom = 70
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom
    x_min = min(x_ticks)
    x_max = max(x_ticks)

    if abs(y_max - y_min) < 1e-12:
        y_max = y_min + 1.0

    def map_x(x_value: float) -> float:
        if x_max == x_min:
            return margin_left + plot_width / 2
        return margin_left + ((x_value - x_min) / (x_max - x_min)) * plot_width

    def map_y(y_value: float) -> float:
        return margin_top + plot_height - ((y_value - y_min) / (y_max - y_min)) * plot_height

    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        svg_text(width / 2, 28, title, size=20, weight="bold"),
        svg_line(margin_left, margin_top, margin_left, margin_top + plot_height),
        svg_line(margin_left, margin_top + plot_height, margin_left + plot_width, margin_top + plot_height),
        svg_text(width / 2, height - 18, x_label, size=15),
        f'<text x="24" y="{margin_top + plot_height / 2:.2f}" font-size="15" '
        f'font-family="Helvetica, Arial, sans-serif" transform="rotate(-90 24 {margin_top + plot_height / 2:.2f})">{escape(y_label)}</text>',
    ]

    for index in range(y_ticks + 1):
        value = y_min + (y_max - y_min) * (index / y_ticks)
        y = map_y(value)
        elements.append(svg_line(margin_left, y, margin_left + plot_width, y, color="#d9d9d9", width=1, dash="4 4"))
        elements.append(svg_text(margin_left - 10, y + 5, f"{value:.3f}", size=11, anchor="end"))

    for tick in x_ticks:
        x = map_x(tick)
        elements.append(svg_line(x, margin_top + plot_height, x, margin_top + plot_height + 6))
        elements.append(svg_text(x, margin_top + plot_height + 24, str(tick), size=12))

    return elements, (lambda value_x, value_y: (map_x(value_x), map_y(value_y))), {
        "margin_left": margin_left,
        "margin_top": margin_top,
        "plot_width": plot_width,
        "plot_height": plot_height,
    }


def create_runtime_plot(
    cflags: str,
    grouped: dict[str, dict[int, list[float]]],
    threads: list[int],
    output_path: Path,
) -> None:
    width = 900
    height = 560
    y_max = max(mean_stddev(grouped[program][t])[0] + mean_stddev(grouped[program][t])[1] for program in grouped for t in threads)
    elements, mapper, frame = build_chart_frame(width, height, f"Laufzeit vs. Threads ({cflags})", "Threads", "Zeit [s]", threads, 0.0, y_max * 1.1)

    legend_x = frame["margin_left"] + frame["plot_width"] - 150
    legend_y = frame["margin_top"] + 10

    for index, program in enumerate(grouped):
        color = COLORS[index % len(COLORS)]
        by_threads = grouped[program]
        averages = [mean(by_threads[t]) for t in threads]
        deviations = [mean_stddev(by_threads[t])[1] for t in threads]
        points = [mapper(t, avg) for t, avg in zip(threads, averages)]
        elements.append(svg_polyline(points, color))

        for thread_count, avg, dev in zip(threads, averages, deviations):
            x, y = mapper(thread_count, avg)
            _, y_low = mapper(thread_count, max(0.0, avg - dev))
            _, y_high = mapper(thread_count, avg + dev)
            elements.append(svg_line(x, y_low, x, y_high, color=color))
            elements.append(svg_line(x - 5, y_low, x + 5, y_low, color=color))
            elements.append(svg_line(x - 5, y_high, x + 5, y_high, color=color))
            elements.append(svg_circle(x, y, 4, color))

        y_legend = legend_y + index * 22
        elements.append(svg_line(legend_x, y_legend, legend_x + 18, y_legend, color=color, width=2.5))
        elements.append(svg_circle(legend_x + 9, y_legend, 3.5, color))
        elements.append(svg_text(legend_x + 28, y_legend + 4, program, size=12, anchor="start"))

    elements.append("</svg>")
    output_path.write_text("\n".join(elements), encoding="utf-8")


def create_speedup_plot(
    cflags: str,
    grouped: dict[str, dict[int, list[float]]],
    threads: list[int],
    output_path: Path,
) -> None:
    width = 900
    height = 560
    speedups_by_program: dict[str, list[float]] = {}
    y_max = max(threads)
    floor = smallest_positive_time(grouped)
    for program, by_threads in grouped.items():
        baseline = safe_average(by_threads[threads[0]], floor)
        speedups = [baseline / safe_average(by_threads[t], floor) for t in threads]
        speedups_by_program[program] = speedups
        y_max = max(y_max, max(speedups))

    elements, mapper, frame = build_chart_frame(
        width, height, f"Speedup vs. Threads ({cflags})", "Threads", "Speedup T(1) / T(p)", threads, 0.0, y_max * 1.1
    )
    ideal_points = [mapper(t, t) for t in threads]
    elements.append(svg_polyline(ideal_points, "#111111", width=1.7).replace("/>", ' stroke-dasharray="6 4"/>'))

    legend_x = frame["margin_left"] + frame["plot_width"] - 170
    legend_y = frame["margin_top"] + 10

    for index, program in enumerate(grouped):
        color = COLORS[index % len(COLORS)]
        points = [mapper(t, s) for t, s in zip(threads, speedups_by_program[program])]
        elements.append(svg_polyline(points, color))
        for x, y in points:
            elements.append(svg_circle(x, y, 4, color))

        y_legend = legend_y + index * 22
        elements.append(svg_line(legend_x, y_legend, legend_x + 18, y_legend, color=color, width=2.5))
        elements.append(svg_circle(legend_x + 9, y_legend, 3.5, color))
        elements.append(svg_text(legend_x + 28, y_legend + 4, program, size=12, anchor="start"))

    ideal_y = legend_y + len(grouped) * 22
    elements.append(svg_line(legend_x, ideal_y, legend_x + 18, ideal_y, color="#111111", width=1.7, dash="6 4"))
    elements.append(svg_text(legend_x + 28, ideal_y + 4, "Idealer Speedup", size=12, anchor="start"))
    elements.append("</svg>")
    output_path.write_text("\n".join(elements), encoding="utf-8")


def create_stability_plot(
    cflags: str,
    grouped: dict[str, dict[int, list[float]]],
    threads: list[int],
    output_path: Path,
) -> None:
    programs = list(grouped.keys())
    width = 960
    row_height = 240
    height = 50 + row_height * len(programs)
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        svg_text(width / 2, 28, f"Messstreuung ueber alle Runs ({cflags})", size=20, weight="bold"),
    ]

    margin_left = 90
    margin_right = 30
    subplot_width = width - margin_left - margin_right

    for row, program in enumerate(programs):
        top = 50 + row * row_height
        plot_height = 150
        series = [grouped[program][t] for t in threads]
        flat_values = [value for values in series for value in values]
        y_min = min(flat_values)
        y_max = max(flat_values)
        if abs(y_max - y_min) < 1e-12:
            y_max = y_min + 1.0

        def map_y(value: float) -> float:
            return top + plot_height - ((value - y_min) / (y_max - y_min)) * plot_height

        def map_x(position: int) -> float:
            if len(threads) == 1:
                return margin_left + subplot_width / 2
            return margin_left + (position / (len(threads) - 1)) * subplot_width

        elements.append(svg_text(width / 2, top + 12, program, size=16, weight="bold"))
        elements.append(svg_line(margin_left, top + 20, margin_left, top + plot_height))
        elements.append(svg_line(margin_left, top + plot_height, margin_left + subplot_width, top + plot_height))

        for index in range(5):
            value = y_min + (y_max - y_min) * (index / 4)
            y = map_y(value)
            elements.append(svg_line(margin_left, y, margin_left + subplot_width, y, color="#d9d9d9", width=1, dash="4 4"))
            elements.append(svg_text(margin_left - 10, y + 4, f"{value:.3f}", size=11, anchor="end"))

        for position, (thread_count, values) in enumerate(zip(threads, series)):
            sorted_values = sorted(values)
            minimum = sorted_values[0]
            q1 = quantile(sorted_values, 0.25)
            median = quantile(sorted_values, 0.5)
            q3 = quantile(sorted_values, 0.75)
            maximum = sorted_values[-1]
            x = map_x(position)
            box_width = min(44, subplot_width / max(len(threads) * 2.5, 1))

            elements.append(svg_line(x, map_y(minimum), x, map_y(maximum), color="#555"))
            elements.append(svg_line(x - 10, map_y(minimum), x + 10, map_y(minimum), color="#555"))
            elements.append(svg_line(x - 10, map_y(maximum), x + 10, map_y(maximum), color="#555"))
            elements.append(svg_rect(x - box_width / 2, map_y(q3), box_width, map_y(q1) - map_y(q3), stroke="#1f77b4", fill="#cfe3f6"))
            elements.append(svg_line(x - box_width / 2, map_y(median), x + box_width / 2, map_y(median), color="#d62728", width=2))
            elements.append(svg_text(x, top + plot_height + 24, str(thread_count), size=12))

        elements.append(svg_text(24, top + plot_height / 2, "Zeit [s]", size=14))
        if row == len(programs) - 1:
            elements.append(svg_text(width / 2, height - 16, "Threads", size=15))

    elements.append("</svg>")
    output_path.write_text("\n".join(elements), encoding="utf-8")


def create_flag_comparison_plot(
    grouped: dict[str, dict[str, dict[int, list[float]]]],
    threads: list[int],
    output_path: Path,
) -> None:
    cflags_list = list(grouped.keys())
    programs = list(next(iter(grouped.values())).keys())
    width = 1100
    row_height = 270
    height = 70 + row_height * len(programs)
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        svg_text(width / 2, 30, "Vergleich der Compiler-Flags", size=22, weight="bold"),
        svg_text(width / 2, 52, "Mittelwerte ueber alle Runs, eine Linie pro Thread-Zahl", size=13),
    ]

    margin_left = 100
    margin_right = 40
    subplot_width = width - margin_left - margin_right

    for row, program in enumerate(programs):
        top = 80 + row * row_height
        plot_height = 165
        all_values = [
            mean(grouped[cflags][program][thread_count])
            for cflags in cflags_list
            for thread_count in threads
        ]
        y_min = 0.0
        y_max = max(all_values) * 1.1
        if abs(y_max - y_min) < 1e-12:
            y_max = y_min + 1.0

        def map_y(value: float) -> float:
            return top + plot_height - ((value - y_min) / (y_max - y_min)) * plot_height

        def map_x(position: int) -> float:
            if len(cflags_list) == 1:
                return margin_left + subplot_width / 2
            return margin_left + (position / (len(cflags_list) - 1)) * subplot_width

        elements.append(svg_text(width / 2, top - 12, program, size=17, weight="bold"))
        elements.append(svg_line(margin_left, top, margin_left, top + plot_height))
        elements.append(svg_line(margin_left, top + plot_height, margin_left + subplot_width, top + plot_height))

        for index in range(6):
            value = y_min + (y_max - y_min) * (index / 5)
            y = map_y(value)
            elements.append(svg_line(margin_left, y, margin_left + subplot_width, y, color="#d9d9d9", width=1, dash="4 4"))
            elements.append(svg_text(margin_left - 10, y + 4, f"{value:.3f}", size=11, anchor="end"))

        for position, cflags in enumerate(cflags_list):
            x = map_x(position)
            label = sanitize_label(cflags).replace("_", "\n")
            elements.append(svg_line(x, top + plot_height, x, top + plot_height + 6))
            for line_index, part in enumerate(label.splitlines()):
                elements.append(svg_text(x, top + plot_height + 22 + line_index * 13, part, size=11))

        for thread_index, thread_count in enumerate(threads):
            color = COLORS[thread_index % len(COLORS)]
            points = []
            for position, cflags in enumerate(cflags_list):
                x = map_x(position)
                y = map_y(mean(grouped[cflags][program][thread_count]))
                points.append((x, y))
            elements.append(svg_polyline(points, color))
            for x, y in points:
                elements.append(svg_circle(x, y, 4, color))

        legend_x = margin_left + subplot_width - 120
        legend_y = top + 12
        for thread_index, thread_count in enumerate(threads):
            color = COLORS[thread_index % len(COLORS)]
            y = legend_y + thread_index * 18
            elements.append(svg_line(legend_x, y, legend_x + 18, y, color=color, width=2.5))
            elements.append(svg_circle(legend_x + 9, y, 3.5, color))
            elements.append(svg_text(legend_x + 28, y + 4, f"{thread_count} Threads", size=12, anchor="start"))

        elements.append(svg_text(30, top + plot_height / 2, "Zeit [s]", size=14))

    elements.append(svg_text(width / 2, height - 12, "Compiler-Flags", size=15))
    elements.append("</svg>")
    output_path.write_text("\n".join(elements), encoding="utf-8")


def print_summary(grouped: dict[str, dict[str, dict[int, list[float]]]], threads: list[int]) -> None:
    for cflags, programs in grouped.items():
        print(f"\n=== {cflags} ===")
        for program, by_threads in programs.items():
            print(f"{program}:")
            for thread_count in threads:
                avg, dev = mean_stddev(by_threads[thread_count])
                print(f"  threads={thread_count:<2} mean={avg:.6f}s stddev={dev:.6f}s")


def main() -> None:
    parser = argparse.ArgumentParser(description="Erstellt Diagramme aus terminal.txt-Messdaten.")
    parser.add_argument(
        "input_file",
        nargs="?",
        default="terminal.txt",
        help="Pfad zur terminal.txt-Datei",
    )
    parser.add_argument(
        "--output-dir",
        default="plots",
        help="Verzeichnis fuer die erzeugten Grafiken",
    )
    args = parser.parse_args()

    input_path = Path(args.input_file)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    lines = input_path.read_text(encoding="utf-8").splitlines()
    programs, threads = parse_layout(lines)
    measurements = parse_measurements(lines, programs, threads)
    grouped = group_measurements(measurements)

    for cflags, program_data in grouped.items():
        suffix = sanitize_label(cflags)
        create_runtime_plot(cflags, program_data, threads, output_dir / f"runtime_{suffix}.svg")
        create_speedup_plot(cflags, program_data, threads, output_dir / f"speedup_{suffix}.svg")
        create_stability_plot(cflags, program_data, threads, output_dir / f"stability_{suffix}.svg")

    create_flag_comparison_plot(grouped, threads, output_dir / "comparison_by_flags.svg")
    print_summary(grouped, threads)
    print(f"\nGrafiken gespeichert in: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
