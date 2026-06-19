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

typedef int (*EnactBuiltinEnvCallback)(
    EnactEnv *env,
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag);

struct EnactBuiltin {
    const char *name;
    size_t min_arity;
    size_t arity;
    EnactBuiltinCallback callback;
    EnactBuiltinEnvCallback env_callback;
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

    if (!builtin || argument_count == 0 || argument_count >= enact_builtin_min_arity(builtin)) {
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

static int enact_builtin_require_list_or_collection(const EnactValue *value, EnactList **out, EnactDiag *diag)
{
    if (!value || !out) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_LIST, -1);
        return 0;
    }
    if (value->kind == ENACT_VALUE_LIST) {
        *out = value->as.as_list;
        return 1;
    }
    if (value->kind == ENACT_VALUE_OBJECT &&
        enact_object_collection_kind(value->as.as_object) != ENACT_COLLECTION_NONE) {
        *out = enact_object_collection_items(value->as.as_object);
        return 1;
    }

    enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_LIST, -1);
    return 0;
}

static int enact_builtin_require_collection_object(const EnactValue *value, EnactObject **out, EnactDiag *diag)
{
    if (!value || !out ||
        value->kind != ENACT_VALUE_OBJECT ||
        enact_object_collection_kind(value->as.as_object) == ENACT_COLLECTION_NONE) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_LIST, -1);
        return 0;
    }

    *out = value->as.as_object;
    return 1;
}

static int enact_builtin_value_is_collection_object(const EnactValue *value)
{
    return value &&
           value->kind == ENACT_VALUE_OBJECT &&
           enact_object_collection_kind(value->as.as_object) != ENACT_COLLECTION_NONE;
}

static int enact_builtin_require_set_collection_object(const EnactValue *value, EnactObject **out, EnactDiag *diag)
{
    if (!value || !out ||
        value->kind != ENACT_VALUE_OBJECT ||
        enact_object_collection_kind(value->as.as_object) != ENACT_COLLECTION_SET) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_LIST, -1);
        return 0;
    }

    *out = value->as.as_object;
    return 1;
}

static int enact_builtin_require_same_collection_kind(
    const EnactValue *left,
    const EnactValue *right,
    EnactObject **left_out,
    EnactObject **right_out,
    EnactCollectionKind *kind_out,
    EnactDiag *diag)
{
    EnactCollectionKind left_kind;
    EnactCollectionKind right_kind;

    if (!enact_builtin_require_collection_object(left, left_out, diag) ||
        !enact_builtin_require_collection_object(right, right_out, diag)) {
        return 0;
    }

    left_kind = enact_object_collection_kind(*left_out);
    right_kind = enact_object_collection_kind(*right_out);
    if (left_kind != right_kind) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_LIST, -1);
        return 0;
    }

    if (kind_out) {
        *kind_out = left_kind;
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

static int enact_builtin_list_size(EnactList *list, int32_t *out, EnactDiag *diag)
{
    int32_t count = 0;

    if (!out) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
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

    *out = count;
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

static int enact_builtin_methods(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *names = NULL;

    (void)argument_count;

    if (arguments[0].kind != ENACT_VALUE_CLASS) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_CLASS, -1);
        return 0;
    }

    if (!enact_class_method_names(arguments[0].as.as_class, &names)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_list(names);
    return 1;
}

static int enact_builtin_supers(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *superclasses = NULL;

    (void)argument_count;

    if (arguments[0].kind != ENACT_VALUE_CLASS) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_CLASS, -1);
        return 0;
    }

    if (!enact_class_superclasses(arguments[0].as.as_class, &superclasses)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_list(superclasses);
    return 1;
}

static int enact_builtin_classes(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *classes = NULL;
    int is_consistent = 1;

    (void)argument_count;

    if (arguments[0].kind != ENACT_VALUE_CLASS) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_CLASS, -1);
        return 0;
    }

    if (!enact_class_linearization_checked(arguments[0].as.as_class, &classes, &is_consistent)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }
    if (!is_consistent) {
        enact_diag_set(diag, ENACT_ERR_INCONSISTENT_LINEARIZATION, -1);
        return 0;
    }

    *out = enact_value_make_list(classes);
    return 1;
}

