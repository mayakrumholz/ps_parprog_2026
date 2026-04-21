# Assignment 6

The goal of this assignment is to expand your knowledge on and familiarity with OpenMP.

## Exercise 1 (1.5 Points)

### Description

There are several methods to approximate Pi numerically. In this exercise, you are asked to approximate Pi using the Monte Carlo method. Therefore, n (n >> 1) random 2D points equally distributed in the interval [0, 1] x [0, 1] are generated, and it is checked whether they are inside the first quadrant of a unit circle. Let i be the number of points that lie inside the quarter of the unit circle. Then Pi can be approximated by 4 * i / n.
The code can be found in the provided serial implementation.

### Tasks

1) Implement three parallel versions of Monte Carlo Pi approximation using OpenMP and the provided serial implementation [ex1/serial.c](ex1/serial.c) with the constructs:
   1) ```critical``` section
   2) ```atomic``` statement
   3) ```reduction``` clause
2) To further increase any performance effects between them, increment the samples counter directly without aggregating into private variables first.
3) Benchmark your parallel implementations with 1, 4, 8 and 12 threads on LCC3 using n=700000000 using OpenMP's time measurement function. What can you observe? How and why do these constructs differ?
4) Add the time of 12 threads to the comparision spreadsheet.

## Exercise 2 (1.5 Points)

### Description

In previous assignments you were asked to implement a program that calculates the [Mandelbrot set](https://en.wikipedia.org/wiki/Mandelbrot_set) in serial and parallel using `Posix Threads`.
In this exercise you will finally see the benefit of using `OpenMP`.

### Tasks

1) Implement the Mandelbrot set calculation in OpenMP.
2) Benchmark your implementation with 1, 4, 8 and 12 threads and describe your observations.
3) Use the loop scheduling methods discussed in the lecture, `static`, `dynamic`, `guided` and `auto`. Explain their differences and compare their performance. What can you observe? In addition, try the loop scheduling methods `auto` and `runtime`. What do they do, what can you observe?
4) Add the fastest time for 12 threads to the comparision spreadsheet.
