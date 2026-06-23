#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "api.h"
#include "object.h"

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

static void enact_print_value_inner(FILE *stream, const EnactValue *value);

static void enact_print_string_inner(FILE *stream, const char *value)
{
    const unsigned char *cursor = (const unsigned char *)(value ? value : "");

    fputc('"', stream);
    while (*cursor) {
        switch (*cursor) {
        case '\\':
            fputs("\\\\", stream);
            break;
        case '"':
            fputs("\\\"", stream);
            break;
        case '\n':
            fputs("\\n", stream);
            break;
        case '\r':
            fputs("\\r", stream);
            break;
        case '\t':
            fputs("\\t", stream);
            break;
        default:
            fputc(*cursor, stream);
            break;
        }
        cursor += 1;
    }
    fputc('"', stream);
}

static void enact_print_atom_inner(FILE *stream, const char *value)
{
    fputc('\'', stream);
    fputs(value ? value : "", stream);
}

static void enact_print_list_inner(FILE *stream, EnactList *list)
{
    const EnactValue *head;

    if (!list) {
        fputs("nil", stream);
        return;
    }

    head = enact_list_head(list);
    if (head && head->kind == ENACT_VALUE_LIST) {
        fputc('(', stream);
        enact_print_value_inner(stream, head);
        fputc(')', stream);
    } else if (head) {
        enact_print_value_inner(stream, head);
    }

    fputc(':', stream);
    enact_print_list_inner(stream, enact_list_tail(list));
}

static void enact_print_collection_inner(FILE *stream, const EnactObject *object)
{
    EnactCollectionKind kind = enact_object_collection_kind(object);
    EnactList *items = enact_object_collection_items(object);

    fputs(kind == ENACT_COLLECTION_SET ? "set(" : "bag(", stream);
    if (items) {
        enact_print_list_inner(stream, items);
    }
    fputc(')', stream);
}

static void enact_print_value_inner(FILE *stream, const EnactValue *value)
{
    switch (value->kind) {
    case ENACT_VALUE_INT:
        fprintf(stream, "%d", value->as.as_int);
        break;
    case ENACT_VALUE_BOOL:
        fprintf(stream, "%s", value->as.as_bool ? "true" : "false");
        break;
    case ENACT_VALUE_STRING:
        enact_print_string_inner(stream, value->as.as_string);
        break;
    case ENACT_VALUE_ATOM:
        enact_print_atom_inner(stream, value->as.as_atom);
        break;
    case ENACT_VALUE_CLASS:
        fprintf(stream, "<class %s>", enact_class_name(value->as.as_class));
        break;
    case ENACT_VALUE_OBJECT:
        if (enact_object_collection_kind(value->as.as_object) != ENACT_COLLECTION_NONE) {
            enact_print_collection_inner(stream, value->as.as_object);
        } else {
            fprintf(stream, "<object %s>", enact_class_name(enact_object_class(value->as.as_object)));
        }
        break;
    case ENACT_VALUE_FUNCTION:
        fputs("<function>", stream);
        break;
    case ENACT_VALUE_LIST:
        enact_print_list_inner(stream, value->as.as_list);
        break;
    case ENACT_VALUE_BUILTIN:
        fputs("<function>", stream);
        break;
    case ENACT_VALUE_BUILTIN_PARTIAL:
        fputs("<function>", stream);
        break;
    case ENACT_VALUE_BOUND_OBJECT_METHOD:
        fputs("<function>", stream);
        break;
    case ENACT_VALUE_BOUND_COLLECTION_METHOD:
        fputs("<function>", stream);
        break;
    }
}

static void enact_print_value(FILE *stream, const EnactValue *value)
{
    enact_print_value_inner(stream, value);
    fputc('\n', stream);
}

static int enact_print_script_result(const EnactResult *result, void *user_data)
{
    FILE *stream = user_data ? (FILE *)user_data : stdout;

    if (!result || !result->ok) {
        return 0;
    }

    enact_print_value(stream, &result->value);
    return 1;
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

static int enact_run_script(const char *source)
{
    EnactSession session;
    EnactDiag diag;
    int status;

    if (!enact_session_init(&session)) {
        fputs("failed to initialize session\n", stderr);
        return 2;
    }

    enact_diag_reset(&diag);
    status = enact_session_eval_script(&session, source, enact_print_script_result, stdout, &diag);
    enact_session_free(&session);
    if (!status) {
        enact_print_diag(stderr, &diag);
        return 1;
    }

    return 0;
}

static int enact_run_session_source(EnactSession *session, const char *source)
{
    EnactDiag diag;

    enact_diag_reset(&diag);
    if (!enact_session_eval_script(session, source, enact_print_script_result, stdout, &diag)) {
        enact_print_diag(stderr, &diag);
        return 1;
    }

    return 0;
}

static int enact_run_lines(int token_mode)
{
    int exit_status = 0;
    EnactSession session;

    if (!token_mode && !enact_session_init(&session)) {
        fputs("failed to initialize session\n", stderr);
        return 2;
    }

    for (;;) {
        char *source = enact_read_line(stdin);
        int status;

        if (!source) {
            if (ferror(stdin)) {
                if (!token_mode) {
                    enact_session_free(&session);
                }
                fputs("failed to read input\n", stderr);
                return 2;
            }
            if (!token_mode) {
                enact_session_free(&session);
            }
            return exit_status;
        }

        status = token_mode ? enact_run_source(source, token_mode) : enact_run_session_source(&session, source);
        free(source);
        if (status != 0) {
            exit_status = status;
        }
        if (!token_mode && enact_session_exit_requested(&session)) {
            enact_session_free(&session);
            return exit_status;
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

    status = token_mode ? enact_run_source(source, token_mode) : enact_run_script(source);
    free(source);
    return status;
}
