CC = gcc
COMMON_CFLAGS = -std=c11 -Wall -Wextra -Wpedantic -O1
LDFLAGS ?=
LDLIBS ?= -lm
REPORT_DIR = report/raw

.PHONY: all clean check reports

all: baseline_float auto_float omp_simd_float baseline_double omp_simd_double

baseline_float: vector_add_typed.c | $(REPORT_DIR)
	$(CC) $(COMMON_CFLAGS) -fno-tree-vectorize -DVARIANT_NAME=\"baseline_float\" -DTYPE_NAME=\"float\" -DDATA_TYPE=float $< -o $@ $(LDFLAGS) $(LDLIBS)

auto_float: vector_add_typed.c | $(REPORT_DIR)
	$(CC) $(COMMON_CFLAGS) -ftree-vectorize -DVARIANT_NAME=\"auto_float\" -DTYPE_NAME=\"float\" -DDATA_TYPE=float $< -o $@ $(LDFLAGS) $(LDLIBS)

omp_simd_float: vector_add_typed.c | $(REPORT_DIR)
	$(CC) $(COMMON_CFLAGS) -fopenmp-simd -fno-tree-vectorize -DUSE_OMP_SIMD -DVARIANT_NAME=\"omp_simd_float\" -DTYPE_NAME=\"float\" -DDATA_TYPE=float $< -o $@ $(LDFLAGS) $(LDLIBS)

baseline_double: vector_add_typed.c | $(REPORT_DIR)
	$(CC) $(COMMON_CFLAGS) -fno-tree-vectorize -DVARIANT_NAME=\"baseline_double\" -DTYPE_NAME=\"double\" -DDATA_TYPE=double $< -o $@ $(LDFLAGS) $(LDLIBS)

omp_simd_double: vector_add_typed.c | $(REPORT_DIR)
	$(CC) $(COMMON_CFLAGS) -fopenmp-simd -fno-tree-vectorize -DUSE_OMP_SIMD -DVARIANT_NAME=\"omp_simd_double\" -DTYPE_NAME=\"double\" -DDATA_TYPE=double $< -o $@ $(LDFLAGS) $(LDLIBS)

reports: | $(REPORT_DIR)
	@if printf 'int main(void) { return 0; }\n' | $(CC) -x c - -o /tmp/vector_add_ex2_probe -fopt-info-vec-all >/dev/null 2>&1; then \
		$(CC) $(COMMON_CFLAGS) -fopenmp-simd -fno-tree-vectorize -DUSE_OMP_SIMD -DVARIANT_NAME=\"omp_simd_float\" -DTYPE_NAME=\"float\" -DDATA_TYPE=float vector_add_typed.c -o /tmp/vector_add_ex2_report $(LDFLAGS) $(LDLIBS) 2> $(REPORT_DIR)/omp_simd_float_vec_report.txt; \
		$(CC) $(COMMON_CFLAGS) -fno-tree-vectorize -DVARIANT_NAME=\"baseline_float\" -DTYPE_NAME=\"float\" -DDATA_TYPE=float vector_add_typed.c -o /tmp/vector_add_ex2_baseline_report $(LDFLAGS) $(LDLIBS) 2> $(REPORT_DIR)/baseline_float_vec_report.txt; \
	else \
		printf '%s\n' 'Compiler in this environment does not support -fopt-info-vec-all. Run this target on LCC3 with GCC 12.2.0.' > $(REPORT_DIR)/omp_simd_float_vec_report.txt; \
		printf '%s\n' 'Compiler in this environment does not support -fopt-info-vec-all. Run this target on LCC3 with GCC 12.2.0.' > $(REPORT_DIR)/baseline_float_vec_report.txt; \
	fi
	rm -f /tmp/vector_add_ex2_probe /tmp/vector_add_ex2_report /tmp/vector_add_ex2_baseline_report

check: all
	./baseline_float 16 8
	./auto_float 16 8
	./omp_simd_float 16 8
	./baseline_double 16 8
	./omp_simd_double 16 8

clean:
	rm -f baseline_float auto_float omp_simd_float baseline_double omp_simd_double
	rm -f $(REPORT_DIR)/omp_simd_float_vec_report.txt $(REPORT_DIR)/baseline_float_vec_report.txt

$(REPORT_DIR):
	mkdir -p $(REPORT_DIR)
