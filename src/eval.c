#include <limits.h>
#include <stdint.h>
#include <string.h>

#include "eval.h"

static int enact_eval_value(const EnactAst *ast, EnactEnv *env, EnactValue *out, EnactDiag *diag);

static int enact_checked_binary(const EnactAst *ast, int32_t left, int32_t right, int32_t *out, EnactDiag *diag)
{
    int64_t intermediate = 0;

    switch (ast->kind) {
    case AST_ADD:
        intermediate = (int64_t)left + (int64_t)right;
        break;
    case AST_SUB:
        intermediate = (int64_t)left - (int64_t)right;
        break;
    case AST_MUL:
        intermediate = (int64_t)left * (int64_t)right;
        break;
    case AST_DIV:
        if (right == 0) {
            enact_diag_set(diag, ENACT_ERR_DIVIDE_BY_ZERO, -1);
            return 0;
        }
        if (left == INT32_MIN && right == -1) {
            enact_diag_set(diag, ENACT_ERR_INT_OVERFLOW, -1);
            return 0;
        }
        intermediate = left / right;
        break;
    case AST_MOD:
        if (right == 0) {
            enact_diag_set(diag, ENACT_ERR_DIVIDE_BY_ZERO, -1);
            return 0;
        }
        if (left == INT32_MIN && right == -1) {
            enact_diag_set(diag, ENACT_ERR_INT_OVERFLOW, -1);
            return 0;
        }
        intermediate = left % right;
        break;
    default:
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }

    if (intermediate < INT32_MIN || intermediate > INT32_MAX) {
        enact_diag_set(diag, ENACT_ERR_INT_OVERFLOW, -1);
        return 0;
    }

    *out = (int32_t)intermediate;
    return 1;
}

static int enact_require_int(const EnactValue *value, int32_t *out, EnactDiag *diag)
{
    if (value->kind != ENACT_VALUE_INT) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_INT, -1);
        return 0;
    }

    *out = value->as.as_int;
    return 1;
}

static int enact_require_bool(const EnactValue *value, bool *out, EnactDiag *diag)
{
    if (value->kind != ENACT_VALUE_BOOL) {
        enact_diag_set(diag, ENACT_ERR_TYPE_EXPECTED_BOOL, -1);
        return 0;
    }

    *out = value->as.as_bool;
    return 1;
}

static int enact_eval_arithmetic_binary(const EnactAst *ast, EnactEnv *env, EnactValue *out, EnactDiag *diag)
{
    EnactValue left_value;
    EnactValue right_value;
    int32_t left = 0;
    int32_t right = 0;
    int32_t result = 0;

    if (!enact_eval_value(ast->as.binary.left, env, &left_value, diag)) {
        return 0;
    }
    if (!enact_require_int(&left_value, &left, diag)) {
        enact_value_free(&left_value);
        return 0;
    }
    if (!enact_eval_value(ast->as.binary.right, env, &right_value, diag)) {
        enact_value_free(&left_value);
        return 0;
    }
    if (!enact_require_int(&right_value, &right, diag)) {
        enact_value_free(&left_value);
        enact_value_free(&right_value);
        return 0;
    }
    if (!enact_checked_binary(ast, left, right, &result, diag)) {
        enact_value_free(&left_value);
        enact_value_free(&right_value);
        return 0;
    }

    enact_value_free(&left_value);
    enact_value_free(&right_value);
    *out = enact_value_make_int(result);
    return 1;
}

static int enact_eval_equality(const EnactAst *ast, EnactEnv *env, EnactValue *out, EnactDiag *diag)
{
    EnactValue left;
    EnactValue right;
    bool result = false;

    if (!enact_eval_value(ast->as.binary.left, env, &left, diag)) {
        return 0;
    }
    if (!enact_eval_value(ast->as.binary.right, env, &right, diag)) {
        enact_value_free(&left);
        return 0;
    }
    if (left.kind != right.kind) {
        enact_value_free(&left);
        enact_value_free(&right);
        enact_diag_set(diag, ENACT_ERR_TYPE_EQUALITY_MISMATCH, -1);
        return 0;
    }

    switch (left.kind) {
    case ENACT_VALUE_INT:
        result = left.as.as_int == right.as.as_int;
        break;
    case ENACT_VALUE_BOOL:
        result = left.as.as_bool == right.as.as_bool;
        break;
    case ENACT_VALUE_STRING:
        result = strcmp(left.as.as_string, right.as.as_string) == 0;
        break;
    }

    if (ast->kind == AST_NEQ) {
        result = !result;
    }

    enact_value_free(&left);
    enact_value_free(&right);
    *out = enact_value_make_bool(result);
    return 1;
}

