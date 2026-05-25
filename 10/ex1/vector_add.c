#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifndef VARIANT_NAME
#define VARIANT_NAME "unknown"
#endif

enum {
    DEFAULT_SIZE = 2048,
    DEFAULT_REPETITIONS = 1000000
};

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

__attribute__((noinline))
static void run_kernel(float *restrict a,
                       const float *restrict b,
                       const float *restrict c,
                       int size,
                       int repetitions) {
    for (int run = 0; run < repetitions; ++run) {
        for (int i = 0; i < size; ++i) {
            a[i] += b[i] * c[i];
        }
    }
}

static void initialize_vectors(float *a, float *b, float *c, int size) {
    for (int i = 0; i < size; ++i) {
        a[i] = 1.0f;
        b[i] = 0.5f;
        c[i] = 0.25f;
    }
}

static double checksum(const float *values, int size) {
    double sum = 0.0;

    for (int i = 0; i < size; ++i) {
        sum += (double)values[i];
    }

    return sum;
}

int main(int argc, char **argv) {
    int size = DEFAULT_SIZE;
    int repetitions = DEFAULT_REPETITIONS;
    const float init_a = 1.0f;
    const float init_b = 0.5f;
    const float init_c = 0.25f;
    const float increment = init_b * init_c;

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

    size_t bytes = (size_t)size * sizeof(float);
    float *a = xaligned_alloc(64, bytes);
    float *b = xaligned_alloc(64, bytes);
    float *c = xaligned_alloc(64, bytes);

    initialize_vectors(a, b, c, size);

    double start = now_seconds();
    run_kernel(a, b, c, size, repetitions);
    double elapsed = now_seconds() - start;

    float expected_value = init_a + (float)repetitions * increment;
    double expected_checksum = (double)size * (double)expected_value;
    double observed_checksum = checksum(a, size);
    float sample0 = a[0];
    float sample_mid = a[size / 2];
    float sample_last = a[size - 1];
    double tolerance = fmax(1e-4, fabs((double)expected_value) * 1e-6);
    const char *status =
        (fabs((double)sample0 - (double)expected_value) <= tolerance &&
         fabs((double)sample_mid - (double)expected_value) <= tolerance &&
         fabs((double)sample_last - (double)expected_value) <= tolerance)
            ? "ok"
            : "mismatch";

    printf("variant=%s size=%d repetitions=%d elapsed_seconds=%.9f "
           "checksum=%.9f expected_checksum=%.9f sample0=%.9f "
           "samplemid=%.9f samplelast=%.9f expected_value=%.9f status=%s\n",
           VARIANT_NAME,
           size,
           repetitions,
           elapsed,
           observed_checksum,
           expected_checksum,
           (double)sample0,
           (double)sample_mid,
           (double)sample_last,
           (double)expected_value,
           status);

    free(a);
    free(b);
    free(c);

    return strcmp(status, "ok") == 0 ? EXIT_SUCCESS : EXIT_FAILURE;
}
