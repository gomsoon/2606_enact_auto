#include <stddef.h>
#include <stdlib.h>
#include <string.h>

#include "api.h"
#include "ast.h"
#include "builtin.h"
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

    if (!state->saw_dot && state->last_token == 0) {
        enact_diag_set(&context->diag, ENACT_ERR_PARSE_MISSING_DOT, (int)state->offset);
        return;
    }

    enact_diag_set(&context->diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, (int)state->token_offset);
}

static int enact_parse_text(const char *source, EnactAst **out, EnactDiag *diag)
{
    EnactParseContext context;
    EnactScannerState state;
    YY_BUFFER_STATE buffer;

    if (!out) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }

    *out = NULL;
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
        *out = context.root;
        return 1;
    }

    if (diag) {
        *diag = context.diag;
    }
    enact_ast_free(context.root);
    return 0;
}

static char *enact_copy_source_range(const char *source, size_t start, size_t end)
{
    char *copy;
    size_t length;

    if (!source || end < start) {
        return NULL;
    }

    length = end - start;
    copy = malloc(length + 1);
    if (!copy) {
        return NULL;
    }

    memcpy(copy, source + start, length);
    copy[length] = '\0';
    return copy;
}

static void enact_skip_script_trivia(const char *source, size_t length, size_t *offset)
{
    size_t index;

    if (!source || !offset) {
        return;
    }

    index = *offset;
    while (index < length) {
        char ch = source[index];

        if (ch == ' ' || ch == '\t' || ch == '\r' || ch == '\n') {
            index += 1;
            continue;
        }

        if (ch == '%') {
            index += 1;
            while (index < length && source[index] != '\n') {
                index += 1;
            }
            continue;
        }

        break;
    }

    *offset = index;
}

static int enact_next_script_chunk(
    const char *source,
    size_t length,
    size_t *offset,
    size_t *start,
    size_t *end)
{
    size_t index;
    int paren_depth = 0;
    int in_string = 0;
    int in_comment = 0;

    if (!source || !offset || !start || !end) {
        return 0;
    }

    enact_skip_script_trivia(source, length, offset);
    if (*offset >= length) {
        return 0;
    }

    *start = *offset;
    for (index = *offset; index < length; index += 1) {
        char ch = source[index];

        if (in_comment) {
            if (ch == '\n') {
                in_comment = 0;
            }
            continue;
        }

        if (in_string) {
            if (ch == '\\' && index + 1 < length) {
                index += 1;
                continue;
            }
            if (ch == '"') {
                in_string = 0;
            }
            continue;
        }

        if (ch == '%') {
            in_comment = 1;
            continue;
        }
        if (ch == '"') {
            in_string = 1;
            continue;
        }
        if (ch == '(') {
            paren_depth += 1;
            continue;
        }
        if (ch == ')') {
            paren_depth -= 1;
            continue;
        }
        if (ch == '.' && paren_depth == 0) {
            *end = index + 1;
            *offset = *end;
            return 1;
        }
    }

    *end = length;
    *offset = length;
    return 1;
}

static EnactResult enact_eval_parsed_ast(EnactAst *root, EnactEnv *env)
{
    EnactResult result;
    EnactDiag eval_diag;

    enact_diag_reset(&eval_diag);
    if (enact_eval_ast_with_env(root, env, &result.value, &eval_diag)) {
        result.ok = true;
        result.error.code = ENACT_OK;
        result.error.offset = -1;
        result.error.message = enact_error_message(ENACT_OK);
    } else {
        result.ok = false;
        result.error = eval_diag;
        result.value = enact_value_make_int(0);
    }

    return result;
}

EnactResult enact_eval_text(const char *source)
{
    EnactResult result;
    EnactDiag parse_diag;
    EnactAst *root = NULL;
    EnactEnv env;

    enact_diag_reset(&parse_diag);
    if (!enact_parse_text(source, &root, &parse_diag)) {
        result.ok = false;
        result.error = parse_diag;
        result.value = enact_value_make_int(0);
        return result;
    }

    enact_env_init(&env);
    if (!enact_install_builtins(&env)) {
        enact_ast_free(root);
        result.ok = false;
        enact_diag_reset(&result.error);
        enact_diag_set(&result.error, ENACT_ERR_OUT_OF_MEMORY, -1);
        result.value = enact_value_make_int(0);
        return result;
    }

    result = enact_eval_parsed_ast(root, &env);
    enact_env_free(&env);
    enact_ast_free(root);
    return result;
}

int enact_session_init(EnactSession *session)
{
    if (!session) {
        return 0;
    }

    session->initialized = false;
    enact_env_init(&session->env);
    if (!enact_install_builtins(&session->env)) {
        enact_env_free(&session->env);
        return 0;
    }

    session->initialized = true;
    return 1;
}

EnactResult enact_session_eval_text(EnactSession *session, const char *source)
{
    EnactResult result;
    EnactDiag parse_diag;
    EnactAst *root = NULL;

    if (!session || !session->initialized) {
        result.ok = false;
        enact_diag_reset(&result.error);
        enact_diag_set(&result.error, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        result.value = enact_value_make_int(0);
        return result;
    }

    enact_diag_reset(&parse_diag);
    if (!enact_parse_text(source, &root, &parse_diag)) {
        result.ok = false;
        result.error = parse_diag;
        result.value = enact_value_make_int(0);
        return result;
    }

    result = enact_eval_parsed_ast(root, &session->env);
    enact_ast_free(root);
    return result;
}

int enact_session_eval_script(
    EnactSession *session,
    const char *source,
    EnactScriptResultCallback callback,
    void *user_data,
    EnactDiag *diag)
{
    size_t offset = 0;
    size_t length;

    if (!session || !session->initialized) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }

    if (!source) {
        source = "";
    }

    length = strlen(source);
    while (offset < length) {
        size_t start = 0;
        size_t end = 0;
        char *chunk;
        EnactResult result;

        if (!enact_next_script_chunk(source, length, &offset, &start, &end)) {
            break;
        }

        chunk = enact_copy_source_range(source, start, end);
        if (!chunk) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }

        result = enact_session_eval_text(session, chunk);
        free(chunk);
        if (!result.ok) {
            if (diag) {
                *diag = result.error;
            }
            enact_result_free(&result);
            return 0;
        }

        if (callback && !callback(&result, user_data)) {
            enact_result_free(&result);
            enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
            return 0;
        }

        enact_result_free(&result);
    }

    return 1;
}

void enact_session_free(EnactSession *session)
{
    if (!session || !session->initialized) {
        return;
    }

    enact_env_free(&session->env);
    session->initialized = false;
}

void enact_result_free(EnactResult *result)
{
    if (!result || !result->ok) {
        return;
    }

    enact_value_free(&result->value);
    result->ok = false;
}
