#include <stdlib.h>
#include <string.h>

#include "builtin.h"
#include "function.h"
#include "object.h"
#include "runtime_stats.h"
#include "value.h"

struct EnactList {
    size_t ref_count;
    EnactValue head;
    EnactList *tail;
};

struct EnactBoundObjectMethod {
    size_t ref_count;
    EnactFunction *method;
    EnactClass *supplier_class;
    EnactValue receiver;
    EnactValue *arguments;
    size_t argument_count;
};

struct EnactBoundCollectionMethod {
    size_t ref_count;
    const EnactBuiltin *builtin;
    size_t receiver_index;
    EnactValue receiver;
    EnactValue *arguments;
    size_t argument_count;
};

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

EnactList *enact_list_cons(const EnactValue *head, EnactList *tail)
{
    EnactList *list;

    if (!head) {
        return NULL;
    }

    list = calloc(1, sizeof(*list));
    if (!list) {
        return NULL;
    }

    if (!enact_value_copy(&list->head, head)) {
        free(list);
        return NULL;
    }

    list->ref_count = 1;
    list->tail = enact_list_retain(tail);
    enact_runtime_cell_allocated();
    return list;
}

EnactList *enact_list_retain(EnactList *list)
{
    if (!list) {
        return NULL;
    }

    list->ref_count += 1;
    return list;
}

void enact_list_release(EnactList *list)
{
    if (!list) {
        return;
    }

    if (list->ref_count > 1) {
        list->ref_count -= 1;
        return;
    }

    enact_value_free(&list->head);
    enact_list_release(list->tail);
    enact_runtime_cell_released();
    free(list);
}

const EnactValue *enact_list_head(const EnactList *list)
{
    return list ? &list->head : NULL;
}

EnactList *enact_list_tail(const EnactList *list)
{
    return list ? list->tail : NULL;
}

static void enact_bound_object_method_free_arguments(
    EnactValue *arguments,
    size_t argument_count)
{
    size_t index;

    if (!arguments) {
        return;
    }

    for (index = 0; index < argument_count; index += 1) {
        enact_value_free(&arguments[index]);
    }
    free(arguments);
}

static int enact_bound_object_method_copy_arguments(
    EnactValue *out,
    const EnactValue *in,
    size_t argument_count)
{
    size_t index;

    for (index = 0; index < argument_count; index += 1) {
        if (!enact_value_copy(&out[index], &in[index])) {
            while (index > 0) {
                index -= 1;
                enact_value_free(&out[index]);
            }
            return 0;
        }
    }

    return 1;
}

EnactBoundObjectMethod *enact_bound_object_method_new(
    EnactFunction *function,
    const EnactValue *receiver)
{
    return enact_bound_object_method_new_with_supplier(function, receiver, NULL);
}

EnactBoundObjectMethod *enact_bound_object_method_new_with_supplier(
    EnactFunction *function,
    const EnactValue *receiver,
    EnactClass *supplier_class)
{
    EnactBoundObjectMethod *method;

    if (!function || !receiver) {
        return NULL;
    }

    method = calloc(1, sizeof(*method));
    if (!method) {
        return NULL;
    }

    method->ref_count = 1;
    method->method = enact_function_retain(function);
    if (!method->method) {
        free(method);
        return NULL;
    }
    method->supplier_class = enact_class_retain(supplier_class);
    if (supplier_class && !method->supplier_class) {
        enact_function_release(method->method);
        free(method);
        return NULL;
    }
    if (!enact_value_copy(&method->receiver, receiver)) {
        enact_class_release(method->supplier_class);
        enact_function_release(method->method);
        free(method);
        return NULL;
    }

    enact_runtime_cell_allocated();
    return method;
}

