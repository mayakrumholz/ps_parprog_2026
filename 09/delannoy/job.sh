#!/bin/bash

#SBATCH --partition=lva
#SBATCH --job-name=assignment09_ex2
#SBATCH --output=job_ex2.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --exclusive

set -eu

cd "${SLURM_SUBMIT_DIR:-$(pwd)}"

if command -v module >/dev/null 2>&1; then
    module load gcc/12.2.0-gcc-8.5.0-p4pe45v
fi

RESULTS_DIR="results"
CSV_FILE="${RESULTS_DIR}/time_results.csv"
RUNS=5
THREADS="1 12"
NS="3 4 5 6 7 8 9 10 11 12 13 14 15"
CUTOFF=8

mkdir -p "$RESULTS_DIR"

make clean
make

printf "mode,threads,run,n,cutoff,result,expected,elapsed_seconds\n" > "$CSV_FILE"

for n in $NS; do
    for run in $(seq 1 "$RUNS"); do
        output=$(./delannoy seq "$n" "$CUTOFF")
        result=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^result=/) {sub(/^result=/, "", $i); print $i}}')
        expected=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^expected=/) {sub(/^expected=/, "", $i); print $i}}')
        elapsed=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^elapsed_seconds=/) {sub(/^elapsed_seconds=/, "", $i); print $i}}')

        if [ "$result" != "$expected" ]; then
            echo "Sequential checksum mismatch for N=$n run=$run" >&2
            exit 1
        fi

        printf "%s,%s,%s,%s,%s,%s,%s,%s\n" \
            "seq" "1" "$run" "$n" "$CUTOFF" "$result" "$expected" "$elapsed" >> "$CSV_FILE"
    done
done

for threads in $THREADS; do
    export OMP_NUM_THREADS="$threads"
    export OMP_PLACES=cores
    export OMP_PROC_BIND=true

    for n in $NS; do
        for run in $(seq 1 "$RUNS"); do
            output=$(./delannoy task "$n" "$CUTOFF")
            result=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^result=/) {sub(/^result=/, "", $i); print $i}}')
            expected=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^expected=/) {sub(/^expected=/, "", $i); print $i}}')
            elapsed=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^elapsed_seconds=/) {sub(/^elapsed_seconds=/, "", $i); print $i}}')

            if [ "$result" != "$expected" ]; then
                echo "Task checksum mismatch for threads=$threads N=$n run=$run" >&2
                exit 1
            fi

            printf "%s,%s,%s,%s,%s,%s,%s,%s\n" \
                "task" "$threads" "$run" "$n" "$CUTOFF" "$result" "$expected" "$elapsed" >> "$CSV_FILE"
        done
    done
done

./analyze_results.py "$CSV_FILE"
echo "Finished. Results written to $RESULTS_DIR"