static int enact_builtin_superiors(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *classes = NULL;
    EnactList *superiors = NULL;
    int is_consistent = 1;

    (void)argument_count;

    if (arguments[0].kind != ENACT_VALUE_CLASS) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_CLASS, -1);
        return 0;
    }

    if (!enact_class_linearization_checked(arguments[0].as.as_class, &classes, &is_consistent)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }
    if (!is_consistent) {
        enact_diag_set(diag, ENACT_ERR_INCONSISTENT_LINEARIZATION, -1);
        return 0;
    }

    superiors = enact_list_retain(enact_list_tail(classes));
    enact_list_release(classes);

    *out = enact_value_make_list(superiors);
    return 1;
}

static int enact_builtin_ok(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    int is_consistent = 0;

    (void)argument_count;

    if (arguments[0].kind != ENACT_VALUE_CLASS) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_CLASS, -1);
        return 0;
    }

    if (!enact_class_linearization_is_consistent(arguments[0].as.as_class, &is_consistent)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_bool(is_consistent != 0);
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

    if (!enact_builtin_require_list_or_collection(&arguments[0], &list, diag)) {
        return 0;
    }
    if (!enact_builtin_list_size(list, &count, diag)) {
        return 0;
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

static int enact_builtin_collect_list(
    const EnactValue *callable,
    EnactList *list,
    EnactCollectionKind collection_kind,
    EnactList **out,
    EnactDiag *diag)
{
    const EnactValue *head;
    EnactValue mapped_head;
    EnactList *mapped_tail = NULL;
    EnactList *result;
    bool found = false;

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

    if (!enact_builtin_collect_list(
            callable,
            enact_list_tail(list),
            collection_kind,
            &mapped_tail,
            diag)) {
        enact_value_free(&mapped_head);
        return 0;
    }

    if (collection_kind == ENACT_COLLECTION_SET) {
        if (!enact_builtin_list_contains_value(mapped_tail, &mapped_head, &found)) {
            enact_value_free(&mapped_head);
            enact_list_release(mapped_tail);
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }
        if (found) {
            enact_value_free(&mapped_head);
            *out = mapped_tail;
            return 1;
        }
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

static int enact_builtin_collect(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactObject *collection = NULL;
    EnactObject *next_collection;
    EnactCollectionKind collection_kind;
    EnactList *list = NULL;
    EnactList *result = NULL;

    (void)argument_count;

    if (!enact_builtin_require_callable(&arguments[0], diag)) {
        return 0;
    }
    if (!enact_builtin_require_collection_object(&arguments[1], &collection, diag)) {
        return 0;
    }

    collection_kind = enact_object_collection_kind(collection);
    list = enact_object_collection_items(collection);
    if (!enact_builtin_collect_list(&arguments[0], list, collection_kind, &result, diag)) {
        return 0;
    }

    next_collection = enact_object_copy_with_collection_items(collection, result);
    enact_list_release(result);
    if (!next_collection) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_object(next_collection);
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
    EnactObject *collection = NULL;
    EnactObject *next_collection;
    EnactList *list = NULL;
    EnactList *result = NULL;

    (void)argument_count;

    if (!enact_builtin_require_callable(&arguments[0], diag)) {
        return 0;
    }
    if (arguments[1].kind == ENACT_VALUE_OBJECT &&
        enact_object_collection_kind(arguments[1].as.as_object) != ENACT_COLLECTION_NONE) {
        collection = arguments[1].as.as_object;
        list = enact_object_collection_items(collection);
        if (!enact_builtin_filter_list(&arguments[0], list, &result, diag)) {
            return 0;
        }

        next_collection = enact_object_copy_with_collection_items(collection, result);
        enact_list_release(result);
        if (!next_collection) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }

        *out = enact_value_make_object(next_collection);
        return 1;
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
    if (!enact_builtin_require_list_or_collection(&arguments[1], &list, diag)) {
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
    if (!enact_builtin_require_list_or_collection(&arguments[1], &list, diag)) {
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

static int enact_builtin_locate(
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
    if (!enact_builtin_require_list_or_collection(&arguments[1], &list, diag)) {
        return 0;
    }

    while (list) {
        const EnactValue *head = enact_list_head(list);

        if (!head || !enact_builtin_apply_predicate(&arguments[0], head, &result, diag)) {
            return 0;
        }
        if (result) {
            if (!enact_value_copy(out, head)) {
                enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
                return 0;
            }
            return 1;
        }

        list = enact_list_tail(list);
    }

    *out = enact_value_make_list(NULL);
    return 1;
}

static int enact_builtin_for_each_do(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *list = NULL;

    (void)argument_count;

    if (!enact_builtin_require_callable(&arguments[0], diag)) {
        return 0;
    }
    if (!enact_builtin_require_list_or_collection(&arguments[1], &list, diag)) {
        return 0;
    }

    while (list) {
        const EnactValue *head = enact_list_head(list);
        EnactValue result;

        if (!head) {
            enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
            return 0;
        }
        if (!enact_eval_apply_callable(&arguments[0], head, 1, &result, diag)) {
            return 0;
        }

        enact_value_free(&result);
        list = enact_list_tail(list);
    }

    *out = enact_value_make_list(NULL);
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
    if (!enact_builtin_require_list_or_collection(&arguments[2], &list, diag)) {
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

    if (!enact_builtin_require_list_or_collection(&arguments[1], &list, diag)) {
        return 0;
    }
    if (!enact_builtin_list_contains_value(list, &arguments[0], &found)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_bool(found);
    return 1;
}

static int enact_builtin_insert(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactObject *collection = NULL;
    EnactList *items;
    EnactList *next_items = NULL;
    EnactObject *next_collection;
    bool found = false;

    (void)argument_count;

    if (!enact_builtin_require_collection_object(&arguments[1], &collection, diag)) {
        return 0;
    }

    items = enact_object_collection_items(collection);
    if (enact_object_collection_kind(collection) == ENACT_COLLECTION_SET) {
        if (!enact_builtin_list_contains_value(items, &arguments[0], &found)) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }
    }

    if (found) {
        next_items = enact_list_retain(items);
        if (items && !next_items) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }
    } else {
        next_items = enact_list_cons(&arguments[0], items);
        if (!next_items) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }
    }

    next_collection = enact_object_copy_with_collection_items(collection, next_items);
    enact_list_release(next_items);
    if (!next_collection) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_object(next_collection);
    return 1;
}

static int enact_builtin_add(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactObject *set = NULL;

    if (!enact_builtin_require_set_collection_object(&arguments[1], &set, diag)) {
        return 0;
    }

    return enact_builtin_insert(arguments, argument_count, out, diag);
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
    EnactObject *collection = NULL;
    EnactObject *next_collection;
    EnactList *list = NULL;
    EnactList *result = NULL;
    bool removed = false;

    (void)argument_count;

    if (arguments[1].kind == ENACT_VALUE_OBJECT &&
        enact_object_collection_kind(arguments[1].as.as_object) != ENACT_COLLECTION_NONE) {
        collection = arguments[1].as.as_object;
        list = enact_object_collection_items(collection);
        if (!enact_builtin_remove_one(&arguments[0], list, &removed, &result)) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }

        next_collection = enact_object_copy_with_collection_items(collection, result);
        enact_list_release(result);
        if (!next_collection) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }

        *out = enact_value_make_object(next_collection);
        return 1;
    }

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

static int enact_builtin_union_lists(
    EnactList *left,
    EnactList *right,
    EnactList **out)
{
    EnactList *left_only = NULL;
    EnactList *result = NULL;

    if (!out) {
        return 0;
    }
    if (!enact_builtin_difference_lists(left, right, &left_only)) {
        return 0;
    }
    if (!enact_builtin_append_lists(left_only, right, &result)) {
        enact_list_release(left_only);
        return 0;
    }

    enact_list_release(left_only);
    *out = result;
    return 1;
}

static int enact_builtin_difference(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactObject *left_set = NULL;
    EnactObject *right_set = NULL;
    EnactList *left = NULL;
    EnactList *right = NULL;
    EnactList *result = NULL;

    (void)argument_count;

    if (enact_builtin_value_is_collection_object(&arguments[0])) {
        EnactObject *next_collection;

        if (!enact_builtin_require_set_collection_object(&arguments[0], &left_set, diag) ||
            !enact_builtin_require_set_collection_object(&arguments[1], &right_set, diag)) {
            return 0;
        }

        left = enact_object_collection_items(left_set);
        right = enact_object_collection_items(right_set);
        if (!enact_builtin_difference_lists(left, right, &result)) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }

        next_collection = enact_object_copy_with_collection_items(left_set, result);
        enact_list_release(result);
        if (!next_collection) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }

        *out = enact_value_make_object(next_collection);
        return 1;
    }

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
    EnactObject *left_set = NULL;
    EnactObject *right_set = NULL;
    EnactList *left = NULL;
    EnactList *right = NULL;
    EnactList *result = NULL;

    (void)argument_count;

    if (enact_builtin_value_is_collection_object(&arguments[0])) {
        EnactObject *next_collection;

        if (!enact_builtin_require_set_collection_object(&arguments[0], &left_set, diag) ||
            !enact_builtin_require_set_collection_object(&arguments[1], &right_set, diag)) {
            return 0;
        }

        left = enact_object_collection_items(left_set);
        right = enact_object_collection_items(right_set);
        if (!enact_builtin_union_lists(left, right, &result)) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }

        next_collection = enact_object_copy_with_collection_items(left_set, result);
        enact_list_release(result);
        if (!next_collection) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }

        *out = enact_value_make_object(next_collection);
        return 1;
    }

    if (!enact_builtin_require_list(&arguments[0], &left, diag)) {
        return 0;
    }
    if (!enact_builtin_require_list(&arguments[1], &right, diag)) {
        return 0;
    }
    if (!enact_builtin_union_lists(left, right, &result)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

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
    EnactObject *left_set = NULL;
    EnactObject *right_set = NULL;
    EnactList *left = NULL;
    EnactList *right = NULL;
    EnactList *result = NULL;

    (void)argument_count;

    if (enact_builtin_value_is_collection_object(&arguments[0])) {
        EnactObject *next_collection;

        if (!enact_builtin_require_set_collection_object(&arguments[0], &left_set, diag) ||
            !enact_builtin_require_set_collection_object(&arguments[1], &right_set, diag)) {
            return 0;
        }

        left = enact_object_collection_items(left_set);
        right = enact_object_collection_items(right_set);
        if (!enact_builtin_intersection_lists(left, right, &result)) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }

        next_collection = enact_object_copy_with_collection_items(left_set, result);
        enact_list_release(result);
        if (!next_collection) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }

        *out = enact_value_make_object(next_collection);
        return 1;
    }

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

static int enact_builtin_list_is_subset(
    EnactList *left,
    EnactList *right,
    bool *out)
{
    if (!out) {
        return 0;
    }

    while (left) {
        const EnactValue *head = enact_list_head(left);
        bool found = false;

        if (!head || !enact_builtin_list_contains_value(right, head, &found)) {
            return 0;
        }
        if (!found) {
            *out = false;
            return 1;
        }

        left = enact_list_tail(left);
    }

    *out = true;
    return 1;
}

static int enact_builtin_list_count_value(
    EnactList *list,
    const EnactValue *needle,
    size_t *out)
{
    size_t count = 0;

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
            count += 1;
        }

        list = enact_list_tail(list);
    }

    *out = count;
    return 1;
}

