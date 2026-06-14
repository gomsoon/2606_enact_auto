#ifndef ENACT_PARSER_STATE_H
#define ENACT_PARSER_STATE_H

#include <stdbool.h>
#include <stddef.h>

#include "ast.h"
#include "diag.h"

typedef struct {
    EnactAst *root;
    EnactDiag diag;
    const char *source;
    size_t source_len;
} EnactParseContext;

typedef struct {
    bool expect_operand;
    int paren_balance;
    size_t offset;
    size_t token_offset;
    int last_token;
    bool saw_dot;
} EnactScannerState;

EnactParseContext *enact_get_parse_context(void);
EnactScannerState *enact_get_scanner_state(void);
void enact_set_parse_context(EnactParseContext *context);
void enact_set_scanner_state(EnactScannerState *state);
void enact_parse_context_take_root(EnactAst *root);

#endif
