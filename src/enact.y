%{
#include <stdlib.h>
#include <stdint.h>

#include "ast.h"
#include "diag.h"
#include "parser_state.h"

int yylex(void);
static void yyerror(const char *message);

static EnactAst *enact_make_int(uint64_t magnitude)
{
    EnactAst *ast = enact_ast_new_int(magnitude);
    EnactParseContext *context = enact_get_parse_context();

    if (!ast && context) {
        enact_diag_set(&context->diag, ENACT_ERR_OUT_OF_MEMORY, -1);
    }

    return ast;
}

static EnactAst *enact_make_bool(int value)
{
    EnactAst *ast = enact_ast_new_bool(value);
    EnactParseContext *context = enact_get_parse_context();

    if (!ast && context) {
        enact_diag_set(&context->diag, ENACT_ERR_OUT_OF_MEMORY, -1);
    }

    return ast;
}

static EnactAst *enact_make_string(char *value)
{
    EnactAst *ast = enact_ast_new_string(value);
    EnactParseContext *context = enact_get_parse_context();

    if (!ast && context) {
        enact_diag_set(&context->diag, ENACT_ERR_OUT_OF_MEMORY, -1);
    }

    return ast;
}

static EnactAst *enact_make_identifier(char *name)
{
    EnactAst *ast = enact_ast_new_identifier(name);
    EnactParseContext *context = enact_get_parse_context();

    if (!ast && context) {
        enact_diag_set(&context->diag, ENACT_ERR_OUT_OF_MEMORY, -1);
    }

    return ast;
}

static EnactAst *enact_make_unary(EnactAstKind kind, EnactAst *child)
{
    EnactAst *ast = enact_ast_new_unary(kind, child);
    EnactParseContext *context = enact_get_parse_context();

    if (!ast && context) {
        enact_diag_set(&context->diag, ENACT_ERR_OUT_OF_MEMORY, -1);
    }

    return ast;
}

static EnactAst *enact_make_binary(EnactAstKind kind, EnactAst *left, EnactAst *right)
{
    EnactAst *ast = enact_ast_new_binary(kind, left, right);
    EnactParseContext *context = enact_get_parse_context();

    if (!ast && context) {
        enact_diag_set(&context->diag, ENACT_ERR_OUT_OF_MEMORY, -1);
    }

    return ast;
}

static EnactAst *enact_make_conditional(EnactAst *condition, EnactAst *if_true, EnactAst *if_false)
{
    EnactAst *ast = enact_ast_new_conditional(condition, if_true, if_false);
    EnactParseContext *context = enact_get_parse_context();

    if (!ast && context) {
        enact_diag_set(&context->diag, ENACT_ERR_OUT_OF_MEMORY, -1);
    }

    return ast;
}

static EnactAst *enact_make_assignment(char *name, EnactAst *value)
{
    EnactAst *ast = enact_ast_new_assignment(name, value);
    EnactParseContext *context = enact_get_parse_context();

    if (!ast && context) {
        enact_diag_set(&context->diag, ENACT_ERR_OUT_OF_MEMORY, -1);
    }

    return ast;
}
%}

%define parse.error verbose

%union {
    uint64_t u64;
    char *text;
    EnactAst *ast;
}

%token <u64> TOK_INT_LITERAL
%token <text> TOK_IDENTIFIER TOK_STRING_LITERAL
%token TOK_UMINUS TOK_PLUS TOK_MINUS TOK_STAR TOK_SLASH TOK_LPAREN TOK_RPAREN TOK_DOT TOK_ERROR
%token TOK_EQEQ TOK_TRUE TOK_FALSE TOK_NOT TOK_AND TOK_OR TOK_IF TOK_ELSE
%token TOK_NEQ TOK_LT TOK_GT TOK_LTE TOK_GTE
%token TOK_ASSIGN TOK_SEMI TOK_MOD

%type <ast> expr sequence assignment conditional logical_or logical_and logical_not comparison additive multiplicative unary primary

%destructor { enact_ast_free($$); } <ast>
%destructor { free($$); } <text>

%%

input:
    expr TOK_DOT
    {
        enact_parse_context_take_root($1);
    }
    ;

expr:
    sequence
    {
        $$ = $1;
    }
    ;

