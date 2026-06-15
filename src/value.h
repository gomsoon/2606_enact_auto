#ifndef ENACT_VALUE_H
#define ENACT_VALUE_H

#include <stdbool.h>
#include <stdint.h>

typedef enum {
    ENACT_VALUE_INT,
    ENACT_VALUE_BOOL,
    ENACT_VALUE_STRING
} EnactValueKind;

typedef struct {
    EnactValueKind kind;
    union {
        int32_t as_int;
        bool as_bool;
        char *as_string;
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

static inline EnactValue enact_value_make_string(char *value)
{
    EnactValue result;

    result.kind = ENACT_VALUE_STRING;
    result.as.as_string = value;
    return result;
}

int enact_value_copy(EnactValue *out, const EnactValue *in);
void enact_value_free(EnactValue *value);

#endif
