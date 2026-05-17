#include <stdio.h>
#include <stdlib.h>
#include <omp.h>

int main(int argc, char** argv) {

    int N = 1000;

    if (argc != 2) {
        printf("Usage: %s <N>\n", argv[0]);
        return EXIT_FAILURE;
    }

    N = atoi(argv[1]);

    long long **matrix;
    double start_time, end_time;

    // Allocate memory for the 2D array
    start_time = omp_get_wtime();
    matrix = (long long **)malloc(N * sizeof(long long *));
    for (int i = 0; i < N; i++) {
        matrix[i] = (long long *)malloc(N * sizeof(long long));
    }
    end_time = omp_get_wtime();
    printf("Memory allocation time: %f seconds\n", end_time - start_time);

    // Initialize the matrix using OpenMP parallel for
    start_time = omp_get_wtime();
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            matrix[i][j] = i + j;
        }
    }
    end_time = omp_get_wtime();
    printf("Matrix initialization time: %f seconds\n", end_time - start_time);

    // Perform a computation on the matrix
    long long sum = 0.0;
    start_time = omp_get_wtime();
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            sum += matrix[i][j];
        }
    }
    end_time = omp_get_wtime();
    printf("Matrix computation time: %f seconds\n", end_time - start_time);

    printf("Sum of matrix elements: %lld\n", sum);

    // Free the allocated memory
    start_time = omp_get_wtime();
    for (int i = 0; i < N; i++) {
        free(matrix[i]);
    }
    free(matrix);
    end_time = omp_get_wtime();
    printf("Memory deallocation time: %f seconds\n", end_time - start_time);

    return EXIT_SUCCESS;
}
