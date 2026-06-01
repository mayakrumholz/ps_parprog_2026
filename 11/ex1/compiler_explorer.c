#include <stdint.h>
#include <string.h>

unsigned original_a(unsigned c1) {
    return 32 * c1;
}

unsigned transformed_a(unsigned c1) {
    return c1 << 5;
}

unsigned original_b(unsigned c1) {
    return 15 * c1;
}

unsigned transformed_b(unsigned c1) {
    return (c1 << 4) - c1;
}

unsigned original_c(unsigned c1) {
    return 96 * c1;
}

unsigned transformed_c(unsigned c1) {
    return (c1 + (c1 << 1)) << 5;
}

unsigned original_d(unsigned c1) {
    return 0.125 * c1;
}

unsigned transformed_d(unsigned c1) {
    return c1 >> 3;
}

unsigned original_e(const unsigned *a, int n) {
    unsigned sum_fifth = 0;

    for (int i = 0; i < n / 5; ++i) {
        sum_fifth += a[5 * i];
    }

    return sum_fifth;
}

unsigned transformed_e(const unsigned *a, int n) {
    unsigned sum_fifth = 0;
    const unsigned *current = a;

    for (int i = 0; i < n / 5; ++i) {
        sum_fifth += *current;
        current += 5;
    }

    return sum_fifth;
}

void original_f(double *a, int n) {
    for (int i = 0; i < n; ++i) {
        a[i] += i / 5.3;
    }
}

void transformed_f(double *a, int n) {
    double quotient = 0.0;
    const double step = 1.0 / 5.3;

    for (int i = 0; i < n; ++i) {
        a[i] += quotient;
        quotient += step;
    }
}

float original_g(float c1) {
    return -1 * c1;
}

float transformed_g(float c1) {
    uint32_t bits;

    memcpy(&bits, &c1, sizeof(bits));
    bits ^= UINT32_C(0x80000000);
    memcpy(&c1, &bits, sizeof(c1));

    return c1;
}
