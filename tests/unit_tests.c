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
    require_true(strcmp(enact_error_code_name(ENACT_ERR_LEX_BARE_EQUALS), "ENACT_ERR_LEX_BARE_EQUALS") == 0, "error code bare equals");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_TYPE_EXPECTED_BOOL), "ENACT_ERR_TYPE_EXPECTED_BOOL") == 0, "error code expected bool");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_TYPE_EXPECTED_INT), "ENACT_ERR_TYPE_EXPECTED_INT") == 0, "error code expected int");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_TYPE_EQUALITY_MISMATCH), "ENACT_ERR_TYPE_EQUALITY_MISMATCH") == 0, "error code equality mismatch");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_OUT_OF_MEMORY), "ENACT_ERR_OUT_OF_MEMORY") == 0, "error code oom");
    require_true(strcmp(enact_error_code_name((EnactErrorCode)999), "ENACT_ERR_UNKNOWN") == 0, "error code unknown");
    require_true(strcmp(enact_error_message(ENACT_OK), "ok") == 0, "error message ok");
    require_true(strcmp(enact_error_message(ENACT_ERR_LEX_BAD_INTEGER), "invalid integer literal") == 0, "error message bad integer");
    require_true(strcmp(enact_error_message(ENACT_ERR_LEX_BARE_EQUALS), "bare '=' is not supported; use '=='") == 0, "error message bare equals");
    require_true(strcmp(enact_error_message(ENACT_ERR_TYPE_EXPECTED_BOOL), "boolean value required") == 0, "error message expected bool");
    require_true(strcmp(enact_error_message(ENACT_ERR_TYPE_EXPECTED_INT), "integer value required") == 0, "error message expected int");
    require_true(strcmp(enact_error_message(ENACT_ERR_TYPE_EQUALITY_MISMATCH), "cannot compare values of different kinds") == 0, "error message equality mismatch");
    require_true(strcmp(enact_error_message(ENACT_ERR_OUT_OF_MEMORY), "out of memory") == 0, "error message oom");
    require_true(strcmp(enact_error_message((EnactErrorCode)999), "unknown error") == 0, "error message unknown");
    enact_diag_set(NULL, ENACT_ERR_INT_OVERFLOW, 1);
    enact_diag_set(&diag, ENACT_ERR_INT_OVERFLOW, 5);
    enact_diag_set(&diag, ENACT_ERR_DIVIDE_BY_ZERO, 6);
    require_true(diag.code == ENACT_ERR_INT_OVERFLOW, "diag set once");
    require_true(diag.offset == 5, "diag offset set");
}

static void test_value_helpers(void)
{
    EnactValue int_value = enact_value_make_int(-12);
    EnactValue bool_value = enact_value_make_bool(true);

    require_true(int_value.kind == ENACT_VALUE_INT, "int value kind");
    require_true(int_value.as.as_int == -12, "int value payload");
    require_true(bool_value.kind == ENACT_VALUE_BOOL, "bool value kind");
    require_true(bool_value.as.as_bool, "bool value payload");
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
    EnactAst int_one = {0};
    EnactAst int_zero = {0};
    EnactAst int_seven = {0};
    EnactAst bool_true = {0};
    EnactAst bool_false = {0};
    EnactAst eq_node = {0};
    EnactAst neq_node = {0};
    EnactAst lt_node = {0};
    EnactAst add_node = {0};
    EnactAst div_node = {0};
    EnactAst and_node = {0};
    EnactAst or_node = {0};
    EnactAst not_node = {0};
    EnactAst conditional_node = {0};

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
    require_true(value.kind == ENACT_VALUE_INT, "int32 min kind");
    require_true(value.as.as_int == INT32_MIN, "int32 min value");

    int_one.kind = AST_INT_LITERAL;
    int_one.as.int_magnitude = 1;
    int_zero.kind = AST_INT_LITERAL;
    int_zero.as.int_magnitude = 0;
    int_seven.kind = AST_INT_LITERAL;
    int_seven.as.int_magnitude = 7;
    bool_true.kind = AST_BOOL_LITERAL;
    bool_true.as.bool_value = 1;
    bool_false.kind = AST_BOOL_LITERAL;
    bool_false.as.bool_value = 0;

    eq_node.kind = AST_EQ;
    eq_node.as.binary.left = &bool_true;
    eq_node.as.binary.right = &int_one;
    enact_diag_reset(&diag);
    require_true(!enact_eval_ast(&eq_node, &value, &diag), "equality mismatch fails");
    require_true(diag.code == ENACT_ERR_TYPE_EQUALITY_MISMATCH, "equality mismatch code");

    neq_node.kind = AST_NEQ;
    neq_node.as.binary.left = &bool_true;
    neq_node.as.binary.right = &bool_false;
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(&neq_node, &value, &diag), "bool inequality succeeds");
    require_true(value.kind == ENACT_VALUE_BOOL, "bool inequality kind");
    require_true(value.as.as_bool, "bool inequality value");

    lt_node.kind = AST_LT;
    lt_node.as.binary.left = &int_zero;
    lt_node.as.binary.right = &int_one;
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(&lt_node, &value, &diag), "integer less-than succeeds");
    require_true(value.kind == ENACT_VALUE_BOOL, "integer less-than kind");
    require_true(value.as.as_bool, "integer less-than value");

    lt_node.as.binary.left = &bool_false;
    lt_node.as.binary.right = &bool_true;
    enact_diag_reset(&diag);
    require_true(!enact_eval_ast(&lt_node, &value, &diag), "bool ordering fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_INT, "bool ordering code");

    not_node.kind = AST_NOT;
    not_node.as.unary.child = &int_one;
    enact_diag_reset(&diag);
    require_true(!enact_eval_ast(&not_node, &value, &diag), "not int fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_BOOL, "not int code");

    add_node.kind = AST_ADD;
    add_node.as.binary.left = &bool_true;
    add_node.as.binary.right = &int_one;
    enact_diag_reset(&diag);
    require_true(!enact_eval_ast(&add_node, &value, &diag), "bool arithmetic fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_INT, "bool arithmetic code");

    div_node.kind = AST_DIV;
    div_node.as.binary.left = &int_one;
    div_node.as.binary.right = &int_zero;

    and_node.kind = AST_AND;
    and_node.as.binary.left = &bool_false;
    and_node.as.binary.right = &div_node;
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(&and_node, &value, &diag), "and short-circuits false");
    require_true(value.kind == ENACT_VALUE_BOOL, "and short-circuit kind");
    require_true(!value.as.as_bool, "and short-circuit value");

    or_node.kind = AST_OR;
    or_node.as.binary.left = &bool_true;
    or_node.as.binary.right = &div_node;
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(&or_node, &value, &diag), "or short-circuits true");
    require_true(value.kind == ENACT_VALUE_BOOL, "or short-circuit kind");
    require_true(value.as.as_bool, "or short-circuit value");

    conditional_node.kind = AST_IF_ELSE;
    conditional_node.as.conditional.condition = &bool_true;
    conditional_node.as.conditional.if_true = &int_seven;
    conditional_node.as.conditional.if_false = &div_node;
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(&conditional_node, &value, &diag), "conditional skips false branch");
    require_true(value.kind == ENACT_VALUE_INT, "conditional selected kind");
    require_true(value.as.as_int == 7, "conditional selected value");
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
    test_value_helpers();
    test_parser_state_helpers();
    test_eval_edge_cases();
    test_api_and_scan_helpers();

    if (failures != 0) {
        return 1;
    }

    puts("unit tests passed");
    return 0;
}
