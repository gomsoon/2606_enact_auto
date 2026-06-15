#include <stdlib.h>
#include <string.h>

#include "env.h"

struct EnactEnvEntry {
    char *name;
    EnactValue value;
    EnactEnvEntry *next;
};

static char *enact_env_copy_name(const char *name)
{
    size_t length;
    char *copy;

    if (!name) {
        name = "";
    }

    length = strlen(name);
    copy = malloc(length + 1);
    if (!copy) {
        return NULL;
    }

    memcpy(copy, name, length + 1);
    return copy;
}

void enact_env_init(EnactEnv *env)
{
    if (!env) {
        return;
    }

    env->head = NULL;
}

void enact_env_free(EnactEnv *env)
{
    EnactEnvEntry *entry;

    if (!env) {
        return;
    }

    entry = env->head;
    while (entry) {
        EnactEnvEntry *next = entry->next;

        free(entry->name);
        enact_value_free(&entry->value);
        free(entry);
        entry = next;
    }

    env->head = NULL;
}

int enact_env_define(EnactEnv *env, const char *name, EnactValue value)
{
    EnactEnvEntry *entry;
    char *name_copy;
    EnactValue value_copy;

    if (!env || !name) {
        return 0;
    }

    if (!enact_value_copy(&value_copy, &value)) {
        return 0;
    }

    for (entry = env->head; entry; entry = entry->next) {
        if (strcmp(entry->name, name) == 0) {
            enact_value_free(&entry->value);
            entry->value = value_copy;
            return 1;
        }
    }

    name_copy = enact_env_copy_name(name);
    if (!name_copy) {
        enact_value_free(&value_copy);
        return 0;
    }

    entry = malloc(sizeof(*entry));
    if (!entry) {
        free(name_copy);
        enact_value_free(&value_copy);
        return 0;
    }

    entry->name = name_copy;
    entry->value = value_copy;
    entry->next = env->head;
    env->head = entry;
    return 1;
}

int enact_env_lookup(const EnactEnv *env, const char *name, EnactValue *out)
{
    const EnactEnvEntry *entry;

    if (!env || !name || !out) {
        return 0;
    }

    for (entry = env->head; entry; entry = entry->next) {
        if (strcmp(entry->name, name) == 0) {
            return enact_value_copy(out, &entry->value);
        }
    }

    return 0;
}
