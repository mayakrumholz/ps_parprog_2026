#include <errno.h>
#include <math.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef struct {
    size_t begin;
    size_t end;
    double *x;
    double *y;
    const double *z;
    int twice;
} worker_args_t;

typedef struct {
    const char *case_name;
    const char *variant;
    int threads;
    size_t n;
    double seconds;
    double checksum;
    double aux;
} benchmark_result_t;

static double now_seconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

static int launch_threads(
    int threads,
    void *(*worker)(void *),
    worker_args_t *args,
    pthread_t *thread_ids
) {
    for (int t = 0; t < threads; ++t) {
        int rc = pthread_create(&thread_ids[t], NULL, worker, &args[t]);
        if (rc != 0) {
            fprintf(stderr, "pthread_create failed: %s\n", strerror(rc));
            return -1;
        }
    }
    for (int t = 0; t < threads; ++t) {
        int rc = pthread_join(thread_ids[t], NULL);
        if (rc != 0) {
            fprintf(stderr, "pthread_join failed: %s\n", strerror(rc));
            return -1;
        }
    }
    return 0;
}

static double checksum_array(const double *values, size_t n) {
    double sum = 0.0;
    for (size_t i = 0; i < n; ++i) {
        sum += values[i];
    }
    return sum;
}

static void initialize_input(double *x, double *y, double *z, size_t n) {
    for (size_t i = 0; i < n; ++i) {
        x[i] = 0.125 + (double)((i * 13u + 5u) % 4096u) / 512.0;
        y[i] = 0.25 + (double)((i * 29u + 3u) % 8192u) / 1024.0;
        z[i] = 0.5 + (double)((i * 7u + 11u) % 2048u) / 256.0;
    }
}

static void *case_a_worker(void *opaque) {
    worker_args_t *args = (worker_args_t *)opaque;
    for (size_t i = args->begin; i < args->end; ++i) {
        int exponent = 0;
        if (i > (size_t)INT32_MAX) {
            exponent = -INT32_MAX;
        } else {
            exponent = -(int)i;
        }
        args->x[i] = ldexp(args->y[i], exponent);
    }
    return NULL;
}

static void *case_b_y_worker(void *opaque) {
    worker_args_t *args = (worker_args_t *)opaque;
    for (size_t i = args->begin; i < args->end; ++i) {
        args->y[i] = args->y[i] + args->z[i] * 3.0;
    }
    return NULL;
}

static void *case_b_x_worker(void *opaque) {
    worker_args_t *args = (worker_args_t *)opaque;
    for (size_t i = args->begin; i < args->end; ++i) {
        args->x[i] = (args->x[i] + args->y[i - 1]) / 2.0;
    }
    return NULL;
}

static int allocate_threads(int threads, pthread_t **thread_ids, worker_args_t **args) {
    *thread_ids = malloc(sizeof(**thread_ids) * (size_t)threads);
    *args = calloc((size_t)threads, sizeof(**args));
    if (*thread_ids == NULL || *args == NULL) {
        fprintf(stderr, "thread allocation failed\n");
        free(*thread_ids);
        free(*args);
        return -1;
    }
    return 0;
}

