# Exercise 2 Summary

## Runtime Summary

| Variant | Type | Runs | Mean [s] | Stddev [s] | Min [s] | Max [s] |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| auto_float | float | 5 | 0.508945 | 0.001478 | 0.507906 | 0.511270 |
| baseline_double | double | 5 | 2.690833 | 0.008255 | 2.682271 | 2.702852 |
| baseline_float | float | 5 | 2.684614 | 0.003729 | 2.682571 | 2.691268 |
| omp_simd_double | double | 5 | 1.793308 | 0.008479 | 1.783826 | 1.804041 |
| omp_simd_float | float | 5 | 0.509245 | 0.001169 | 0.508043 | 0.510922 |

## Speedup Summary

| Comparison | Reference | Candidate | Speedup |
| --- | --- | --- | ---: |
| float auto vs baseline | baseline_float | auto_float | 5.275 |
| float omp simd vs baseline | baseline_float | omp_simd_float | 5.272 |
| float omp simd vs auto | auto_float | omp_simd_float | 0.999 |
| double omp simd vs baseline | baseline_double | omp_simd_double | 1.500 |
