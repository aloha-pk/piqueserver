/*
    Copyright (c) Mathias Kaerlev 2011-2012.

    This file is part of pyspades.

    pyspades is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    pyspades is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with pyspades.  If not, see <http://www.gnu.org/licenses/>.

*/

#include "vxl_c.h"
#include "Python.h"
#include <vector>

using namespace std;

void inline limit(int *value, int min, int max)
{
    if (*value > max)
    {
        *value = max;
    }
    else if (*value < min)
    {
        *value = min;
    }
}

MapData *load_vxl(unsigned char *v)
{
    MapData *map = new MapData;
    if (v == NULL)
        return map;
    int x, y, z;
    for (y = 0; y < 512; ++y)
    {
        for (x = 0; x < 512; ++x)
        {
            for (z = 0; z < 64; ++z)
            {
                map->geometry[get_pos(x, y, z)] = 1;
            }
            z = 0;
            for (;;)
            {
                int *color;
                int i;
                int number_4byte_chunks = v[0];
                int top_color_start = v[1];
                int top_color_end = v[2]; // inclusive
                int bottom_color_start;
                int bottom_color_end; // exclusive
                int len_top;
                int len_bottom;
                for (i = z; i < top_color_start; i++)
                    map->geometry[get_pos(x, y, i)] = 0;
                color = (int *)(v + 4);
                for (z = top_color_start; z <= top_color_end; z++)
                    map->colors[get_pos(x, y, z)] = *color++;
                len_bottom = top_color_end - top_color_start + 1;

                // check for end of data marker
                if (number_4byte_chunks == 0)
                {
                    // infer ACTUAL number of 4-byte chunks from the length of the color data
                    v += 4 * (len_bottom + 1);
                    break;
                }

                // infer the number of bottom colors in next span from chunk length
                len_top = (number_4byte_chunks - 1) - len_bottom;

                // now skip the v pointer past the data to the beginning of the next span
                v += v[0] * 4;

                bottom_color_end = v[3]; // aka air start
                bottom_color_start = bottom_color_end - len_top;
                for (z = bottom_color_start; z < bottom_color_end; ++z)
                {
                    map->colors[get_pos(x, y, z)] = *color++;
                }
            }
        }
    }
    return map;
}

void inline delete_vxl(MapData *map)
{
    delete map;
}

struct Position
{
    int x;
    int y;
    int z;
};

#define NODE_RESERVE_SIZE 250000
static Position *nodes = NULL;
static int node_pos;
static int nodes_size;
static set_type<int> marked;

inline void push_back_node(int x, int y, int z)
{
    nodes[node_pos].x = x;
    nodes[node_pos].y = y;
    nodes[node_pos].z = z;
    node_pos++;
}

inline const Position *pop_back_node()
{
    return &nodes[--node_pos];
}

inline void add_node(int x, int y, int z, MapData *map)
{
    if (x < 0 || x > 511 ||
        y < 0 || y > 511 ||
        z < 0 || z > 63)
        return;
    if (!map->geometry[get_pos(x, y, z)])
        return;
    push_back_node(x, y, z);
}

int check_node(int x, int y, int z, MapData *map, int destroy)
{
    if (nodes == NULL)
    {
        nodes = (Position *)malloc(sizeof(Position) * NODE_RESERVE_SIZE);
        nodes_size = NODE_RESERVE_SIZE;
    }
    node_pos = 0;

    push_back_node(x, y, z);

    while (node_pos > 0)
    {
        if (node_pos >= nodes_size - 6)
        {
            nodes_size += NODE_RESERVE_SIZE;
            nodes = (Position *)realloc((void *)nodes,
                                        sizeof(Position) * nodes_size);
        }
        const Position *current_node = pop_back_node();
        z = current_node->z;
        if (z >= 62)
        {
            marked.clear();
            return 0;
        }
        x = current_node->x;
        y = current_node->y;

        int i = get_pos(x, y, z);

        // already visited?
        pair<set_type<int>::iterator, bool> ret;
        ret = marked.insert(i);
        if (ret.second)
        {
            add_node(x, y, z - 1, map);
            add_node(x, y - 1, z, map);
            add_node(x, y + 1, z, map);
            add_node(x - 1, y, z, map);
            add_node(x + 1, y, z, map);
            add_node(x, y, z + 1, map);
        }
    }

    // destroy the node's path!

    if (destroy)
    {
        for (set_type<int>::const_iterator iter = marked.begin();
             iter != marked.end(); ++iter)
        {
            map->geometry[*iter] = 0;
            map->colors.erase(*iter);
        }
    }

    int ret = (int)marked.size();
    marked.clear();
    return ret;
}