static int benchmark_case_a(const char *variant, int threads, size_t n, benchmark_result_t *result) {
    double *x = malloc(sizeof(*x) * n);
    double *y = malloc(sizeof(*y) * n);
    double *z = malloc(sizeof(*z) * n);
    if (x == NULL || y == NULL || z == NULL) {
        fprintf(stderr, "allocation failed for case_a\n");
        free(x);
        free(y);
        free(z);
        return -1;
    }
    initialize_input(x, y, z, n);

    const double start = now_seconds();
    if (strcmp(variant, "original") == 0) {
        double factor = 1.0;
        for (size_t i = 0; i < n; ++i) {
            x[i] = factor * y[i];
            factor = factor / 2.0;
        }
    } else {
        pthread_t *thread_ids = NULL;
        worker_args_t *args = NULL;
        if (allocate_threads(threads, &thread_ids, &args) != 0) {
            free(x);
            free(y);
            free(z);
            return -1;
        }
        for (int t = 0; t < threads; ++t) {
            args[t].begin = (size_t)t * n / (size_t)threads;
            args[t].end = (size_t)(t + 1) * n / (size_t)threads;
            args[t].x = x;
            args[t].y = y;
            args[t].z = z;
        }
        if (launch_threads(threads, case_a_worker, args, thread_ids) != 0) {
            free(thread_ids);
            free(args);
            free(x);
            free(y);
            free(z);
            return -1;
        }
        free(thread_ids);
        free(args);
    }
    const double end = now_seconds();

    result->case_name = "case_a";
    result->variant = variant;
    result->threads = threads;
    result->n = n;
    result->seconds = end - start;
    result->checksum = checksum_array(x, n);
    result->aux = x[n - 1];
    free(x);
    free(y);
    free(z);
    return 0;
}

static int benchmark_case_b(const char *variant, int threads, size_t n, benchmark_result_t *result) {
    double *x = malloc(sizeof(*x) * n);
    double *y = malloc(sizeof(*y) * n);
    double *z = malloc(sizeof(*z) * n);
    if (x == NULL || y == NULL || z == NULL) {
        fprintf(stderr, "allocation failed for case_b\n");
        free(x);
        free(y);
        free(z);
        return -1;
    }
    initialize_input(x, y, z, n);

    const double start = now_seconds();
    if (strcmp(variant, "original") == 0) {
        for (size_t i = 1; i < n; ++i) {
            x[i] = (x[i] + y[i - 1]) / 2.0;
            y[i] = y[i] + z[i] * 3.0;
        }
    } else {
        pthread_t *thread_ids = NULL;
        worker_args_t *args = NULL;
        if (allocate_threads(threads, &thread_ids, &args) != 0) {
            free(x);
            free(y);
            free(z);
            return -1;
        }
        const size_t work_items = n - 1;
        for (int t = 0; t < threads; ++t) {
            args[t].begin = 1 + (size_t)t * work_items / (size_t)threads;
            args[t].end = 1 + (size_t)(t + 1) * work_items / (size_t)threads;
            args[t].x = x;
            args[t].y = y;
            args[t].z = z;
        }
        if (launch_threads(threads, case_b_y_worker, args, thread_ids) != 0) {
            free(thread_ids);
            free(args);
            free(x);
            free(y);
            free(z);
            return -1;
        }
        if (launch_threads(threads, case_b_x_worker, args, thread_ids) != 0) {
            free(thread_ids);
            free(args);
            free(x);
            free(y);
            free(z);
            return -1;
        }
        free(thread_ids);
        free(args);
    }
    const double end = now_seconds();

    result->case_name = "case_b";
    result->variant = variant;
    result->threads = threads;
    result->n = n;
    result->seconds = end - start;
    result->checksum = checksum_array(x, n) + checksum_array(y, n);
    result->aux = x[n / 2];
    free(x);
    free(y);
    free(z);
    return 0;
}

static void *case_c_transformed_worker(void *opaque) {
    worker_args_t *args = (worker_args_t *)opaque;
    const size_t n = (size_t)args->z[0];
    for (size_t i = args->begin; i < args->end; ++i) {
        const double updated = args->x[i] + 5.0 * args->y[i];
        if (args->twice && i + 1 < n) {
            args->x[i] = 2.0 * updated;
        } else {
            args->x[i] = updated;
        }
    }
    return NULL;
}

