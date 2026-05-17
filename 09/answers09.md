# Assignment 9

## Exercise 1

### Überblick

Für diese Aufgabe habe ich das Programm aus `09/first_touch/first_touch.c` mit OpenMP parallelisiert und so erweitert, dass man den First-Touch-Effekt gezielt vergleichen kann.

Es gibt jetzt zwei klar getrennte Fälle:

- `parallel`: Die Matrix wird parallel initialisiert. Dadurch werden die Speicherseiten beim ersten Schreiben von den Threads angefasst, die später idealerweise auch wieder darauf rechnen. Das ist der Fall **mit** First-Touch-Vorteil.
- `serial`: Die Matrix wird seriell initialisiert. Dann werden die Speicherseiten zuerst nur von einem Thread angefasst. Wenn später 12 Threads parallel darauf rechnen, ist die Speicherlokalität schlechter. Das ist der Fall **ohne** First-Touch-Vorteil.

Zusätzlich kann die Loop-Scheduling-Strategie gewählt werden:

- `static`
- `dynamic`
- `guided`

Damit kann man nicht nur den First-Touch-Effekt zeigen, sondern auch beantworten, ob das Scheduling dabei eine Rolle spielt.

Verwendete Dateien:

- Programm: [09/first_touch/first_touch.c](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/09/first_touch/first_touch.c)
- Build-Datei: [09/first_touch/Makefile](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/09/first_touch/Makefile)
- Jobscript: [09/first_touch/job.sh](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/09/first_touch/job.sh)
- Auswertung: [09/first_touch/analyze_results.py](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/09/first_touch/analyze_results.py)


### 1) Parallelisierung des Programms mit OpenMP

Die ursprüngliche Vorlage hat die Matrix seriell initialisiert und seriell aufsummiert.

Ich habe das Programm in diesen Punkten erweitert:

1. Die Matrix wird weiter dynamisch alloziert.
2. Die eigentlichen Daten liegen jetzt in **einem zusammenhängenden Speicherblock**.
3. Die Initialisierung kann wahlweise seriell oder parallel ausgeführt werden.
4. Die Berechnung der Summe läuft parallel mit OpenMP.
5. Die Scheduling-Strategie wird zur Laufzeit gewählt.
6. Das Programm gibt parsebare Messwerte aus, damit das Jobscript die Zahlen automatisch in eine CSV-Datei schreiben kann.

Die parallele Berechnung der Summe verwendet eine `reduction`, damit kein Race Condition auf `sum` entsteht:

```c
#pragma omp parallel for reduction(+ : sum) schedule(runtime)
for (int i = 0; i < n; ++i) {
    for (int j = 0; j < n; ++j) {
        sum += matrix[i][j];
    }
}
```

Warum `reduction` richtig ist:

- jeder Thread berechnet zunächst eine private Teilsumme
- am Ende werden alle Teilsummen korrekt zusammengeführt
- dadurch ist die Lösung korrekt und effizient

Zur Korrektheitsprüfung berechnet das Programm zusätzlich die erwartete Summe:

```text
expected_sum = N * N * (N - 1)
```

Nur wenn die berechnete Summe und die erwartete Summe übereinstimmen, endet das Programm erfolgreich.


### 2) Wie werden 12 Threads auf feste physische Kerne gebunden?

Die Bindung der Threads an Kerne wird hier **nicht im C-Code**, sondern im Jobscript über OpenMP-Umgebungsvariablen gesteuert:

```bash
export OMP_NUM_THREADS=12
export OMP_PLACES=cores
export OMP_PROC_BIND=true
```

Bedeutung:

- `OMP_NUM_THREADS=12`
  startet genau 12 OpenMP-Threads
- `OMP_PLACES=cores`
  verwendet Kerne als mögliche Bindungsorte
- `OMP_PROC_BIND=true`
  sorgt dafür, dass Threads an diese Orte gebunden bleiben und nicht frei zwischen Kernen wandern

Damit bekommt jeder Thread einen festen Kern zugewiesen. Das ist wichtig, weil der First-Touch-Effekt nur dann sauber messbar ist, wenn Threads nicht ständig ihre Ausführungsorte wechseln.

Im SLURM-Jobscript werden außerdem 12 CPUs reserviert:

```bash
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --exclusive
```

Das bedeutet:

- ein Prozess
- 12 CPU-Kerne für diesen Prozess
- exklusiver Zugriff auf den Knoten während des Jobs


