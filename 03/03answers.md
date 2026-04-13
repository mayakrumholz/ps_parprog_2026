# Exercise 1
## Laufzeit auf LCC3
| Run | real  | user  | sys  |
|-----|-------|-------|------|
| 1   | 17.68 | 17.63 | 0.00 |
| 2   | 17.67 | 17.63 | 0.00 |
| 3   | 17.72 | 17.67 | 0.00 |
| 4   | 17.68 | 17.63 | 0.00 |
| 5   | 17.73 | 17.68 | 0.00 |

## Mögliche Verbesserungen
- Parallelisierung über die äußere Schleife der Bildzeilen -> jedes Pixel ist unabhängig (gut für OpenMP)
- Berechnung der Pixelkoordinaten cx und cy verbessern (statt pro Pixel die komplette Formel neu auszuwerten, könnte man Schrittweiten vorab berechnen)
- Eventuell kleinere Optimierungen in der arithmetischen Berechnung
- Compiler Flags
- Bildgröße oder `MAX_ITER` anpasssen

## Algorithmus parallelisieren
Mögliche Lösung: Nicht ein Thread berechnet das ganze Bild allein, sondern mehrere Threads teilen sich die for-Schleife über `py`, also über die Zeilen des Bildes.
- Zeilen sind unabhängig voneinander
- Ein Pixel (px, py) braucht nur seine eigenen lokalen Variablen x, y, cx, cy, iterationen
- Threads würden in unterrschiedliche Bereiche des Arrays `image` schrreiben

```
#pragma omp parallel for schedule(dynamic)
for (int py = 0; py < Y; py++) {
    for (int px = 0; px < X; px++) {
      ...
      image[py][px] = ...;
    }
}
```

Vor allem `schedule(dynamic)`wäre sinnvoll, weil:
- nicht jeder Pixel gleich viele Iterationen braucht
- Punkte nahe am Mandelbrot-Set sind teurer als Punkte außerhalb

# Exercise 2
## 1. Gemeinsamkeiten/Unterschiede der Programme
### Gemeinsamkeiten:
- Sie starten einen OpenMP-Parallelbereich
- Jeder Thread holt sich seine Thread-ID `tid`
- Jeder Thread inkrementiert in einer Schleife sehr oft seinen Zähler
- Am Ende werden alle Teilzähler aufsummiert und ausgegeben
Inhaltlich wollen sie also dasselbe: Jeder Thread zählt lokal hooch und am Ende werden alle Beiträge addiert

### Unterschiede:
Entscheidende Unterschied liegt nicht in Logik, sondern im Speicherlayout
- Größe und Zugriff auf das Array:
    - In false_sharing.c steht: `int* volatile sum (int*)calloc(MAX_NUM_THREADS, sizeof(int));` und später `sum[tid]++;``
        - Es gibt ein Array mit `MAX_NUM_THREADS` Einträgen
        - Thread 0 schreibt auf sum[0], Thread 1 auf sum[1]...
        - Die Werte liegen direkt nebeneinander im Speicher
    - In false_sharing_2.c steht: 
        ````
        #define FACTOR 16
        int* volatile sum = (int*)calloc(MAX_NUM_THREADS * FACTOR, sizeof(int));
        ````
        und später: `sum[tid * FACTOR]++;`
        - Das Array ist künstlich größer gemacht
        - Thread 0 schreibt auf sum[0]
        - Thread 1 schreibt auf sum[16]
        - Thread 2 schreibt auf sum[32] ...
        - Thread zähler liegen niccht direkt nebeneinander, sondern mit Abstand

CPUs arbeiten nicht mit einzelnen int-Werten direkt aus dem RAM, sondern holen Daten in Cache-Lines. Eine Cache-Line ist typischerweise 64 Byte groß, ein int 4 Byte, bedeutet in eine Cache-Line passen ungefähr 16 ints

**Was passiert in false_sharing.c?** \
Wenn mehrere Threads gleichzeitig auf sum[0], sum[1], sum[2], ... schreiben, dann liegen diese Einträge (sum[0] bis sum[15]) sehr wahrscheinlich alle in derselben Cache-Line 
Obwohl die Threads logisch verschiedene Variablen ändern, liegen diese Physisch in derselben Cache-Line -> für die Hardware sieht das wie ein Konflikt aus:
- Wenn ein Thread auf die Cache-Line schreibt, braucht er sie exklusiv in seinem Cache
- Andere Caches müssen ihre Kopie dieser Linie verwerfen oder aktualisieren
- Die Cache-Linie "wandert" ständig zwischen den Kernen hin und her = false sharing

**Was passiert in false_sharing_2.c?** \
Hier werden die Zähler künstlich auseinander gezogen.
Wenn int = 4 Byte und FACTOR = 16, dann ist der Abstand:
16 * 4 Byte = 64 Byte
Damit landet jeder Thread-Zähler in einer eignen Cache-Line und es gibt viel weniger Cache-Kohärenzverkehr zwischen den Kernen. Sorgt für:
- weniger Invalidierungen
- weniger Warten
- meist deutlich bessere Laufzeit

-> mathematisch gleich, Hardwarekosten sind sehr unterschiedlich

**Warum wurde volatile verwendet?** \
Das volatile bei `int* volatile sum` soll verhindern, dass der Compiler die Schleife zu aggressiv optimiert und z.B. Inkremente komplett wegoptimiert/lokal im Register hält

## 2. Codes auf LCC3
1. module load gcc/12.2.0-gcc-8.5.0-p4pe45v
2. srun --pty bash
3. make
4. Mit 6 threads auf einem Sockel testen: sbatch job_same_socket.sh
    ````
    false_sharing on the same socket:
    Total sum: 600000000
    Time taken: 0.393938 seconds
    false_sharing_2 on the same socket
    Total sum: 600000000
    Time taken: 0.207897 seconds
    ````
5. Mit 6 threads auf cores von unterschiedlichen processors
    ```
    Total sum: 600000000
    Time taken: 0.461722 seconds
    false_sharing_2 on different core
    Total sum: 600000000
    Time taken: 0.232286 seconds
    ```

Zeigt folgendes:
- false_sharing.c ist deutlich langsamer als false_sharing_2.c
- auf demselben Sockel: 0.393938 s vs. 0.207897 s
- über verschiedene Prozessoren: 0.461722 s vs. 0.232286 s
- die gepaddete Version ist jeweils ungefähr fast doppelt so schnell
- die Verteilung über verschiedene Prozessoren macht beide Varianten etwas langsamer

-> Die Verteilung über verschiedene Prozessoren verschlechtert die Laufzeit zusätzlich, weil die betroffene Cache-Line dann nicht nur zwischen Kernen, sondern auch zwischen Sockeln übertragen werden muss

### perf stat false_sharing_:
```
Total sum: 600000000
Time taken: 0.393145 seconds

 Performance counter stats for './false_sharing 100000000':

          2,235.39 msec task-clock:u              #    5.476 CPUs utilized          
                 0      context-switches:u        #    0.000 /sec                   
                 0      cpu-migrations:u          #    0.000 /sec                   
                81      page-faults:u             #   36.235 /sec                   
     6,488,130,818      cycles:u                  #    2.902 GHz                      (83.45%)
     5,305,642,593      stalled-cycles-frontend:u #   81.77% frontend cycles idle     (83.47%)
     1,425,452,651      stalled-cycles-backend:u  #   21.97% backend cycles idle      (66.57%)
     2,412,872,739      instructions:u            #    0.37  insn per cycle         
                                                  #    2.20  stalled cycles per insn  (83.27%)
       603,620,783      branches:u                #  270.029 M/sec                    (83.27%)
             6,633      branch-misses:u           #    0.00% of all branches          (83.33%)

       0.408191445 seconds time elapsed

       2.214107000 seconds user
       0.001990000 seconds sys
