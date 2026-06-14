#include <stdio.h>
#include <stdlib.h>
#include <string.h>

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

int main(int argc, char **argv)
{
    char *source = enact_read_all(stdin);

    if (!source) {
        fputs("failed to read input\n", stderr);
        return 2;
    }

    if (argc > 1 && strcmp(argv[1], "--tokens") == 0) {
        EnactDiag diag;
        int status;

        enact_diag_reset(&diag);
        status = enact_dump_tokens_text(source, stdout, &diag);
        free(source);
        if (status != 0) {
            enact_print_diag(stderr, &diag);
            return 1;
        }
        return 0;
    }

    {
        EnactResult result = enact_eval_text(source);

        free(source);
        if (!result.ok) {
            enact_print_diag(stderr, &result.error);
            enact_result_free(&result);
            return 1;
        }

        printf("%d\n", result.value.as_int);
        enact_result_free(&result);
        return 0;
    }
}
