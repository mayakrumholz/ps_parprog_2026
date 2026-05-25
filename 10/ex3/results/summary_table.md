# Exercise 3 Summary

## Intrinsics Runtime Summary

| Variant | Size | Runs | Mean [s] | Stddev [s] | Min [s] | Max [s] |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| intrinsics_float | 256 | 2 | 0.000003 | 0.000000 | 0.000003 | 0.000003 |
| intrinsics_float | 2048 | 2 | 0.000020 | 0.000000 | 0.000020 | 0.000020 |

## Comparison Summary

| Size | Baseline [s] | Auto [s] | OMP SIMD [s] | Intrinsics [s] | Speedup vs baseline | Speedup vs auto | Speedup vs OMP |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 256 | 0.338855 | 0.063496 | - | 0.000003 | 112951.804 | 21165.461 | - |
| 2048 | 2.685649 | 0.510449 | 0.509245 | 0.000020 | 134282.471 | 25522.467 | 25462.233 |
