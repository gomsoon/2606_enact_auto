#ifndef ENACT_VALUE_H
#define ENACT_VALUE_H

#include <stdbool.h>
#include <stdint.h>

typedef struct EnactFunction EnactFunction;
typedef struct EnactList EnactList;
typedef struct EnactBuiltin EnactBuiltin;
typedef struct EnactBuiltinPartial EnactBuiltinPartial;

typedef enum {
    ENACT_VALUE_INT,
    ENACT_VALUE_BOOL,
    ENACT_VALUE_STRING,
    ENACT_VALUE_ATOM,
    ENACT_VALUE_FUNCTION,
    ENACT_VALUE_LIST,
    ENACT_VALUE_BUILTIN,
    ENACT_VALUE_BUILTIN_PARTIAL
} EnactValueKind;

typedef struct {
    EnactValueKind kind;
    union {
        int32_t as_int;
        bool as_bool;
        char *as_string;
        char *as_atom;
        EnactFunction *as_function;
        EnactList *as_list;
        const EnactBuiltin *as_builtin;
        EnactBuiltinPartial *as_builtin_partial;
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

static inline EnactValue enact_value_make_atom(char *value)
{
    EnactValue result;

    result.kind = ENACT_VALUE_ATOM;
    result.as.as_atom = value;
    return result;
}

static inline EnactValue enact_value_make_function(EnactFunction *function)
{
    EnactValue result;

    result.kind = ENACT_VALUE_FUNCTION;
    result.as.as_function = function;
    return result;
}

static inline EnactValue enact_value_make_list(EnactList *list)
{
    EnactValue result;

    result.kind = ENACT_VALUE_LIST;
    result.as.as_list = list;
    return result;
}

static inline EnactValue enact_value_make_builtin(const EnactBuiltin *builtin)
{
    EnactValue result;

    result.kind = ENACT_VALUE_BUILTIN;
    result.as.as_builtin = builtin;
    return result;
}

static inline EnactValue enact_value_make_builtin_partial(EnactBuiltinPartial *partial)
{
    EnactValue result;

    result.kind = ENACT_VALUE_BUILTIN_PARTIAL;
    result.as.as_builtin_partial = partial;
    return result;
}

EnactList *enact_list_cons(const EnactValue *head, EnactList *tail);
EnactList *enact_list_retain(EnactList *list);
void enact_list_release(EnactList *list);
const EnactValue *enact_list_head(const EnactList *list);
EnactList *enact_list_tail(const EnactList *list);
int enact_value_equal(const EnactValue *left, const EnactValue *right, bool *out);
int enact_value_copy(EnactValue *out, const EnactValue *in);
void enact_value_free(EnactValue *value);

#endif
