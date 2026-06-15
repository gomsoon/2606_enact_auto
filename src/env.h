#ifndef ENACT_ENV_H
#define ENACT_ENV_H

#include "value.h"

typedef struct EnactEnvEntry EnactEnvEntry;

typedef struct {
    EnactEnvEntry *head;
} EnactEnv;

void enact_env_init(EnactEnv *env);
void enact_env_free(EnactEnv *env);
int enact_env_clone(EnactEnv *out, const EnactEnv *in);
int enact_env_define(EnactEnv *env, const char *name, EnactValue value);
int enact_env_lookup(const EnactEnv *env, const char *name, EnactValue *out);

#endif
