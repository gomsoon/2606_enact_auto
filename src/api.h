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
    bool exit_requested;
} EnactSession;

typedef int (*EnactScriptResultCallback)(const EnactResult *result, void *user_data);

EnactResult enact_eval_text(const char *source);
int enact_session_init(EnactSession *session);
void enact_session_set_input_provider(
    EnactSession *session,
    EnactInputProvider provider,
    void *user_data);
EnactResult enact_session_eval_text(EnactSession *session, const char *source);
int enact_session_eval_script(
    EnactSession *session,
    const char *source,
    EnactScriptResultCallback callback,
    void *user_data,
    EnactDiag *diag);
int enact_session_exit_requested(const EnactSession *session);
void enact_session_free(EnactSession *session);
int enact_dump_tokens_text(const char *source, FILE *out, EnactDiag *diag);
void enact_result_free(EnactResult *result);

#endif
