#ifndef ENACT_FUNCTION_H
#define ENACT_FUNCTION_H

#include "ast.h"
#include "env.h"

typedef struct EnactFunction EnactFunction;

EnactFunction *enact_function_new(const char *param_name, const EnactAst *body, const EnactEnv *env);
EnactFunction *enact_function_retain(EnactFunction *function);
void enact_function_release(EnactFunction *function);
const char *enact_function_param_name(const EnactFunction *function);
const EnactAst *enact_function_body(const EnactFunction *function);
const EnactEnv *enact_function_env(const EnactFunction *function);

#endif
