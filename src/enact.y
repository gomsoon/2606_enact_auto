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

static EnactAst *enact_make_nil(void)
{
    EnactAst *ast = enact_ast_new_nil();
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

static EnactAst *enact_make_where(EnactAst *body, char *name, EnactAst *value)
{
    EnactAst *ast = enact_ast_new_where(body, name, value);
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

static EnactAst *enact_make_function_literal(EnactNameList *param_names, EnactAst *body)
{
    EnactAst *ast = enact_ast_new_function_literal(param_names, body);
    EnactParseContext *context = enact_get_parse_context();

    if (!ast && context) {
        enact_diag_set(&context->diag, ENACT_ERR_OUT_OF_MEMORY, -1);
    }

    return ast;
}

static EnactAst *enact_make_call(EnactAst *callee, EnactAstList *arguments)
{
    EnactAst *ast = enact_ast_new_call(callee, arguments);
    EnactParseContext *context = enact_get_parse_context();

    if (!ast && context) {
        enact_diag_set(&context->diag, ENACT_ERR_OUT_OF_MEMORY, -1);
    }

    return ast;
}

static EnactAstList *enact_make_argument_list(EnactAst *argument)
{
    EnactAstList *list = enact_ast_list_new();
    EnactParseContext *context = enact_get_parse_context();

    if (!list || !enact_ast_list_append(list, argument)) {
        enact_ast_list_free(list);
        enact_ast_free(argument);
        if (context) {
            enact_diag_set(&context->diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        }
        return NULL;
    }

    return list;
}

static EnactAstList *enact_append_argument(EnactAstList *list, EnactAst *argument)
{
    EnactParseContext *context = enact_get_parse_context();

    if (!enact_ast_list_append(list, argument)) {
        enact_ast_list_free(list);
        enact_ast_free(argument);
        if (context) {
            enact_diag_set(&context->diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        }
        return NULL;
    }

    return list;
}

static void enact_set_unexpected_token_diag(void)
{
    EnactParseContext *context = enact_get_parse_context();
    EnactScannerState *state = enact_get_scanner_state();

    if (context) {
        enact_diag_set(&context->diag, ENACT_ERR_PARSE_UNEXPECTED_TOKEN, state ? (int)state->token_offset : -1);
    }
}

static EnactNameList *enact_make_parameter_list(char *name)
{
    EnactNameList *list = enact_name_list_new();
    EnactParseContext *context = enact_get_parse_context();

    if (!list || !enact_name_list_append(list, name)) {
        enact_name_list_free(list);
        free(name);
        if (context) {
            enact_diag_set(&context->diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        }
        return NULL;
    }

    return list;
}

static EnactNameList *enact_append_parameter(EnactNameList *list, char *name)
{
    EnactParseContext *context = enact_get_parse_context();

    if (!list || !name) {
        enact_name_list_free(list);
        free(name);
        enact_set_unexpected_token_diag();
        return NULL;
    }

    if (enact_name_list_contains(list, name)) {
        enact_name_list_free(list);
        free(name);
        enact_set_unexpected_token_diag();
        return NULL;
    }

    if (!enact_name_list_append(list, name)) {
        enact_name_list_free(list);
        free(name);
        if (context) {
            enact_diag_set(&context->diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        }
        return NULL;
    }

    return list;
}

static char *enact_take_identifier_name(EnactAst *ast)
{
    char *name = ast->as.identifier_name;

    ast->as.identifier_name = NULL;
    return name;
}

static int enact_ast_is_bare_identifier(const EnactAst *ast)
{
    return ast && ast->kind == AST_IDENTIFIER;
}

static int enact_take_parameter_name(EnactNameList *names, EnactAst *argument)
{
    EnactParseContext *context = enact_get_parse_context();
    char *name;

    if (!names || !enact_ast_is_bare_identifier(argument)) {
        enact_set_unexpected_token_diag();
        return 0;
    }

    name = enact_take_identifier_name(argument);
    if (enact_name_list_contains(names, name)) {
        free(name);
        enact_set_unexpected_token_diag();
        return 0;
    }

    if (!enact_name_list_append(names, name)) {
        free(name);
        if (context) {
            enact_diag_set(&context->diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        }
        return 0;
    }

    return 1;
}

static int enact_take_parameter_names_from_list(EnactNameList *names, EnactAstList *arguments)
{
    size_t index;

    if (!names || !arguments || enact_ast_list_count(arguments) == 0) {
        enact_set_unexpected_token_diag();
        return 0;
    }

    for (index = 0; index < enact_ast_list_count(arguments); index += 1) {
        if (!enact_take_parameter_name(names, enact_ast_list_get(arguments, index))) {
            return 0;
        }
    }

    return 1;
}

static int enact_take_call_parameter_names_from_lhs(EnactNameList *names, EnactAst *call)
{
    if (!call || call->kind != AST_CALL) {
        enact_set_unexpected_token_diag();
        return 0;
    }

    if (call->as.call.callee && call->as.call.callee->kind == AST_CALL) {
        if (!enact_take_call_parameter_names_from_lhs(names, call->as.call.callee)) {
            return 0;
        }
    }

    return enact_take_parameter_names_from_list(names, call->as.call.arguments);
}

static EnactAst *enact_call_root(EnactAst *ast)
{
    while (ast && ast->kind == AST_CALL) {
        ast = ast->as.call.callee;
    }

    return ast;
}

static EnactNameList *enact_take_call_parameter_names(EnactAst *call)
{
    EnactNameList *names;
    EnactParseContext *context = enact_get_parse_context();

    if (!call || call->kind != AST_CALL) {
        enact_set_unexpected_token_diag();
        return NULL;
    }

    names = enact_name_list_new();
    if (!names) {
        if (context) {
            enact_diag_set(&context->diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        }
        return NULL;
    }

    if (!enact_take_call_parameter_names_from_lhs(names, call)) {
        enact_name_list_free(names);
        return NULL;
    }

    return names;
}

static EnactAst *enact_make_assignment_from_lhs(EnactAst *lhs, EnactAst *value)
{
    EnactAst *result;

    if (!lhs || !value) {
        enact_ast_free(lhs);
        enact_ast_free(value);
        enact_set_unexpected_token_diag();
        return NULL;
    }

    if (lhs->kind == AST_IDENTIFIER) {
        char *name = enact_take_identifier_name(lhs);

        enact_ast_free(lhs);
        result = enact_make_assignment(name, value);
        if (!result) {
            free(name);
            enact_ast_free(value);
            return NULL;
        }
        return result;
    }

    if (lhs->kind == AST_CALL) {
        EnactAst *root = enact_call_root(lhs);
        EnactNameList *param_names;
        char *name;
        EnactAst *function;

        if (!root || root->kind != AST_IDENTIFIER) {
            enact_ast_free(lhs);
            enact_ast_free(value);
            enact_set_unexpected_token_diag();
            return NULL;
        }

        param_names = enact_take_call_parameter_names(lhs);
        if (!param_names) {
            enact_ast_free(lhs);
            enact_ast_free(value);
            return NULL;
        }

        name = enact_take_identifier_name(root);
        enact_ast_free(lhs);

        function = enact_make_function_literal(param_names, value);
        if (!function) {
            free(name);
            enact_name_list_free(param_names);
            enact_ast_free(value);
            return NULL;
        }

        result = enact_make_assignment(name, function);
        if (!result) {
            free(name);
            enact_ast_free(function);
            return NULL;
        }
        return result;
    }

    enact_ast_free(lhs);
    enact_ast_free(value);
    enact_set_unexpected_token_diag();
    return NULL;
}
%}

%define parse.error verbose

%union {
    uint64_t u64;
    char *text;
    EnactAst *ast;
    EnactAstList *ast_list;
    EnactNameList *name_list;
}

%token <u64> TOK_INT_LITERAL
%token <text> TOK_IDENTIFIER TOK_STRING_LITERAL
%token TOK_UMINUS TOK_PLUS TOK_MINUS TOK_STAR TOK_SLASH TOK_LPAREN TOK_RPAREN TOK_DOT TOK_ERROR
%token TOK_EQEQ TOK_TRUE TOK_FALSE TOK_NIL TOK_NOT TOK_AND TOK_OR TOK_IF TOK_ELSE
%token TOK_NEQ TOK_LT TOK_GT TOK_LTE TOK_GTE
%token TOK_ASSIGN TOK_LAMBDA TOK_SEMI TOK_COMMA TOK_CONS TOK_MOD TOK_WHERE

%type <ast> expr sequence assignment lambda conditional logical_or logical_and where_expr logical_not comparison cons additive multiplicative unary call application_argument primary
%type <ast_list> argument_list
%type <name_list> lambda_head parameter_list

%destructor { enact_ast_free($$); } <ast>
%destructor { enact_ast_list_free($$); } <ast_list>
%destructor { enact_name_list_free($$); } <name_list>
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
    call TOK_ASSIGN assignment
    {
        $$ = enact_make_assignment_from_lhs($1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | lambda
    {
        $$ = $1;
    }
    ;

lambda:
    lambda_head TOK_LAMBDA assignment
    {
        $$ = enact_make_function_literal($1, $3);
        if (!$$) {
            enact_name_list_free($1);
            enact_ast_free($3);
            YYABORT;
        }
    }
    | conditional
    {
        $$ = $1;
    }
    ;

lambda_head:
    TOK_IDENTIFIER
    {
        $$ = enact_make_parameter_list($1);
        if (!$$) {
            YYABORT;
        }
    }
    | TOK_LPAREN parameter_list TOK_RPAREN
    {
        $$ = $2;
    }
    ;

parameter_list:
    TOK_IDENTIFIER TOK_COMMA TOK_IDENTIFIER
    {
        EnactNameList *list = enact_make_parameter_list($1);

        if (!list) {
            free($3);
            YYABORT;
        }

        $$ = enact_append_parameter(list, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | parameter_list TOK_COMMA TOK_IDENTIFIER
    {
        $$ = enact_append_parameter($1, $3);
        if (!$$) {
            YYABORT;
        }
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
    logical_and TOK_AND where_expr
    {
        $$ = enact_make_binary(AST_AND, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | where_expr
    {
        $$ = $1;
    }
    ;

where_expr:
    logical_not
    {
        $$ = $1;
    }
    | logical_not TOK_WHERE TOK_IDENTIFIER TOK_ASSIGN logical_not
    {
        $$ = enact_make_where($1, $3, $5);
        if (!$$) {
            enact_ast_free($1);
            free($3);
            enact_ast_free($5);
            YYABORT;
        }
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
    cons
    {
        $$ = $1;
    }
    | cons TOK_EQEQ cons
    {
        $$ = enact_make_binary(AST_EQ, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | cons TOK_NEQ cons
    {
        $$ = enact_make_binary(AST_NEQ, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | cons TOK_LT cons
    {
        $$ = enact_make_binary(AST_LT, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | cons TOK_GT cons
    {
        $$ = enact_make_binary(AST_GT, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | cons TOK_LTE cons
    {
        $$ = enact_make_binary(AST_LTE, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | cons TOK_GTE cons
    {
        $$ = enact_make_binary(AST_GTE, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    ;

cons:
    additive TOK_CONS cons
    {
        $$ = enact_make_binary(AST_CONS, $1, $3);
        if (!$$) {
            YYABORT;
        }
    }
    | additive
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
    | call
    {
        $$ = $1;
    }
    ;

call:
    call TOK_LPAREN argument_list TOK_RPAREN
    {
        $$ = enact_make_call($1, $3);
        if (!$$) {
            enact_ast_free($1);
            enact_ast_list_free($3);
            YYABORT;
        }
    }
    | call application_argument
    {
        EnactAstList *arguments = enact_make_argument_list($2);

        if (!arguments) {
            enact_ast_free($1);
            YYABORT;
        }

        $$ = enact_make_call($1, arguments);
        if (!$$) {
            enact_ast_free($1);
            enact_ast_list_free(arguments);
            YYABORT;
        }
    }
    | primary
    {
        $$ = $1;
    }
    ;

application_argument:
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
    | TOK_NIL
    {
        $$ = enact_make_nil();
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
    ;

argument_list:
    assignment
    {
        $$ = enact_make_argument_list($1);
        if (!$$) {
            YYABORT;
        }
    }
    | argument_list TOK_COMMA assignment
    {
        $$ = enact_append_argument($1, $3);
        if (!$$) {
            YYABORT;
        }
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
    | TOK_NIL
    {
        $$ = enact_make_nil();
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
        $$ = enact_make_unary(AST_GROUP, $2);
        if (!$$) {
            YYABORT;
        }
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
