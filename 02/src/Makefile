CC = gcc-15
CFLAGS = -fopenmp

TARGETS = slow medium fast

all: $(TARGETS)

slow: slow.c
	$(CC) $(CFLAGS) -o slow slow.c

medium: medium.c
	$(CC) $(CFLAGS) -o medium medium.c

fast: fast.c
	$(CC) $(CFLAGS) -o fast fast.c

clean:
	rm -f $(TARGETS)
