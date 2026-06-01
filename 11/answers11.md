# Assignment 11

## Exercise 1

### 1) Überblick

Bei Strength Reduction wird eine teure Operation durch günstigere Operationen
ersetzt. Typische Beispiele sind:

- Multiplikation mit einer Zweierpotenz durch Bit-Shifts
- Division eines `unsigned`-Werts durch eine Zweierpotenz durch einen
  Rechts-Shift
- wiederholt neu berechnete Array-Indizes durch einen fortlaufenden Zeiger
- eine Division in einer Schleife durch eine additive Induktionsvariable

Für den Assembly-Vergleich wurde eine Compiler-Explorer-Quelldatei vorbereitet:

- [11/ex1/compiler_explorer.c](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/11/ex1/compiler_explorer.c)
- [11/ex1/report/gcc_12_2_O3_assembly.txt](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/11/ex1/report/gcc_12_2_O3_assembly.txt)

In Compiler Explorer wird die Datei mit `x86-64 gcc` und der Compiler-Option
`-O3` übersetzt. Jede Teilaufgabe enthält eine `original_*`- und eine
`transformed_*`-Funktion, sodass die erzeugten Instruktionen direkt
gegenübergestellt werden können.

### 2) Transformationen

#### a) Multiplikation mit 32

Original:

```c
unsigned c2 = 32 * c1;
```

Transformation:

```c
unsigned c2 = c1 << 5;
```

Begründung:

```text
32 = 2^5
```

Ein Links-Shift um fünf Stellen multipliziert einen `unsigned`-Wert mit `32`.
Die Transformation ist sinnvoll, wenn ein Shift günstiger als eine
Multiplikation ist. Bei `unsigned` bleibt auch das Verhalten bei einem
Überlauf gleich: Das Ergebnis wird modulo `2^w` berechnet, wobei `w` die
Bitbreite des Typs ist.

#### b) Multiplikation mit 15

Original:

```c
unsigned c2 = 15 * c1;
```

Transformation:

```c
unsigned c2 = (c1 << 4) - c1;
```

Begründung:

```text
15 * c1 = (16 - 1) * c1 = (c1 << 4) - c1
```

Die Transformation ist sinnvoll, wenn Shift und Subtraktion zusammen
günstiger als die Multiplikation sind. Auch hier ist die Transformation für
`unsigned` einschließlich Wraparound semantisch äquivalent.

#### c) Multiplikation mit 96

Original:

```c
unsigned c2 = 96 * c1;
```

Transformation:

```c
unsigned c2 = (c1 + (c1 << 1)) << 5;
```

Begründung:

```text
96 * c1 = 3 * 32 * c1 = (c1 + 2 * c1) << 5
```

Die Multiplikation wird durch zwei Shifts und eine Addition ersetzt. Das ist
sinnvoll, wenn diese Instruktionsfolge günstiger als die Multiplikation ist.
Auf x86 kann der Compiler `c1 + 2 * c1` gegebenenfalls zusätzlich mit einer
`lea`-Instruktion berechnen.

#### d) Multiplikation mit 0.125

Original:

```c
unsigned c2 = 0.125 * c1;
```

Transformation:

```c
unsigned c2 = c1 >> 3;
```

Begründung:

```text
0.125 = 1 / 8 = 1 / 2^3
```

Da `c1` und `c2` vom Typ `unsigned` sind, wird das Ergebnis beim Zuweisen
abgeschnitten. Ein Rechts-Shift um drei Stellen berechnet ebenfalls die
ganzzahlige Division durch `8`. Die Transformation vermeidet die
Gleitkommaumwandlung, Gleitkommamultiplikation und Rückumwandlung.

Sie ist geeignet, wenn tatsächlich die ganzzahlige, abgerundete Division
gewünscht ist. Für negative Werte wäre diese Argumentation nicht ohne
Weiteres übertragbar, geht nur wegen `unsigned`.

#### e) Jedes fünfte Array-Element summieren

Original:

```c
unsigned sum_fifth = 0;

for (int i = 0; i < N / 5; ++i) {
    sum_fifth += a[5 * i];
}
```

Transformation:

```c
unsigned sum_fifth = 0;
const unsigned *current = a;

for (int i = 0; i < N / 5; ++i) {
    sum_fifth += *current;
    current += 5;
}
```

Der Index `5 * i` wird nicht in jeder Iteration neu berechnet. Stattdessen
wird ein Zeiger nach jedem Zugriff direkt um fünf Elemente weitergeschoben.
Die Transformation ist sinnvoll, wenn das Aktualisieren des Zeigers günstiger
als die wiederholte Indexberechnung ist. Moderne Compiler erkennen solche
Induktionsvariablen häufig selbst.

#### f) Division innerhalb einer Schleife

Original:

```c
for (int i = 0; i < N; ++i) {
    a[i] += i / 5.3;
}
```

Transformation:

```c
double quotient = 0.0;
const double step = 1.0 / 5.3;

for (int i = 0; i < N; ++i) {
    a[i] += quotient;
    quotient += step;
}
```

Die teure Division wird nur einmal für `step` ausgeführt. Danach wird der
Quotient pro Schleifendurchlauf additiv aktualisiert.

Diese Transformation darf nur angewendet werden, wenn kleine
Gleitkommaabweichungen akzeptabel sind. Aufgrund von Rundungsfehlern ist eine
wiederholte Addition nicht bitgenau identisch zur einzelnen Berechnung von
`i / 5.3`. Außerdem erzeugt die additive Induktionsvariable eine Abhängigkeit
zwischen Schleifeniterationen. Dadurch kann sie Vektorisierung erschweren und
trotz eingesparter Division auf einer konkreten Architektur langsamer sein.

