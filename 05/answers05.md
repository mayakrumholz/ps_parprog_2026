# Assignment 5

## Exercise 1

### 1) Was macht der gegebene Code auf abstrakter Ebene und was sollte passieren?

Der gegebene Code implementiert ein einfaches Kommunikationsmuster zwischen zwei Threads. Es handelt sich um ein Producer-Consumer- bzw. Message-Passing-Szenario.

Bedeutung der Variablen:

- `data`
  - enthält die eigentliche Nutzinformation
- `flag`
  - dient als Signalvariable
  - `flag == 0`: Daten sind noch nicht freigegeben
  - `flag == 1`: Daten wurden von Thread 0 bereitgestellt

Rolle der Threads:

- Thread 0:
  - schreibt `data = 42`
  - setzt anschließend `flag = 1`
- Thread 1:
  - wartet in einer Schleife darauf, dass `flag` den Wert `1` annimmt
  - liest danach `data`
  - gibt beide Werte aus

Abstrakter Ablauf:

1. Thread 0 produziert ein Ergebnis.
2. Thread 0 signalisiert mit `flag`, dass dieses Ergebnis bereit ist.
3. Thread 1 wartet auf dieses Signal.
4. Nach dem Signal verwendet Thread 1 die erzeugten Daten.

Erwartetes Verhalten:

- Das Programm sollte terminieren
- Thread 1 sollte die Warteschleife verlassen, sobald Thread 0 `flag = 1` gesetzt hat
- Danach sollte die Ausgabe lauten:

```text
flag=1 data=42
```

Einordnung:

- Die Rechenlogik ist sehr einfach
- Die eigentliche Schwierigkeit liegt im Speicher- und Synchronisationsmodell von OpenMP
- Entscheidend ist nicht, was berechnet wird, sondern ob ein Thread die Änderungen des anderen Threads korrekt und rechtzeitig sieht

### 2) Kompilierung mit `-O3`, häufige Ausführung und Beobachtungen

Mittels Jobskript [05/ex1/job.sh](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/05/ex1/job.sh). Es übernimmt drei zentrale Aufgaben:

- Kompilierung des Programms mit `-O3`
- wiederholte Ausführung des Programms in insgesamt `5000` Läufen
- Protokollierung aller erfolgreichen Läufe sowie aller Timeouts

Zusätzlich setzt das Skript pro Lauf ein Timeout von `2s`. Dadurch lässt sich sauber erkennen, ob das Programm korrekt terminiert oder in der Warteschleife hängen bleibt. Wichtig, weil das Fehlverhalten nur gelegentlich auftritt und deshalb durch viele Wiederholungen sichtbar gemacht werden muss.

Verwendete Ergebnisdateien:

- [05/ex1/results/ex1_report.txt](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/05/ex1/results/ex1_report.txt)
- [05/ex1/results/ex1_outputs.txt](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/05/ex1/results/ex1_outputs.txt)

Beobachtete Resultate:

| Kategorie | Anzahl |
| --- | ---: |
| erfolgreiche Läufe | 4996 |
| Timeouts | 4 |
| sonstige Fehler | 0 |

Beobachtungen:

- Alle erfolgreichen Läufe lieferten dieselbe Ausgabe:

```text
flag=1 data=42
```

- Es traten jedoch 4 Timeouts auf
- Damit gibt es Läufe, in denen das Programm nicht terminiert

Bewertung der Beobachtung:

- Der Code scheint in den meisten Fällen korrekt zu funktionieren
- Er ist aber nicht zuverlässig korrekt
- Gerade bei parallelen Programmen ist das entscheidend: "funktioniert meistens" ist kein Korrektheitsbeweis

#### Fachliche Bedeutung der Timeouts

Wenn ein Lauf in den Timeout geht, bleibt Thread 1 in der Warteschleife hängen:

```c
while (flag_val < 1) {
    flag_val = flag;
}
```

Das zeigt:

- Thread 1 beobachtet die Änderung von `flag` nicht zuverlässig
- Ohne geeignete Synchronisation ist nicht garantiert, dass der geänderte Wert rechtzeitig oder überhaupt sichtbar wird
- Optimierung mit `-O3` macht solche Probleme leichter sichtbar


### 3) Braucht der Code `#pragma omp flush`? Wenn ja, wo?

