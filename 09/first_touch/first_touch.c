#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef enum {
    INIT_SERIAL = 0,
    INIT_PARALLEL = 1
} init_mode_t;

typedef enum {
    SCHED_STATIC = 0,
    SCHED_DYNAMIC = 1,
    SCHED_GUIDED = 2
} schedule_kind_t;

static int parse_init_mode(const char *text, init_mode_t *mode) {
    if (strcmp(text, "serial") == 0) {
        *mode = INIT_SERIAL;
        return 1;
    }
    if (strcmp(text, "parallel") == 0) {
        *mode = INIT_PARALLEL;
        return 1;
    }
    return 0;
}

static int parse_schedule_kind(const char *text, schedule_kind_t *kind) {
    if (strcmp(text, "static") == 0) {
        *kind = SCHED_STATIC;
        return 1;
    }
    if (strcmp(text, "dynamic") == 0) {
        *kind = SCHED_DYNAMIC;
        return 1;
    }
    if (strcmp(text, "guided") == 0) {
        *kind = SCHED_GUIDED;
        return 1;
    }
    return 0;
}

static omp_sched_t to_omp_schedule(schedule_kind_t kind) {
    switch (kind) {
        case SCHED_STATIC:
            return omp_sched_static;
        case SCHED_DYNAMIC:
            return omp_sched_dynamic;
        case SCHED_GUIDED:
            return omp_sched_guided;
    }

    return omp_sched_static;
}

static long long expected_sum(int n) {
    long long nn = (long long)n;
    return nn * nn * (nn - 1);
}

int main(int argc, char **argv) {
    int n = 1000;
    init_mode_t init_mode = INIT_PARALLEL;
    schedule_kind_t schedule_kind = SCHED_STATIC;

    if (argc != 4) {
        fprintf(stderr, "Usage: %s <N> <serial|parallel> <static|dynamic|guided>\n", argv[0]);
        return EXIT_FAILURE;
    }

    n = atoi(argv[1]);
    if (n <= 0) {
        fprintf(stderr, "N must be positive.\n");
        return EXIT_FAILURE;
    }

    if (!parse_init_mode(argv[2], &init_mode)) {
        fprintf(stderr, "Unknown init mode '%s'. Use serial or parallel.\n", argv[2]);
        return EXIT_FAILURE;
    }

    if (!parse_schedule_kind(argv[3], &schedule_kind)) {
        fprintf(stderr, "Unknown schedule '%s'. Use static, dynamic or guided.\n", argv[3]);
        return EXIT_FAILURE;
    }

    omp_set_schedule(to_omp_schedule(schedule_kind), 1);

    double allocation_seconds = 0.0;
    double initialization_seconds = 0.0;
    double computation_seconds = 0.0;
    double deallocation_seconds = 0.0;

    double start_time = omp_get_wtime();
    long long **matrix = (long long **)malloc((size_t)n * sizeof(*matrix));
    long long *data = (long long *)malloc((size_t)n * (size_t)n * sizeof(*data));
    double end_time = omp_get_wtime();
    allocation_seconds = end_time - start_time;

    if (matrix == NULL || data == NULL) {
        free(matrix);
        free(data);
        fprintf(stderr, "Memory allocation failed for N=%d.\n", n);
        return EXIT_FAILURE;
    }

    for (int i = 0; i < n; ++i) {
        matrix[i] = data + (size_t)i * (size_t)n;
    }

    start_time = omp_get_wtime();
    if (init_mode == INIT_PARALLEL) {
        #pragma omp parallel for schedule(runtime)
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                matrix[i][j] = (long long)i + (long long)j;
            }
        }
    } else {
        for (int i = 0; i < n; ++i) {
            for (int j = 0; j < n; ++j) {
                matrix[i][j] = (long long)i + (long long)j;
            }
        }
    }
    end_time = omp_get_wtime();
    initialization_seconds = end_time - start_time;

    long long sum = 0;
    start_time = omp_get_wtime();
    #pragma omp parallel for reduction(+ : sum) schedule(runtime)
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            sum += matrix[i][j];
        }
    }
    end_time = omp_get_wtime();
    computation_seconds = end_time - start_time;

    start_time = omp_get_wtime();
    free(data);
    free(matrix);
    end_time = omp_get_wtime();
    deallocation_seconds = end_time - start_time;

    printf(
        "n=%d init_mode=%s schedule=%s threads=%d allocation_seconds=%.6f "
        "initialization_seconds=%.6f computation_seconds=%.6f deallocation_seconds=%.6f "
        "sum=%lld expected_sum=%lld\n",
        n,
        init_mode == INIT_PARALLEL ? "parallel" : "serial",
        argv[3],
        omp_get_max_threads(),
        allocation_seconds,
        initialization_seconds,
        computation_seconds,
        deallocation_seconds,
        sum,
        expected_sum(n));

    return (sum == expected_sum(n)) ? EXIT_SUCCESS : EXIT_FAILURE;
}