#### g) Multiplikation eines `float`-Werts mit -1

Original:

```c
float c2 = -1 * c1;
```

Einfache Transformation in C:

```c
float c2 = -c1;
```

Explizite Umsetzung über die IEEE-754-Repräsentation:

```c
uint32_t bits;

memcpy(&bits, &c1, sizeof(bits));
bits ^= UINT32_C(0x80000000);
memcpy(&c2, &bits, sizeof(c2));
```

Bei einer IEEE-754-Zahl mit einfacher Genauigkeit liegt das Vorzeichen im
höchsten Bit. Durch XOR mit `0x80000000` wird nur dieses Vorzeichenbit
umgeschaltet. Eine Gleitkommamultiplikation ist nicht notwendig.

Die explizite Bit-Transformation setzt voraus, dass `float` tatsächlich im
IEEE-754-Binary32-Format gespeichert wird und `uint32_t` verfügbar ist.
`memcpy` wird verwendet, um Verletzungen der C-Aliasing-Regeln zu vermeiden.
Zusätzlich dürfen Sonderfälle wie signaling NaNs und beobachtbare
Floating-Point-Exceptions für die Anwendung keine Rolle spielen. Im normalen
C-Code ist `-c1` klarer; der Compiler kann daraus selbst eine passende
Instruktion erzeugen.

### 3) Assembly-Vergleich mit `gcc -O3`

Die Compiler-Explorer-Quelldatei wurde mit `x86-64 gcc 12.2` und `-O3`
übersetzt. Die wichtigsten erzeugten Instruktionen sind:

| Teil | Original | Transformation | Beobachtung |
| --- | --- | --- | --- |
| a | `sal eax, 5` | `sal eax, 5` | GCC ersetzt die Multiplikation mit `32` bereits selbst durch einen Links-Shift. Beide Funktionen sind identisch. |
| b | `sal eax, 4` und `sub eax, edi` | `sal eax, 4` und `sub eax, edi` | GCC setzt auch beim Original selbst `15 * c1 = 16 * c1 - c1` um. Beide Funktionen sind identisch. |
| c | `lea eax, [rdi+rdi*2]` und `sal eax, 5` | `lea eax, [rdi+rdi*2]` und `sal eax, 5` | GCC berechnet zuerst `3 * c1` mit `lea` und multipliziert das Ergebnis anschließend per Shift mit `32`. Beide Funktionen sind identisch. |
| d | `cvtsi2sd`, `mulsd` und `cvttsd2si` | `shr eax, 3` | Das Original konvertiert den Integer zu `double`, multipliziert und konvertiert zurück. Die manuelle Transformation ist deutlich einfacher. |
| e | `add edx, DWORD PTR [rdi]` und `add rdi, 20` | `add edx, DWORD PTR [rdi]` und `add rdi, 20` | GCC erkennt die Induktionsvariable selbst. Beide Schleifen verwenden einen Zeiger, der pro Iteration um `20` Bytes beziehungsweise fünf `unsigned`-Elemente erhöht wird. |
| f | vektorisierte Schleife mit `divpd` sowie Restbehandlung mit `divsd` | skalare Schleife mit `addsd xmm0, xmm2` | GCC vektorisiert das Original und berechnet mehrere Divisionen parallel. Die Transformation ersetzt Divisionen durch Additionen, erzeugt aber eine Schleifenabhängigkeit und bleibt deshalb skalar. |
| g | `xorps xmm0, XMMWORD PTR .LC7[rip]` | `movd eax, xmm0`, `add eax, -2147483648`, `movd xmm0, eax` | Im Original ändert GCC das Vorzeichenbit direkt per XOR-Maske. Bei der expliziten Bitvariante verwendet GCC eine Integer-Addition mit `0x80000000`, die modulo `2^32` denselben Bitwechsel bewirkt. |

#### Bewertung der Compiler-Optimierung

Bei a, b, c und e ist die manuelle Transformation im optimierten
Maschinencode nicht mehr sichtbar: GCC erkennt die Strength Reduction bereits
selbst und erzeugt für Original und Transformation denselben Code.

Bei d ist die manuelle Transformation weiterhin deutlich vorteilhaft. GCC
darf die Gleitkommaberechnung mit anschließender Konvertierung nicht
selbstständig durch einen Integer-Shift ersetzen, obwohl dies für den hier
verwendeten Wertebereich semantisch passend ist.

Bei f ist eine reine Betrachtung der Anzahl arithmetischer Operationen nicht
ausreichend. Die manuelle Variante spart Divisionen, erschwert aber wegen der
Abhängigkeit von `quotient` zwischen den Iterationen die SIMD-Vektorisierung.
Ob die Transformation tatsächlich schneller ist, müsste deshalb auf der
Zielarchitektur gemessen werden.

Bei g optimiert GCC bereits die Originalmultiplikation zu einem direkten
Wechsel des IEEE-754-Vorzeichenbits. Die manuelle Bitmanipulation ist daher im
Quellcode komplizierter, ohne für den optimierten Code einen klaren Vorteil zu
bieten.

### 4) Fazit

Strength Reduction ist besonders nützlich, wenn eine teure Operation durch
semantisch gleichwertige günstigere Instruktionen ersetzt werden kann. Bei
einfachen ganzzahligen Fällen nimmt `gcc -O3` viele Transformationen bereits
selbst vor. Manuelle Änderungen sind vor allem dann relevant, wenn der
Compiler die Äquivalenz wegen Typumwandlungen, Gleitkommarundung oder
komplizierter Schleifenstruktur nicht selbst herleiten darf.
