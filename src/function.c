#include <stdlib.h>

#include "function.h"

struct EnactFunction {
    size_t ref_count;
    EnactNameList *param_names;
    EnactAst *body;
    EnactEnv captured_env;
};

EnactFunction *enact_function_new(const EnactNameList *param_names, const EnactAst *body, const EnactEnv *env)
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

    return function;
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
