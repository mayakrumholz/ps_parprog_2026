#!/bin/bash

#SBATCH --partition=lva
#SBATCH --job-name hadamard_cache
#SBATCH --output=hadamard_cache.log
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --exclusive

set -eu

cd "${SLURM_SUBMIT_DIR:-$(pwd)}"

RESULTS_DIR="results"
REPORT_FILE="${RESULTS_DIR}/report.txt"
SIZES="512 1024 2048"

mkdir -p "$RESULTS_DIR"
: > "$REPORT_FILE"

echo "===== JOB INFO =====" | tee -a "$REPORT_FILE"
/bin/hostname | tee -a "$REPORT_FILE"
pwd | tee -a "$REPORT_FILE"
echo "Sizes: $SIZES" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

echo "===== BUILD =====" | tee -a "$REPORT_FILE"
make clean || true
make 2>&1 | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

for n in $SIZES; do
    for mode in 0 1; do
        if [ "$mode" -eq 0 ]; then
            variant="v0 (j aussen, i innen)"
        else
            variant="v1 (i aussen, j innen)"
        fi

        echo "==================================================" | tee -a "$REPORT_FILE"
        echo "n=$n | mode=$mode | $variant" | tee -a "$REPORT_FILE"
        echo "==================================================" | tee -a "$REPORT_FILE"
        echo "" | tee -a "$REPORT_FILE"

        echo "--- PROGRAM OUTPUT ---" | tee -a "$REPORT_FILE"
        ./hadamard "$n" "$mode" 2>&1 | tee -a "$REPORT_FILE"
        echo "" | tee -a "$REPORT_FILE"

        echo "--- CACHEGRIND ---" | tee -a "$REPORT_FILE"
        valgrind --tool=cachegrind ./hadamard "$n" "$mode" 2>&1 | tee -a "$REPORT_FILE"
        echo "" | tee -a "$REPORT_FILE"

        echo "--- PERF ---" | tee -a "$REPORT_FILE"
        perf stat -e LLC-load-misses,LLC-store-misses ./hadamard "$n" "$mode" 2>&1 | tee -a "$REPORT_FILE"
        echo "" | tee -a "$REPORT_FILE"
    done
done

echo "===== DONE =====" | tee -a "$REPORT_FILE"
echo "Wrote combined report to $REPORT_FILE" | tee -a "$REPORT_FILE"