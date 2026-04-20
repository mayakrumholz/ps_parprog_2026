# Assignment 5 - Answers

## Exercise 1

### 1) High-level description

The program implements a very simple producer/consumer pattern with two OpenMP threads:

- Thread 0 computes or provides a value by writing `data = 42`.
- Afterwards, thread 0 signals completion by setting `flag = 1`.
- Thread 1 busy-waits until it sees that `flag` became `1`.
- Once the flag is visible, thread 1 prints both `flag` and `data`.

At a high level, the intended behavior is:

```text
thread 0: write data -> publish flag
thread 1: wait for flag -> read data
```

So the expected output is:

```text
flag=1 data=42
```

### 2) Observation with `-O3`

When compiled with `-O3` and executed many times, the code can become nondeterministic. The typical observation is that some runs never terminate anymore, because thread 1 keeps spinning in the loop:

```c
while (flag_val < 1) {
    flag_val = flag;
}
```

The reason is that, without synchronization, the compiler and hardware are allowed to keep values in registers or caches and reorder memory operations. With optimization enabled, the read of `flag` may effectively stop reflecting thread 0's write in a reliable way. So repeated runs often show one of these symptoms:

- the program prints `flag=1 data=42`
- the program hangs forever
- more generally, the behavior is undefined because the code contains a data race

The most relevant practical symptom for this example is the occasional infinite loop.

### 3) Are `#pragma omp flush` directives necessary?

Yes. If this program is implemented with the `flush` mechanism, then synchronization is required between:

- thread 0 writing `data`
- thread 0 publishing `flag`
- thread 1 polling `flag`
- thread 1 reading `data` after the flag was observed

One correct `flush`-based version is:

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

Conceptually:

- after writing `data`, thread 0 must make that write visible
- after writing `flag`, thread 0 must publish the signal
- thread 1 must refresh `flag` inside the loop
- after observing `flag == 1`, thread 1 must refresh `data` before printing

Important nuance: in OpenMP, `flush` is the mechanism this exercise is about, so this is the intended fix. A plain busy-wait loop without synchronization is not correct.

### 4) Are `#pragma omp atomic` directives necessary?

Not strictly necessary if the program is fixed using a correct `flush` synchronization pattern, because this exercise is specifically about visibility and ordering.

However, `atomic` is often the cleaner and less error-prone solution for the flag. In practice, a robust alternative is:

- `#pragma omp atomic write` for `flag = 1`
- `#pragma omp atomic read` when thread 1 polls `flag`

Even with atomics for the flag, the publication of `data` still has to be ordered correctly with respect to the flag. So for this exercise, the clearest answer is:

- `flush` is required to make the intended communication correct
- `atomic` is optional here, but often preferable for the flag in production code

### Reproducibility material

The file [job.sh](/Users/mayakrumholz/Desktop/Uni/5_Semester/Parallele_Programmierung/ps_parprog_2026/05/ex1/job.sh) builds the program with `-O3`, executes it repeatedly on the cluster, and writes the collected observations to text files in `05/ex1/results/`.