static int enact_builtin_list_is_bag_subset(
    EnactList *left,
    EnactList *right,
    bool *out)
{
    if (!out) {
        return 0;
    }

    while (left) {
        const EnactValue *head = enact_list_head(left);
        size_t left_count = 0;
        size_t right_count = 0;

        if (!head ||
            !enact_builtin_list_count_value(left, head, &left_count) ||
            !enact_builtin_list_count_value(right, head, &right_count)) {
            return 0;
        }
        if (left_count > right_count) {
            *out = false;
            return 1;
        }

        left = enact_list_tail(left);
    }

    *out = true;
    return 1;
}

static int enact_builtin_subset(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactObject *left_collection = NULL;
    EnactObject *right_collection = NULL;
    EnactCollectionKind collection_kind = ENACT_COLLECTION_NONE;
    bool result = false;

    (void)argument_count;

    if (!enact_builtin_require_same_collection_kind(
            &arguments[0],
            &arguments[1],
            &left_collection,
            &right_collection,
            &collection_kind,
            diag)) {
        return 0;
    }

    if (collection_kind == ENACT_COLLECTION_SET) {
        if (!enact_builtin_list_is_subset(
                enact_object_collection_items(left_collection),
                enact_object_collection_items(right_collection),
                &result)) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }
    } else if (!enact_builtin_list_is_bag_subset(
            enact_object_collection_items(left_collection),
            enact_object_collection_items(right_collection),
            &result)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_bool(result);
    return 1;
}

