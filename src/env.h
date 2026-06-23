#ifndef ENACT_ENV_H
#define ENACT_ENV_H

#include "diag.h"
#include "value.h"

typedef struct EnactEnvEntry EnactEnvEntry;
typedef int (*EnactInputProvider)(void *user_data, char **out_line, EnactDiag *diag);

typedef struct {
    EnactEnvEntry *head;
    EnactInputProvider input_provider;
    void *input_user_data;
} EnactEnv;

void enact_env_init(EnactEnv *env);
void enact_env_free(EnactEnv *env);
int enact_env_clone(EnactEnv *out, const EnactEnv *in);
int enact_env_define(EnactEnv *env, const char *name, EnactValue value);
int enact_env_lookup(const EnactEnv *env, const char *name, EnactValue *out);
void enact_env_set_input_provider(EnactEnv *env, EnactInputProvider provider, void *user_data);
int enact_env_read_input(EnactEnv *env, char **out_line, EnactDiag *diag);

#endif
