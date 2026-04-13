#!/bin/bash

# Execute job in the partition "lva" unless you have special requirements.
#SBATCH --partition=lva
# Name your job to be able to identify it later
#SBATCH --job-name mandelbrot_pthreads
# Redirect output stream to this file
#SBATCH --output=mandelbrot_pthreads.log
# Maximum number of tasks (=processes) to start in total
#SBATCH --ntasks=1
# Maximum number of tasks (=processes) to start per node
#SBATCH --ntasks-per-node=1
# Enforce exclusive node allocation, do not share with other jobs
#SBATCH --exclusive

set -eu

cd "${SLURM_SUBMIT_DIR:-$(pwd)}"

THREADS="1 2 4 8 12"
RUNS=10
RESULTS_DIR="results"
IMAGES_DIR="${RESULTS_DIR}/images"
CSV_FILE="${RESULTS_DIR}/time_results.csv"
SUMMARY_FILE="${RESULTS_DIR}/run_summary.txt"
TIME_FILE="${RESULTS_DIR}/time_output.txt"

mkdir -p "$IMAGES_DIR"
: > "$SUMMARY_FILE"
printf "threads,run,real,user,sys,image\n" > "$CSV_FILE"

/bin/hostname | tee -a "$SUMMARY_FILE"
pwd | tee -a "$SUMMARY_FILE"
echo "Threads: $THREADS" | tee -a "$SUMMARY_FILE"
echo "Runs per thread count: $RUNS" | tee -a "$SUMMARY_FILE"

make clean
make

for thread_count in $THREADS; do
    for run in $(seq 1 "$RUNS"); do
        image_file="${IMAGES_DIR}/mandelbrot_t${thread_count}_run${run}.png"

        echo "===== threads=${thread_count} run=${run}/${RUNS} =====" | tee -a "$SUMMARY_FILE"
        /usr/bin/time -p -o "$TIME_FILE" ./mandelbrot_pthreads "$thread_count" "$image_file"

        real_time=$(awk '$1 == "real" { print $2 }' "$TIME_FILE")
        user_time=$(awk '$1 == "user" { print $2 }' "$TIME_FILE")
        sys_time=$(awk '$1 == "sys" { print $2 }' "$TIME_FILE")

        printf "%s,%s,%s,%s,%s,%s\n" \
            "$thread_count" \
            "$run" \
            "$real_time" \
            "$user_time" \
            "$sys_time" \
            "$image_file" >> "$CSV_FILE"
    done
done

echo "Wrote raw timing data to $CSV_FILE" | tee -a "$SUMMARY_FILE"
echo "Wrote images to $IMAGES_DIR" | tee -a "$SUMMARY_FILE"
