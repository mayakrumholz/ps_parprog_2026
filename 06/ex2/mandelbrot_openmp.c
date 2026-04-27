#include <omp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

#define X 1280
#define Y 720
#define MAX_ITER 10000

typedef enum {
    SCHEDULE_STATIC,
    SCHEDULE_DYNAMIC,
    SCHEDULE_GUIDED,
    SCHEDULE_AUTO,
    SCHEDULE_RUNTIME
} schedule_mode_t;

static void compute_row(uint8_t image[Y][X], int py) {
    for (int px = 0; px < X; ++px) {
        double x = 0.0;
        double y = 0.0;
        const double cx = -2.5 + (3.5 * px) / (X - 1);
        const double cy = -1.0 + (2.0 * py) / (Y - 1);
        int iteration = 0;

        while ((x * x) + (y * y) <= 4.0 && iteration < MAX_ITER) {
            const double x_tmp = (x * x) - (y * y) + cx;
            y = (2.0 * x * y) + cy;
            x = x_tmp;
            ++iteration;
        }

        image[py][px] = (uint8_t)(255.0 * iteration / MAX_ITER);
    }
}

static int parse_thread_count(const char *arg) {
    char *endptr = NULL;
    const long value = strtol(arg, &endptr, 10);

    if (endptr == arg || *endptr != '\0' || value <= 0 || value > Y) {
        return -1;
    }

    return (int)value;
}

static int parse_chunk_size(const char *arg) {
    char *endptr = NULL;
    const long value = strtol(arg, &endptr, 10);

    if (endptr == arg || *endptr != '\0' || value <= 0) {
        return -1;
    }

    return (int)value;
}

static schedule_mode_t parse_schedule_mode(const char *arg) {
    if (strcmp(arg, "static") == 0) {
        return SCHEDULE_STATIC;
    }
    if (strcmp(arg, "dynamic") == 0) {
        return SCHEDULE_DYNAMIC;
    }
    if (strcmp(arg, "guided") == 0) {
        return SCHEDULE_GUIDED;
    }
    if (strcmp(arg, "auto") == 0) {
        return SCHEDULE_AUTO;
    }
    if (strcmp(arg, "runtime") == 0) {
        return SCHEDULE_RUNTIME;
    }

    return (schedule_mode_t)-1;
}

static omp_sched_t parse_runtime_schedule(const char *arg) {
    if (strcmp(arg, "static") == 0) {
        return omp_sched_static;
    }
    if (strcmp(arg, "dynamic") == 0) {
        return omp_sched_dynamic;
    }
    if (strcmp(arg, "guided") == 0) {
        return omp_sched_guided;
    }
    if (strcmp(arg, "auto") == 0) {
        return omp_sched_auto;
    }

    return (omp_sched_t)-1;
}

static const char *runtime_schedule_name(omp_sched_t schedule) {
    switch (schedule) {
        case omp_sched_static:
            return "static";
        case omp_sched_dynamic:
            return "dynamic";
        case omp_sched_guided:
            return "guided";
        case omp_sched_auto:
            return "auto";
        default:
            return "unknown";
    }
}

static void run_schedule(uint8_t image[Y][X], int thread_count, schedule_mode_t mode) {
    switch (mode) {
        case SCHEDULE_STATIC:
            #pragma omp parallel for num_threads(thread_count) schedule(static)
            for (int py = 0; py < Y; ++py) {
                compute_row(image, py);
            }
            break;
        case SCHEDULE_DYNAMIC:
            #pragma omp parallel for num_threads(thread_count) schedule(dynamic, 1)
            for (int py = 0; py < Y; ++py) {
                compute_row(image, py);
            }
            break;
        case SCHEDULE_GUIDED:
            #pragma omp parallel for num_threads(thread_count) schedule(guided, 1)
            for (int py = 0; py < Y; ++py) {
                compute_row(image, py);
            }
            break;
        case SCHEDULE_AUTO:
            #pragma omp parallel for num_threads(thread_count) schedule(auto)
            for (int py = 0; py < Y; ++py) {
                compute_row(image, py);
            }
            break;
        case SCHEDULE_RUNTIME:
            #pragma omp parallel for num_threads(thread_count) schedule(runtime)
            for (int py = 0; py < Y; ++py) {
                compute_row(image, py);
            }
            break;
    }
}

int main(int argc, char **argv) {
    const char *output_path = "mandelbrot_openmp.png";
    uint8_t image[Y][X];
    int thread_count = 1;
    int chunk_size = 1;
    schedule_mode_t mode;
    omp_sched_t runtime_schedule = omp_sched_guided;
    double start_time;
    double end_time;

    if (argc < 3 || argc > 6) {
        fprintf(stderr,
                "Usage: %s <threads> <schedule> [output.png] [runtime_schedule|chunk_size] [chunk_size]\n",
                argv[0]);
        return EXIT_FAILURE;
    }

    thread_count = parse_thread_count(argv[1]);
    mode = parse_schedule_mode(argv[2]);

    if (thread_count < 1 || (int)mode < 0) {
        fprintf(stderr, "Invalid thread count or schedule\n");
        return EXIT_FAILURE;
    }

    if (argc >= 4) {
        output_path = argv[3];
    }

    if ((mode == SCHEDULE_DYNAMIC || mode == SCHEDULE_GUIDED) && argc >= 5) {
        chunk_size = parse_chunk_size(argv[4]);
        if (chunk_size < 1) {
            fprintf(stderr, "Invalid chunk size: %s\n", argv[4]);
            return EXIT_FAILURE;
        }
    }

    if (mode == SCHEDULE_RUNTIME && argc >= 5) {
        runtime_schedule = parse_runtime_schedule(argv[4]);
        if ((int)runtime_schedule < 0) {
            fprintf(stderr, "Invalid runtime schedule: %s\n", argv[4]);
            return EXIT_FAILURE;
        }
    }

    if (mode == SCHEDULE_RUNTIME && argc >= 6) {
        chunk_size = parse_chunk_size(argv[5]);
        if (chunk_size < 1) {
            fprintf(stderr, "Invalid chunk size: %s\n", argv[5]);
            return EXIT_FAILURE;
        }
    }

    if (mode == SCHEDULE_RUNTIME) {
        omp_set_schedule(runtime_schedule, chunk_size);
    }

    start_time = omp_get_wtime();
    run_schedule(image, thread_count, mode);
    end_time = omp_get_wtime();

    if (stbi_write_png(output_path, X, Y, 1, image, 0) == 0) {
        fprintf(stderr, "Failed to write image: %s\n", output_path);
        return EXIT_FAILURE;
    }

    if (mode == SCHEDULE_RUNTIME) {
        printf("variant=runtime_%s", runtime_schedule_name(runtime_schedule));
    } else {
        printf("variant=%s", argv[2]);
    }
    printf(" threads=%d chunk=%d elapsed_seconds=%.6f image=%s\n",
           thread_count,
           chunk_size,
           end_time - start_time,
           output_path);

    return EXIT_SUCCESS;
}
