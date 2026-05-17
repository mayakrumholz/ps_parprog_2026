#!/bin/bash

#SBATCH --partition=lva
#SBATCH --job-name=assignment09_ex1
#SBATCH --output=job_ex1.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --exclusive

set -eu

cd "${SLURM_SUBMIT_DIR:-$(pwd)}"

if command -v module >/dev/null 2>&1; then
    module load gcc/12.2.0-gcc-8.5.0-p4pe45v
fi

THREADS=12
RUNS=5
N=40000
RESULTS_DIR="results"
CSV_FILE="${RESULTS_DIR}/time_results.csv"

mkdir -p "$RESULTS_DIR"

make clean
make

export OMP_NUM_THREADS="$THREADS"
export OMP_PLACES=cores
export OMP_PROC_BIND=true

printf "case,init_mode,schedule,threads,run,n,allocation_seconds,initialization_seconds,computation_seconds,deallocation_seconds,sum,expected_sum\n" > "$CSV_FILE"

for init_mode in parallel serial; do
    for schedule in static dynamic guided; do
        for run in $(seq 1 "$RUNS"); do
            output=$(./first_touch "$N" "$init_mode" "$schedule")

            allocation=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^allocation_seconds=/) {sub(/^allocation_seconds=/, "", $i); print $i}}')
            initialization=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^initialization_seconds=/) {sub(/^initialization_seconds=/, "", $i); print $i}}')
            computation=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^computation_seconds=/) {sub(/^computation_seconds=/, "", $i); print $i}}')
            deallocation=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^deallocation_seconds=/) {sub(/^deallocation_seconds=/, "", $i); print $i}}')
            sum=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^sum=/) {sub(/^sum=/, "", $i); print $i}}')
            expected_sum=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^expected_sum=/) {sub(/^expected_sum=/, "", $i); print $i}}')

            if [ "$sum" != "$expected_sum" ]; then
                echo "Checksum mismatch for init_mode=$init_mode schedule=$schedule run=$run" >&2
                exit 1
            fi

            case_name="schedule_check"
            if [ "$schedule" = "static" ]; then
                if [ "$init_mode" = "parallel" ]; then
                    case_name="first_touch_good"
                else
                    case_name="first_touch_bad"
                fi
            fi

            printf "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" \
                "$case_name" \
                "$init_mode" \
                "$schedule" \
                "$THREADS" \
                "$run" \
                "$N" \
                "$allocation" \
                "$initialization" \
                "$computation" \
                "$deallocation" \
                "$sum" \
                "$expected_sum" >> "$CSV_FILE"
        done
    done
done

./analyze_results.py "$CSV_FILE"
echo "Finished. Results written to $RESULTS_DIR"
