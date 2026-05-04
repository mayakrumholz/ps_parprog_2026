CC ?= cc
CFLAGS = -std=c11 -O3 -Wall -Wextra -Werror -pedantic
LDFLAGS =
LDLIBS = -pthread

.PHONY: all clean run analyze

all: benchmark

benchmark: benchmark.c
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $< $(LDLIBS)

run: benchmark
	python3 run_benchmarks.py

analyze:
	python3 analyze_results.py

clean:
	$(RM) benchmark
