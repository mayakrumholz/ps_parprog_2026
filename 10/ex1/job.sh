#!/bin/bash

#SBATCH --partition=lva
#SBATCH --job-name=assignment10_ex1
#SBATCH --output=job_ex1.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --exclusive

set -eu

cd "${SLURM_SUBMIT_DIR:-$(pwd)}"

if command -v module >/dev/null 2>&1; then
    module load gcc/12.2.0-gcc-8.5.0-p4pe45v
fi

SIZES="256 512 1024 2048 4096 8192"
PERF_SIZES="2048 8192"
REPETITIONS=1000000
RUNS=5
RESULTS_DIR="results"
PERF_DIR="${RESULTS_DIR}/perf"
TIME_CSV="${RESULTS_DIR}/time_results.csv"
PERF_CSV="${RESULTS_DIR}/perf_results.csv"
EVENTS="cycles,instructions,r0410,r1010,r2010,r4010"

mkdir -p "$RESULTS_DIR" "$PERF_DIR"

make clean
make all
make reports
make check

printf "variant,size,repetitions,run,elapsed_seconds,checksum,expected_checksum,sample0,samplemid,samplelast,expected_value,status\n" > "$TIME_CSV"
printf "variant,size,repetitions,metric,value,unit\n" > "$PERF_CSV"

extract_field() {
    local key="$1"
    awk -v search_key="$key" '{
        for (i = 1; i <= NF; ++i) {
            split($i, pair, "=");
            if (pair[1] == search_key) {
                print pair[2];
                exit;
            }
        }
    }'
}

for variant in baseline auto_vectorized; do
    for size in $SIZES; do
        for run in $(seq 1 "$RUNS"); do
            output=$(./"$variant" "$size" "$REPETITIONS")

            elapsed_seconds=$(printf "%s\n" "$output" | extract_field elapsed_seconds)
            checksum=$(printf "%s\n" "$output" | extract_field checksum)
            expected_checksum=$(printf "%s\n" "$output" | extract_field expected_checksum)
            sample0=$(printf "%s\n" "$output" | extract_field sample0)
            samplemid=$(printf "%s\n" "$output" | extract_field samplemid)
            samplelast=$(printf "%s\n" "$output" | extract_field samplelast)
            expected_value=$(printf "%s\n" "$output" | extract_field expected_value)
            status=$(printf "%s\n" "$output" | extract_field status)

            if [ "$status" != "ok" ]; then
                echo "Correctness check failed for variant=$variant size=$size run=$run" >&2
                exit 1
            fi

            printf "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n" \
                "$variant" \
                "$size" \
                "$REPETITIONS" \
                "$run" \
                "$elapsed_seconds" \
                "$checksum" \
                "$expected_checksum" \
                "$sample0" \
                "$samplemid" \
                "$samplelast" \
                "$expected_value" \
                "$status" >> "$TIME_CSV"
        done
    done
done

for variant in baseline auto_vectorized; do
    for size in $PERF_SIZES; do
        perf_raw="${PERF_DIR}/${variant}_n${size}.csv"
        program_out="${PERF_DIR}/${variant}_n${size}.program.txt"

        perf stat -x, -e "$EVENTS" \
            ./"$variant" "$size" "$REPETITIONS" \
            > "$program_out" 2> "$perf_raw"

        if ! grep -q "status=ok" "$program_out"; then
            echo "Correctness check failed during perf run for variant=$variant size=$size" >&2
            exit 1
        fi

        awk -F, -v variant="$variant" -v size="$size" -v repetitions="$REPETITIONS" '
            NF >= 3 && $1 !~ /^#/ {
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", $1);
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2);
                gsub(/^[[:space:]]+|[[:space:]]+$/, "", $3);

                if ($1 == "<not supported>" || $1 == "") {
                    next;
                }

                printf "%s,%s,%s,%s,%s,%s\n", variant, size, repetitions, $3, $1, $2;
            }
        ' "$perf_raw" >> "$PERF_CSV"
    done
done

python3 ./analyze_results.py "$TIME_CSV" "$PERF_CSV"
echo "Finished. Results written to $RESULTS_DIR"