sequence:
    sequence TOK_SEMI assignment
    {
        $$ = enact_make_binary(AST_SEQUENCE, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | assignment
    {
        $$ = $1;
    }
    ;

assignment:
    TOK_IDENTIFIER TOK_ASSIGN assignment
    {
        $$ = enact_make_assignment($1, $3);
        if (!$$) {
            free($1);
            enact_ast_free($3);
            YYABORT;
        }
    }
    | conditional
    {
        $$ = $1;
    }
    ;

conditional:
    logical_or
    {
        $$ = $1;
    }
    | logical_or TOK_IF logical_or TOK_ELSE conditional
    {
        $$ = enact_make_conditional($3, $1, $5);
        if (!$$) {
            YYABORT;
        }
    }
    ;

logical_or:
    logical_or TOK_OR logical_and
    {
        $$ = enact_make_binary(AST_OR, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | logical_and
    {
        $$ = $1;
    }
    ;

logical_and:
    logical_and TOK_AND logical_not
    {
        $$ = enact_make_binary(AST_AND, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | logical_not
    {
        $$ = $1;
    }
    ;

logical_not:
    TOK_NOT logical_not
    {
        $$ = enact_make_unary(AST_NOT, $2);
        if (!$$) {
            YYABORT;
        }
    }
    | comparison
    {
        $$ = $1;
    }
    ;

comparison:
    additive
    {
        $$ = $1;
    }
    | additive TOK_EQEQ additive
    {
        $$ = enact_make_binary(AST_EQ, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | additive TOK_NEQ additive
    {
        $$ = enact_make_binary(AST_NEQ, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | additive TOK_LT additive
    {
        $$ = enact_make_binary(AST_LT, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | additive TOK_GT additive
    {
        $$ = enact_make_binary(AST_GT, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | additive TOK_LTE additive
    {
        $$ = enact_make_binary(AST_LTE, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | additive TOK_GTE additive
    {
        $$ = enact_make_binary(AST_GTE, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    ;

additive:
    additive TOK_PLUS multiplicative
    {
        $$ = enact_make_binary(AST_ADD, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | additive TOK_MINUS multiplicative
    {
        $$ = enact_make_binary(AST_SUB, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | multiplicative
    {
        $$ = $1;
    }
    ;

multiplicative:
    multiplicative TOK_STAR unary
    {
        $$ = enact_make_binary(AST_MUL, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | multiplicative TOK_SLASH unary
    {
        $$ = enact_make_binary(AST_DIV, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | multiplicative TOK_MOD unary
    {
        $$ = enact_make_binary(AST_MOD, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | unary
    {
        $$ = $1;
    }
    ;

unary:
    TOK_UMINUS unary
    {
        $$ = enact_make_unary(AST_UNARY_NEG, $2);
        if (!$$) {
            YYABORT;
        }
    }
    | primary
    {
        $$ = $1;
    }
    ;

primary:
    TOK_INT_LITERAL
    {
        $$ = enact_make_int($1);
        if (!$$) {
            YYABORT;
        }
    }
    | TOK_TRUE
    {
        $$ = enact_make_bool(1);
        if (!$$) {
            YYABORT;
        }
    }
    | TOK_FALSE
    {
        $$ = enact_make_bool(0);
        if (!$$) {
            YYABORT;
        }
    }
    | TOK_STRING_LITERAL
    {
        $$ = enact_make_string($1);
        if (!$$) {
            free($1);
            YYABORT;
        }
    }
    | TOK_IDENTIFIER
    {
        $$ = enact_make_identifier($1);
        if (!$$) {
            free($1);
            YYABORT;
        }
    }
    | TOK_LPAREN expr TOK_RPAREN
    {
        $$ = $2;
    }
    ;

%%

static void yyerror(const char *message)
{
    EnactParseContext *context = enact_get_parse_context();
    EnactScannerState *state = enact_get_scanner_state();

    (void)message;

    if (!context || context->diag.code != ENACT_OK) {
        return;
    }

    if (state && state->paren_balance != 0) {
        enact_diag_set(&context->diag, ENACT_ERR_PARSE_UNMATCHED_PAREN, (int)state->token_offset);
        return;
    }

    if (state && !state->saw_dot && state->last_token == 0) {
        enact_diag_set(&context->diag, ENACT_ERR_PARSE_MISSING_DOT, (int)state->offset);
        return;
    }

    enact_diag_set(&context->diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, state ? (int)state->token_offset : -1);
}
