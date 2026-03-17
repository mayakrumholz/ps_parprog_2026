#include <omp.h>
#include <stdio.h>
#include <stdlib.h>

#define MAX_NUM_THREADS 16

int main(int argc, char **argv) {

    if (argc != 2) {
        printf("Usage: %s <problem_size>\n", argv[0]);
        return EXIT_FAILURE;
    }

    int problem_size = atoll(argv[1]);

    double start, end;
    int* volatile sum = (int*)calloc(MAX_NUM_THREADS, sizeof(int));

    start = omp_get_wtime();

    #pragma omp parallel
    {
        int tid = omp_get_thread_num();
        for (int i = 0; i < problem_size; i++) {
            sum[tid]++;
        }
    }

    end = omp_get_wtime();

    int total_sum = 0;
    for (int i = 0; i < MAX_NUM_THREADS; i++) {
        total_sum += sum[i];
    }

    printf("Total sum: %d\n", total_sum);
    printf("Time taken: %f seconds\n", end - start);

    free(sum);

    return EXIT_SUCCESS;
}
