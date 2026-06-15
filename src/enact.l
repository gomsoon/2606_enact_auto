%option noyywrap nounput noinput nodefault never-interactive

%{
#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "diag.h"
#include "parser_state.h"
#include "enact.tab.h"

#define YY_USER_ACTION                                                         \
    do {                                                                       \
        EnactScannerState *state__ = enact_get_scanner_state();                \
        if (state__) {                                                         \
            state__->token_offset = state__->offset;                           \
            state__->offset += (size_t)yyleng;                                 \
        }                                                                      \
    } while (0);

static int enact_emit_simple_token(int token, int expect_operand_after)
{
    EnactScannerState *state = enact_get_scanner_state();

    if (state) {
        state->last_token = token;
        state->expect_operand = expect_operand_after != 0;
        if (token == TOK_DOT) {
            state->saw_dot = true;
        }
    }

    return token;
}

static int enact_current_offset_or_unknown(const EnactScannerState *state)
{
    return state ? (int)state->token_offset : -1;
}

static char *enact_copy_yytext(void)
{
    size_t length = (size_t)yyleng;
    char *copy = malloc(length + 1);

    if (!copy) {
        return NULL;
    }

    memcpy(copy, yytext, length);
    copy[length] = '\0';
    return copy;
}

static char *enact_decode_string_literal(int *bad_escape)
{
    size_t length = (size_t)yyleng;
    char *copy;
    size_t read_index;
    size_t write_index = 0;

    if (bad_escape) {
        *bad_escape = 0;
    }

    copy = malloc(length);
    if (!copy) {
        return NULL;
    }

    for (read_index = 1; read_index + 1 < length; read_index += 1) {
        char ch = yytext[read_index];

        if (ch != '\\') {
            copy[write_index++] = ch;
            continue;
        }

        read_index += 1;
        if (read_index + 1 >= length) {
            if (bad_escape) {
                *bad_escape = 1;
            }
            free(copy);
            return NULL;
        }

        switch (yytext[read_index]) {
        case '\\':
            copy[write_index++] = '\\';
            break;
        case '"':
            copy[write_index++] = '"';
            break;
        case 'n':
            copy[write_index++] = '\n';
            break;
        case 'r':
            copy[write_index++] = '\r';
            break;
        case 't':
            copy[write_index++] = '\t';
            break;
        default:
            if (bad_escape) {
                *bad_escape = 1;
            }
            free(copy);
            return NULL;
        }
    }

    copy[write_index] = '\0';
    return copy;
}
%}