static int enact_builtin_equal(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactObject *left_collection = NULL;
    EnactObject *right_collection = NULL;
    EnactCollectionKind collection_kind = ENACT_COLLECTION_NONE;
    bool left_is_subset = false;
    bool right_is_subset = false;

    (void)argument_count;

    if (!enact_builtin_require_same_collection_kind(
            &arguments[0],
            &arguments[1],
            &left_collection,
            &right_collection,
            &collection_kind,
            diag)) {
        return 0;
    }

    if (collection_kind == ENACT_COLLECTION_SET) {
        if (!enact_builtin_list_is_subset(
                enact_object_collection_items(left_collection),
                enact_object_collection_items(right_collection),
                &left_is_subset)) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }
    } else if (!enact_builtin_list_is_bag_subset(
            enact_object_collection_items(left_collection),
            enact_object_collection_items(right_collection),
            &left_is_subset)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }
    if (!left_is_subset) {
        *out = enact_value_make_bool(false);
        return 1;
    }

    if (collection_kind == ENACT_COLLECTION_SET) {
        if (!enact_builtin_list_is_subset(
                enact_object_collection_items(right_collection),
                enact_object_collection_items(left_collection),
                &right_is_subset)) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }
    } else if (!enact_builtin_list_is_bag_subset(
            enact_object_collection_items(right_collection),
            enact_object_collection_items(left_collection),
            &right_is_subset)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_bool(right_is_subset);
    return 1;
}

