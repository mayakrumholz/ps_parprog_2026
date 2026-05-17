from pathlib import Path
from collections import Counter
import re
import matplotlib.pyplot as plt


# Change this if your file has a different name
INPUT_FILE = Path("vec-analysis.out")


def read_output(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Could not find file: {path}")
    return path.read_text(errors="replace")


def extract_loop_blocks(text: str):
    """
    Splits GCC vectorization output into blocks starting with:
    'Analyzing loop at analysis.c:<line>'
    """
    matches = list(re.finditer(r"Analyzing loop at analysis\.c:(\d+)", text))

    loop_blocks = []

    for index, match in enumerate(matches):
        line_number = int(match.group(1))
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)

        block = text[start:end]
        loop_blocks.append((line_number, block))

    return loop_blocks


def classify_loop(block: str):
    """
    Classifies one analyzed loop as vectorized or not vectorized.
    Also tries to identify the main reason.
    """
    if "LOOP VECTORIZED" in block or "optimized: loop vectorized" in block:
        return "vectorized", "success"

    if "bad data dependence" in block:
        return "not vectorized", "bad data dependence"

    if "possible alias" in block:
        return "not vectorized", "possible alias"

    if "clobbers memory" in block or "function calls" in block or "printf" in block:
        return "not vectorized", "function call / memory clobber"

    if "not consecutive access" in block:
        return "not vectorized", "non-consecutive memory access"

    return "not vectorized", "other reason"


def build_loop_summary(loop_blocks):
    """
    Creates a list with one entry per analyzed source-code loop.
    """
    rows = []

    for line, block in loop_blocks:
        status, reason = classify_loop(block)

        rows.append({
            "location": f"analysis.c:{line}",
            "status": status,
            "reason": reason,
        })

    # Sort by source line number
    rows.sort(key=lambda row: int(row["location"].split(":")[1]))

    return rows


def plot_loop_decision_table(loop_blocks):
    """
    Plot 1:
    Creates a table-style figure showing the compiler decision for each loop.

    This is clearer than a 0/1 bar plot because failed loops do not disappear.
    """
    rows = build_loop_summary(loop_blocks)

    table_data = [
        [row["location"], row["status"], row["reason"]]
        for row in rows
    ]

    column_labels = ["Source location", "Compiler decision", "Main reason"]

    fig, ax = plt.subplots(figsize=(10, 2.8))
    ax.axis("off")

    table = ax.table(
        cellText=table_data,
        colLabels=column_labels,
        cellLoc="left",
        colLoc="left",
        loc="center",
    )

    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.6)

    # Make header row bold
    for column_index in range(len(column_labels)):
        table[(0, column_index)].set_text_props(weight="bold")

    plt.title("Vectorization decision for each analyzed loop", pad=20)
    plt.tight_layout()

    plt.savefig("plot_1_vectorization_decision_table.png", dpi=200)
    plt.close()


def plot_missed_reasons(text: str):
    """
    Plot 2:
    Counts common reasons for missed vectorization.

    Important:
    These are diagnostic message counts, not distinct loop counts.
    One loop can produce several related messages.
    """
    reason_patterns = {
        "bad data\ndependence": r"bad data dependence",
        "possible\nalias": r"possible alias",
        "function call /\nmemory clobber": r"clobbers memory|function calls|printf",
        "non-consecutive\naccess": r"not consecutive access",
        "no vector\ntype": r"no vectype",
        "not affine\noffset": r"not affine|evolution of offset is not affine",
        "no grouped\nstores": r"no grouped stores",
    }

    counts = Counter()

    for reason, pattern in reason_patterns.items():
        counts[reason] = len(re.findall(pattern, text))

    # Remove categories that do not occur
    counts = Counter({key: value for key, value in counts.items() if value > 0})

    plt.figure(figsize=(10, 5))
    bars = plt.bar(counts.keys(), counts.values())

    plt.title("Reported reasons for missed vectorization")
    plt.ylabel("Number of diagnostic messages")
    plt.xlabel("Reason")

    plt.xticks(rotation=25, ha="right")

    # Add values above bars
    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            str(int(height)),
            ha="center",
            va="bottom",
        )

    plt.figtext(
        0.5,
        0.01,
        "Note: Counts are GCC diagnostic messages, not distinct source-code loops.",
        ha="center",
        fontsize=9,
    )

    plt.tight_layout(rect=(0, 0.05, 1, 1))

    plt.savefig("plot_2_missed_vectorization_reasons.png", dpi=200)
    plt.close()


def plot_analysis_phases(loop_blocks):
    """
    Plot 3:
    Counts how often important GCC vectorization analysis phases appear.

    This supports the finding that GCC performs more analysis than only
    dependence checking and semantic correctness.
    """
    phase_patterns = {
        "loop form": "vect_analyze_loop_form",
        "iteration count": "get_loop_niters",
        "data references": "vect_analyze_data_refs",
        "scalar cycles": "vect_analyze_scalar_cycles",
        "dependences": "vect_analyze_data_ref_dependences",
        "access pattern": "vect_analyze_data_ref_accesses",
        "vectorization factor": "vect_determine_vectorization_factor",
        "alignment": "vect_analyze_data_refs_alignment",
        "cost model": "Cost model analysis",
        "transform": "vec_transform_loop",
    }

    counts = Counter()

    for _, block in loop_blocks:
        for phase_name, search_string in phase_patterns.items():
            if search_string in block:
                counts[phase_name] += 1

    # Keep only phases that appear
    counts = Counter({key: value for key, value in counts.items() if value > 0})

    plt.figure(figsize=(11, 5))
    bars = plt.bar(counts.keys(), counts.values())

    plt.title("GCC vectorization analysis phases found in the output")
    plt.ylabel("Number of loop analyses containing this phase")
    plt.xlabel("Analysis phase")

    plt.xticks(rotation=30, ha="right")

    # Add values above bars
    for bar in bars:
        height = bar.get_height()
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            height,
            str(int(height)),
            ha="center",
            va="bottom",
        )

    plt.figtext(
        0.5,
        0.01,
        "This shows that GCC performs loop-form, data-reference, dependence, alignment, and cost-model analyses.",
        ha="center",
        fontsize=9,
    )

    plt.tight_layout(rect=(0, 0.06, 1, 1))

    plt.savefig("plot_3_gcc_analysis_phases.png", dpi=200)
    plt.close()


def print_summary(loop_blocks):
    rows = build_loop_summary(loop_blocks)

    print("Loop summary:")
    print()

    for row in rows:
        print(f"{row['location']}: {row['status']} — {row['reason']}")


def main():
    text = read_output(INPUT_FILE)
    loop_blocks = extract_loop_blocks(text)

    if not loop_blocks:
        print("No loop analysis blocks found.")
        print("Check whether the input file contains lines like:")
        print("Analyzing loop at analysis.c:<line>")
        return

    print_summary(loop_blocks)

    plot_loop_decision_table(loop_blocks)
    plot_missed_reasons(text)
    plot_analysis_phases(loop_blocks)

    print()
    print("Created plots:")
    print("plot_1_vectorization_decision_table.png")
    print("plot_2_missed_vectorization_reasons.png")
    print("plot_3_gcc_analysis_phases.png")


if __name__ == "__main__":
    main()