// write_map/save_vxl function from stb/nothings - thanks a lot for the
// public-domain code!

inline int is_surface(MapData *map, int x, int y, int z)
{
    if (map->geometry[get_pos(x, y, z)] == 0)
        return 0;
    if (z == 0)
        return 1;
    if (x > 0 && map->geometry[get_pos(x - 1, y, z)] == 0)
        return 1;
    if (x + 1 < 512 && map->geometry[get_pos(x + 1, y, z)] == 0)
        return 1;
    if (y > 0 && map->geometry[get_pos(x, y - 1, z)] == 0)
        return 1;
    if (y + 1 < 512 && map->geometry[get_pos(x, y + 1, z)] == 0)
        return 1;
    if (z > 0 && map->geometry[get_pos(x, y, z - 1)] == 0)
        return 1;
    if (z + 1 < 64 && map->geometry[get_pos(x, y, z + 1)] == 0)
        return 1;
    return 0;
}

inline int get_write_color(MapData *map, int x, int y, int z)
{
    map_type<int, int>::const_iterator iter = map->colors.find(
        get_pos(x, y, z));
    if (iter == map->colors.end())
        return DEFAULT_COLOR;
    return iter->second;
}

inline void write_color(char **pos, int color)
{
    // assume color is ARGB native, but endianness is unknown
    // file format endianness is ARGB little endian, i.e. B,G,R,A
    (*pos)[0] = color & 0xFF;
    (*pos)[1] = (color >> 8) & 0xFF;
    (*pos)[2] = (color >> 16) & 0xFF;
    (*pos)[3] = (color >> 24) & 0xFF;

    // wind the cursor forward 4 bytes
    *pos += 4;
}

char *out_global = 0;

void create_temp()
{
    if (out_global == 0)
        out_global = (char *)malloc(10 * 1024 * 1024); // allocate 10 mb
}

PyObject *save_vxl(MapData *map)
{
    int i, j, k;
    create_temp();
    char *out = out_global;

    for (j = 0; j < MAP_Y; ++j)
    {
        for (i = 0; i < MAP_X; ++i)
        {
            k = 0;
            while (k < MAP_Z)
            {
                int z;

                int air_start;
                int top_colors_start;
                int top_colors_end; // exclusive
                int bottom_colors_start;
                int bottom_colors_end; // exclusive
                int top_colors_len;
                int bottom_colors_len;
                int colors;
                // find the air region
                air_start = k;
                while (k < MAP_Z && !map->geometry[get_pos(i, j, k)])
                    ++k;
                // find the top region
                top_colors_start = k;
                while (k < MAP_Z && is_surface(map, i, j, k))
                    ++k;
                top_colors_end = k;

                // now skip past the solid voxels
                while (k < MAP_Z && map->geometry[get_pos(i, j, k)] &&
                       !is_surface(map, i, j, k))
                    ++k;

                // at the end of the solid voxels, we have colored voxels.
                // in the "normal" case they're bottom colors; but it's
                // possible to have air-color-solid-color-solid-color-air,
                // which we encode as air-color-solid-0, 0-color-solid-air

                // so figure out if we have any bottom colors at this point
                bottom_colors_start = k;

                z = k;
                while (z < MAP_Z && is_surface(map, i, j, z))
                    ++z;

                if (z == MAP_Z)
                    ; // in this case, the bottom colors of this span are empty, because we'l emit as top colors
                else
                {
                    // otherwise, these are real bottom colors so we can write them
                    while (is_surface(map, i, j, k))
                        ++k;
                }
                bottom_colors_end = k;

                // now we're ready to write a span
                top_colors_len = top_colors_end - top_colors_start;
                bottom_colors_len = bottom_colors_end - bottom_colors_start;

                colors = top_colors_len + bottom_colors_len;

                if (k == MAP_Z)
                {
                    *out = 0;
                    out += 1;
                }
                else
                {
                    *out = colors + 1;
                    out += 1;
                }
                *out = top_colors_start;
                out += 1;
                *out = top_colors_end - 1;
                out += 1;
                *out = air_start;
                out += 1;

                for (z = 0; z < top_colors_len; ++z)
                {
                    write_color(&out, get_write_color(map, i, j,
                                                      top_colors_start + z));
                }
                for (z = 0; z < bottom_colors_len; ++z)
                {
                    write_color(&out, get_write_color(map, i, j,
                                                      bottom_colors_start + z));
                }
            }
        }
    }
    return PyBytes_FromStringAndSize((char *)out_global, out - out_global);
}

