#!/bin/bash
#SBATCH --job-name=vec-analysis
#SBATCH --output=vec-analysis.out
#SBATCH --error=vec-analysis.err
#SBATCH --time=00:02:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1

module load gcc/12.2.0-gcc-8.5.0-p4pe45v

echo "Running on $(hostname)"
echo "Starting at $(date)"

echo "===== BUILD ====="
make clean || true
make 2>&1

echo "===== REPORT ====="
cat vec_report.txt