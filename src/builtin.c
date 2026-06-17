#include <limits.h>
#include <stdlib.h>
#include <string.h>

#include "builtin.h"
#include "eval.h"
#include "object.h"

#define ENACT_VERSION_STRING "enact-auto 0.1.0"

typedef int (*EnactBuiltinCallback)(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag);

struct EnactBuiltin {
    const char *name;
    size_t arity;
    EnactBuiltinCallback callback;
};

struct EnactBuiltinPartial {
    size_t ref_count;
    const EnactBuiltin *builtin;
    EnactValue *arguments;
    size_t argument_count;
};

static char *enact_builtin_copy_text(const char *text)
{
    size_t length;
    char *copy;

    if (!text) {
        text = "";
    }

    length = strlen(text);
    copy = malloc(length + 1);
    if (!copy) {
        return NULL;
    }

    memcpy(copy, text, length + 1);
    return copy;
}

static void enact_builtin_free_argument_values(EnactValue *arguments, size_t argument_count)
{
    size_t index;

    if (!arguments) {
        return;
    }

    for (index = 0; index < argument_count; index += 1) {
        enact_value_free(&arguments[index]);
    }
}

static void enact_builtin_free_arguments(EnactValue *arguments, size_t argument_count)
{
    if (!arguments) {
        return;
    }

    enact_builtin_free_argument_values(arguments, argument_count);
    free(arguments);
}

static int enact_builtin_copy_arguments(EnactValue *out, const EnactValue *in, size_t argument_count)
{
    size_t index;

    if (argument_count > 0 && (!out || !in)) {
        return 0;
    }

    for (index = 0; index < argument_count; index += 1) {
        if (!enact_value_copy(&out[index], &in[index])) {
            enact_builtin_free_argument_values(out, index);
            return 0;
        }
    }

    return 1;
}

static EnactBuiltinPartial *enact_builtin_partial_alloc(const EnactBuiltin *builtin, size_t argument_count)
{
    EnactBuiltinPartial *partial;

    if (!builtin || argument_count == 0 || argument_count >= enact_builtin_arity(builtin)) {
        return NULL;
    }

    partial = calloc(1, sizeof(*partial));
    if (!partial) {
        return NULL;
    }

    partial->arguments = calloc(argument_count, sizeof(*partial->arguments));
    if (!partial->arguments) {
        free(partial);
        return NULL;
    }

    partial->ref_count = 1;
    partial->builtin = builtin;
    partial->argument_count = argument_count;
    return partial;
}

static int enact_builtin_require_list(const EnactValue *value, EnactList **out, EnactDiag *diag)
{
    if (!value || value->kind != ENACT_VALUE_LIST) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_LIST, -1);
        return 0;
    }

    *out = value->as.as_list;
    return 1;
}

static int enact_builtin_require_non_empty_list(const EnactValue *value, EnactList **out, EnactDiag *diag)
{
    if (!enact_builtin_require_list(value, out, diag)) {
        return 0;
    }
    if (!*out) {
        enact_diag_set(diag, ENACT_ERR_LIST_EMPTY, -1);
        return 0;
    }

    return 1;
}

static int enact_builtin_require_callable(const EnactValue *value, EnactDiag *diag)
{
    if (!value ||
        (value->kind != ENACT_VALUE_FUNCTION &&
         value->kind != ENACT_VALUE_BUILTIN &&
         value->kind != ENACT_VALUE_BUILTIN_PARTIAL)) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_FUNCTION, -1);
        return 0;
    }

    return 1;
}

static int enact_builtin_require_bool_value(const EnactValue *value, bool *out, EnactDiag *diag)
{
    if (!value || value->kind != ENACT_VALUE_BOOL) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_BOOL, -1);
        return 0;
    }

    *out = value->as.as_bool;
    return 1;
}

static int enact_builtin_apply_predicate(
    const EnactValue *callable,
    const EnactValue *argument,
    bool *out,
    EnactDiag *diag)
{
    EnactValue result;
    int status;

    if (!out) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }
    if (!enact_eval_apply_callable(callable, argument, 1, &result, diag)) {
        return 0;
    }

    status = enact_builtin_require_bool_value(&result, out, diag);
    enact_value_free(&result);
    return status;
}

