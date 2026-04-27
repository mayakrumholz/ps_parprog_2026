CC = gcc
CFLAGS = -std=gnu11 -Wall -Wextra -Werror -O3 -fopenmp
LDLIBS = -lm

.PHONY: all clean

PROGRAMS = serial critical atomic reduction

all: $(PROGRAMS)

clean:
	$(RM) $(PROGRAMS)

serial: serial.c
critical: critical.c
atomic: atomic.c
reduction: reduction.c
