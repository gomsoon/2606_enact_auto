#ifndef ENACT_AST_H
#define ENACT_AST_H

#include <stddef.h>
#include <stdint.h>

typedef enum {
    AST_INT_LITERAL,
    AST_BOOL_LITERAL,
    AST_STRING_LITERAL,
    AST_NIL,
    AST_IDENTIFIER,
    AST_GROUP,
    AST_UNARY_NEG,
    AST_NOT,
    AST_ADD,
    AST_SUB,
    AST_MUL,
    AST_DIV,
    AST_MOD,
    AST_EQ,
    AST_NEQ,
    AST_LT,
    AST_GT,
    AST_LTE,
    AST_GTE,
    AST_CONS,
    AST_AND,
    AST_OR,
    AST_IF_ELSE,
    AST_WHERE,
    AST_ASSIGN,
    AST_FUNCTION_LITERAL,
    AST_CALL,
    AST_SEQUENCE
} EnactAstKind;

typedef struct EnactSourceSpan {
    int start_offset;
    int end_offset;
} EnactSourceSpan;

typedef struct EnactAst EnactAst;

typedef struct {
    char **items;
    size_t count;
    size_t capacity;
} EnactNameList;

typedef struct {
    EnactAst **items;
    size_t count;
    size_t capacity;
} EnactAstList;

struct EnactAst {
    EnactAstKind kind;
    EnactSourceSpan span;
    union {
        uint64_t int_magnitude;
        int bool_value;
        char *string_value;
        char *identifier_name;
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
        struct {
            EnactAst *body;
            char *name;
            EnactAst *value;
        } where_expr;
        struct {
            char *name;
            EnactAst *value;
        } assignment;
        struct {
            EnactNameList *param_names;
            EnactAst *body;
        } function_literal;
        struct {
            EnactAst *callee;
            EnactAstList *arguments;
        } call;
    } as;
};

EnactNameList *enact_name_list_new(void);
int enact_name_list_append(EnactNameList *list, char *name);
EnactNameList *enact_name_list_clone(const EnactNameList *list);
size_t enact_name_list_count(const EnactNameList *list);
const char *enact_name_list_get(const EnactNameList *list, size_t index);
int enact_name_list_contains(const EnactNameList *list, const char *name);
void enact_name_list_free(EnactNameList *list);

EnactAstList *enact_ast_list_new(void);
int enact_ast_list_append(EnactAstList *list, EnactAst *ast);
EnactAstList *enact_ast_list_clone(const EnactAstList *list);
size_t enact_ast_list_count(const EnactAstList *list);
EnactAst *enact_ast_list_get(const EnactAstList *list, size_t index);
void enact_ast_list_free(EnactAstList *list);

EnactAst *enact_ast_new_int(uint64_t int_magnitude);
EnactAst *enact_ast_new_bool(int bool_value);
EnactAst *enact_ast_new_string(char *value);
EnactAst *enact_ast_new_nil(void);
EnactAst *enact_ast_new_identifier(char *name);
EnactAst *enact_ast_new_unary(EnactAstKind kind, EnactAst *child);
EnactAst *enact_ast_new_binary(EnactAstKind kind, EnactAst *left, EnactAst *right);
EnactAst *enact_ast_new_conditional(EnactAst *condition, EnactAst *if_true, EnactAst *if_false);
EnactAst *enact_ast_new_where(EnactAst *body, char *name, EnactAst *value);
EnactAst *enact_ast_new_assignment(char *name, EnactAst *value);
EnactAst *enact_ast_new_function_literal(EnactNameList *param_names, EnactAst *body);
EnactAst *enact_ast_new_call(EnactAst *callee, EnactAstList *arguments);
EnactAst *enact_ast_clone(const EnactAst *ast);
void enact_ast_free(EnactAst *ast);

#endif
