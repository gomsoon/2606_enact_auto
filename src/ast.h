#ifndef ENACT_AST_H
#define ENACT_AST_H

#include <stdint.h>

typedef enum {
    AST_INT_LITERAL,
    AST_BOOL_LITERAL,
    AST_UNARY_NEG,
    AST_NOT,
    AST_ADD,
    AST_SUB,
    AST_MUL,
    AST_DIV,
    AST_EQ,
    AST_AND,
    AST_OR,
    AST_IF_ELSE
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
        int bool_value;
        struct {
            EnactAst *child;
        } unary;
        struct {
            EnactAst *left;
            EnactAst *right;
        } binary;
        struct {
            EnactAst *condition;
            EnactAst *if_true;
            EnactAst *if_false;
        } conditional;
    } as;
};

EnactAst *enact_ast_new_int(uint64_t int_magnitude);
EnactAst *enact_ast_new_bool(int bool_value);
EnactAst *enact_ast_new_unary(EnactAstKind kind, EnactAst *child);
EnactAst *enact_ast_new_binary(EnactAstKind kind, EnactAst *left, EnactAst *right);
EnactAst *enact_ast_new_conditional(EnactAst *condition, EnactAst *if_true, EnactAst *if_false);
void enact_ast_free(EnactAst *ast);

#endif
