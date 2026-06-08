#!/bin/bash

#SBATCH --partition=lva
#SBATCH --job-name=assignment12_ex2
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
OUTPUT_DIR="${RESULTS_DIR}/raw"
CSV_FILE="${RESULTS_DIR}/time_results.csv"
RUNS="${RUNS:-5}"
THREADS="1 2 6 12"

mkdir -p "$OUTPUT_DIR"
touch timer.flag

make clean
make CC=gcc all

printf "variant,threads,run,benchmark_seconds,wall_seconds,l2_norm,verification,output_file\n" > "$CSV_FILE"

extract_result_field() {
    local key="$1"
    awk -v search_key="$key" '
        /^RESULT / {
            for (i = 1; i <= NF; ++i) {
                split($i, pair, "=");
                if (pair[1] == search_key) {
                    print pair[2];
                    exit;
                }
            }
        }
    '
}

run_case() {
    local variant="$1"
    local threads="$2"
    local run="$3"
    local executable="$4"
    local output_file="${OUTPUT_DIR}/${variant}_t${threads}_run${run}.txt"
    local start_ns end_ns wall_seconds output benchmark_seconds l2_norm verification

    export OMP_NUM_THREADS="$threads"
    export OMP_PLACES=cores
    export OMP_PROC_BIND=close

    start_ns=$(date +%s%N)
    output=$("./$executable")
    end_ns=$(date +%s%N)
    wall_seconds=$(awk -v start="$start_ns" -v end="$end_ns" 'BEGIN { printf "%.9f", (end - start) / 1000000000.0 }')

    printf "%s\n" "$output" > "$output_file"

    benchmark_seconds=$(printf "%s\n" "$output" | extract_result_field benchmark_seconds)
    l2_norm=$(printf "%s\n" "$output" | extract_result_field l2_norm)
    verification=$(printf "%s\n" "$output" | extract_result_field verification)

    if [ "$verification" != "SUCCESSFUL" ]; then
        echo "Verification failed for variant=$variant threads=$threads run=$run" >&2
        exit 1
    fi

    printf "%s,%s,%s,%s,%s,%s,%s,%s\n" \
        "$variant" "$threads" "$run" "$benchmark_seconds" "$wall_seconds" \
        "$l2_norm" "$verification" "$output_file" >> "$CSV_FILE"
}

for run in $(seq 1 "$RUNS"); do
    run_case "serial" "1" "$run" "real_serial"
done

for threads in $THREADS; do
    for run in $(seq 1 "$RUNS"); do
        run_case "openmp" "$threads" "$run" "real_openmp"
    done
done

python3 ./analyze_results.py "$CSV_FILE"
echo "Finished. Results written to $RESULTS_DIR"
