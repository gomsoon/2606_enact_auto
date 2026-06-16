#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "diag.h"
#include "parser_state.h"
#include "scan.h"

#include "enact.tab.h"

typedef struct yy_buffer_state *YY_BUFFER_STATE;

extern YY_BUFFER_STATE yy_scan_string(const char *yy_str);
extern void yy_delete_buffer(YY_BUFFER_STATE buffer);
extern int yylex(void);
extern int yylex_destroy(void);

static const char *enact_token_name(int token)
{
    switch (token) {
    case TOK_INT_LITERAL:
        return "TOK_INT_LITERAL";
    case TOK_IDENTIFIER:
        return "TOK_IDENTIFIER";
    case TOK_STRING_LITERAL:
        return "TOK_STRING_LITERAL";
    case TOK_NIL:
        return "TOK_NIL";
    case TOK_UMINUS:
        return "TOK_UMINUS";
    case TOK_PLUS:
        return "TOK_PLUS";
    case TOK_MINUS:
        return "TOK_MINUS";
    case TOK_STAR:
        return "TOK_STAR";
    case TOK_SLASH:
        return "TOK_SLASH";
    case TOK_MOD:
        return "TOK_MOD";
    case TOK_EQEQ:
        return "TOK_EQEQ";
    case TOK_NEQ:
        return "TOK_NEQ";
    case TOK_LT:
        return "TOK_LT";
    case TOK_GT:
        return "TOK_GT";
    case TOK_LTE:
        return "TOK_LTE";
    case TOK_GTE:
        return "TOK_GTE";
    case TOK_ASSIGN:
        return "TOK_ASSIGN";
    case TOK_LAMBDA:
        return "TOK_LAMBDA";
    case TOK_SEMI:
        return "TOK_SEMI";
    case TOK_COMMA:
        return "TOK_COMMA";
    case TOK_CONS:
        return "TOK_CONS";
    case TOK_TRUE:
        return "TOK_TRUE";
    case TOK_FALSE:
        return "TOK_FALSE";
    case TOK_NOT:
        return "TOK_NOT";
    case TOK_AND:
        return "TOK_AND";
    case TOK_OR:
        return "TOK_OR";
    case TOK_IF:
        return "TOK_IF";
    case TOK_THEN:
        return "TOK_THEN";
    case TOK_ELSE:
        return "TOK_ELSE";
    case TOK_WHERE:
        return "TOK_WHERE";
    case TOK_FIX:
        return "TOK_FIX";
    case TOK_LPAREN:
        return "TOK_LPAREN";
    case TOK_RPAREN:
        return "TOK_RPAREN";
    case TOK_DOT:
        return "TOK_DOT";
    case TOK_ERROR:
        return "TOK_ERROR";
    case 0:
        return "TOK_EOF";
    default:
        return "TOK_UNKNOWN";
    }
}

int enact_dump_tokens_text(const char *source, FILE *out, EnactDiag *diag)
{
    EnactParseContext context;
    EnactScannerState state;
    YY_BUFFER_STATE buffer;
    int token;
    bool first = true;

    if (!source) {
        source = "";
    }
    if (!out) {
        out = stdout;
    }

    context.root = NULL;
    context.source = source;
    context.source_len = strlen(source);
    enact_diag_reset(&context.diag);

    state.expect_operand = true;
    state.paren_balance = 0;
    state.offset = 0;
    state.token_offset = 0;
    state.last_token = 0;
    state.saw_dot = false;

    enact_set_parse_context(&context);
    enact_set_scanner_state(&state);

    buffer = yy_scan_string(source);
    if (!buffer) {
        enact_diag_set(&context.diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        enact_set_parse_context(NULL);
        enact_set_scanner_state(NULL);
        if (diag) {
            *diag = context.diag;
        }
        return 1;
    }

    do {
        token = yylex();
        if (context.diag.code != ENACT_OK) {
            yy_delete_buffer(buffer);
            yylex_destroy();
            enact_set_parse_context(NULL);
            enact_set_scanner_state(NULL);
            if (diag) {
                *diag = context.diag;
            }
            return 1;
        }

        fprintf(out, "%s%s", first ? "" : " ", enact_token_name(token));
        if (token == TOK_IDENTIFIER || token == TOK_STRING_LITERAL) {
            free(yylval.text);
        }
        first = false;
    } while (token != 0);

    fputc('\n', out);

    yy_delete_buffer(buffer);
    yylex_destroy();
    enact_set_parse_context(NULL);
    enact_set_scanner_state(NULL);

    if (diag) {
        *diag = context.diag;
    }
    return 0;
}
