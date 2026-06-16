#ifndef ENACT_API_H
#define ENACT_API_H

#include <stdbool.h>
#include <stdio.h>

#include "diag.h"
#include "env.h"
#include "value.h"

typedef struct {
    bool ok;
    EnactValue value;
    EnactDiag error;
} EnactResult;

typedef struct {
    EnactEnv env;
    bool initialized;
} EnactSession;

typedef int (*EnactScriptResultCallback)(const EnactResult *result, void *user_data);

EnactResult enact_eval_text(const char *source);
int enact_session_init(EnactSession *session);
EnactResult enact_session_eval_text(EnactSession *session, const char *source);
int enact_session_eval_script(
    EnactSession *session,
    const char *source,
    EnactScriptResultCallback callback,
    void *user_data,
    EnactDiag *diag);
void enact_session_free(EnactSession *session);
int enact_dump_tokens_text(const char *source, FILE *out, EnactDiag *diag);
void enact_result_free(EnactResult *result);

#endif
