#include <stdlib.h>
#include <string.h>

#include "builtin.h"
#include "function.h"
#include "object.h"
#include "value.h"

struct EnactList {
    size_t ref_count;
    EnactValue head;
    EnactList *tail;
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
    }

    value->kind = ENACT_VALUE_INT;
    value->as.as_int = 0;
}
