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