Ja. In dieser Programmstruktur wäre `#pragma omp flush` notwendig, damit die Kommunikation zwischen den Threads korrekt abgesichert ist.

#### Warum ist `flush` notwendig?

Ohne Synchronisation gibt es keine saubere Garantie für:

- Sichtbarkeit:
  - Wann sieht Thread 1 die von Thread 0 geschriebenen Werte?
- Reihenfolge:
  - Ist garantiert, dass `data = 42` bereits sichtbar ist, wenn `flag = 1` sichtbar wird?

Genau diese beiden Eigenschaften werden in diesem Beispiel benötigt:

- Thread 1 muss zuverlässig erkennen, dass `flag` gesetzt wurde
- Wenn Thread 1 `flag == 1` sieht, dann muss auch `data == 42` sichtbar sein

#### Wo ist `flush` notwendig?

Die Synchronisation muss an den logisch relevanten Stellen erfolgen:

1. nachdem Thread 0 `data` geschrieben hat
2. nachdem Thread 0 `flag` gesetzt hat
3. während Thread 1 wiederholt `flag` prüft
4. bevor Thread 1 `data` verwendet

Eine mögliche korrigierte Version ist:

```c
#include <omp.h>
#include <stdio.h>

int main(void) {
    int data = 0;
    int flag = 0;

    #pragma omp parallel num_threads(2) shared(data, flag)
    {
        if (omp_get_thread_num() == 0) {
            data = 42;
            #pragma omp flush(data)

            flag = 1;
            #pragma omp flush(flag)

        } else {
            int flag_val = 0;

            while (flag_val < 1) {
                #pragma omp flush(flag)
                flag_val = flag;
            }

            #pragma omp flush(data)
            printf("flag=%d data=%d\n", flag, data);
        }
    }

    return 0;
}
```

#### Begründung der einzelnen Stellen

- `#pragma omp flush(data)` nach `data = 42;`
  - die geschriebenen Daten werden veröffentlicht
- `#pragma omp flush(flag)` nach `flag = 1;`
  - das Bereitschaftssignal wird veröffentlicht
- `#pragma omp flush(flag)` in der Schleife
  - Thread 1 synchronisiert die Sicht auf `flag` immer wieder neu
- `#pragma omp flush(data)` nach der Schleife
  - vor dem Lesen von `data` wird die Sicht auf die Nutzdaten aktualisiert

#### Warum reicht es nicht, nur an `flag` zu denken?

Das Kommunikationsmuster besteht aus zwei Teilen:

- `flag` sagt, dass etwas bereit ist
- `data` ist der eigentliche Inhalt

Deshalb muss die Lösung beides absichern:

- Sichtbarkeit des Signals
- Sichtbarkeit der zugehörigen Daten

Ablauf ist also:

1. Daten schreiben
2. Daten veröffentlichen
3. Signal setzen
4. Signal veröffentlichen
5. Signal zuverlässig beobachten
6. Daten sichtbar machen
7. Daten verwenden

### 4) Optionale Frage: Braucht der Code `#pragma omp atomic`?

Nicht zwingend.

Begründung:

- `data` wird nur von Thread 0 geschrieben und danach von Thread 1 gelesen
- `flag` wird von Thread 0 geschrieben und von Thread 1 abgefragt
- Das Kernproblem ist hier nicht ein konkurrierendes Update mehrerer Threads auf dieselbe Variable
- Das Kernproblem ist die korrekte Sichtbarkeit und Reihenfolge der Kommunikation zwischen zwei Threads

Deshalb gilt:

- `flush` ist für diese Aufgabenstellung das passende Konzept
- `atomic` ist hier nicht notwendig, wenn die Kommunikation bereits korrekt über `flush` abgesichert wird
- Für `data` braucht man in dieser Struktur kein `atomic`
- Für `flag` könnte man theoretisch alternative Formulierungen diskutieren, weil `flag` genau die Variable ist, über die der wartende Thread ständig mit dem schreibenden Thread kommuniziert. Man könnte daher überlegen, den Zugriff auf `flag` statt über `flush` über andere Synchronisationsmechanismen auszudrücken
## Exercise 2

### 1) Aufgabenstellung

In dieser Aufgabe müssen die einzelnen Codebeispiele darauf untersucht werden,