static int enact_eval_ordering(const EnactAst *ast, EnactEnv *env, EnactValue *out, EnactDiag *diag)
{
    EnactValue left_value;
    EnactValue right_value;
    int32_t left = 0;
    int32_t right = 0;
    bool result = false;

    if (!enact_eval_value(ast->as.binary.left, env, &left_value, diag)) {
        return 0;
    }
    if (!enact_require_int(&left_value, &left, diag)) {
        enact_value_free(&left_value);
        return 0;
    }
    if (!enact_eval_value(ast->as.binary.right, env, &right_value, diag)) {
        enact_value_free(&left_value);
        return 0;
    }
    if (!enact_require_int(&right_value, &right, diag)) {
        enact_value_free(&left_value);
        enact_value_free(&right_value);
        return 0;
    }

    switch (ast->kind) {
    case AST_LT:
        result = left < right;
        break;
    case AST_GT:
        result = left > right;
        break;
    case AST_LTE:
        result = left <= right;
        break;
    case AST_GTE:
        result = left >= right;
        break;
    default:
        enact_value_free(&left_value);
        enact_value_free(&right_value);
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }

    enact_value_free(&left_value);
    enact_value_free(&right_value);
    *out = enact_value_make_bool(result);
    return 1;
}

static int enact_eval_and(const EnactAst *ast, EnactEnv *env, EnactValue *out, EnactDiag *diag)
{
    EnactValue left;
    EnactValue right;
    bool left_bool = false;
    bool right_bool = false;

    if (!enact_eval_value(ast->as.binary.left, env, &left, diag)) {
        return 0;
    }
    if (!enact_require_bool(&left, &left_bool, diag)) {
        enact_value_free(&left);
        return 0;
    }
    if (!left_bool) {
        enact_value_free(&left);
        *out = enact_value_make_bool(false);
        return 1;
    }

    enact_value_free(&left);
    if (!enact_eval_value(ast->as.binary.right, env, &right, diag)) {
        return 0;
    }
    if (!enact_require_bool(&right, &right_bool, diag)) {
        enact_value_free(&right);
        return 0;
    }

    enact_value_free(&right);
    *out = enact_value_make_bool(right_bool);
    return 1;
}

static int enact_eval_or(const EnactAst *ast, EnactEnv *env, EnactValue *out, EnactDiag *diag)
{
    EnactValue left;
    EnactValue right;
    bool left_bool = false;
    bool right_bool = false;

    if (!enact_eval_value(ast->as.binary.left, env, &left, diag)) {
        return 0;
    }
    if (!enact_require_bool(&left, &left_bool, diag)) {
        enact_value_free(&left);
        return 0;
    }
    if (left_bool) {
        enact_value_free(&left);
        *out = enact_value_make_bool(true);
        return 1;
    }

    enact_value_free(&left);
    if (!enact_eval_value(ast->as.binary.right, env, &right, diag)) {
        return 0;
    }
    if (!enact_require_bool(&right, &right_bool, diag)) {
        enact_value_free(&right);
        return 0;
    }

    enact_value_free(&right);
    *out = enact_value_make_bool(right_bool);
    return 1;
}

static int enact_eval_conditional(const EnactAst *ast, EnactEnv *env, EnactValue *out, EnactDiag *diag)
{
    EnactValue condition;
    bool condition_bool = false;

    if (!enact_eval_value(ast->as.conditional.condition, env, &condition, diag)) {
        return 0;
    }
    if (!enact_require_bool(&condition, &condition_bool, diag)) {
        enact_value_free(&condition);
        return 0;
    }

    enact_value_free(&condition);
    if (condition_bool) {
        return enact_eval_value(ast->as.conditional.if_true, env, out, diag);
    }

    return enact_eval_value(ast->as.conditional.if_false, env, out, diag);
}

