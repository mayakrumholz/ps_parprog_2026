#!/usr/bin/env python3

import csv
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
CSV_PATH = RESULTS_DIR / "time_results.csv"
CASES = [
    ("case_a", 12_000_000),
    ("case_b", 10_000_000),
    ("case_c_twice0", 12_000_000),
    ("case_c_twice1", 12_000_000),
]
THREADS = [1, 2, 4, 8]
RUNS = 5
LINE_RE = re.compile(
    r"case=(?P<case>\S+) "
    r"variant=(?P<variant>\S+) "
    r"threads=(?P<threads>\d+) "
    r"n=(?P<n>\d+) "
    r"seconds=(?P<seconds>\S+) "
    r"checksum=(?P<checksum>\S+) "
    r"aux=(?P<aux>\S+)"
)


def run_case(case_name: str, variant: str, threads: int, n: int) -> dict[str, str]:
    command = [str(ROOT / "benchmark"), case_name, variant, str(threads), str(n)]
    completed = subprocess.run(command, check=True, text=True, capture_output=True)
    match = LINE_RE.fullmatch(completed.stdout.strip())
    if match is None:
        raise RuntimeError(f"Unexpected benchmark output: {completed.stdout!r}")
    return match.groupdict()


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["case", "variant", "threads", "run", "n", "seconds", "checksum", "aux"])

        for case_name, n in CASES:
            original = run_case(case_name, "original", 1, n)
            writer.writerow([case_name, "original", 1, 1, n, original["seconds"], original["checksum"], original["aux"]])
            for threads in THREADS:
                for run in range(1, RUNS + 1):
                    result = run_case(case_name, "parallel", threads, n)
                    writer.writerow([case_name, "parallel", threads, run, n, result["seconds"], result["checksum"], result["aux"]])

    print(f"Wrote {CSV_PATH}")


if __name__ == "__main__":
    main()
