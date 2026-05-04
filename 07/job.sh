#!/bin/bash

#SBATCH --partition=lva
#SBATCH --job-name=assignment07_ex2
#SBATCH --output=job07.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --exclusive

set -eu

cd "${SLURM_SUBMIT_DIR:-$(pwd)}"

THREADS="1 4 8 12"
CASES="a b c_false c_true"
RUNS=5
RESULTS_DIR="results"
CSV_FILE="${RESULTS_DIR}/time_results.csv"

make clean
make
make check

mkdir -p "$RESULTS_DIR"
printf "case,variant,n,repetitions,threads,run,elapsed_seconds,checksum\n" > "$CSV_FILE"

for bench_case in $CASES; do
    case "$bench_case" in
        a)
            n=12000000
            repetitions=32
            ;;
        b)
            n=12000000
            repetitions=20
            ;;
        c_false)
            n=16000000
            repetitions=16
            ;;
        c_true)
            n=16000000
            repetitions=12
            ;;
        *)
            echo "unknown case $bench_case" >&2
            exit 1
            ;;
    esac

    for variant in original parallel; do
        for threads in $THREADS; do
            for run in $(seq 1 "$RUNS"); do
                output=$(./ex2_benchmark "$bench_case" "$variant" "$n" "$repetitions" "$threads")
                elapsed=$(printf "%s\n" "$output" | awk '{for (i=1; i<=NF; ++i) if ($i ~ /^elapsed_seconds=/) {sub(/^elapsed_seconds=/, "", $i); print $i}}')
                checksum=$(printf "%s\n" "$output" | awk '{for (i=1; i<=NF; ++i) if ($i ~ /^checksum=/) {sub(/^checksum=/, "", $i); print $i}}')

                printf "%s,%s,%s,%s,%s,%s,%s,%s\n" \
                    "$bench_case" \
                    "$variant" \
                    "$n" \
                    "$repetitions" \
                    "$threads" \
                    "$run" \
                    "$elapsed" \
                    "$checksum" >> "$CSV_FILE"
            done
        done
    done
done

./analyze_results.py "$CSV_FILE"
echo "Finished. Results written to $RESULTS_DIR"
