// todo - chunk the lighting into small areas and only render the surrounding 8, save compute time - Not setup CPU side

__kernel void update(
        __global float* light_map,
        __global const int* lights,

        int map_height,
        int light_count
) {
   int x = get_global_id(0);
   int y = get_global_id(1);

   float pixel_accum_brightness = 0;
   for (int i = 0; i<light_count; i++) {
        int dx = lights[(i*3)+1] - x;
        int dy = lights[(i*3)] - y;
        int radius = lights[(i*3)+2];

        int distance_squared = (dx * dx) + (dy * dy);

        float invRadius = 1.0f / radius;
        float inv_radius_squared = invRadius * invRadius;

        float t2 = distance_squared * inv_radius_squared;
        float intensity = 1.0f - t2;

        intensity = clamp(intensity, 0.0f, 1.0f);

        pixel_accum_brightness = pixel_accum_brightness + intensity;
   }

   float pixel_brightness = clamp(pixel_accum_brightness, 0.0f, 1.0f);
   int map_index = x * map_height + y;

   light_map[map_index] = pixel_brightness * 255;
}