#ifndef ENACT_VALUE_H
#define ENACT_VALUE_H

#include <stdbool.h>
#include <stdint.h>

typedef enum {
    ENACT_VALUE_INT,
    ENACT_VALUE_BOOL
} EnactValueKind;

typedef struct {
    EnactValueKind kind;
    union {
        int32_t as_int;
        bool as_bool;
    } as;
} EnactValue;

static inline EnactValue enact_value_make_int(int32_t value)
{
    EnactValue result;

    result.kind = ENACT_VALUE_INT;
    result.as.as_int = value;
    return result;
}

static inline EnactValue enact_value_make_bool(bool value)
{
    EnactValue result;

    result.kind = ENACT_VALUE_BOOL;
    result.as.as_bool = value;
    return result;
}

#endif
