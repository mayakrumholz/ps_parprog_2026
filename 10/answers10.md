# Assignment 10

Team: Maya Krumholz & Marie Sagerer

## Exercise 1

### Überblick und Ziel der Aufgabe

In dieser Aufgabe soll untersucht werden, ob und wie sich eine sehr einfache Rechenschleife durch Compiler-Vektorisierung beschleunigen lässt. Die betrachtete Operation ist:

```c
a[i] += b[i] * c[i];
```

Diese Operation wird nicht nur einmal, sondern `1e6` mal auf drei `float`-Vektoren ausgeführt. Das ist wichtig, weil die Laufzeit sonst zu kurz wäre, um Unterschiede zwischen zwei Compiler-Konfigurationen zuverlässig zu messen.

Die Kernfrage der Aufgabe ist:

- Wie schnell ist die reine sequenzielle Referenz?
- Was ändert sich, wenn nur die Auto-Vektorisierung des Compilers aktiviert wird?
- Bleibt das Ergebnis korrekt?
- Wie lässt sich ein Geschwindigkeitsunterschied mit `perf` erklären?


### Fachliches Verständnis der Aufgabe

Die Schleife hat aus Sicht des Compilers eine günstige Struktur:

- jede Iteration arbeitet auf einem eigenen Index `i`
- es gibt keine offensichtige Schleifenabhängigkeit zwischen verschiedenen Iterationen
- die Datenzugriffe sind linear und regelmäßig

Genau solche Schleifen sind gute Kandidaten für SIMD-Vektorisierung.

Die Grundidee ist:

- ohne Vektorisierung verarbeitet die CPU typischerweise pro Instruktion nur einen `float`-Wert
- mit Vektorisierung kann eine SIMD-Instruktion mehrere `float`-Werte gleichzeitig verarbeiten

Für diese Aufgabe wird **nicht** der Algorithmus geändert. Stattdessen wird dasselbe Programm mit zwei verschiedenen Compiler-Einstellungen gebaut:

- `baseline`: `-O1 -fno-tree-vectorize`
- `auto_vectorized`: `-O1 -ftree-vectorize`

Dadurch bleibt der Vergleich fair: Die Programmstruktur ist identisch, nur die Vektorisierung des Compilers wird umgeschaltet.


### Implementierte Lösung

Verwendete Dateien:

- Programm: [10/ex1/vector_add.c](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/10/ex1/vector_add.c)
- Build-Datei: [10/ex1/Makefile](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/10/ex1/Makefile)
- Jobscript: [10/ex1/job.sh](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/10/ex1/job.sh)
- Auswertung: [10/ex1/analyze_results.py](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/10/ex1/analyze_results.py)

Das C-Programm macht genau die geforderte Rechnung und trennt die Schritte sauber:

1. Speicher für `a`, `b` und `c` reservieren
2. alle drei Vektoren mit konstanten Werten initialisieren
3. nur die eigentliche Rechenschleife messen
4. das Ergebnis auf Korrektheit prüfen
5. parsebare Ausgaben für die automatische Auswertung erzeugen

Die zentrale Schleife ist:

```c
for (int run = 0; run < repetitions; ++run) {
    for (int i = 0; i < size; ++i) {
        a[i] += b[i] * c[i];
    }
}
```

Die Messung umfasst bewusst **nur** den Bereich zwischen Start- und Endzeitpunkt dieser Rechenschleife. Initialisierung, Speicherallokation und Korrektheitsprüfung werden nicht mitgemessen, weil die Aufgabenstellung explizit die Ausführungszeit der Berechnung verlangt.


### Warum diese Initialisierung korrekt und numerisch stabil ist

Für alle Elemente werden die konstanten Startwerte verwendet:

```text
a[i] = 1.0
b[i] = 0.5
c[i] = 0.25
```

Pro Schleifendurchlauf wird damit immer

```text
b[i] * c[i] = 0.125
```

zu `a[i]` addiert.

Nach `1e6` Wiederholungen ist der erwartete Wert:

```text
a[i] = 1.0 + 1e6 * 0.125 = 125001.0
```

Dieser Wert ist für `float` völlig unkritisch und vermeidet Überläufe. Das Programm prüft mehrere Stichprobenwerte sowie die Gesamtsumme gegen den erwarteten Wert und bricht bei einer Abweichung ab.


### Was am Code für die Vektorisierung relevant ist

Die eigentliche Rechenschleife liegt in einer eigenen Funktion:

```c
static void run_kernel(float *restrict a,
                       const float *restrict b,
                       const float *restrict c,
                       int size,
                       int repetitions)
```

Die `restrict`-Qualifier sind hier wichtig, weil sie dem Compiler sagen, dass `a`, `b` und `c` nicht auf überlappende Speicherbereiche zeigen. Das erleichtert der Auto-Vektorisierung die Analyse, weil der Compiler weniger konservativ bezüglich möglicher Alias-Effekte sein muss.