static int enact_builtin_list_contains_value(
    EnactList *list,
    const EnactValue *needle,
    bool *out)
{
    if (!needle || !out) {
        return 0;
    }

    while (list) {
        const EnactValue *head = enact_list_head(list);
        bool equal = false;

        if (!head || !enact_value_equal(head, needle, &equal)) {
            return 0;
        }
        if (equal) {
            *out = true;
            return 1;
        }

        list = enact_list_tail(list);
    }

    *out = false;
    return 1;
}

static int enact_builtin_hd(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *list = NULL;
    const EnactValue *head;

    (void)argument_count;

    if (!enact_builtin_require_non_empty_list(&arguments[0], &list, diag)) {
        return 0;
    }

    head = enact_list_head(list);
    if (!head || !enact_value_copy(out, head)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    return 1;
}

static int enact_builtin_tl(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *list = NULL;

    (void)argument_count;

    if (!enact_builtin_require_non_empty_list(&arguments[0], &list, diag)) {
        return 0;
    }

    *out = enact_value_make_list(enact_list_retain(enact_list_tail(list)));
    return 1;
}

static int enact_builtin_atom(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    (void)argument_count;
    (void)diag;

    *out = enact_value_make_bool(
        arguments[0].kind != ENACT_VALUE_LIST || arguments[0].as.as_list == NULL);
    return 1;
}

static int enact_builtin_is_object(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    (void)argument_count;
    (void)diag;

    *out = enact_value_make_bool(arguments[0].kind == ENACT_VALUE_OBJECT);
    return 1;
}

static int enact_builtin_classof(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactClass *class_value;

    (void)argument_count;

    if (arguments[0].kind != ENACT_VALUE_OBJECT) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_OBJECT, -1);
        return 0;
    }

    class_value = enact_class_retain(enact_object_class(arguments[0].as.as_object));
    if (!class_value) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_class(class_value);
    return 1;
}

static int enact_builtin_attrs(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *names = NULL;

    (void)argument_count;

    if (arguments[0].kind != ENACT_VALUE_OBJECT) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_OBJECT, -1);
        return 0;
    }

    if (!enact_object_attribute_names(arguments[0].as.as_object, &names)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_list(names);
    return 1;
}

static int enact_builtin_version(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    char *version;

    (void)arguments;
    (void)argument_count;

    version = enact_builtin_copy_text(ENACT_VERSION_STRING);
    if (!version) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_string(version);
    return 1;
}

static int enact_builtin_list(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *result;

    (void)argument_count;

    result = enact_list_cons(&arguments[0], NULL);
    if (!result) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_list(result);
    return 1;
}

static int enact_builtin_unitset(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    return enact_builtin_list(arguments, argument_count, out, diag);
}

static int enact_builtin_append_lists(EnactList *left, EnactList *right, EnactList **out)
{
    EnactList *tail = NULL;
    EnactList *result;

    if (!out) {
        return 0;
    }
    if (!left) {
        *out = enact_list_retain(right);
        return right == NULL || *out != NULL;
    }

    if (!enact_builtin_append_lists(enact_list_tail(left), right, &tail)) {
        return 0;
    }

    result = enact_list_cons(enact_list_head(left), tail);
    enact_list_release(tail);
    if (!result) {
        return 0;
    }

    *out = result;
    return 1;
}

