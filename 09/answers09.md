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

Warum `reduction`:

- jeder Thread berechnet zunächst eine private Teilsumme
- am Ende werden alle Teilsummen korrekt zusammengeführt

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

Es macht folgende Schritte:

1. kompiliert das Programm mit OpenMP
2. setzt die Affinity-Variablen für 12 feste Threads
3. führt alle Messungen mit `N=40000` aus
4. testet beide Initialisierungsmodi:
   `parallel` und `serial`
5. testet alle drei Schedules:
   `static`, `dynamic`, `guided`
6. wiederholt jede Konfiguration `5` mal
7. schreibt alle Rohdaten nach `results/time_results.csv`
8. erzeugt daraus:
   - `results/summary_stats.csv`
   - `results/summary_table.md`



### 6) Gemessene Ergebnisse auf LCC3

Die Auswertung der Rohdaten aus `results/time_results.csv` ergibt folgende Mittelwerte für die Rechenphase:

#### Relevante Messwerte für Aufgabe 5

| Fall | Init-Modus | Schedule | Threads | N | Compute mean [s] |
| --- | --- | --- | ---: | ---: | ---: |
| mit First-Touch-Vorteil | parallel | static | 12 | 40000 | `0.423355` |
| ohne First-Touch-Vorteil | serial | static | 12 | 40000 | `0.648515` |


#### Interpretation dieser beiden Hauptwerte

Der Fall mit First Touch (`parallel + static`) ist klar schneller als der Fall ohne First Touch (`serial + static`).

Genauer:

- ohne First Touch: `0.648515 s`
- mit First Touch: `0.423355 s`

Die Differenz beträgt:

```text
0.648515 s - 0.423355 s = 0.225160 s
```

Relativ gesehen ist die Rechenphase mit First Touch ungefähr **1.53-mal schneller** als ohne First Touch:

```text
0.648515 / 0.423355 ≈ 1.532
```

Oder anders formuliert:

- die Rechenzeit sinkt um ungefähr **34.7 %**

Das ist genau die Beobachtung, die man von First Touch auf einem NUMA-System erwartet:

- wenn die Threads den Speicher schon bei der Initialisierung passend „anfassen“
- und später mit derselben Datenaufteilung weiterrechnen
- dann werden unnötige entfernte Speicherzugriffe reduziert


### 8) Einfluss des Schedulings auf First Touch


#### Übersicht der gemessenen Rechenzeiten

| Init-Modus | Schedule | Compute mean [s] |
| --- | --- | ---: |
| parallel | static | `0.423355` |
| parallel | dynamic | `0.498355` |
| parallel | guided | `0.440965` |
| serial | static | `0.648515` |
| serial | dynamic | `0.548355` |
| serial | guided | `0.533050` |

#### Was sieht man daran?

Bei **paralleler Initialisierung** ist `static` am besten:

- `parallel + static`: `0.423355 s`
- `parallel + guided`: `0.440965 s`
- `parallel + dynamic`: `0.498355 s`

Das passt gut zur Theorie:

- bei `static` bleibt die Zuordnung von Datenbereichen zu Threads am stabilsten
- dadurch kann der First-Touch-Vorteil am besten erhalten bleiben

Bei **serieller Initialisierung** ist `static` dagegen am schlechtesten:

- `serial + static`: `0.648515 s`
- `serial + dynamic`: `0.548355 s`
- `serial + guided`: `0.533050 s`

Das zeigt ebenfalls, dass das Scheduling eine Rolle spielt.

Eine einfache Interpretation ist:

- bei `serial` gibt es von Anfang an keine gute First-Touch-Zuordnung für alle Threads
- dann kann eine andere Arbeitsverteilung in der Rechenphase die tatsächlichen Speicherzugriffe spürbar verändern

#### Antwort auf Frage

Ja, die Loop-Scheduling-Strategie **beeinflusst** First Touch.

Begründung:

- First Touch ist dann am wirkungsvollsten, wenn der Thread später wieder auf genau die Daten zugreift, die er zuvor selbst initialisiert hat
- `static` hält diese Zuordnung am ehesten stabil
- `dynamic` und `guided` ändern die Zuordnung der Arbeit während der Laufzeit stärker
- dadurch kann der Lokalitätsvorteil kleiner werden oder teilweise verloren gehen

Die Messungen auf LCC3 bestätigen genau das:

- mit First Touch ist `static` die beste Variante
- wenn keine gute First-Touch-Zuordnung vorhanden ist, verändern andere Schedules das Verhalten deutlich


### 9) Zusammenfassung der Beobachtung

Die Experimente zeigen den First-Touch-Effekt klar:

- `parallel + static` ist mit `0.423355 s` die beste Konfiguration für den eigentlichen First-Touch-Vergleich
- `serial + static` ist mit `0.648515 s` deutlich langsamer
- der Unterschied ist groß genug, um den Effekt klar zu sehen
- das Scheduling beeinflusst das Ergebnis zusätzlich und damit auch die Stärke des Lokalitätsvorteils