Zusätzlich werden die Arrays 64-Byte-ausgerichtet alloziert. Das ist nicht zwingend notwendig, verbessert aber die Voraussetzungen für effiziente Vektorzugriffe.


### Messaufbau auf LCC3

Das Jobscript testet mehrere Problemgrößen:

```text
256, 512, 1024, 2048, 4096, 8192
```

Für jede Größe werden beide Varianten jeweils `5` mal gemessen:

- `baseline`
- `auto_vectorized`

Außerdem werden für die Größen `2048` und `8192` zusätzliche `perf`-Messungen durchgeführt. Dabei werden diese Ereignisse aufgezeichnet:

- `cycles`
- `instructions`
- `r0410` = `FP_COMP_OPS_EXE.SSE_FP`
- `r1010` = `FP_COMP_OPS_EXE.SSE_FP_PACKED`
- `r2010` = `FP_COMP_OPS_EXE.SSE_FP_SCALAR`
- `r4010` = `FP_COMP_OPS_EXE.SSE_SINGLE_PRECISION`

Gerade `SSE_FP_PACKED` und `SSE_FP_SCALAR` sind für diese Aufgabe besonders interessant:

- ein Anstieg von `SSE_FP_PACKED` spricht dafür, dass mehrere `float`-Operationen in SIMD-Paketen ausgeführt werden
- ein hoher Anteil an `SSE_FP_SCALAR` deutet eher auf skalar ausgeführte Gleitkommaoperationen hin


### Automatische Auswertung

Nach dem Lauf auf LCC3 erzeugt die Auswertung automatisch:

- Rohdaten: `10/ex1/results/time_results.csv`
- aggregierte Laufzeitstatistik: `10/ex1/results/summary_stats.csv`
- Speedup-Tabelle: `10/ex1/results/speedup_stats.csv`
- Markdown-Zusammenfassung: `10/ex1/results/summary_table.md`
- `perf`-Zusammenfassung: `10/ex1/results/perf_summary.csv`
- Abbildungen auf Basis der echten Messdaten:
  - `10/ex1/results/plots/runtime_by_size.svg`
  - `10/ex1/results/plots/speedup_by_size.svg`
  - `10/ex1/results/plots/perf_vector_events.svg`

Damit ist die Lösung reproduzierbar aufgebaut: Der gesamte Weg von der Messung bis zur Auswertung ist Teil des Projekts.


### Erwartung vor der Cluster-Ausführung

Vor der tatsächlichen Ausführung auf LCC3 ist die fachlich sinnvolle Erwartung:

1. Die Auto-Vektorisierung sollte bei dieser Schleife prinzipiell möglich sein.
2. Die auto-vektorisierte Variante sollte für mittlere und größere Problemgrößen schneller sein als die Baseline.
3. Der Speedup muss nicht konstant sein, weil Startkosten, Speicherverhalten und SIMD-Auslastung von der Problemgröße abhängen.
4. Das Ergebnis sollte unverändert korrekt bleiben, weil Vektorisierung hier nur die Ausführungsform ändert, nicht die mathematische Bedeutung der einzelnen Iterationen.

Diese Punkte sind zunächst Hypothesen. Die endgültige Bewertung soll erst nach den realen Messdaten auf LCC3 erfolgen.


### Durchführung auf LCC3

Auf dem Cluster sind für Exercise 1 nur diese Schritte nötig:

```bash
cd 10/ex1
sbatch job.sh
```

Wichtige Ausgabedateien nach dem Lauf:

- `10/ex1/job_ex1.log`
- `10/ex1/results/time_results.csv`
- `10/ex1/results/perf_results.csv`
- `10/ex1/results/summary_table.md`
- `10/ex1/results/perf_summary.md`
- `10/ex1/results/plots/*.svg`


### Ergebnisse

Die finale Ergebnisinterpretation wird ergänzt, sobald die echten LCC3-Daten vorliegen und zurück ins Repository gepusht wurden.

Dann sollen hier insbesondere eingetragen werden:

- mittlere Laufzeit der Baseline bei `size = 2048`
- mittlere Laufzeit der auto-vektorisierten Variante bei `size = 2048`
- berechneter Speedup
- Beobachtungen über den Einfluss der Problemgröße
- Interpretation der `perf`-Zähler
- Auswahl der Abbildung(en), die den Unterschied am besten erklären


### Vorläufiges Fazit

Die Aufgabe ist bis zur eigentlichen Cluster-Ausführung vollständig vorbereitet:

- Referenzprogramm vorhanden
- Compiler-Vektorisierungsvariante vorhanden
- Korrektheitsprüfung eingebaut
- LCC3-Jobscript vorbereitet
- automatische Datenauswertung vorbereitet
- spätere Diagrammerzeugung aus echten Messdaten vorbereitet

Sobald die Ergebnisse von LCC3 vorliegen, kann darauf aufbauend die endgültige Analyse ergänzt und die Abgabe in eine vollständig ausformulierte Endfassung überführt werden.
