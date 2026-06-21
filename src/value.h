#ifndef ENACT_VALUE_H
#define ENACT_VALUE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef struct EnactFunction EnactFunction;
typedef struct EnactClass EnactClass;
typedef struct EnactObject EnactObject;
typedef struct EnactList EnactList;
typedef struct EnactBuiltin EnactBuiltin;
typedef struct EnactBuiltinPartial EnactBuiltinPartial;
typedef struct EnactBoundObjectMethod EnactBoundObjectMethod;
typedef struct EnactBoundCollectionMethod EnactBoundCollectionMethod;

typedef enum {
    ENACT_VALUE_INT,
    ENACT_VALUE_BOOL,
    ENACT_VALUE_STRING,
    ENACT_VALUE_ATOM,
    ENACT_VALUE_CLASS,
    ENACT_VALUE_OBJECT,
    ENACT_VALUE_FUNCTION,
    ENACT_VALUE_LIST,
    ENACT_VALUE_BUILTIN,
    ENACT_VALUE_BUILTIN_PARTIAL,
    ENACT_VALUE_BOUND_OBJECT_METHOD,
    ENACT_VALUE_BOUND_COLLECTION_METHOD
} EnactValueKind;

typedef struct EnactValue {
    EnactValueKind kind;
    union {
        int32_t as_int;
        bool as_bool;
        char *as_string;
        char *as_atom;
        EnactClass *as_class;
        EnactObject *as_object;
        EnactFunction *as_function;
        EnactList *as_list;
        const EnactBuiltin *as_builtin;
        EnactBuiltinPartial *as_builtin_partial;
        EnactBoundObjectMethod *as_bound_object_method;
        EnactBoundCollectionMethod *as_bound_collection_method;
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

static inline EnactValue enact_value_make_class(EnactClass *class_value)
{
    EnactValue result;

    result.kind = ENACT_VALUE_CLASS;
    result.as.as_class = class_value;
    return result;
}

static inline EnactValue enact_value_make_object(EnactObject *object)
{
    EnactValue result;

    result.kind = ENACT_VALUE_OBJECT;
    result.as.as_object = object;
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

static inline EnactValue enact_value_make_bound_object_method(EnactBoundObjectMethod *method)
{
    EnactValue result;

    result.kind = ENACT_VALUE_BOUND_OBJECT_METHOD;
    result.as.as_bound_object_method = method;
    return result;
}

static inline EnactValue enact_value_make_bound_collection_method(EnactBoundCollectionMethod *method)
{
    EnactValue result;

    result.kind = ENACT_VALUE_BOUND_COLLECTION_METHOD;
    result.as.as_bound_collection_method = method;
    return result;
}

EnactList *enact_list_cons(const EnactValue *head, EnactList *tail);
EnactList *enact_list_retain(EnactList *list);
void enact_list_release(EnactList *list);
const EnactValue *enact_list_head(const EnactList *list);
EnactList *enact_list_tail(const EnactList *list);
EnactBoundObjectMethod *enact_bound_object_method_new(
    EnactFunction *method,
    const EnactValue *receiver);
EnactBoundObjectMethod *enact_bound_object_method_new_with_supplier(
    EnactFunction *method,
    const EnactValue *receiver,
    EnactClass *supplier_class);
EnactBoundObjectMethod *enact_bound_object_method_extend(
    const EnactBoundObjectMethod *method,
    const EnactValue *arguments,
    size_t argument_count);
EnactBoundObjectMethod *enact_bound_object_method_retain(EnactBoundObjectMethod *method);
void enact_bound_object_method_release(EnactBoundObjectMethod *method);
EnactFunction *enact_bound_object_method_function(const EnactBoundObjectMethod *method);
EnactClass *enact_bound_object_method_supplier_class(const EnactBoundObjectMethod *method);
const EnactValue *enact_bound_object_method_receiver(const EnactBoundObjectMethod *method);
size_t enact_bound_object_method_argument_count(const EnactBoundObjectMethod *method);
const EnactValue *enact_bound_object_method_argument(
    const EnactBoundObjectMethod *method,
    size_t index);
EnactBoundCollectionMethod *enact_bound_collection_method_new(
    const EnactBuiltin *builtin,
    size_t receiver_index,
    const EnactValue *receiver);
EnactBoundCollectionMethod *enact_bound_collection_method_extend(
    const EnactBoundCollectionMethod *method,
    const EnactValue *arguments,
    size_t argument_count);
EnactBoundCollectionMethod *enact_bound_collection_method_retain(EnactBoundCollectionMethod *method);
void enact_bound_collection_method_release(EnactBoundCollectionMethod *method);
const EnactBuiltin *enact_bound_collection_method_builtin(const EnactBoundCollectionMethod *method);
size_t enact_bound_collection_method_receiver_index(const EnactBoundCollectionMethod *method);
const EnactValue *enact_bound_collection_method_receiver(const EnactBoundCollectionMethod *method);
size_t enact_bound_collection_method_argument_count(const EnactBoundCollectionMethod *method);
const EnactValue *enact_bound_collection_method_argument(
    const EnactBoundCollectionMethod *method,
    size_t index);
int enact_value_equal(const EnactValue *left, const EnactValue *right, bool *out);
int enact_value_copy(EnactValue *out, const EnactValue *in);
void enact_value_free(EnactValue *value);

#endif
