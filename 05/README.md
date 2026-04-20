# Assignment 5

The goal of this assignment is to expand your knowledge on and familiarity with OpenMP.

## Exercise 1 (1.5 Points)

### Description

This exercise deals with the OpenMP flush directive and why it can be necessary.

### Tasks

1) Examine [ex1/ex1.c](ex1/ex1.c) and explain what the code does from an abstract, high-level perspective. What should happen here?
2) Compile this code with optimization level `-O3`. Run it in an interactive job (e.g. using `salloc --exclusive --tasks-per-node=1 --cpus-per-task=1 srun --pty bash`) in a loop many times (e.g. write a loop in bash that executes it 1000 times). Run this loop repeatedly. What can you observe? **Note: Please quit your interactive job once you are done!**
3) Does this code require any `#pragma omp flush` directives? If it does, where are they necessary? If it does not, why not?
4) Optional, advanced question: Does this code require any `#pragma omp atomic` directives? If it does, where are they necessary? If it does not, why not?

## Exercise 2 (1.5 Points)

### Description

Consider the following, individual code examples in the context of parallelization and data sharing:

```C
a[0] = 0;
#pragma omp parallel for
for (i=1; i<N; i++) {
    a[i] = 2.0*i*(i-1);
    b[i] = a[i] - a[i-1];
}
```

```C
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

```C
#pragma omp parallel for default(none)
for (i=0; i<N; i++) {
    x = sqrt(b[i]) - 1;
    a[i] = x*x + 2*x + 1;
}
```

```C
f = 2;
#pragma omp parallel for private(f,x)
for (i=0; i<N; i++) {
    x = f * b[i];
    a[i] = x - 7;
}
a[0] = x; 
```

```C
sum = 0; 
#pragma omp parallel for
for (i=0; i<N; i++) {
    sum = sum + b[i];
}
```

```C
#pragma omp parallel
#pragma omp for
for (i=0; i<N; i++) {
    #pragma omp for
    for (j=0; j<N; j++) {
        a[i][j] = b[i][j];
    }
}
```

### Tasks

1) For each example that already contains a pragma, investigate whether it is parallelized correctly or whether there are any compiler or runtime issues. If there are any, fix them while keeping the parallelism.
2) For each example not already containing a pragma, investigate how to parallelize it correctly.
3) Are there multiple solutions and if so, what are their advantages and disadvantages?

## General Notes

All the material required by the tasks above (e.g., code, figures, text, etc...) must be part of the solution that is handed in. Your experiments should be reproducible and comparable to your measurements using the solution materials that you hand in.

**Every** member of your group must be able to explain the given problem, your solution, and possible findings. You may also need to answer detailed questions about any of these aspects.
