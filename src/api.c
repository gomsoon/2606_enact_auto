#include <stddef.h>
#include <stdio.h>
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

static int enact_is_script_space(char ch)
{
    return ch == ' ' || ch == '\t' || ch == '\r' || ch == '\n';
}

static int enact_is_identifier_char(char ch)
{
    return (ch >= 'A' && ch <= 'Z') ||
        (ch >= 'a' && ch <= 'z') ||
        (ch >= '0' && ch <= '9') ||
        ch == '_';
}

static int enact_is_identifier_start(char ch)
{
    return (ch >= 'A' && ch <= 'Z') ||
        (ch >= 'a' && ch <= 'z') ||
        ch == '_';
}

static int enact_dot_starts_attribute_access(const char *source, size_t length, size_t index)
{
    char previous;

    if (!source || index == 0 || index + 1 >= length) {
        return 0;
    }

    previous = source[index - 1];
    return enact_is_identifier_start(source[index + 1]) &&
        (enact_is_identifier_char(previous) || previous == ')');
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

        if (enact_is_script_space(ch)) {
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

static int enact_skip_required_command_trivia(const char *source, size_t length, size_t *offset)
{
    size_t before;

    if (!source || !offset) {
        return 0;
    }

    before = *offset;
    enact_skip_script_trivia(source, length, offset);
    return *offset > before;
}

static int enact_next_script_chunk(
    const char *source,
    size_t length,
    size_t *offset,
    size_t *start,
    size_t *end,
    int *needs_dot)
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
    if (needs_dot) {
        *needs_dot = 0;
    }
    for (index = *offset; index < length; index += 1) {
        char ch = source[index];

        if (in_comment) {
            if (ch == '\n') {
                in_comment = 0;
                if (paren_depth == 0) {
                    *end = index + 1;
                    *offset = *end;
                    if (needs_dot) {
                        *needs_dot = 1;
                    }
                    return 1;
                }
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
        if (ch == '\n' && paren_depth == 0) {
            *end = index + 1;
            *offset = *end;
            if (needs_dot) {
                *needs_dot = 1;
            }
            return 1;
        }
        if (ch == '.' && paren_depth == 0 && !enact_dot_starts_attribute_access(source, length, index)) {
            *end = index + 1;
            *offset = *end;
            return 1;
        }
    }

    *end = length;
    *offset = length;
    return 1;
}

static char *enact_read_file_text(const char *path, EnactDiag *diag)
{
    FILE *stream;
    size_t capacity = 1024;
    size_t length = 0;
    char *buffer;

    if (!path) {
        enact_diag_set(diag, ENACT_ERR_LOAD_FILE, -1);
        return NULL;
    }

    stream = fopen(path, "rb");
    if (!stream) {
        enact_diag_set(diag, ENACT_ERR_LOAD_FILE, -1);
        return NULL;
    }

    buffer = malloc(capacity);
    if (!buffer) {
        fclose(stream);
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return NULL;
    }

    for (;;) {
        size_t remaining = capacity - length;
        size_t read_count;

        if (remaining < 512) {
            char *grown;

            capacity *= 2;
            grown = realloc(buffer, capacity);
            if (!grown) {
                free(buffer);
                fclose(stream);
                enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
                return NULL;
            }
            buffer = grown;
            remaining = capacity - length;
        }

        read_count = fread(buffer + length, 1, remaining - 1, stream);
        length += read_count;
        if (ferror(stream)) {
            free(buffer);
            fclose(stream);
            enact_diag_set(diag, ENACT_ERR_LOAD_FILE, -1);
            return NULL;
        }
        if (feof(stream)) {
            break;
        }
    }

    fclose(stream);
    buffer[length] = '\0';
    return buffer;
}

static char *enact_copy_script_chunk(
    const char *source,
    size_t start,
    size_t end,
    int append_dot)
{
    char *copy;
    size_t length;

    if (!source || end < start) {
        return NULL;
    }

    length = end - start;
    copy = malloc(length + (append_dot ? 2 : 1));
    if (!copy) {
        return NULL;
    }

    memcpy(copy, source + start, length);
    if (append_dot) {
        copy[length] = '.';
        length += 1;
    }
    copy[length] = '\0';
    return copy;
}

static int enact_source_range_is_dot_only(const char *source, size_t start, size_t end)
{
    const char *chunk;
    size_t length;
    size_t offset = 0;

    if (!source || end < start) {
        return 0;
    }

    chunk = source + start;
    length = end - start;
    enact_skip_script_trivia(chunk, length, &offset);
    if (offset >= length || chunk[offset] != '.') {
        return 0;
    }

    offset += 1;
    enact_skip_script_trivia(chunk, length, &offset);
    return offset == length;
}

static char *enact_parse_load_string_literal(
    const char *source,
    size_t length,
    size_t *offset,
    EnactDiag *diag)
{
    size_t read_index;
    size_t write_index = 0;
    char *copy;

    if (!source || !offset || *offset >= length || source[*offset] != '"') {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, offset ? (int)*offset : -1);
        return NULL;
    }

    copy = malloc(length - *offset);
    if (!copy) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return NULL;
    }

    for (read_index = *offset + 1; read_index < length; read_index += 1) {
        char ch = source[read_index];

        if (ch == '"') {
            copy[write_index] = '\0';
            *offset = read_index + 1;
            return copy;
        }
        if (ch == '\r' || ch == '\n') {
            free(copy);
            enact_diag_set(diag, ENACT_ERR_LEX_BAD_STRING, (int)read_index);
            return NULL;
        }
        if (ch != '\\') {
            copy[write_index++] = ch;
            continue;
        }

        read_index += 1;
        if (read_index >= length) {
            free(copy);
            enact_diag_set(diag, ENACT_ERR_LEX_BAD_STRING, (int)(read_index - 1));
            return NULL;
        }

        switch (source[read_index]) {
        case '\\':
            copy[write_index++] = '\\';
            break;
        case '"':
            copy[write_index++] = '"';
            break;
        case 'n':
            copy[write_index++] = '\n';
            break;
        case 'r':
            copy[write_index++] = '\r';
            break;
        case 't':
            copy[write_index++] = '\t';
            break;
        default:
            free(copy);
            enact_diag_set(diag, ENACT_ERR_LEX_BAD_STRING, (int)(read_index - 1));
            return NULL;
        }
    }

    free(copy);
    enact_diag_set(diag, ENACT_ERR_LEX_BAD_STRING, (int)*offset);
    return NULL;
}

static int enact_script_chunk_is_load_command(const char *chunk, size_t length)
{
    size_t offset = 0;

    enact_skip_script_trivia(chunk, length, &offset);
    return offset + 4 <= length &&
        memcmp(chunk + offset, "load", 4) == 0 &&
        (offset + 4 == length || !enact_is_identifier_char(chunk[offset + 4]));
}

static int enact_session_eval_load_command(
    EnactSession *session,
    const char *chunk,
    EnactScriptResultCallback callback,
    void *user_data,
    EnactDiag *diag)
{
    size_t length;
    size_t offset = 0;
    char *path;
    char *loaded_source;
    int status;

    if (!chunk) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }

    length = strlen(chunk);
    enact_skip_script_trivia(chunk, length, &offset);
    offset += 4;

    if (!enact_skip_required_command_trivia(chunk, length, &offset)) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, (int)offset);
        return 0;
    }

    path = enact_parse_load_string_literal(chunk, length, &offset, diag);
    if (!path) {
        return 0;
    }

    enact_skip_script_trivia(chunk, length, &offset);
    if (offset >= length) {
        free(path);
        enact_diag_set(diag, ENACT_ERR_PARSE_MISSING_DOT, (int)offset);
        return 0;
    }
    if (chunk[offset] != '.') {
        free(path);
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, (int)offset);
        return 0;
    }

    offset += 1;
    enact_skip_script_trivia(chunk, length, &offset);
    if (offset != length) {
        free(path);
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, (int)offset);
        return 0;
    }

    loaded_source = enact_read_file_text(path, diag);
    free(path);
    if (!loaded_source) {
        return 0;
    }

    status = enact_session_eval_script(session, loaded_source, callback, user_data, diag);
    free(loaded_source);
    return status;
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
    int allow_redundant_dot = 0;

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
        int needs_dot = 0;
        char *chunk;
        EnactResult result;

        if (!enact_next_script_chunk(source, length, &offset, &start, &end, &needs_dot)) {
            break;
        }

        if (!needs_dot && allow_redundant_dot && enact_source_range_is_dot_only(source, start, end)) {
            allow_redundant_dot = 0;
            continue;
        }

        chunk = enact_copy_script_chunk(source, start, end, needs_dot);
        if (!chunk) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }

        if (enact_script_chunk_is_load_command(chunk, strlen(chunk))) {
            int status = enact_session_eval_load_command(session, chunk, callback, user_data, diag);

            free(chunk);
            if (!status) {
                return 0;
            }
            allow_redundant_dot = needs_dot;
            continue;
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
        allow_redundant_dot = needs_dot;
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
