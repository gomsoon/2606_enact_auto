#include <limits.h>
#include <stdlib.h>
#include <string.h>

#include "builtin.h"
#include "eval.h"
#include "function.h"
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
    const char *const *param_names;
};

struct EnactBuiltinPartial {
    size_t ref_count;
    const EnactBuiltin *builtin;
    EnactValue *arguments;
    size_t argument_count;
};

typedef struct {
    const char *name;
    unsigned kinds;
    size_t receiver_index;
} EnactNativeCollectionMethod;

#define ENACT_COLLECTION_METHOD_SET ((unsigned)ENACT_COLLECTION_SET)
#define ENACT_COLLECTION_METHOD_BAG ((unsigned)ENACT_COLLECTION_BAG)
#define ENACT_COLLECTION_METHOD_ANY (ENACT_COLLECTION_METHOD_SET | ENACT_COLLECTION_METHOD_BAG)

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

static int enact_builtin_effective_methods_add_native_collection_methods(
    EnactClass *class_value,
    EnactList **names);

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
         value->kind != ENACT_VALUE_BUILTIN_PARTIAL &&
         value->kind != ENACT_VALUE_BOUND_OBJECT_METHOD &&
         value->kind != ENACT_VALUE_BOUND_COLLECTION_METHOD)) {
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

static EnactClass *enact_builtin_class_or_object_class(const EnactValue *value, EnactDiag *diag)
{
    if (!value) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT, -1);
        return NULL;
    }
    if (value->kind == ENACT_VALUE_CLASS) {
        return value->as.as_class;
    }
    if (value->kind == ENACT_VALUE_OBJECT) {
        return enact_object_class(value->as.as_object);
    }

    enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT, -1);
    return NULL;
}

static int enact_builtin_native_collection_method_signature(
    const EnactClass *class_value,
    const char *method_name,
    const EnactBuiltin **builtin_out,
    size_t *receiver_index_out)
{
    EnactCollectionKind collection_kind;

    if (!class_value || !method_name || !builtin_out || !receiver_index_out) {
        return 0;
    }

    collection_kind = enact_class_collection_kind(class_value);
    if (collection_kind == ENACT_COLLECTION_NONE) {
        return 0;
    }

    return enact_builtin_collection_method(
        collection_kind,
        method_name,
        builtin_out,
        receiver_index_out);
}

