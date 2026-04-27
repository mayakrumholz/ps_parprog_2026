#!/bin/bash

#SBATCH --partition=lva
#SBATCH --job-name=omp_mandelbrot_ex2
#SBATCH --output=ex2_job.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --exclusive

set -eu

cd "${SLURM_SUBMIT_DIR:-$(pwd)}"

THREADS="1 4 8 12"
SCHEDULES="static dynamic guided auto runtime_static runtime_dynamic runtime_guided"
RUNS=5
RESULTS_DIR="results"
IMAGES_DIR="${RESULTS_DIR}/images"
CSV_FILE="${RESULTS_DIR}/time_results.csv"

make clean
make

mkdir -p "$RESULTS_DIR" "$IMAGES_DIR"

printf "variant,threads,run,chunk,elapsed_seconds,image\n" > "$CSV_FILE"

for schedule in $SCHEDULES; do
    for thread_count in $THREADS; do
        export OMP_NUM_THREADS="$thread_count"

        for run in $(seq 1 "$RUNS"); do
            image_file="${IMAGES_DIR}/${schedule}_t${thread_count}_run${run}.png"

            case "$schedule" in
                runtime_static)
                    output=$(./mandelbrot_openmp "$thread_count" runtime "$image_file" static 1)
                    ;;
                runtime_dynamic)
                    output=$(./mandelbrot_openmp "$thread_count" runtime "$image_file" dynamic 1)
                    ;;
                runtime_guided)
                    output=$(./mandelbrot_openmp "$thread_count" runtime "$image_file" guided 1)
                    ;;
                dynamic|guided)
                    output=$(./mandelbrot_openmp "$thread_count" "$schedule" "$image_file" 1)
                    ;;
                *)
                    output=$(./mandelbrot_openmp "$thread_count" "$schedule" "$image_file")
                    ;;
            esac

            variant_value=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^variant=/) {sub(/^variant=/, "", $i); print $i}}')
            chunk_value=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^chunk=/) {sub(/^chunk=/, "", $i); print $i}}')
            elapsed_value=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^elapsed_seconds=/) {sub(/^elapsed_seconds=/, "", $i); print $i}}')
            image_value=$(printf "%s\n" "$output" | awk '{for (i = 1; i <= NF; ++i) if ($i ~ /^image=/) {sub(/^image=/, "", $i); print $i}}')

            printf "%s,%s,%s,%s,%s,%s\n" \
                "$variant_value" \
                "$thread_count" \
                "$run" \
                "$chunk_value" \
                "$elapsed_value" \
                "$image_value" >> "$CSV_FILE"
        done
    done
done

echo "Fertig. Ergebnisse stehen in $CSV_FILE"