- ob sie korrekt parallelisiert sind,
- welche Probleme auftreten,
- wie eine korrekte Lösung aussieht,
- und ob es mehrere sinnvolle Lösungswege gibt

Dabei auf folgende Dinge achten:

- Gibt es Datenabhängigkeiten zwischen Iterationen?
- Sind Variablen korrekt als `shared`, `private`, `firstprivate` oder per `reduction` behandelt?
- Ist eine Synchronisation oder Barriere notwendig?
- Schreiben mehrere Threads gleichzeitig in dieselbe Variable?


### 2) Beispiel 1

Gegeben:

```c
a[0] = 0;
#pragma omp parallel for
for (i=1; i<N; i++) {
    a[i] = 2.0*i*(i-1);
    b[i] = a[i] - a[i-1];
}
```

#### Analyse

Dieses Beispiel ist in der gegebenen Form **nicht korrekt parallelisiert**.

Grund:

- Jede Iteration berechnet zunächst `a[i]`
- Danach wird `b[i]` mit `a[i] - a[i-1]` berechnet
- Der Zugriff auf `a[i-1]` erzeugt eine Abhängigkeit zur vorherigen Iteration

Problem:

- Bei `#pragma omp parallel for` können verschiedene Iterationen von verschiedenen Threads ausgeführt werden
- Dann ist nicht garantiert, dass `a[i-1]` bereits berechnet wurde, wenn Iteration `i` `b[i]` auswertet

Damit liegt eine echte Schleifenabhängigkeit vor.

#### Korrekte Lösung

Die allgemeine und saubere Lösung ist, die Berechnung in zwei Schleifen aufzuteilen:

```c
a[0] = 0;

#pragma omp parallel for
for (i = 1; i < N; i++) {
    a[i] = 2.0 * i * (i - 1);
}

#pragma omp parallel for
for (i = 1; i < N; i++) {
    b[i] = a[i] - a[i - 1];
}
```

Warum ist das korrekt?

- Die erste Schleife berechnet alle Werte von `a`
- Am Ende der ersten `parallel for`-Schleife gibt es eine implizite Barriere
- Erst danach startet die zweite Schleife
- Zu diesem Zeitpunkt sind alle benötigten Werte vorhanden

#### Alternative Lösung

Hier kann man `b[i]` auch direkt ausrechnen:

```c
a[0] = 0;
#pragma omp parallel for
for (i = 1; i < N; i++) {
    a[i] = 2.0 * i * (i - 1);
    b[i] = 4.0 * i - 2.0;
}
```

Denn:

```text
a[i]     = 2i(i-1)
a[i-1]   = 2(i-1)(i-2)
b[i]     = a[i] - a[i-1] = 4i - 2
```

#### Vor- und Nachteile

- Zwei Schleifen:
  - allgemein und robust
  - direkt aus der Datenabhängigkeit begründet
- direkte Formel:
  - effizienter
  - aber nur möglich, wenn eine passende Umformung bekannt ist

### 3) Beispiel 2

Gegeben:

```c
a[0] = 0;
#pragma omp parallel
{
    #pragma omp for nowait
    for (i=1; i<N; i++) {
        a[i] = 3.0*i*(i+1);
    }
    #pragma omp for
    for (i=1; i<N; i++) {
        b[i] = a[i] - a[i-1];
    }
}
```

#### Analyse

Dieses Beispiel ist **nicht korrekt**, weil `nowait` an der falschen Stelle steht.

Problem:

- Die erste Schleife berechnet `a[i]`
- Die zweite Schleife benutzt `a[i]` und `a[i-1]`
- Durch `nowait` entfällt die implizite Barriere am Ende der ersten `omp for`-Schleife
- Dadurch kann ein Thread schon mit der zweiten Schleife anfangen, obwohl andere Threads noch an der ersten Schleife arbeiten

Folge:

- Die zweite Schleife kann auf noch nicht berechnete Werte von `a` zugreifen

#### Korrekte Lösung

Die einfachste Korrektur ist, `nowait` zu entfernen:

```c
a[0] = 0;
#pragma omp parallel
{
    #pragma omp for
    for (i = 1; i < N; i++) {
        a[i] = 3.0 * i * (i + 1);
    }

    #pragma omp for
    for (i = 1; i < N; i++) {
        b[i] = a[i] - a[i - 1];
    }
}
```

