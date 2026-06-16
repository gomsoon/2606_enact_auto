#ifndef ENACT_BUILTIN_H
#define ENACT_BUILTIN_H

#include <stddef.h>

#include "diag.h"
#include "env.h"
#include "value.h"

typedef struct EnactBuiltin EnactBuiltin;
typedef struct EnactBuiltinPartial EnactBuiltinPartial;

const EnactBuiltin *enact_builtin_lookup(const char *name);
const char *enact_builtin_name(const EnactBuiltin *builtin);
size_t enact_builtin_arity(const EnactBuiltin *builtin);
EnactBuiltinPartial *enact_builtin_partial_new(
    const EnactBuiltin *builtin,
    const EnactValue *arguments,
    size_t argument_count);
EnactBuiltinPartial *enact_builtin_partial_extend(
    const EnactBuiltinPartial *partial,
    const EnactValue *arguments,
    size_t argument_count);
EnactBuiltinPartial *enact_builtin_partial_retain(EnactBuiltinPartial *partial);
void enact_builtin_partial_release(EnactBuiltinPartial *partial);
const EnactBuiltin *enact_builtin_partial_builtin(const EnactBuiltinPartial *partial);
size_t enact_builtin_partial_argument_count(const EnactBuiltinPartial *partial);
int enact_builtin_apply(
    const EnactBuiltin *builtin,
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag);
int enact_builtin_partial_apply(
    const EnactBuiltinPartial *partial,
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag);
int enact_install_builtins(EnactEnv *env);

#endif
