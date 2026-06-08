# Assignment 12

## Exercise 1

### 1. Ziel der Aufgabe

In dieser Aufgabe soll ein unbekanntes numerisches Programm untersucht werden,
bevor es parallelisiert wird. Das Ziel ist also noch nicht die OpenMP-Umsetzung,
sondern die Suche nach den wichtigsten Rechenstellen.

Dafür wurde das Programm aus `real.tar.gz` entpackt, mit Profiling-Unterstützung
gebaut und ausgeführt. Der Lauf erzeugt die Datei `gmon.out`. Diese Datei kann
danach mit `gprof` ausgewertet werden.

Die verwendeten Befehle sind:

```bash
gcc -std=c99 -O3 -g -pg *.c -lm -o real_gprof
./real_gprof > run_output.txt
gprof --line real_gprof gmon.out > gprof_analysis.txt
```

Falls `gprof --line` auf dem System nicht verfügbar ist, kann auch die
einfachere Variante verwendet werden:

```bash
gprof real_gprof gmon.out > gprof_analysis.txt
```

### 2. Korrektheit des Programmlaufs

Das Programm wurde mit den kompilierten Standardwerten ausgeführt:

```text
Size:  256x 256x 256  (class B)
Iterations: 20
```

Die Ausgabe zeigt, dass der Programmlauf korrekt war:

```text
VERIFICATION SUCCESSFUL
L2 Norm is  1.8005644013551E-06
Error is    6.6330115975290E-14
```

Damit ist wichtig: Die Profiling-Daten stammen von einem gültigen Lauf. Es
wurde also nicht nur ein Teilprogramm oder ein fehlerhafter Testfall gemessen.

### 3. Gemessenes Profil

Der Benchmark selbst dauerte:

```text
benchmk: 5.836 s
```

Die programminternen Abschnittszeiten zeigen folgende Verteilung:

| Abschnitt | Zeit in Sekunden | Anteil |
|---|---:|---:|
| `mg3P` | 4.383 | 75.09 % |
| `resid` | 2.911 | 49.87 % |
| `psinv` | 1.401 | 24.01 % |
| `rprj3` | 0.696 | 11.92 % |
| `interp` | 0.597 | 10.22 % |
| `comm3` | 0.121 | 2.08 % |
| `norm2` | 0.053 | 0.90 % |

Die Werte addieren sich nicht alle direkt zu 100 Prozent, weil `mg3P` eine
übergeordnete Multigrid-Routine ist. Sie ruft andere Funktionen wie `resid`,
`psinv`, `rprj3` und `interp` auf. Deshalb ist `mg3P` eher als grober
Programmbereich zu verstehen, während die darunterliegenden Funktionen die
eigentlichen Rechenkerne enthalten.

### 4. Interpretation

Der wichtigste Befund ist, dass fast die gesamte relevante Laufzeit in wenigen
numerischen Kernfunktionen liegt.

Die Funktion `mg3P` ist mit etwa 75 Prozent der Benchmark-Zeit der zentrale
Programmbereich. Diese Funktion führt einen Multigrid-V-Zyklus aus. Sie ist
aber selbst nicht nur eine einzelne Rechenschleife, sondern koordiniert mehrere
Rechenoperationen auf verschiedenen Gitterebenen.

Innerhalb dieses Bereichs ist `resid` besonders wichtig. Die Funktion benötigt
insgesamt etwa 49.87 Prozent der Benchmark-Zeit. Sie berechnet das Residuum,
also vereinfacht gesagt die Abweichung zwischen aktueller Näherung und rechter
Seite des Gleichungssystems. Im Code geschieht das über dreifach geschachtelte
Schleifen über ein dreidimensionales Gitter.

Die Funktion `psinv` ist mit etwa 24.01 Prozent ebenfalls ein großer
Zeitanteil. Sie wendet einen Glatter auf das Residuum an. Auch diese Funktion
arbeitet über regelmäßige dreidimensionale Schleifen.

Danach folgen `rprj3` mit etwa 11.92 Prozent und `interp` mit etwa 10.22
Prozent. `rprj3` projiziert Daten auf ein gröberes Gitter, während `interp`
Daten von einem groberen auf ein feineres Gitter interpoliert. Beide Funktionen
sind ebenfalls typische numerische Gitteroperationen.

`comm3` und `norm2` sind deutlich kleiner. `comm3` aktualisiert Randbereiche des
Gitters. `norm2` berechnet Normen zur Kontrolle des Ergebnisses. Diese
Funktionen sind für die Korrektheit wichtig, aber für eine erste
Parallelisierung weniger wichtig als die großen Rechenkerne.

