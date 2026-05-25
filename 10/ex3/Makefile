CC = gcc
COMMON_CFLAGS = -std=c11 -Wall -Wextra -Wpedantic -O1 -fno-tree-vectorize
LDFLAGS ?=
LDLIBS ?= -lm
REPORT_DIR = report/raw

.PHONY: all clean check reports

all: intrinsics_float

intrinsics_float: vector_add_intrinsics.c | $(REPORT_DIR)
	$(CC) $(COMMON_CFLAGS) -msse -DVARIANT_NAME=\"intrinsics_float\" $< -o $@ $(LDFLAGS) $(LDLIBS)

reports: | $(REPORT_DIR)
	objdump -d intrinsics_float > $(REPORT_DIR)/intrinsics_float_disassembly.txt

check: all
	./intrinsics_float 16 8

clean:
	rm -f intrinsics_float
	rm -f $(REPORT_DIR)/intrinsics_float_disassembly.txt

$(REPORT_DIR):
	mkdir -p $(REPORT_DIR)
