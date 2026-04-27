CC = gcc
CFLAGS = -std=gnu11 -Wall -Wextra -Werror -O3 -fopenmp
LDLIBS = -lm

.PHONY: all clean

all: mandelbrot_openmp

mandelbrot_openmp: mandelbrot_openmp.c

clean:
	$(RM) mandelbrot_openmp
