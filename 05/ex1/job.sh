#!/bin/bash

# Execute job in the partition "lva" unless you have special requirements.
#SBATCH --partition=lva
# Name your job to be able to identify it later
#SBATCH --job-name ex1_flush
# Redirect output stream to this file
#SBATCH --output=ex1_job.log
# Maximum number of tasks (=processes) to start in total
#SBATCH --ntasks=1
# Maximum number of tasks (=processes) to start per node
#SBATCH --ntasks-per-node=1
# Enforce exclusive node allocation, do not share with other jobs
#SBATCH --exclusive

set -eu

cd "${SLURM_SUBMIT_DIR:-$(pwd)}"

RESULTS_DIR="results"
REPORT_FILE="${RESULTS_DIR}/ex1_report.txt"
OUTPUT_FILE="${RESULTS_DIR}/ex1_outputs.txt"
BUILD_LOG="${RESULTS_DIR}/build.log"
RUN_LOG="${RESULTS_DIR}/last_run.log"
RUNS_PER_BATCH=1000
BATCHES=5
TIME_LIMIT="2s"

mkdir -p "$RESULTS_DIR"
: > "$REPORT_FILE"
: > "$OUTPUT_FILE"
: > "$BUILD_LOG"

echo "===== JOB INFO =====" | tee -a "$REPORT_FILE"
/bin/hostname | tee -a "$REPORT_FILE"
pwd | tee -a "$REPORT_FILE"
echo "Batches: $BATCHES" | tee -a "$REPORT_FILE"
echo "Runs per batch: $RUNS_PER_BATCH" | tee -a "$REPORT_FILE"
echo "Timeout per run: $TIME_LIMIT" | tee -a "$REPORT_FILE"
echo "" | tee -a "$REPORT_FILE"

echo "===== BUILD =====" | tee -a "$REPORT_FILE"
make clean >> "$BUILD_LOG" 2>&1 || true
make CFLAGS="-std=gnu11 -Wall -Wextra -lm -fopenmp -O3" >> "$BUILD_LOG" 2>&1
tee -a "$REPORT_FILE" < "$BUILD_LOG"
echo "" | tee -a "$REPORT_FILE"

for batch in $(seq 1 "$BATCHES"); do
    success_count=0
    timeout_count=0
    error_count=0

    echo "===== BATCH $batch/$BATCHES =====" | tee -a "$REPORT_FILE"

    for run in $(seq 1 "$RUNS_PER_BATCH"); do
        if timeout "$TIME_LIMIT" ./ex1 > "$RUN_LOG" 2>&1; then
            success_count=$((success_count + 1))
            printf "batch=%s run=%s status=ok output=%s\n" \
                "$batch" "$run" "$(tr '\n' ' ' < "$RUN_LOG")" >> "$OUTPUT_FILE"
        else
            run_status=$?

            if [ "$run_status" -eq 124 ]; then
                timeout_count=$((timeout_count + 1))
                printf "batch=%s run=%s status=timeout\n" \
                    "$batch" "$run" >> "$OUTPUT_FILE"
            else
                error_count=$((error_count + 1))
                printf "batch=%s run=%s status=error exit_code=%s output=%s\n" \
                    "$batch" "$run" "$run_status" "$(tr '\n' ' ' < "$RUN_LOG")" >> "$OUTPUT_FILE"
            fi
        fi
    done

    echo "successful runs: $success_count" | tee -a "$REPORT_FILE"
    echo "timed out runs:  $timeout_count" | tee -a "$REPORT_FILE"
    echo "error runs:      $error_count" | tee -a "$REPORT_FILE"
    echo "" | tee -a "$REPORT_FILE"
done

echo "===== DONE =====" | tee -a "$REPORT_FILE"
echo "Detailed per-run results: $OUTPUT_FILE" | tee -a "$REPORT_FILE"
echo "Summary report: $REPORT_FILE" | tee -a "$REPORT_FILE"