#define ENACT_BUILTIN(name, arity, callback) {name, arity, arity, callback, NULL}
#define ENACT_ENV_BUILTIN(name, arity, callback) {name, arity, arity, NULL, callback}
#define ENACT_ENV_BUILTIN_RANGE(name, min_arity, arity, callback) {name, min_arity, arity, NULL, callback}

static int enact_builtin_construct_object(
    EnactEnv *env,
    const char *class_name,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactValue class_value;
    EnactObject *object;

    if (!env || !enact_env_lookup(env, class_name, &class_value)) {
        enact_diag_set(diag, ENACT_ERR_NAME_UNBOUND, -1);
        return 0;
    }
    if (class_value.kind != ENACT_VALUE_CLASS) {
        enact_value_free(&class_value);
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_CLASS, -1);
        return 0;
    }

    object = enact_object_new(class_value.as.as_class);
    enact_value_free(&class_value);
    if (!object) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_object(object);
    return 1;
}

static int enact_builtin_collection_items_from_list(
    EnactList *list,
    EnactCollectionKind collection_kind,
    EnactList **out,
    EnactDiag *diag)
{
    const EnactValue *head;
    EnactList *tail = NULL;
    EnactList *result;
    bool found = false;

    if (!out) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }
    if (!list) {
        *out = NULL;
        return 1;
    }

    head = enact_list_head(list);
    if (!head) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }
    if (!enact_builtin_collection_items_from_list(
            enact_list_tail(list),
            collection_kind,
            &tail,
            diag)) {
        return 0;
    }

    if (collection_kind == ENACT_COLLECTION_SET) {
        if (!enact_builtin_list_contains_value(tail, head, &found)) {
            enact_list_release(tail);
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }
        if (found) {
            *out = tail;
            return 1;
        }
    }

    result = enact_list_cons(head, tail);
    enact_list_release(tail);
    if (!result) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = result;
    return 1;
}

static int enact_builtin_construct_collection(
    EnactEnv *env,
    const char *class_name,
    EnactCollectionKind collection_kind,
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactValue object_value;
    EnactList *source = NULL;
    EnactList *items = NULL;
    EnactObject *collection;
    EnactObject *next_collection;

    if (!enact_builtin_construct_object(env, class_name, &object_value, diag)) {
        return 0;
    }
    if (argument_count == 0) {
        *out = object_value;
        return 1;
    }
    if (!enact_builtin_require_list(&arguments[0], &source, diag)) {
        enact_value_free(&object_value);
        return 0;
    }
    if (object_value.kind != ENACT_VALUE_OBJECT ||
        enact_object_collection_kind(object_value.as.as_object) != collection_kind) {
        enact_value_free(&object_value);
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_CLASS, -1);
        return 0;
    }

    collection = object_value.as.as_object;
    if (!enact_builtin_collection_items_from_list(source, collection_kind, &items, diag)) {
        enact_value_free(&object_value);
        return 0;
    }

    next_collection = enact_object_copy_with_collection_items(collection, items);
    enact_list_release(items);
    enact_value_free(&object_value);
    if (!next_collection) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_object(next_collection);
    return 1;
}

