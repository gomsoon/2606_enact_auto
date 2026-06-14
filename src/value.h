#ifndef ENACT_VALUE_H
#define ENACT_VALUE_H

#include <stdint.h>

typedef enum {
    ENACT_VALUE_INT
} EnactValueKind;

typedef struct {
    EnactValueKind kind;
    int32_t as_int;
} EnactValue;

#endif