inline MapData *copy_map(MapData *map)
{
    return new MapData(*map);
}

struct Point2D
{
    int x, y;
};

inline unsigned int random(unsigned int a, unsigned int b, float value)
{
    return (unsigned int)(value * (b - a) + a);
}

inline void get_random_point(int x1, int y1, int x2, int y2, MapData *map,
                             float random_1, float random_2,
                             int *end_x, int *end_y)
{
    limit(&x1, 0, 511);
    limit(&y1, 0, 511);
    limit(&x2, 0, 511);
    limit(&y2, 0, 511);
    vector<Point2D> items;
    int size = 0;
    int x, y;
    for (x = x1; x < x2; x++)
    {
        for (y = y1; y < y2; y++)
        {
            if (map->geometry[get_pos(x, y, 62)])
            {
                Point2D item;
                item.x = x;
                item.y = y;
                items.push_back(item);
                size += 1;
            }
        }
    }
    if (size == 0)
    {
        *end_x = random(x1, x2, random_1);
        *end_y = random(y1, y2, random_2);
    }
    else
    {
        Point2D item = items[random(0, size, random_1)];
        *end_x = item.x;
        *end_y = item.y;
    }
}

#define SHADOW_DISTANCE 18
#define SHADOW_STEP 2

int sunblock(MapData *map, int x, int y, int z)
{
    int dec = SHADOW_DISTANCE;
    int i = 127;

    while (dec && z)
    {
        if (get_solid_wrap(x, --y, --z, map))
            i -= dec;
        dec -= SHADOW_STEP;
    }
    return i;
}

void update_shadows(MapData *map)
{
    int x, y, z;
    for (map_type<int, int>::iterator iter = map->colors.begin();
         iter != map->colors.end(); ++iter)
    {
        get_xyz(iter->first, &x, &y, &z);
        unsigned int color = iter->second;
        int a = sunblock(map, x, y, z);
        iter->second = (color & 0x00FFFFFF) | (a << 24);
    }
}

struct MapGenerator
{
    MapData *map;
    int x, y;
};

MapGenerator *create_map_generator(MapData *original)
{
    MapGenerator *generator = new MapGenerator;
    generator->map = copy_map(original);
    generator->x = 0;
    generator->y = 0;
    return generator;
}

void delete_map_generator(MapGenerator *generator)
{
    delete_vxl(generator->map);
    delete generator;
}

