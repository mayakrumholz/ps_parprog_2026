#!/bin/bash

#SBATCH --partition=lva
#SBATCH --job-name=assignment09_ex2_n14
#SBATCH --output=job_ex2_n14.log
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
THREADS=12
N=14
CUTOFF=8

mkdir -p "$RESULTS_DIR"

if [ ! -f "$CSV_FILE" ]; then
    printf "mode,threads,run,n,cutoff,result,expected,elapsed_seconds\n" > "$CSV_FILE"
fi

make clean
make

export OMP_NUM_THREADS="$THREADS"
export OMP_PLACES=cores
export OMP_PROC_BIND=true

for run in $(seq 1 "$RUNS"); do
    output=$(./delannoy task "$N" "$CUTOFF")
    result=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^result=/) {sub(/^result=/, "", $i); print $i}}')
    expected=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^expected=/) {sub(/^expected=/, "", $i); print $i}}')
    elapsed=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^elapsed_seconds=/) {sub(/^elapsed_seconds=/, "", $i); print $i}}')

    if [ "$result" != "$expected" ]; then
        echo "Task checksum mismatch for threads=$THREADS N=$N run=$run" >&2
        exit 1
    fi

    printf "%s,%s,%s,%s,%s,%s,%s,%s\n" \
        "task" "$THREADS" "$run" "$N" "$CUTOFF" "$result" "$expected" "$elapsed" >> "$CSV_FILE"
done

./analyze_results.py "$CSV_FILE"
echo "Finished remaining runs for N=$N"
