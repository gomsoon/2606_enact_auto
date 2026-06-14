%{
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
%}

%define parse.error verbose

%union {
    uint64_t u64;
    EnactAst *ast;
}

%token <u64> TOK_INT_LITERAL
%token TOK_UMINUS TOK_PLUS TOK_MINUS TOK_STAR TOK_SLASH TOK_LPAREN TOK_RPAREN TOK_DOT TOK_ERROR

%type <ast> expr additive multiplicative unary primary

%destructor { enact_ast_free($$); } <ast>

%%

input:
    expr TOK_DOT
    {
        enact_parse_context_take_root($1);
    }
    ;

expr:
    additive
    {
        $$ = $1;
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

    if (state && !state->saw_dot) {
        enact_diag_set(&context->diag, ENACT_ERR_PARSE_MISSING_DOT, (int)state->offset);
        return;
    }

    enact_diag_set(&context->diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, state ? (int)state->token_offset : -1);
}