PyObject *get_generator_data(MapGenerator *generator, int columns)
{
    int i, j, k;
    create_temp();
    char *out = out_global;
    int column = 0;
    MapData *map = generator->map;

    for (j = generator->y; j < MAP_Y; ++j)
    {
        for (i = generator->x; i < MAP_X; ++i)
        {
            if (column == columns)
            {
                goto done;
            }
            k = 0;
            while (k < MAP_Z)
            {
                // find the air region
                int air_start = k;
                while (k < MAP_Z && !map->geometry[get_pos(i, j, k)])
                    ++k;
                // find the top region
                int top_colors_start = k;
                while (k < MAP_Z && is_surface(map, i, j, k))
                    ++k;
                int top_colors_end = k; // exlusive

                // now skip past the solid voxels
                while (k < MAP_Z && map->geometry[get_pos(i, j, k)] &&
                       !is_surface(map, i, j, k))
                    ++k;

                // at the end of the solid voxels, we have colored voxels.
                // in the "normal" case they're bottom colors; but it's
                // possible to have air-color-solid-color-solid-color-air,
                // which we encode as air-color-solid-0, 0-color-solid-air

                // so figure out if we have any bottom colors at this point
                int bottom_colors_start = k;

                int z = k;
                while (z < MAP_Z && is_surface(map, i, j, z))
                    ++z;

                if (z == MAP_Z)
                {
                    // in this case, the bottom colors of this span are empty, because we'll emit as top colors
                }
                else
                {
                    // otherwise, these are real bottom colors so we can write them
                    while (is_surface(map, i, j, k))
                        ++k;
                }
                int bottom_colors_end = k; // exclusive

                // now we're ready to write a span
                int top_colors_len = top_colors_end - top_colors_start;
                int bottom_colors_len = bottom_colors_end - bottom_colors_start;

                int colors = top_colors_len + bottom_colors_len;

                if (k == MAP_Z)
                {
                    *out = 0;
                    out += 1;
                }
                else
                {
                    *out = colors + 1;
                    out += 1;
                }
                *out = top_colors_start;
                out += 1;
                *out = top_colors_end - 1;
                out += 1;
                *out = air_start;
                out += 1;

                for (z = 0; z < top_colors_len; ++z)
                {
                    write_color(&out, get_write_color(map, i, j,
                                                      top_colors_start + z));
                }
                for (z = 0; z < bottom_colors_len; ++z)
                {
                    write_color(&out, get_write_color(map, i, j,
                                                      bottom_colors_start + z));
                }
            }
            column++;
        }
        generator->x = 0;
    }
done:
    generator->x = i;
    generator->y = j;
    return PyBytes_FromStringAndSize((char *)out_global, out - out_global);
}

