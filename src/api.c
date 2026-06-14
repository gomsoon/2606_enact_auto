#include <stddef.h>
#include <string.h>

#include "api.h"
#include "ast.h"
#include "diag.h"
#include "eval.h"
#include "parser_state.h"

typedef struct yy_buffer_state *YY_BUFFER_STATE;

extern YY_BUFFER_STATE yy_scan_string(const char *yy_str);
extern void yy_delete_buffer(YY_BUFFER_STATE buffer);
extern int yyparse(void);
extern int yylex_destroy(void);

static void enact_scanner_state_init(EnactScannerState *state)
{
    state->expect_operand = true;
    state->paren_balance = 0;
    state->offset = 0;
    state->token_offset = 0;
    state->last_token = 0;
    state->saw_dot = false;
}

static void enact_context_init(EnactParseContext *context, const char *source)
{
    context->root = NULL;
    context->source = source;
    context->source_len = strlen(source);
    enact_diag_reset(&context->diag);
}

static void enact_fill_parse_error(EnactParseContext *context, const EnactScannerState *state)
{
    if (context->diag.code != ENACT_OK) {
        return;
    }

    if (state->paren_balance != 0) {
        enact_diag_set(&context->diag, ENACT_ERR_PARSE_UNMATCHED_PAREN, (int)state->token_offset);
        return;
    }

    if (!state->saw_dot) {
        enact_diag_set(&context->diag, ENACT_ERR_PARSE_MISSING_DOT, (int)state->offset);
        return;
    }

    enact_diag_set(&context->diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, (int)state->token_offset);
}

EnactResult enact_eval_text(const char *source)
{
    EnactParseContext context;
    EnactScannerState state;
    EnactResult result;
    YY_BUFFER_STATE buffer;

    if (!source) {
        source = "";
    }

    enact_context_init(&context, source);
    enact_scanner_state_init(&state);

    enact_set_parse_context(&context);
    enact_set_scanner_state(&state);

    buffer = yy_scan_string(source);
    if (!buffer) {
        enact_diag_set(&context.diag, ENACT_ERR_OUT_OF_MEMORY, -1);
    } else {
        int parse_status = yyparse();
        yy_delete_buffer(buffer);
        yylex_destroy();

        if ((parse_status != 0 || context.root == NULL) && context.diag.code == ENACT_OK) {
            enact_fill_parse_error(&context, &state);
        }
    }

    enact_set_parse_context(NULL);
    enact_set_scanner_state(NULL);

    if (context.diag.code == ENACT_OK && context.root != NULL) {
        EnactDiag eval_diag;

        enact_diag_reset(&eval_diag);
        if (enact_eval_ast(context.root, &result.value, &eval_diag)) {
            result.ok = true;
            result.error.code = ENACT_OK;
            result.error.offset = -1;
            result.error.message = enact_error_message(ENACT_OK);
        } else {
            result.ok = false;
            result.error = eval_diag;
        }
    } else {
        result.ok = false;
        result.error = context.diag;
        result.value.kind = ENACT_VALUE_INT;
        result.value.as_int = 0;
    }

    enact_ast_free(context.root);
    return result;
}

void enact_result_free(EnactResult *result)
{
    (void)result;
}