static int enact_builtin_methods(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactClass *class_value;
    EnactList *names = NULL;

    (void)argument_count;

    class_value = enact_builtin_class_or_object_class(&arguments[0], diag);
    if (!class_value) {
        return 0;
    }

    if (!enact_class_method_names(class_value, &names)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_list(names);
    return 1;
}

static int enact_builtin_effective_methods(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactClass *class_value;
    EnactList *names = NULL;
    int is_consistent = 1;

    (void)argument_count;

    class_value = enact_builtin_class_or_object_class(&arguments[0], diag);
    if (!class_value) {
        return 0;
    }

    if (!enact_class_effective_method_names(class_value, &names, &is_consistent)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }
    if (!is_consistent) {
        enact_diag_set(diag, ENACT_ERR_INCONSISTENT_LINEARIZATION, -1);
        return 0;
    }
    if (!enact_builtin_effective_methods_add_native_collection_methods(class_value, &names)) {
        enact_list_release(names);
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
    EnactClass *class_value;
    EnactList *superclasses = NULL;

    (void)argument_count;

    class_value = enact_builtin_class_or_object_class(&arguments[0], diag);
    if (!class_value) {
        return 0;
    }

    if (!enact_class_superclasses(class_value, &superclasses)) {
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
    EnactClass *class_value;
    EnactList *classes = NULL;
    int is_consistent = 1;

    (void)argument_count;

    class_value = enact_builtin_class_or_object_class(&arguments[0], diag);
    if (!class_value) {
        return 0;
    }

    if (!enact_class_linearization_checked(class_value, &classes, &is_consistent)) {
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
    EnactClass *class_value;
    EnactList *classes = NULL;
    EnactList *superiors = NULL;
    int is_consistent = 1;

    (void)argument_count;

    class_value = enact_builtin_class_or_object_class(&arguments[0], diag);
    if (!class_value) {
        return 0;
    }

    if (!enact_class_linearization_checked(class_value, &classes, &is_consistent)) {
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
    EnactClass *class_value;

    (void)argument_count;

    class_value = enact_builtin_class_or_object_class(&arguments[0], diag);
    if (!class_value) {
        return 0;
    }

    if (!enact_class_linearization_is_consistent(class_value, &is_consistent)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_bool(is_consistent != 0);
    return 1;
}

static int enact_builtin_bad_attrs(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *names = NULL;
    EnactClass *class_value;

    (void)argument_count;

    class_value = enact_builtin_class_or_object_class(&arguments[0], diag);
    if (!class_value) {
        return 0;
    }

    if (!enact_class_bad_attribute_names(class_value, &names)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_list(names);
    return 1;
}

static int enact_builtin_suppliers(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *classes = NULL;
    EnactClass *class_value;

    (void)argument_count;

    class_value = enact_builtin_class_or_object_class(&arguments[0], diag);
    if (!class_value) {
        return 0;
    }
    if (arguments[1].kind != ENACT_VALUE_ATOM) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_ATOM, -1);
        return 0;
    }

    if (!enact_class_attribute_suppliers(class_value, arguments[1].as.as_atom, &classes)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_list(classes);
    return 1;
}

static int enact_builtin_method_supplier(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactClass *class_value;
    EnactClass *supplier = NULL;
    EnactFunction *method = NULL;
    int is_consistent = 1;

    (void)argument_count;

    class_value = enact_builtin_class_or_object_class(&arguments[0], diag);
    if (!class_value) {
        return 0;
    }
    if (arguments[1].kind != ENACT_VALUE_ATOM) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_ATOM, -1);
        return 0;
    }

    if (!enact_class_lookup_method_with_supplier(
            class_value,
            arguments[1].as.as_atom,
            &method,
            &supplier,
            &is_consistent)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }
    if (!is_consistent) {
        enact_diag_set(diag, ENACT_ERR_INCONSISTENT_LINEARIZATION, -1);
        return 0;
    }
    if (method) {
        enact_function_release(method);
    }
    if (!supplier) {
        *out = enact_value_make_list(NULL);
        return 1;
    }

    supplier = enact_class_retain(supplier);
    if (!supplier) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_class(supplier);
    return 1;
}

static int enact_builtin_has_method(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactClass *class_value;
    EnactFunction *method = NULL;
    const EnactBuiltin *native_builtin = NULL;
    size_t native_arity;
    size_t receiver_index = 0;
    int is_consistent = 1;
    int has_method = 0;

    (void)argument_count;

    class_value = enact_builtin_class_or_object_class(&arguments[0], diag);
    if (!class_value) {
        return 0;
    }
    if (arguments[1].kind != ENACT_VALUE_ATOM) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_ATOM, -1);
        return 0;
    }

    if (!enact_class_lookup_method(
            class_value,
            arguments[1].as.as_atom,
            &method,
            &is_consistent)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }
    if (!is_consistent) {
        enact_diag_set(diag, ENACT_ERR_INCONSISTENT_LINEARIZATION, -1);
        return 0;
    }
    if (method) {
        enact_function_release(method);
        has_method = 1;
    } else if (enact_builtin_native_collection_method_signature(
            class_value,
            arguments[1].as.as_atom,
            &native_builtin,
            &receiver_index)) {
        native_arity = enact_builtin_arity(native_builtin);
        if (native_arity == 0 || receiver_index >= native_arity) {
            enact_diag_set(diag, ENACT_ERR_ARITY_MISMATCH, -1);
            return 0;
        }
        has_method = 1;
    }

    *out = enact_value_make_bool(has_method != 0);
    return 1;
}

static int enact_builtin_method_arity(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactClass *class_value;
    EnactClass *supplier = NULL;
    EnactFunction *method = NULL;
    const EnactBuiltin *native_builtin = NULL;
    size_t arity;
    size_t receiver_index = 0;
    int is_consistent = 1;

    (void)argument_count;

    class_value = enact_builtin_class_or_object_class(&arguments[0], diag);
    if (!class_value) {
        return 0;
    }
    if (arguments[1].kind != ENACT_VALUE_ATOM) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_ATOM, -1);
        return 0;
    }

    if (!enact_class_lookup_method_with_supplier(
            class_value,
            arguments[1].as.as_atom,
            &method,
            &supplier,
            &is_consistent)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }
    if (!is_consistent) {
        enact_diag_set(diag, ENACT_ERR_INCONSISTENT_LINEARIZATION, -1);
        return 0;
    }
    if (method) {
        arity = enact_function_arity(method);
        enact_function_release(method);
    } else if (enact_builtin_native_collection_method_signature(
            class_value,
            arguments[1].as.as_atom,
            &native_builtin,
            &receiver_index)) {
        arity = enact_builtin_arity(native_builtin);
        if (arity == 0 || receiver_index >= arity) {
            enact_diag_set(diag, ENACT_ERR_ARITY_MISMATCH, -1);
            return 0;
        }
        arity -= 1;
    } else {
        *out = enact_value_make_list(NULL);
        return 1;
    }

    if (arity > (size_t)INT_MAX) {
        enact_diag_set(diag, ENACT_ERR_INT_OVERFLOW, -1);
        return 0;
    }

    *out = enact_value_make_int((int32_t)arity);
    return 1;
}

static int enact_builtin_prepend_atom_name(const char *name, EnactList **list)
{
    char *name_copy;
    EnactValue name_value;
    EnactList *next;

    if (!list) {
        return 0;
    }

    name_copy = enact_builtin_copy_text(name);
    if (!name_copy) {
        return 0;
    }

    name_value = enact_value_make_atom(name_copy);
    next = enact_list_cons(&name_value, *list);
    enact_value_free(&name_value);
    if (!next) {
        return 0;
    }

    enact_list_release(*list);
    *list = next;
    return 1;
}

static int enact_builtin_function_params_to_list(
    const EnactFunction *function,
    size_t start_index,
    EnactList **out)
{
    EnactList *result = NULL;
    size_t index;

    if (!function || !out || start_index > enact_function_arity(function)) {
        return 0;
    }

    index = enact_function_arity(function);
    while (index > start_index) {
        index -= 1;
        if (!enact_builtin_prepend_atom_name(enact_function_param_name(function, index), &result)) {
            enact_list_release(result);
            return 0;
        }
    }

    *out = result;
    return 1;
}

