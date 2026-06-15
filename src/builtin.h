#ifndef ENACT_BUILTIN_H
#define ENACT_BUILTIN_H

#include <stddef.h>

#include "diag.h"
#include "env.h"
#include "value.h"

typedef struct EnactBuiltin EnactBuiltin;

const EnactBuiltin *enact_builtin_lookup(const char *name);
const char *enact_builtin_name(const EnactBuiltin *builtin);
size_t enact_builtin_arity(const EnactBuiltin *builtin);
int enact_builtin_apply(
    const EnactBuiltin *builtin,
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag);
int enact_install_builtins(EnactEnv *env);

#endif
