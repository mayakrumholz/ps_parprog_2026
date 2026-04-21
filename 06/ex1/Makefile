CFLAGS = -std=gnu11 -Wall -Werror -Wextra -fopenmp -O3

.PHONY: all
all: serial atomic critical reduction

.PHONY: clean
clean:
	$(RM) serial atomic critical reduction

serial: serial.c

atomic: atomic.c

critical: critical.c

reduction: reduction.c