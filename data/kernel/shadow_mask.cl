
__kernel void mask(__global uchar* pixels, __global float* height_map, __global float* light_map, __global float* deltas, int screen_width, int screen_height, int map_width, int map_height, int max_step_count, int x_offset, int y_offset, float view_height) {
    int delta_index = get_global_id(0);

    float delta_x = deltas[delta_index * 2];
    float delta_y = deltas[(delta_index * 2) + 1];

    float ray_x = (float)(screen_width) / 2.0f;
    float ray_y = (float)(screen_height) / 2.0f;

    float ray_brightness = 1;

    int view_distance_left = 10; // Distance we can see past a wall (Assuming height doesn't change)
    int wall_hit = 0;
    int vision_obstructed = 0;

    for (int step = 0; step < max_step_count; step++) {
        if (step > 50) {
            ray_brightness = ray_brightness * 0.98;
        }

        ray_x = ray_x + delta_x;
        ray_y = ray_y + delta_y;

        if ((ray_x < 0) || (ray_x >= screen_width)) { break; }
        if ((ray_y < 0) || (ray_y >= screen_height)) { break; }

        int map_x = (int)(ray_x) + x_offset;
        int map_y = (int)(ray_y) + y_offset;

        if ((map_x < 0) || (map_x >= map_width)) { break; }
        if ((map_y < 0) || (map_y >= map_height)) { break; }

        int map_index = map_x * map_height + map_y;

        float map_height = height_map[map_index];
        float light_intensity = light_map[map_index];

        if (map_height >= view_height) { wall_hit = 1; }

        if ((map_height > 0) && (map_height < view_height)) {
            vision_obstructed = 1;
        } else {
            if (vision_obstructed == 1) {
                vision_obstructed = 0;
                ray_brightness = ray_brightness * 0.6;
            }
        }

        if (wall_hit) {
            view_distance_left--;
            ray_brightness = ray_brightness * 0.8;
        }

        if (view_distance_left == 0) { break; }

        int pixel_x = (int)(ray_x);
        int pixel_y = (int)(ray_y);

        int pixel_index = pixel_y * screen_width + pixel_x;

        float pixel_brightness = ray_brightness * 0.1;

        if (light_intensity > pixel_brightness) { pixel_brightness = light_intensity; }

        pixels[pixel_index] = (uchar)((1 - pixel_brightness) * 255);

    }

}