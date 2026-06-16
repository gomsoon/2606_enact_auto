#include <stdlib.h>
#include <string.h>

#include "function.h"

struct EnactFunction {
    size_t ref_count;
    EnactNameList *param_names;
    EnactAst *body;
    EnactEnv captured_env;
    char *recursive_name;
};

static char *enact_function_copy_text(const char *text)
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

static EnactNameList *enact_function_remaining_params(const EnactFunction *function, size_t argument_count)
{
    EnactNameList *remaining;
    size_t index;
    size_t arity = enact_function_arity(function);

    if (!function || argument_count >= arity) {
        return NULL;
    }

    remaining = enact_name_list_new();
    if (!remaining) {
        return NULL;
    }

    for (index = argument_count; index < arity; index += 1) {
        char *name = enact_function_copy_text(enact_name_list_get(function->param_names, index));

        if (!name || !enact_name_list_append(remaining, name)) {
            free(name);
            enact_name_list_free(remaining);
            return NULL;
        }
    }

    return remaining;
}

static EnactFunction *enact_function_new_with_recursive_name(
    const EnactNameList *param_names,
    const EnactAst *body,
    const EnactEnv *env,
    const char *recursive_name)
{
    EnactFunction *function;

    if (!param_names || enact_name_list_count(param_names) == 0 || !body || !env) {
        return NULL;
    }

    function = calloc(1, sizeof(*function));
    if (!function) {
        return NULL;
    }

    function->ref_count = 1;
    function->param_names = enact_name_list_clone(param_names);
    if (!function->param_names) {
        free(function);
        return NULL;
    }

    function->body = enact_ast_clone(body);
    if (!function->body) {
        enact_name_list_free(function->param_names);
        free(function);
        return NULL;
    }

    if (!enact_env_clone(&function->captured_env, env)) {
        enact_ast_free(function->body);
        enact_name_list_free(function->param_names);
        free(function);
        return NULL;
    }

    if (recursive_name) {
        function->recursive_name = enact_function_copy_text(recursive_name);
        if (!function->recursive_name) {
            enact_env_free(&function->captured_env);
            enact_ast_free(function->body);
            enact_name_list_free(function->param_names);
            free(function);
            return NULL;
        }
    }

    return function;
}

EnactFunction *enact_function_new(const EnactNameList *param_names, const EnactAst *body, const EnactEnv *env)
{
    return enact_function_new_with_recursive_name(param_names, body, env, NULL);
}

EnactFunction *enact_function_new_recursive(
    const EnactNameList *param_names,
    const EnactAst *body,
    const EnactEnv *env,
    const char *recursive_name)
{
    if (!recursive_name || recursive_name[0] == '\0') {
        return NULL;
    }

    return enact_function_new_with_recursive_name(param_names, body, env, recursive_name);
}

EnactFunction *enact_function_partial(
    const EnactFunction *function,
    const EnactValue *arguments,
    size_t argument_count)
{
    EnactEnv partial_env;
    EnactNameList *remaining_params;
    EnactFunction *partial;
    size_t arity = enact_function_arity(function);
    size_t index;

    if (!function || !arguments || argument_count == 0 || argument_count >= arity) {
        return NULL;
    }

    if (!enact_env_clone(&partial_env, &function->captured_env)) {
        return NULL;
    }

    if (function->recursive_name) {
        EnactValue self = enact_value_make_function((EnactFunction *)function);

        if (!enact_env_define(&partial_env, function->recursive_name, self)) {
            enact_env_free(&partial_env);
            return NULL;
        }
    }

    for (index = 0; index < argument_count; index += 1) {
        if (!enact_env_define(&partial_env, enact_name_list_get(function->param_names, index), arguments[index])) {
            enact_env_free(&partial_env);
            return NULL;
        }
    }

    remaining_params = enact_function_remaining_params(function, argument_count);
    if (!remaining_params) {
        enact_env_free(&partial_env);
        return NULL;
    }

    partial = enact_function_new(remaining_params, function->body, &partial_env);
    enact_name_list_free(remaining_params);
    enact_env_free(&partial_env);
    return partial;
}

int enact_function_define_capture(EnactFunction *function, const char *name, EnactValue value)
{
    if (!function || !name) {
        return 0;
    }

    return enact_env_define(&function->captured_env, name, value);
}

EnactFunction *enact_function_retain(EnactFunction *function)
{
    if (!function) {
        return NULL;
    }

    function->ref_count += 1;
    return function;
}

void enact_function_release(EnactFunction *function)
{
    if (!function) {
        return;
    }

    if (function->ref_count > 1) {
        function->ref_count -= 1;
        return;
    }

    enact_name_list_free(function->param_names);
    enact_ast_free(function->body);
    enact_env_free(&function->captured_env);
    free(function->recursive_name);
    free(function);
}

size_t enact_function_arity(const EnactFunction *function)
{
    return function ? enact_name_list_count(function->param_names) : 0;
}

const char *enact_function_param_name(const EnactFunction *function, size_t index)
{
    return function ? enact_name_list_get(function->param_names, index) : "";
}

const EnactAst *enact_function_body(const EnactFunction *function)
{
    return function ? function->body : NULL;
}

const EnactEnv *enact_function_env(const EnactFunction *function)
{
    return function ? &function->captured_env : NULL;
}

const char *enact_function_recursive_name(const EnactFunction *function)
{
    return function ? function->recursive_name : NULL;
}
