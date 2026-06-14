#ifndef ENACT_AST_H
#define ENACT_AST_H

#include <stdint.h>

typedef enum {
    AST_INT_LITERAL,
    AST_UNARY_NEG,
    AST_ADD,
    AST_SUB,
    AST_MUL,
    AST_DIV
} EnactAstKind;

typedef struct EnactSourceSpan {
    int start_offset;
    int end_offset;
} EnactSourceSpan;

typedef struct EnactAst EnactAst;

struct EnactAst {
    EnactAstKind kind;
    EnactSourceSpan span;
    union {
        uint64_t int_magnitude;
        struct {
            EnactAst *child;
        } unary;
        struct {
            EnactAst *left;
            EnactAst *right;
        } binary;
    } as;
};

EnactAst *enact_ast_new_int(uint64_t int_magnitude);
EnactAst *enact_ast_new_unary(EnactAstKind kind, EnactAst *child);
EnactAst *enact_ast_new_binary(EnactAstKind kind, EnactAst *left, EnactAst *right);
void enact_ast_free(EnactAst *ast);

#endif
