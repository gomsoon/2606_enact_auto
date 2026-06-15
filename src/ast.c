#include <stdlib.h>

#include "ast.h"

static EnactAst *enact_ast_alloc(EnactAstKind kind)
{
    EnactAst *ast = calloc(1, sizeof(*ast));
    if (!ast) {
        return NULL;
    }

    ast->kind = kind;
    ast->span.start_offset = -1;
    ast->span.end_offset = -1;
    return ast;
}

EnactAst *enact_ast_new_int(uint64_t int_magnitude)
{
    EnactAst *ast = enact_ast_alloc(AST_INT_LITERAL);
    if (!ast) {
        return NULL;
    }

    ast->as.int_magnitude = int_magnitude;
    return ast;
}

EnactAst *enact_ast_new_bool(int bool_value)
{
    EnactAst *ast = enact_ast_alloc(AST_BOOL_LITERAL);
    if (!ast) {
        return NULL;
    }

    ast->as.bool_value = bool_value != 0;
    return ast;
}

EnactAst *enact_ast_new_identifier(char *name)
{
    EnactAst *ast = enact_ast_alloc(AST_IDENTIFIER);
    if (!ast) {
        return NULL;
    }

    ast->as.identifier_name = name;
    return ast;
}

EnactAst *enact_ast_new_unary(EnactAstKind kind, EnactAst *child)
{
    EnactAst *ast = enact_ast_alloc(kind);
    if (!ast) {
        return NULL;
    }

    ast->as.unary.child = child;
    return ast;
}

EnactAst *enact_ast_new_binary(EnactAstKind kind, EnactAst *left, EnactAst *right)
{
    EnactAst *ast = enact_ast_alloc(kind);
    if (!ast) {
        return NULL;
    }

    ast->as.binary.left = left;
    ast->as.binary.right = right;
    return ast;
}

EnactAst *enact_ast_new_conditional(EnactAst *condition, EnactAst *if_true, EnactAst *if_false)
{
    EnactAst *ast = enact_ast_alloc(AST_IF_ELSE);
    if (!ast) {
        return NULL;
    }

    ast->as.conditional.condition = condition;
    ast->as.conditional.if_true = if_true;
    ast->as.conditional.if_false = if_false;
    return ast;
}

void enact_ast_free(EnactAst *ast)
{
    if (!ast) {
        return;
    }

    switch (ast->kind) {
    case AST_INT_LITERAL:
    case AST_BOOL_LITERAL:
        break;
    case AST_IDENTIFIER:
        free(ast->as.identifier_name);
        break;
    case AST_UNARY_NEG:
    case AST_NOT:
        enact_ast_free(ast->as.unary.child);
        break;
    case AST_ADD:
    case AST_SUB:
    case AST_MUL:
    case AST_DIV:
    case AST_EQ:
    case AST_NEQ:
    case AST_LT:
    case AST_GT:
    case AST_LTE:
    case AST_GTE:
    case AST_AND:
    case AST_OR:
        enact_ast_free(ast->as.binary.left);
        enact_ast_free(ast->as.binary.right);
        break;
    case AST_IF_ELSE:
        enact_ast_free(ast->as.conditional.condition);
        enact_ast_free(ast->as.conditional.if_true);
        enact_ast_free(ast->as.conditional.if_false);
        break;
    }

    free(ast);
}
