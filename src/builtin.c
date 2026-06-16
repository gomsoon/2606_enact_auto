#include <limits.h>
#include <string.h>

#include "builtin.h"

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

static const EnactBuiltin builtin_table[] = {
    {"hd", 1, enact_builtin_hd},
    {"tl", 1, enact_builtin_tl},
    {"append", 2, enact_builtin_append},
    {"size", 1, enact_builtin_size},
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

int enact_install_builtins(EnactEnv *env)
{
    size_t index;

    if (!env) {
        return 0;
    }

    for (index = 0; index < enact_builtin_count(); index += 1) {
        EnactValue value = enact_value_make_builtin(&builtin_table[index]);

        if (!enact_env_define(env, builtin_table[index].name, value)) {
            return 0;
        }
    }

    return 1;
}
