#ifndef COMMON_C_H
#define COMMON_C_H

#include <stdlib.h>

struct Vector { float x, y, z; };
struct LongVector { long x, y, z; };

inline struct Vector *create_vector(float x, float y, float z)
{
	struct Vector *v = malloc(sizeof(struct Vector));
	if (v == NULL)
		abort();

	v->x = x;
	v->y = y;
	v->z = z;

	return v;
}

inline void destroy_vector(struct Vector *v)
{
    free(v);
}

#endif /* COMMON_C_H */
