#!/bin/sh

set -eu

echo "Use job.sh for timed benchmark runs with /usr/bin/time -p."
echo "This helper only builds the program and generates one image per thread count."

THREADS="1 2 4 8 12"
IMAGES_DIR="${1:-images}"

mkdir -p "$IMAGES_DIR"
make

for thread_count in $THREADS; do
    ./mandelbrot_pthreads "$thread_count" "${IMAGES_DIR}/mandelbrot_${thread_count}.png"
done

printf "Wrote images to %s\n" "$IMAGES_DIR"