static int enact_builtin_set(
    EnactEnv *env,
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    return enact_builtin_construct_collection(
        env,
        "Set",
        ENACT_COLLECTION_SET,
        arguments,
        argument_count,
        out,
        diag);
}

static int enact_builtin_bag(
    EnactEnv *env,
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    return enact_builtin_construct_collection(
        env,
        "Bag",
        ENACT_COLLECTION_BAG,
        arguments,
        argument_count,
        out,
        diag);
}

static int enact_builtin_union_aggregate_lists(
    EnactList *sets,
    EnactObject **prototype,
    EnactList **out,
    EnactDiag *diag)
{
    EnactList *result = NULL;

    if (!prototype || !out) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }

    *prototype = NULL;
    while (sets) {
        const EnactValue *head = enact_list_head(sets);
        EnactObject *set = NULL;
        EnactList *next_result = NULL;

        if (!head || !enact_builtin_require_set_collection_object(head, &set, diag)) {
            enact_list_release(result);
            return 0;
        }
        if (!*prototype) {
            *prototype = set;
        }

        if (!enact_builtin_union_lists(result, enact_object_collection_items(set), &next_result)) {
            enact_list_release(result);
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }

        enact_list_release(result);
        result = next_result;
        sets = enact_list_tail(sets);
    }

    *out = result;
    return 1;
}

static int enact_builtin_union_aggregate(
    EnactEnv *env,
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *sets = NULL;
    EnactList *result = NULL;
    EnactObject *prototype = NULL;
    EnactObject *next_collection;

    (void)argument_count;

    if (!enact_builtin_require_list(&arguments[0], &sets, diag)) {
        return 0;
    }
    if (!enact_builtin_union_aggregate_lists(sets, &prototype, &result, diag)) {
        return 0;
    }

    if (!prototype) {
        return enact_builtin_construct_object(env, "Set", out, diag);
    }

    next_collection = enact_object_copy_with_collection_items(prototype, result);
    enact_list_release(result);
    if (!next_collection) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_object(next_collection);
    return 1;
}