static int enact_builtin_param_names_to_list(
    const char *const *param_names,
    size_t param_count,
    size_t start_index,
    EnactList **out)
{
    EnactList *result = NULL;
    size_t index;

    if (!out || start_index > param_count) {
        return 0;
    }
    if (!param_names) {
        *out = NULL;
        return 1;
    }

    index = param_count;
    while (index > start_index) {
        index -= 1;
        if (!enact_builtin_prepend_atom_name(param_names[index], &result)) {
            enact_list_release(result);
            return 0;
        }
    }

    *out = result;
    return 1;
}

static int enact_builtin_params_to_list(
    const EnactBuiltin *builtin,
    size_t start_index,
    EnactList **out)
{
    if (!builtin) {
        return 0;
    }

    return enact_builtin_param_names_to_list(
        builtin->param_names,
        enact_builtin_arity(builtin),
        start_index,
        out);
}

static int enact_builtin_collection_method_params_to_list(
    const EnactBuiltin *builtin,
    size_t receiver_index,
    size_t captured_count,
    EnactList **out)
{
    EnactList *result = NULL;
    size_t arity;
    size_t index;

    if (!builtin || !out) {
        return 0;
    }
    if (!builtin->param_names) {
        *out = NULL;
        return 1;
    }

    arity = enact_builtin_arity(builtin);
    if (arity == 0 || receiver_index >= arity || captured_count > arity - 1) {
        return 0;
    }

    index = arity;
    while (index > 0) {
        size_t visible_index;

        index -= 1;
        if (index == receiver_index) {
            continue;
        }

        visible_index = index < receiver_index ? index : index - 1;
        if (visible_index < captured_count) {
            continue;
        }
        if (!enact_builtin_prepend_atom_name(builtin->param_names[index], &result)) {
            enact_list_release(result);
            return 0;
        }
    }

    *out = result;
    return 1;
}

static int enact_builtin_bound_collection_params_to_list(
    const EnactBoundCollectionMethod *method,
    EnactList **out)
{
    if (!method) {
        return 0;
    }

    return enact_builtin_collection_method_params_to_list(
        enact_bound_collection_method_builtin(method),
        enact_bound_collection_method_receiver_index(method),
        enact_bound_collection_method_argument_count(method),
        out);
}

static int enact_builtin_method_params(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactClass *class_value;
    EnactClass *supplier = NULL;
    EnactFunction *method = NULL;
    const EnactBuiltin *native_builtin = NULL;
    EnactList *params = NULL;
    size_t receiver_index = 0;
    int is_consistent = 1;

    (void)argument_count;

    class_value = enact_builtin_class_or_object_class(&arguments[0], diag);
    if (!class_value) {
        return 0;
    }
    if (arguments[1].kind != ENACT_VALUE_ATOM) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_ATOM, -1);
        return 0;
    }

    if (!enact_class_lookup_method_with_supplier(
            class_value,
            arguments[1].as.as_atom,
            &method,
            &supplier,
            &is_consistent)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }
    if (!is_consistent) {
        enact_diag_set(diag, ENACT_ERR_INCONSISTENT_LINEARIZATION, -1);
        return 0;
    }
    if (method) {
        if (!enact_builtin_function_params_to_list(method, 0, &params)) {
            enact_function_release(method);
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }
        enact_function_release(method);
    } else if (enact_builtin_native_collection_method_signature(
            class_value,
            arguments[1].as.as_atom,
            &native_builtin,
            &receiver_index)) {
        if (!enact_builtin_collection_method_params_to_list(
                native_builtin,
                receiver_index,
                0,
                &params)) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }
    } else {
        *out = enact_value_make_list(NULL);
        return 1;
    }

    *out = enact_value_make_list(params);
    return 1;
}

static int enact_builtin_callable_params(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *params = NULL;

    (void)argument_count;

    if (!enact_builtin_require_callable(&arguments[0], diag)) {
        return 0;
    }

    switch (arguments[0].kind) {
    case ENACT_VALUE_FUNCTION:
        if (!enact_builtin_function_params_to_list(arguments[0].as.as_function, 0, &params)) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }
        *out = enact_value_make_list(params);
        return 1;
    case ENACT_VALUE_BUILTIN:
        if (!enact_builtin_params_to_list(arguments[0].as.as_builtin, 0, &params)) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }
        *out = enact_value_make_list(params);
        return 1;
    case ENACT_VALUE_BUILTIN_PARTIAL: {
        const EnactBuiltin *builtin = enact_builtin_partial_builtin(arguments[0].as.as_builtin_partial);
        size_t captured_count = enact_builtin_partial_argument_count(arguments[0].as.as_builtin_partial);

        if (!builtin || captured_count > enact_builtin_arity(builtin)) {
            enact_diag_set(diag, ENACT_ERR_ARITY_MISMATCH, -1);
            return 0;
        }
        if (!enact_builtin_params_to_list(builtin, captured_count, &params)) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }
        *out = enact_value_make_list(params);
        return 1;
    }
    case ENACT_VALUE_BOUND_COLLECTION_METHOD:
        if (!enact_builtin_bound_collection_params_to_list(arguments[0].as.as_bound_collection_method, &params)) {
            enact_diag_set(diag, ENACT_ERR_ARITY_MISMATCH, -1);
            return 0;
        }
        *out = enact_value_make_list(params);
        return 1;
    case ENACT_VALUE_BOUND_OBJECT_METHOD: {
        EnactBoundObjectMethod *method = arguments[0].as.as_bound_object_method;
        EnactFunction *function = enact_bound_object_method_function(method);
        size_t captured_count = enact_bound_object_method_argument_count(method);

        if (!function || captured_count > enact_function_arity(function)) {
            enact_diag_set(diag, ENACT_ERR_ARITY_MISMATCH, -1);
            return 0;
        }
        if (!enact_builtin_function_params_to_list(function, captured_count, &params)) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }
        *out = enact_value_make_list(params);
        return 1;
    }
    default:
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_FUNCTION, -1);
        return 0;
    }
}