### 5. Was enthält ein `gprof`-Profil?

Ein `gprof`-Profil enthält vor allem zwei wichtige Sichten.

Die erste Sicht ist das sogenannte Flat Profile. Dort wird für jede Funktion
angezeigt, wie viel Zeit direkt in dieser Funktion verbracht wurde. Das ist
nützlich, weil man schnell erkennt, welche Funktionen die meiste Rechenzeit
verbrauchen.

Wichtige Spalten sind dabei:

- `% time`: Anteil der Laufzeit in dieser Funktion
- `self seconds`: Zeit, die direkt in dieser Funktion verbracht wurde
- `calls`: Anzahl der Funktionsaufrufe
- `self ms/call`: durchschnittliche Eigenzeit pro Aufruf
- `total ms/call`: durchschnittliche Zeit pro Aufruf inklusive aufgerufener
  Funktionen

Die zweite Sicht ist der Call Graph. Dort sieht man, welche Funktionen andere
Funktionen aufrufen. Das ist wichtig, weil eine Funktion wie `mg3P` viel Zeit
verursachen kann, obwohl ein großer Teil davon in Unterfunktionen wie `resid`
oder `psinv` entsteht.

### 6. Warum ist das für die Parallelisierung hilfreich?

Profiling verhindert, dass man zufällig an einer unwichtigen Stelle optimiert.
Bei diesem Programm zeigt das Profil klar, dass man zuerst die numerischen
Gitterkerne untersuchen sollte:

1. `resid`
2. `psinv`
3. `rprj3`
4. `interp`

Diese Funktionen enthalten große, regelmäßige Schleifen über
dreidimensionale Arrays. Solche Schleifen sind grundsätzlich gute Kandidaten
für OpenMP, weil viele Gitterpunkte nach demselben Muster berechnet werden.

Trotzdem darf man sie nicht blind parallelisieren. Vorher muss für jede
Schleife geprüft werden:

- Schreiben mehrere Iterationen auf dieselbe Speicherstelle?
- Gibt es Abhängigkeiten zwischen benachbarten Gitterpunkten?
- Werden temporäre Arrays wie `u1`, `u2`, `r1`, `r2`, `z1`, `z2` oder `z3`
  pro Thread privat benötigt?
- Müssen Randaktualisierungen wie in `comm3` getrennt behandelt werden?

Das Profil liefert also nicht direkt die fertige Parallelisierung. Es zeigt
aber, wo die Analyse beginnen sollte. Für Exercise 2 wäre deshalb der
sinnvolle nächste Schritt, zuerst `resid` und `psinv` auf sichere
OpenMP-Parallelisierung zu prüfen, danach `rprj3` und `interp`.

### 7. Zusammenfassung

Das Profil zeigt, dass das Programm stark von wenigen numerischen Kernfunktionen
dominiert wird. Der wichtigste Programmbereich ist `mg3P` mit etwa 75 Prozent
der Laufzeit. Darin sind besonders `resid` und `psinv` relevant. Zusammen mit
`rprj3` und `interp` bilden sie die wichtigsten Ansatzpunkte für eine spätere
OpenMP-Parallelisierung.

Damit ist die Profiling-Analyse für Exercise 1 abgeschlossen: Die Messung zeigt
nicht nur, dass das Programm korrekt ausgeführt wurde, sondern auch, welche
Funktionen für die Performance entscheidend sind.

## Exercise 2

### 1. Ziel der Aufgabe

In Exercise 2 soll das Programm mit OpenMP parallelisiert werden. Aus Exercise 1
war bereits ersichtlich, dass vor allem diese Funktionen relevant sind:

1. `resid`
2. `psinv`
3. `rprj3`
4. `interp`

Diese Funktionen enthalten große Schleifen über ein dreidimensionales Gitter.
Das ist ein typischer Fall für OpenMP, weil viele Gitterpunkte unabhängig
voneinander berechnet werden können.

Die Umsetzung liegt in:

- `12/ex2/real.c`
- `12/ex2/Makefile`
- `12/ex2/job.sh`

Die unveränderte Referenzversion liegt zusätzlich in:

- `12/ex2/original`

### 2. Parallelisierte Schleifen

#### `resid`

`resid` berechnet das Residuum:

```text
r = v - A u
```

