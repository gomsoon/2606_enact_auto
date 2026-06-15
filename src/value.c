#include <stdlib.h>
#include <string.h>

#include "value.h"

static char *enact_value_copy_string(const char *value)
{
    size_t length;
    char *copy;

    if (!value) {
        value = "";
    }

    length = strlen(value);
    copy = malloc(length + 1);
    if (!copy) {
        return NULL;
    }

    memcpy(copy, value, length + 1);
    return copy;
}

int enact_value_copy(EnactValue *out, const EnactValue *in)
{
    if (!out || !in) {
        return 0;
    }

    switch (in->kind) {
    case ENACT_VALUE_INT:
    case ENACT_VALUE_BOOL:
        *out = *in;
        return 1;
    case ENACT_VALUE_STRING:
        out->kind = ENACT_VALUE_STRING;
        out->as.as_string = enact_value_copy_string(in->as.as_string);
        return out->as.as_string != NULL;
    }

    return 0;
}

void enact_value_free(EnactValue *value)
{
    if (!value) {
        return;
    }

    if (value->kind == ENACT_VALUE_STRING) {
        free(value->as.as_string);
    }

    value->kind = ENACT_VALUE_INT;
    value->as.as_int = 0;
}
