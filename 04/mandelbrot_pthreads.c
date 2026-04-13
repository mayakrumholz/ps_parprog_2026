#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

#define X 1280
#define Y 720
#define MAX_ITER 10000

typedef struct {
    uint8_t (*image)[X];
    int start_row;
    int end_row;
} worker_args_t;

static void *calc_rows(void *arg) {
    worker_args_t *args = (worker_args_t *)arg;

    for (int py = args->start_row; py < args->end_row; ++py) {
        for (int px = 0; px < X; ++px) {
            double x = 0.0;
            double y = 0.0;
            double cx = -2.5 + (3.5 * px) / (X - 1);
            double cy = -1.0 + (2.0 * py) / (Y - 1);
            int iteration = 0;

            while (x * x + y * y <= 4.0 && iteration < MAX_ITER) {
                double x_tmp = x * x - y * y + cx;
                y = 2.0 * x * y + cy;
                x = x_tmp;
                ++iteration;
            }

            args->image[py][px] = (uint8_t)(255.0 * iteration / MAX_ITER);
        }
    }

    return NULL;
}

static int parse_thread_count(const char *arg) {
    char *endptr = NULL;
    long value = strtol(arg, &endptr, 10);

    if (endptr == arg || *endptr != '\0' || value <= 0 || value > Y) {
        return -1;
    }

    return (int)value;
}

int main(int argc, char **argv) {
    const char *output_path = "mandelbrot_pthreads.png";
    int thread_count = 1;
    uint8_t image[Y][X];

    if (argc >= 2) {
        thread_count = parse_thread_count(argv[1]);
        if (thread_count < 1) {
            fprintf(stderr, "Invalid thread count: %s\n", argv[1]);
            return EXIT_FAILURE;
        }
    }

    if (argc >= 3) {
        output_path = argv[2];
    }

    pthread_t *threads = malloc((size_t)thread_count * sizeof(*threads));
    worker_args_t *args = malloc((size_t)thread_count * sizeof(*args));

    if (threads == NULL || args == NULL) {
        fprintf(stderr, "Allocation failed\n");
        free(threads);
        free(args);
        return EXIT_FAILURE;
    }

    for (int t = 0; t < thread_count; ++t) {
        int start_row = (t * Y) / thread_count;
        int end_row = ((t + 1) * Y) / thread_count;

        args[t].image = image;
        args[t].start_row = start_row;
        args[t].end_row = end_row;

        if (pthread_create(&threads[t], NULL, calc_rows, &args[t]) != 0) {
            fprintf(stderr, "pthread_create failed for thread %d\n", t);
            free(threads);
            free(args);
            return EXIT_FAILURE;
        }
    }

    for (int t = 0; t < thread_count; ++t) {
        if (pthread_join(threads[t], NULL) != 0) {
            fprintf(stderr, "pthread_join failed for thread %d\n", t);
            free(threads);
            free(args);
            return EXIT_FAILURE;
        }
    }

    if (stbi_write_png(output_path, X, Y, 1, image, 0) == 0) {
        fprintf(stderr, "Failed to write image: %s\n", output_path);
        free(threads);
        free(args);
        return EXIT_FAILURE;
    }

    free(threads);
    free(args);
    return EXIT_SUCCESS;
}