static int enact_builtin_callable_remaining_arity_range(
    const EnactValue *value,
    size_t *min_out,
    size_t *max_out,
    EnactDiag *diag)
{
    size_t min_arity;
    size_t arity;
    size_t captured_count;

    if (!min_out || !max_out) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }
    if (!enact_builtin_require_callable(value, diag)) {
        return 0;
    }

    switch (value->kind) {
    case ENACT_VALUE_FUNCTION:
        arity = enact_function_arity(value->as.as_function);
        *min_out = arity;
        *max_out = arity;
        return 1;
    case ENACT_VALUE_BUILTIN:
        min_arity = enact_builtin_min_arity(value->as.as_builtin);
        arity = enact_builtin_arity(value->as.as_builtin);
        if (min_arity > arity) {
            enact_diag_set(diag, ENACT_ERR_ARITY_MISMATCH, -1);
            return 0;
        }
        *min_out = min_arity;
        *max_out = arity;
        return 1;
    case ENACT_VALUE_BUILTIN_PARTIAL:
        min_arity = enact_builtin_min_arity(enact_builtin_partial_builtin(value->as.as_builtin_partial));
        arity = enact_builtin_arity(enact_builtin_partial_builtin(value->as.as_builtin_partial));
        captured_count = enact_builtin_partial_argument_count(value->as.as_builtin_partial);
        if (min_arity > arity || captured_count > arity) {
            enact_diag_set(diag, ENACT_ERR_ARITY_MISMATCH, -1);
            return 0;
        }
        *min_out = min_arity > captured_count ? min_arity - captured_count : 0;
        *max_out = arity - captured_count;
        return 1;
    case ENACT_VALUE_BOUND_OBJECT_METHOD: {
        EnactBoundObjectMethod *method = value->as.as_bound_object_method;
        EnactFunction *function = enact_bound_object_method_function(method);

        captured_count = enact_bound_object_method_argument_count(method);
        arity = enact_function_arity(function);
        if (!function || captured_count > arity) {
            enact_diag_set(diag, ENACT_ERR_ARITY_MISMATCH, -1);
            return 0;
        }
        arity -= captured_count;
        *min_out = arity;
        *max_out = arity;
        return 1;
    }
    case ENACT_VALUE_BOUND_COLLECTION_METHOD: {
        EnactBoundCollectionMethod *method = value->as.as_bound_collection_method;
        const EnactBuiltin *builtin = enact_bound_collection_method_builtin(method);

        arity = enact_builtin_arity(builtin);
        captured_count = enact_bound_collection_method_argument_count(method);
        if (!builtin ||
            arity == 0 ||
            enact_bound_collection_method_receiver_index(method) >= arity ||
            captured_count > arity - 1) {
            enact_diag_set(diag, ENACT_ERR_ARITY_MISMATCH, -1);
            return 0;
        }
        arity = arity - 1 - captured_count;
        *min_out = arity;
        *max_out = arity;
        return 1;
    }
    default:
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_FUNCTION, -1);
        return 0;
    }
}

static int enact_builtin_callable_remaining_arity(
    const EnactValue *value,
    size_t *out,
    EnactDiag *diag)
{
    size_t min_arity;

    return enact_builtin_callable_remaining_arity_range(value, &min_arity, out, diag);
}

static int enact_builtin_callable_arity(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    size_t arity;

    (void)argument_count;

    if (!enact_builtin_callable_remaining_arity(&arguments[0], &arity, diag)) {
        return 0;
    }
    if (arity > (size_t)INT_MAX) {
        enact_diag_set(diag, ENACT_ERR_INT_OVERFLOW, -1);
        return 0;
    }

    *out = enact_value_make_int((int32_t)arity);
    return 1;
}

static int enact_builtin_callable_min_arity(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    size_t min_arity;
    size_t max_arity;

    (void)argument_count;

    if (!enact_builtin_callable_remaining_arity_range(&arguments[0], &min_arity, &max_arity, diag)) {
        return 0;
    }
    if (min_arity > (size_t)INT_MAX) {
        enact_diag_set(diag, ENACT_ERR_INT_OVERFLOW, -1);
        return 0;
    }

    *out = enact_value_make_int((int32_t)min_arity);
    return 1;
}

static int enact_builtin_int_pair_list(int32_t first, int32_t second, EnactList **out)
{
    EnactValue first_value;
    EnactValue second_value;
    EnactList *second_node;
    EnactList *first_node;

    if (!out) {
        return 0;
    }

    second_value = enact_value_make_int(second);
    second_node = enact_list_cons(&second_value, NULL);
    if (!second_node) {
        return 0;
    }

    first_value = enact_value_make_int(first);
    first_node = enact_list_cons(&first_value, second_node);
    enact_list_release(second_node);
    if (!first_node) {
        return 0;
    }

    *out = first_node;
    return 1;
}

