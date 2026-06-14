#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "api.h"
#include "ast.h"
#include "diag.h"
#include "eval.h"
#include "parser_state.h"

static int failures;

static void require_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        failures += 1;
    }
}

static void test_diag_helpers(void)
{
    EnactDiag diag;

    enact_diag_reset(NULL);
    enact_diag_reset(&diag);
    require_true(diag.code == ENACT_OK, "diag reset sets OK");
    require_true(strcmp(enact_error_code_name(ENACT_OK), "ENACT_OK") == 0, "error code ok");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_LEX_BAD_INTEGER), "ENACT_ERR_LEX_BAD_INTEGER") == 0, "error code bad integer");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_OUT_OF_MEMORY), "ENACT_ERR_OUT_OF_MEMORY") == 0, "error code oom");
    require_true(strcmp(enact_error_code_name((EnactErrorCode)999), "ENACT_ERR_UNKNOWN") == 0, "error code unknown");
    require_true(strcmp(enact_error_message(ENACT_OK), "ok") == 0, "error message ok");
    require_true(strcmp(enact_error_message(ENACT_ERR_LEX_BAD_INTEGER), "invalid integer literal") == 0, "error message bad integer");
    require_true(strcmp(enact_error_message(ENACT_ERR_OUT_OF_MEMORY), "out of memory") == 0, "error message oom");
    require_true(strcmp(enact_error_message((EnactErrorCode)999), "unknown error") == 0, "error message unknown");
    enact_diag_set(NULL, ENACT_ERR_INT_OVERFLOW, 1);
    enact_diag_set(&diag, ENACT_ERR_INT_OVERFLOW, 5);
    enact_diag_set(&diag, ENACT_ERR_DIVIDE_BY_ZERO, 6);
    require_true(diag.code == ENACT_ERR_INT_OVERFLOW, "diag set once");
    require_true(diag.offset == 5, "diag offset set");
}

static void test_parser_state_helpers(void)
{
    EnactParseContext context;
    EnactScannerState state;

    memset(&context, 0, sizeof(context));
    memset(&state, 0, sizeof(state));
    enact_set_parse_context(&context);
    enact_set_scanner_state(&state);
    require_true(enact_get_parse_context() == &context, "get parse context");
    require_true(enact_get_scanner_state() == &state, "get scanner state");
    enact_parse_context_take_root(NULL);
    enact_set_parse_context(NULL);
    enact_set_scanner_state(NULL);
    enact_parse_context_take_root(NULL);
    require_true(enact_get_parse_context() == NULL, "clear parse context");
    require_true(enact_get_scanner_state() == NULL, "clear scanner state");
}

static void test_eval_edge_cases(void)
{
    EnactDiag diag;
    EnactValue value;
    EnactAst bogus = {0};
    EnactAst int_node = {0};
    EnactAst unary_node = {0};

    enact_diag_reset(&diag);
    require_true(!enact_eval_ast(NULL, &value, &diag), "null ast fails");
    require_true(diag.code == ENACT_ERR_PARSE_UNEXPECTED_TOKEN, "null ast error code");

    enact_diag_reset(&diag);
    require_true(!enact_eval_ast(&bogus, NULL, &diag), "null value fails");
    require_true(diag.code == ENACT_ERR_PARSE_UNEXPECTED_TOKEN, "null value error code");

    bogus.kind = (EnactAstKind)99;
    enact_diag_reset(&diag);
    require_true(!enact_eval_ast(&bogus, &value, &diag), "bogus ast fails");
    require_true(diag.code == ENACT_ERR_PARSE_UNEXPECTED_TOKEN, "bogus ast error code");

    int_node.kind = AST_INT_LITERAL;
    int_node.as.int_magnitude = 2147483648ULL;
    enact_diag_reset(&diag);
    require_true(!enact_eval_ast(&int_node, &value, &diag), "literal overflow fails");
    require_true(diag.code == ENACT_ERR_INT_OVERFLOW, "literal overflow code");

    unary_node.kind = AST_UNARY_NEG;
    unary_node.as.unary.child = &int_node;
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(&unary_node, &value, &diag), "int32 min unary case succeeds");
    require_true(value.as_int == INT32_MIN, "int32 min value");
}

static void test_api_and_scan_helpers(void)
{
    EnactResult result;
    EnactDiag diag;
    FILE *tmp;
    char output[256];
    size_t nread;

    result = enact_eval_text(NULL);
    require_true(!result.ok, "null source parse fails");
    require_true(result.error.code == ENACT_ERR_PARSE_MISSING_DOT, "null source missing dot");
    enact_result_free(&result);

    result = enact_eval_text(")");
    require_true(!result.ok, "unexpected token parse fails");
    require_true(result.error.code == ENACT_ERR_PARSE_UNMATCHED_PAREN, "unexpected token code");
    enact_result_free(&result);

    tmp = tmpfile();
    require_true(tmp != NULL, "tmpfile created");
    if (!tmp) {
        return;
    }

    enact_diag_reset(&diag);
    require_true(enact_dump_tokens_text(NULL, tmp, &diag) == 0, "token dump null source");
    rewind(tmp);
    memset(output, 0, sizeof(output));
    nread = fread(output, 1, sizeof(output) - 1, tmp);
    output[nread] = '\0';
    require_true(strcmp(output, "TOK_EOF\n") == 0, "token dump null source stdout");

    freopen(NULL, "w+", tmp);
    enact_diag_reset(&diag);
    require_true(enact_dump_tokens_text("a", tmp, &diag) != 0, "token dump invalid char fails");
    require_true(diag.code == ENACT_ERR_LEX_INVALID_CHAR, "token dump invalid char code");

    freopen(NULL, "w+", tmp);
    require_true(enact_dump_tokens_text("% comment\n1.", tmp, NULL) == 0, "token dump null diag succeeds");
    rewind(tmp);
    memset(output, 0, sizeof(output));
    nread = fread(output, 1, sizeof(output) - 1, tmp);
    output[nread] = '\0';
    require_true(strcmp(output, "TOK_INT_LITERAL TOK_DOT TOK_EOF\n") == 0, "token dump null diag stdout");
    fclose(tmp);
}

int main(void)
{
    test_diag_helpers();
    test_parser_state_helpers();
    test_eval_edge_cases();
    test_api_and_scan_helpers();

    if (failures != 0) {
        return 1;
    }

    puts("unit tests passed");
    return 0;
}
