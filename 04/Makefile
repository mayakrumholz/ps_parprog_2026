CFLAGS = -std=gnu11 -Wall -Wextra -O2
LDLIBS = -lm -pthread

.PHONY: all clean

all: mandelbrot_pthreads

mandelbrot_pthreads: mandelbrot_pthreads.c

clean:
	$(RM) mandelbrot_pthreads mandelbrot_pthreads.png
	$(RM) benchmark_results.csv
	$(RM) -r results images
