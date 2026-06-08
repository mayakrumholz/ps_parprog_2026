CC = gcc
CFLAGS ?= -std=c99 -O3 -g3
LDFLAGS ?= -lm
OMPFLAGS ?= -fopenmp

SRC := $(wildcard *.c)

.PHONY: all clean run

all: real_serial real_openmp

real_serial: $(SRC)
	$(CC) $(CFLAGS) $(SRC) $(LDFLAGS) -o $@

real_openmp: $(SRC)
	$(CC) $(CFLAGS) $(OMPFLAGS) $(SRC) $(LDFLAGS) -o $@

run: all
	@echo "Sequential original:"
	@./real_serial
	@echo
	@echo "OpenMP, OMP_NUM_THREADS=$${OMP_NUM_THREADS:-1}:"
	@./real_openmp

clean:
	rm -f real real_serial real_openmp gmon.out
