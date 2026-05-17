CC = gcc
CFLAGS = -O3 -Wall -Wextra -std=c11 -fopenmp
TARGET = first_touch

.PHONY: all clean

all: $(TARGET)

$(TARGET): first_touch.c
	$(CC) $(CFLAGS) -o $(TARGET) first_touch.c

clean:
	rm -f $(TARGET)
