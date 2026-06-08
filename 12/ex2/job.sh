#!/bin/bash
#SBATCH --job-name=assignment12_ex2
#SBATCH --output=job_%j.out
#SBATCH --error=job_%j.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=00:20:00

set -euo pipefail

mkdir -p results

module purge
module load gcc || true

make clean || true
make CC=gcc

# The comparison spreadsheet asks for wall time. Disable the optional
# internal section timers so the measured run matches the normal program run.
rm -f timer.flag

run_measured() {
  local label="$1"
  local output_file="$2"
  shift 2

  echo "${label}" | tee -a results/benchmark_summary.txt
  /usr/bin/time -f "WALL_TIME_SECONDS %e" -o "${output_file}.time" "$@" \
    | tee "${output_file}"
  cat "${output_file}.time" | tee -a results/benchmark_summary.txt
}

echo "Sequential reference" | tee results/benchmark_summary.txt
run_measured "Sequential reference run" "results/seq_output.txt" \
  env OMP_NUM_THREADS=1 ./real_seq

for threads in 1 2 6 12; do
  echo | tee -a results/benchmark_summary.txt
  run_measured "OpenMP with ${threads} thread(s)" "results/omp_${threads}_threads_output.txt" \
    env OMP_NUM_THREADS=${threads} OMP_PROC_BIND=close OMP_PLACES=cores ./real_omp
done

{
  echo
  echo "Collected benchmark lines"
  echo "========================="
  grep -H "Verification\\|Time in seconds\\|Mop/s total\\|benchmk\\|mg3P\\|psinv\\|resid\\|rprj3\\|interp\\|norm2\\|comm3" \
    results/seq_output.txt results/omp_*_threads_output.txt || true
  echo
  echo "Collected wall times"
  echo "===================="
  grep -H "WALL_TIME_SECONDS" results/*.time || true
} >> results/benchmark_summary.txt
