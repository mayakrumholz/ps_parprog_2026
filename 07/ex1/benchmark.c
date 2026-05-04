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
    const double *x_old;
    double *y;
    double *z;
    double a_scalar;
} worker_args_t;

typedef struct {
    const char *snippet;
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

static void *snippet1_worker(void *opaque) {
    worker_args_t *args = (worker_args_t *)opaque;
    for (size_t i = args->begin; i < args->end; ++i) {
        args->x[i] = (args->y[i] + args->x_old[i + 1]) / 7.0;
    }
    return NULL;
}

static void *snippet2_worker(void *opaque) {
    worker_args_t *args = (worker_args_t *)opaque;
    for (size_t i = args->begin; i < args->end; ++i) {
        args->z[i] = (args->x[i] + args->y[i]) / (double)(i + 1);
    }
    return NULL;
}

static void *snippet3_first_worker(void *opaque) {
    worker_args_t *args = (worker_args_t *)opaque;
    const double b = args->a_scalar;
    for (size_t i = args->begin; i < args->end; ++i) {
        args->x[i] = args->y[i] * 2.0 + b * (double)i;
    }
    return NULL;
}

static void *snippet3_second_worker(void *opaque) {
    worker_args_t *args = (worker_args_t *)opaque;
    const double a = args->a_scalar;
    for (size_t i = args->begin; i < args->end; ++i) {
        args->y[i] = args->x[i] + a / (double)(i + 1);
    }
    return NULL;
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
        x[i] = 0.25 + (double)((i * 17u) % 1024u) / 1024.0;
        y[i] = 0.5 + (double)((i * 31u + 7u) % 2048u) / 2048.0;
        z[i] = 0.0;
    }
}

static int benchmark_snippet1(
    const char *variant,
    int threads,
    size_t n,
    benchmark_result_t *result
) {
    double *x = malloc(sizeof(*x) * n);
    double *y = malloc(sizeof(*y) * n);
    double *z = malloc(sizeof(*z) * n);
    double *x_old = malloc(sizeof(*x_old) * n);
    if (x == NULL || y == NULL || z == NULL || x_old == NULL) {
        fprintf(stderr, "allocation failed for snippet1\n");
        free(x);
        free(y);
        free(z);
        free(x_old);
        return -1;
    }

    initialize_input(x, y, z, n);
    memcpy(x_old, x, sizeof(*x) * n);

    const double start = now_seconds();
    if (strcmp(variant, "original") == 0) {
        for (size_t i = 0; i + 1 < n; ++i) {
            x[i] = (y[i] + x[i + 1]) / 7.0;
        }
    } else {
        pthread_t *thread_ids = malloc(sizeof(*thread_ids) * (size_t)threads);
        worker_args_t *args = calloc((size_t)threads, sizeof(*args));
        if (thread_ids == NULL || args == NULL) {
            fprintf(stderr, "allocation failed for snippet1 threads\n");
            free(thread_ids);
            free(args);
            free(x);
            free(y);
            free(z);
            free(x_old);
            return -1;
        }

        const size_t work_items = n - 1;
        for (int t = 0; t < threads; ++t) {
            size_t begin = (size_t)t * work_items / (size_t)threads;
            size_t end = (size_t)(t + 1) * work_items / (size_t)threads;
            args[t].begin = begin;
            args[t].end = end;
            args[t].x = x;
            args[t].x_old = x_old;
            args[t].y = y;
        }

        if (launch_threads(threads, snippet1_worker, args, thread_ids) != 0) {
            free(thread_ids);
            free(args);
            free(x);
            free(y);
            free(z);
            free(x_old);
            return -1;
        }

        free(thread_ids);
        free(args);
    }
    const double end = now_seconds();

    result->snippet = "snippet1";
    result->variant = variant;
    result->threads = threads;
    result->n = n;
    result->seconds = end - start;
    result->checksum = checksum_array(x, n);
    result->aux = x[n - 1];

    free(x);
    free(y);
    free(z);
    free(x_old);
    return 0;
}

