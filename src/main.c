#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "api.h"

static char *enact_read_all(FILE *stream)
{
    size_t capacity = 1024;
    size_t length = 0;
    char *buffer = malloc(capacity);

    if (!buffer) {
        return NULL;
    }

    while (!feof(stream)) {
        size_t remaining = capacity - length;
        size_t read_count;

        if (remaining < 512) {
            char *grown;
            capacity *= 2;
            grown = realloc(buffer, capacity);
            if (!grown) {
                free(buffer);
                return NULL;
            }
            buffer = grown;
            remaining = capacity - length;
        }

        read_count = fread(buffer + length, 1, remaining - 1, stream);
        length += read_count;

        if (ferror(stream)) {
            free(buffer);
            return NULL;
        }
    }

    buffer[length] = '\0';
    return buffer;
}

static char *enact_read_line(FILE *stream)
{
    size_t capacity = 128;
    size_t length = 0;
    char *buffer = malloc(capacity);
    int ch;

    if (!buffer) {
        return NULL;
    }

    while ((ch = fgetc(stream)) != EOF) {
        char *grown;

        if (length + 1 >= capacity) {
            capacity *= 2;
            grown = realloc(buffer, capacity);
            if (!grown) {
                free(buffer);
                return NULL;
            }
            buffer = grown;
        }

        buffer[length++] = (char)ch;
        if (ch == '\n') {
            break;
        }
    }

    if (length == 0) {
        free(buffer);
        return NULL;
    }

    buffer[length] = '\0';
    return buffer;
}

static void enact_print_diag(FILE *stream, const EnactDiag *diag)
{
    if (!diag) {
        return;
    }

    if (diag->offset >= 0) {
        fprintf(
            stream,
            "%s: %s at offset %d\n",
            enact_error_code_name(diag->code),
            diag->message,
            diag->offset
        );
    } else {
        fprintf(stream, "%s: %s\n", enact_error_code_name(diag->code), diag->message);
    }
}

static void enact_print_value(FILE *stream, const EnactValue *value)
{
    switch (value->kind) {
    case ENACT_VALUE_INT:
        fprintf(stream, "%d\n", value->as.as_int);
        break;
    case ENACT_VALUE_BOOL:
        fprintf(stream, "%s\n", value->as.as_bool ? "true" : "false");
        break;
    }
}

static int enact_run_source(const char *source, int token_mode)
{
    if (token_mode) {
        EnactDiag diag;
        int status;

        enact_diag_reset(&diag);
        status = enact_dump_tokens_text(source, stdout, &diag);
        if (status != 0) {
            enact_print_diag(stderr, &diag);
            return 1;
        }
        return 0;
    }

    {
        EnactResult result = enact_eval_text(source);

        if (!result.ok) {
            enact_print_diag(stderr, &result.error);
            enact_result_free(&result);
            return 1;
        }

        enact_print_value(stdout, &result.value);
        enact_result_free(&result);
        return 0;
    }
}

static int enact_run_lines(int token_mode)
{
    int exit_status = 0;

    for (;;) {
        char *source = enact_read_line(stdin);
        int status;

        if (!source) {
            if (ferror(stdin)) {
                fputs("failed to read input\n", stderr);
                return 2;
            }
            return exit_status;
        }

        status = enact_run_source(source, token_mode);
        free(source);
        if (status != 0) {
            exit_status = status;
        }
    }
}

int main(int argc, char **argv)
{
    int token_mode = argc > 1 && strcmp(argv[1], "--tokens") == 0;
    char *source;
    int status;

    if (isatty(STDIN_FILENO)) {
        return enact_run_lines(token_mode);
    }

    source = enact_read_all(stdin);
    if (!source) {
        fputs("failed to read input\n", stderr);
        return 2;
    }

    status = enact_run_source(source, token_mode);
    free(source);
    return status;
}