static int benchmark_case_c(
    const char *variant,
    int threads,
    size_t n,
    int twice,
    benchmark_result_t *result
) {
    double *x = malloc(sizeof(*x) * n);
    double *y = malloc(sizeof(*y) * n);
    double *z = malloc(sizeof(*z) * n);
    if (x == NULL || y == NULL || z == NULL) {
        fprintf(stderr, "allocation failed for case_c\n");
        free(x);
        free(y);
        free(z);
        return -1;
    }
    initialize_input(x, y, z, n);

    const double start = now_seconds();
    if (strcmp(variant, "original") == 0) {
        x[0] = x[0] + 5.0 * y[0];
        for (size_t i = 1; i < n; ++i) {
            x[i] = x[i] + 5.0 * y[i];
            if (twice) {
                x[i - 1] = 2.0 * x[i - 1];
            }
        }
    } else {
        pthread_t *thread_ids = NULL;
        worker_args_t *args = NULL;
        if (allocate_threads(threads, &thread_ids, &args) != 0) {
            free(x);
            free(y);
            free(z);
            return -1;
        }
        z[0] = (double)n;
        for (int t = 0; t < threads; ++t) {
            args[t].begin = (size_t)t * n / (size_t)threads;
            args[t].end = (size_t)(t + 1) * n / (size_t)threads;
            args[t].x = x;
            args[t].y = y;
            args[t].z = z;
            args[t].twice = twice;
        }
        if (launch_threads(threads, case_c_transformed_worker, args, thread_ids) != 0) {
            free(thread_ids);
            free(args);
            free(x);
            free(y);
            free(z);
            return -1;
        }
        free(thread_ids);
        free(args);
    }
    const double end = now_seconds();

    result->case_name = twice ? "case_c_twice1" : "case_c_twice0";
    result->variant = variant;
    result->threads = threads;
    result->n = n;
    result->seconds = end - start;
    result->checksum = checksum_array(x, n);
    result->aux = x[n / 2];
    free(x);
    free(y);
    free(z);
    return 0;
}

static int run_case(
    const char *case_name,
    const char *variant,
    int threads,
    size_t n,
    benchmark_result_t *result
) {
    if (strcmp(case_name, "case_a") == 0) {
        return benchmark_case_a(variant, threads, n, result);
    }
    if (strcmp(case_name, "case_b") == 0) {
        return benchmark_case_b(variant, threads, n, result);
    }
    if (strcmp(case_name, "case_c_twice0") == 0) {
        return benchmark_case_c(variant, threads, n, 0, result);
    }
    if (strcmp(case_name, "case_c_twice1") == 0) {
        return benchmark_case_c(variant, threads, n, 1, result);
    }
    fprintf(stderr, "unknown case name: %s\n", case_name);
    return -1;
}

int main(int argc, char **argv) {
    if (argc != 5) {
        fprintf(
            stderr,
            "usage: %s <case_a|case_b|case_c_twice0|case_c_twice1> <original|parallel> <threads> <n>\n",
            argv[0]
        );
        return 1;
    }

    char *endptr = NULL;
    errno = 0;
    const long threads_long = strtol(argv[3], &endptr, 10);
    if (errno != 0 || endptr == argv[3] || *endptr != '\0' || threads_long < 1 || threads_long > 256) {
        fprintf(stderr, "invalid thread count: %s\n", argv[3]);
        return 1;
    }

    errno = 0;
    const unsigned long long n_value = strtoull(argv[4], &endptr, 10);
    if (errno != 0 || endptr == argv[4] || *endptr != '\0' || n_value < 8ull) {
        fprintf(stderr, "invalid problem size: %s\n", argv[4]);
        return 1;
    }

    benchmark_result_t result;
    if (run_case(argv[1], argv[2], (int)threads_long, (size_t)n_value, &result) != 0) {
        return 1;
    }

    printf(
        "case=%s variant=%s threads=%d n=%zu seconds=%.9f checksum=%.12f aux=%.12f\n",
        result.case_name,
        result.variant,
        result.threads,
        result.n,
        result.seconds,
        result.checksum,
        result.aux
    );
    return 0;
}