static int enact_builtin_append(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *left = NULL;
    EnactList *right = NULL;
    EnactList *result = NULL;

    (void)argument_count;

    if (!enact_builtin_require_list(&arguments[0], &left, diag)) {
        return 0;
    }
    if (!enact_builtin_require_list(&arguments[1], &right, diag)) {
        return 0;
    }

    if (!enact_builtin_append_lists(left, right, &result)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_list(result);
    return 1;
}

static int enact_builtin_size(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *list = NULL;
    int32_t count = 0;

    (void)argument_count;

    if (!enact_builtin_require_list(&arguments[0], &list, diag)) {
        return 0;
    }

    while (list) {
        if (count == INT_MAX) {
            enact_diag_set(diag, ENACT_ERR_INT_OVERFLOW, -1);
            return 0;
        }
        count += 1;
        list = enact_list_tail(list);
    }

    *out = enact_value_make_int(count);
    return 1;
}

static int enact_builtin_map_list(
    const EnactValue *callable,
    EnactList *list,
    EnactList **out,
    EnactDiag *diag)
{
    const EnactValue *head;
    EnactValue mapped_head;
    EnactList *mapped_tail = NULL;
    EnactList *result;

    if (!out) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }
    if (!list) {
        *out = NULL;
        return 1;
    }

    head = enact_list_head(list);
    if (!head || !enact_eval_apply_callable(callable, head, 1, &mapped_head, diag)) {
        return 0;
    }

    if (!enact_builtin_map_list(callable, enact_list_tail(list), &mapped_tail, diag)) {
        enact_value_free(&mapped_head);
        return 0;
    }

    result = enact_list_cons(&mapped_head, mapped_tail);
    enact_value_free(&mapped_head);
    enact_list_release(mapped_tail);
    if (!result) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = result;
    return 1;
}

static int enact_builtin_map(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *list = NULL;
    EnactList *result = NULL;

    (void)argument_count;

    if (!enact_builtin_require_callable(&arguments[0], diag)) {
        return 0;
    }
    if (!enact_builtin_require_list(&arguments[1], &list, diag)) {
        return 0;
    }
    if (!enact_builtin_map_list(&arguments[0], list, &result, diag)) {
        return 0;
    }

    *out = enact_value_make_list(result);
    return 1;
}

static int enact_builtin_filter_list(
    const EnactValue *callable,
    EnactList *list,
    EnactList **out,
    EnactDiag *diag)
{
    const EnactValue *head;
    EnactList *filtered_tail = NULL;
    bool keep = false;

    if (!out) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }
    if (!list) {
        *out = NULL;
        return 1;
    }

    head = enact_list_head(list);
    if (!head || !enact_builtin_apply_predicate(callable, head, &keep, diag)) {
        return 0;
    }

    if (!enact_builtin_filter_list(callable, enact_list_tail(list), &filtered_tail, diag)) {
        return 0;
    }

    if (keep) {
        EnactList *result = enact_list_cons(head, filtered_tail);

        enact_list_release(filtered_tail);
        if (!result) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }

        *out = result;
        return 1;
    }

    *out = filtered_tail;
    return 1;
}

static int enact_builtin_filter(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *list = NULL;
    EnactList *result = NULL;

    (void)argument_count;

    if (!enact_builtin_require_callable(&arguments[0], diag)) {
        return 0;
    }
    if (!enact_builtin_require_list(&arguments[1], &list, diag)) {
        return 0;
    }
    if (!enact_builtin_filter_list(&arguments[0], list, &result, diag)) {
        return 0;
    }

    *out = enact_value_make_list(result);
    return 1;
}

static int enact_builtin_all(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *list = NULL;
    bool result = false;

    (void)argument_count;

    if (!enact_builtin_require_callable(&arguments[0], diag)) {
        return 0;
    }
    if (!enact_builtin_require_list(&arguments[1], &list, diag)) {
        return 0;
    }

    while (list) {
        const EnactValue *head = enact_list_head(list);

        if (!head || !enact_builtin_apply_predicate(&arguments[0], head, &result, diag)) {
            return 0;
        }
        if (!result) {
            *out = enact_value_make_bool(false);
            return 1;
        }

        list = enact_list_tail(list);
    }

    *out = enact_value_make_bool(true);
    return 1;
}

static int enact_builtin_exists(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *list = NULL;
    bool result = false;

    (void)argument_count;

    if (!enact_builtin_require_callable(&arguments[0], diag)) {
        return 0;
    }
    if (!enact_builtin_require_list(&arguments[1], &list, diag)) {
        return 0;
    }

    while (list) {
        const EnactValue *head = enact_list_head(list);

        if (!head || !enact_builtin_apply_predicate(&arguments[0], head, &result, diag)) {
            return 0;
        }
        if (result) {
            *out = enact_value_make_bool(true);
            return 1;
        }

        list = enact_list_tail(list);
    }

    *out = enact_value_make_bool(false);
    return 1;
}

