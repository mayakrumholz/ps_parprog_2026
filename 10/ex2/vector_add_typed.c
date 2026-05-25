#define _POSIX_C_SOURCE 200809L

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifndef DATA_TYPE
#define DATA_TYPE float
#endif

#ifndef TYPE_NAME
#define TYPE_NAME "float"
#endif

#ifndef VARIANT_NAME
#define VARIANT_NAME "unknown"
#endif

#ifndef DEFAULT_SIZE
#define DEFAULT_SIZE 2048
#endif

#ifndef DEFAULT_REPETITIONS
#define DEFAULT_REPETITIONS 1000000
#endif

static double now_seconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
}

static void *xaligned_alloc(size_t alignment, size_t bytes) {
    void *ptr = NULL;
    int rc = posix_memalign(&ptr, alignment, bytes);

    if (rc != 0) {
        fprintf(stderr, "posix_memalign failed: %s\n", strerror(rc));
        exit(EXIT_FAILURE);
    }

    return ptr;
}

static void initialize_vectors(DATA_TYPE *a, DATA_TYPE *b, DATA_TYPE *c, int size) {
    int i;

    for (i = 0; i < size; ++i) {
        a[i] = (DATA_TYPE)1.0;
        b[i] = (DATA_TYPE)0.5;
        c[i] = (DATA_TYPE)0.25;
    }
}

__attribute__((noinline))
static void run_kernel(DATA_TYPE *restrict a,
                       const DATA_TYPE *restrict b,
                       const DATA_TYPE *restrict c,
                       int size,
                       int repetitions) {
    int run;

    for (run = 0; run < repetitions; ++run) {
#ifdef USE_OMP_SIMD
#pragma omp simd
#endif
        for (int i = 0; i < size; ++i) {
            a[i] += b[i] * c[i];
        }
    }
}

static long double checksum(const DATA_TYPE *values, int size) {
    long double sum = 0.0L;
    int i;

    for (i = 0; i < size; ++i) {
        sum += (long double)values[i];
    }

    return sum;
}

int main(int argc, char **argv) {
    int size = DEFAULT_SIZE;
    int repetitions = DEFAULT_REPETITIONS;
    const DATA_TYPE init_a = (DATA_TYPE)1.0;
    const DATA_TYPE init_b = (DATA_TYPE)0.5;
    const DATA_TYPE init_c = (DATA_TYPE)0.25;
    const DATA_TYPE increment = init_b * init_c;
    size_t bytes;
    DATA_TYPE *a;
    DATA_TYPE *b;
    DATA_TYPE *c;
    double start;
    double elapsed;
    DATA_TYPE expected_value;
    long double expected_checksum;
    long double observed_checksum;
    DATA_TYPE sample0;
    DATA_TYPE samplemid;
    DATA_TYPE samplelast;
    long double tolerance;
    const char *status;

    if (argc >= 2) {
        size = atoi(argv[1]);
    }
    if (argc >= 3) {
        repetitions = atoi(argv[2]);
    }

    if (size <= 0 || repetitions <= 0) {
        fprintf(stderr, "usage: %s [size>0] [repetitions>0]\n", argv[0]);
        return EXIT_FAILURE;
    }

    bytes = (size_t)size * sizeof(DATA_TYPE);
    a = xaligned_alloc(64, bytes);
    b = xaligned_alloc(64, bytes);
    c = xaligned_alloc(64, bytes);

    initialize_vectors(a, b, c, size);

    start = now_seconds();
    run_kernel(a, b, c, size, repetitions);
    elapsed = now_seconds() - start;

    expected_value = init_a + (DATA_TYPE)repetitions * increment;
    expected_checksum = (long double)size * (long double)expected_value;
    observed_checksum = checksum(a, size);
    sample0 = a[0];
    samplemid = a[size / 2];
    samplelast = a[size - 1];
    tolerance = fabsl((long double)expected_value) * 1e-9L;
    if (tolerance < 1e-7L) {
        tolerance = 1e-7L;
    }

    status =
        (fabsl((long double)sample0 - (long double)expected_value) <= tolerance &&
         fabsl((long double)samplemid - (long double)expected_value) <= tolerance &&
         fabsl((long double)samplelast - (long double)expected_value) <= tolerance)
            ? "ok"
            : "mismatch";

    printf("variant=%s type=%s size=%d repetitions=%d elapsed_seconds=%.9f "
           "checksum=%.12Lf expected_checksum=%.12Lf sample0=%.12Lf "
           "samplemid=%.12Lf samplelast=%.12Lf expected_value=%.12Lf status=%s\n",
           VARIANT_NAME,
           TYPE_NAME,
           size,
           repetitions,
           elapsed,
           observed_checksum,
           expected_checksum,
           (long double)sample0,
           (long double)samplemid,
           (long double)samplelast,
           (long double)expected_value,
           status);

    free(a);
    free(b);
    free(c);

    return strcmp(status, "ok") == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
