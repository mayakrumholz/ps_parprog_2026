CC = gcc-15
CFLAGS = -std=gnu11 -Wall -Wextra -Werror -O2 -ftree-vectorize -fopt-info-vec-all-internals

.PHONY: all clean

all: analysis

analysis: analysis.c
	$(CC) $(CFLAGS) -o analysis analysis.c

clean:
	$(RM) analysis