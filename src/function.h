#ifndef ENACT_FUNCTION_H
#define ENACT_FUNCTION_H

#include "ast.h"
#include "env.h"

typedef struct EnactFunction EnactFunction;

EnactFunction *enact_function_new(const EnactNameList *param_names, const EnactAst *body, const EnactEnv *env);
EnactFunction *enact_function_new_recursive(
    const EnactNameList *param_names,
    const EnactAst *body,
    const EnactEnv *env,
    const char *recursive_name);
EnactFunction *enact_function_partial(
    const EnactFunction *function,
    const EnactValue *arguments,
    size_t argument_count);
EnactFunction *enact_function_retain(EnactFunction *function);
void enact_function_release(EnactFunction *function);
size_t enact_function_arity(const EnactFunction *function);
const char *enact_function_param_name(const EnactFunction *function, size_t index);
const EnactAst *enact_function_body(const EnactFunction *function);
const EnactEnv *enact_function_env(const EnactFunction *function);
const char *enact_function_recursive_name(const EnactFunction *function);

#endif
