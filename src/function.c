#include <stdlib.h>
#include <string.h>

#include "function.h"

struct EnactFunction {
    size_t ref_count;
    char *param_name;
    EnactAst *body;
    EnactEnv captured_env;
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

EnactFunction *enact_function_new(const char *param_name, const EnactAst *body, const EnactEnv *env)
{
    EnactFunction *function;

    if (!body || !env) {
        return NULL;
    }

    function = calloc(1, sizeof(*function));
    if (!function) {
        return NULL;
    }

    function->ref_count = 1;
    function->param_name = enact_function_copy_text(param_name);
    if (!function->param_name) {
        free(function);
        return NULL;
    }

    function->body = enact_ast_clone(body);
    if (!function->body) {
        free(function->param_name);
        free(function);
        return NULL;
    }

    if (!enact_env_clone(&function->captured_env, env)) {
        enact_ast_free(function->body);
        free(function->param_name);
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

    free(function->param_name);
    enact_ast_free(function->body);
    enact_env_free(&function->captured_env);
    free(function);
}

const char *enact_function_param_name(const EnactFunction *function)
{
    return function ? function->param_name : "";
}

const EnactAst *enact_function_body(const EnactFunction *function)
{
    return function ? function->body : NULL;
}

const EnactEnv *enact_function_env(const EnactFunction *function)
{
    return function ? &function->captured_env : NULL;
}