static int enact_builtin_callable_arity_range(
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag)
{
    EnactList *range = NULL;
    size_t min_arity;
    size_t max_arity;

    (void)argument_count;

    if (!enact_builtin_callable_remaining_arity_range(&arguments[0], &min_arity, &max_arity, diag)) {
        return 0;
    }
    if (min_arity > (size_t)INT_MAX || max_arity > (size_t)INT_MAX) {
        enact_diag_set(diag, ENACT_ERR_INT_OVERFLOW, -1);
        return 0;
    }
    if (!enact_builtin_int_pair_list((int32_t)min_arity, (int32_t)max_arity, &range)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = enact_value_make_list(range);
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

static int enact_builtin_bag_difference_lists(
    EnactList *left,
    EnactList *right,
    EnactList **out)
{
    const EnactValue *head;
    EnactList *filtered_tail = NULL;
    EnactList *result;
    size_t left_count = 0;
    size_t right_count = 0;

    if (!out) {
        return 0;
    }
    if (!left) {
        *out = NULL;
        return 1;
    }

    head = enact_list_head(left);
    if (!head ||
        !enact_builtin_list_count_value(left, head, &left_count) ||
        !enact_builtin_list_count_value(right, head, &right_count)) {
        return 0;
    }
    if (!enact_builtin_bag_difference_lists(enact_list_tail(left), right, &filtered_tail)) {
        return 0;
    }

    if (left_count <= right_count) {
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

static int enact_builtin_bag_union_lists(
    EnactList *left,
    EnactList *right,
    EnactList **out)
{
    EnactList *left_only = NULL;
    EnactList *result = NULL;

    if (!out) {
        return 0;
    }
    if (!enact_builtin_bag_difference_lists(left, right, &left_only)) {
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

static int enact_builtin_bag_intersection_lists(
    EnactList *left,
    EnactList *right,
    EnactList **out)
{
    const EnactValue *head;
    EnactList *filtered_tail = NULL;
    EnactList *result;
    size_t left_count = 0;
    size_t right_count = 0;

    if (!out) {
        return 0;
    }
    if (!left) {
        *out = NULL;
        return 1;
    }

    head = enact_list_head(left);
    if (!head ||
        !enact_builtin_list_count_value(left, head, &left_count) ||
        !enact_builtin_list_count_value(right, head, &right_count)) {
        return 0;
    }
    if (!enact_builtin_bag_intersection_lists(enact_list_tail(left), right, &filtered_tail)) {
        return 0;
    }

    if (left_count > right_count) {
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
    EnactObject *left_collection = NULL;
    EnactObject *right_collection = NULL;
    EnactCollectionKind collection_kind = ENACT_COLLECTION_NONE;
    EnactList *left = NULL;
    EnactList *right = NULL;
    EnactList *result = NULL;

    (void)argument_count;

    if (enact_builtin_value_is_collection_object(&arguments[0])) {
        EnactObject *next_collection;

        if (!enact_builtin_require_same_collection_kind(
                &arguments[0],
                &arguments[1],
                &left_collection,
                &right_collection,
                &collection_kind,
                diag)) {
            return 0;
        }

        left = enact_object_collection_items(left_collection);
        right = enact_object_collection_items(right_collection);
        if (collection_kind == ENACT_COLLECTION_SET) {
            if (!enact_builtin_difference_lists(left, right, &result)) {
                enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
                return 0;
            }
        } else if (collection_kind == ENACT_COLLECTION_BAG) {
            if (!enact_builtin_bag_difference_lists(left, right, &result)) {
                enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
                return 0;
            }
        } else {
            enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_LIST, -1);
            return 0;
        }

        next_collection = enact_object_copy_with_collection_items(left_collection, result);
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
    EnactObject *left_collection = NULL;
    EnactObject *right_collection = NULL;
    EnactCollectionKind collection_kind = ENACT_COLLECTION_NONE;
    EnactList *left = NULL;
    EnactList *right = NULL;
    EnactList *result = NULL;

    (void)argument_count;

    if (enact_builtin_value_is_collection_object(&arguments[0])) {
        EnactObject *next_collection;

        if (!enact_builtin_require_same_collection_kind(
                &arguments[0],
                &arguments[1],
                &left_collection,
                &right_collection,
                &collection_kind,
                diag)) {
            return 0;
        }

        left = enact_object_collection_items(left_collection);
        right = enact_object_collection_items(right_collection);
        if (collection_kind == ENACT_COLLECTION_SET) {
            if (!enact_builtin_union_lists(left, right, &result)) {
                enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
                return 0;
            }
        } else if (collection_kind == ENACT_COLLECTION_BAG) {
            if (!enact_builtin_bag_union_lists(left, right, &result)) {
                enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
                return 0;
            }
        } else {
            enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_LIST, -1);
            return 0;
        }

        next_collection = enact_object_copy_with_collection_items(left_collection, result);
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
    EnactObject *left_collection = NULL;
    EnactObject *right_collection = NULL;
    EnactCollectionKind collection_kind = ENACT_COLLECTION_NONE;
    EnactList *left = NULL;
    EnactList *right = NULL;
    EnactList *result = NULL;

    (void)argument_count;

    if (enact_builtin_value_is_collection_object(&arguments[0])) {
        EnactObject *next_collection;

        if (!enact_builtin_require_same_collection_kind(
                &arguments[0],
                &arguments[1],
                &left_collection,
                &right_collection,
                &collection_kind,
                diag)) {
            return 0;
        }

        left = enact_object_collection_items(left_collection);
        right = enact_object_collection_items(right_collection);
        if (collection_kind == ENACT_COLLECTION_SET) {
            if (!enact_builtin_intersection_lists(left, right, &result)) {
                enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
                return 0;
            }
        } else if (collection_kind == ENACT_COLLECTION_BAG) {
            if (!enact_builtin_bag_intersection_lists(left, right, &result)) {
                enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
                return 0;
            }
        } else {
            enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_LIST, -1);
            return 0;
        }

        next_collection = enact_object_copy_with_collection_items(left_collection, result);
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

#define ENACT_BUILTIN(name, arity, callback) {name, arity, arity, callback, NULL, NULL}
#define ENACT_BUILTIN_PARAMS(name, arity, callback, params) {name, arity, arity, callback, NULL, params}
#define ENACT_ENV_BUILTIN(name, arity, callback) {name, arity, arity, NULL, callback, NULL}
#define ENACT_ENV_BUILTIN_PARAMS(name, arity, callback, params) {name, arity, arity, NULL, callback, params}
#define ENACT_ENV_BUILTIN_RANGE(name, min_arity, arity, callback, params) \
    {name, min_arity, arity, NULL, callback, params}

static const char *const enact_builtin_params_value[] = {"value"};
static const char *const enact_builtin_params_list[] = {"list"};
static const char *const enact_builtin_params_object[] = {"object"};
static const char *const enact_builtin_params_target[] = {"target"};
static const char *const enact_builtin_params_callable[] = {"callable"};
static const char *const enact_builtin_params_items[] = {"items"};
static const char *const enact_builtin_params_collection[] = {"collection"};
static const char *const enact_builtin_params_collections[] = {"collections"};
static const char *const enact_builtin_params_left_right[] = {"left", "right"};
static const char *const enact_builtin_params_target_attr[] = {"target", "attr"};
static const char *const enact_builtin_params_target_method[] = {"target", "method"};
static const char *const enact_builtin_params_function_collection[] = {"function", "collection"};
static const char *const enact_builtin_params_predicate_collection[] = {"predicate", "collection"};
static const char *const enact_builtin_params_value_collection[] = {"value", "collection"};
static const char *const enact_builtin_params_function_initial_collection[] = {
    "function",
    "initial",
    "collection",
};

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
    EnactList *collections,
    EnactObject **prototype,
    EnactList **out,
    EnactDiag *diag)
{
    EnactCollectionKind collection_kind = ENACT_COLLECTION_NONE;
    EnactList *result = NULL;

    if (!prototype || !out) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }

    *prototype = NULL;
    while (collections) {
        const EnactValue *head = enact_list_head(collections);
        EnactObject *collection = NULL;
        EnactList *next_result = NULL;
        EnactCollectionKind next_kind;

        if (!head || !enact_builtin_require_collection_object(head, &collection, diag)) {
            enact_list_release(result);
            return 0;
        }

        next_kind = enact_object_collection_kind(collection);
        if (!*prototype) {
            *prototype = collection;
            collection_kind = next_kind;
        } else if (next_kind != collection_kind) {
            enact_list_release(result);
            enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_LIST, -1);
            return 0;
        }

        if (collection_kind == ENACT_COLLECTION_SET) {
            if (!enact_builtin_union_lists(result, enact_object_collection_items(collection), &next_result)) {
                enact_list_release(result);
                enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
                return 0;
            }
        } else if (collection_kind == ENACT_COLLECTION_BAG) {
            if (!enact_builtin_bag_union_lists(result, enact_object_collection_items(collection), &next_result)) {
                enact_list_release(result);
                enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
                return 0;
            }
        } else {
            enact_list_release(result);
            enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_LIST, -1);
            return 0;
        }

        enact_list_release(result);
        result = next_result;
        collections = enact_list_tail(collections);
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
    EnactList *collections = NULL;
    EnactList *result = NULL;
    EnactObject *prototype = NULL;
    EnactObject *next_collection;

    (void)argument_count;

    if (!enact_builtin_require_list_or_collection(&arguments[0], &collections, diag)) {
        return 0;
    }
    if (!enact_builtin_union_aggregate_lists(collections, &prototype, &result, diag)) {
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
    ENACT_BUILTIN_PARAMS("hd", 1, enact_builtin_hd, enact_builtin_params_list),
    ENACT_BUILTIN_PARAMS("tl", 1, enact_builtin_tl, enact_builtin_params_list),
    ENACT_BUILTIN_PARAMS("atom", 1, enact_builtin_atom, enact_builtin_params_value),
    ENACT_BUILTIN_PARAMS("isObject", 1, enact_builtin_is_object, enact_builtin_params_value),
    ENACT_BUILTIN_PARAMS("classof", 1, enact_builtin_classof, enact_builtin_params_object),
    ENACT_BUILTIN_PARAMS("attrs", 1, enact_builtin_attrs, enact_builtin_params_object),
    ENACT_BUILTIN_PARAMS("methods", 1, enact_builtin_methods, enact_builtin_params_target),
    ENACT_BUILTIN_PARAMS("effectiveMethods", 1, enact_builtin_effective_methods, enact_builtin_params_target),
    ENACT_BUILTIN_PARAMS("classes", 1, enact_builtin_classes, enact_builtin_params_target),
    ENACT_BUILTIN_PARAMS("supers", 1, enact_builtin_supers, enact_builtin_params_target),
    ENACT_BUILTIN_PARAMS("superiors", 1, enact_builtin_superiors, enact_builtin_params_target),
    ENACT_BUILTIN_PARAMS("OK", 1, enact_builtin_ok, enact_builtin_params_target),
    ENACT_BUILTIN_PARAMS("badAttrs", 1, enact_builtin_bad_attrs, enact_builtin_params_target),
    ENACT_BUILTIN_PARAMS("suppliers", 2, enact_builtin_suppliers, enact_builtin_params_target_attr),
    ENACT_BUILTIN_PARAMS(
        "methodSupplier",
        2,
        enact_builtin_method_supplier,
        enact_builtin_params_target_method),
    ENACT_BUILTIN_PARAMS("hasMethod", 2, enact_builtin_has_method, enact_builtin_params_target_method),
    ENACT_BUILTIN_PARAMS("methodArity", 2, enact_builtin_method_arity, enact_builtin_params_target_method),
    ENACT_BUILTIN_PARAMS("methodParams", 2, enact_builtin_method_params, enact_builtin_params_target_method),
    ENACT_BUILTIN_PARAMS("callableArity", 1, enact_builtin_callable_arity, enact_builtin_params_callable),
    ENACT_BUILTIN_PARAMS(
        "callableMinArity",
        1,
        enact_builtin_callable_min_arity,
        enact_builtin_params_callable),
    ENACT_BUILTIN_PARAMS("callableParams", 1, enact_builtin_callable_params, enact_builtin_params_callable),
    ENACT_BUILTIN_PARAMS(
        "callableArityRange",
        1,
        enact_builtin_callable_arity_range,
        enact_builtin_params_callable),
    ENACT_BUILTIN("version", 0, enact_builtin_version),
    ENACT_BUILTIN_PARAMS("list", 1, enact_builtin_list, enact_builtin_params_value),
    ENACT_ENV_BUILTIN_RANGE("set", 0, 1, enact_builtin_set, enact_builtin_params_items),
    ENACT_ENV_BUILTIN_RANGE("bag", 0, 1, enact_builtin_bag, enact_builtin_params_items),
    ENACT_BUILTIN_PARAMS("append", 2, enact_builtin_append, enact_builtin_params_left_right),
    ENACT_BUILTIN_PARAMS("size", 1, enact_builtin_size, enact_builtin_params_collection),
    ENACT_BUILTIN_PARAMS("map", 2, enact_builtin_map, enact_builtin_params_function_collection),
    ENACT_BUILTIN_PARAMS("collect", 2, enact_builtin_collect, enact_builtin_params_function_collection),
    ENACT_BUILTIN_PARAMS("filter", 2, enact_builtin_filter, enact_builtin_params_predicate_collection),
    ENACT_BUILTIN_PARAMS("select", 2, enact_builtin_filter, enact_builtin_params_predicate_collection),
    ENACT_BUILTIN_PARAMS("all", 2, enact_builtin_all, enact_builtin_params_predicate_collection),
    ENACT_BUILTIN_PARAMS("exists", 2, enact_builtin_exists, enact_builtin_params_predicate_collection),
    ENACT_BUILTIN_PARAMS("locate", 2, enact_builtin_locate, enact_builtin_params_predicate_collection),
    ENACT_BUILTIN_PARAMS("forEachDo", 2, enact_builtin_for_each_do, enact_builtin_params_function_collection),
    ENACT_BUILTIN_PARAMS("reduce", 3, enact_builtin_reduce, enact_builtin_params_function_initial_collection),
    ENACT_BUILTIN_PARAMS("member", 2, enact_builtin_member, enact_builtin_params_value_collection),
    ENACT_BUILTIN_PARAMS("insert", 2, enact_builtin_insert, enact_builtin_params_value_collection),
    ENACT_BUILTIN_PARAMS("add", 2, enact_builtin_add, enact_builtin_params_value_collection),
    ENACT_BUILTIN_PARAMS("remove", 2, enact_builtin_remove, enact_builtin_params_value_collection),
    ENACT_BUILTIN_PARAMS("unitset", 1, enact_builtin_unitset, enact_builtin_params_value),
    ENACT_BUILTIN_PARAMS("union", 2, enact_builtin_union, enact_builtin_params_left_right),
    ENACT_ENV_BUILTIN_PARAMS("UNION", 1, enact_builtin_union_aggregate, enact_builtin_params_collections),
    ENACT_BUILTIN_PARAMS("difference", 2, enact_builtin_difference, enact_builtin_params_left_right),
    ENACT_BUILTIN_PARAMS("intersection", 2, enact_builtin_intersection, enact_builtin_params_left_right),
    ENACT_BUILTIN_PARAMS("subset", 2, enact_builtin_subset, enact_builtin_params_left_right),
    ENACT_BUILTIN_PARAMS("equal", 2, enact_builtin_equal, enact_builtin_params_left_right),
};

static size_t enact_builtin_count(void)
{
    return sizeof(builtin_table) / sizeof(builtin_table[0]);
}

static const EnactNativeCollectionMethod native_collection_method_table[] = {
    {"size", ENACT_COLLECTION_METHOD_ANY, 0},
    {"union", ENACT_COLLECTION_METHOD_ANY, 0},
    {"difference", ENACT_COLLECTION_METHOD_ANY, 0},
    {"intersection", ENACT_COLLECTION_METHOD_ANY, 0},
    {"subset", ENACT_COLLECTION_METHOD_ANY, 0},
    {"equal", ENACT_COLLECTION_METHOD_ANY, 0},
    {"UNION", ENACT_COLLECTION_METHOD_ANY, 0},
    {"member", ENACT_COLLECTION_METHOD_ANY, 1},
    {"insert", ENACT_COLLECTION_METHOD_ANY, 1},
    {"remove", ENACT_COLLECTION_METHOD_ANY, 1},
    {"add", ENACT_COLLECTION_METHOD_ANY, 1},
    {"collect", ENACT_COLLECTION_METHOD_ANY, 1},
    {"filter", ENACT_COLLECTION_METHOD_ANY, 1},
    {"select", ENACT_COLLECTION_METHOD_ANY, 1},
    {"all", ENACT_COLLECTION_METHOD_ANY, 1},
    {"exists", ENACT_COLLECTION_METHOD_ANY, 1},
    {"locate", ENACT_COLLECTION_METHOD_ANY, 1},
    {"forEachDo", ENACT_COLLECTION_METHOD_ANY, 1},
    {"reduce", ENACT_COLLECTION_METHOD_ANY, 2},
};

static size_t enact_builtin_collection_method_count(void)
{
    return sizeof(native_collection_method_table) / sizeof(native_collection_method_table[0]);
}

static int enact_builtin_list_contains_atom_name(EnactList *list, const char *name, int *out)
{
    if (!name || !out) {
        return 0;
    }

    while (list) {
        const EnactValue *head = enact_list_head(list);

        if (!head) {
            return 0;
        }
        if (head->kind == ENACT_VALUE_ATOM && strcmp(head->as.as_atom, name) == 0) {
            *out = 1;
            return 1;
        }

        list = enact_list_tail(list);
    }

    *out = 0;
    return 1;
}

static int enact_builtin_native_collection_method_names_to_list(
    EnactCollectionKind kind,
    EnactList *existing_names,
    size_t index,
    EnactList **out)
{
    const EnactNativeCollectionMethod *method;
    EnactList *tail = NULL;
    EnactList *result;
    EnactValue name_value;
    char *name_copy;
    int already_present = 0;

    if (!out) {
        return 0;
    }
    if (index >= enact_builtin_collection_method_count()) {
        *out = NULL;
        return 1;
    }

    if (!enact_builtin_native_collection_method_names_to_list(
            kind,
            existing_names,
            index + 1,
            &tail)) {
        return 0;
    }

    method = &native_collection_method_table[index];
    if ((method->kinds & (unsigned)kind) == 0) {
        *out = tail;
        return 1;
    }
    if (!enact_builtin_list_contains_atom_name(existing_names, method->name, &already_present)) {
        enact_list_release(tail);
        return 0;
    }
    if (already_present) {
        *out = tail;
        return 1;
    }

    name_copy = enact_builtin_copy_text(method->name);
    if (!name_copy) {
        enact_list_release(tail);
        return 0;
    }

    name_value = enact_value_make_atom(name_copy);
    result = enact_list_cons(&name_value, tail);
    enact_value_free(&name_value);
    enact_list_release(tail);
    if (!result) {
        return 0;
    }

    *out = result;
    return 1;
}

static int enact_builtin_effective_methods_add_native_collection_methods(
    EnactClass *class_value,
    EnactList **names)
{
    EnactCollectionKind collection_kind;
    EnactList *native_names = NULL;
    EnactList *combined_names = NULL;

    if (!class_value || !names) {
        return 0;
    }

    collection_kind = enact_class_collection_kind(class_value);
    if (collection_kind == ENACT_COLLECTION_NONE) {
        return 1;
    }

    if (!enact_builtin_native_collection_method_names_to_list(
            collection_kind,
            *names,
            0,
            &native_names)) {
        return 0;
    }
    if (!native_names) {
        return 1;
    }

    if (!enact_builtin_append_lists(*names, native_names, &combined_names)) {
        enact_list_release(native_names);
        return 0;
    }

    enact_list_release(native_names);
    enact_list_release(*names);
    *names = combined_names;
    return 1;
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

int enact_builtin_collection_method(
    EnactCollectionKind kind,
    const char *name,
    const EnactBuiltin **builtin_out,
    size_t *receiver_index_out)
{
    const EnactNativeCollectionMethod *method;
    const EnactBuiltin *builtin;
    size_t index;

    if (!name || !builtin_out || !receiver_index_out || kind == ENACT_COLLECTION_NONE) {
        return 0;
    }

    for (index = 0; index < enact_builtin_collection_method_count(); index += 1) {
        method = &native_collection_method_table[index];
        if ((method->kinds & (unsigned)kind) == 0 || strcmp(method->name, name) != 0) {
            continue;
        }

        builtin = enact_builtin_lookup(name);
        if (!builtin) {
            return 0;
        }

        *builtin_out = builtin;
        *receiver_index_out = method->receiver_index;
        return 1;
    }

    return 0;
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
