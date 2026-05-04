#!/bin/bash

#SBATCH --partition=lva
#SBATCH --job-name=pp_07_ex3
#SBATCH --output=ex3_job.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --exclusive

set -eu

cd "${SLURM_SUBMIT_DIR:-$(pwd)}"

echo "===== JOB INFO ====="
/bin/hostname
pwd
echo "SLURM_CPUS_PER_TASK=${SLURM_CPUS_PER_TASK:-unset}"
echo ""

make clean
make CC=gcc

python3 run_benchmarks.py
python3 analyze_results.py

echo ""
echo "Fertig. Dateien:"
echo "  results/time_results.csv"
echo "  results/summary_stats.csv"
echo "  results/summary_report.txt"
echo "  results/plots/runtime_bar.svg"
