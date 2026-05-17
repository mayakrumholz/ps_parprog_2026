#include <omp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef enum {
    MODE_SEQ = 0,
    MODE_TASK = 1
} mode_t;

static const unsigned long long known_delannoy[] = {
    1ULL,
    3ULL,
    13ULL,
    63ULL,
    321ULL,
    1683ULL,
    8989ULL,
    48639ULL,
    265729ULL,
    1462563ULL,
    8097453ULL,
    45046719ULL,
    251595969ULL,
    1409933619ULL,
    7923848253ULL,
    44642381823ULL
};

static int parse_mode(const char *text, mode_t *mode) {
    if (strcmp(text, "seq") == 0) {
        *mode = MODE_SEQ;
        return 1;
    }
    if (strcmp(text, "task") == 0) {
        *mode = MODE_TASK;
        return 1;
    }
    return 0;
}

static unsigned long long delannoy_seq(int m, int n) {
    if (m == 0 || n == 0) {
        return 1ULL;
    }

    return delannoy_seq(m - 1, n)
        + delannoy_seq(m - 1, n - 1)
        + delannoy_seq(m, n - 1);
}

static unsigned long long delannoy_task_cutoff(int m, int n, int cutoff) {
    if (m == 0 || n == 0) {
        return 1ULL;
    }

    if (m + n <= cutoff) {
        return delannoy_seq(m, n);
    }

    unsigned long long a = 0ULL;
    unsigned long long b = 0ULL;
    unsigned long long c = 0ULL;

    #pragma omp task shared(a) firstprivate(m, n, cutoff)
    a = delannoy_task_cutoff(m - 1, n, cutoff);

    #pragma omp task shared(b) firstprivate(m, n, cutoff)
    b = delannoy_task_cutoff(m - 1, n - 1, cutoff);

    #pragma omp task shared(c) firstprivate(m, n, cutoff)
    c = delannoy_task_cutoff(m, n - 1, cutoff);

    #pragma omp taskwait
    return a + b + c;
}

static unsigned long long delannoy_task(int n, int cutoff) {
    unsigned long long result = 0ULL;

    #pragma omp parallel
    {
        #pragma omp single
        result = delannoy_task_cutoff(n, n, cutoff);
    }

    return result;
}

int main(int argc, char **argv) {
    int n = 0;
    int cutoff = 8;
    mode_t mode = MODE_SEQ;

    if (argc < 3 || argc > 4) {
        fprintf(stderr, "Usage: %s <seq|task> <N> [cutoff]\n", argv[0]);
        return EXIT_FAILURE;
    }

    if (!parse_mode(argv[1], &mode)) {
        fprintf(stderr, "Unknown mode '%s'. Use seq or task.\n", argv[1]);
        return EXIT_FAILURE;
    }

    n = atoi(argv[2]);
    if (n < 0) {
        fprintf(stderr, "N must be non-negative.\n");
        return EXIT_FAILURE;
    }

    if (argc == 4) {
        cutoff = atoi(argv[3]);
        if (cutoff < 0) {
            fprintf(stderr, "cutoff must be non-negative.\n");
            return EXIT_FAILURE;
        }
    }

    double start = omp_get_wtime();
    unsigned long long result = 0ULL;

    if (mode == MODE_SEQ) {
        result = delannoy_seq(n, n);
    } else {
        result = delannoy_task(n, cutoff);
    }

    double end = omp_get_wtime();
    unsigned long long expected = 0ULL;
    int expected_known = 0;

    if (n >= 0 && n < (int)(sizeof(known_delannoy) / sizeof(known_delannoy[0]))) {
        expected = known_delannoy[n];
        expected_known = 1;
    }

    printf(
        "mode=%s n=%d cutoff=%d threads=%d result=%llu expected=%llu expected_known=%d elapsed_seconds=%.6f\n",
        mode == MODE_SEQ ? "seq" : "task",
        n,
        cutoff,
        omp_get_max_threads(),
        result,
        expected,
        expected_known,
        end - start);

    if (expected_known && result != expected) {
        fprintf(stderr, "Wrong result for N=%d: got %llu, expected %llu.\n", n, result, expected);
        return EXIT_FAILURE;
    }

    return EXIT_SUCCESS;
}
