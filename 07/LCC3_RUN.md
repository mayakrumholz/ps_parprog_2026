# LCC3 Ausführung für Assignment 07

## Einmalig auf dem Cluster

Ins Repository wechseln:

```bash
cd /path/to/ps_parprog_2026/07
```

Optional prüfen:

```bash
which gcc
which python3
```

## Jobs abschicken

Einzeln:

```bash
cd ex1 && sbatch job.sh && cd ..
cd ex2 && sbatch job.sh && cd ..
cd ex3 && sbatch job.sh && cd ..
```

Oder gesammelt:

```bash
bash run_all_lcc3.sh
```

## Status prüfen

```bash
squeue -u $USER
```

Wenn die Jobs fertig sind, die Logs ansehen:

```bash
cat ex1/ex1_job.log
cat ex2/ex2_job.log
cat ex3/ex3_job.log
```

## Wichtige Ergebnisdateien

Exercise 1:

```bash
cat ex1/results/summary_report.txt
head -n 20 ex1/results/summary_stats.csv
```

Exercise 2:

```bash
cat ex2/results/summary_report.txt
head -n 20 ex2/results/summary_stats.csv
```

Exercise 3:

```bash
cat ex3/results/summary_report.txt
head -n 20 ex3/results/summary_stats.csv
```

## Dateien für die Rückgabe an mich

Bitte schick mir idealerweise diese Dateien bzw. ihren Inhalt:

- `07/ex1/results/time_results.csv`
- `07/ex1/results/summary_stats.csv`
- `07/ex2/results/time_results.csv`
- `07/ex2/results/summary_stats.csv`
- `07/ex3/results/time_results.csv`
- `07/ex3/results/summary_stats.csv`

Optional zusätzlich:

- `07/ex1/ex1_job.log`
- `07/ex2/ex2_job.log`
- `07/ex3/ex3_job.log`
