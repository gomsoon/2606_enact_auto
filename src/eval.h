#ifndef ENACT_EVAL_H
#define ENACT_EVAL_H

#include "ast.h"
#include "diag.h"
#include "value.h"

int enact_eval_ast(const EnactAst *ast, EnactValue *value, EnactDiag *diag);

#endif