Jeder innere Gitterpunkt schreibt genau ein Element von `r`. Die Werte von `u`
und `v` werden nur gelesen. Deshalb können die äußeren beiden Schleifen über
`i3` und `i2` parallelisiert werden.

Wichtig ist dabei, dass die temporären Arrays `u1` und `u2` nicht von mehreren
Threads gemeinsam benutzt werden. Deshalb werden sie innerhalb der parallelen
Schleife angelegt. Jeder Thread hat dadurch seine eigenen temporären Arrays.

#### `psinv`

`psinv` aktualisiert die Näherung `u` mit Hilfe des Residuums `r`.

Auch hier schreibt jede Iteration auf einen eigenen Gitterpunkt. Das Residuum
wird nur gelesen. Deshalb wurden ebenfalls die Schleifen über `i3` und `i2`
parallelisiert.

Die temporären Arrays `r1` und `r2` wurden in den Schleifenrumpf verschoben.
Damit entstehen keine Datenrennen zwischen Threads.

#### `rprj3`

`rprj3` projiziert Werte auf ein gröberes Gitter. Jede Iteration schreibt auf
einen eigenen Punkt im Zielgitter `s`. Die Eingabedaten aus `r` werden nur
gelesen.

Die äußere Schleife über `j3` wurde mit OpenMP parallelisiert. Eine
Parallelisierung mit `collapse(2)` wurde hier nicht verwendet, weil zwischen
den Schleifen noch Indexwerte wie `i3` berechnet werden. Dadurch sind die
Schleifen nicht perfekt geschachtelt. Auch hier müssen temporäre Arrays wie
`x1` und `y1` thread-lokal sein.

#### `interp`

`interp` interpoliert Werte vom gröberen auf das feinere Gitter. Für den
normalen Fall, also wenn keine Gitterdimension gleich `3` ist, wurden die
Schleifen über `i3` und `i2` parallelisiert.

Der Spezialfall für sehr kleine Gitter bleibt sequenziell. Dieser Teil ist für
die Gesamtlaufzeit weniger wichtig und ist wegen der vielen Indexfälle
fehleranfälliger. Diese Entscheidung hält die Parallelisierung einfacher und
sicherer.

#### `norm2u3` und `zero3`

`norm2u3` berechnet eine Summe und ein Maximum. Dafür wurde eine OpenMP-Reduction
verwendet:

```c
reduction(+:s) reduction(max:my_rnmu)
```

`zero3` setzt ein dreidimensionales Array auf `0.0`. Diese Operation ist
ebenfalls gut parallelisierbar, weil jedes Arrayelement unabhängig geschrieben
wird.

### 3. Verwendete OpenMP-Strategie

Für die großen Gitterkerne wurde meistens diese Form verwendet:

```c
#pragma omp parallel for collapse(2) schedule(static)
```

`collapse(2)` fasst zwei geschachtelte Schleifen zu einem größeren
Iterationsraum zusammen. Das ist sinnvoll, weil dadurch mehr Arbeit auf die
Threads verteilt werden kann.

`schedule(static)` verteilt die Iterationen fest auf die Threads. Das passt hier
gut, weil die Arbeit pro Gitterpunkt ungefähr gleich groß ist.

Bei `rprj3` wird dagegen nur die äußere Schleife parallelisiert:

```c
#pragma omp parallel for schedule(static)
```

Der Grund ist, dass OpenMP für `collapse(2)` perfekt geschachtelte Schleifen
verlangt. Diese Bedingung ist in `rprj3` wegen der zusätzlichen
Indexberechnungen zwischen den Schleifen nicht erfüllt.

### 4. Benchmark auf LCC3

Für den Benchmark wird das Jobscript verwendet:

```bash
cd 12/ex2
sbatch job.sh
```

Das Skript baut beide Versionen mit `gcc`:

- `real_seq`: unveränderte sequenzielle Referenz
- `real_omp`: OpenMP-Version

Danach führt es die OpenMP-Version mit 1, 2, 6 und 12 Threads aus.

Die relevanten Ausgaben liegen nach dem Lauf in:

```text
12/ex2/results/
```

Für die Auswertung sind besonders diese Dateien wichtig:

- `results/seq_output.txt`
- `results/omp_1_threads_output.txt`
- `results/omp_2_threads_output.txt`
- `results/omp_6_threads_output.txt`
- `results/omp_12_threads_output.txt`
- `results/benchmark_summary.txt`

### 5. Ergebnistabelle

Der Benchmark wurde auf LCC3 mit der Problemklasse B ausgeführt:

