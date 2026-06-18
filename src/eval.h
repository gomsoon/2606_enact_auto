#ifndef ENACT_EVAL_H
#define ENACT_EVAL_H

#include <stddef.h>

#include "ast.h"
#include "diag.h"
#include "env.h"
#include "value.h"

int enact_eval_ast(const EnactAst *ast, EnactValue *value, EnactDiag *diag);
int enact_eval_ast_with_env(const EnactAst *ast, EnactEnv *env, EnactValue *value, EnactDiag *diag);
int enact_eval_apply_callable(
    const EnactValue *callee,
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag);
int enact_eval_apply_callable_in_env(
    const EnactValue *callee,
    EnactEnv *env,
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag);

#endif