Warum ist das korrekt?

- Zwischen den beiden Schleifen gibt es nun wieder eine implizite Barriere
- Erst wenn alle `a[i]` berechnet wurden, beginnt die Berechnung von `b[i]`

#### Alternative Lösung

Auch hier kann man `b[i]` direkt umformen:

```c
a[0] = 0;
#pragma omp parallel for
for (i = 1; i < N; i++) {
    a[i] = 3.0 * i * (i + 1);
    b[i] = 6.0 * i;
}
```

Denn:

```text
a[i]     = 3i(i+1)
a[i-1]   = 3(i-1)i
b[i]     = a[i] - a[i-1] = 6i
```

#### Vor- und Nachteile

- `nowait` entfernen:
  - minimale Änderung
  - allgemein gültig
- direkte Formel:
  - weniger Synchronisationsaufwand
  - aber stärker an die konkrete Mathematik des Beispiels gebunden

### 4) Beispiel 3

Gegeben:

```c
#pragma omp parallel for default(none)
for (i=0; i<N; i++) {
    x = sqrt(b[i]) - 1;
    a[i] = x*x + 2*x + 1;
}
```

#### Analyse

Dieses Beispiel ist in der vorliegenden Form **nicht korrekt bzw. nicht vollständig**, weil bei `default(none)` alle Variablen explizit angegeben werden müssen.

Es fehlen insbesondere Angaben für:

- `a`
- `b`
- `N`
- `x`

Zusätzlich ist `x` kritisch:

- `x` wird in jeder Iteration neu beschrieben
- Wenn `x` gemeinsam wäre, würden mehrere Threads gleichzeitig auf dieselbe Variable schreiben
- `x` muss daher privat sein

#### Korrekte Lösung

```c
#pragma omp parallel for default(none) shared(a, b, N) private(i, x)
for (i = 0; i < N; i++) {
    x = sqrt(b[i]) - 1;
    a[i] = x * x + 2 * x + 1;
}
```

Warum ist das korrekt?

- `a`, `b` und `N` werden von allen Threads gemeinsam benutzt und sind daher `shared`
- `x` ist ein temporärer Hilfswert und muss privat sein
- Jede Iteration schreibt nur in `a[i]`, also in einen eigenen Speicherbereich

#### Alternative Lösung

Der Ausdruck kann vereinfacht werden:

```text
(sqrt(b[i]) - 1)^2 + 2(sqrt(b[i]) - 1) + 1 = b[i]
```

Damit wäre auch diese Lösung möglich:

```c
#pragma omp parallel for default(none) shared(a, b, N) private(i)
for (i = 0; i < N; i++) {
    a[i] = b[i];
}
```

#### Vor- und Nachteile

- explizite Scope-Korrektur:
  - bleibt nah am Original
  - zeigt den eigentlichen Schwerpunkt der Aufgabe
- algebraische Vereinfachung:
  - effizienter
  - aber fachlich nicht nötig, wenn es hier um Data Sharing geht

### 5) Beispiel 4

Gegeben:

```c
f = 2;
#pragma omp parallel for private(f,x)
for (i=0; i<N; i++) {
    x = f * b[i];
    a[i] = x - 7;
}
a[0] = x; 
```

#### Analyse

Dieses Beispiel ist **nicht korrekt**.

Es gibt zwei getrennte Probleme.

#### Problem 1: `f` ist falsch behandelt

Vor der Schleife wird `f = 2` gesetzt. Danach wird `f` aber als `private(f)` deklariert.

Bedeutung von `private(f)`:

- Jeder Thread bekommt eine eigene lokale Instanz von `f`
- Diese Instanz übernimmt den alten Wert nicht automatisch
- `f` ist innerhalb der Schleife damit uninitialisiert

Folge:

- `x = f * b[i]` verwendet einen undefinierten Wert

#### Problem 2: `a[0] = x;`

Nach der Schleife wird `x` noch einmal benutzt:

```c
a[0] = x;
```

Das ist problematisch, weil:

- `x` als `private(x)` threadlokal ist,
- nach dem parallelen Bereich kein sinnvoll definierter gemeinsamer Wert von `x` existiert

#### Korrekte Lösung

```c
f = 2;
#pragma omp parallel for firstprivate(f) private(x)
for (i = 0; i < N; i++) {
    x = f * b[i];
    a[i] = x - 7;
}
```

