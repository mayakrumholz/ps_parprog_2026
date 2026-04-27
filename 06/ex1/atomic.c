#include <omp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define DEFAULT_SAMPLES 700000000LL

static long long parse_samples(int argc, char **argv) {
    char *endptr = NULL;
    long long samples;

    if (argc < 2) {
        return DEFAULT_SAMPLES;
    }

    samples = strtoll(argv[1], &endptr, 10);
    if (endptr == argv[1] || *endptr != '\0' || samples <= 0) {
        fprintf(stderr, "Usage: %s [positive_sample_count]\n", argv[0]);
        exit(EXIT_FAILURE);
    }

    return samples;
}

static double next_unit_random(uint32_t *state) {
    *state = (*state * 1664525u) + 1013904223u;
    return (double)(*state) / (double)UINT32_MAX;
}

int main(int argc, char **argv) {
    const long long samples = parse_samples(argc, argv);
    long long inside_circle = 0;
    double start_time;
    double end_time;
    double pi;

    start_time = omp_get_wtime();

    #pragma omp parallel default(none) shared(inside_circle) firstprivate(samples)
    {
        uint32_t seed = 0x12345678u ^ (uint32_t)(0x9e3779b9u * (unsigned)(omp_get_thread_num() + 1));

        #pragma omp for
        for (long long i = 0; i < samples; ++i) {
            const double x = next_unit_random(&seed);
            const double y = next_unit_random(&seed);

            if ((x * x) + (y * y) <= 1.0) {
                #pragma omp atomic update
                inside_circle++;
            }
        }
    }

    end_time = omp_get_wtime();
    pi = 4.0 * (double)inside_circle / (double)samples;

    printf("variant=atomic threads=%d n=%lld pi=%.12f elapsed_seconds=%.6f\n",
           omp_get_max_threads(),
           samples,
           pi,
           end_time - start_time);

    return 0;
}