```
### perf stat false_sharing_2:
```
Total sum: 600000000
Time taken: 0.207748 seconds

 Performance counter stats for './false_sharing_2 100000000':

          1,250.21 msec task-clock:u              #    5.842 CPUs utilized          
                 0      context-switches:u        #    0.000 /sec                   
                 0      cpu-migrations:u          #    0.000 /sec                   
                80      page-faults:u             #   63.989 /sec                   
     3,630,128,744      cycles:u                  #    2.904 GHz                      (83.23%)
     2,438,043,942      stalled-cycles-frontend:u #   67.16% frontend cycles idle     (83.21%)
       658,128,420      stalled-cycles-backend:u  #   18.13% backend cycles idle      (66.43%)
     2,413,501,977      instructions:u            #    0.66  insn per cycle         
                                                  #    1.01  stalled cycles per insn  (83.22%)
       602,788,642      branches:u                #  482.149 M/sec                    (83.59%)
             7,630      branch-misses:u           #    0.00% of all branches          (83.66%)

       0.214010625 seconds time elapsed

       1.236878000 seconds user
       0.002964000 seconds sys
```
### cache events false_sharing:
```
Total sum: 600000000
Time taken: 0.390327 seconds

 Performance counter stats for './false_sharing 100000000':

        10,265,854      cache-references:u                                          
         5,898,156      cache-misses:u            #   57.454 % of all cache refs    

       0.394685303 seconds time elapsed

       2.213607000 seconds user
       0.000995000 seconds sys
```
### cache events false_sharing_2:
```
Total sum: 600000000
Time taken: 0.205792 seconds

 Performance counter stats for './false_sharing_2 100000000':

            11,834      cache-references:u                                          
               573      cache-misses:u            #    4.842 % of all cache refs    

       0.210023872 seconds time elapsed

       1.235847000 seconds user
       0.000000000 seconds sys
````

### Interpretation von perf stat
- cycles: 6.49e9 vs. 3.61e9
    - Die langsamere Version braucht viel mehr CPU-Zyklen
- instructions: fast gleich (2.409e9 vs. 2.396e9)
    - Beide Programme führen fast dieselbe Anzahl an Instruktionen aus
    - Der Unterschied ist auch hiernach wieder nicht die Rechenlogik, sondern das Warten auf Speicher/Kohärenz
- IPC: 0.37 vs. 0.66
    - Die CPU arbeitet bei false_sharing.c deutlich effizienter
- task-clock und CPUs utilized sind ähnlich
    - Bedeutet keine große Differenz bei der Thread-Nutzung, sondern beim Speicherverwalten
Schlussfolgerung bestärkt bisheriges: gleiche Arbeit + ähnliche Thread-Auslastung + ähnliche Instruktionszahl, aber viel schlechtere Laufzeit => Speicher-/Cacheproblem

### Interpretation der Cache-Events
- cache-misses: 5,897,671 vs. 605
- Miss-Rate: 57.6% vs. 5.9%
- L1-dcache-load-misses: 10,895,950 vs. 10,724
- L1-dcache-store-misses: 4,257,142 vs. 997
Deutlicher Beleg:
Vor allem Store-Misses -> viele Threads schreiben ständig in dieselbe Cache Line-Gruppe, dadurch wird die Linie dauernd in anderen Caches invalidiert. Beim nächsten Schreiben muss sie erneut geholt werden, genau das produziert die hohen Miss-Zahlen