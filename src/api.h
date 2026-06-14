#ifndef ENACT_API_H
#define ENACT_API_H

#include <stdbool.h>
#include <stdio.h>

#include "diag.h"
#include "value.h"

typedef struct {
    bool ok;
    EnactValue value;
    EnactDiag error;
} EnactResult;

EnactResult enact_eval_text(const char *source);
int enact_dump_tokens_text(const char *source, FILE *out, EnactDiag *diag);
void enact_result_free(EnactResult *result);

#endif
