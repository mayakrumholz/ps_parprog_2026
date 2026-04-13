# Assignment 4

## Exercise 1
1) Implement a parallelized version of the mandelbrot calculation using `Posix Threads`

Was gleich bleiben konnte:
- Für jedes Pixel (px, py) werden cx und cy auf den Mandelbrot-Bereich abgebildet
- Die while Schleife läuft durch bis der Punkt divergiert oderr MAX_ITER erreicht ist
- Die Iterationszahl wird auf einen Grauwert von 0..255 abgebildet

Was ich erweitert habe:
1. pthread.h wurde eingebunden
2. Eine worker_args_t-Struktur enthält image, start_row und end_row (einfacher um es dem Thread als einem Argument zu übergeben)
3. Die Berechnung habe ich in eine Thread-Funktion verschoben  
    - Früher `calc_mandelbrot(image)`: eine Funktion berechnet das ganze Bild
    - Jetzt `calc_rows(void *arg)`: Jeder Thread berechnet nur einen Teil des Bildes (seine Zeilen start_row bis end_row)
    = Die äußere Schleife über py wird aufgeteilt
4. Die Arbeit wird zeilenweise auf Threads verteilt
    - `start_row = (t * Y) / thread_count`
    - `end_row = ((t + 1) * Y) / thread_count``
    -> Dadurch werden die Y Bildzeilen möglichst gleichmäßig verteilt
    -> Jeder Thread schreibt in einem eigenen Bereich des Arrays - vermeidet Datenkonflikte beim Schreiben
5. Thread-Anzahl als Programmargument eingelesen und durch parse_thread_count(...) geprüft
6. Dynamische Arrays für Threads und deren Argumente (`pthread_t *threads` und `worker_args_t *args`)
7. Threads werden gestartet und wieder eingesammelt
    - pthread_create startet parallele Ausführung
    - pthread_join stellt sicher, dass das Hauptprogramm erst weitermacht, wenn alle Threads fertig sind