const uint32_t crc32_table[256] = {
    0x00000000, 0x77073096, 0xee0e612c, 0x990951ba, 0x076dc419, 0x706af48f,
    0xe963a535, 0x9e6495a3, 0x0edb8832, 0x79dcb8a4, 0xe0d5e91e, 0x97d2d988,
    0x09b64c2b, 0x7eb17cbd, 0xe7b82d07, 0x90bf1d91, 0x1db71064, 0x6ab020f2,
    0xf3b97148, 0x84be41de, 0x1adad47d, 0x6ddde4eb, 0xf4d4b551, 0x83d385c7,
    0x136c9856, 0x646ba8c0, 0xfd62f97a, 0x8a65c9ec, 0x14015c4f, 0x63066cd9,
    0xfa0f3d63, 0x8d080df5, 0x3b6e20c8, 0x4c69105e, 0xd56041e4, 0xa2677172,
    0x3c03e4d1, 0x4b04d447, 0xd20d85fd, 0xa50ab56b, 0x35b5a8fa, 0x42b2986c,
    0xdbbbc9d6, 0xacbcf940, 0x32d86ce3, 0x45df5c75, 0xdcd60dcf, 0xabd13d59,
    0x26d930ac, 0x51de003a, 0xc8d75180, 0xbfd06116, 0x21b4f4b5, 0x56b3c423,
    0xcfba9599, 0xb8bda50f, 0x2802b89e, 0x5f058808, 0xc60cd9b2, 0xb10be924,
    0x2f6f7c87, 0x58684c11, 0xc1611dab, 0xb6662d3d, 0x76dc4190, 0x01db7106,
    0x98d220bc, 0xefd5102a, 0x71b18589, 0x06b6b51f, 0x9fbfe4a5, 0xe8b8d433,
    0x7807c9a2, 0x0f00f934, 0x9609a88e, 0xe10e9818, 0x7f6a0dbb, 0x086d3d2d,
    0x91646c97, 0xe6635c01, 0x6b6b51f4, 0x1c6c6162, 0x856530d8, 0xf262004e,
    0x6c0695ed, 0x1b01a57b, 0x8208f4c1, 0xf50fc457, 0x65b0d9c6, 0x12b7e950,
    0x8bbeb8ea, 0xfcb9887c, 0x62dd1ddf, 0x15da2d49, 0x8cd37cf3, 0xfbd44c65,
    0x4db26158, 0x3ab551ce, 0xa3bc0074, 0xd4bb30e2, 0x4adfa541, 0x3dd895d7,
    0xa4d1c46d, 0xd3d6f4fb, 0x4369e96a, 0x346ed9fc, 0xad678846, 0xda60b8d0,
    0x44042d73, 0x33031de5, 0xaa0a4c5f, 0xdd0d7cc9, 0x5005713c, 0x270241aa,
    0xbe0b1010, 0xc90c2086, 0x5768b525, 0x206f85b3, 0xb966d409, 0xce61e49f,
    0x5edef90e, 0x29d9c998, 0xb0d09822, 0xc7d7a8b4, 0x59b33d17, 0x2eb40d81,
    0xb7bd5c3b, 0xc0ba6cad, 0xedb88320, 0x9abfb3b6, 0x03b6e20c, 0x74b1d29a,
    0xead54739, 0x9dd277af, 0x04db2615, 0x73dc1683, 0xe3630b12, 0x94643b84,
    0x0d6d6a3e, 0x7a6a5aa8, 0xe40ecf0b, 0x9309ff9d, 0x0a00ae27, 0x7d079eb1,
    0xf00f9344, 0x8708a3d2, 0x1e01f268, 0x6906c2fe, 0xf762575d, 0x806567cb,
    0x196c3671, 0x6e6b06e7, 0xfed41b76, 0x89d32be0, 0x10da7a5a, 0x67dd4acc,
    0xf9b9df6f, 0x8ebeeff9, 0x17b7be43, 0x60b08ed5, 0xd6d6a3e8, 0xa1d1937e,
    0x38d8c2c4, 0x4fdff252, 0xd1bb67f1, 0xa6bc5767, 0x3fb506dd, 0x48b2364b,
    0xd80d2bda, 0xaf0a1b4c, 0x36034af6, 0x41047a60, 0xdf60efc3, 0xa867df55,
    0x316e8eef, 0x4669be79, 0xcb61b38c, 0xbc66831a, 0x256fd2a0, 0x5268e236,
    0xcc0c7795, 0xbb0b4703, 0x220216b9, 0x5505262f, 0xc5ba3bbe, 0xb2bd0b28,
    0x2bb45a92, 0x5cb36a04, 0xc2d7ffa7, 0xb5d0cf31, 0x2cd99e8b, 0x5bdeae1d,
    0x9b64c2b0, 0xec63f226, 0x756aa39c, 0x026d930a, 0x9c0906a9, 0xeb0e363f,
    0x72076785, 0x05005713, 0x95bf4a82, 0xe2b87a14, 0x7bb12bae, 0x0cb61b38,
    0x92d28e9b, 0xe5d5be0d, 0x7cdcefb7, 0x0bdbdf21, 0x86d3d2d4, 0xf1d4e242,
    0x68ddb3f8, 0x1fda836e, 0x81be16cd, 0xf6b9265b, 0x6fb077e1, 0x18b74777,
    0x88085ae6, 0xff0f6a70, 0x66063bca, 0x11010b5c, 0x8f659eff, 0xf862ae69,
    0x616bffd3, 0x166ccf45, 0xa00ae278, 0xd70dd2ee, 0x4e048354, 0x3903b3c2,
    0xa7672661, 0xd06016f7, 0x4969474d, 0x3e6e77db, 0xaed16a4a, 0xd9d65adc,
    0x40df0b66, 0x37d83bf0, 0xa9bcae53, 0xdebb9ec5, 0x47b2cf7f, 0x30b5ffe9,
    0xbdbdf21c, 0xcabac28a, 0x53b39330, 0x24b4a3a6, 0xbad03605, 0xcdd70693,
    0x54de5729, 0x23d967bf, 0xb3667a2e, 0xc4614ab8, 0x5d681b02, 0x2a6f2b94,
    0xb40bbe37, 0xc30c8ea1, 0x5a05df1b, 0x2d02ef8d
};

uint32_t compute_crc32(uint32_t initial, const unsigned char *buf, size_t len) {
    uint32_t crc = initial ^ 0xFFFFFFFF;

    while (len--) {
        crc = crc32_table[(crc ^ *buf++) & 0xFF] ^ (crc >> 8);
    }

    return crc ^ 0xFFFFFFFF;
}

char* compute_map_hash(MapData *map) {
    // Hash the memory content of the MapData structure
    unsigned int hash = compute_crc32(0, (unsigned char*)map, sizeof(MapData));

    // Convert the hash to a string (hex format)
    char* hash_string = (char*) malloc(9); // 8 characters for CRC32 in hex + 1 for null terminator
    sprintf(hash_string, "%08X", hash);

    return hash_string;
}