static int benchmark_snippet2(
    const char *variant,
    int threads,
    size_t n,
    benchmark_result_t *result
) {
    double *x = malloc(sizeof(*x) * n);
    double *y = malloc(sizeof(*y) * n);
    double *z = malloc(sizeof(*z) * n);
    if (x == NULL || y == NULL || z == NULL) {
        fprintf(stderr, "allocation failed for snippet2\n");
        free(x);
        free(y);
        free(z);
        return -1;
    }

    initialize_input(x, y, z, n);
    const double k = 3.75;
    double a = 0.0;

    const double start = now_seconds();
    if (strcmp(variant, "original") == 0) {
        for (size_t i = 0; i < n; ++i) {
            a = (x[i] + y[i]) / (double)(i + 1);
            z[i] = a;
        }
    } else {
        pthread_t *thread_ids = malloc(sizeof(*thread_ids) * (size_t)threads);
        worker_args_t *args = calloc((size_t)threads, sizeof(*args));
        if (thread_ids == NULL || args == NULL) {
            fprintf(stderr, "allocation failed for snippet2 threads\n");
            free(thread_ids);
            free(args);
            free(x);
            free(y);
            free(z);
            return -1;
        }

        for (int t = 0; t < threads; ++t) {
            size_t begin = (size_t)t * n / (size_t)threads;
            size_t end = (size_t)(t + 1) * n / (size_t)threads;
            args[t].begin = begin;
            args[t].end = end;
            args[t].x = x;
            args[t].y = y;
            args[t].z = z;
        }

        if (launch_threads(threads, snippet2_worker, args, thread_ids) != 0) {
            free(thread_ids);
            free(args);
            free(x);
            free(y);
            free(z);
            return -1;
        }

        a = (x[n - 1] + y[n - 1]) / (double)n;
        free(thread_ids);
        free(args);
    }
    const double f = sqrt(a + k);
    const double end = now_seconds();

    result->snippet = "snippet2";
    result->variant = variant;
    result->threads = threads;
    result->n = n;
    result->seconds = end - start;
    result->checksum = checksum_array(z, n);
    result->aux = f;

    free(x);
    free(y);
    free(z);
    return 0;
}

static int benchmark_snippet3(
    const char *variant,
    int threads,
    size_t n,
    benchmark_result_t *result
) {
    double *x = malloc(sizeof(*x) * n);
    double *y = malloc(sizeof(*y) * n);
    double *z = malloc(sizeof(*z) * n);
    if (x == NULL || y == NULL || z == NULL) {
        fprintf(stderr, "allocation failed for snippet3\n");
        free(x);
        free(y);
        free(z);
        return -1;
    }

    initialize_input(x, y, z, n);
    const double a = 1.75;
    const double b = 0.125;

    const double start = now_seconds();
    if (strcmp(variant, "original") == 0) {
        for (size_t i = 0; i < n; ++i) {
            x[i] = y[i] * 2.0 + b * (double)i;
        }
        for (size_t i = 0; i < n; ++i) {
            y[i] = x[i] + a / (double)(i + 1);
        }
    } else {
        pthread_t *thread_ids = malloc(sizeof(*thread_ids) * (size_t)threads);
        worker_args_t *args = calloc((size_t)threads, sizeof(*args));
        if (thread_ids == NULL || args == NULL) {
            fprintf(stderr, "allocation failed for snippet3 threads\n");
            free(thread_ids);
            free(args);
            free(x);
            free(y);
            free(z);
            return -1;
        }

        for (int t = 0; t < threads; ++t) {
            size_t begin = (size_t)t * n / (size_t)threads;
            size_t end = (size_t)(t + 1) * n / (size_t)threads;
            args[t].begin = begin;
            args[t].end = end;
            args[t].x = x;
            args[t].y = y;
            args[t].a_scalar = b;
        }
        if (launch_threads(threads, snippet3_first_worker, args, thread_ids) != 0) {
            free(thread_ids);
            free(args);
            free(x);
            free(y);
            free(z);
            return -1;
        }

        for (int t = 0; t < threads; ++t) {
            args[t].a_scalar = a;
        }
        if (launch_threads(threads, snippet3_second_worker, args, thread_ids) != 0) {
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

    result->snippet = "snippet3";
    result->variant = variant;
    result->threads = threads;
    result->n = n;
    result->seconds = end - start;
    result->checksum = checksum_array(y, n);
    result->aux = x[n / 2];

    free(x);
    free(y);
    free(z);
    return 0;
}

static int run_case(
    const char *snippet,
    const char *variant,
    int threads,
    size_t n,
    benchmark_result_t *result
) {
    if (threads < 1) {
        fprintf(stderr, "threads must be >= 1\n");
        return -1;
    }
    if (strcmp(snippet, "snippet1") == 0) {
        return benchmark_snippet1(variant, threads, n, result);
    }
    if (strcmp(snippet, "snippet2") == 0) {
        return benchmark_snippet2(variant, threads, n, result);
    }
    if (strcmp(snippet, "snippet3") == 0) {
        return benchmark_snippet3(variant, threads, n, result);
    }
    fprintf(stderr, "unknown snippet: %s\n", snippet);
    return -1;
}

int main(int argc, char **argv) {
    if (argc != 5) {
        fprintf(stderr, "usage: %s <snippet1|snippet2|snippet3> <original|parallel> <threads> <n>\n", argv[0]);
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
        "snippet=%s variant=%s threads=%d n=%zu seconds=%.9f checksum=%.12f aux=%.12f\n",
        result.snippet,
        result.variant,
        result.threads,
        result.n,
        result.seconds,
        result.checksum,
        result.aux
    );
    return 0;
}
