#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "api.h"
#include "ast.h"
#include "diag.h"
#include "env.h"
#include "eval.h"
#include "function.h"
#include "parser_state.h"

static int failures;

static void require_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        failures += 1;
    }
}

static char *copy_test_name(const char *name)
{
    size_t length = strlen(name);
    char *copy = malloc(length + 1);

    if (!copy) {
        return NULL;
    }

    memcpy(copy, name, length + 1);
    return copy;
}

static EnactNameList *make_test_name_list(const char **names, size_t count)
{
    EnactNameList *list = enact_name_list_new();
    size_t index;

    if (!list) {
        return NULL;
    }

    for (index = 0; index < count; index += 1) {
        char *copy = copy_test_name(names[index]);

        if (!copy || !enact_name_list_append(list, copy)) {
            free(copy);
            enact_name_list_free(list);
            return NULL;
        }
    }

    return list;
}

static EnactAstList *make_test_ast_list1(EnactAst *first)
{
    EnactAstList *list = enact_ast_list_new();

    if (!list || !enact_ast_list_append(list, first)) {
        enact_ast_list_free(list);
        enact_ast_free(first);
        return NULL;
    }

    return list;
}

static EnactAstList *make_test_ast_list2(EnactAst *first, EnactAst *second)
{
    EnactAstList *list = make_test_ast_list1(first);

    if (!list || !enact_ast_list_append(list, second)) {
        enact_ast_list_free(list);
        enact_ast_free(second);
        return NULL;
    }

    return list;
}