## Exercise 2

### Überblick

Für diese Aufgabe habe ich ein neues Programm für Delannoy-Zahlen erstellt. Es unterstützt:

- eine **sequenzielle** Variante
- eine **OpenMP-Task-Variante**

Verwendete Dateien:

- Programm: [09/delannoy/delannoy.c](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/09/delannoy/delannoy.c)
- Build-Datei: [09/delannoy/Makefile](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/09/delannoy/Makefile)
- Jobscript: [09/delannoy/job.sh](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/09/delannoy/job.sh)
- Auswertung: [09/delannoy/analyze_results.py](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/09/delannoy/analyze_results.py)

Die Lösung basiert auf der einfachen Rekurrenz:

```text
D(m, n) = D(m - 1, n) + D(m - 1, n - 1) + D(m, n - 1)
```

mit den Basisfällen:

```text
D(0, n) = 1
D(m, 0) = 1
```

Für die Aufgabe brauchen wir den zentralen Delannoy-Wert `D(N, N)`.


### 1) Sequenzielle Implementierung

Die sequenzielle Variante ist eine direkte rekursive Umsetzung der Rekurrenz:

```c
static unsigned long long delannoy_seq(int m, int n) {
    if (m == 0 || n == 0) {
        return 1ULL;
    }

    return delannoy_seq(m - 1, n)
        + delannoy_seq(m - 1, n - 1)
        + delannoy_seq(m, n - 1);
}
```

Wichtig dabei:

- es wird **keine dynamische Programmierung**
- **keine Memoisierung**
- und **keine mathematische Abkürzung**

verwendet.

Damit ist die Lösung wirklich die geforderte **naive** Variante.

#### Korrektheitsprüfung

Im Programm sind bekannte zentrale Delannoy-Zahlen für `N = 0` bis `15` hinterlegt. Dazu gehören zum Beispiel:

- `D(0,0) = 1`
- `D(1,1) = 3`
- `D(2,2) = 13`
- `D(3,3) = 63`
- `D(12,12) = 251595969`
- `D(15,15) = 44642381823`

Nach jedem Lauf vergleicht das Programm den berechneten Wert mit dem erwarteten Wert. Falls die Werte nicht übereinstimmen, beendet sich das Programm mit einem Fehler.


### 2) Parallelisierung mit OpenMP Tasks

Die Task-Variante verwendet dieselbe Rekurrenz, aber die drei rekursiven Teilaufrufe werden als OpenMP-Tasks gestartet:

```c
#pragma omp task shared(a) firstprivate(m, n, cutoff)
a = delannoy_task_cutoff(m - 1, n, cutoff);

#pragma omp task shared(b) firstprivate(m, n, cutoff)
b = delannoy_task_cutoff(m - 1, n - 1, cutoff);

#pragma omp task shared(c) firstprivate(m, n, cutoff)
c = delannoy_task_cutoff(m, n - 1, cutoff);

#pragma omp taskwait
return a + b + c;
```

Die Task-Berechnung wird in einer `parallel`-Region mit einer `single`-Region gestartet:

```c
#pragma omp parallel
{
    #pragma omp single
    result = delannoy_task_cutoff(n, n, cutoff);
}
```

Warum:

- `parallel` startet das Team von Threads
- `single` sorgt dafür, dass nur ein Thread die erste Aufgabe anstößt
- danach können die erzeugten Tasks von allen Threads gemeinsam bearbeitet werden


### 3) Warum gibt es einen Cutoff?

Die naive Rekurrenz erzeugt extrem viele rekursive Aufrufe. Wenn man aus **jedem** Aufruf wieder drei neue Tasks macht, entsteht sehr schnell eine riesige Anzahl sehr kleiner Tasks.

Genau das ist das Hauptproblem der Task-Variante.

Deshalb verwende ich einen kleinen Cutoff:

```text
if (m + n <= cutoff) {
    return delannoy_seq(m, n);
}
```

Das bedeutet:

- für große Teilprobleme werden noch Tasks erzeugt
- für kleine Teilprobleme wird wieder direkt sequenziell weitergerechnet

Wichtig:

- der **Algorithmus selbst bleibt gleich**
- es wird nur vermieden, dass für winzige Teilprobleme unnötig viel Task-Verwaltung entsteht

Das ist genau eine sinnvolle Antwort auf die Bottleneck-Frage:

- **Bottleneck**: sehr hoher Verwaltungsaufwand für sehr viele kleine Tasks
- **Verbesserung ohne Algorithmuswechsel**: Cutoff-Größe verwenden, damit kleine Teilprobleme nicht mehr als einzelne Tasks erzeugt werden


### 4) Erwartete Beobachtung beim Benchmark

Für kleine `N` ist die Task-Variante oft nicht besser als die sequenzielle Variante.

Der Grund ist:

- das eigentliche Teilproblem ist noch klein
- aber das Erzeugen, Einplanen und Synchronisieren der Tasks kostet trotzdem Zeit

Mit wachsendem `N` kann die Task-Variante interessanter werden, aber auch dann bleibt die naive Rekurrenz teuer, weil viele Teilprobleme mehrfach berechnet werden.

Deshalb erwarte ich typischerweise:

- bei kleinen `N` wenig oder keinen Speedup
- eventuell sogar langsamere Laufzeiten mit Tasks
- bei größeren `N` möglicherweise einen gewissen Vorteil mit `12` Threads
- insgesamt aber keine perfekte Skalierung


### 5) Benchmark auf LCC3

Das Jobscript liegt hier:

- [09/delannoy/job.sh](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/09/delannoy/job.sh)

Es macht automatisch folgende Schritte:

1. lädt bei Bedarf das GCC-Modul
2. kompiliert das Programm mit OpenMP
3. testet `N = 3` bis `15`
4. führt jede Konfiguration `5` mal aus
5. misst:
   `seq` mit `1` Thread sowie `task` mit `1` und `12` Threads
6. schreibt die Rohdaten nach `results/time_results.csv`
7. erzeugt daraus:
   - `results/summary_stats.csv`
   - `results/summary_table.md`

Ausführen auf LCC3:

```bash
cd 09/delannoy
sbatch job.sh
```

Nach dem Lauf:

```bash
cat results/summary_table.md
cat results/summary_stats.csv
```


### 6) Welche Werte gehören in die Comparison Spreadsheet?

Laut Aufgabenstellung sind für `N = 12` besonders diese Zeiten wichtig:

- sequenzielle Version
- parallele Version mit `1` Thread
- parallele Version mit `12` Threads

Dafür würde ich jeweils den Mittelwert `elapsed_mean` aus `results/summary_table.md` eintragen.

Warum:

- hier misst das Programm nur die eigentliche Delannoy-Berechnung
- damit ist die gemessene Wall-Clock-Time direkt die relevante Rechenzeit


### 7) Ergebnisvorlage zum Eintragen nach dem Clusterlauf

| Variante | Threads | N | Mean [s] |
| --- | ---: | ---: | ---: |
| seq | 1 | 12 | `<hier eintragen>` |
| task | 1 | 12 | `<hier eintragen>` |
| task | 12 | 12 | `<hier eintragen>` |


### 8) Schritt-für-Schritt-Erklärung in einfacher Sprache

#### Schritt 1: Rekurrenz verstehen

Eine Delannoy-Zahl zählt Wege durch ein Gitter.

Wenn ich bei `(m, n)` ankommen will, dann kann der letzte Schritt nur aus drei Richtungen gekommen sein:

- von links
- von unten
- von links unten diagonal

Darum setzt sich `D(m, n)` aus genau drei kleineren Teilproblemen zusammen.

#### Schritt 2: Naive rekursive Lösung

Die einfachste Idee ist:

- wenn ich am Rand bin, ist das Ergebnis `1`
- sonst berechne ich die drei kleineren Fälle rekursiv und addiere sie

Das ist leicht zu verstehen, aber ineffizient, weil dieselben Teilprobleme oft sehr oft neu berechnet werden.

#### Schritt 3: Tasks einsetzen

Die drei rekursiven Aufrufe sind zunächst unabhängige Arbeiten.

Deshalb kann man sie als Tasks formulieren:

- ein Task für `D(m - 1, n)`
- ein Task für `D(m - 1, n - 1)`
- ein Task für `D(m, n - 1)`

Danach muss mit `taskwait` gewartet werden, bis alle drei Ergebnisse fertig sind.

#### Schritt 4: Bottleneck verstehen

Das Problem ist nicht nur die Rechnung selbst, sondern auch die Organisation:

- ein Task muss erzeugt werden
- er muss geplant werden
- Threads müssen ihn übernehmen
- am Ende muss synchronisiert werden

Wenn Teilprobleme sehr klein sind, ist diese Verwaltung oft teurer als die eigentliche Berechnung.

#### Schritt 5: Verbesserung ohne neuen Algorithmus

Mit einem Cutoff kann man sagen:

- große Teilprobleme: parallel mit Tasks
- kleine Teilprobleme: direkt sequenziell

Dadurch bleibt der Grundalgorithmus gleich, aber der Verwaltungsaufwand sinkt deutlich.


### 9) Lokale Vorprüfung

Die echten Messungen sollen auf LCC3 laufen. Lokal kann man aber schon die Struktur prüfen.

Sinnvolle Testaufrufe:

```bash
cd 09/delannoy
make
OMP_NUM_THREADS=1 ./delannoy seq 12 8
OMP_NUM_THREADS=1 ./delannoy task 12 8
OMP_NUM_THREADS=4 OMP_PLACES=cores OMP_PROC_BIND=true ./delannoy task 12 8
```

Wenn `result` und `expected` übereinstimmen, ist die Berechnung korrekt.