EnactBoundObjectMethod *enact_bound_object_method_extend(
    const EnactBoundObjectMethod *method,
    const EnactValue *arguments,
    size_t argument_count)
{
    EnactBoundObjectMethod *extended;
    size_t total_count;
    size_t method_arity;

    if (!method || argument_count == 0 || !arguments) {
        return NULL;
    }

    total_count = method->argument_count + argument_count;
    if (total_count < method->argument_count) {
        return NULL;
    }
    method_arity = enact_function_arity(method->method);
    if (total_count > method_arity) {
        return NULL;
    }

    extended = calloc(1, sizeof(*extended));
    if (!extended) {
        return NULL;
    }
    extended->arguments = calloc(total_count, sizeof(*extended->arguments));
    if (!extended->arguments) {
        free(extended);
        return NULL;
    }

    extended->ref_count = 1;
    extended->method = enact_function_retain(method->method);
    extended->argument_count = total_count;
    if (!extended->method) {
        free(extended->arguments);
        free(extended);
        return NULL;
    }
    extended->supplier_class = enact_class_retain(method->supplier_class);
    if (method->supplier_class && !extended->supplier_class) {
        enact_function_release(extended->method);
        free(extended->arguments);
        free(extended);
        return NULL;
    }
    if (!enact_value_copy(&extended->receiver, &method->receiver)) {
        enact_class_release(extended->supplier_class);
        enact_function_release(extended->method);
        free(extended->arguments);
        free(extended);
        return NULL;
    }
    if (!enact_bound_object_method_copy_arguments(
            extended->arguments,
            method->arguments,
            method->argument_count)) {
        enact_value_free(&extended->receiver);
        enact_class_release(extended->supplier_class);
        enact_function_release(extended->method);
        free(extended->arguments);
        free(extended);
        return NULL;
    }
    if (!enact_bound_object_method_copy_arguments(
            extended->arguments + method->argument_count,
            arguments,
            argument_count)) {
        enact_bound_object_method_free_arguments(extended->arguments, method->argument_count);
        enact_value_free(&extended->receiver);
        enact_class_release(extended->supplier_class);
        enact_function_release(extended->method);
        free(extended);
        return NULL;
    }

    enact_runtime_cell_allocated();
    return extended;
}

EnactBoundObjectMethod *enact_bound_object_method_retain(EnactBoundObjectMethod *method)
{
    if (!method) {
        return NULL;
    }

    method->ref_count += 1;
    return method;
}

void enact_bound_object_method_release(EnactBoundObjectMethod *method)
{
    if (!method) {
        return;
    }

    if (method->ref_count > 1) {
        method->ref_count -= 1;
        return;
    }

    enact_function_release(method->method);
    enact_class_release(method->supplier_class);
    enact_value_free(&method->receiver);
    enact_bound_object_method_free_arguments(method->arguments, method->argument_count);
    enact_runtime_cell_released();
    free(method);
}

EnactFunction *enact_bound_object_method_function(const EnactBoundObjectMethod *method)
{
    return method ? method->method : NULL;
}

EnactClass *enact_bound_object_method_supplier_class(const EnactBoundObjectMethod *method)
{
    return method ? method->supplier_class : NULL;
}

const EnactValue *enact_bound_object_method_receiver(const EnactBoundObjectMethod *method)
{
    return method ? &method->receiver : NULL;
}

size_t enact_bound_object_method_argument_count(const EnactBoundObjectMethod *method)
{
    return method ? method->argument_count : 0;
}

const EnactValue *enact_bound_object_method_argument(
    const EnactBoundObjectMethod *method,
    size_t index)
{
    if (!method || index >= method->argument_count) {
        return NULL;
    }

    return &method->arguments[index];
}

static void enact_bound_collection_method_free_arguments(
    EnactValue *arguments,
    size_t argument_count)
{
    size_t index;

    if (!arguments) {
        return;
    }

    for (index = 0; index < argument_count; index += 1) {
        enact_value_free(&arguments[index]);
    }
    free(arguments);
}

static int enact_bound_collection_method_copy_arguments(
    EnactValue *out,
    const EnactValue *in,
    size_t argument_count)
{
    size_t index;

    for (index = 0; index < argument_count; index += 1) {
        if (!enact_value_copy(&out[index], &in[index])) {
            while (index > 0) {
                index -= 1;
                enact_value_free(&out[index]);
            }
            return 0;
        }
    }

    return 1;
}

static size_t enact_bound_collection_method_arity(const EnactBuiltin *builtin)
{
    size_t builtin_arity = enact_builtin_arity(builtin);

    return builtin_arity > 0 ? builtin_arity - 1 : 0;
}

EnactBoundCollectionMethod *enact_bound_collection_method_new(
    const EnactBuiltin *builtin,
    size_t receiver_index,
    const EnactValue *receiver)
{
    EnactBoundCollectionMethod *method;

    if (!builtin || !receiver || receiver_index >= enact_builtin_arity(builtin)) {
        return NULL;
    }

    method = calloc(1, sizeof(*method));
    if (!method) {
        return NULL;
    }

    method->ref_count = 1;
    method->builtin = builtin;
    method->receiver_index = receiver_index;
    if (!enact_value_copy(&method->receiver, receiver)) {
        free(method);
        return NULL;
    }

    enact_runtime_cell_allocated();
    return method;
}