static void test_diag_helpers(void)
{
    EnactDiag diag;

    enact_diag_reset(NULL);
    enact_diag_reset(&diag);
    require_true(diag.code == ENACT_OK, "diag reset sets OK");
    require_true(strcmp(enact_error_code_name(ENACT_OK), "ENACT_OK") == 0, "error code ok");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_LEX_BAD_INTEGER), "ENACT_ERR_LEX_BAD_INTEGER") == 0, "error code bad integer");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_LEX_BAD_STRING), "ENACT_ERR_LEX_BAD_STRING") == 0, "error code bad string");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_LEX_BARE_EQUALS), "ENACT_ERR_LEX_BARE_EQUALS") == 0, "error code bare equals");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_TYPE_EXPECTED_BOOL), "ENACT_ERR_TYPE_EXPECTED_BOOL") == 0, "error code expected bool");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_TYPE_EXPECTED_INT), "ENACT_ERR_TYPE_EXPECTED_INT") == 0, "error code expected int");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_TYPE_EXPECTED_FUNCTION), "ENACT_ERR_TYPE_EXPECTED_FUNCTION") == 0, "error code expected function");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_TYPE_EQUALITY_MISMATCH), "ENACT_ERR_TYPE_EQUALITY_MISMATCH") == 0, "error code equality mismatch");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_ARITY_MISMATCH), "ENACT_ERR_ARITY_MISMATCH") == 0, "error code arity mismatch");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_NAME_UNBOUND), "ENACT_ERR_NAME_UNBOUND") == 0, "error code unbound name");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_OUT_OF_MEMORY), "ENACT_ERR_OUT_OF_MEMORY") == 0, "error code oom");
    require_true(strcmp(enact_error_code_name((EnactErrorCode)999), "ENACT_ERR_UNKNOWN") == 0, "error code unknown");
    require_true(strcmp(enact_error_message(ENACT_OK), "ok") == 0, "error message ok");
    require_true(strcmp(enact_error_message(ENACT_ERR_LEX_BAD_INTEGER), "invalid integer literal") == 0, "error message bad integer");
    require_true(strcmp(enact_error_message(ENACT_ERR_LEX_BAD_STRING), "invalid string literal") == 0, "error message bad string");
    require_true(strcmp(enact_error_message(ENACT_ERR_LEX_BARE_EQUALS), "bare '=' is not supported; use '=='") == 0, "error message bare equals");
    require_true(strcmp(enact_error_message(ENACT_ERR_TYPE_EXPECTED_BOOL), "boolean value required") == 0, "error message expected bool");
    require_true(strcmp(enact_error_message(ENACT_ERR_TYPE_EXPECTED_INT), "integer value required") == 0, "error message expected int");
    require_true(strcmp(enact_error_message(ENACT_ERR_TYPE_EXPECTED_FUNCTION), "function value required") == 0, "error message expected function");
    require_true(strcmp(enact_error_message(ENACT_ERR_TYPE_EQUALITY_MISMATCH), "cannot compare values of different kinds") == 0, "error message equality mismatch");
    require_true(strcmp(enact_error_message(ENACT_ERR_ARITY_MISMATCH), "function arity mismatch") == 0, "error message arity mismatch");
    require_true(strcmp(enact_error_message(ENACT_ERR_NAME_UNBOUND), "unbound identifier") == 0, "error message unbound name");
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
    EnactValue string_value = enact_value_make_string(copy_test_name("hello"));
    EnactValue string_copy;
    EnactEnv empty_env;
    EnactAst *function_body;
    EnactFunction *function;
    EnactFunction *partial_function;
    EnactValue function_value;
    EnactValue function_copy;
    EnactValue partial_args[2];
    EnactValue partial_lookup;
    EnactNameList *params;
    EnactNameList *two_params;
    EnactNameList *empty_params;
    EnactNameList *params_clone;
    char *bad_append_name;
    const char *one_param[] = {"x"};
    const char *two_param_names[] = {"x", "y"};

    require_true(int_value.kind == ENACT_VALUE_INT, "int value kind");
    require_true(int_value.as.as_int == -12, "int value payload");
    require_true(bool_value.kind == ENACT_VALUE_BOOL, "bool value kind");
    require_true(bool_value.as.as_bool, "bool value payload");
    require_true(string_value.kind == ENACT_VALUE_STRING, "string value kind");
    require_true(string_value.as.as_string != NULL, "string value payload allocated");
    require_true(strcmp(string_value.as.as_string, "hello") == 0, "string value payload");
    require_true(enact_value_copy(&string_copy, &string_value), "string value copy succeeds");
    require_true(string_copy.kind == ENACT_VALUE_STRING, "string copy kind");
    require_true(strcmp(string_copy.as.as_string, "hello") == 0, "string copy payload");
    require_true(string_copy.as.as_string != string_value.as.as_string, "string copy is deep");
    enact_value_free(&string_copy);
    enact_value_free(&string_value);

    enact_env_init(&empty_env);
    function_body = enact_ast_new_int(1);
    require_true(function_body != NULL, "function body ast created");
    params = make_test_name_list(one_param, 1);
    require_true(params != NULL, "function params created");
    empty_params = enact_name_list_new();
    require_true(empty_params != NULL, "empty params created");
    require_true(enact_function_new(NULL, function_body, &empty_env) == NULL, "function new null params fails");
    require_true(enact_function_new(empty_params, function_body, &empty_env) == NULL, "function new empty params fails");
    require_true(enact_function_new(params, NULL, &empty_env) == NULL, "function new null body fails");
    require_true(enact_function_new(params, function_body, NULL) == NULL, "function new null env fails");
    require_true(enact_function_partial(NULL, partial_args, 1) == NULL, "function partial null function fails");
    params_clone = enact_name_list_clone(params);
    require_true(params_clone != NULL, "name list clone succeeds");
    require_true(enact_name_list_count(params_clone) == 1, "name list clone count");
    require_true(strcmp(enact_name_list_get(params_clone, 0), "x") == 0, "name list clone value");
    require_true(strcmp(enact_name_list_get(params_clone, 99), "") == 0, "name list out of range");
    require_true(enact_name_list_contains(params_clone, "x"), "name list contains x");
    require_true(!enact_name_list_contains(params_clone, "missing"), "name list missing value");
    bad_append_name = copy_test_name("bad");
    require_true(!enact_name_list_append(NULL, bad_append_name), "name list append null list fails");
    free(bad_append_name);
    require_true(!enact_name_list_append(params_clone, NULL), "name list append null name fails");
    enact_name_list_free(params_clone);
    function = enact_function_new(params, function_body, &empty_env);
    require_true(function != NULL, "function value payload created");
    if (function) {
        require_true(enact_function_arity(function) == 1, "function arity");
        require_true(strcmp(enact_function_param_name(function, 0), "x") == 0, "function first param");
        require_true(strcmp(enact_function_param_name(function, 99), "") == 0, "function param out of range");
        partial_args[0] = enact_value_make_int(1);
        require_true(enact_function_partial(function, NULL, 1) == NULL, "function partial null arguments fails");
        require_true(enact_function_partial(function, partial_args, 0) == NULL, "function partial zero arguments fails");
        require_true(enact_function_partial(function, partial_args, 1) == NULL, "function partial exact arity fails");
        function_value = enact_value_make_function(function);
        require_true(function_value.kind == ENACT_VALUE_FUNCTION, "function value kind");
        require_true(enact_value_copy(&function_copy, &function_value), "function value copy succeeds");
        require_true(function_copy.kind == ENACT_VALUE_FUNCTION, "function copy kind");
        require_true(function_copy.as.as_function == function_value.as.as_function, "function copy retains same object");
        enact_value_free(&function_copy);
        enact_value_free(&function_value);
    }
    two_params = make_test_name_list(two_param_names, 2);
    require_true(two_params != NULL, "two-parameter list created");
    function = enact_function_new(two_params, function_body, &empty_env);
    require_true(function != NULL, "two-parameter function created");
    if (function) {
        partial_args[0] = enact_value_make_int(7);
        partial_args[1] = enact_value_make_int(8);
        partial_function = enact_function_partial(function, partial_args, 1);
        require_true(partial_function != NULL, "function partial one argument succeeds");
        if (partial_function) {
            require_true(enact_function_arity(partial_function) == 1, "partial function arity");
            require_true(strcmp(enact_function_param_name(partial_function, 0), "y") == 0, "partial function remaining param");
            require_true(
                enact_env_lookup(enact_function_env(partial_function), "x", &partial_lookup),
                "partial function captures bound argument");
            require_true(partial_lookup.kind == ENACT_VALUE_INT, "partial captured argument kind");
            require_true(partial_lookup.as.as_int == 7, "partial captured argument value");
            enact_value_free(&partial_lookup);
            enact_function_release(partial_function);
        }
        require_true(
            enact_function_partial(function, partial_args, 2) == NULL,
            "function partial all arguments fails");
        enact_function_release(function);
    }
    require_true(enact_function_retain(NULL) == NULL, "function retain null fails");
    enact_function_release(NULL);
    require_true(enact_function_arity(NULL) == 0, "function null arity");
    require_true(strcmp(enact_function_param_name(NULL, 0), "") == 0, "function null param accessor");
    require_true(enact_function_body(NULL) == NULL, "function null body accessor");
    require_true(enact_function_env(NULL) == NULL, "function null env accessor");
    function_value = enact_value_make_function(NULL);
    require_true(!enact_value_copy(&function_copy, &function_value), "function value copy null payload fails");
    enact_value_free(&function_value);
    enact_name_list_free(empty_params);
    enact_name_list_free(params);
    enact_name_list_free(two_params);
    enact_ast_free(function_body);
    enact_env_free(&empty_env);

    require_true(!enact_value_copy(NULL, &int_value), "value copy null out fails");
    require_true(!enact_value_copy(&string_copy, NULL), "value copy null in fails");
    enact_value_free(NULL);
}