### 3) Wie wird der First-Touch-Effekt mit minimalen Codeänderungen demonstriert?

Die Idee ist sehr einfach:

- Im **guten Fall** wird die Matrix parallel initialisiert.
- Im **schlechten Fall** wird die Matrix seriell initialisiert.
- Die eigentliche Berechnung der Summe bleibt in beiden Fällen parallel.

So wird fast nur die Art des ersten Speicherzugriffs geändert. Genau dadurch lässt sich der First-Touch-Effekt sichtbar machen.

#### Guter Fall: First-Touch wird genutzt

```text
./first_touch 40000 parallel static
```

Hier schreiben die Threads die Matrix schon bei der Initialisierung selbst. Bei `static`-Scheduling bekommen Threads typischerweise zusammenhängende Zeilenblöcke. Wenn später die Summe wieder mit `static`-Scheduling berechnet wird, arbeiten die Threads meist wieder auf denselben Datenbereichen. Das verbessert die Speicherlokalität.

#### Schlechter Fall: Kein First-Touch-Vorteil

```text
./first_touch 40000 serial static
```

Hier wird die Matrix zuerst nur seriell beschrieben. Dadurch landen die Speicherseiten zuerst bei einem einzigen Ausführungskontext. Wenn später 12 Threads parallel darauf arbeiten, müssen viele Zugriffe auf Speicherbereiche erfolgen, die nicht lokal zu ihrem Thread liegen. Das ist genau der Effekt, den man zeigen möchte.

Wichtig:

- Die Rechenschleife bleibt parallel.
- Es ändert sich nur, **wer den Speicher zuerst beschreibt**.
- Genau deshalb ist das eine minimal-invasive Demonstration des First-Touch-Effekts.


### 4) Beeinflussen Loop-Scheduling-Strategien den First-Touch-Effekt?

Ja, **Loop-Scheduling-Strategien können den First-Touch-Effekt beeinflussen**.

Der Grund ist:

- First Touch ist dann besonders hilfreich, wenn **derselbe Thread** später wieder auf die Daten zugreift, die er zuerst beschrieben hat.
- Das Scheduling entscheidet aber, **welcher Thread welche Iterationen** ausführt.

#### Fall `static`

`static` ist für First Touch meistens die beste Wahl.

Warum:

- die Iterationen werden vorhersagbar und in festen Blöcken auf Threads verteilt
- bei Initialisierung und Berechnung kann dadurch sehr oft dieselbe Datenaufteilung entstehen
- das erhöht die Chance, dass ein Thread „seine“ Daten später wieder selbst benutzt

#### Fall `dynamic`

`dynamic` kann den First-Touch-Vorteil abschwächen oder teilweise zerstören.

Warum:

- Iterationen werden erst zur Laufzeit verteilt
- Threads holen sich die nächsten Blöcke dynamisch
- dadurch ist es viel weniger wahrscheinlich, dass dieselben Daten wieder vom selben Thread bearbeitet werden

Dann kann es passieren, dass Speicher lokal zu Thread A angelegt wurde, aber später oft von Thread B gelesen wird. Das erzeugt zusätzliche NUMA-Kosten.

#### Fall `guided`

`guided` verhält sich ähnlich wie `dynamic`, nur mit anfangs größeren und später kleineren Blöcken.

Das heißt:

- auch hier ist die Zuordnung weniger stabil als bei `static`
- deshalb kann auch `guided` den First-Touch-Vorteil verschlechtern

#### Fazit zu Aufgabe 4

Ja, das Scheduling beeinflusst First Touch, **weil es die Zuordnung von Daten zu Threads indirekt verändert**.

Kurz gesagt:

- `static`: gut für reproduzierbare Datenlokalität
- `dynamic` und `guided`: meist schlechter für Datenlokalität, wenn First Touch ausgenutzt werden soll


### 5) Messung auf LCC3 mit Jobscript

Das vorbereitete Jobscript liegt hier:

- [09/first_touch/job.sh](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/09/first_touch/job.sh)

Es macht automatisch folgende Schritte:

1. lädt bei Bedarf das GCC-Modul
2. kompiliert das Programm mit OpenMP
3. setzt die Affinity-Variablen für 12 feste Threads
4. führt alle Messungen mit `N=40000` aus
5. testet beide Initialisierungsmodi:
   `parallel` und `serial`
6. testet alle drei Schedules:
   `static`, `dynamic`, `guided`