EnactBoundCollectionMethod *enact_bound_collection_method_extend(
    const EnactBoundCollectionMethod *method,
    const EnactValue *arguments,
    size_t argument_count)
{
    EnactBoundCollectionMethod *extended;
    size_t total_count;
    size_t method_arity;

    if (!method || argument_count == 0 || !arguments) {
        return NULL;
    }

    total_count = method->argument_count + argument_count;
    if (total_count < method->argument_count) {
        return NULL;
    }
    method_arity = enact_bound_collection_method_arity(method->builtin);
    if (total_count > method_arity) {
        return NULL;
    }

    extended = calloc(1, sizeof(*extended));
    if (!extended) {
        return NULL;
    }
    extended->arguments = calloc(total_count, sizeof(*extended->arguments));
    if (!extended->arguments) {
        free(extended);
        return NULL;
    }

    extended->ref_count = 1;
    extended->builtin = method->builtin;
    extended->receiver_index = method->receiver_index;
    extended->argument_count = total_count;
    if (!enact_value_copy(&extended->receiver, &method->receiver)) {
        free(extended->arguments);
        free(extended);
        return NULL;
    }
    if (!enact_bound_collection_method_copy_arguments(
            extended->arguments,
            method->arguments,
            method->argument_count)) {
        enact_value_free(&extended->receiver);
        free(extended->arguments);
        free(extended);
        return NULL;
    }
    if (!enact_bound_collection_method_copy_arguments(
            extended->arguments + method->argument_count,
            arguments,
            argument_count)) {
        enact_bound_collection_method_free_arguments(extended->arguments, method->argument_count);
        enact_value_free(&extended->receiver);
        free(extended);
        return NULL;
    }

    enact_runtime_cell_allocated();
    return extended;
}

EnactBoundCollectionMethod *enact_bound_collection_method_retain(EnactBoundCollectionMethod *method)
{
    if (!method) {
        return NULL;
    }

    method->ref_count += 1;
    return method;
}

void enact_bound_collection_method_release(EnactBoundCollectionMethod *method)
{
    if (!method) {
        return;
    }

    if (method->ref_count > 1) {
        method->ref_count -= 1;
        return;
    }

    enact_value_free(&method->receiver);
    enact_bound_collection_method_free_arguments(method->arguments, method->argument_count);
    enact_runtime_cell_released();
    free(method);
}

const EnactBuiltin *enact_bound_collection_method_builtin(const EnactBoundCollectionMethod *method)
{
    return method ? method->builtin : NULL;
}

size_t enact_bound_collection_method_receiver_index(const EnactBoundCollectionMethod *method)
{
    return method ? method->receiver_index : 0;
}

const EnactValue *enact_bound_collection_method_receiver(const EnactBoundCollectionMethod *method)
{
    return method ? &method->receiver : NULL;
}

size_t enact_bound_collection_method_argument_count(const EnactBoundCollectionMethod *method)
{
    return method ? method->argument_count : 0;
}

const EnactValue *enact_bound_collection_method_argument(
    const EnactBoundCollectionMethod *method,
    size_t index)
{
    if (!method || index >= method->argument_count) {
        return NULL;
    }

    return &method->arguments[index];
}

static int enact_list_equal(const EnactList *left, const EnactList *right, bool *out)
{
    while (left && right) {
        bool heads_equal = false;

        if (!enact_value_equal(&left->head, &right->head, &heads_equal)) {
            return 0;
        }
        if (!heads_equal) {
            *out = false;
            return 1;
        }

        left = left->tail;
        right = right->tail;
    }

    *out = left == NULL && right == NULL;
    return 1;
}