static void test_env_helpers(void)
{
    EnactEnv env;
    EnactEnv clone;
    EnactValue value;
    EnactValue result;
    EnactDiag diag;
    EnactAst *identifier;
    EnactAst *left;
    EnactAst *right;
    EnactAst *sum;
    EnactAst *assignment;
    EnactAst *sequence;
    EnactAst *where_ast;
    EnactAst *function_body;
    EnactAst *function_literal;
    EnactAst *function_call;
    EnactNameList *params;
    EnactAstList *arguments;
    EnactValue string_binding;

    enact_env_init(NULL);
    enact_env_free(NULL);
    require_true(!enact_env_clone(NULL, &env), "clone null out fails");
    require_true(!enact_env_clone(&clone, NULL), "clone null in fails");
    require_true(!enact_env_define(NULL, "x", enact_value_make_int(1)), "define null env fails");
    require_true(!enact_env_define(&env, NULL, enact_value_make_int(1)), "define null name fails");
    require_true(!enact_env_lookup(NULL, "x", &value), "lookup null env fails");
    require_true(!enact_env_lookup(&env, NULL, &value), "lookup null name fails");
    require_true(!enact_env_lookup(&env, "x", NULL), "lookup null out fails");

    enact_env_init(&env);
    require_true(!enact_env_lookup(&env, "missing", &value), "missing lookup fails");

    require_true(enact_env_define(&env, "x", enact_value_make_int(7)), "define int binding");
    require_true(enact_env_lookup(&env, "x", &value), "lookup int binding");
    require_true(value.kind == ENACT_VALUE_INT, "lookup int kind");
    require_true(value.as.as_int == 7, "lookup int value");

    require_true(enact_env_define(&env, "flag", enact_value_make_bool(true)), "define bool binding");
    require_true(enact_env_lookup(&env, "flag", &value), "lookup bool binding");
    require_true(value.kind == ENACT_VALUE_BOOL, "lookup bool kind");
    require_true(value.as.as_bool, "lookup bool value");

    string_binding = enact_value_make_string(copy_test_name("text"));
    require_true(enact_env_define(&env, "s", string_binding), "define string binding");
    enact_value_free(&string_binding);
    require_true(enact_env_lookup(&env, "s", &value), "lookup string binding");
    require_true(value.kind == ENACT_VALUE_STRING, "lookup string kind");
    require_true(strcmp(value.as.as_string, "text") == 0, "lookup string value");
    enact_value_free(&value);

    require_true(enact_env_define(&env, "x", enact_value_make_int(9)), "redefine int binding");
    require_true(enact_env_lookup(&env, "x", &value), "lookup redefined int binding");
    require_true(value.as.as_int == 9, "redefined int value");

    require_true(enact_env_clone(&clone, &env), "clone env succeeds");
    require_true(enact_env_lookup(&clone, "x", &value), "lookup cloned int binding");
    require_true(value.kind == ENACT_VALUE_INT, "cloned int kind");
    require_true(value.as.as_int == 9, "cloned int value");
    require_true(enact_env_lookup(&clone, "s", &value), "lookup cloned string binding");
    require_true(value.kind == ENACT_VALUE_STRING, "cloned string kind");
    require_true(strcmp(value.as.as_string, "text") == 0, "cloned string value");
    enact_value_free(&value);
    require_true(enact_env_define(&clone, "x", enact_value_make_int(100)), "redefine cloned int binding");
    require_true(enact_env_lookup(&clone, "x", &value), "lookup redefined clone binding");
    require_true(value.as.as_int == 100, "redefined clone value");
    require_true(enact_env_lookup(&env, "x", &value), "lookup original after clone redefine");
    require_true(value.as.as_int == 9, "original unchanged after clone redefine");
    enact_env_free(&clone);

    identifier = enact_ast_new_identifier(copy_test_name("x"));
    require_true(identifier != NULL, "identifier ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(identifier, &env, &result, &diag), "identifier resolves through env");
    require_true(result.kind == ENACT_VALUE_INT, "identifier result kind");
    require_true(result.as.as_int == 9, "identifier result value");
    enact_ast_free(identifier);

    left = enact_ast_new_identifier(copy_test_name("x"));
    right = enact_ast_new_int(1);
    sum = enact_ast_new_binary(AST_ADD, left, right);
    require_true(left != NULL && right != NULL && sum != NULL, "identifier arithmetic ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(sum, &env, &result, &diag), "identifier arithmetic resolves through env");
    require_true(result.kind == ENACT_VALUE_INT, "identifier arithmetic result kind");
    require_true(result.as.as_int == 10, "identifier arithmetic result value");
    enact_ast_free(sum);

    assignment = enact_ast_new_assignment(copy_test_name("z"), enact_ast_new_int(5));
    require_true(assignment != NULL, "assignment ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(assignment, &env, &result, &diag), "assignment evaluates through env");
    require_true(result.kind == ENACT_VALUE_INT, "assignment result kind");
    require_true(result.as.as_int == 5, "assignment result value");
    require_true(enact_env_lookup(&env, "z", &value), "assignment defines env binding");
    require_true(value.kind == ENACT_VALUE_INT, "assignment env binding kind");
    require_true(value.as.as_int == 5, "assignment env binding value");
    enact_ast_free(assignment);

    left = enact_ast_new_assignment(copy_test_name("a"), enact_ast_new_int(1));
    right = enact_ast_new_binary(
        AST_ADD,
        enact_ast_new_identifier(copy_test_name("a")),
        enact_ast_new_int(2));
    sequence = enact_ast_new_binary(AST_SEQUENCE, left, right);
    require_true(left != NULL && right != NULL && sequence != NULL, "sequence ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(sequence, &env, &result, &diag), "sequence evaluates left then right");
    require_true(result.kind == ENACT_VALUE_INT, "sequence result kind");
    require_true(result.as.as_int == 3, "sequence result value");
    enact_ast_free(sequence);

    where_ast = enact_ast_new_where(
        enact_ast_new_identifier(copy_test_name("w")),
        copy_test_name("w"),
        enact_ast_new_int(4));
    require_true(where_ast != NULL, "where ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(where_ast, &env, &result, &diag), "where evaluates through local env");
    require_true(result.kind == ENACT_VALUE_INT, "where result kind");
    require_true(result.as.as_int == 4, "where result value");
    require_true(!enact_env_lookup(&env, "w", &value), "where binding does not leak");
    enact_ast_free(where_ast);

    function_body = enact_ast_new_binary(
        AST_ADD,
        enact_ast_new_identifier(copy_test_name("p")),
        enact_ast_new_int(1));
    {
        const char *names[] = {"p"};
        params = make_test_name_list(names, 1);
    }
    arguments = make_test_ast_list1(enact_ast_new_int(4));
    function_literal = enact_ast_new_function_literal(params, function_body);
    function_call = enact_ast_new_call(function_literal, arguments);
    require_true(params != NULL && arguments != NULL && function_body != NULL && function_literal != NULL && function_call != NULL, "function call ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(function_call, &env, &result, &diag), "function call evaluates through env");
    require_true(result.kind == ENACT_VALUE_INT, "function call result kind");
    require_true(result.as.as_int == 5, "function call result value");
    enact_ast_free(function_call);

    function_body = enact_ast_new_binary(
        AST_ADD,
        enact_ast_new_identifier(copy_test_name("left")),
        enact_ast_new_identifier(copy_test_name("right")));
    {
        const char *names[] = {"left", "right"};
        params = make_test_name_list(names, 2);
    }
    arguments = make_test_ast_list2(enact_ast_new_int(2), enact_ast_new_int(3));
    function_literal = enact_ast_new_function_literal(params, function_body);
    function_call = enact_ast_new_call(function_literal, arguments);
    require_true(params != NULL && arguments != NULL && function_body != NULL && function_literal != NULL && function_call != NULL, "multi-argument function call ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(function_call, &env, &result, &diag), "multi-argument function call evaluates through env");
    require_true(result.kind == ENACT_VALUE_INT, "multi-argument function call result kind");
    require_true(result.as.as_int == 5, "multi-argument function call result value");
    enact_ast_free(function_call);

    function_body = enact_ast_new_binary(
        AST_ADD,
        enact_ast_new_identifier(copy_test_name("left")),
        enact_ast_new_identifier(copy_test_name("right")));
    {
        const char *names[] = {"left", "right"};
        params = make_test_name_list(names, 2);
    }
    arguments = make_test_ast_list1(enact_ast_new_int(2));
    function_literal = enact_ast_new_function_literal(params, function_body);
    function_call = enact_ast_new_call(function_literal, arguments);
    require_true(params != NULL && arguments != NULL && function_body != NULL && function_literal != NULL && function_call != NULL, "partial function call ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(function_call, &env, &result, &diag), "partial function call evaluates through env");
    require_true(result.kind == ENACT_VALUE_FUNCTION, "partial function call result kind");
    require_true(enact_function_arity(result.as.as_function) == 1, "partial function call result arity");
    require_true(strcmp(enact_function_param_name(result.as.as_function, 0), "right") == 0, "partial function call remaining param");
    enact_value_free(&result);
    enact_ast_free(function_call);

    function_body = enact_ast_new_identifier(copy_test_name("only"));
    {
        const char *names[] = {"only"};
        params = make_test_name_list(names, 1);
    }
    arguments = make_test_ast_list2(enact_ast_new_int(1), enact_ast_new_int(2));
    function_literal = enact_ast_new_function_literal(params, function_body);
    function_call = enact_ast_new_call(function_literal, arguments);
    require_true(params != NULL && arguments != NULL && function_body != NULL && function_literal != NULL && function_call != NULL, "arity mismatch call ast created");
    enact_diag_reset(&diag);
    require_true(!enact_eval_ast_with_env(function_call, &env, &result, &diag), "arity mismatch function call fails");
    require_true(diag.code == ENACT_ERR_ARITY_MISMATCH, "arity mismatch function call code");
    enact_ast_free(function_call);

    function_body = enact_ast_new_binary(
        AST_SEQUENCE,
        enact_ast_new_assignment(copy_test_name("x"), enact_ast_new_int(2)),
        enact_ast_new_identifier(copy_test_name("x")));
    {
        const char *names[] = {"x"};
        params = make_test_name_list(names, 1);
    }
    arguments = make_test_ast_list1(enact_ast_new_int(0));
    function_literal = enact_ast_new_function_literal(params, function_body);
    function_call = enact_ast_new_call(function_literal, arguments);
    require_true(params != NULL && arguments != NULL && function_body != NULL && function_literal != NULL && function_call != NULL, "function body assignment ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(function_call, &env, &result, &diag), "function body assignment evaluates locally");
    require_true(result.kind == ENACT_VALUE_INT, "function body assignment result kind");
    require_true(result.as.as_int == 2, "function body assignment result value");
    require_true(enact_env_lookup(&env, "x", &value), "lookup outer after function body assignment");
    require_true(value.as.as_int == 9, "function body assignment does not leak");
    enact_ast_free(function_call);

    identifier = enact_ast_new_identifier(copy_test_name("missing"));
    require_true(identifier != NULL, "missing identifier ast created");
    enact_diag_reset(&diag);
    require_true(!enact_eval_ast_with_env(identifier, &env, &result, &diag), "missing identifier fails");
    require_true(diag.code == ENACT_ERR_NAME_UNBOUND, "missing identifier code");
    enact_ast_free(identifier);

    enact_env_free(&env);
}

static void test_ast_clone_helpers(void)
{
    EnactAst unknown = {0};
    EnactAst *original;
    EnactAst *clone;
    EnactValue value;
    EnactDiag diag;
    EnactNameList *params;
    EnactAstList *arguments;

    require_true(enact_ast_clone(NULL) == NULL, "clone null ast fails");
    unknown.kind = (EnactAstKind)99;
    require_true(enact_ast_clone(&unknown) == NULL, "clone unknown ast fails");

    original = enact_ast_new_string(NULL);
    require_true(original != NULL, "null string clone source created");
    clone = enact_ast_clone(original);
    require_true(clone != NULL, "null string clone created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(clone, &value, &diag), "null string clone evaluates");
    require_true(value.kind == ENACT_VALUE_STRING, "null string clone result kind");
    require_true(strcmp(value.as.as_string, "") == 0, "null string clone result value");
    enact_value_free(&value);
    enact_ast_free(clone);
    enact_ast_free(original);

    original = enact_ast_new_conditional(
        enact_ast_new_bool(1),
        enact_ast_new_string(copy_test_name("yes")),
        enact_ast_new_string(copy_test_name("no")));
    require_true(original != NULL, "conditional clone source created");
    clone = enact_ast_clone(original);
    require_true(clone != NULL, "conditional clone created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(clone, &value, &diag), "conditional clone evaluates");
    require_true(value.kind == ENACT_VALUE_STRING, "conditional clone result kind");
    require_true(strcmp(value.as.as_string, "yes") == 0, "conditional clone result value");
    enact_value_free(&value);
    enact_ast_free(clone);
    enact_ast_free(original);

    {
        const char *names[] = {"x"};
        params = make_test_name_list(names, 1);
    }
    original = enact_ast_new_function_literal(
        params,
        enact_ast_new_identifier(copy_test_name("x")));
    require_true(original != NULL, "function literal clone source created");
    clone = enact_ast_clone(original);
    require_true(clone != NULL, "function literal clone created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(clone, &value, &diag), "function literal clone evaluates");
    require_true(value.kind == ENACT_VALUE_FUNCTION, "function literal clone result kind");
    enact_value_free(&value);
    enact_ast_free(clone);
    enact_ast_free(original);

    {
        const char *names[] = {"x"};
        params = make_test_name_list(names, 1);
    }
    arguments = make_test_ast_list1(enact_ast_new_int(7));
    original = enact_ast_new_call(
        enact_ast_new_function_literal(params, enact_ast_new_identifier(copy_test_name("x"))),
        arguments);
    require_true(params != NULL && arguments != NULL && original != NULL, "call clone source created");
    clone = enact_ast_clone(original);
    require_true(clone != NULL, "call clone created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(clone, &value, &diag), "call clone evaluates");
    require_true(value.kind == ENACT_VALUE_INT, "call clone result kind");
    require_true(value.as.as_int == 7, "call clone result value");
    enact_ast_free(clone);
    enact_ast_free(original);
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
    EnactAst string_node = {0};
    EnactAst eq_node = {0};
    EnactAst neq_node = {0};
    EnactAst lt_node = {0};
    EnactAst add_node = {0};
    EnactAst div_node = {0};
    EnactAst mod_node = {0};
    EnactAst and_node = {0};
    EnactAst or_node = {0};
    EnactAst not_node = {0};
    EnactAst conditional_node = {0};
    EnactAst *call_node;

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
    string_node.kind = AST_STRING_LITERAL;
    string_node.as.string_value = "unit";

    eq_node.kind = AST_EQ;
    eq_node.as.binary.left = &bool_true;
    eq_node.as.binary.right = &int_one;
    enact_diag_reset(&diag);
    require_true(!enact_eval_ast(&eq_node, &value, &diag), "equality mismatch fails");
    require_true(diag.code == ENACT_ERR_TYPE_EQUALITY_MISMATCH, "equality mismatch code");

    eq_node.as.binary.left = &string_node;
    eq_node.as.binary.right = &string_node;
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(&eq_node, &value, &diag), "string equality succeeds");
    require_true(value.kind == ENACT_VALUE_BOOL, "string equality kind");
    require_true(value.as.as_bool, "string equality value");

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

    mod_node.kind = AST_MOD;
    mod_node.as.binary.left = &int_seven;
    mod_node.as.binary.right = &int_one;
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(&mod_node, &value, &diag), "mod succeeds");
    require_true(value.kind == ENACT_VALUE_INT, "mod result kind");
    require_true(value.as.as_int == 0, "mod result value");

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

    call_node = enact_ast_new_call(enact_ast_new_int(1), make_test_ast_list1(enact_ast_new_int(0)));
    require_true(call_node != NULL, "non-function call ast created");
    enact_diag_reset(&diag);
    require_true(!enact_eval_ast(call_node, &value, &diag), "non-function call fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_FUNCTION, "non-function call code");
    enact_ast_free(call_node);

    enact_diag_reset(&diag);
    require_true(enact_eval_ast(&string_node, &value, &diag), "string literal ast succeeds");
    require_true(value.kind == ENACT_VALUE_STRING, "string literal ast kind");
    require_true(strcmp(value.as.as_string, "unit") == 0, "string literal ast value");
    enact_value_free(&value);
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
    require_true(enact_dump_tokens_text("$", tmp, &diag) != 0, "token dump invalid char fails");
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
    test_env_helpers();
    test_ast_clone_helpers();
    test_parser_state_helpers();
    test_eval_edge_cases();
    test_api_and_scan_helpers();

    if (failures != 0) {
        return 1;
    }

    puts("unit tests passed");
    return 0;
}
