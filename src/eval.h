#ifndef ENACT_EVAL_H
#define ENACT_EVAL_H

#include "ast.h"
#include "diag.h"
#include "env.h"
#include "value.h"

int enact_eval_ast(const EnactAst *ast, EnactValue *value, EnactDiag *diag);
int enact_eval_ast_with_env(const EnactAst *ast, const EnactEnv *env, EnactValue *value, EnactDiag *diag);

#endif
