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

void enact_ast_free(EnactAst *ast)
{
    if (!ast) {
        return;
    }

    switch (ast->kind) {
    case AST_INT_LITERAL:
        break;
    case AST_UNARY_NEG:
        enact_ast_free(ast->as.unary.child);
        break;
    case AST_ADD:
    case AST_SUB:
    case AST_MUL:
    case AST_DIV:
        enact_ast_free(ast->as.binary.left);
        enact_ast_free(ast->as.binary.right);
        break;
    }

    free(ast);
}
