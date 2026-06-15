#ifndef ENACT_DIAG_H
#define ENACT_DIAG_H

typedef enum {
    ENACT_OK = 0,
    ENACT_ERR_LEX_INVALID_CHAR,
    ENACT_ERR_LEX_BAD_INTEGER,
    ENACT_ERR_LEX_BAD_STRING,
    ENACT_ERR_LEX_BARE_EQUALS,
    ENACT_ERR_PARSE_UNEXPECTED_TOKEN,
    ENACT_ERR_PARSE_MISSING_DOT,
    ENACT_ERR_PARSE_UNMATCHED_PAREN,
    ENACT_ERR_DIVIDE_BY_ZERO,
    ENACT_ERR_INT_OVERFLOW,
    ENACT_ERR_TYPE_EXPECTED_BOOL,
    ENACT_ERR_TYPE_EXPECTED_INT,
    ENACT_ERR_TYPE_EXPECTED_FUNCTION,
    ENACT_ERR_TYPE_EXPECTED_LIST,
    ENACT_ERR_TYPE_EQUALITY_MISMATCH,
    ENACT_ERR_LIST_EMPTY,
    ENACT_ERR_ARITY_MISMATCH,
    ENACT_ERR_NAME_UNBOUND,
    ENACT_ERR_OUT_OF_MEMORY
} EnactErrorCode;

typedef struct {
    EnactErrorCode code;
    int offset;
    const char *message;
} EnactDiag;

void enact_diag_reset(EnactDiag *diag);
void enact_diag_set(EnactDiag *diag, EnactErrorCode code, int offset);
const char *enact_error_code_name(EnactErrorCode code);
const char *enact_error_message(EnactErrorCode code);

#endif
