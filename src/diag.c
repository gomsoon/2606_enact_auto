#include "diag.h"

const char *enact_error_code_name(EnactErrorCode code)
{
    switch (code) {
    case ENACT_OK:
        return "ENACT_OK";
    case ENACT_ERR_LEX_INVALID_CHAR:
        return "ENACT_ERR_LEX_INVALID_CHAR";
    case ENACT_ERR_LEX_BAD_INTEGER:
        return "ENACT_ERR_LEX_BAD_INTEGER";
    case ENACT_ERR_LEX_BAD_STRING:
        return "ENACT_ERR_LEX_BAD_STRING";
    case ENACT_ERR_LEX_BARE_EQUALS:
        return "ENACT_ERR_LEX_BARE_EQUALS";
    case ENACT_ERR_PARSE_UNEXPECTED_TOKEN:
        return "ENACT_ERR_PARSE_UNEXPECTED_TOKEN";
    case ENACT_ERR_PARSE_MISSING_DOT:
        return "ENACT_ERR_PARSE_MISSING_DOT";
    case ENACT_ERR_PARSE_UNMATCHED_PAREN:
        return "ENACT_ERR_PARSE_UNMATCHED_PAREN";
    case ENACT_ERR_DIVIDE_BY_ZERO:
        return "ENACT_ERR_DIVIDE_BY_ZERO";
    case ENACT_ERR_INT_OVERFLOW:
        return "ENACT_ERR_INT_OVERFLOW";
    case ENACT_ERR_TYPE_EXPECTED_BOOL:
        return "ENACT_ERR_TYPE_EXPECTED_BOOL";
    case ENACT_ERR_TYPE_EXPECTED_INT:
        return "ENACT_ERR_TYPE_EXPECTED_INT";
    case ENACT_ERR_TYPE_EXPECTED_FUNCTION:
        return "ENACT_ERR_TYPE_EXPECTED_FUNCTION";
    case ENACT_ERR_TYPE_EXPECTED_LIST:
        return "ENACT_ERR_TYPE_EXPECTED_LIST";
    case ENACT_ERR_TYPE_EXPECTED_CLASS:
        return "ENACT_ERR_TYPE_EXPECTED_CLASS";
    case ENACT_ERR_TYPE_EXPECTED_OBJECT:
        return "ENACT_ERR_TYPE_EXPECTED_OBJECT";
    case ENACT_ERR_TYPE_EXPECTED_ATOM:
        return "ENACT_ERR_TYPE_EXPECTED_ATOM";
    case ENACT_ERR_TYPE_EQUALITY_MISMATCH:
        return "ENACT_ERR_TYPE_EQUALITY_MISMATCH";
    case ENACT_ERR_LIST_EMPTY:
        return "ENACT_ERR_LIST_EMPTY";
    case ENACT_ERR_ARITY_MISMATCH:
        return "ENACT_ERR_ARITY_MISMATCH";
    case ENACT_ERR_NAME_UNBOUND:
        return "ENACT_ERR_NAME_UNBOUND";
    case ENACT_ERR_ATTRIBUTE_UNBOUND:
        return "ENACT_ERR_ATTRIBUTE_UNBOUND";
    case ENACT_ERR_INCONSISTENT_LINEARIZATION:
        return "ENACT_ERR_INCONSISTENT_LINEARIZATION";
    case ENACT_ERR_LOAD_FILE:
        return "ENACT_ERR_LOAD_FILE";
    case ENACT_ERR_OUT_OF_MEMORY:
        return "ENACT_ERR_OUT_OF_MEMORY";
    default:
        return "ENACT_ERR_UNKNOWN";
    }
}

const char *enact_error_message(EnactErrorCode code)
{
    switch (code) {
    case ENACT_OK:
        return "ok";
    case ENACT_ERR_LEX_INVALID_CHAR:
        return "invalid character";
    case ENACT_ERR_LEX_BAD_INTEGER:
        return "invalid integer literal";
    case ENACT_ERR_LEX_BAD_STRING:
        return "invalid string literal";
    case ENACT_ERR_LEX_BARE_EQUALS:
        return "bare '=' is not supported; use '=='";
    case ENACT_ERR_PARSE_UNEXPECTED_TOKEN:
        return "unexpected token";
    case ENACT_ERR_PARSE_MISSING_DOT:
        return "missing terminating '.'";
    case ENACT_ERR_PARSE_UNMATCHED_PAREN:
        return "mismatched parentheses";
    case ENACT_ERR_DIVIDE_BY_ZERO:
        return "division by zero";
    case ENACT_ERR_INT_OVERFLOW:
        return "integer overflow";
    case ENACT_ERR_TYPE_EXPECTED_BOOL:
        return "boolean value required";
    case ENACT_ERR_TYPE_EXPECTED_INT:
        return "integer value required";
    case ENACT_ERR_TYPE_EXPECTED_FUNCTION:
        return "function value required";
    case ENACT_ERR_TYPE_EXPECTED_LIST:
        return "list value required";
    case ENACT_ERR_TYPE_EXPECTED_CLASS:
        return "class value required";
    case ENACT_ERR_TYPE_EXPECTED_OBJECT:
        return "object value required";
    case ENACT_ERR_TYPE_EXPECTED_ATOM:
        return "atom value required";
    case ENACT_ERR_TYPE_EQUALITY_MISMATCH:
        return "cannot compare values of different kinds";
    case ENACT_ERR_LIST_EMPTY:
        return "non-empty list required";
    case ENACT_ERR_ARITY_MISMATCH:
        return "function arity mismatch";
    case ENACT_ERR_NAME_UNBOUND:
        return "unbound identifier";
    case ENACT_ERR_ATTRIBUTE_UNBOUND:
        return "unbound attribute";
    case ENACT_ERR_INCONSISTENT_LINEARIZATION:
        return "inconsistent class linearization";
    case ENACT_ERR_LOAD_FILE:
        return "could not load file";
    case ENACT_ERR_OUT_OF_MEMORY:
        return "out of memory";
    default:
        return "unknown error";
    }
}

void enact_diag_reset(EnactDiag *diag)
{
    if (!diag) {
        return;
    }

    diag->code = ENACT_OK;
    diag->offset = -1;
    diag->message = enact_error_message(ENACT_OK);
}

void enact_diag_set(EnactDiag *diag, EnactErrorCode code, int offset)
{
    if (!diag || diag->code != ENACT_OK) {
        return;
    }

    diag->code = code;
    diag->offset = offset;
    diag->message = enact_error_message(code);
}
