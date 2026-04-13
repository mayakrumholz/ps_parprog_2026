#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <time.h>

static inline void hadamard_col_major(size_t n, int32_t *a, int32_t *b, int32_t *c) {
    for (size_t j = 0; j < n; ++j) {
        for (size_t i = 0; i < n; ++i) {
            c[i * n + j] = a[i * n + j] * b[i * n + j];
        }
    }
}

static inline void hadamard_row_major(size_t n, int32_t *a, int32_t *b, int32_t *c) {
    for (size_t i = 0; i < n; ++i) {
        for (size_t j = 0; j < n; ++j) {
            c[i * n + j] = a[i * n + j] * b[i * n + j];
        }
    }
}

void init_matrix(size_t n, int32_t *m) {
    for (size_t i = 0; i < n * n; ++i) {
        m[i] = (int32_t)(i % 100);
    }
}

long long checksum(size_t n, int32_t *m) {
    long long sum = 0;
    for (size_t i = 0; i < n * n; ++i) {
        sum += m[i];
    }
    return sum;
}

int main(int argc, char **argv) {
    if (argc < 3) {
        fprintf(stderr, "Usage: %s <n> <mode>\n", argv[0]);
        fprintf(stderr, "mode = 0 -> col-major style (j outer, i inner)\n");
        fprintf(stderr, "mode = 1 -> row-major style (i outer, j inner)\n");
        return 1;
    }

    size_t n = (size_t)atoll(argv[1]);
    int mode = atoi(argv[2]);

    int32_t *a = aligned_alloc(64, n * n * sizeof(int32_t));
    int32_t *b = aligned_alloc(64, n * n * sizeof(int32_t));
    int32_t *c = aligned_alloc(64, n * n * sizeof(int32_t));

    if (!a || !b || !c) {
        perror("alloc");
        return 1;
    }

    init_matrix(n, a);
    init_matrix(n, b);

    if (mode == 0) {
        hadamard_col_major(n, a, b, c);
    } else {
        hadamard_row_major(n, a, b, c);
    }

    printf("checksum = %lld\n", checksum(n, c));

    free(a);
    free(b);
    free(c);
    return 0;
}