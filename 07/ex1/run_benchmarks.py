#!/usr/bin/env python3

import csv
import os
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
CSV_PATH = RESULTS_DIR / "time_results.csv"

CASES = [
    ("snippet1", 8_000_000),
    ("snippet2", 8_000_000),
    ("snippet3", 8_000_000),
]
THREADS = [1, 2, 4, 8]
RUNS = 5
LINE_RE = re.compile(
    r"snippet=(?P<snippet>\S+) "
    r"variant=(?P<variant>\S+) "
    r"threads=(?P<threads>\d+) "
    r"n=(?P<n>\d+) "
    r"seconds=(?P<seconds>\S+) "
    r"checksum=(?P<checksum>\S+) "
    r"aux=(?P<aux>\S+)"
)


def run_case(snippet: str, variant: str, threads: int, n: int) -> dict[str, str]:
    command = [str(ROOT / "benchmark"), snippet, variant, str(threads), str(n)]
    completed = subprocess.run(command, check=True, text=True, capture_output=True)
    match = LINE_RE.fullmatch(completed.stdout.strip())
    if match is None:
        raise RuntimeError(f"Unexpected benchmark output: {completed.stdout!r}")
    return match.groupdict()


def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    with CSV_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["snippet", "variant", "threads", "run", "n", "seconds", "checksum", "aux"])

        for snippet, n in CASES:
            original_result = run_case(snippet, "original", 1, n)
            writer.writerow(
                [
                    snippet,
                    "original",
                    1,
                    1,
                    n,
                    original_result["seconds"],
                    original_result["checksum"],
                    original_result["aux"],
                ]
            )

            for threads in THREADS:
                for run in range(1, RUNS + 1):
                    result = run_case(snippet, "parallel", threads, n)
                    writer.writerow(
                        [
                            snippet,
                            "parallel",
                            threads,
                            run,
                            n,
                            result["seconds"],
                            result["checksum"],
                            result["aux"],
                        ]
                    )

    print(f"Wrote {CSV_PATH}")


if __name__ == "__main__":
    main()