DIGITS [0-9]+
IDENT_START [A-Za-z_]
IDENT_CONT [A-Za-z0-9_]
IDENTIFIER {IDENT_START}{IDENT_CONT}*
STRING_CHAR ([^"\\\r\n]|\\.)

%%
[ \t\r\n]+                ;
%[^\n]*                   ;

"true" { return enact_emit_simple_token(TOK_TRUE, 0); }
"false" { return enact_emit_simple_token(TOK_FALSE, 0); }
"not" { return enact_emit_simple_token(TOK_NOT, 1); }
"and" { return enact_emit_simple_token(TOK_AND, 1); }
"or" { return enact_emit_simple_token(TOK_OR, 1); }
"if" { return enact_emit_simple_token(TOK_IF, 1); }
"else" { return enact_emit_simple_token(TOK_ELSE, 1); }
"mod" { return enact_emit_simple_token(TOK_MOD, 1); }
"==" { return enact_emit_simple_token(TOK_EQEQ, 1); }
":=" { return enact_emit_simple_token(TOK_ASSIGN, 1); }
"!=" { return enact_emit_simple_token(TOK_NEQ, 1); }
";" { return enact_emit_simple_token(TOK_SEMI, 1); }
"<=" { return enact_emit_simple_token(TOK_LTE, 1); }
">=" { return enact_emit_simple_token(TOK_GTE, 1); }
"<" { return enact_emit_simple_token(TOK_LT, 1); }
">" { return enact_emit_simple_token(TOK_GT, 1); }
"=" {
    EnactParseContext *context = enact_get_parse_context();
    EnactScannerState *state = enact_get_scanner_state();

    if (context) {
        enact_diag_set(&context->diag, ENACT_ERR_LEX_BARE_EQUALS, enact_current_offset_or_unknown(state));
    }
    return TOK_ERROR;
}

{DIGITS} {
    EnactScannerState *state = enact_get_scanner_state();
    EnactParseContext *context = enact_get_parse_context();
    unsigned long long value;

    errno = 0;
    value = strtoull(yytext, NULL, 10);
    if (errno == ERANGE) {
        if (context) {
            enact_diag_set(&context->diag, ENACT_ERR_LEX_BAD_INTEGER, enact_current_offset_or_unknown(state));
        }
        return TOK_ERROR;
    }

    yylval.u64 = (uint64_t)value;
    if (state) {
        state->last_token = TOK_INT_LITERAL;
        state->expect_operand = 0;
    }
    return TOK_INT_LITERAL;
}

\"{STRING_CHAR}*\" {
    EnactScannerState *state = enact_get_scanner_state();
    EnactParseContext *context = enact_get_parse_context();
    int bad_escape = 0;

    yylval.text = enact_decode_string_literal(&bad_escape);
    if (!yylval.text) {
        if (context) {
            enact_diag_set(
                &context->diag,
                bad_escape ? ENACT_ERR_LEX_BAD_STRING : ENACT_ERR_OUT_OF_MEMORY,
                enact_current_offset_or_unknown(state));
        }
        return TOK_ERROR;
    }

    if (state) {
        state->last_token = TOK_STRING_LITERAL;
        state->expect_operand = 0;
    }
    return TOK_STRING_LITERAL;
}

\"{STRING_CHAR}* {
    EnactParseContext *context = enact_get_parse_context();
    EnactScannerState *state = enact_get_scanner_state();

    if (context) {
        enact_diag_set(&context->diag, ENACT_ERR_LEX_BAD_STRING, enact_current_offset_or_unknown(state));
    }
    return TOK_ERROR;
}

{IDENTIFIER} {
    EnactScannerState *state = enact_get_scanner_state();
    EnactParseContext *context = enact_get_parse_context();

    yylval.text = enact_copy_yytext();
    if (!yylval.text) {
        if (context) {
            enact_diag_set(&context->diag, ENACT_ERR_OUT_OF_MEMORY, enact_current_offset_or_unknown(state));
        }
        return TOK_ERROR;
    }

    if (state) {
        state->last_token = TOK_IDENTIFIER;
        state->expect_operand = 0;
    }
    return TOK_IDENTIFIER;
}

"(" {
    EnactScannerState *state = enact_get_scanner_state();
    if (state) {
        state->paren_balance += 1;
    }
    return enact_emit_simple_token(TOK_LPAREN, 1);
}

")" {
    EnactScannerState *state = enact_get_scanner_state();
    if (state) {
        state->paren_balance -= 1;
    }
    return enact_emit_simple_token(TOK_RPAREN, 0);
}

"+" { return enact_emit_simple_token(TOK_PLUS, 1); }
"*" { return enact_emit_simple_token(TOK_STAR, 1); }
"/" { return enact_emit_simple_token(TOK_SLASH, 1); }
"." { return enact_emit_simple_token(TOK_DOT, 1); }

"-" {
    EnactScannerState *state = enact_get_scanner_state();
    if (state && state->expect_operand) {
        return enact_emit_simple_token(TOK_UMINUS, 1);
    }
    return enact_emit_simple_token(TOK_MINUS, 1);
}

. {
    EnactParseContext *context = enact_get_parse_context();
    EnactScannerState *state = enact_get_scanner_state();

    if (context) {
        enact_diag_set(&context->diag, ENACT_ERR_LEX_INVALID_CHAR, enact_current_offset_or_unknown(state));
    }
    return TOK_ERROR;
}

<<EOF>> {
    EnactScannerState *state = enact_get_scanner_state();
    if (state) {
        state->last_token = 0;
    }
    return 0;
}

%%
