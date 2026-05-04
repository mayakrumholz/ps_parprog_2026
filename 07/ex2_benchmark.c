#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef _OPENMP
#include <omp.h>
#else
static double omp_get_wtime(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

static void omp_set_num_threads(int threads) {
    (void)threads;
}

static int omp_get_max_threads(void) {
    return 1;
}
#endif

typedef enum {
    CASE_A,
    CASE_B,
    CASE_C_FALSE,
    CASE_C_TRUE
} benchmark_case_t;

typedef enum {
    VARIANT_ORIGINAL,
    VARIANT_PARALLEL
} benchmark_variant_t;

typedef struct {
    size_t n;
    double *x;
    double *y;
    double *z;
} arrays_t;

static void *xmalloc(size_t bytes) {
    void *ptr = malloc(bytes);
    if (ptr == NULL) {
        fprintf(stderr, "allocation failed for %zu bytes\n", bytes);
        exit(EXIT_FAILURE);
    }
    return ptr;
}

static benchmark_case_t parse_case(const char *text) {
    if (strcmp(text, "a") == 0) {
        return CASE_A;
    }
    if (strcmp(text, "b") == 0) {
        return CASE_B;
    }
    if (strcmp(text, "c_false") == 0) {
        return CASE_C_FALSE;
    }
    if (strcmp(text, "c_true") == 0) {
        return CASE_C_TRUE;
    }
    fprintf(stderr, "unknown case: %s\n", text);
    exit(EXIT_FAILURE);
}

static benchmark_variant_t parse_variant(const char *text) {
    if (strcmp(text, "original") == 0) {
        return VARIANT_ORIGINAL;
    }
    if (strcmp(text, "parallel") == 0) {
        return VARIANT_PARALLEL;
    }
    fprintf(stderr, "unknown variant: %s\n", text);
    exit(EXIT_FAILURE);
}

static const char *case_name(benchmark_case_t bench_case) {
    switch (bench_case) {
        case CASE_A:
            return "a";
        case CASE_B:
            return "b";
        case CASE_C_FALSE:
            return "c_false";
        case CASE_C_TRUE:
            return "c_true";
    }
    return "unknown";
}

static void init_arrays(arrays_t *arrays) {
    for (size_t i = 0; i < arrays->n; ++i) {
        arrays->x[i] = 1.0 + (double)((i * 17u) % 101u) / 97.0;
        arrays->y[i] = 0.5 + (double)((i * 13u) % 89u) / 53.0;
        if (arrays->z != NULL) {
            arrays->z[i] = 0.001 + (double)((i * 7u) % 41u) / 10000.0;
        }
    }
}

static arrays_t make_arrays(size_t n, int need_z) {
    arrays_t arrays;
    arrays.n = n;
    arrays.x = xmalloc(n * sizeof(*arrays.x));
    arrays.y = xmalloc(n * sizeof(*arrays.y));
    arrays.z = need_z ? xmalloc(n * sizeof(*arrays.z)) : NULL;
    init_arrays(&arrays);
    return arrays;
}

static void clone_arrays(arrays_t *dst, const arrays_t *src, int need_z) {
    memcpy(dst->x, src->x, src->n * sizeof(*src->x));
    memcpy(dst->y, src->y, src->n * sizeof(*src->y));
    if (need_z) {
        memcpy(dst->z, src->z, src->n * sizeof(*src->z));
    }
}

static void free_arrays(arrays_t *arrays) {
    free(arrays->x);
    free(arrays->y);
    free(arrays->z);
}

static void run_case_a_original(arrays_t *arrays, int repetitions) {
    for (int rep = 0; rep < repetitions; ++rep) {
        double factor = 1.0;
        for (size_t i = 0; i < arrays->n; ++i) {
            arrays->x[i] = factor * arrays->y[i];
            factor *= 0.5;
        }
    }
}

static void run_case_a_parallel(arrays_t *arrays, int repetitions) {
    for (int rep = 0; rep < repetitions; ++rep) {
        #pragma omp parallel
        {
            const int tid = omp_get_thread_num();
            const int thread_count = omp_get_num_threads();
            const size_t start = (size_t)tid * arrays->n / (size_t)thread_count;
            const size_t end = (size_t)(tid + 1) * arrays->n / (size_t)thread_count;
            double factor = ldexp(1.0, -(int)start);

            for (size_t i = start; i < end; ++i) {
                arrays->x[i] = factor * arrays->y[i];
                factor *= 0.5;
            }
        }
    }
}

static void run_case_b_original(arrays_t *arrays, int repetitions) {
    for (int rep = 0; rep < repetitions; ++rep) {
        for (size_t i = 1; i < arrays->n; ++i) {
            arrays->x[i] = (arrays->x[i] + arrays->y[i - 1]) / 2.0;
            arrays->y[i] = arrays->y[i] + arrays->z[i] * 3.0;
        }
    }
}

static void run_case_b_parallel(arrays_t *arrays, int repetitions) {
    for (int rep = 0; rep < repetitions; ++rep) {
        #pragma omp parallel for schedule(static)
        for (size_t i = 1; i < arrays->n; ++i) {
            arrays->y[i] = arrays->y[i] + arrays->z[i] * 3.0;
        }

        #pragma omp parallel for schedule(static)
        for (size_t i = 1; i < arrays->n; ++i) {
            arrays->x[i] = (arrays->x[i] + arrays->y[i - 1]) / 2.0;
        }
    }
}

static void run_case_c_false_original(arrays_t *arrays, int repetitions) {
    for (int rep = 0; rep < repetitions; ++rep) {
        arrays->x[0] = arrays->x[0] + 5.0 * arrays->y[0];
        for (size_t i = 1; i < arrays->n; ++i) {
            arrays->x[i] = arrays->x[i] + 5.0 * arrays->y[i];
        }
    }
}

static void run_case_c_false_parallel(arrays_t *arrays, int repetitions) {
    for (int rep = 0; rep < repetitions; ++rep) {
        #pragma omp parallel for schedule(static)
        for (size_t i = 0; i < arrays->n; ++i) {
            arrays->x[i] = arrays->x[i] + 5.0 * arrays->y[i];
        }
    }
}

static void run_case_c_true_original(arrays_t *arrays, int repetitions) {
    for (int rep = 0; rep < repetitions; ++rep) {
        arrays->x[0] = arrays->x[0] + 5.0 * arrays->y[0];
        for (size_t i = 1; i < arrays->n; ++i) {
            arrays->x[i] = arrays->x[i] + 5.0 * arrays->y[i];
            arrays->x[i - 1] = 2.0 * arrays->x[i - 1];
        }
    }
}

static void run_case_c_true_parallel(arrays_t *arrays, int repetitions) {
    for (int rep = 0; rep < repetitions; ++rep) {
        #pragma omp parallel for schedule(static)
        for (size_t i = 0; i < arrays->n; ++i) {
            const double updated = arrays->x[i] + 5.0 * arrays->y[i];
            arrays->x[i] = (i + 1u < arrays->n) ? 2.0 * updated : updated;
        }
    }
}

static void run_case(arrays_t *arrays, benchmark_case_t bench_case, benchmark_variant_t variant, int repetitions) {
    switch (bench_case) {
        case CASE_A:
            if (variant == VARIANT_ORIGINAL) {
                run_case_a_original(arrays, repetitions);
            } else {
                run_case_a_parallel(arrays, repetitions);
            }
            break;
        case CASE_B:
            if (variant == VARIANT_ORIGINAL) {
                run_case_b_original(arrays, repetitions);
            } else {
                run_case_b_parallel(arrays, repetitions);
            }
            break;
        case CASE_C_FALSE:
            if (variant == VARIANT_ORIGINAL) {
                run_case_c_false_original(arrays, repetitions);
            } else {
                run_case_c_false_parallel(arrays, repetitions);
            }
            break;
        case CASE_C_TRUE:
            if (variant == VARIANT_ORIGINAL) {
                run_case_c_true_original(arrays, repetitions);
            } else {
                run_case_c_true_parallel(arrays, repetitions);
            }
            break;
    }
}

static double checksum(const arrays_t *arrays, benchmark_case_t bench_case) {
    double sum = 0.0;
    for (size_t i = 0; i < arrays->n; ++i) {
        sum += arrays->x[i] * 0.75 + arrays->y[i] * 0.25;
        if (bench_case == CASE_B) {
            sum += arrays->z[i] * 0.125;
        }
    }
    return sum;
}

static int need_z_for_case(benchmark_case_t bench_case) {
    return bench_case == CASE_B;
}

static int verify_case(benchmark_case_t bench_case, size_t n, int repetitions, int threads) {
    const int need_z = need_z_for_case(bench_case);
    arrays_t base = make_arrays(n, need_z);
    arrays_t serial = make_arrays(n, need_z);
    arrays_t parallel = make_arrays(n, need_z);
    int ok = 1;

    clone_arrays(&serial, &base, need_z);
    clone_arrays(&parallel, &base, need_z);

    omp_set_num_threads(1);
    run_case(&serial, bench_case, VARIANT_ORIGINAL, repetitions);
    omp_set_num_threads(threads);
    run_case(&parallel, bench_case, VARIANT_PARALLEL, repetitions);

    for (size_t i = 0; i < n; ++i) {
        if (fabs(serial.x[i] - parallel.x[i]) > 1e-9 || fabs(serial.y[i] - parallel.y[i]) > 1e-9) {
            ok = 0;
            fprintf(
                stderr,
                "mismatch in case %s at index %zu: x_serial=%.17g x_parallel=%.17g y_serial=%.17g y_parallel=%.17g\n",
                case_name(bench_case),
                i,
                serial.x[i],
                parallel.x[i],
                serial.y[i],
                parallel.y[i]
            );
            break;
        }
    }

    free_arrays(&base);
    free_arrays(&serial);
    free_arrays(&parallel);
    return ok;
}

static void usage(const char *program) {
    fprintf(stderr, "usage:\n");
    fprintf(stderr, "  %s verify\n", program);
    fprintf(stderr, "  %s <case> <variant> <n> <repetitions> <threads>\n", program);
}

int main(int argc, char **argv) {
    if (argc == 2 && strcmp(argv[1], "verify") == 0) {
        const struct {
            benchmark_case_t bench_case;
            size_t n;
            int repetitions;
        } checks[] = {
            {CASE_A, 2048, 4},
            {CASE_B, 4096, 5},
            {CASE_C_FALSE, 4096, 6},
            {CASE_C_TRUE, 4096, 5},
        };

        int all_ok = 1;
        for (size_t i = 0; i < sizeof(checks) / sizeof(checks[0]); ++i) {
            const int ok = verify_case(checks[i].bench_case, checks[i].n, checks[i].repetitions, 4);
            printf(
                "verify case=%s n=%zu repetitions=%d status=%s\n",
                case_name(checks[i].bench_case),
                checks[i].n,
                checks[i].repetitions,
                ok ? "ok" : "failed"
            );
            if (!ok) {
                all_ok = 0;
            }
        }
        return all_ok ? EXIT_SUCCESS : EXIT_FAILURE;
    }

    if (argc != 6) {
        usage(argv[0]);
        return EXIT_FAILURE;
    }

    const benchmark_case_t bench_case = parse_case(argv[1]);
    const benchmark_variant_t variant = parse_variant(argv[2]);
    const size_t n = (size_t)strtoull(argv[3], NULL, 10);
    const int repetitions = atoi(argv[4]);
    const int threads = atoi(argv[5]);
    const int need_z = need_z_for_case(bench_case);

    if (n < 2 || repetitions < 1 || threads < 1) {
        fprintf(stderr, "invalid arguments\n");
        return EXIT_FAILURE;
    }

    arrays_t arrays = make_arrays(n, need_z);
    omp_set_num_threads(threads);

    const double start = omp_get_wtime();
    run_case(&arrays, bench_case, variant, repetitions);
    const double elapsed = omp_get_wtime() - start;

    printf(
        "case=%s variant=%s n=%zu repetitions=%d threads=%d elapsed_seconds=%.9f checksum=%.17g max_threads=%d\n",
        case_name(bench_case),
        variant == VARIANT_ORIGINAL ? "original" : "parallel",
        n,
        repetitions,
        threads,
        elapsed,
        checksum(&arrays, bench_case),
        omp_get_max_threads()
    );

    free_arrays(&arrays);
    return EXIT_SUCCESS;
}
