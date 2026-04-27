# Assignment 6

## Exercise 1

### 1) Implementierung der drei OpenMP-Varianten

Für die Monte-Carlo-Approximation von Pi wurden auf Basis der seriellen Vorlage drei parallele Versionen umgesetzt:

- `critical`: [06/ex1/critical.c](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/06/ex1/critical.c)
- `atomic`: [06/ex1/atomic.c](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/06/ex1/atomic.c)
- `reduction`: [06/ex1/reduction.c](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/06/ex1/reduction.c)

Zusätzlich liegt eine serielle Referenzversion vor:

- `serial`: [06/ex1/serial.c](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/06/ex1/serial.c)

Alle Varianten verwenden dieselbe Grundidee:

1. Es werden `n` Zufallspunkte im Quadrat `[0, 1] x [0, 1]` erzeugt.
2. Für jeden Punkt wird geprüft, ob `x^2 + y^2 <= 1` gilt.
3. Falls ja, wird der Zähler `inside_circle` erhöht.
4. Am Ende wird Pi über

    ```text
    pi = 4 * inside_circle / n
    ```

    approximiert.

Gemäß Aufgabenstellung wird der Trefferzähler in den parallelen Versionen direkt in der Schleife erhöht und nicht zuerst in einer privaten Hilfsvariable gesammelt.

#### Warum ein eigener Zufallszahlengenerator?

Die serielle Vorlage verwendet `rand()`. Für die parallelen Varianten ist das unpraktisch, weil `rand()` eine globale Zustandsvariable benutzt und dadurch zusätzliche Synchronisation oder undefiniertes Verhalten verursachen kann. Deshalb nutzt jede Variante einen einfachen thread-lokalen Pseudozufallszahlengenerator mit eigenem Seed pro Thread. Dadurch bleibt der Fokus der Messung auf den OpenMP-Konstrukten `critical`, `atomic` und `reduction`.

### 2) Unterschied zwischen `critical`, `atomic` und `reduction`

#### Variante mit `critical`

Bei `critical` darf immer nur ein Thread gleichzeitig den geschützten Abschnitt betreten:

```c
#pragma omp critical
inside_circle++;
```

Das ist korrekt, aber teuer. Jeder Treffer im Kreis führt dazu, dass sich alle Threads um genau diese eine kritische Sektion konkurrieren.

#### Variante mit `atomic`

Bei `atomic` wird nur die einzelne Update-Operation geschützt:

```c
#pragma omp atomic update
inside_circle++;
```

Das ist typischerweise günstiger als `critical`, weil nur der eigentliche Speicherzugriff atomar gemacht werden muss und keine allgemeine kritische Sektion aufgebaut wird.

#### Variante mit `reduction`

Bei `reduction` erhält jeder Thread zunächst eine private Kopie des Zählers. Erst am Ende werden diese Teilresultate zusammengeführt:

```c
#pragma omp parallel reduction(+ : inside_circle)
```

Die Inkrement-Operation innerhalb der Schleife bleibt einfach:

```c
inside_circle++;
```

Der große Vorteil ist, dass während der Schleife keine globale Synchronisation bei jedem Treffer nötig ist.

### 3) Benchmark-Vorbereitung für den Cluster

Das Jobskript liegt hier:

- [06/ex1/job.sh](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/06/ex1/job.sh)

Die Programme messen ihre Laufzeit mit `omp_get_wtime()`, also mit OpenMPs eigener Timing-Funktion.

Das Skript:

- kompiliert alle vier Programme mit `-O3` und `-fopenmp`
- setzt `OMP_NUM_THREADS` auf `1`, `4`, `8` und `12`
- führt für jede Konfiguration mehrere Läufe aus
- verwendet für `critical` standardmäßig weniger Wiederholungen
- schreibt vor und nach jedem Lauf einen kurzen Fortschrittsstatus ins Job-Log
- schreibt alle Rohdaten direkt in `results/time_results.csv`

Die Standardparameter im Skript sind:

- `RUNS=5` für `serial`, `atomic` und `reduction`
- `CRITICAL_RUNS=1` für `critical`
- `SAMPLES=700000000`

Der getrennte Wert für `critical` ist sinnvoll, weil diese Variante durch die globale kritische Sektion extrem schlecht skaliert und sonst leicht in das Slurm-Zeitlimit läuft.

Falls du die Varianten getrennt starten willst, geht das direkt über `sbatch`:

```bash
sbatch --export=ALL,VARIANTS="serial atomic reduction" job.sh
sbatch --export=ALL,VARIANTS="critical",CRITICAL_RUNS=1 job.sh
```

