CC ?= gcc
CFLAGS ?= -std=c11 -O3 -Wall -Wextra -Werror -fopenmp
LDLIBS ?= -lm

.PHONY: all clean check

all: ex2_benchmark

ex2_benchmark: ex2_benchmark.c

check: ex2_benchmark
	./ex2_benchmark verify

clean:
	$(RM) ex2_benchmark
