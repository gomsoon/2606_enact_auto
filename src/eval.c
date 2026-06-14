#include <limits.h>
#include <stdint.h>

#include "eval.h"

static int enact_eval_int(const EnactAst *ast, int32_t *out, EnactDiag *diag);

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

static int enact_eval_int(const EnactAst *ast, int32_t *out, EnactDiag *diag)
{
    int32_t left = 0;
    int32_t right = 0;

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
        *out = (int32_t)ast->as.int_magnitude;
        return 1;
    case AST_UNARY_NEG:
        if (ast->as.unary.child && ast->as.unary.child->kind == AST_INT_LITERAL &&
            ast->as.unary.child->as.int_magnitude == ((uint64_t)INT32_MAX + 1ULL)) {
            *out = INT32_MIN;
            return 1;
        }
        if (!enact_eval_int(ast->as.unary.child, &left, diag)) {
            return 0;
        }
        if (left == INT32_MIN) {
            enact_diag_set(diag, ENACT_ERR_INT_OVERFLOW, -1);
            return 0;
        }
        *out = -left;
        return 1;
    case AST_ADD:
    case AST_SUB:
    case AST_MUL:
    case AST_DIV:
        if (!enact_eval_int(ast->as.binary.left, &left, diag)) {
            return 0;
        }
        if (!enact_eval_int(ast->as.binary.right, &right, diag)) {
            return 0;
        }
        return enact_checked_binary(ast, left, right, out, diag);
    }

    enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
    return 0;
}

int enact_eval_ast(const EnactAst *ast, EnactValue *value, EnactDiag *diag)
{
    int32_t result = 0;

    if (!value) {
        enact_diag_set(diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, -1);
        return 0;
    }

    if (!enact_eval_int(ast, &result, diag)) {
        return 0;
    }

    value->kind = ENACT_VALUE_INT;
    value->as_int = result;
    return 1;
}
