CC = gcc
CFLAGS = -O3 -Wall -Wextra -std=c11 -fopenmp
TARGET = delannoy

.PHONY: all clean

all: $(TARGET)

$(TARGET): delannoy.c
	$(CC) $(CFLAGS) -o $(TARGET) delannoy.c

clean:
	rm -f $(TARGET)
