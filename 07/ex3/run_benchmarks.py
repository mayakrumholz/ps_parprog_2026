#!/usr/bin/env python3

import csv
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
CSV_PATH = RESULTS_DIR / "time_results.csv"
ROWS = 2048
COLS = 8192
RUNS = 7
LINE_RE = re.compile(
    r"variant=(?P<variant>\S+) "
    r"threads=(?P<threads>\d+) "
    r"rows=(?P<rows>\d+) "
    r"cols=(?P<cols>\d+) "
    r"seconds=(?P<seconds>\S+) "
    r"checksum=(?P<checksum>\S+) "
    r"aux=(?P<aux>\S+)"
)


def run_case(variant: str, threads: int) -> dict[str, str]:
    command = [str(ROOT / "benchmark"), variant, str(threads), str(ROWS), str(COLS)]
    completed = subprocess.run(command, check=True, text=True, capture_output=True)
    match = LINE_RE.fullmatch(completed.stdout.strip())
    if match is None:
        raise RuntimeError(f"Unexpected benchmark output: {completed.stdout!r}")
    return match.groupdict()


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["variant", "threads", "run", "rows", "cols", "seconds", "checksum", "aux"])

        for run in range(1, RUNS + 1):
            original = run_case("original", 1)
            writer.writerow(["original", 1, run, ROWS, COLS, original["seconds"], original["checksum"], original["aux"]])

        for run in range(1, RUNS + 1):
            parallel = run_case("parallel", 2)
            writer.writerow(["parallel", 2, run, ROWS, COLS, parallel["seconds"], parallel["checksum"], parallel["aux"]])

    print(f"Wrote {CSV_PATH}")


if __name__ == "__main__":
    main()
