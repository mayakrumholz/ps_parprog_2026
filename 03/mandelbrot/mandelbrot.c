#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

// Include that allows to print result as an image
#define STB_IMAGE_WRITE_IMPLEMENTATION
#include "stb_image_write.h"

// Default size of image
#define X 1280
#define Y 720
#define MAX_ITER 10000

void calc_mandelbrot(uint8_t image[Y][X]) {
	for (int py = 0; py < Y; py++) {
		for (int px = 0; px < X; px++) {
			double x = 0.0;
			double y = 0.0;
			double cx = -2.5 + (3.5 * px) / (X - 1);
			double cy = -1.0 + (2.0 * py) / (Y - 1);
			int iteration = 0;

			while (x * x + y * y <= 4.0 && iteration < MAX_ITER) {
				double x_tmp = x * x - y * y + cx;
				y = 2.0 * x * y + cy;
				x = x_tmp;
				iteration++;
			}

			image[py][px] = (uint8_t)(255.0 * iteration / MAX_ITER);
		}
	}
}

int main() {
	uint8_t image[Y][X];

	calc_mandelbrot(image);

	const int channel_nr = 1, stride_bytes = 0;
	stbi_write_png("mandelbrot.png", X, Y, channel_nr, image, stride_bytes);
	return EXIT_SUCCESS;
}
