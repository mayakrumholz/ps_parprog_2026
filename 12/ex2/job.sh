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

touch timer.flag

echo "Sequential reference" | tee results/benchmark_summary.txt
OMP_NUM_THREADS=1 ./real_seq | tee results/seq_output.txt

for threads in 1 2 6 12; do
  echo | tee -a results/benchmark_summary.txt
  echo "OpenMP with ${threads} thread(s)" | tee -a results/benchmark_summary.txt
  OMP_NUM_THREADS=${threads} OMP_PROC_BIND=close OMP_PLACES=cores ./real_omp \
    | tee "results/omp_${threads}_threads_output.txt"
done

{
  echo
  echo "Collected benchmark lines"
  echo "========================="
  grep -H "Verification\\|Time in seconds\\|Mop/s total\\|benchmk\\|mg3P\\|psinv\\|resid\\|rprj3\\|interp\\|norm2\\|comm3" \
    results/seq_output.txt results/omp_*_threads_output.txt || true
} >> results/benchmark_summary.txt