static int enact_builtin_reduce(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *list = NULL;
    EnactValue accumulator;

    (void)argument_count;

    if (!enact_builtin_require_callable(&arguments[0], diag)) {
        return 0;
    }
    if (!enact_builtin_require_list(&arguments[2], &list, diag)) {
        return 0;
    }
    if (!enact_value_copy(&accumulator, &arguments[1])) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    while (list) {
        const EnactValue *head = enact_list_head(list);
        EnactValue reducer_arguments[2];
        EnactValue next_accumulator;

        if (!head) {
            enact_value_free(&accumulator);
            enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
            return 0;
        }

        reducer_arguments[0] = accumulator;
        reducer_arguments[1] = *head;
        if (!enact_eval_apply_callable(&arguments[0], reducer_arguments, 2, &next_accumulator, diag)) {
            enact_value_free(&accumulator);
            return 0;
        }

        enact_value_free(&accumulator);
        accumulator = next_accumulator;
        list = enact_list_tail(list);
    }

    *out = accumulator;
    return 1;
}

static int enact_builtin_member(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *list = NULL;
    bool found = false;

    (void)argument_count;

    if (!enact_builtin_require_list(&arguments[1], &list, diag)) {
        return 0;
    }
    if (!enact_builtin_list_contains_value(list, &arguments[0], &found)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_bool(found);
    return 1;
}

static int enact_builtin_remove_one(
    const EnactValue *needle,
    EnactList *list,
    bool *removed,
    EnactList **out)
{
    const EnactValue *head;
    EnactList *tail = NULL;
    EnactList *result;
    bool equal = false;

    if (!needle || !removed || !out) {
        return 0;
    }
    if (!list) {
        *out = NULL;
        return 1;
    }

    head = enact_list_head(list);
    if (!head) {
        return 0;
    }
    if (!*removed && !enact_value_equal(head, needle, &equal)) {
        return 0;
    }
    if (!*removed && equal) {
        EnactList *rest = enact_list_retain(enact_list_tail(list));

        if (enact_list_tail(list) && !rest) {
            return 0;
        }
        *removed = true;
        *out = rest;
        return 1;
    }

    if (!enact_builtin_remove_one(needle, enact_list_tail(list), removed, &tail)) {
        return 0;
    }

    result = enact_list_cons(head, tail);
    enact_list_release(tail);
    if (!result) {
        return 0;
    }

    *out = result;
    return 1;
}

static int enact_builtin_remove(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *list = NULL;
    EnactList *result = NULL;
    bool removed = false;

    (void)argument_count;

    if (!enact_builtin_require_list(&arguments[1], &list, diag)) {
        return 0;
    }
    if (!enact_builtin_remove_one(&arguments[0], list, &removed, &result)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_list(result);
    return 1;
}

static int enact_builtin_difference_lists(
    EnactList *left,
    EnactList *right,
    EnactList **out)
{
    const EnactValue *head;
    EnactList *filtered_tail = NULL;
    EnactList *result;
    bool in_right = false;

    if (!out) {
        return 0;
    }
    if (!left) {
        *out = NULL;
        return 1;
    }

    head = enact_list_head(left);
    if (!head || !enact_builtin_list_contains_value(right, head, &in_right)) {
        return 0;
    }
    if (!enact_builtin_difference_lists(enact_list_tail(left), right, &filtered_tail)) {
        return 0;
    }

    if (in_right) {
        *out = filtered_tail;
        return 1;
    }

    result = enact_list_cons(head, filtered_tail);
    enact_list_release(filtered_tail);
    if (!result) {
        return 0;
    }

    *out = result;
    return 1;
}

static int enact_builtin_difference(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *left = NULL;
    EnactList *right = NULL;
    EnactList *result = NULL;

    (void)argument_count;

    if (!enact_builtin_require_list(&arguments[0], &left, diag)) {
        return 0;
    }
    if (!enact_builtin_require_list(&arguments[1], &right, diag)) {
        return 0;
    }
    if (!enact_builtin_difference_lists(left, right, &result)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_list(result);
    return 1;
}

static int enact_builtin_union(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *left = NULL;
    EnactList *right = NULL;
    EnactList *left_only = NULL;
    EnactList *result = NULL;

    (void)argument_count;

    if (!enact_builtin_require_list(&arguments[0], &left, diag)) {
        return 0;
    }
    if (!enact_builtin_require_list(&arguments[1], &right, diag)) {
        return 0;
    }
    if (!enact_builtin_difference_lists(left, right, &left_only)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }
    if (!enact_builtin_append_lists(left_only, right, &result)) {
        enact_list_release(left_only);
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    enact_list_release(left_only);
    *out = enact_value_make_list(result);
    return 1;
}

static int enact_builtin_intersection_lists(
    EnactList *left,
    EnactList *right,
    EnactList **out)
{
    const EnactValue *head;
    EnactList *filtered_tail = NULL;
    EnactList *result;
    bool in_right = false;

    if (!out) {
        return 0;
    }
    if (!left) {
        *out = NULL;
        return 1;
    }

    head = enact_list_head(left);
    if (!head || !enact_builtin_list_contains_value(right, head, &in_right)) {
        return 0;
    }
    if (!enact_builtin_intersection_lists(enact_list_tail(left), right, &filtered_tail)) {
        return 0;
    }

    if (!in_right) {
        *out = filtered_tail;
        return 1;
    }

    result = enact_list_cons(head, filtered_tail);
    enact_list_release(filtered_tail);
    if (!result) {
        return 0;
    }

    *out = result;
    return 1;
}

static int enact_builtin_intersection(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *left = NULL;
    EnactList *right = NULL;
    EnactList *result = NULL;

    (void)argument_count;

    if (!enact_builtin_require_list(&arguments[0], &left, diag)) {
        return 0;
    }
    if (!enact_builtin_require_list(&arguments[1], &right, diag)) {
        return 0;
    }
    if (!enact_builtin_intersection_lists(left, right, &result)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_list(result);
    return 1;
}

static const EnactBuiltin builtin_table[] = {
    {"hd", 1, enact_builtin_hd},
    {"tl", 1, enact_builtin_tl},
    {"atom", 1, enact_builtin_atom},
    {"isObject", 1, enact_builtin_is_object},
    {"classof", 1, enact_builtin_classof},
    {"attrs", 1, enact_builtin_attrs},
    {"version", 0, enact_builtin_version},
    {"list", 1, enact_builtin_list},
    {"append", 2, enact_builtin_append},
    {"size", 1, enact_builtin_size},
    {"map", 2, enact_builtin_map},
    {"filter", 2, enact_builtin_filter},
    {"all", 2, enact_builtin_all},
    {"exists", 2, enact_builtin_exists},
    {"reduce", 3, enact_builtin_reduce},
    {"member", 2, enact_builtin_member},
    {"remove", 2, enact_builtin_remove},
    {"unitset", 1, enact_builtin_unitset},
    {"union", 2, enact_builtin_union},
    {"difference", 2, enact_builtin_difference},
    {"intersection", 2, enact_builtin_intersection},
};

static size_t enact_builtin_count(void)
{
    return sizeof(builtin_table) / sizeof(builtin_table[0]);
}

const EnactBuiltin *enact_builtin_lookup(const char *name)
{
    size_t index;

    if (!name) {
        return NULL;
    }

    for (index = 0; index < enact_builtin_count(); index += 1) {
        if (strcmp(builtin_table[index].name, name) == 0) {
            return &builtin_table[index];
        }
    }

    return NULL;
}

const char *enact_builtin_name(const EnactBuiltin *builtin)
{
    return builtin ? builtin->name : "";
}

size_t enact_builtin_arity(const EnactBuiltin *builtin)
{
    return builtin ? builtin->arity : 0;
}

EnactBuiltinPartial *enact_builtin_partial_new(
    const EnactBuiltin *builtin,
    const EnactValue *arguments,
    size_t argument_count)
{
    EnactBuiltinPartial *partial = enact_builtin_partial_alloc(builtin, argument_count);

    if (!partial) {
        return NULL;
    }
    if (!enact_builtin_copy_arguments(partial->arguments, arguments, argument_count)) {
        free(partial->arguments);
        free(partial);
        return NULL;
    }

    return partial;
}

EnactBuiltinPartial *enact_builtin_partial_extend(
    const EnactBuiltinPartial *partial,
    const EnactValue *arguments,
    size_t argument_count)
{
    EnactBuiltinPartial *extended;
    size_t total_count;

    if (!partial || argument_count == 0) {
        return NULL;
    }

    total_count = partial->argument_count + argument_count;
    if (total_count < partial->argument_count) {
        return NULL;
    }
    extended = enact_builtin_partial_alloc(partial->builtin, total_count);
    if (!extended) {
        return NULL;
    }

    if (!enact_builtin_copy_arguments(extended->arguments, partial->arguments, partial->argument_count)) {
        free(extended->arguments);
        free(extended);
        return NULL;
    }
    if (!enact_builtin_copy_arguments(
            extended->arguments + partial->argument_count,
            arguments,
            argument_count)) {
        enact_builtin_free_arguments(extended->arguments, partial->argument_count);
        free(extended);
        return NULL;
    }

    return extended;
}

EnactBuiltinPartial *enact_builtin_partial_retain(EnactBuiltinPartial *partial)
{
    if (!partial) {
        return NULL;
    }

    partial->ref_count += 1;
    return partial;
}

void enact_builtin_partial_release(EnactBuiltinPartial *partial)
{
    if (!partial) {
        return;
    }

    if (partial->ref_count > 1) {
        partial->ref_count -= 1;
        return;
    }

    enact_builtin_free_arguments(partial->arguments, partial->argument_count);
    free(partial);
}

const EnactBuiltin *enact_builtin_partial_builtin(const EnactBuiltinPartial *partial)
{
    return partial ? partial->builtin : NULL;
}

size_t enact_builtin_partial_argument_count(const EnactBuiltinPartial *partial)
{
    return partial ? partial->argument_count : 0;
}

int enact_builtin_apply(
    const EnactBuiltin *builtin,
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    if (!builtin || !out) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }
    if (argument_count != builtin->arity) {
        enact_diag_set(diag, ENACT_ERR_ARITY_MISMATCH, -1);
        return 0;
    }
    if (argument_count > 0 && !arguments) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }

    return builtin->callback(arguments, argument_count, out, diag);
}

int enact_builtin_partial_apply(
    const EnactBuiltinPartial *partial,
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactValue *combined;
    size_t prefix_count;
    size_t total_count;
    int status;

    if (!partial || !out) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }

    prefix_count = partial->argument_count;
    total_count = prefix_count + argument_count;
    if (total_count != enact_builtin_arity(partial->builtin)) {
        enact_diag_set(diag, ENACT_ERR_ARITY_MISMATCH, -1);
        return 0;
    }
    if (argument_count > 0 && !arguments) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }

    combined = calloc(total_count, sizeof(*combined));
    if (!combined) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    if (prefix_count > 0) {
        memcpy(combined, partial->arguments, prefix_count * sizeof(*combined));
    }
    if (argument_count > 0) {
        memcpy(combined + prefix_count, arguments, argument_count * sizeof(*combined));
    }

    status = enact_builtin_apply(partial->builtin, combined, total_count, out, diag);
    free(combined);
    return status;
}

int enact_install_builtins(EnactEnv *env)
{
    size_t index;
    EnactClass *object_class;
    EnactValue object_value;

    if (!env) {
        return 0;
    }

    for (index = 0; index < enact_builtin_count(); index += 1) {
        EnactValue value = enact_value_make_builtin(&builtin_table[index]);

        if (!enact_env_define(env, builtin_table[index].name, value)) {
            return 0;
        }
    }

    object_class = enact_class_new("Object");
    if (!object_class) {
        return 0;
    }

    object_value = enact_value_make_class(object_class);
    if (!enact_env_define(env, "Object", object_value)) {
        enact_value_free(&object_value);
        return 0;
    }
    enact_value_free(&object_value);

    return 1;
}
