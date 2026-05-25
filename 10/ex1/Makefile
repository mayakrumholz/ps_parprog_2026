CC = gcc
COMMON_CFLAGS = -std=c11 -Wall -Wextra -Wpedantic -O1
LDFLAGS ?=
LDLIBS ?= -lm
REPORT_DIR = report/raw

.PHONY: all clean check reports

all: baseline auto_vectorized

baseline: vector_add.c | $(REPORT_DIR)
	$(CC) $(COMMON_CFLAGS) -fno-tree-vectorize -DVARIANT_NAME=\"baseline\" $< -o $@ $(LDFLAGS) $(LDLIBS)

auto_vectorized: vector_add.c | $(REPORT_DIR)
	$(CC) $(COMMON_CFLAGS) -ftree-vectorize -DVARIANT_NAME=\"auto_vectorized\" $< -o $@ $(LDFLAGS) $(LDLIBS)

reports: | $(REPORT_DIR)
	@if printf 'int main(void) { return 0; }\n' | $(CC) -x c - -o /tmp/vector_add_report_probe -fopt-info-vec-all >/dev/null 2>&1; then \
		$(CC) $(COMMON_CFLAGS) -fno-tree-vectorize -fopt-info-vec-all -DVARIANT_NAME=\"baseline\" vector_add.c -o /tmp/vector_add_baseline_report $(LDFLAGS) $(LDLIBS) 2> $(REPORT_DIR)/baseline_vec_report.txt; \
		$(CC) $(COMMON_CFLAGS) -ftree-vectorize -fopt-info-vec-all -DVARIANT_NAME=\"auto_vectorized\" vector_add.c -o /tmp/vector_add_auto_report $(LDFLAGS) $(LDLIBS) 2> $(REPORT_DIR)/auto_vec_report.txt; \
	else \
		printf '%s\n' 'Compiler in this environment does not support -fopt-info-vec-all. Run this target on LCC3 with GCC 12.2.0.' > $(REPORT_DIR)/baseline_vec_report.txt; \
		printf '%s\n' 'Compiler in this environment does not support -fopt-info-vec-all. Run this target on LCC3 with GCC 12.2.0.' > $(REPORT_DIR)/auto_vec_report.txt; \
	fi
	rm -f /tmp/vector_add_report_probe /tmp/vector_add_baseline_report /tmp/vector_add_auto_report

check: all
	./baseline 16 8
	./auto_vectorized 16 8

clean:
	rm -f baseline auto_vectorized
	rm -f $(REPORT_DIR)/baseline_vec_report.txt $(REPORT_DIR)/auto_vec_report.txt

$(REPORT_DIR):
	mkdir -p $(REPORT_DIR)