static const EnactBuiltin builtin_table[] = {
    ENACT_BUILTIN("hd", 1, enact_builtin_hd),
    ENACT_BUILTIN("tl", 1, enact_builtin_tl),
    ENACT_BUILTIN("atom", 1, enact_builtin_atom),
    ENACT_BUILTIN("isObject", 1, enact_builtin_is_object),
    ENACT_BUILTIN("classof", 1, enact_builtin_classof),
    ENACT_BUILTIN("attrs", 1, enact_builtin_attrs),
    ENACT_BUILTIN("methods", 1, enact_builtin_methods),
    ENACT_BUILTIN("classes", 1, enact_builtin_classes),
    ENACT_BUILTIN("supers", 1, enact_builtin_supers),
    ENACT_BUILTIN("superiors", 1, enact_builtin_superiors),
    ENACT_BUILTIN("OK", 1, enact_builtin_ok),
    ENACT_BUILTIN("version", 0, enact_builtin_version),
    ENACT_BUILTIN("list", 1, enact_builtin_list),
    ENACT_ENV_BUILTIN_RANGE("set", 0, 1, enact_builtin_set),
    ENACT_ENV_BUILTIN_RANGE("bag", 0, 1, enact_builtin_bag),
    ENACT_BUILTIN("append", 2, enact_builtin_append),
    ENACT_BUILTIN("size", 1, enact_builtin_size),
    ENACT_BUILTIN("map", 2, enact_builtin_map),
    ENACT_BUILTIN("collect", 2, enact_builtin_collect),
    ENACT_BUILTIN("filter", 2, enact_builtin_filter),
    ENACT_BUILTIN("select", 2, enact_builtin_filter),
    ENACT_BUILTIN("all", 2, enact_builtin_all),
    ENACT_BUILTIN("exists", 2, enact_builtin_exists),
    ENACT_BUILTIN("locate", 2, enact_builtin_locate),
    ENACT_BUILTIN("forEachDo", 2, enact_builtin_for_each_do),
    ENACT_BUILTIN("reduce", 3, enact_builtin_reduce),
    ENACT_BUILTIN("member", 2, enact_builtin_member),
    ENACT_BUILTIN("insert", 2, enact_builtin_insert),
    ENACT_BUILTIN("add", 2, enact_builtin_add),
    ENACT_BUILTIN("remove", 2, enact_builtin_remove),
    ENACT_BUILTIN("unitset", 1, enact_builtin_unitset),
    ENACT_BUILTIN("union", 2, enact_builtin_union),
    ENACT_ENV_BUILTIN("UNION", 1, enact_builtin_union_aggregate),
    ENACT_BUILTIN("difference", 2, enact_builtin_difference),
    ENACT_BUILTIN("intersection", 2, enact_builtin_intersection),
    ENACT_BUILTIN("subset", 2, enact_builtin_subset),
    ENACT_BUILTIN("equal", 2, enact_builtin_equal),
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

size_t enact_builtin_min_arity(const EnactBuiltin *builtin)
{
    return builtin ? builtin->min_arity : 0;
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
    return enact_builtin_apply_in_env(builtin, NULL, arguments, argument_count, out, diag);
}

int enact_builtin_apply_in_env(
    const EnactBuiltin *builtin,
    EnactEnv *env,
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    if (!builtin || !out) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }
    if (argument_count < builtin->min_arity || argument_count > builtin->arity) {
        enact_diag_set(diag, ENACT_ERR_ARITY_MISMATCH, -1);
        return 0;
    }
    if (argument_count > 0 && !arguments) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }

    if (builtin->callback) {
        return builtin->callback(arguments, argument_count, out, diag);
    }
    if (builtin->env_callback) {
        return builtin->env_callback(env, arguments, argument_count, out, diag);
    }

    enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
    return 0;
}

int enact_builtin_partial_apply(
    const EnactBuiltinPartial *partial,
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    return enact_builtin_partial_apply_in_env(partial, NULL, arguments, argument_count, out, diag);
}

int enact_builtin_partial_apply_in_env(
    const EnactBuiltinPartial *partial,
    EnactEnv *env,
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
    if (total_count < enact_builtin_min_arity(partial->builtin) ||
        total_count > enact_builtin_arity(partial->builtin)) {
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

    status = enact_builtin_apply_in_env(partial->builtin, env, combined, total_count, out, diag);
    free(combined);
    return status;
}

static int enact_install_class(EnactEnv *env, const char *name, EnactClass *superclass, EnactClass **out)
{
    EnactClass *class_value;
    EnactValue value;

    if (!env || !name) {
        return 0;
    }

    class_value = enact_class_new_with_superclass(name, superclass);
    if (!class_value) {
        return 0;
    }

    value = enact_value_make_class(class_value);
    if (!enact_env_define(env, name, value)) {
        enact_value_free(&value);
        return 0;
    }
    if (out) {
        *out = enact_class_retain(class_value);
        if (!*out) {
            enact_value_free(&value);
            return 0;
        }
    }
    enact_value_free(&value);
    return 1;
}

int enact_install_builtins(EnactEnv *env)
{
    size_t index;
    EnactClass *object_class;
    EnactClass *set_class = NULL;
    EnactClass *bag_class = NULL;

    if (!env) {
        return 0;
    }

    for (index = 0; index < enact_builtin_count(); index += 1) {
        EnactValue value = enact_value_make_builtin(&builtin_table[index]);

        if (!enact_env_define(env, builtin_table[index].name, value)) {
            return 0;
        }
    }

    if (!enact_install_class(env, "Object", NULL, &object_class)) {
        return 0;
    }
    if (!enact_install_class(env, "Set", object_class, &set_class)) {
        enact_class_release(object_class);
        return 0;
    }
    if (!enact_install_class(env, "Bag", object_class, &bag_class)) {
        enact_class_release(set_class);
        enact_class_release(object_class);
        return 0;
    }

    enact_class_release(bag_class);
    enact_class_release(set_class);
    enact_class_release(object_class);

    return 1;
}
