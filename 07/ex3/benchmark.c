#include <errno.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef struct {
    size_t rows;
    size_t cols;
    size_t parity;
    double b;
    double *matrix;
} worker_args_t;

typedef struct {
    const char *variant;
    int threads;
    size_t rows;
    size_t cols;
    double seconds;
    double checksum;
    double aux;
} benchmark_result_t;

static double now_seconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

static size_t index_of(size_t cols, size_t row, size_t col) {
    return row * cols + col;
}

static void initialize_matrix(double *matrix, size_t rows, size_t cols) {
    for (size_t i = 0; i < rows; ++i) {
        for (size_t j = 0; j < cols; ++j) {
            matrix[index_of(cols, i, j)] = 0.25 + (double)(((i * 37u) + (j * 19u)) % 1024u) / 128.0;
        }
    }
}

static double checksum_matrix(const double *matrix, size_t rows, size_t cols) {
    const size_t elements = rows * cols;
    double sum = 0.0;
    for (size_t i = 0; i < elements; ++i) {
        sum += matrix[i];
    }
    return sum;
}

static void *parity_worker(void *opaque) {
    worker_args_t *args = (worker_args_t *)opaque;
    for (size_t i = args->parity; i + 2 < args->rows; i += 2) {
        for (size_t j = 1; j < args->cols; ++j) {
            args->matrix[index_of(args->cols, i + 2, j - 1)] =
                args->b * args->matrix[index_of(args->cols, i, j)] + 4.0;
        }
    }
    return NULL;
}

static int run_case(const char *variant, int threads, size_t rows, size_t cols, benchmark_result_t *result) {
    double *matrix = malloc(sizeof(*matrix) * rows * cols);
    if (matrix == NULL) {
        fprintf(stderr, "allocation failed for matrix\n");
        return -1;
    }

    initialize_matrix(matrix, rows, cols);
    const double b = 0.75;

    const double start = now_seconds();
    if (strcmp(variant, "original") == 0) {
        for (size_t i = 0; i + 2 < rows; ++i) {
            for (size_t j = 1; j < cols; ++j) {
                matrix[index_of(cols, i + 2, j - 1)] = b * matrix[index_of(cols, i, j)] + 4.0;
            }
        }
    } else {
        pthread_t thread_ids[2];
        worker_args_t args[2];
        const int worker_count = threads >= 2 ? 2 : 1;
        for (int t = 0; t < worker_count; ++t) {
            args[t].rows = rows;
            args[t].cols = cols;
            args[t].parity = (size_t)t;
            args[t].b = b;
            args[t].matrix = matrix;
        }

        if (worker_count == 1) {
            parity_worker(&args[0]);
            args[0].parity = 1;
            parity_worker(&args[0]);
        } else {
            for (int t = 0; t < worker_count; ++t) {
                int rc = pthread_create(&thread_ids[t], NULL, parity_worker, &args[t]);
                if (rc != 0) {
                    fprintf(stderr, "pthread_create failed: %s\n", strerror(rc));
                    free(matrix);
                    return -1;
                }
            }
            for (int t = 0; t < worker_count; ++t) {
                int rc = pthread_join(thread_ids[t], NULL);
                if (rc != 0) {
                    fprintf(stderr, "pthread_join failed: %s\n", strerror(rc));
                    free(matrix);
                    return -1;
                }
            }
        }
    }
    const double end = now_seconds();

    result->variant = variant;
    result->threads = strcmp(variant, "parallel") == 0 ? (threads >= 2 ? 2 : 1) : 1;
    result->rows = rows;
    result->cols = cols;
    result->seconds = end - start;
    result->checksum = checksum_matrix(matrix, rows, cols);
    result->aux = matrix[index_of(cols, rows / 2, cols / 2)];
    free(matrix);
    return 0;
}

int main(int argc, char **argv) {
    if (argc != 5) {
        fprintf(stderr, "usage: %s <original|parallel> <threads> <rows> <cols>\n", argv[0]);
        return 1;
    }

    char *endptr = NULL;
    errno = 0;
    const long threads_long = strtol(argv[2], &endptr, 10);
    if (errno != 0 || endptr == argv[2] || *endptr != '\0' || threads_long < 1 || threads_long > 32) {
        fprintf(stderr, "invalid thread count: %s\n", argv[2]);
        return 1;
    }

    errno = 0;
    const unsigned long long rows_value = strtoull(argv[3], &endptr, 10);
    if (errno != 0 || endptr == argv[3] || *endptr != '\0' || rows_value < 4ull) {
        fprintf(stderr, "invalid rows: %s\n", argv[3]);
        return 1;
    }

    errno = 0;
    const unsigned long long cols_value = strtoull(argv[4], &endptr, 10);
    if (errno != 0 || endptr == argv[4] || *endptr != '\0' || cols_value < 4ull) {
        fprintf(stderr, "invalid cols: %s\n", argv[4]);
        return 1;
    }

    benchmark_result_t result;
    if (run_case(argv[1], (int)threads_long, (size_t)rows_value, (size_t)cols_value, &result) != 0) {
        return 1;
    }

    printf(
        "variant=%s threads=%d rows=%zu cols=%zu seconds=%.9f checksum=%.12f aux=%.12f\n",
        result.variant,
        result.threads,
        result.rows,
        result.cols,
        result.seconds,
        result.checksum,
        result.aux
    );
    return 0;
}
