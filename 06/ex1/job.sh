#!/bin/bash

#SBATCH --partition=lva
#SBATCH --job-name=omp_pi_ex1
#SBATCH --output=ex1_job.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --exclusive

set -eu

cd "${SLURM_SUBMIT_DIR:-$(pwd)}"

THREADS="1 4 8 12"
VARIANTS="serial critical atomic reduction"
RUNS=5
SAMPLES=700000000
RESULTS_DIR="results"
CSV_FILE="${RESULTS_DIR}/time_results.csv"

mkdir -p "$RESULTS_DIR"

make clean
make

printf "variant,threads,run,samples,pi,elapsed_seconds\n" > "$CSV_FILE"

for variant in $VARIANTS; do
    for thread_count in $THREADS; do
        if [ "$variant" = "serial" ] && [ "$thread_count" -ne 1 ]; then
            continue
        fi

        export OMP_NUM_THREADS="$thread_count"

        for run in $(seq 1 "$RUNS"); do
            output=$(./"$variant" "$SAMPLES")

            pi_value=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^pi=/) {sub(/^pi=/, "", $i); print $i}}')
            elapsed_value=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^elapsed_seconds=/) {sub(/^elapsed_seconds=/, "", $i); print $i}}')

            printf "%s,%s,%s,%s,%s,%s\n" \
                "$variant" \
                "$thread_count" \
                "$run" \
                "$SAMPLES" \
                "$pi_value" \
                "$elapsed_value" >> "$CSV_FILE"
        done
    done
done

echo "Fertig. Ergebnisse stehen in $CSV_FILE"