```text
Size: 256 x 256 x 256
Iterations: 20
```

Alle gemessenen Varianten wurden erfolgreich verifiziert.

Die Tabelle verwendet die äußere Wall Time. Diese Zeit wurde mit
`/usr/bin/time` gemessen und umfasst den vollständigen Programmlauf inklusive
Initialisierung, Benchmark, Verifikation und Ausgabe.

| Version | Threads | Wall Time in Sekunden | Speedup gegenüber sequenziell | Verifikation |
|---|---:|---:|---:|---|
| Original | 1 | 6.88 | 1.00 | erfolgreich |
| OpenMP | 1 | 7.17 | 0.96 | erfolgreich |
| OpenMP | 2 | 4.76 | 1.45 | erfolgreich |
| OpenMP | 6 | 4.40 | 1.56 | erfolgreich |
| OpenMP | 12 | 2.90 | 2.37 | erfolgreich |

Erinnerung:

```text
Speedup = Wall Time der sequenziellen Referenz / Wall Time der OpenMP-Version
```

### 6. Diskussion der Ergebnisse

Die OpenMP-Version mit einem Thread ist etwas langsamer als die sequenzielle
Referenz. Das ist plausibel, weil OpenMP auch bei nur einem Thread zusätzlichen
Overhead erzeugt. Dazu gehören zum Beispiel das Erzeugen paralleler Regionen und
die Verwaltung der Schleifenverteilung.

Mit zwei Threads sinkt die Wall Time von `6.88 s` auf `4.76 s`. Das entspricht
einem Speedup von etwa `1.45`. Die Parallelisierung wirkt also, erreicht aber
noch keine ideale Verdopplung.

Mit sechs Threads beträgt die Wall Time `4.40 s`. Der Speedup steigt damit nur
auf etwa `1.56`. Dieser Schritt skaliert schwächer als erwartet. Ein Grund ist,
dass nicht alle Programmteile parallelisiert wurden. Außerdem sind einige
Operationen speicherlastig. Dann begrenzt die Speicherbandbreite, wie stark
zusätzliche Threads helfen können.

Mit zwölf Threads fällt die Wall Time auf `2.90 s`. Das entspricht einem
Speedup von etwa `2.37`. Das ist der beste gemessene Wert. Trotzdem bleibt der
Speedup deutlich unter `12`, weil weiterhin sequenzielle und schlecht
skalierende Programmteile vorhanden sind.

Nach Amdahls Gesetz begrenzt jeder sequenzielle Programmteil den maximalen
Speedup. Das betrifft hier unter anderem:

- den Multigrid-Ablauf selbst
- die Randbehandlung in `comm3`
- Initialisierung und Zufallsdaten in `zran3`
- kleinere Gitterebenen mit wenig Arbeit

Auch die internen Abschnittszeiten zeigen, dass die wichtigsten Kernfunktionen
schneller werden. Diese Zeiten messen nur den Benchmark-Abschnitt und sind
deshalb kleiner als die äußere Wall Time. Zum Beispiel sinkt `psinv` von
`1.328 s` in der Referenz auf `0.338 s` mit zwölf Threads. `resid` sinkt von
`2.664 s` auf `0.896 s`. Gleichzeitig bleibt `comm3` relativ klein, skaliert
aber nicht gut. Bei zwölf Threads liegt `comm3` bei `0.132 s` und ist damit
etwas höher als in der sequenziellen Referenz. Das passt zur Interpretation,
dass Randbehandlung und Verwaltung bei mehr Threads stärker ins Gewicht fallen.

Wichtig bleibt, dass alle Versionen weiterhin korrekt verifiziert wurden. Die
OpenMP-Änderungen haben also die numerische Korrektheit nicht verletzt.

### 7. Zusammenfassung

Die Parallelisierung verbessert die Laufzeit deutlich. Die beste gemessene
Variante ist die OpenMP-Version mit zwölf Threads:

```text
Original, 1 Thread: 6.88 s
OpenMP, 12 Threads: 2.90 s
Speedup: 2.37
```

Der Speedup ist nicht ideal, aber sachlich erklärbar. Das Programm enthält
weiterhin sequenzielle Teile, kleinere Gitterebenen mit wenig Arbeit und
speicherlastige Operationen. Insgesamt zeigt der Benchmark trotzdem, dass die
aus dem Profiling ausgewählten Schleifen sinnvolle Ansatzpunkte für OpenMP
waren.