int enact_value_equal(const EnactValue *left, const EnactValue *right, bool *out)
{
    if (!left || !right || !out) {
        return 0;
    }
    if (left->kind != right->kind) {
        *out = false;
        return 1;
    }

    switch (left->kind) {
    case ENACT_VALUE_INT:
        *out = left->as.as_int == right->as.as_int;
        return 1;
    case ENACT_VALUE_BOOL:
        *out = left->as.as_bool == right->as.as_bool;
        return 1;
    case ENACT_VALUE_STRING:
        *out = strcmp(left->as.as_string, right->as.as_string) == 0;
        return 1;
    case ENACT_VALUE_ATOM:
        *out = strcmp(left->as.as_atom, right->as.as_atom) == 0;
        return 1;
    case ENACT_VALUE_CLASS:
        *out = left->as.as_class == right->as.as_class;
        return 1;
    case ENACT_VALUE_OBJECT:
        *out = left->as.as_object == right->as.as_object;
        return 1;
    case ENACT_VALUE_FUNCTION:
        *out = left->as.as_function == right->as.as_function;
        return 1;
    case ENACT_VALUE_LIST:
        return enact_list_equal(left->as.as_list, right->as.as_list, out);
    case ENACT_VALUE_BUILTIN:
        *out = left->as.as_builtin == right->as.as_builtin;
        return 1;
    case ENACT_VALUE_BUILTIN_PARTIAL:
        *out = left->as.as_builtin_partial == right->as.as_builtin_partial;
        return 1;
    case ENACT_VALUE_BOUND_OBJECT_METHOD:
        *out = left->as.as_bound_object_method == right->as.as_bound_object_method;
        return 1;
    case ENACT_VALUE_BOUND_COLLECTION_METHOD:
        *out = left->as.as_bound_collection_method == right->as.as_bound_collection_method;
        return 1;
    }

    return 0;
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
    case ENACT_VALUE_ATOM:
        out->kind = ENACT_VALUE_ATOM;
        out->as.as_atom = enact_value_copy_string(in->as.as_atom);
        return out->as.as_atom != NULL;
    case ENACT_VALUE_CLASS:
        out->kind = ENACT_VALUE_CLASS;
        out->as.as_class = enact_class_retain(in->as.as_class);
        return out->as.as_class != NULL;
    case ENACT_VALUE_OBJECT:
        out->kind = ENACT_VALUE_OBJECT;
        out->as.as_object = enact_object_retain(in->as.as_object);
        return out->as.as_object != NULL;
    case ENACT_VALUE_FUNCTION:
        out->kind = ENACT_VALUE_FUNCTION;
        out->as.as_function = enact_function_retain(in->as.as_function);
        return out->as.as_function != NULL;
    case ENACT_VALUE_LIST:
        out->kind = ENACT_VALUE_LIST;
        out->as.as_list = enact_list_retain(in->as.as_list);
        return in->as.as_list == NULL || out->as.as_list != NULL;
    case ENACT_VALUE_BUILTIN:
        if (!in->as.as_builtin) {
            return 0;
        }
        *out = *in;
        return 1;
    case ENACT_VALUE_BUILTIN_PARTIAL:
        out->kind = ENACT_VALUE_BUILTIN_PARTIAL;
        out->as.as_builtin_partial = enact_builtin_partial_retain(in->as.as_builtin_partial);
        return out->as.as_builtin_partial != NULL;
    case ENACT_VALUE_BOUND_OBJECT_METHOD:
        out->kind = ENACT_VALUE_BOUND_OBJECT_METHOD;
        out->as.as_bound_object_method =
            enact_bound_object_method_retain(in->as.as_bound_object_method);
        return out->as.as_bound_object_method != NULL;
    case ENACT_VALUE_BOUND_COLLECTION_METHOD:
        out->kind = ENACT_VALUE_BOUND_COLLECTION_METHOD;
        out->as.as_bound_collection_method =
            enact_bound_collection_method_retain(in->as.as_bound_collection_method);
        return out->as.as_bound_collection_method != NULL;
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
    } else if (value->kind == ENACT_VALUE_ATOM) {
        free(value->as.as_atom);
    } else if (value->kind == ENACT_VALUE_CLASS) {
        enact_class_release(value->as.as_class);
    } else if (value->kind == ENACT_VALUE_OBJECT) {
        enact_object_release(value->as.as_object);
    } else if (value->kind == ENACT_VALUE_FUNCTION) {
        enact_function_release(value->as.as_function);
    } else if (value->kind == ENACT_VALUE_LIST) {
        enact_list_release(value->as.as_list);
    } else if (value->kind == ENACT_VALUE_BUILTIN_PARTIAL) {
        enact_builtin_partial_release(value->as.as_builtin_partial);
    } else if (value->kind == ENACT_VALUE_BOUND_OBJECT_METHOD) {
        enact_bound_object_method_release(value->as.as_bound_object_method);
    } else if (value->kind == ENACT_VALUE_BOUND_COLLECTION_METHOD) {
        enact_bound_collection_method_release(value->as.as_bound_collection_method);
    }

    value->kind = ENACT_VALUE_INT;
    value->as.as_int = 0;
}
