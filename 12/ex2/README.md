# Assignment 12 - Exercise 2

This directory contains the prepared OpenMP solution and LCC3 benchmark setup.

## Build

```bash
make clean
make CC=gcc all
```

The build creates two executables:

- `real_serial`: original sequential program, compiled without OpenMP
- `real_openmp`: OpenMP version, compiled with `-fopenmp`

## LCC3 Benchmark

Submit the benchmark job from this directory:

```bash
sbatch job.sh
```

The job runs:

- the original sequential program
- the OpenMP version with `OMP_NUM_THREADS=1,2,6,12`

Each run writes a raw output file and one CSV row. The CSV contains both the
program's benchmark timer and an external wall-time measurement:

```text
results/time_results.csv
```

After the run, `analyze_results.py` creates:

- `results/summary.csv`
- `results/summary.md`
- `results/wall_time.png`
- `results/speedup.png`
- `results/efficiency.png`

Use the generated `summary.md` and plots for the final written discussion.
