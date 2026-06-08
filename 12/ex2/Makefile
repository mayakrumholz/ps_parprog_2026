CC ?= gcc
CFLAGS ?= -std=c99 -O3 -g
OMPFLAGS ?= -fopenmp
LDLIBS = -lm

SEQ_SRC = $(wildcard original/*.c)
OMP_SRC = $(wildcard *.c)

.PHONY: all clean run-seq run-omp

all: real_seq real_omp

real_seq: $(SEQ_SRC)
	$(CC) $(CFLAGS) $^ $(LDLIBS) -o $@

real_omp: $(OMP_SRC)
	$(CC) $(CFLAGS) $(OMPFLAGS) $^ $(LDLIBS) -o $@

run-seq: real_seq
	OMP_NUM_THREADS=1 ./real_seq

run-omp: real_omp
	./real_omp

clean:
	rm -f real_seq real_omp