static int enact_eval_assignment(const EnactAst *ast, EnactEnv *env, EnactValue *out, EnactDiag *diag)
{
    EnactValue value;

    if (!enact_eval_value(ast->as.assignment.value, env, &value, diag)) {
        return 0;
    }
    if (!enact_env_define(env, ast->as.assignment.name, value)) {
        enact_value_free(&value);
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    *out = value;
    return 1;
}

static int enact_eval_where(const EnactAst *ast, EnactEnv *env, EnactValue *out, EnactDiag *diag)
{
    EnactEnv local;
    EnactValue binding_value;
    int status = 0;

    if (!enact_env_clone(&local, env)) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    if (!enact_eval_value(ast->as.where_expr.value, &local, &binding_value, diag)) {
        enact_env_free(&local);
        return 0;
    }
    if (!enact_env_define(&local, ast->as.where_expr.name, binding_value)) {
        enact_value_free(&binding_value);
        enact_env_free(&local);
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }
    enact_value_free(&binding_value);

    status = enact_eval_value(ast->as.where_expr.body, &local, out, diag);
    enact_env_free(&local);
    return status;
}

static int enact_eval_sequence(const EnactAst *ast, EnactEnv *env, EnactValue *out, EnactDiag *diag)
{
    EnactValue ignored;

    if (!enact_eval_value(ast->as.binary.left, env, &ignored, diag)) {
        return 0;
    }

    enact_value_free(&ignored);
    return enact_eval_value(ast->as.binary.right, env, out, diag);
}

static int enact_eval_value(const EnactAst *ast, EnactEnv *env, EnactValue *out, EnactDiag *diag)
{
    EnactValue child;
    EnactValue literal;
    int32_t int_value = 0;
    bool bool_value = false;

    if (!ast) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }

    switch (ast->kind) {
    case AST_INT_LITERAL:
        if (ast->as.int_magnitude > (uint64_t)INT32_MAX) {
            enact_diag_set(diag, ENACT_ERR_INT_OVERFLOW, -1);
            return 0;
        }
        *out = enact_value_make_int((int32_t)ast->as.int_magnitude);
        return 1;
    case AST_BOOL_LITERAL:
        *out = enact_value_make_bool(ast->as.bool_value != 0);
        return 1;
    case AST_STRING_LITERAL:
        literal = enact_value_make_string(ast->as.string_value);
        if (!enact_value_copy(out, &literal)) {
            enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
            return 0;
        }
        return 1;
    case AST_IDENTIFIER:
        if (enact_env_lookup(env, ast->as.identifier_name, out)) {
            return 1;
        }
        enact_diag_set(diag, ENACT_ERR_NAME_UNBOUND, -1);
        return 0;
    case AST_UNARY_NEG:
        if (ast->as.unary.child && ast->as.unary.child->kind == AST_INT_LITERAL &&
            ast->as.unary.child->as.int_magnitude == ((uint64_t)INT32_MAX + 1ULL)) {
            *out = enact_value_make_int(INT32_MIN);
            return 1;
        }
        if (!enact_eval_value(ast->as.unary.child, env, &child, diag)) {
            return 0;
        }
        if (!enact_require_int(&child, &int_value, diag)) {
            enact_value_free(&child);
            return 0;
        }
        if (int_value == INT32_MIN) {
            enact_value_free(&child);
            enact_diag_set(diag, ENACT_ERR_INT_OVERFLOW, -1);
            return 0;
        }
        enact_value_free(&child);
        *out = enact_value_make_int(-int_value);
        return 1;
    case AST_NOT:
        if (!enact_eval_value(ast->as.unary.child, env, &child, diag)) {
            return 0;
        }
        if (!enact_require_bool(&child, &bool_value, diag)) {
            enact_value_free(&child);
            return 0;
        }
        enact_value_free(&child);
        *out = enact_value_make_bool(!bool_value);
        return 1;
    case AST_ADD:
    case AST_SUB:
    case AST_MUL:
    case AST_DIV:
    case AST_MOD:
        return enact_eval_arithmetic_binary(ast, env, out, diag);
    case AST_EQ:
    case AST_NEQ:
        return enact_eval_equality(ast, env, out, diag);
    case AST_LT:
    case AST_GT:
    case AST_LTE:
    case AST_GTE:
        return enact_eval_ordering(ast, env, out, diag);
    case AST_AND:
        return enact_eval_and(ast, env, out, diag);
    case AST_OR:
        return enact_eval_or(ast, env, out, diag);
    case AST_IF_ELSE:
        return enact_eval_conditional(ast, env, out, diag);
    case AST_WHERE:
        return enact_eval_where(ast, env, out, diag);
    case AST_ASSIGN:
        return enact_eval_assignment(ast, env, out, diag);
    case AST_SEQUENCE:
        return enact_eval_sequence(ast, env, out, diag);
    }

    enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
    return 0;
}

int enact_eval_ast(const EnactAst *ast, EnactValue *value, EnactDiag *diag)
{
    EnactEnv env;
    int status;

    enact_env_init(&env);
    status = enact_eval_ast_with_env(ast, &env, value, diag);
    enact_env_free(&env);
    return status;
}

int enact_eval_ast_with_env(const EnactAst *ast, EnactEnv *env, EnactValue *value, EnactDiag *diag)
{
    if (!value) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }

    return enact_eval_value(ast, env, value, diag);
}
