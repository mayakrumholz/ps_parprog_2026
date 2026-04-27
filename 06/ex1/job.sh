#!/bin/bash

#SBATCH --partition=lva
#SBATCH --job-name=omp_pi_ex1
#SBATCH --output=ex1_job.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=01:00:00
#SBATCH --mail-user=maya.krumholz@gmail.com
#SBATCH --mail-type=END,FAIL
#SBATCH --exclusive

set -eu

cd "${SLURM_SUBMIT_DIR:-$(pwd)}"

THREADS="1 4 8 12"
VARIANTS="${VARIANTS:-serial critical atomic reduction}"
RUNS="${RUNS:-5}"
CRITICAL_RUNS="${CRITICAL_RUNS:-1}"
SAMPLES="${SAMPLES:-700000000}"
RESULTS_DIR="results"
CSV_FILE="${RESULTS_DIR}/time_results.csv"
STATUS_FILE="${RESULTS_DIR}/job_status.txt"
MAIL_INTERVAL_SECONDS=600

mkdir -p "$RESULTS_DIR"

make clean
make

printf "variant,threads,run,samples,pi,elapsed_seconds\n" > "$CSV_FILE"
printf "job gestartet: %s\n" "$(date)" > "$STATUS_FILE"

send_status_mail() {
    if command -v mail >/dev/null 2>&1; then
        mail -s "$1" maya.krumholz@gmail.com < "$STATUS_FILE" || true
    fi
}

progress_mail_loop() {
    while true; do
        sleep "$MAIL_INTERVAL_SECONDS"
        send_status_mail "LCC3 Status: omp_pi_ex1 laeuft noch"
    done
}

progress_mail_loop &
MAIL_LOOP_PID=$!

cleanup() {
    if [ -n "${MAIL_LOOP_PID:-}" ]; then
        kill "$MAIL_LOOP_PID" 2>/dev/null || true
    fi
}

trap cleanup EXIT

for variant in $VARIANTS; do
    variant_runs="$RUNS"
    if [ "$variant" = "critical" ]; then
        variant_runs="$CRITICAL_RUNS"
    fi

    for thread_count in $THREADS; do
        if [ "$variant" = "serial" ] && [ "$thread_count" -ne 1 ]; then
            continue
        fi

        export OMP_NUM_THREADS="$thread_count"

        for run in $(seq 1 "$variant_runs"); do
            echo "starte: variant=$variant threads=$thread_count run=$run/$variant_runs"
            printf "laufend: variant=%s threads=%s run=%s/%s start=%s\n" \
                "$variant" \
                "$thread_count" \
                "$run" \
                "$variant_runs" \
                "$(date)" > "$STATUS_FILE"
            output=$(./"$variant" "$SAMPLES")
            printf "%s\n" "$output"

            pi_value=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^pi=/) {sub(/^pi=/, "", $i); print $i}}')
            elapsed_value=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^elapsed_seconds=/) {sub(/^elapsed_seconds=/, "", $i); print $i}}')

            printf "%s,%s,%s,%s,%s,%s\n" \
                "$variant" \
                "$thread_count" \
                "$run" \
                "$SAMPLES" \
                "$pi_value" \
                "$elapsed_value" >> "$CSV_FILE"

            echo "fertig: variant=$variant threads=$thread_count run=$run/$variant_runs elapsed=${elapsed_value}s"
            printf "fertig: variant=%s threads=%s run=%s/%s elapsed=%ss zeit=%s\n" \
                "$variant" \
                "$thread_count" \
                "$run" \
                "$variant_runs" \
                "$elapsed_value" \
                "$(date)" > "$STATUS_FILE"
        done
    done
done

echo "Fertig. Ergebnisse stehen in $CSV_FILE"
printf "job fertig: %s\ncsv: %s\n" "$(date)" "$CSV_FILE" > "$STATUS_FILE"
send_status_mail "LCC3 Status: omp_pi_ex1 fertig"