Die Zeile

```c
a[0] = x;
```

muss entfernt oder neu definiert werden.

Warum ist das korrekt?

- `firstprivate(f)` sorgt dafür, dass jeder Thread mit dem Wert `f = 2` startet
- `x` bleibt privat, was für eine temporäre Hilfsvariable richtig ist
- Jede Iteration schreibt nur nach `a[i]`

#### Anmerkung zu `a[0] = x;`

Diese Zeile ist in der gegebenen Form nicht sinnvoll.

Wenn man sie behalten wollte, müsste man zuerst präzise definieren:

- Welcher Wert von `x` überhaupt gemeint ist
- Warum genau dieser Wert nach der Parallelregion gespeichert werden soll

Ohne diese Definition ist die saubere Lösung:

- `f` zu `firstprivate` ändern
- `x` privat lassen
- die letzte Zeile entfernen

### 6) Beispiel 5

Gegeben:

```c
sum = 0; 
#pragma omp parallel for
for (i=0; i<N; i++) {
    sum = sum + b[i];
}
```

#### Analyse

Dieses Beispiel ist **nicht korrekt parallelisiert**, weil eine Race Condition auf `sum` vorliegt.

Problem:

- Alle Threads lesen und schreiben dieselbe Variable `sum`
- Die Operation

```c
sum = sum + b[i];
```

ist nicht atomar.

Folge:

- Updates können verloren gehen
- Das Ergebnis ist vom zeitlichen Ablauf abhängig

#### Korrekte Lösung

Die passende OpenMP-Lösung ist eine Reduction:

```c
sum = 0;
#pragma omp parallel for reduction(+:sum)
for (i = 0; i < N; i++) {
    sum = sum + b[i];
}
```

Warum ist das korrekt?

- Jeder Thread berechnet zunächst eine lokale Teilsumme
- Am Ende werden alle Teilsummen korrekt zusammengeführt

#### Alternative Lösung

Eine alternative, aber meist schlechtere Lösung ist `atomic`:

```c
sum = 0;
#pragma omp parallel for
for (i = 0; i < N; i++) {
    #pragma omp atomic
    sum += b[i];
}
```

#### Vor- und Nachteile

- `reduction(+:sum)`:
  - idiomatische OpenMP-Lösung
  - meist effizienter
  - fachlich die sauberste Wahl
- `atomic`:
  - korrekt
  - aber stärker synchronisiert
  - bei vielen Iterationen oft langsamer

### 7) Beispiel 6

Gegeben:

```c
#pragma omp parallel
#pragma omp for
for (i=0; i<N; i++) {
    #pragma omp for
    for (j=0; j<N; j++) {
        a[i][j] = b[i][j];
    }
}
```

#### Analyse

Dieses Beispiel ist **falsch**.

Grund:

- `omp for` ist ein Worksharing-Konstrukt
- Ein solches Konstrukt muss von allen Threads des Teams gemeinsam und in derselben Programmstruktur erreicht werden
- Das innere `#pragma omp for` steht hier innerhalb der äußeren Schleife und ist deshalb kein gültiges Muster

#### Korrekte Lösung 1

Nur die äußere Schleife wird parallelisiert:

```c
#pragma omp parallel for
for (i = 0; i < N; i++) {
    for (j = 0; j < N; j++) {
        a[i][j] = b[i][j];
    }
}
```

Warum ist das korrekt?

- Jede Iteration der äußeren Schleife bearbeitet genau eine Zeile
- Unterschiedliche Threads schreiben in unterschiedliche Bereiche von `a`
- Es gibt keine Datenkonflikte

#### Korrekte Lösung 2

Man kann auch beide Schleifen mit `collapse(2)` zusammenfassen:

```c
#pragma omp parallel for collapse(2)
for (i = 0; i < N; i++) {
    for (j = 0; j < N; j++) {
        a[i][j] = b[i][j];
    }
}
```

#### Vor- und Nachteile

- nur äußere Schleife parallelisieren:
  - einfach
  - meist gute Lokalität
  - oft die natürlichste Lösung
- `collapse(2)`:
  - mehr Parallelismus bei kleinen Schleifengrenzen
  - feinere Aufteilung
  - kann aber unnötig komplexer sein
