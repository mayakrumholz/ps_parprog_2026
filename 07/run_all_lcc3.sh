#!/bin/bash

set -eu

cd "$(dirname "$0")"

echo "Submitting ex1/job.sh"
sbatch ex1/job.sh

echo "Submitting ex2/job.sh"
sbatch ex2/job.sh

echo "Submitting ex3/job.sh"
sbatch ex3/job.sh