7. wiederholt jede Konfiguration `5` mal
8. schreibt alle Rohdaten nach `results/time_results.csv`
9. erzeugt daraus:
   - `results/summary_stats.csv`
   - `results/summary_table.md`

Ausführen auf LCC3:

```bash
cd 09/first_touch
sbatch job.sh
```

Jobstatus prüfen:

```bash
squ
```

Nach dem Lauf die erzeugten Dateien ansehen:

```bash
cat results/summary_table.md
cat results/summary_stats.csv
```


### 6) Welche Werte müssen in die Comparison Spreadsheet eingetragen werden?

Für die Aufgabenstellung sind bei `12` Threads und `N=40000` besonders diese beiden Fälle wichtig:

- **mit First-Touch-Vorteil**:
  `init_mode=parallel`, `schedule=static`
- **ohne First-Touch-Vorteil**:
  `init_mode=serial`, `schedule=static`

In die Comparison Spreadsheet gehört die **Wall-Clock-Time** dieser beiden Fälle.

Für die Abgabe würde ich dafür den Mittelwert der Spalte `computation_mean` aus `results/summary_table.md` verwenden, weil genau diese Zeit die eigentliche Rechenphase der Matrixsumme misst.


### 7) Ergebnisvorlage zum Eintragen nach dem Clusterlauf

Nach dem Ausführen des Jobs bitte die Zahlen aus `results/summary_table.md` hier eintragen.

#### Relevante Messwerte für Aufgabe 5

| Fall | Init-Modus | Schedule | Threads | N | Compute mean [s] |
| --- | --- | --- | ---: | ---: | ---: |
| mit First-Touch-Vorteil | parallel | static | 12 | 40000 | `<hier eintragen>` |
| ohne First-Touch-Vorteil | serial | static | 12 | 40000 | `<hier eintragen>` |


### 8) Erwartete Beobachtung

Ich erwarte auf einem NUMA-System wie LCC3:

- `parallel + static` ist schneller als `serial + static`
- `dynamic` und `guided` sind oft schlechter als `static`, wenn man First Touch ausnutzen möchte

Der Grund ist, dass `parallel + static` die beste Chance bietet, dass Speicherlokalität zwischen Initialisierung und Berechnung erhalten bleibt.


### 9) Schritt-für-Schritt-Erklärung in einfacher Sprache

#### Schritt 1: Speicher reservieren

Zuerst wird Platz für die Matrix im Hauptspeicher reserviert.

Wichtig dabei:

- `malloc` reserviert nur den Adressraum
- die physische Zuordnung der Speicherseiten passiert bei normalen anonymen Speicherzugriffen typischerweise erst beim **ersten Schreiben**

Genau darum geht es bei First Touch.

#### Schritt 2: Matrix zum ersten Mal beschreiben

Jetzt wird in jedes Matrixelement ein Wert geschrieben:

```c
matrix[i][j] = i + j;
```

Dabei gibt es zwei Varianten:

- seriell
- parallel

Der Thread, der eine Seite zuerst beschreibt, sorgt typischerweise dafür, dass diese Seite auf „seinem“ NUMA-Bereich landet.

#### Schritt 3: Matrix später parallel lesen

Danach wird die gesamte Matrix parallel aufsummiert.

Wenn dieselben Threads wieder ungefähr dieselben Bereiche bearbeiten, ist das gut für die Lokalität.

Wenn andere Threads auf diese Bereiche zugreifen, müssen Daten häufiger über NUMA-Grenzen bewegt werden. Das kostet Zeit.

#### Schritt 4: Schedules vergleichen

Mit `static`, `dynamic` und `guided` wird getestet, wie stabil oder instabil die Verteilung der Arbeit auf Threads ist.

Das hilft, die Antwort zu Aufgabe 4 nicht nur theoretisch, sondern auch experimentell zu begründen.


### 10) Lokale Vorprüfung

Die echte Zielmessung muss auf LCC3 laufen, weil dort die NUMA-Eigenschaften des Clusterknotens relevant sind.

Lokal kann man aber schon prüfen, ob das Programm korrekt kompiliert und grundsätzlich läuft:

```bash
cd 09/first_touch
make
OMP_NUM_THREADS=4 OMP_PLACES=cores OMP_PROC_BIND=true ./first_touch 2000 parallel static
OMP_NUM_THREADS=4 OMP_PLACES=cores OMP_PROC_BIND=true ./first_touch 2000 serial static
```

Wenn beide Läufe erfolgreich sind und `sum` gleich `expected_sum` ist, funktioniert die Implementierung korrekt.
