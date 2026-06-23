#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "api.h"
#include "ast.h"
#include "builtin.h"
#include "diag.h"
#include "env.h"
#include "eval.h"
#include "function.h"
#include "object.h"
#include "parser_state.h"
#include "runtime_stats.h"

static int failures;

static void require_true(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        failures += 1;
    }
}

typedef struct {
    size_t count;
    EnactValue values[8];
} ScriptCapture;

typedef struct {
    const char **lines;
    size_t count;
    size_t index;
} TestInput;

static void script_capture_free(ScriptCapture *capture)
{
    size_t index;

    if (!capture) {
        return;
    }

    for (index = 0; index < capture->count; index += 1) {
        enact_value_free(&capture->values[index]);
    }
    capture->count = 0;
}

static int script_capture_result(const EnactResult *result, void *user_data)
{
    ScriptCapture *capture = user_data;

    if (!result || !result->ok || !capture || capture->count >= 8) {
        return 0;
    }
    if (!enact_value_copy(&capture->values[capture->count], &result->value)) {
        return 0;
    }

    capture->count += 1;
    return 1;
}

static int script_reject_result(const EnactResult *result, void *user_data)
{
    (void)result;
    (void)user_data;

    return 0;
}

static int test_input_provider(void *user_data, char **out_line, EnactDiag *diag)
{
    TestInput *input = user_data;
    const char *line;
    size_t length;
    char *copy;

    if (!input || !out_line || input->index >= input->count) {
        enact_diag_set(diag, ENACT_ERR_INPUT_UNAVAILABLE, -1);
        return 0;
    }

    line = input->lines[input->index++];
    length = strlen(line);
    copy = malloc(length + 1);
    if (!copy) {
        enact_diag_set(diag, ENACT_ERR_OUT_OF_MEMORY, -1);
        return 0;
    }

    memcpy(copy, line, length + 1);
    *out_line = copy;
    return 1;
}

static char *copy_test_name(const char *name)
{
    size_t length = strlen(name);
    char *copy = malloc(length + 1);

    if (!copy) {
        return NULL;
    }

    memcpy(copy, name, length + 1);
    return copy;
}

static EnactNameList *make_test_name_list(const char **names, size_t count)
{
    EnactNameList *list = enact_name_list_new();
    size_t index;

    if (!list) {
        return NULL;
    }

    for (index = 0; index < count; index += 1) {
        char *copy = copy_test_name(names[index]);

        if (!copy || !enact_name_list_append(list, copy)) {
            free(copy);
            enact_name_list_free(list);
            return NULL;
        }
    }

    return list;
}

static EnactAstList *make_test_ast_list1(EnactAst *first)
{
    EnactAstList *list = enact_ast_list_new();

    if (!list || !enact_ast_list_append(list, first)) {
        enact_ast_list_free(list);
        enact_ast_free(first);
        return NULL;
    }

    return list;
}

static EnactAstList *make_test_ast_list2(EnactAst *first, EnactAst *second)
{
    EnactAstList *list = make_test_ast_list1(first);

    if (!list || !enact_ast_list_append(list, second)) {
        enact_ast_list_free(list);
        enact_ast_free(second);
        return NULL;
    }

    return list;
}

static void test_runtime_stats_helpers(void)
{
    const EnactBuiltin *reduce_builtin = enact_builtin_lookup("reduce");
    const EnactBuiltin *size_builtin = enact_builtin_lookup("size");
    const char *one_param[] = {"x"};
    EnactValue int_value = enact_value_make_int(1);
    EnactValue object_value;
    EnactValue partial_arg;
    EnactList *tail;
    EnactList *list;
    EnactEnv env;
    EnactAst *body;
    EnactNameList *params;
    EnactFunction *function;
    EnactClass *class_value;
    EnactObject *object;
    EnactBoundObjectMethod *bound_method;
    EnactBoundObjectMethod *extended_bound_method;
    EnactBoundCollectionMethod *bound_collection_method;
    EnactBuiltinPartial *partial;
    EnactBuiltinPartial *extended_partial;

    enact_runtime_stats_reset();
    require_true(enact_runtime_cells() == 0, "runtime stats reset cells");
    require_true(enact_runtime_max_cells() == 0, "runtime stats reset max cells");
    enact_runtime_cell_released();
    require_true(enact_runtime_cells() == 0, "runtime stats release at zero stays zero");
    require_true(enact_runtime_max_cells() == 0, "runtime stats release at zero keeps max zero");
    enact_runtime_cell_allocated();
    require_true(enact_runtime_cells() == 1, "runtime stats direct allocate increments cells");
    require_true(enact_runtime_max_cells() == 1, "runtime stats direct allocate updates max");
    enact_runtime_cell_released();
    require_true(enact_runtime_cells() == 0, "runtime stats direct release decrements cells");
    require_true(enact_runtime_max_cells() == 1, "runtime stats release keeps max");
    enact_runtime_cell_allocated();
    require_true(enact_runtime_max_cells() == 1, "runtime stats non-peak allocate keeps max");
    enact_runtime_cell_released();

    enact_runtime_stats_reset();
    tail = enact_list_cons(&int_value, NULL);
    require_true(tail != NULL, "runtime stats list tail created");
    require_true(enact_runtime_cells() == 1, "runtime stats list increments cells");
    require_true(enact_runtime_max_cells() == 1, "runtime stats list updates max");
    require_true(enact_list_retain(tail) == tail, "runtime stats list retain succeeds");
    require_true(enact_runtime_cells() == 1, "runtime stats list retain keeps cells");
    enact_list_release(tail);
    require_true(enact_runtime_cells() == 1, "runtime stats retained list release keeps cells");
    list = enact_list_cons(&int_value, tail);
    require_true(list != NULL, "runtime stats list head created");
    require_true(enact_runtime_cells() == 2, "runtime stats nested list increments cells");
    require_true(enact_runtime_max_cells() == 2, "runtime stats nested list updates max");
    enact_list_release(tail);
    require_true(enact_runtime_cells() == 2, "runtime stats list shared tail release keeps cells");
    enact_list_release(list);
    require_true(enact_runtime_cells() == 0, "runtime stats list release cascades cells");
    require_true(enact_runtime_max_cells() == 2, "runtime stats list max persists");

    enact_runtime_stats_reset();
    partial_arg = enact_value_make_int(7);
    partial = enact_builtin_partial_new(reduce_builtin, &partial_arg, 1);
    require_true(partial != NULL, "runtime stats builtin partial created");
    require_true(enact_runtime_cells() == 1, "runtime stats builtin partial increments cells");
    require_true(enact_builtin_partial_retain(partial) == partial, "runtime stats builtin partial retain succeeds");
    require_true(enact_runtime_cells() == 1, "runtime stats builtin partial retain keeps cells");
    enact_builtin_partial_release(partial);
    require_true(enact_runtime_cells() == 1, "runtime stats retained builtin partial release keeps cells");
    extended_partial = enact_builtin_partial_extend(partial, &partial_arg, 1);
    require_true(extended_partial != NULL, "runtime stats builtin partial extend created");
    require_true(enact_runtime_cells() == 2, "runtime stats builtin partial extend increments cells");
    enact_builtin_partial_release(extended_partial);
    require_true(enact_runtime_cells() == 1, "runtime stats builtin partial extended release decrements cells");
    enact_builtin_partial_release(partial);
    require_true(enact_runtime_cells() == 0, "runtime stats builtin partial release clears cells");
    require_true(enact_runtime_max_cells() == 2, "runtime stats builtin partial max persists");

    enact_runtime_stats_reset();
    enact_env_init(&env);
    body = enact_ast_new_int(1);
    params = make_test_name_list(one_param, 1);
    function = params && body ? enact_function_new(params, body, &env) : NULL;
    require_true(function != NULL, "runtime stats function created");
    require_true(enact_runtime_cells() == 1, "runtime stats function increments cells");
    require_true(enact_function_retain(function) == function, "runtime stats function retain succeeds");
    enact_function_release(function);
    require_true(enact_runtime_cells() == 1, "runtime stats retained function release keeps cells");
    class_value = enact_class_new("RuntimeCell");
    require_true(class_value != NULL, "runtime stats class created");
    require_true(enact_runtime_cells() == 2, "runtime stats class increments cells");
    object = enact_object_new(class_value);
    require_true(object != NULL, "runtime stats object created");
    require_true(enact_runtime_cells() == 3, "runtime stats object increments cells");
    object_value = enact_value_make_object(object);
    bound_method = enact_bound_object_method_new(function, &object_value);
    require_true(bound_method != NULL, "runtime stats bound object method created");
    require_true(enact_runtime_cells() == 4, "runtime stats bound object method increments cells");
    extended_bound_method = enact_bound_object_method_extend(bound_method, &partial_arg, 1);
    require_true(extended_bound_method != NULL, "runtime stats bound object method extend created");
    require_true(enact_runtime_cells() == 5, "runtime stats bound object method extend increments cells");
    enact_bound_object_method_release(extended_bound_method);
    require_true(enact_runtime_cells() == 4, "runtime stats extended bound object method release decrements cells");
    bound_collection_method = enact_bound_collection_method_new(size_builtin, 0, &object_value);
    require_true(bound_collection_method != NULL, "runtime stats bound collection method created");
    require_true(enact_runtime_cells() == 5, "runtime stats bound collection method increments cells");
    enact_bound_collection_method_release(bound_collection_method);
    require_true(enact_runtime_cells() == 4, "runtime stats bound collection method release decrements cells");
    enact_bound_object_method_release(bound_method);
    require_true(enact_runtime_cells() == 3, "runtime stats bound object method release decrements cells");
    enact_object_release(object);
    require_true(enact_runtime_cells() == 2, "runtime stats object release decrements cells");
    enact_class_release(class_value);
    require_true(enact_runtime_cells() == 1, "runtime stats class release decrements cells");
    enact_function_release(function);
    require_true(enact_runtime_cells() == 0, "runtime stats function release clears cells");
    require_true(enact_runtime_max_cells() == 5, "runtime stats composite max persists");
    enact_name_list_free(params);
    enact_ast_free(body);
    enact_env_free(&env);

    enact_runtime_stats_reset();
    enact_env_init(&env);
    require_true(enact_install_builtins(&env), "runtime stats builtin install succeeds");
    require_true(enact_runtime_cells() == 3, "runtime stats builtin install creates root classes");
    require_true(enact_runtime_max_cells() == 3, "runtime stats builtin install updates max");
    enact_env_free(&env);
    require_true(enact_runtime_cells() == 0, "runtime stats env free releases root classes");
    require_true(enact_runtime_max_cells() == 3, "runtime stats env free keeps max");
    enact_runtime_stats_reset();
}

static void test_diag_helpers(void)
{
    EnactDiag diag;

    enact_diag_reset(NULL);
    enact_diag_reset(&diag);
    require_true(diag.code == ENACT_OK, "diag reset sets OK");
    require_true(strcmp(enact_error_code_name(ENACT_OK), "ENACT_OK") == 0, "error code ok");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_LEX_BAD_INTEGER), "ENACT_ERR_LEX_BAD_INTEGER") == 0, "error code bad integer");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_LEX_BAD_STRING), "ENACT_ERR_LEX_BAD_STRING") == 0, "error code bad string");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_LEX_BARE_EQUALS), "ENACT_ERR_LEX_BARE_EQUALS") == 0, "error code bare equals");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_TYPE_EXPECTED_BOOL), "ENACT_ERR_TYPE_EXPECTED_BOOL") == 0, "error code expected bool");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_TYPE_EXPECTED_INT), "ENACT_ERR_TYPE_EXPECTED_INT") == 0, "error code expected int");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_TYPE_EXPECTED_FUNCTION), "ENACT_ERR_TYPE_EXPECTED_FUNCTION") == 0, "error code expected function");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_TYPE_EXPECTED_LIST), "ENACT_ERR_TYPE_EXPECTED_LIST") == 0, "error code expected list");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_TYPE_EXPECTED_CLASS), "ENACT_ERR_TYPE_EXPECTED_CLASS") == 0, "error code expected class");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_TYPE_EXPECTED_OBJECT), "ENACT_ERR_TYPE_EXPECTED_OBJECT") == 0, "error code expected object");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT), "ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT") == 0, "error code expected class or object");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_TYPE_EXPECTED_ATOM), "ENACT_ERR_TYPE_EXPECTED_ATOM") == 0, "error code expected atom");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_TYPE_EQUALITY_MISMATCH), "ENACT_ERR_TYPE_EQUALITY_MISMATCH") == 0, "error code equality mismatch");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_LIST_EMPTY), "ENACT_ERR_LIST_EMPTY") == 0, "error code list empty");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_ARITY_MISMATCH), "ENACT_ERR_ARITY_MISMATCH") == 0, "error code arity mismatch");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_NAME_UNBOUND), "ENACT_ERR_NAME_UNBOUND") == 0, "error code unbound name");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_ATTRIBUTE_UNBOUND), "ENACT_ERR_ATTRIBUTE_UNBOUND") == 0, "error code unbound attribute");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_INVALID_SUPER_CONTEXT), "ENACT_ERR_INVALID_SUPER_CONTEXT") == 0, "error code invalid super context");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_INCONSISTENT_LINEARIZATION), "ENACT_ERR_INCONSISTENT_LINEARIZATION") == 0, "error code inconsistent linearization");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_LOAD_FILE), "ENACT_ERR_LOAD_FILE") == 0, "error code load file");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_INPUT_UNAVAILABLE), "ENACT_ERR_INPUT_UNAVAILABLE") == 0, "error code input unavailable");
    require_true(strcmp(enact_error_code_name(ENACT_ERR_OUT_OF_MEMORY), "ENACT_ERR_OUT_OF_MEMORY") == 0, "error code oom");
    require_true(strcmp(enact_error_code_name((EnactErrorCode)999), "ENACT_ERR_UNKNOWN") == 0, "error code unknown");
    require_true(strcmp(enact_error_message(ENACT_OK), "ok") == 0, "error message ok");
    require_true(strcmp(enact_error_message(ENACT_ERR_LEX_BAD_INTEGER), "invalid integer literal") == 0, "error message bad integer");
    require_true(strcmp(enact_error_message(ENACT_ERR_LEX_BAD_STRING), "invalid string literal") == 0, "error message bad string");
    require_true(strcmp(enact_error_message(ENACT_ERR_LEX_BARE_EQUALS), "bare '=' is not supported; use '=='") == 0, "error message bare equals");
    require_true(strcmp(enact_error_message(ENACT_ERR_TYPE_EXPECTED_BOOL), "boolean value required") == 0, "error message expected bool");
    require_true(strcmp(enact_error_message(ENACT_ERR_TYPE_EXPECTED_INT), "integer value required") == 0, "error message expected int");
    require_true(strcmp(enact_error_message(ENACT_ERR_TYPE_EXPECTED_FUNCTION), "function value required") == 0, "error message expected function");
    require_true(strcmp(enact_error_message(ENACT_ERR_TYPE_EXPECTED_LIST), "list value required") == 0, "error message expected list");
    require_true(strcmp(enact_error_message(ENACT_ERR_TYPE_EXPECTED_CLASS), "class value required") == 0, "error message expected class");
    require_true(strcmp(enact_error_message(ENACT_ERR_TYPE_EXPECTED_OBJECT), "object value required") == 0, "error message expected object");
    require_true(strcmp(enact_error_message(ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT), "class or object value required") == 0, "error message expected class or object");
    require_true(strcmp(enact_error_message(ENACT_ERR_TYPE_EXPECTED_ATOM), "atom value required") == 0, "error message expected atom");
    require_true(strcmp(enact_error_message(ENACT_ERR_TYPE_EQUALITY_MISMATCH), "cannot compare values of different kinds") == 0, "error message equality mismatch");
    require_true(strcmp(enact_error_message(ENACT_ERR_LIST_EMPTY), "non-empty list required") == 0, "error message list empty");
    require_true(strcmp(enact_error_message(ENACT_ERR_ARITY_MISMATCH), "function arity mismatch") == 0, "error message arity mismatch");
    require_true(strcmp(enact_error_message(ENACT_ERR_NAME_UNBOUND), "unbound identifier") == 0, "error message unbound name");
    require_true(strcmp(enact_error_message(ENACT_ERR_ATTRIBUTE_UNBOUND), "unbound attribute") == 0, "error message unbound attribute");
    require_true(strcmp(enact_error_message(ENACT_ERR_INVALID_SUPER_CONTEXT), "super method access requires an active method context") == 0, "error message invalid super context");
    require_true(strcmp(enact_error_message(ENACT_ERR_INCONSISTENT_LINEARIZATION), "inconsistent class linearization") == 0, "error message inconsistent linearization");
    require_true(strcmp(enact_error_message(ENACT_ERR_LOAD_FILE), "could not load file") == 0, "error message load file");
    require_true(strcmp(enact_error_message(ENACT_ERR_INPUT_UNAVAILABLE), "input unavailable") == 0, "error message input unavailable");
    require_true(strcmp(enact_error_message(ENACT_ERR_OUT_OF_MEMORY), "out of memory") == 0, "error message oom");
    require_true(strcmp(enact_error_message((EnactErrorCode)999), "unknown error") == 0, "error message unknown");
    enact_diag_set(NULL, ENACT_ERR_INT_OVERFLOW, 1);
    enact_diag_set(&diag, ENACT_ERR_INT_OVERFLOW, 5);
    enact_diag_set(&diag, ENACT_ERR_DIVIDE_BY_ZERO, 6);
    require_true(diag.code == ENACT_ERR_INT_OVERFLOW, "diag set once");
    require_true(diag.offset == 5, "diag offset set");
}

static void test_value_helpers(void)
{
    EnactValue int_value = enact_value_make_int(-12);
    EnactValue bool_value = enact_value_make_bool(true);
    EnactValue string_value = enact_value_make_string(copy_test_name("hello"));
    EnactValue atom_value = enact_value_make_atom(copy_test_name("hello"));
    EnactValue string_copy;
    EnactValue atom_copy;
    EnactValue class_value;
    EnactValue class_copy;
    EnactValue object_value;
    EnactValue object_copy;
    EnactValue other_object_value;
    EnactValue attribute_value;
    EnactValue attribute_lookup;
    EnactValue list_head;
    EnactValue list_value;
    EnactValue list_copy;
    EnactValue left_class_value;
    EnactValue right_class_value;
    EnactList *list;
    EnactList *superclasses;
    EnactList *multi_superclass_tail;
    EnactList *multi_superclasses;
    EnactList *attribute_names;
    EnactList *method_names;
    EnactList *effective_method_names;
    EnactClass *empty_class;
    EnactClass *object_class;
    EnactClass *node_class;
    EnactClass *left_class;
    EnactClass *right_class;
    EnactClass *pair_class;
    EnactClass *method_class;
    EnactClass *method_supplier;
    EnactObject *object;
    EnactObject *other_object;
    EnactObject *method_object;
    EnactBoundObjectMethod *bound_method;
    EnactBoundObjectMethod *extended_bound_method;
    bool values_equal = false;
    EnactEnv empty_env;
    EnactAst *function_body;
    EnactFunction *function;
    EnactFunction *zero_function;
    EnactFunction *partial_function;
    EnactFunction *recursive_function;
    EnactFunction *method_lookup;
    int method_lookup_consistent = 1;
    int effective_method_names_consistent = 1;
    EnactValue function_value;
    EnactValue function_copy;
    EnactValue partial_args[2];
    EnactValue partial_lookup;
    EnactNameList *params;
    EnactNameList *two_params;
    EnactNameList *empty_params;
    EnactNameList *params_clone;
    char *bad_append_name;
    int linearization_ok = 0;
    const char *one_param[] = {"x"};
    const char *two_param_names[] = {"x", "y"};

    require_true(int_value.kind == ENACT_VALUE_INT, "int value kind");
    require_true(int_value.as.as_int == -12, "int value payload");
    require_true(bool_value.kind == ENACT_VALUE_BOOL, "bool value kind");
    require_true(bool_value.as.as_bool, "bool value payload");
    require_true(string_value.kind == ENACT_VALUE_STRING, "string value kind");
    require_true(string_value.as.as_string != NULL, "string value payload allocated");
    require_true(strcmp(string_value.as.as_string, "hello") == 0, "string value payload");
    require_true(enact_value_copy(&string_copy, &string_value), "string value copy succeeds");
    require_true(string_copy.kind == ENACT_VALUE_STRING, "string copy kind");
    require_true(strcmp(string_copy.as.as_string, "hello") == 0, "string copy payload");
    require_true(string_copy.as.as_string != string_value.as.as_string, "string copy is deep");
    enact_value_free(&string_copy);
    enact_value_free(&string_value);

    require_true(atom_value.kind == ENACT_VALUE_ATOM, "atom value kind");
    require_true(atom_value.as.as_atom != NULL, "atom value payload allocated");
    require_true(strcmp(atom_value.as.as_atom, "hello") == 0, "atom value payload");
    require_true(enact_value_copy(&atom_copy, &atom_value), "atom value copy succeeds");
    require_true(atom_copy.kind == ENACT_VALUE_ATOM, "atom copy kind");
    require_true(strcmp(atom_copy.as.as_atom, "hello") == 0, "atom copy payload");
    require_true(atom_copy.as.as_atom != atom_value.as.as_atom, "atom copy is deep");
    require_true(enact_value_equal(&atom_value, &atom_copy, &values_equal), "atom value equality succeeds");
    require_true(values_equal, "atom value equality true");
    enact_value_free(&atom_copy);
    enact_value_free(&atom_value);

    list_head = enact_value_make_int(42);
    list = enact_list_cons(&list_head, NULL);
    require_true(list != NULL, "list cons created");
    if (list) {
        require_true(enact_list_head(list) != NULL, "list head accessor");
        require_true(enact_list_head(list)->kind == ENACT_VALUE_INT, "list head kind");
        require_true(enact_list_head(list)->as.as_int == 42, "list head value");
        require_true(enact_list_tail(list) == NULL, "list tail nil");
        list_value = enact_value_make_list(list);
        require_true(enact_value_copy(&list_copy, &list_value), "list value copy succeeds");
        require_true(list_copy.kind == ENACT_VALUE_LIST, "list copy kind");
        require_true(list_copy.as.as_list == list_value.as.as_list, "list copy retains same list");
        require_true(enact_value_equal(&list_value, &list_copy, &values_equal), "list value equality succeeds");
        require_true(values_equal, "list value equality true");
        enact_value_free(&list_copy);
        enact_value_free(&list_value);
    }
    require_true(enact_list_cons(NULL, NULL) == NULL, "list cons null head fails");
    require_true(enact_list_retain(NULL) == NULL, "list retain null");
    enact_list_release(NULL);
    require_true(enact_list_head(NULL) == NULL, "list head null");
    require_true(enact_list_tail(NULL) == NULL, "list tail null");

    empty_class = enact_class_new(NULL);
    require_true(empty_class != NULL, "empty-name class created");
    if (empty_class) {
        require_true(strcmp(enact_class_name(empty_class), "") == 0, "empty-name class name");
        enact_class_release(empty_class);
    }
    require_true(enact_class_retain(NULL) == NULL, "class retain null");
    enact_class_release(NULL);
    require_true(strcmp(enact_class_name(NULL), "") == 0, "class name null");
    require_true(enact_class_superclass(NULL) == NULL, "class superclass null");
    superclasses = NULL;
    require_true(!enact_class_superclasses(NULL, &superclasses), "class superclasses null class fails");
    require_true(!enact_class_linearization_is_consistent(NULL, &linearization_ok), "class OK null class fails");
    require_true(enact_object_new(NULL) == NULL, "object new null class fails");
    require_true(enact_object_retain(NULL) == NULL, "object retain null");
    enact_object_release(NULL);
    require_true(enact_object_class(NULL) == NULL, "object class null");
    require_true(!enact_object_define_attribute(NULL, "x", enact_value_make_int(1)), "object define null object fails");
    require_true(!enact_object_lookup_attribute(NULL, "x", &attribute_lookup), "object lookup null object fails");
    attribute_names = NULL;
    require_true(!enact_object_attribute_names(NULL, &attribute_names), "object attribute names null object fails");
    method_names = NULL;
    require_true(!enact_class_method_names(NULL, &method_names), "class method names null class fails");
    effective_method_names = NULL;
    require_true(
        !enact_class_effective_method_names(NULL, &effective_method_names, &effective_method_names_consistent),
        "class effective method names null class fails");

    object_class = enact_class_new("Object");
    require_true(object_class != NULL, "root class created");
    if (object_class) {
        class_value = enact_value_make_class(object_class);
        require_true(class_value.kind == ENACT_VALUE_CLASS, "class value kind");
        require_true(strcmp(enact_class_name(class_value.as.as_class), "Object") == 0, "class value name");
        require_true(enact_class_superclass(class_value.as.as_class) == NULL, "root class has no superclass");
        require_true(!enact_class_superclasses(class_value.as.as_class, NULL), "class superclasses null out fails");
        require_true(
            !enact_class_linearization_is_consistent(class_value.as.as_class, NULL),
            "class OK null out fails");
        require_true(
            enact_class_linearization_is_consistent(class_value.as.as_class, &linearization_ok),
            "root class OK succeeds");
        require_true(linearization_ok, "root class OK true");
        superclasses = NULL;
        require_true(enact_class_superclasses(class_value.as.as_class, &superclasses), "root class superclasses succeeds");
        require_true(superclasses == NULL, "root class superclasses nil");
        require_true(enact_value_copy(&class_copy, &class_value), "class value copy succeeds");
        require_true(class_copy.kind == ENACT_VALUE_CLASS, "class copy kind");
        require_true(class_copy.as.as_class == class_value.as.as_class, "class copy retains same class");
        require_true(enact_value_equal(&class_value, &class_copy, &values_equal), "class value equality succeeds");
        require_true(values_equal, "class value equality true");

        node_class = enact_class_new_with_superclass("Node", object_class);
        require_true(node_class != NULL, "subclass created");
        if (node_class) {
            require_true(strcmp(enact_class_name(node_class), "Node") == 0, "subclass name");
            require_true(enact_class_superclass(node_class) == object_class, "subclass superclass");
            superclasses = NULL;
            require_true(enact_class_superclasses(node_class, &superclasses), "subclass superclasses succeeds");
            require_true(superclasses != NULL, "subclass superclasses non-empty");
            require_true(enact_list_head(superclasses)->kind == ENACT_VALUE_CLASS, "subclass superclass head kind");
            require_true(
                enact_list_head(superclasses)->as.as_class == object_class,
                "subclass superclass head identity");
            require_true(enact_list_tail(superclasses) == NULL, "subclass superclasses tail nil");
            enact_list_release(superclasses);
            enact_class_release(node_class);
        }

        left_class = enact_class_new_with_superclass("Left", object_class);
        right_class = enact_class_new_with_superclass("Right", object_class);
        require_true(left_class != NULL && right_class != NULL, "multiple superclass inputs created");
        if (left_class && right_class) {
            left_class_value = enact_value_make_class(left_class);
            right_class_value = enact_value_make_class(right_class);
            multi_superclass_tail = enact_list_cons(&right_class_value, NULL);
            require_true(multi_superclass_tail != NULL, "multiple superclass tail list created");
            multi_superclasses = multi_superclass_tail ? enact_list_cons(&left_class_value, multi_superclass_tail) : NULL;
            enact_list_release(multi_superclass_tail);
            require_true(multi_superclasses != NULL, "multiple superclass input list created");
            pair_class = enact_class_new_with_superclasses("Pair", multi_superclasses);
            enact_list_release(multi_superclasses);
            require_true(pair_class != NULL, "multiple superclass class created");
            if (pair_class) {
                superclasses = NULL;
                require_true(enact_class_superclasses(pair_class, &superclasses), "multiple superclasses succeeds");
                require_true(superclasses != NULL, "multiple superclasses non-empty");
                require_true(enact_list_head(superclasses)->as.as_class == left_class, "multiple superclass first identity");
                require_true(enact_list_tail(superclasses) != NULL, "multiple superclass second node");
                if (enact_list_tail(superclasses)) {
                    require_true(
                        enact_list_head(enact_list_tail(superclasses))->as.as_class == right_class,
                        "multiple superclass second identity");
                    require_true(enact_list_tail(enact_list_tail(superclasses)) == NULL, "multiple superclass tail nil");
                }
                enact_list_release(superclasses);
                enact_class_release(pair_class);
            }
        }
        enact_class_release(left_class);
        enact_class_release(right_class);

        object = enact_object_new(object_class);
        other_object = enact_object_new(object_class);
        require_true(object != NULL && other_object != NULL, "root objects created");
        if (object && other_object) {
            object_value = enact_value_make_object(object);
            other_object_value = enact_value_make_object(other_object);
            require_true(object_value.kind == ENACT_VALUE_OBJECT, "object value kind");
            require_true(
                enact_object_class(object_value.as.as_object) == object_class,
                "object value class pointer");
            require_true(
                strcmp(enact_class_name(enact_object_class(object_value.as.as_object)), "Object") == 0,
                "object value class name");
            require_true(
                !enact_object_attribute_names(object_value.as.as_object, NULL),
                "object attribute names null out fails");
            require_true(enact_value_copy(&object_copy, &object_value), "object value copy succeeds");
            require_true(object_copy.kind == ENACT_VALUE_OBJECT, "object copy kind");
            require_true(object_copy.as.as_object == object_value.as.as_object, "object copy retains same object");
            require_true(enact_value_equal(&object_value, &object_copy, &values_equal), "object value equality succeeds");
            require_true(values_equal, "object copy equality true");
            attribute_value = enact_value_make_string(copy_test_name("stored"));
            require_true(
                enact_object_define_attribute(object_value.as.as_object, "name", attribute_value),
                "object define string attribute succeeds");
            enact_value_free(&attribute_value);
            require_true(
                enact_object_lookup_attribute(object_value.as.as_object, "name", &attribute_lookup),
                "object lookup string attribute succeeds");
            require_true(attribute_lookup.kind == ENACT_VALUE_STRING, "object lookup attribute kind");
            require_true(strcmp(attribute_lookup.as.as_string, "stored") == 0, "object lookup attribute value");
            enact_value_free(&attribute_lookup);
            attribute_value = enact_value_make_int(99);
            require_true(
                enact_object_define_attribute(object_value.as.as_object, "name", attribute_value),
                "object redefine attribute succeeds");
            require_true(
                enact_object_lookup_attribute(object_value.as.as_object, "name", &attribute_lookup),
                "object lookup redefined attribute succeeds");
            require_true(attribute_lookup.kind == ENACT_VALUE_INT, "object lookup redefined attribute kind");
            require_true(attribute_lookup.as.as_int == 99, "object lookup redefined attribute value");
            enact_value_free(&attribute_lookup);
            require_true(
                !enact_object_lookup_attribute(object_value.as.as_object, "missing", &attribute_lookup),
                "object lookup missing attribute fails");
            attribute_names = NULL;
            require_true(
                enact_object_attribute_names(object_value.as.as_object, &attribute_names),
                "object attribute names succeeds");
            require_true(attribute_names != NULL, "object attribute names non-empty");
            require_true(enact_list_head(attribute_names)->kind == ENACT_VALUE_ATOM, "object attribute name kind");
            require_true(
                strcmp(enact_list_head(attribute_names)->as.as_atom, "name") == 0,
                "object attribute name value");
            require_true(enact_list_tail(attribute_names) == NULL, "object attribute names tail nil");
            enact_list_release(attribute_names);
            require_true(
                enact_value_equal(&object_value, &other_object_value, &values_equal),
                "independent object equality succeeds");
            require_true(!values_equal, "independent object equality false");
            enact_value_free(&object_copy);
            enact_value_free(&other_object_value);
            enact_value_free(&object_value);
        } else {
            enact_object_release(object);
            enact_object_release(other_object);
        }

        enact_value_free(&class_copy);
        enact_value_free(&class_value);
    }
    class_value = enact_value_make_class(NULL);
    require_true(!enact_value_copy(&class_copy, &class_value), "null class copy fails");
    object_value = enact_value_make_object(NULL);
    require_true(!enact_value_copy(&object_copy, &object_value), "null object copy fails");
    require_true(!enact_value_equal(NULL, &int_value, &values_equal), "value equality null left fails");
    require_true(!enact_value_equal(&int_value, NULL, &values_equal), "value equality null right fails");
    require_true(!enact_value_equal(&int_value, &int_value, NULL), "value equality null out fails");

    enact_env_init(&empty_env);
    function_body = enact_ast_new_int(1);
    require_true(function_body != NULL, "function body ast created");
    params = make_test_name_list(one_param, 1);
    require_true(params != NULL, "function params created");
    empty_params = enact_name_list_new();
    require_true(empty_params != NULL, "empty params created");
    require_true(enact_function_new(NULL, function_body, &empty_env) == NULL, "function new null params fails");
    zero_function = enact_function_new(empty_params, function_body, &empty_env);
    require_true(zero_function != NULL, "function new empty params succeeds");
    if (zero_function) {
        partial_args[0] = enact_value_make_int(1);
        require_true(enact_function_arity(zero_function) == 0, "zero function arity");
        require_true(strcmp(enact_function_param_name(zero_function, 0), "") == 0, "zero function param accessor");
        require_true(
            enact_function_partial(zero_function, partial_args, 0) == NULL,
            "zero function partial zero arguments fails");
        require_true(
            enact_function_partial(zero_function, partial_args, 1) == NULL,
            "zero function partial extra argument fails");
        enact_function_release(zero_function);
    }
    require_true(enact_function_new(params, NULL, &empty_env) == NULL, "function new null body fails");
    require_true(enact_function_new(params, function_body, NULL) == NULL, "function new null env fails");
    require_true(
        enact_function_new_recursive(params, function_body, &empty_env, NULL) == NULL,
        "recursive function new null name fails");
    require_true(
        enact_function_new_recursive(params, function_body, &empty_env, "") == NULL,
        "recursive function new empty name fails");
    zero_function = enact_function_new_recursive(empty_params, function_body, &empty_env, "self0");
    require_true(zero_function != NULL, "recursive function new empty params succeeds");
    if (zero_function) {
        require_true(enact_function_arity(zero_function) == 0, "zero recursive function arity");
        require_true(
            strcmp(enact_function_recursive_name(zero_function), "self0") == 0,
            "zero recursive function name accessor");
        enact_function_release(zero_function);
    }
    require_true(enact_function_partial(NULL, partial_args, 1) == NULL, "function partial null function fails");
    params_clone = enact_name_list_clone(params);
    require_true(params_clone != NULL, "name list clone succeeds");
    require_true(enact_name_list_count(params_clone) == 1, "name list clone count");
    require_true(strcmp(enact_name_list_get(params_clone, 0), "x") == 0, "name list clone value");
    require_true(strcmp(enact_name_list_get(params_clone, 99), "") == 0, "name list out of range");
    require_true(enact_name_list_contains(params_clone, "x"), "name list contains x");
    require_true(!enact_name_list_contains(params_clone, "missing"), "name list missing value");
    bad_append_name = copy_test_name("bad");
    require_true(!enact_name_list_append(NULL, bad_append_name), "name list append null list fails");
    free(bad_append_name);
    require_true(!enact_name_list_append(params_clone, NULL), "name list append null name fails");
    enact_name_list_free(params_clone);
    function = enact_function_new(params, function_body, &empty_env);
    require_true(function != NULL, "function value payload created");
    if (function) {
        require_true(enact_function_arity(function) == 1, "function arity");
        require_true(strcmp(enact_function_param_name(function, 0), "x") == 0, "function first param");
        require_true(strcmp(enact_function_param_name(function, 99), "") == 0, "function param out of range");
        partial_args[0] = enact_value_make_int(1);
        require_true(enact_function_partial(function, NULL, 1) == NULL, "function partial null arguments fails");
        require_true(enact_function_partial(function, partial_args, 0) == NULL, "function partial zero arguments fails");
        require_true(enact_function_partial(function, partial_args, 1) == NULL, "function partial exact arity fails");
        function_value = enact_value_make_function(function);
        require_true(function_value.kind == ENACT_VALUE_FUNCTION, "function value kind");
        require_true(enact_value_copy(&function_copy, &function_value), "function value copy succeeds");
        require_true(function_copy.kind == ENACT_VALUE_FUNCTION, "function copy kind");
        require_true(function_copy.as.as_function == function_value.as.as_function, "function copy retains same object");
        enact_value_free(&function_copy);
        method_class = enact_class_new("MethodNode");
        require_true(!enact_class_define_method(NULL, "id", function), "method define null class fails");
        require_true(!enact_class_define_method(method_class, NULL, function), "method define null name fails");
        require_true(!enact_class_define_method(method_class, "id", NULL), "method define null function fails");
        require_true(!enact_class_lookup_method(NULL, "id", &method_lookup, &method_lookup_consistent), "method lookup null class fails");
        require_true(!enact_class_lookup_method(method_class, NULL, &method_lookup, &method_lookup_consistent), "method lookup null name fails");
        require_true(!enact_class_lookup_method(method_class, "id", NULL, &method_lookup_consistent), "method lookup null out fails");
        require_true(!enact_class_lookup_method(method_class, "id", &method_lookup, NULL), "method lookup null consistency out fails");
        method_supplier = NULL;
        require_true(
            !enact_class_lookup_method_with_supplier(
                NULL,
                "id",
                &method_lookup,
                &method_supplier,
                &method_lookup_consistent),
            "method lookup supplier null class fails");
        require_true(
            !enact_class_lookup_method_with_supplier(
                method_class,
                NULL,
                &method_lookup,
                &method_supplier,
                &method_lookup_consistent),
            "method lookup supplier null name fails");
        require_true(
            !enact_class_lookup_method_with_supplier(
                method_class,
                "id",
                NULL,
                &method_supplier,
                &method_lookup_consistent),
            "method lookup supplier null function out fails");
        require_true(
            !enact_class_lookup_method_with_supplier(
                method_class,
                "id",
                &method_lookup,
                NULL,
                &method_lookup_consistent),
            "method lookup supplier null supplier out fails");
        require_true(
            !enact_class_lookup_method_with_supplier(
                method_class,
                "id",
                &method_lookup,
                &method_supplier,
                NULL),
            "method lookup supplier null consistency out fails");
        require_true(
            !enact_class_lookup_super_method_with_supplier(
                NULL,
                method_class,
                "id",
                &method_lookup,
                &method_supplier,
                &method_lookup_consistent),
            "super method lookup null receiver class fails");
        require_true(
            !enact_class_lookup_super_method_with_supplier(
                method_class,
                NULL,
                "id",
                &method_lookup,
                &method_supplier,
                &method_lookup_consistent),
            "super method lookup null current supplier fails");
        require_true(
            !enact_class_lookup_super_method_with_supplier(
                method_class,
                method_class,
                NULL,
                &method_lookup,
                &method_supplier,
                &method_lookup_consistent),
            "super method lookup null name fails");
        require_true(
            !enact_class_lookup_super_method_with_supplier(
                method_class,
                method_class,
                "id",
                NULL,
                &method_supplier,
                &method_lookup_consistent),
            "super method lookup null function out fails");
        require_true(
            !enact_class_lookup_super_method_with_supplier(
                method_class,
                method_class,
                "id",
                &method_lookup,
                NULL,
                &method_lookup_consistent),
            "super method lookup null supplier out fails");
        require_true(
            !enact_class_lookup_super_method_with_supplier(
                method_class,
                method_class,
                "id",
                &method_lookup,
                &method_supplier,
                NULL),
            "super method lookup null consistency out fails");
        require_true(!enact_class_method_names(method_class, NULL), "method names null out fails");
        require_true(
            !enact_class_effective_method_names(method_class, NULL, &effective_method_names_consistent),
            "effective method names null out fails");
        effective_method_names = NULL;
        require_true(
            !enact_class_effective_method_names(method_class, &effective_method_names, NULL),
            "effective method names null consistency out fails");
        if (method_class) {
            method_names = NULL;
            require_true(enact_class_method_names(method_class, &method_names), "empty method names succeeds");
            require_true(method_names == NULL, "empty method names nil");
            effective_method_names = NULL;
            effective_method_names_consistent = 0;
            require_true(
                enact_class_effective_method_names(
                    method_class,
                    &effective_method_names,
                    &effective_method_names_consistent),
                "empty effective method names succeeds");
            require_true(effective_method_names_consistent, "empty effective method names consistent");
            require_true(effective_method_names == NULL, "empty effective method names nil");
            require_true(enact_class_define_method(method_class, "id", function), "method define succeeds");
            method_lookup = NULL;
            method_supplier = NULL;
            method_lookup_consistent = 0;
            require_true(
                enact_class_lookup_super_method_with_supplier(
                    method_class,
                    method_class,
                    "id",
                    &method_lookup,
                    &method_supplier,
                    &method_lookup_consistent),
                "root super method lookup succeeds");
            require_true(method_lookup_consistent, "root super method lookup consistent");
            require_true(method_lookup == NULL, "root super method lookup finds no method");
            require_true(method_supplier == NULL, "root super method lookup finds no supplier");
            method_lookup = NULL;
            method_supplier = NULL;
            method_lookup_consistent = 0;
            require_true(
                enact_class_lookup_method_with_supplier(
                    method_class,
                    "id",
                    &method_lookup,
                    &method_supplier,
                    &method_lookup_consistent),
                "method lookup with supplier succeeds");
            require_true(method_lookup_consistent, "method lookup consistent");
            require_true(method_lookup == function, "method lookup retains same function");
            require_true(method_supplier == method_class, "method lookup supplier is direct class");
            if (method_lookup) {
                require_true(enact_function_arity(method_lookup) == 1, "method lookup function arity");
                enact_function_release(method_lookup);
            }
            method_lookup = NULL;
            method_lookup_consistent = 0;
            require_true(
                enact_class_lookup_method(method_class, "id", &method_lookup, &method_lookup_consistent),
                "method lookup wrapper still succeeds");
            require_true(method_lookup_consistent, "method lookup wrapper consistent");
            require_true(method_lookup == function, "method lookup wrapper retains same function");
            if (method_lookup) {
                enact_function_release(method_lookup);
            }
            method_names = NULL;
            require_true(enact_class_method_names(method_class, &method_names), "method names succeeds");
            require_true(method_names != NULL, "method names non-empty");
            require_true(enact_list_head(method_names)->kind == ENACT_VALUE_ATOM, "method name kind");
            require_true(strcmp(enact_list_head(method_names)->as.as_atom, "id") == 0, "method name value");
            require_true(enact_list_tail(method_names) == NULL, "method names tail nil");
            enact_list_release(method_names);
            effective_method_names = NULL;
            effective_method_names_consistent = 0;
            require_true(
                enact_class_effective_method_names(
                    method_class,
                    &effective_method_names,
                    &effective_method_names_consistent),
                "method effective names succeeds");
            require_true(effective_method_names_consistent, "method effective names consistent");
            require_true(effective_method_names != NULL, "method effective names non-empty");
            require_true(
                enact_list_head(effective_method_names)->kind == ENACT_VALUE_ATOM,
                "method effective name kind");
            require_true(
                strcmp(enact_list_head(effective_method_names)->as.as_atom, "id") == 0,
                "method effective name value");
            require_true(enact_list_tail(effective_method_names) == NULL, "method effective names tail nil");
            enact_list_release(effective_method_names);
            node_class = enact_class_new_with_superclass("MethodLeaf", method_class);
            require_true(node_class != NULL, "method subclass created");
            if (node_class) {
                method_lookup = NULL;
                method_supplier = NULL;
                method_lookup_consistent = 0;
                require_true(
                    enact_class_lookup_method_with_supplier(
                        node_class,
                        "id",
                        &method_lookup,
                        &method_supplier,
                        &method_lookup_consistent),
                    "method lookup superclass with supplier succeeds");
                require_true(method_lookup_consistent, "method lookup superclass consistent");
                require_true(method_lookup == function, "method lookup searches superclass");
                require_true(method_supplier == method_class, "method lookup inherited supplier is superclass");
                if (method_lookup) {
                    enact_function_release(method_lookup);
                }
                method_names = NULL;
                require_true(enact_class_method_names(node_class, &method_names), "subclass direct method names succeeds");
                require_true(method_names == NULL, "subclass direct method names exclude superclass");
                effective_method_names = NULL;
                effective_method_names_consistent = 0;
                require_true(
                    enact_class_effective_method_names(
                        node_class,
                        &effective_method_names,
                        &effective_method_names_consistent),
                    "subclass effective method names succeeds");
                require_true(effective_method_names_consistent, "subclass effective method names consistent");
                require_true(effective_method_names != NULL, "subclass effective method names include superclass");
                require_true(
                    strcmp(enact_list_head(effective_method_names)->as.as_atom, "id") == 0,
                    "subclass effective method name value");
                require_true(
                    enact_list_tail(effective_method_names) == NULL,
                    "subclass effective method names tail nil");
                enact_list_release(effective_method_names);
                require_true(enact_class_define_method(node_class, "id", function), "method override define succeeds");
                method_lookup = NULL;
                method_supplier = NULL;
                method_lookup_consistent = 0;
                require_true(
                    enact_class_lookup_method_with_supplier(
                        node_class,
                        "id",
                        &method_lookup,
                        &method_supplier,
                        &method_lookup_consistent),
                    "method lookup override with supplier succeeds");
                require_true(method_lookup_consistent, "method lookup override consistent");
                require_true(method_lookup == function, "method lookup override returns function");
                require_true(method_supplier == node_class, "method lookup override supplier is subclass");
                if (method_lookup) {
                    enact_function_release(method_lookup);
                }
                method_lookup = NULL;
                method_supplier = NULL;
                method_lookup_consistent = 0;
                require_true(
                    enact_class_lookup_super_method_with_supplier(
                        node_class,
                        node_class,
                        "id",
                        &method_lookup,
                        &method_supplier,
                        &method_lookup_consistent),
                    "super method lookup override succeeds");
                require_true(method_lookup_consistent, "super method lookup override consistent");
                require_true(method_lookup == function, "super method lookup override returns inherited function");
                require_true(method_supplier == method_class, "super method lookup override supplier is superclass");
                if (method_lookup) {
                    enact_function_release(method_lookup);
                }
                method_lookup = NULL;
                method_supplier = NULL;
                method_lookup_consistent = 0;
                require_true(
                    enact_class_lookup_super_method_with_supplier(
                        node_class,
                        method_class,
                        "id",
                        &method_lookup,
                        &method_supplier,
                        &method_lookup_consistent),
                    "super method lookup after superclass succeeds");
                require_true(method_lookup_consistent, "super method lookup after superclass consistent");
                require_true(method_lookup == NULL, "super method lookup after superclass finds no method");
                require_true(method_supplier == NULL, "super method lookup after superclass finds no supplier");
                method_lookup = NULL;
                method_supplier = NULL;
                method_lookup_consistent = 0;
                require_true(
                    enact_class_lookup_super_method_with_supplier(
                        method_class,
                        node_class,
                        "id",
                        &method_lookup,
                        &method_supplier,
                        &method_lookup_consistent),
                    "super method lookup unrelated supplier succeeds");
                require_true(method_lookup_consistent, "super method lookup unrelated supplier consistent");
                require_true(method_lookup == NULL, "super method lookup unrelated supplier finds no method");
                require_true(method_supplier == NULL, "super method lookup unrelated supplier finds no supplier");
                effective_method_names = NULL;
                effective_method_names_consistent = 0;
                require_true(
                    enact_class_effective_method_names(
                        node_class,
                        &effective_method_names,
                        &effective_method_names_consistent),
                    "override effective method names succeeds");
                require_true(effective_method_names_consistent, "override effective method names consistent");
                require_true(effective_method_names != NULL, "override effective method names non-empty");
                require_true(
                    strcmp(enact_list_head(effective_method_names)->as.as_atom, "id") == 0,
                    "override effective method name value");
                require_true(
                    enact_list_tail(effective_method_names) == NULL,
                    "override effective method names masks duplicate");
                enact_list_release(effective_method_names);
                method_object = enact_object_new(node_class);
                require_true(method_object != NULL, "method supplier object created");
                if (method_object) {
                    object_value = enact_value_make_object(method_object);
                    require_true(
                        enact_bound_object_method_new_with_supplier(NULL, &object_value, node_class) == NULL,
                        "bound object method with supplier null function fails");
                    require_true(
                        enact_bound_object_method_new_with_supplier(function, NULL, node_class) == NULL,
                        "bound object method with supplier null receiver fails");
                    bound_method = enact_bound_object_method_new(function, &object_value);
                    require_true(bound_method != NULL, "bound object method wrapper created");
                    if (bound_method) {
                        require_true(
                            enact_bound_object_method_supplier_class(bound_method) == NULL,
                            "bound object method wrapper has no supplier");
                        enact_bound_object_method_release(bound_method);
                    }
                    bound_method = enact_bound_object_method_new_with_supplier(function, &object_value, node_class);
                    require_true(bound_method != NULL, "bound object method with supplier created");
                    if (bound_method) {
                        require_true(
                            enact_bound_object_method_supplier_class(bound_method) == node_class,
                            "bound object method supplier retained");
                        partial_args[0] = enact_value_make_int(11);
                        extended_bound_method = enact_bound_object_method_extend(bound_method, partial_args, 1);
                        require_true(extended_bound_method != NULL, "bound object method supplier extend succeeds");
                        if (extended_bound_method) {
                            require_true(
                                enact_bound_object_method_supplier_class(extended_bound_method) == node_class,
                                "extended bound object method keeps supplier");
                            enact_bound_object_method_release(extended_bound_method);
                        }
                        enact_bound_object_method_release(bound_method);
                    }
                    enact_value_free(&object_value);
                }
                enact_class_release(node_class);
            }
            left_class = enact_class_new("SuperLeft");
            right_class = enact_class_new("SuperRight");
            require_true(left_class != NULL && right_class != NULL, "super method lookup MI classes created");
            if (left_class && right_class) {
                left_class_value = enact_value_make_class(left_class);
                right_class_value = enact_value_make_class(right_class);
                multi_superclass_tail = enact_list_cons(&right_class_value, NULL);
                require_true(multi_superclass_tail != NULL, "super method lookup MI tail created");
                multi_superclasses = multi_superclass_tail
                    ? enact_list_cons(&left_class_value, multi_superclass_tail)
                    : NULL;
                enact_list_release(multi_superclass_tail);
                require_true(multi_superclasses != NULL, "super method lookup MI list created");
                pair_class = enact_class_new_with_superclasses("SuperPair", multi_superclasses);
                enact_list_release(multi_superclasses);
                require_true(pair_class != NULL, "super method lookup MI receiver created");
                if (pair_class) {
                    require_true(
                        enact_class_define_method(left_class, "id", function),
                        "super method lookup MI left method defined");
                    require_true(
                        enact_class_define_method(right_class, "id", function),
                        "super method lookup MI right method defined");
                    method_lookup = NULL;
                    method_supplier = NULL;
                    method_lookup_consistent = 0;
                    require_true(
                        enact_class_lookup_super_method_with_supplier(
                            pair_class,
                            pair_class,
                            "id",
                            &method_lookup,
                            &method_supplier,
                            &method_lookup_consistent),
                        "super method lookup MI first supplier succeeds");
                    require_true(method_lookup_consistent, "super method lookup MI first supplier consistent");
                    require_true(method_lookup == function, "super method lookup MI first supplier function");
                    require_true(method_supplier == left_class, "super method lookup MI first supplier identity");
                    if (method_lookup) {
                        enact_function_release(method_lookup);
                    }
                    method_lookup = NULL;
                    method_supplier = NULL;
                    method_lookup_consistent = 0;
                    require_true(
                        enact_class_lookup_super_method_with_supplier(
                            pair_class,
                            left_class,
                            "id",
                            &method_lookup,
                            &method_supplier,
                            &method_lookup_consistent),
                        "super method lookup MI second supplier succeeds");
                    require_true(method_lookup_consistent, "super method lookup MI second supplier consistent");
                    require_true(method_lookup == function, "super method lookup MI second supplier function");
                    require_true(method_supplier == right_class, "super method lookup MI second supplier identity");
                    if (method_lookup) {
                        enact_function_release(method_lookup);
                    }
                    enact_class_release(pair_class);
                }
            }
            enact_class_release(left_class);
            enact_class_release(right_class);
            method_lookup = NULL;
            method_supplier = method_class;
            method_lookup_consistent = 0;
            require_true(
                enact_class_lookup_method_with_supplier(
                    method_class,
                    "missing",
                    &method_lookup,
                    &method_supplier,
                    &method_lookup_consistent),
                "method lookup missing with supplier succeeds");
            require_true(method_lookup_consistent, "method lookup missing consistent");
            require_true(method_lookup == NULL, "method lookup missing returns null");
            require_true(method_supplier == NULL, "method lookup missing supplier returns null");
            enact_class_release(method_class);
        }
        enact_value_free(&function_value);
    }
    two_params = make_test_name_list(two_param_names, 2);
    require_true(two_params != NULL, "two-parameter list created");
    function = enact_function_new(two_params, function_body, &empty_env);
    require_true(function != NULL, "two-parameter function created");
    if (function) {
        partial_args[0] = enact_value_make_int(7);
        partial_args[1] = enact_value_make_int(8);
        partial_function = enact_function_partial(function, partial_args, 1);
        require_true(partial_function != NULL, "function partial one argument succeeds");
        if (partial_function) {
            require_true(enact_function_arity(partial_function) == 1, "partial function arity");
            require_true(strcmp(enact_function_param_name(partial_function, 0), "y") == 0, "partial function remaining param");
            require_true(
                enact_env_lookup(enact_function_env(partial_function), "x", &partial_lookup),
                "partial function captures bound argument");
            require_true(partial_lookup.kind == ENACT_VALUE_INT, "partial captured argument kind");
            require_true(partial_lookup.as.as_int == 7, "partial captured argument value");
            enact_value_free(&partial_lookup);
            enact_function_release(partial_function);
        }
        require_true(
            enact_function_partial(function, partial_args, 2) == NULL,
            "function partial all arguments fails");
        enact_function_release(function);
    }
    recursive_function = enact_function_new_recursive(two_params, function_body, &empty_env, "self");
    require_true(recursive_function != NULL, "recursive function created");
    if (recursive_function) {
        require_true(
            strcmp(enact_function_recursive_name(recursive_function), "self") == 0,
            "recursive function name accessor");
        partial_args[0] = enact_value_make_int(7);
        partial_function = enact_function_partial(recursive_function, partial_args, 1);
        require_true(partial_function != NULL, "recursive function partial succeeds");
        if (partial_function) {
            require_true(enact_function_recursive_name(partial_function) == NULL, "partial recursive name cleared");
            require_true(
                enact_env_lookup(enact_function_env(partial_function), "self", &partial_lookup),
                "recursive partial captures original self");
            require_true(partial_lookup.kind == ENACT_VALUE_FUNCTION, "recursive partial self kind");
            require_true(
                partial_lookup.as.as_function == recursive_function,
                "recursive partial self points to original");
            enact_value_free(&partial_lookup);
            enact_function_release(partial_function);
        }
        require_true(
            !enact_function_define_capture(NULL, "peer", enact_value_make_int(3)),
            "function define capture null function fails");
        require_true(
            !enact_function_define_capture(recursive_function, NULL, enact_value_make_int(3)),
            "function define capture null name fails");
        require_true(
            enact_function_define_capture(recursive_function, "peer", enact_value_make_int(3)),
            "function define capture succeeds");
        require_true(
            enact_env_lookup(enact_function_env(recursive_function), "peer", &partial_lookup),
            "function define capture binding visible");
        require_true(partial_lookup.kind == ENACT_VALUE_INT, "function define capture value kind");
        require_true(partial_lookup.as.as_int == 3, "function define capture value");
        enact_value_free(&partial_lookup);
        enact_function_release(recursive_function);
    }
    require_true(enact_function_retain(NULL) == NULL, "function retain null fails");
    enact_function_release(NULL);
    require_true(enact_function_arity(NULL) == 0, "function null arity");
    require_true(strcmp(enact_function_param_name(NULL, 0), "") == 0, "function null param accessor");
    require_true(enact_function_body(NULL) == NULL, "function null body accessor");
    require_true(enact_function_env(NULL) == NULL, "function null env accessor");
    require_true(enact_function_recursive_name(NULL) == NULL, "function null recursive name accessor");
    function_value = enact_value_make_function(NULL);
    require_true(!enact_value_copy(&function_copy, &function_value), "function value copy null payload fails");
    enact_value_free(&function_value);
    enact_name_list_free(empty_params);
    enact_name_list_free(params);
    enact_name_list_free(two_params);
    enact_ast_free(function_body);
    enact_env_free(&empty_env);

    require_true(!enact_value_copy(NULL, &int_value), "value copy null out fails");
    require_true(!enact_value_copy(&string_copy, NULL), "value copy null in fails");
    enact_value_free(NULL);
}

static void test_builtin_helpers(void)
{
    const EnactBuiltin *hd = enact_builtin_lookup("hd");
    const EnactBuiltin *tl = enact_builtin_lookup("tl");
    const EnactBuiltin *atom = enact_builtin_lookup("atom");
    const EnactBuiltin *is_object = enact_builtin_lookup("isObject");
    const EnactBuiltin *is_int = enact_builtin_lookup("isInt");
    const EnactBuiltin *is_bool = enact_builtin_lookup("isBool");
    const EnactBuiltin *is_string = enact_builtin_lookup("isString");
    const EnactBuiltin *is_list = enact_builtin_lookup("isList");
    const EnactBuiltin *is_nil = enact_builtin_lookup("isNil");
    const EnactBuiltin *is_empty = enact_builtin_lookup("isEmpty");
    const EnactBuiltin *is_symbol = enact_builtin_lookup("isSymbol");
    const EnactBuiltin *is_class = enact_builtin_lookup("isClass");
    const EnactBuiltin *is_callable = enact_builtin_lookup("isCallable");
    const EnactBuiltin *is_collection = enact_builtin_lookup("isCollection");
    const EnactBuiltin *is_set = enact_builtin_lookup("isSet");
    const EnactBuiltin *is_bag = enact_builtin_lookup("isBag");
    const EnactBuiltin *classof = enact_builtin_lookup("classof");
    const EnactBuiltin *attrs = enact_builtin_lookup("attrs");
    const EnactBuiltin *has_attr = enact_builtin_lookup("hasAttr");
    const EnactBuiltin *methods = enact_builtin_lookup("methods");
    const EnactBuiltin *effective_methods = enact_builtin_lookup("effectiveMethods");
    const EnactBuiltin *classes = enact_builtin_lookup("classes");
    const EnactBuiltin *supers = enact_builtin_lookup("supers");
    const EnactBuiltin *superiors = enact_builtin_lookup("superiors");
    const EnactBuiltin *ok_builtin = enact_builtin_lookup("OK");
    const EnactBuiltin *suppliers = enact_builtin_lookup("suppliers");
    const EnactBuiltin *method_supplier = enact_builtin_lookup("methodSupplier");
    const EnactBuiltin *has_method = enact_builtin_lookup("hasMethod");
    const EnactBuiltin *method_arity = enact_builtin_lookup("methodArity");
    const EnactBuiltin *method_params = enact_builtin_lookup("methodParams");
    const EnactBuiltin *callable_arity = enact_builtin_lookup("callableArity");
    const EnactBuiltin *callable_min_arity = enact_builtin_lookup("callableMinArity");
    const EnactBuiltin *callable_params = enact_builtin_lookup("callableParams");
    const EnactBuiltin *callable_arity_range = enact_builtin_lookup("callableArityRange");
    const EnactBuiltin *version_builtin = enact_builtin_lookup("version");
    const EnactBuiltin *time_builtin = enact_builtin_lookup("time");
    const EnactBuiltin *ask_builtin = enact_builtin_lookup("ask");
    const EnactBuiltin *list_builtin = enact_builtin_lookup("list");
    const EnactBuiltin *set_builtin = enact_builtin_lookup("set");
    const EnactBuiltin *bag_builtin = enact_builtin_lookup("bag");
    const EnactBuiltin *append = enact_builtin_lookup("append");
    const EnactBuiltin *size = enact_builtin_lookup("size");
    const EnactBuiltin *map = enact_builtin_lookup("map");
    const EnactBuiltin *collect = enact_builtin_lookup("collect");
    const EnactBuiltin *filter = enact_builtin_lookup("filter");
    const EnactBuiltin *select = enact_builtin_lookup("select");
    const EnactBuiltin *all = enact_builtin_lookup("all");
    const EnactBuiltin *exists = enact_builtin_lookup("exists");
    const EnactBuiltin *locate = enact_builtin_lookup("locate");
    const EnactBuiltin *for_each_do = enact_builtin_lookup("forEachDo");
    const EnactBuiltin *reduce = enact_builtin_lookup("reduce");
    const EnactBuiltin *member = enact_builtin_lookup("member");
    const EnactBuiltin *insert = enact_builtin_lookup("insert");
    const EnactBuiltin *add = enact_builtin_lookup("add");
    const EnactBuiltin *remove = enact_builtin_lookup("remove");
    const EnactBuiltin *unitset = enact_builtin_lookup("unitset");
    const EnactBuiltin *union_builtin = enact_builtin_lookup("union");
    const EnactBuiltin *union_aggregate = enact_builtin_lookup("UNION");
    const EnactBuiltin *difference = enact_builtin_lookup("difference");
    const EnactBuiltin *intersection = enact_builtin_lookup("intersection");
    const EnactBuiltin *subset = enact_builtin_lookup("subset");
    const EnactBuiltin *equal = enact_builtin_lookup("equal");
    EnactBuiltinPartial *append_partial;
    EnactBuiltinPartial *other_append_partial;
    EnactValue builtin_value;
    EnactValue builtin_copy;
    EnactValue partial_value;
    EnactValue partial_copy;
    EnactValue other_partial_value;
    EnactValue lookup_value;
    EnactValue head;
    EnactValue args[1];
    EnactValue append_args[2];
    EnactValue supplier_args[2];
    EnactValue set_args[2];
    EnactValue map_args[2];
    EnactValue predicate_args[2];
    EnactValue reduce_args[3];
    EnactValue attribute_value;
    EnactValue inner_left_value;
    EnactValue inner_right_value;
    EnactValue inner_true_value;
    EnactValue inner_false_value;
    EnactValue bad_prefix_args[1];
    EnactValue result;
    EnactList *list;
    EnactList *left_list;
    EnactList *right_list;
    EnactList *inner_left_list;
    EnactList *inner_right_list;
    EnactList *inner_true_list;
    EnactList *inner_false_list;
    EnactList *outer_tail;
    EnactList *outer_list;
    EnactList *predicate_tail;
    EnactList *predicate_list;
    EnactList *reduce_tail;
    EnactList *reduce_list;
    EnactClass *object_class;
    EnactClass *node_class;
    EnactClass *leaf_class;
    EnactObject *object;
    EnactObject *node_object;
    EnactDiag diag;
    EnactEnv env;
    const char *ask_lines[] = {"unit input\r\n", ""};
    TestInput ask_input = {ask_lines, 2, 0};
    EnactAst *call;
    EnactAst *class_def;
    EnactAst *new_node;
    bool values_equal = false;

    require_true(hd != NULL, "hd builtin lookup succeeds");
    require_true(tl != NULL, "tl builtin lookup succeeds");
    require_true(atom != NULL, "atom builtin lookup succeeds");
    require_true(is_object != NULL, "isObject builtin lookup succeeds");
    require_true(is_int != NULL, "isInt builtin lookup succeeds");
    require_true(is_bool != NULL, "isBool builtin lookup succeeds");
    require_true(is_string != NULL, "isString builtin lookup succeeds");
    require_true(is_list != NULL, "isList builtin lookup succeeds");
    require_true(is_nil != NULL, "isNil builtin lookup succeeds");
    require_true(is_empty != NULL, "isEmpty builtin lookup succeeds");
    require_true(is_symbol != NULL, "isSymbol builtin lookup succeeds");
    require_true(is_class != NULL, "isClass builtin lookup succeeds");
    require_true(is_callable != NULL, "isCallable builtin lookup succeeds");
    require_true(is_collection != NULL, "isCollection builtin lookup succeeds");
    require_true(is_set != NULL, "isSet builtin lookup succeeds");
    require_true(is_bag != NULL, "isBag builtin lookup succeeds");
    require_true(classof != NULL, "classof builtin lookup succeeds");
    require_true(attrs != NULL, "attrs builtin lookup succeeds");
    require_true(has_attr != NULL, "hasAttr builtin lookup succeeds");
    require_true(methods != NULL, "methods builtin lookup succeeds");
    require_true(effective_methods != NULL, "effectiveMethods builtin lookup succeeds");
    require_true(classes != NULL, "classes builtin lookup succeeds");
    require_true(supers != NULL, "supers builtin lookup succeeds");
    require_true(superiors != NULL, "superiors builtin lookup succeeds");
    require_true(ok_builtin != NULL, "OK builtin lookup succeeds");
    require_true(suppliers != NULL, "suppliers builtin lookup succeeds");
    require_true(method_supplier != NULL, "methodSupplier builtin lookup succeeds");
    require_true(has_method != NULL, "hasMethod builtin lookup succeeds");
    require_true(method_arity != NULL, "methodArity builtin lookup succeeds");
    require_true(method_params != NULL, "methodParams builtin lookup succeeds");
    require_true(callable_arity != NULL, "callableArity builtin lookup succeeds");
    require_true(callable_min_arity != NULL, "callableMinArity builtin lookup succeeds");
    require_true(callable_params != NULL, "callableParams builtin lookup succeeds");
    require_true(callable_arity_range != NULL, "callableArityRange builtin lookup succeeds");
    require_true(version_builtin != NULL, "version builtin lookup succeeds");
    require_true(time_builtin != NULL, "time builtin lookup succeeds");
    require_true(ask_builtin != NULL, "ask builtin lookup succeeds");
    require_true(list_builtin != NULL, "list builtin lookup succeeds");
    require_true(set_builtin != NULL, "set builtin lookup succeeds");
    require_true(bag_builtin != NULL, "bag builtin lookup succeeds");
    require_true(append != NULL, "append builtin lookup succeeds");
    require_true(size != NULL, "size builtin lookup succeeds");
    require_true(map != NULL, "map builtin lookup succeeds");
    require_true(collect != NULL, "collect builtin lookup succeeds");
    require_true(filter != NULL, "filter builtin lookup succeeds");
    require_true(select != NULL, "select builtin lookup succeeds");
    require_true(all != NULL, "all builtin lookup succeeds");
    require_true(exists != NULL, "exists builtin lookup succeeds");
    require_true(locate != NULL, "locate builtin lookup succeeds");
    require_true(for_each_do != NULL, "forEachDo builtin lookup succeeds");
    require_true(reduce != NULL, "reduce builtin lookup succeeds");
    require_true(member != NULL, "member builtin lookup succeeds");
    require_true(insert != NULL, "insert builtin lookup succeeds");
    require_true(add != NULL, "add builtin lookup succeeds");
    require_true(remove != NULL, "remove builtin lookup succeeds");
    require_true(unitset != NULL, "unitset builtin lookup succeeds");
    require_true(union_builtin != NULL, "union builtin lookup succeeds");
    require_true(union_aggregate != NULL, "UNION builtin lookup succeeds");
    require_true(difference != NULL, "difference builtin lookup succeeds");
    require_true(intersection != NULL, "intersection builtin lookup succeeds");
    require_true(subset != NULL, "subset builtin lookup succeeds");
    require_true(equal != NULL, "equal builtin lookup succeeds");
    require_true(enact_builtin_lookup("missing") == NULL, "missing builtin lookup fails");
    require_true(enact_builtin_lookup("load") == NULL, "load is not a builtin");
    require_true(enact_builtin_lookup("bye") == NULL, "bye is not a builtin");
    require_true(enact_builtin_lookup(NULL) == NULL, "null builtin lookup fails");
    require_true(strcmp(enact_builtin_name(hd), "hd") == 0, "hd builtin name");
    require_true(strcmp(enact_builtin_name(NULL), "") == 0, "null builtin name");
    require_true(enact_builtin_arity(hd) == 1, "hd builtin arity");
    require_true(enact_builtin_arity(atom) == 1, "atom builtin arity");
    require_true(enact_builtin_arity(is_object) == 1, "isObject builtin arity");
    require_true(enact_builtin_arity(is_int) == 1, "isInt builtin arity");
    require_true(enact_builtin_arity(is_bool) == 1, "isBool builtin arity");
    require_true(enact_builtin_arity(is_string) == 1, "isString builtin arity");
    require_true(enact_builtin_arity(is_list) == 1, "isList builtin arity");
    require_true(enact_builtin_arity(is_nil) == 1, "isNil builtin arity");
    require_true(enact_builtin_arity(is_empty) == 1, "isEmpty builtin arity");
    require_true(enact_builtin_arity(is_symbol) == 1, "isSymbol builtin arity");
    require_true(enact_builtin_arity(is_class) == 1, "isClass builtin arity");
    require_true(enact_builtin_arity(is_callable) == 1, "isCallable builtin arity");
    require_true(enact_builtin_arity(is_collection) == 1, "isCollection builtin arity");
    require_true(enact_builtin_arity(is_set) == 1, "isSet builtin arity");
    require_true(enact_builtin_arity(is_bag) == 1, "isBag builtin arity");
    require_true(enact_builtin_arity(classof) == 1, "classof builtin arity");
    require_true(enact_builtin_arity(attrs) == 1, "attrs builtin arity");
    require_true(enact_builtin_arity(has_attr) == 2, "hasAttr builtin arity");
    require_true(enact_builtin_arity(methods) == 1, "methods builtin arity");
    require_true(enact_builtin_arity(effective_methods) == 1, "effectiveMethods builtin arity");
    require_true(enact_builtin_arity(classes) == 1, "classes builtin arity");
    require_true(enact_builtin_arity(supers) == 1, "supers builtin arity");
    require_true(enact_builtin_arity(superiors) == 1, "superiors builtin arity");
    require_true(enact_builtin_arity(ok_builtin) == 1, "OK builtin arity");
    require_true(enact_builtin_arity(suppliers) == 2, "suppliers builtin arity");
    require_true(enact_builtin_arity(method_supplier) == 2, "methodSupplier builtin arity");
    require_true(enact_builtin_arity(has_method) == 2, "hasMethod builtin arity");
    require_true(enact_builtin_arity(method_arity) == 2, "methodArity builtin arity");
    require_true(enact_builtin_arity(method_params) == 2, "methodParams builtin arity");
    require_true(enact_builtin_arity(callable_arity) == 1, "callableArity builtin arity");
    require_true(enact_builtin_arity(callable_min_arity) == 1, "callableMinArity builtin arity");
    require_true(enact_builtin_arity(callable_params) == 1, "callableParams builtin arity");
    require_true(enact_builtin_arity(callable_arity_range) == 1, "callableArityRange builtin arity");
    require_true(enact_builtin_arity(version_builtin) == 0, "version builtin arity");
    require_true(enact_builtin_arity(time_builtin) == 0, "time builtin arity");
    require_true(enact_builtin_arity(ask_builtin) == 0, "ask builtin arity");
    require_true(enact_builtin_arity(list_builtin) == 1, "list builtin arity");
    require_true(enact_builtin_min_arity(set_builtin) == 0, "set builtin min arity");
    require_true(enact_builtin_min_arity(bag_builtin) == 0, "bag builtin min arity");
    require_true(enact_builtin_arity(set_builtin) == 1, "set builtin max arity");
    require_true(enact_builtin_arity(bag_builtin) == 1, "bag builtin max arity");
    require_true(enact_builtin_arity(append) == 2, "append builtin arity");
    require_true(enact_builtin_arity(size) == 1, "size builtin arity");
    require_true(enact_builtin_arity(map) == 2, "map builtin arity");
    require_true(enact_builtin_arity(collect) == 2, "collect builtin arity");
    require_true(enact_builtin_arity(filter) == 2, "filter builtin arity");
    require_true(enact_builtin_arity(select) == 2, "select builtin arity");
    require_true(enact_builtin_arity(all) == 2, "all builtin arity");
    require_true(enact_builtin_arity(exists) == 2, "exists builtin arity");
    require_true(enact_builtin_arity(locate) == 2, "locate builtin arity");
    require_true(enact_builtin_arity(for_each_do) == 2, "forEachDo builtin arity");
    require_true(enact_builtin_arity(reduce) == 3, "reduce builtin arity");
    require_true(enact_builtin_arity(member) == 2, "member builtin arity");
    require_true(enact_builtin_arity(insert) == 2, "insert builtin arity");
    require_true(enact_builtin_arity(add) == 2, "add builtin arity");
    require_true(enact_builtin_arity(remove) == 2, "remove builtin arity");
    require_true(enact_builtin_arity(unitset) == 1, "unitset builtin arity");
    require_true(enact_builtin_arity(union_builtin) == 2, "union builtin arity");
    require_true(enact_builtin_arity(union_aggregate) == 1, "UNION builtin arity");
    require_true(enact_builtin_arity(difference) == 2, "difference builtin arity");
    require_true(enact_builtin_arity(intersection) == 2, "intersection builtin arity");
    require_true(enact_builtin_arity(subset) == 2, "subset builtin arity");
    require_true(enact_builtin_arity(equal) == 2, "equal builtin arity");
    require_true(enact_builtin_min_arity(append) == 2, "append builtin min arity");
    require_true(enact_builtin_arity(NULL) == 0, "null builtin arity");
    require_true(enact_builtin_min_arity(NULL) == 0, "null builtin min arity");
    require_true(enact_builtin_partial_builtin(NULL) == NULL, "null partial builtin accessor");
    require_true(enact_builtin_partial_argument_count(NULL) == 0, "null partial argument count");
    require_true(enact_builtin_partial_retain(NULL) == NULL, "null partial retain");
    enact_builtin_partial_release(NULL);

    builtin_value = enact_value_make_builtin(hd);
    require_true(builtin_value.kind == ENACT_VALUE_BUILTIN, "builtin value kind");
    require_true(enact_value_copy(&builtin_copy, &builtin_value), "builtin value copy succeeds");
    require_true(builtin_copy.kind == ENACT_VALUE_BUILTIN, "builtin copy kind");
    require_true(builtin_copy.as.as_builtin == builtin_value.as.as_builtin, "builtin copy payload");
    require_true(enact_value_equal(&builtin_value, &builtin_copy, &values_equal), "builtin equality succeeds");
    require_true(values_equal, "builtin equality true");
    args[0] = builtin_value;
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_class, args, 1, &result, &diag), "isClass builtin apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "isClass builtin result kind");
    require_true(!result.as.as_bool, "isClass builtin result false");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_callable, args, 1, &result, &diag), "isCallable builtin apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "isCallable builtin result kind");
    require_true(result.as.as_bool, "isCallable builtin result true");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(callable_arity, args, 1, &result, &diag), "callableArity builtin apply succeeds");
    require_true(result.kind == ENACT_VALUE_INT, "callableArity builtin result kind");
    require_true(result.as.as_int == 1, "callableArity builtin result value");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(
        enact_builtin_apply(callable_min_arity, args, 1, &result, &diag),
        "callableMinArity builtin apply succeeds");
    require_true(result.kind == ENACT_VALUE_INT, "callableMinArity builtin result kind");
    require_true(result.as.as_int == 1, "callableMinArity builtin result value");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(callable_params, args, 1, &result, &diag), "callableParams builtin apply succeeds");
    require_true(result.kind == ENACT_VALUE_LIST, "callableParams builtin result kind");
    require_true(enact_list_head(result.as.as_list)->kind == ENACT_VALUE_ATOM, "callableParams builtin head kind");
    require_true(
        strcmp(enact_list_head(result.as.as_list)->as.as_atom, "list") == 0,
        "callableParams builtin head value");
    require_true(enact_list_tail(result.as.as_list) == NULL, "callableParams builtin tail");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(
        enact_builtin_apply(callable_arity_range, args, 1, &result, &diag),
        "callableArityRange builtin apply succeeds");
    require_true(result.kind == ENACT_VALUE_LIST, "callableArityRange builtin result kind");
    require_true(enact_list_head(result.as.as_list)->as.as_int == 1, "callableArityRange builtin min");
    require_true(
        enact_list_head(enact_list_tail(result.as.as_list))->as.as_int == 1,
        "callableArityRange builtin max");
    require_true(enact_list_tail(enact_list_tail(result.as.as_list)) == NULL, "callableArityRange builtin tail");
    enact_value_free(&result);
    enact_value_free(&builtin_copy);
    builtin_value = enact_value_make_builtin(NULL);
    require_true(!enact_value_copy(&builtin_copy, &builtin_value), "null builtin copy fails");

    args[0] = enact_value_make_int(1);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(atom, args, 1, &result, &diag), "atom int apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "atom int result kind");
    require_true(result.as.as_bool, "atom int result true");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_object, args, 1, &result, &diag), "isObject int apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "isObject int result kind");
    require_true(!result.as.as_bool, "isObject int result false");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_int, args, 1, &result, &diag), "isInt int apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "isInt int result kind");
    require_true(result.as.as_bool, "isInt int result true");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_bool, args, 1, &result, &diag), "isBool int apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "isBool int result kind");
    require_true(!result.as.as_bool, "isBool int result false");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_string, args, 1, &result, &diag), "isString int apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "isString int result kind");
    require_true(!result.as.as_bool, "isString int result false");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_list, args, 1, &result, &diag), "isList int apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "isList int result kind");
    require_true(!result.as.as_bool, "isList int result false");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_nil, args, 1, &result, &diag), "isNil int apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "isNil int result kind");
    require_true(!result.as.as_bool, "isNil int result false");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_empty, args, 1, &result, &diag), "isEmpty int apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "isEmpty int result kind");
    require_true(!result.as.as_bool, "isEmpty int result false");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_symbol, args, 1, &result, &diag), "isSymbol int apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "isSymbol int result kind");
    require_true(!result.as.as_bool, "isSymbol int result false");
    enact_value_free(&result);
    args[0] = enact_value_make_bool(true);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_bool, args, 1, &result, &diag), "isBool bool apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "isBool bool result kind");
    require_true(result.as.as_bool, "isBool bool result true");
    enact_value_free(&result);
    args[0] = enact_value_make_string(copy_test_name("x"));
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_string, args, 1, &result, &diag), "isString string apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "isString string result kind");
    require_true(result.as.as_bool, "isString string result true");
    enact_value_free(&result);
    enact_value_free(&args[0]);
    args[0] = enact_value_make_list(NULL);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_list, args, 1, &result, &diag), "isList nil apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "isList nil result kind");
    require_true(result.as.as_bool, "isList nil result true");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_nil, args, 1, &result, &diag), "isNil nil apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "isNil nil result kind");
    require_true(result.as.as_bool, "isNil nil result true");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_empty, args, 1, &result, &diag), "isEmpty nil apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "isEmpty nil result kind");
    require_true(result.as.as_bool, "isEmpty nil result true");
    enact_value_free(&result);
    enact_value_free(&args[0]);
    head = enact_value_make_int(1);
    list = enact_list_cons(&head, NULL);
    require_true(list != NULL, "isNil non-empty list fixture created");
    args[0] = enact_value_make_list(list);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_nil, args, 1, &result, &diag), "isNil list apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "isNil list result kind");
    require_true(!result.as.as_bool, "isNil list result false");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_empty, args, 1, &result, &diag), "isEmpty list apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "isEmpty list result kind");
    require_true(!result.as.as_bool, "isEmpty list result false");
    enact_value_free(&result);
    enact_value_free(&args[0]);
    args[0] = enact_value_make_atom(copy_test_name("x"));
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_symbol, args, 1, &result, &diag), "isSymbol atom apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "isSymbol atom result kind");
    require_true(result.as.as_bool, "isSymbol atom result true");
    enact_value_free(&result);
    enact_value_free(&args[0]);
    object_class = enact_class_new("Object");
    object = object_class ? enact_object_new(object_class) : NULL;
    require_true(object_class != NULL && object != NULL, "isObject test object created");
    if (object_class && object) {
        args[0] = enact_value_make_object(object);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(is_object, args, 1, &result, &diag), "isObject object apply succeeds");
        require_true(result.kind == ENACT_VALUE_BOOL, "isObject object result kind");
        require_true(result.as.as_bool, "isObject object result true");
        enact_value_free(&result);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(is_class, args, 1, &result, &diag), "isClass object apply succeeds");
        require_true(result.kind == ENACT_VALUE_BOOL, "isClass object result kind");
        require_true(!result.as.as_bool, "isClass object result false");
        enact_value_free(&result);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(is_callable, args, 1, &result, &diag), "isCallable object apply succeeds");
        require_true(result.kind == ENACT_VALUE_BOOL, "isCallable object result kind");
        require_true(!result.as.as_bool, "isCallable object result false");
        enact_value_free(&result);
        enact_diag_reset(&diag);
        require_true(
            enact_builtin_apply(is_collection, args, 1, &result, &diag),
            "isCollection object apply succeeds");
        require_true(result.kind == ENACT_VALUE_BOOL, "isCollection object result kind");
        require_true(!result.as.as_bool, "isCollection object result false");
        enact_value_free(&result);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(is_set, args, 1, &result, &diag), "isSet object apply succeeds");
        require_true(result.kind == ENACT_VALUE_BOOL, "isSet object result kind");
        require_true(!result.as.as_bool, "isSet object result false");
        enact_value_free(&result);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(is_bag, args, 1, &result, &diag), "isBag object apply succeeds");
        require_true(result.kind == ENACT_VALUE_BOOL, "isBag object result kind");
        require_true(!result.as.as_bool, "isBag object result false");
        enact_value_free(&result);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(is_empty, args, 1, &result, &diag), "isEmpty object apply succeeds");
        require_true(result.kind == ENACT_VALUE_BOOL, "isEmpty object result kind");
        require_true(!result.as.as_bool, "isEmpty object result false");
        enact_value_free(&result);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(atom, args, 1, &result, &diag), "atom object apply succeeds");
        require_true(result.kind == ENACT_VALUE_BOOL, "atom object result kind");
        require_true(result.as.as_bool, "atom object result true");
        enact_value_free(&result);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(classof, args, 1, &result, &diag), "classof object apply succeeds");
        require_true(result.kind == ENACT_VALUE_CLASS, "classof object result kind");
        require_true(result.as.as_class == object_class, "classof object class identity");
        require_true(strcmp(enact_class_name(result.as.as_class), "Object") == 0, "classof object class name");
        enact_value_free(&result);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(attrs, args, 1, &result, &diag), "attrs empty object apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "attrs empty object result kind");
        require_true(result.as.as_list == NULL, "attrs empty object result nil");
        enact_value_free(&result);
        supplier_args[0] = args[0];
        supplier_args[1] = enact_value_make_atom(copy_test_name("x"));
        enact_diag_reset(&diag);
        require_true(
            enact_builtin_apply(has_attr, supplier_args, 2, &result, &diag),
            "hasAttr missing apply succeeds");
        require_true(result.kind == ENACT_VALUE_BOOL, "hasAttr missing result kind");
        require_true(!result.as.as_bool, "hasAttr missing result false");
        enact_value_free(&result);
        enact_value_free(&supplier_args[1]);
        attribute_value = enact_value_make_int(1);
        require_true(enact_object_define_attribute(object, "x", attribute_value), "attrs test attribute define");
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(attrs, args, 1, &result, &diag), "attrs object apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "attrs object result kind");
        require_true(result.as.as_list != NULL, "attrs object result non-empty");
        require_true(enact_list_head(result.as.as_list)->kind == ENACT_VALUE_ATOM, "attrs object head kind");
        require_true(strcmp(enact_list_head(result.as.as_list)->as.as_atom, "x") == 0, "attrs object head value");
        require_true(enact_list_tail(result.as.as_list) == NULL, "attrs object result tail nil");
        enact_value_free(&result);
        supplier_args[1] = enact_value_make_atom(copy_test_name("x"));
        enact_diag_reset(&diag);
        require_true(
            enact_builtin_apply(has_attr, supplier_args, 2, &result, &diag),
            "hasAttr object apply succeeds");
        require_true(result.kind == ENACT_VALUE_BOOL, "hasAttr object result kind");
        require_true(result.as.as_bool, "hasAttr object result true");
        enact_value_free(&result);
        enact_value_free(&supplier_args[1]);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(supers, args, 1, &result, &diag), "supers root object apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "supers root object result kind");
        require_true(result.as.as_list == NULL, "supers root object result nil");
        enact_value_free(&result);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(superiors, args, 1, &result, &diag), "superiors root object apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "superiors root object result kind");
        require_true(result.as.as_list == NULL, "superiors root object result nil");
        enact_value_free(&result);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(methods, args, 1, &result, &diag), "methods root object apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "methods root object result kind");
        require_true(result.as.as_list == NULL, "methods root object result nil");
        enact_value_free(&result);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(classes, args, 1, &result, &diag), "classes root object apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "classes root object result kind");
        require_true(result.as.as_list != NULL, "classes root object result non-empty");
        require_true(enact_list_head(result.as.as_list)->kind == ENACT_VALUE_CLASS, "classes root object head kind");
        require_true(
            enact_list_head(result.as.as_list)->as.as_class == object_class,
            "classes root object head identity");
        require_true(enact_list_tail(result.as.as_list) == NULL, "classes root object result tail nil");
        enact_value_free(&result);
        enact_value_free(&args[0]);
        args[0] = enact_value_make_class(object_class);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(is_class, args, 1, &result, &diag), "isClass class apply succeeds");
        require_true(result.kind == ENACT_VALUE_BOOL, "isClass class result kind");
        require_true(result.as.as_bool, "isClass class result true");
        enact_value_free(&result);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(is_callable, args, 1, &result, &diag), "isCallable class apply succeeds");
        require_true(result.kind == ENACT_VALUE_BOOL, "isCallable class result kind");
        require_true(!result.as.as_bool, "isCallable class result false");
        enact_value_free(&result);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(supers, args, 1, &result, &diag), "supers root class apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "supers root class result kind");
        require_true(result.as.as_list == NULL, "supers root class result nil");
        enact_value_free(&result);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(superiors, args, 1, &result, &diag), "superiors root class apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "superiors root class result kind");
        require_true(result.as.as_list == NULL, "superiors root class result nil");
        enact_value_free(&result);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(methods, args, 1, &result, &diag), "methods root class apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "methods root class result kind");
        require_true(result.as.as_list == NULL, "methods root class result nil");
        enact_value_free(&result);
        enact_diag_reset(&diag);
        require_true(
            enact_builtin_apply(effective_methods, args, 1, &result, &diag),
            "effectiveMethods root class apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "effectiveMethods root class result kind");
        require_true(result.as.as_list == NULL, "effectiveMethods root class result nil");
        enact_value_free(&result);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(classes, args, 1, &result, &diag), "classes root class apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "classes root class result kind");
        require_true(result.as.as_list != NULL, "classes root class result non-empty");
        require_true(enact_list_head(result.as.as_list)->kind == ENACT_VALUE_CLASS, "classes root class head kind");
        require_true(
            enact_list_head(result.as.as_list)->as.as_class == object_class,
            "classes root class head identity");
        require_true(enact_list_tail(result.as.as_list) == NULL, "classes root class result tail nil");
        enact_value_free(&result);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(ok_builtin, args, 1, &result, &diag), "OK root class apply succeeds");
        require_true(result.kind == ENACT_VALUE_BOOL, "OK root class result kind");
        require_true(result.as.as_bool, "OK root class result true");
        enact_value_free(&result);
        supplier_args[0] = enact_value_make_class(object_class);
        supplier_args[1] = enact_value_make_atom(copy_test_name("missing"));
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(suppliers, supplier_args, 2, &result, &diag), "suppliers missing apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "suppliers missing result kind");
        require_true(result.as.as_list == NULL, "suppliers missing result nil");
        enact_value_free(&result);
        enact_value_free(&supplier_args[1]);
        supplier_args[1] = enact_value_make_atom(copy_test_name("missing"));
        enact_diag_reset(&diag);
        require_true(
            enact_builtin_apply(method_supplier, supplier_args, 2, &result, &diag),
            "methodSupplier missing apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "methodSupplier missing result kind");
        require_true(result.as.as_list == NULL, "methodSupplier missing result nil");
        enact_value_free(&result);
        enact_value_free(&supplier_args[1]);
        supplier_args[1] = enact_value_make_atom(copy_test_name("missing"));
        enact_diag_reset(&diag);
        require_true(
            enact_builtin_apply(has_method, supplier_args, 2, &result, &diag),
            "hasMethod missing apply succeeds");
        require_true(result.kind == ENACT_VALUE_BOOL, "hasMethod missing result kind");
        require_true(!result.as.as_bool, "hasMethod missing result false");
        enact_value_free(&result);
        enact_value_free(&supplier_args[1]);
        supplier_args[1] = enact_value_make_atom(copy_test_name("missing"));
        enact_diag_reset(&diag);
        require_true(
            enact_builtin_apply(method_arity, supplier_args, 2, &result, &diag),
            "methodArity missing apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "methodArity missing result kind");
        require_true(result.as.as_list == NULL, "methodArity missing result nil");
        enact_value_free(&result);
        enact_value_free(&supplier_args[1]);
        supplier_args[1] = enact_value_make_atom(copy_test_name("missing"));
        enact_diag_reset(&diag);
        require_true(
            enact_builtin_apply(method_params, supplier_args, 2, &result, &diag),
            "methodParams missing apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "methodParams missing result kind");
        require_true(result.as.as_list == NULL, "methodParams missing result nil");
        enact_value_free(&result);
        enact_value_free(&supplier_args[1]);
        node_class = enact_class_new_with_superclass("Node", object_class);
        require_true(node_class != NULL, "supers test subclass created");
        if (node_class) {
            args[0] = enact_value_make_class(node_class);
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(supers, args, 1, &result, &diag), "supers subclass apply succeeds");
            require_true(result.kind == ENACT_VALUE_LIST, "supers subclass result kind");
            require_true(result.as.as_list != NULL, "supers subclass result non-empty");
            require_true(enact_list_head(result.as.as_list)->kind == ENACT_VALUE_CLASS, "supers subclass head kind");
            require_true(
                enact_list_head(result.as.as_list)->as.as_class == object_class,
                "supers subclass head identity");
            require_true(enact_list_tail(result.as.as_list) == NULL, "supers subclass result tail nil");
            enact_value_free(&result);
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(classes, args, 1, &result, &diag), "classes subclass apply succeeds");
            require_true(result.kind == ENACT_VALUE_LIST, "classes subclass result kind");
            require_true(result.as.as_list != NULL, "classes subclass result non-empty");
            require_true(
                enact_list_head(result.as.as_list)->as.as_class == node_class,
                "classes subclass head identity");
            require_true(enact_list_tail(result.as.as_list) != NULL, "classes subclass tail non-empty");
            require_true(
                enact_list_head(enact_list_tail(result.as.as_list))->as.as_class == object_class,
                "classes subclass tail identity");
            require_true(
                enact_list_tail(enact_list_tail(result.as.as_list)) == NULL,
                "classes subclass result ends");
            enact_value_free(&result);
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(superiors, args, 1, &result, &diag), "superiors subclass apply succeeds");
            require_true(result.kind == ENACT_VALUE_LIST, "superiors subclass result kind");
            require_true(result.as.as_list != NULL, "superiors subclass result non-empty");
            require_true(
                enact_list_head(result.as.as_list)->as.as_class == object_class,
                "superiors subclass head identity");
            require_true(enact_list_tail(result.as.as_list) == NULL, "superiors subclass result tail nil");
            enact_value_free(&result);
            node_object = enact_object_new(node_class);
            require_true(node_object != NULL, "supers object test subclass object created");
            if (node_object) {
                args[0] = enact_value_make_object(node_object);
                enact_diag_reset(&diag);
                require_true(enact_builtin_apply(supers, args, 1, &result, &diag), "supers subclass object apply succeeds");
                require_true(result.kind == ENACT_VALUE_LIST, "supers subclass object result kind");
                require_true(result.as.as_list != NULL, "supers subclass object result non-empty");
                require_true(
                    enact_list_head(result.as.as_list)->as.as_class == object_class,
                    "supers subclass object head identity");
                require_true(enact_list_tail(result.as.as_list) == NULL, "supers subclass object result tail nil");
                enact_value_free(&result);
                enact_diag_reset(&diag);
                require_true(
                    enact_builtin_apply(superiors, args, 1, &result, &diag),
                    "superiors subclass object apply succeeds");
                require_true(result.kind == ENACT_VALUE_LIST, "superiors subclass object result kind");
                require_true(result.as.as_list != NULL, "superiors subclass object result non-empty");
                require_true(
                    enact_list_head(result.as.as_list)->as.as_class == object_class,
                    "superiors subclass object head identity");
                require_true(
                    enact_list_tail(result.as.as_list) == NULL,
                    "superiors subclass object result tail nil");
                enact_value_free(&result);
                enact_diag_reset(&diag);
                require_true(enact_builtin_apply(methods, args, 1, &result, &diag), "methods subclass object apply succeeds");
                require_true(result.kind == ENACT_VALUE_LIST, "methods subclass object result kind");
                require_true(result.as.as_list == NULL, "methods subclass object result nil");
                enact_value_free(&result);
                enact_diag_reset(&diag);
                require_true(
                    enact_builtin_apply(effective_methods, args, 1, &result, &diag),
                    "effectiveMethods subclass object apply succeeds");
                require_true(result.kind == ENACT_VALUE_LIST, "effectiveMethods subclass object result kind");
                require_true(result.as.as_list == NULL, "effectiveMethods subclass object result nil");
                enact_value_free(&result);
                enact_diag_reset(&diag);
                require_true(enact_builtin_apply(classes, args, 1, &result, &diag), "classes subclass object apply succeeds");
                require_true(result.kind == ENACT_VALUE_LIST, "classes subclass object result kind");
                require_true(result.as.as_list != NULL, "classes subclass object result non-empty");
                require_true(
                    enact_list_head(result.as.as_list)->as.as_class == node_class,
                    "classes subclass object head identity");
                require_true(
                    enact_list_tail(result.as.as_list) != NULL,
                    "classes subclass object tail non-empty");
                require_true(
                    enact_list_head(enact_list_tail(result.as.as_list))->as.as_class == object_class,
                    "classes subclass object tail identity");
                require_true(
                    enact_list_tail(enact_list_tail(result.as.as_list)) == NULL,
                    "classes subclass object result ends");
                enact_value_free(&result);
                enact_value_free(&args[0]);
            }
            leaf_class = enact_class_new_with_superclass("Leaf", node_class);
            require_true(leaf_class != NULL, "superiors test leaf class created");
            if (leaf_class) {
                EnactList *tail;

                args[0] = enact_value_make_class(leaf_class);
                enact_diag_reset(&diag);
                require_true(enact_builtin_apply(superiors, args, 1, &result, &diag), "superiors leaf apply succeeds");
                require_true(result.kind == ENACT_VALUE_LIST, "superiors leaf result kind");
                require_true(result.as.as_list != NULL, "superiors leaf result non-empty");
                require_true(
                    enact_list_head(result.as.as_list)->as.as_class == node_class,
                    "superiors leaf head identity");
                tail = enact_list_tail(result.as.as_list);
                require_true(tail != NULL, "superiors leaf tail non-empty");
                require_true(enact_list_head(tail)->as.as_class == object_class, "superiors leaf tail identity");
                require_true(enact_list_tail(tail) == NULL, "superiors leaf result ends");
                enact_value_free(&result);
                enact_class_release(leaf_class);
            }
            enact_class_release(node_class);
        }
    } else {
        enact_object_release(object);
    }
    enact_class_release(object_class);
    args[0] = enact_value_make_int(1);
    enact_diag_reset(&diag);
    require_true(!enact_builtin_apply(classof, args, 1, &result, &diag), "classof int fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_OBJECT, "classof int error code");
    enact_diag_reset(&diag);
    require_true(!enact_builtin_apply(attrs, args, 1, &result, &diag), "attrs int fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_OBJECT, "attrs int error code");
    enact_diag_reset(&diag);
    require_true(!enact_builtin_apply(supers, args, 1, &result, &diag), "supers int fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT, "supers int error code");
    enact_diag_reset(&diag);
    require_true(!enact_builtin_apply(superiors, args, 1, &result, &diag), "superiors int fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT, "superiors int error code");
    enact_diag_reset(&diag);
    require_true(!enact_builtin_apply(methods, args, 1, &result, &diag), "methods int fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT, "methods int error code");
    enact_diag_reset(&diag);
    require_true(
        !enact_builtin_apply(effective_methods, args, 1, &result, &diag),
        "effectiveMethods int fails");
    require_true(
        diag.code == ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT,
        "effectiveMethods int error code");
    enact_diag_reset(&diag);
    require_true(!enact_builtin_apply(classes, args, 1, &result, &diag), "classes int fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT, "classes int error code");
    enact_diag_reset(&diag);
    require_true(!enact_builtin_apply(ok_builtin, args, 1, &result, &diag), "OK int fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT, "OK int error code");
    supplier_args[0] = enact_value_make_int(1);
    supplier_args[1] = enact_value_make_atom(copy_test_name("missing"));
    enact_diag_reset(&diag);
    require_true(
        !enact_builtin_apply(method_supplier, supplier_args, 2, &result, &diag),
        "methodSupplier int class fails");
    require_true(
        diag.code == ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT,
        "methodSupplier int class error code");
    enact_value_free(&supplier_args[1]);
    object_class = enact_class_new("Object");
    require_true(object_class != NULL, "suppliers type test class created");
    if (object_class) {
        supplier_args[0] = enact_value_make_class(object_class);
        supplier_args[1] = enact_value_make_int(1);
        enact_diag_reset(&diag);
        require_true(!enact_builtin_apply(suppliers, supplier_args, 2, &result, &diag), "suppliers non-atom fails");
        require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_ATOM, "suppliers non-atom error code");
        enact_diag_reset(&diag);
        require_true(
            !enact_builtin_apply(method_supplier, supplier_args, 2, &result, &diag),
            "methodSupplier non-atom fails");
        require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_ATOM, "methodSupplier non-atom error code");
        enact_value_free(&supplier_args[0]);
        enact_value_free(&supplier_args[1]);
        object_class = NULL;
    }
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(version_builtin, NULL, 0, &result, &diag), "version apply succeeds");
    require_true(result.kind == ENACT_VALUE_STRING, "version result kind");
    require_true(strcmp(result.as.as_string, "enact-auto 0.1.0") == 0, "version result value");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(time_builtin, NULL, 0, &result, &diag), "time apply succeeds");
    require_true(result.kind == ENACT_VALUE_INT, "time result kind");
    require_true(result.as.as_int >= 0, "time result non-negative");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(!enact_builtin_apply(ask_builtin, NULL, 0, &result, &diag), "ask apply without env fails");
    require_true(diag.code == ENACT_ERR_INPUT_UNAVAILABLE, "ask apply without env code");
    enact_env_set_input_provider(&env, test_input_provider, &ask_input);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply_in_env(ask_builtin, &env, NULL, 0, &result, &diag), "ask env apply succeeds");
    require_true(result.kind == ENACT_VALUE_STRING, "ask env result kind");
    require_true(strcmp(result.as.as_string, "unit input") == 0, "ask env strips newline");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply_in_env(ask_builtin, &env, NULL, 0, &result, &diag), "ask empty line succeeds");
    require_true(result.kind == ENACT_VALUE_STRING, "ask empty result kind");
    require_true(strcmp(result.as.as_string, "") == 0, "ask empty result value");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(!enact_builtin_apply_in_env(ask_builtin, &env, NULL, 0, &result, &diag), "ask env EOF fails");
    require_true(diag.code == ENACT_ERR_INPUT_UNAVAILABLE, "ask env EOF code");
    args[0] = enact_value_make_int(1);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(list_builtin, args, 1, &result, &diag), "list int apply succeeds");
    require_true(result.kind == ENACT_VALUE_LIST, "list int result kind");
    require_true(result.as.as_list != NULL, "list int result non-empty");
    require_true(enact_list_head(result.as.as_list)->as.as_int == 1, "list int result head");
    require_true(enact_list_tail(result.as.as_list) == NULL, "list int result tail nil");
    enact_value_free(&result);

    args[0] = enact_value_make_builtin(hd);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(atom, args, 1, &result, &diag), "atom builtin apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "atom builtin result kind");
    require_true(result.as.as_bool, "atom builtin result true");
    enact_value_free(&result);

    head = enact_value_make_int(11);
    list = enact_list_cons(&head, NULL);
    require_true(list != NULL, "builtin test list created");
    args[0] = enact_value_make_list(list);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(atom, args, 1, &result, &diag), "atom non-empty list apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "atom non-empty list result kind");
    require_true(!result.as.as_bool, "atom non-empty list result false");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(hd, args, 1, &result, &diag), "hd builtin apply succeeds");
    require_true(result.kind == ENACT_VALUE_INT, "hd builtin result kind");
    require_true(result.as.as_int == 11, "hd builtin result value");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(tl, args, 1, &result, &diag), "tl builtin apply succeeds");
    require_true(result.kind == ENACT_VALUE_LIST, "tl builtin result kind");
    require_true(result.as.as_list == NULL, "tl builtin singleton tail is nil");
    enact_value_free(&result);
    enact_value_free(&args[0]);

    args[0] = enact_value_make_list(NULL);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(atom, args, 1, &result, &diag), "atom nil apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "atom nil result kind");
    require_true(result.as.as_bool, "atom nil result true");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(!enact_builtin_apply(hd, args, 1, &result, &diag), "hd nil fails");
    require_true(diag.code == ENACT_ERR_LIST_EMPTY, "hd nil error code");
    enact_diag_reset(&diag);
    require_true(!enact_builtin_apply(tl, args, 1, &result, &diag), "tl nil fails");
    require_true(diag.code == ENACT_ERR_LIST_EMPTY, "tl nil error code");

    head = enact_value_make_int(1);
    left_list = enact_list_cons(&head, NULL);
    head = enact_value_make_int(2);
    right_list = enact_list_cons(&head, NULL);
    require_true(left_list != NULL && right_list != NULL, "append test lists created");
    if (left_list && right_list) {
        append_args[0] = enact_value_make_list(left_list);
        append_args[1] = enact_value_make_list(right_list);
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(size, append_args, 1, &result, &diag), "size builtin apply succeeds");
        require_true(result.kind == ENACT_VALUE_INT, "size builtin result kind");
        require_true(result.as.as_int == 1, "size builtin result value");
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(append, append_args, 2, &result, &diag), "append builtin apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "append builtin result kind");
        require_true(enact_list_head(result.as.as_list)->as.as_int == 1, "append builtin first value");
        require_true(enact_list_head(enact_list_tail(result.as.as_list))->as.as_int == 2, "append builtin second value");
        require_true(enact_list_tail(enact_list_tail(result.as.as_list)) == NULL, "append builtin tail nil");
        enact_value_free(&result);

        set_args[0] = enact_value_make_int(1);
        set_args[1] = append_args[0];
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(member, set_args, 2, &result, &diag), "member builtin apply succeeds");
        require_true(result.kind == ENACT_VALUE_BOOL, "member builtin result kind");
        require_true(result.as.as_bool, "member builtin finds value");
        enact_value_free(&result);

        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(remove, set_args, 2, &result, &diag), "remove builtin apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "remove builtin result kind");
        require_true(result.as.as_list == NULL, "remove singleton result nil");
        enact_value_free(&result);

        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(unitset, set_args, 1, &result, &diag), "unitset builtin apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "unitset builtin result kind");
        require_true(enact_list_head(result.as.as_list)->as.as_int == 1, "unitset builtin first value");
        require_true(enact_list_tail(result.as.as_list) == NULL, "unitset builtin tail nil");
        enact_value_free(&result);

        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(union_builtin, append_args, 2, &result, &diag), "union builtin apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "union builtin result kind");
        require_true(enact_list_head(result.as.as_list)->as.as_int == 1, "union builtin first value");
        require_true(enact_list_head(enact_list_tail(result.as.as_list))->as.as_int == 2, "union builtin second value");
        require_true(enact_list_tail(enact_list_tail(result.as.as_list)) == NULL, "union builtin tail nil");
        enact_value_free(&result);

        enact_diag_reset(&diag);
        require_true(
            enact_builtin_apply(difference, append_args, 2, &result, &diag),
            "difference builtin apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "difference builtin result kind");
        require_true(enact_list_head(result.as.as_list)->as.as_int == 1, "difference builtin keeps left value");
        require_true(enact_list_tail(result.as.as_list) == NULL, "difference builtin tail nil");
        enact_value_free(&result);

        enact_diag_reset(&diag);
        require_true(
            enact_builtin_apply(intersection, append_args, 2, &result, &diag),
            "intersection builtin apply succeeds");
        require_true(result.kind == ENACT_VALUE_LIST, "intersection builtin result kind");
        require_true(result.as.as_list == NULL, "intersection disjoint result nil");
        enact_value_free(&result);

        append_partial = enact_builtin_partial_new(append, append_args, 1);
        require_true(append_partial != NULL, "append partial created");
        if (append_partial) {
            require_true(enact_builtin_partial_builtin(append_partial) == append, "append partial builtin");
            require_true(enact_builtin_partial_argument_count(append_partial) == 1, "append partial count");
            partial_value = enact_value_make_builtin_partial(append_partial);
            require_true(partial_value.kind == ENACT_VALUE_BUILTIN_PARTIAL, "partial value kind");
            require_true(enact_value_copy(&partial_copy, &partial_value), "partial value copy succeeds");
            require_true(partial_copy.kind == ENACT_VALUE_BUILTIN_PARTIAL, "partial copy kind");
            require_true(
                partial_copy.as.as_builtin_partial == partial_value.as.as_builtin_partial,
                "partial copy payload");
            require_true(enact_value_equal(&partial_value, &partial_copy, &values_equal), "partial equality succeeds");
            require_true(values_equal, "partial copy equality true");
            other_append_partial = enact_builtin_partial_new(append, append_args, 1);
            require_true(other_append_partial != NULL, "second append partial created");
            if (other_append_partial) {
                other_partial_value = enact_value_make_builtin_partial(other_append_partial);
                require_true(
                    enact_value_equal(&partial_value, &other_partial_value, &values_equal),
                    "independent partial equality succeeds");
                require_true(!values_equal, "independent partial equality false");
                enact_value_free(&other_partial_value);
            }
            args[0] = partial_value;
            enact_diag_reset(&diag);
            require_true(
                enact_builtin_apply(callable_arity, args, 1, &result, &diag),
                "callableArity partial apply succeeds");
            require_true(result.kind == ENACT_VALUE_INT, "callableArity partial result kind");
            require_true(result.as.as_int == 1, "callableArity partial result value");
            enact_value_free(&result);
            enact_diag_reset(&diag);
            require_true(
                enact_builtin_apply(callable_min_arity, args, 1, &result, &diag),
                "callableMinArity partial apply succeeds");
            require_true(result.kind == ENACT_VALUE_INT, "callableMinArity partial result kind");
            require_true(result.as.as_int == 1, "callableMinArity partial result value");
            enact_value_free(&result);
            enact_diag_reset(&diag);
            require_true(
                enact_builtin_apply(callable_params, args, 1, &result, &diag),
                "callableParams partial apply succeeds");
            require_true(result.kind == ENACT_VALUE_LIST, "callableParams partial result kind");
            require_true(enact_list_head(result.as.as_list)->kind == ENACT_VALUE_ATOM, "callableParams partial head kind");
            require_true(
                strcmp(enact_list_head(result.as.as_list)->as.as_atom, "right") == 0,
                "callableParams partial head value");
            require_true(enact_list_tail(result.as.as_list) == NULL, "callableParams partial tail");
            enact_value_free(&result);
            enact_diag_reset(&diag);
            require_true(
                enact_builtin_apply(callable_arity_range, args, 1, &result, &diag),
                "callableArityRange partial apply succeeds");
            require_true(result.kind == ENACT_VALUE_LIST, "callableArityRange partial result kind");
            require_true(enact_list_head(result.as.as_list)->as.as_int == 1, "callableArityRange partial min");
            require_true(
                enact_list_head(enact_list_tail(result.as.as_list))->as.as_int == 1,
                "callableArityRange partial max");
            enact_value_free(&result);
            enact_diag_reset(&diag);
            require_true(
                enact_builtin_partial_apply(append_partial, &append_args[1], 1, &result, &diag),
                "append partial apply succeeds");
            require_true(result.kind == ENACT_VALUE_LIST, "append partial result kind");
            require_true(enact_list_head(result.as.as_list)->as.as_int == 1, "append partial first value");
            require_true(
                enact_list_head(enact_list_tail(result.as.as_list))->as.as_int == 2,
                "append partial second value");
            enact_value_free(&result);
            require_true(
                enact_builtin_partial_extend(append_partial, &append_args[1], 1) == NULL,
                "append partial exact extension fails");
            enact_value_free(&partial_copy);
            enact_value_free(&partial_value);
        }

        reduce_tail = enact_list_cons(&append_args[1], NULL);
        reduce_list = enact_list_cons(&append_args[0], reduce_tail);
        enact_list_release(reduce_tail);
        require_true(reduce_list != NULL, "reduce input list created");
        if (reduce_list) {
            reduce_args[0] = enact_value_make_builtin(append);
            reduce_args[1] = enact_value_make_list(NULL);
            reduce_args[2] = enact_value_make_list(reduce_list);
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(reduce, reduce_args, 3, &result, &diag), "reduce builtin apply succeeds");
            require_true(result.kind == ENACT_VALUE_LIST, "reduce builtin result kind");
            require_true(enact_list_head(result.as.as_list)->as.as_int == 1, "reduce builtin first value");
            require_true(enact_list_head(enact_list_tail(result.as.as_list))->as.as_int == 2, "reduce builtin second value");
            require_true(enact_list_tail(enact_list_tail(result.as.as_list)) == NULL, "reduce builtin tail nil");
            enact_value_free(&result);
            enact_value_free(&reduce_args[1]);
            enact_value_free(&reduce_args[2]);
        }

        enact_value_free(&append_args[0]);
        enact_value_free(&append_args[1]);
    }

    head = enact_value_make_int(1);
    inner_left_list = enact_list_cons(&head, NULL);
    head = enact_value_make_int(2);
    inner_right_list = enact_list_cons(&head, NULL);
    require_true(inner_left_list != NULL && inner_right_list != NULL, "map inner lists created");
    if (inner_left_list && inner_right_list) {
        inner_left_value = enact_value_make_list(inner_left_list);
        inner_right_value = enact_value_make_list(inner_right_list);
        outer_tail = enact_list_cons(&inner_right_value, NULL);
        outer_list = enact_list_cons(&inner_left_value, outer_tail);
        enact_value_free(&inner_left_value);
        enact_value_free(&inner_right_value);
        enact_list_release(outer_tail);
        require_true(outer_list != NULL, "map outer list created");
        if (outer_list) {
            map_args[0] = enact_value_make_builtin(size);
            map_args[1] = enact_value_make_list(outer_list);
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(map, map_args, 2, &result, &diag), "map builtin apply succeeds");
            require_true(result.kind == ENACT_VALUE_LIST, "map builtin result kind");
            require_true(enact_list_head(result.as.as_list)->as.as_int == 1, "map builtin first value");
            require_true(enact_list_head(enact_list_tail(result.as.as_list))->as.as_int == 1, "map builtin second value");
            require_true(enact_list_tail(enact_list_tail(result.as.as_list)) == NULL, "map builtin tail nil");
            enact_value_free(&result);
            enact_value_free(&map_args[1]);
        }
    }

    head = enact_value_make_bool(true);
    inner_true_list = enact_list_cons(&head, NULL);
    head = enact_value_make_bool(false);
    inner_false_list = enact_list_cons(&head, NULL);
    require_true(inner_true_list != NULL && inner_false_list != NULL, "predicate inner lists created");
    if (inner_true_list && inner_false_list) {
        inner_true_value = enact_value_make_list(inner_true_list);
        inner_false_value = enact_value_make_list(inner_false_list);
        predicate_tail = enact_list_cons(&inner_false_value, NULL);
        predicate_list = enact_list_cons(&inner_true_value, predicate_tail);
        enact_value_free(&inner_true_value);
        enact_value_free(&inner_false_value);
        enact_list_release(predicate_tail);
        require_true(predicate_list != NULL, "predicate outer list created");
        if (predicate_list) {
            predicate_args[0] = enact_value_make_builtin(hd);
            predicate_args[1] = enact_value_make_list(predicate_list);
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(filter, predicate_args, 2, &result, &diag), "filter builtin apply succeeds");
            require_true(result.kind == ENACT_VALUE_LIST, "filter builtin result kind");
            require_true(result.as.as_list != NULL, "filter builtin keeps one item");
            require_true(enact_list_head(result.as.as_list)->kind == ENACT_VALUE_LIST, "filter kept item kind");
            require_true(
                enact_list_head(enact_list_head(result.as.as_list)->as.as_list)->as.as_bool,
                "filter kept true-headed list");
            require_true(enact_list_tail(result.as.as_list) == NULL, "filter builtin result tail nil");
            enact_value_free(&result);

            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(all, predicate_args, 2, &result, &diag), "all builtin apply succeeds");
            require_true(result.kind == ENACT_VALUE_BOOL, "all builtin result kind");
            require_true(!result.as.as_bool, "all builtin result false");
            enact_value_free(&result);

            enact_diag_reset(&diag);
            require_true(
                enact_builtin_apply(exists, predicate_args, 2, &result, &diag),
                "exists builtin apply succeeds");
            require_true(result.kind == ENACT_VALUE_BOOL, "exists builtin result kind");
            require_true(result.as.as_bool, "exists builtin result true");
            enact_value_free(&result);

            enact_diag_reset(&diag);
            require_true(
                enact_builtin_apply(locate, predicate_args, 2, &result, &diag),
                "locate builtin apply succeeds");
            require_true(result.kind == ENACT_VALUE_LIST, "locate builtin result kind");
            require_true(result.as.as_list != NULL, "locate builtin found list item");
            require_true(enact_list_head(result.as.as_list)->kind == ENACT_VALUE_BOOL, "locate found item kind");
            require_true(
                enact_list_head(result.as.as_list)->as.as_bool,
                "locate found true-headed list");
            enact_value_free(&result);

            enact_diag_reset(&diag);
            require_true(
                enact_builtin_apply(for_each_do, predicate_args, 2, &result, &diag),
                "forEachDo builtin apply succeeds");
            require_true(result.kind == ENACT_VALUE_LIST, "forEachDo builtin result kind");
            require_true(result.as.as_list == NULL, "forEachDo builtin result nil");
            enact_value_free(&result);

            enact_value_free(&predicate_args[1]);
        }
    }

    predicate_args[0] = enact_value_make_builtin(hd);
    predicate_args[1] = enact_value_make_list(NULL);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(exists, predicate_args, 2, &result, &diag), "exists nil apply succeeds");
    require_true(result.kind == ENACT_VALUE_BOOL, "exists nil result kind");
    require_true(!result.as.as_bool, "exists nil result false");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(locate, predicate_args, 2, &result, &diag), "locate nil apply succeeds");
    require_true(result.kind == ENACT_VALUE_LIST, "locate nil result kind");
    require_true(result.as.as_list == NULL, "locate nil result nil");
    enact_value_free(&result);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(for_each_do, predicate_args, 2, &result, &diag), "forEachDo nil apply succeeds");
    require_true(result.kind == ENACT_VALUE_LIST, "forEachDo nil result kind");
    require_true(result.as.as_list == NULL, "forEachDo nil result nil");
    enact_value_free(&result);
    enact_value_free(&predicate_args[1]);

    args[0] = enact_value_make_bool(true);
    enact_diag_reset(&diag);
    require_true(!enact_builtin_apply(callable_arity, args, 1, &result, &diag), "callableArity non-callable fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_FUNCTION, "callableArity non-callable code");
    enact_diag_reset(&diag);
    require_true(
        !enact_builtin_apply(callable_min_arity, args, 1, &result, &diag),
        "callableMinArity non-callable fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_FUNCTION, "callableMinArity non-callable code");
    enact_diag_reset(&diag);
    require_true(!enact_builtin_apply(callable_params, args, 1, &result, &diag), "callableParams non-callable fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_FUNCTION, "callableParams non-callable code");
    enact_diag_reset(&diag);
    require_true(
        !enact_builtin_apply(callable_arity_range, args, 1, &result, &diag),
        "callableArityRange non-callable fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_FUNCTION, "callableArityRange non-callable code");
    enact_diag_reset(&diag);
    require_true(!enact_builtin_apply(hd, args, 1, &result, &diag), "hd non-list fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_LIST, "hd non-list error code");
    enact_diag_reset(&diag);
    require_true(!enact_builtin_apply(hd, NULL, 0, &result, &diag), "hd arity mismatch fails");
    require_true(diag.code == ENACT_ERR_ARITY_MISMATCH, "hd arity mismatch code");
    enact_diag_reset(&diag);
    require_true(!enact_builtin_apply(NULL, args, 1, &result, &diag), "null builtin apply fails");
    require_true(diag.code == ENACT_ERR_PARSE_UNEXPECTED_TOKEN, "null builtin apply code");
    enact_diag_reset(&diag);
    require_true(!enact_builtin_apply(hd, args, 1, NULL, &diag), "null builtin output fails");
    require_true(diag.code == ENACT_ERR_PARSE_UNEXPECTED_TOKEN, "null builtin output code");
    append_args[0] = enact_value_make_int(1);
    append_args[1] = enact_value_make_list(NULL);
    enact_diag_reset(&diag);
    require_true(!enact_builtin_apply(append, append_args, 2, &result, &diag), "append non-list left fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_LIST, "append non-list left code");
    enact_diag_reset(&diag);
    require_true(!enact_builtin_apply(append, append_args, 1, &result, &diag), "append wrong arity fails");
    require_true(diag.code == ENACT_ERR_ARITY_MISMATCH, "append wrong arity code");
    bad_prefix_args[0] = enact_value_make_int(1);
    append_partial = enact_builtin_partial_new(append, bad_prefix_args, 1);
    require_true(append_partial != NULL, "append bad prefix partial created");
    if (append_partial) {
        append_args[0] = enact_value_make_list(NULL);
        enact_diag_reset(&diag);
        require_true(
            !enact_builtin_partial_apply(append_partial, append_args, 1, &result, &diag),
            "append bad prefix partial apply fails");
        require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_LIST, "append bad prefix partial code");
        enact_builtin_partial_release(append_partial);
    }
    enact_diag_reset(&diag);
    require_true(
        !enact_builtin_partial_apply(NULL, append_args, 1, &result, &diag),
        "null partial apply fails");
    require_true(diag.code == ENACT_ERR_PARSE_UNEXPECTED_TOKEN, "null partial apply code");
    require_true(enact_builtin_partial_new(NULL, append_args, 1) == NULL, "partial new null builtin fails");
    require_true(enact_builtin_partial_new(set_builtin, append_args, 1) == NULL, "partial new set argument fails");
    require_true(enact_builtin_partial_new(size, append_args, 1) == NULL, "partial new exact arity fails");
    require_true(enact_builtin_partial_new(append, NULL, 1) == NULL, "partial new null args fails");

    enact_env_init(&env);
    require_true(enact_install_builtins(&env), "install builtins succeeds");
    require_true(enact_env_lookup(&env, "hd", &lookup_value), "lookup installed hd");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed hd value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "atom", &lookup_value), "lookup installed atom");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed atom value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "isObject", &lookup_value), "lookup installed isObject");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed isObject value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "isInt", &lookup_value), "lookup installed isInt");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed isInt value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "isBool", &lookup_value), "lookup installed isBool");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed isBool value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "isString", &lookup_value), "lookup installed isString");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed isString value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "isList", &lookup_value), "lookup installed isList");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed isList value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "isNil", &lookup_value), "lookup installed isNil");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed isNil value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "isEmpty", &lookup_value), "lookup installed isEmpty");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed isEmpty value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "isSymbol", &lookup_value), "lookup installed isSymbol");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed isSymbol value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "isClass", &lookup_value), "lookup installed isClass");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed isClass value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "isCallable", &lookup_value), "lookup installed isCallable");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed isCallable value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "isCollection", &lookup_value), "lookup installed isCollection");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed isCollection value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "isSet", &lookup_value), "lookup installed isSet");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed isSet value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "isBag", &lookup_value), "lookup installed isBag");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed isBag value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "classof", &lookup_value), "lookup installed classof");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed classof value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "attrs", &lookup_value), "lookup installed attrs");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed attrs value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "hasAttr", &lookup_value), "lookup installed hasAttr");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed hasAttr value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "methods", &lookup_value), "lookup installed methods");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed methods value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "effectiveMethods", &lookup_value), "lookup installed effectiveMethods");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed effectiveMethods value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "classes", &lookup_value), "lookup installed classes");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed classes value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "supers", &lookup_value), "lookup installed supers");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed supers value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "superiors", &lookup_value), "lookup installed superiors");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed superiors value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "suppliers", &lookup_value), "lookup installed suppliers");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed suppliers value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "methodSupplier", &lookup_value), "lookup installed methodSupplier");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed methodSupplier value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "hasMethod", &lookup_value), "lookup installed hasMethod");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed hasMethod value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "methodArity", &lookup_value), "lookup installed methodArity");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed methodArity value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "methodParams", &lookup_value), "lookup installed methodParams");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed methodParams value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "callableArity", &lookup_value), "lookup installed callableArity");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed callableArity value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "callableMinArity", &lookup_value), "lookup installed callableMinArity");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed callableMinArity value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "callableParams", &lookup_value), "lookup installed callableParams");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed callableParams value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "callableArityRange", &lookup_value), "lookup installed callableArityRange");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed callableArityRange value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "version", &lookup_value), "lookup installed version");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed version value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "time", &lookup_value), "lookup installed time");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed time value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "ask", &lookup_value), "lookup installed ask");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed ask value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "list", &lookup_value), "lookup installed list");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed list value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "set", &lookup_value), "lookup installed set");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed set value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "bag", &lookup_value), "lookup installed bag");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed bag value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "append", &lookup_value), "lookup installed append");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed append value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "size", &lookup_value), "lookup installed size");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed size value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "map", &lookup_value), "lookup installed map");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed map value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "collect", &lookup_value), "lookup installed collect");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed collect value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "filter", &lookup_value), "lookup installed filter");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed filter value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "select", &lookup_value), "lookup installed select");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed select value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "all", &lookup_value), "lookup installed all");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed all value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "exists", &lookup_value), "lookup installed exists");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed exists value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "locate", &lookup_value), "lookup installed locate");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed locate value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "forEachDo", &lookup_value), "lookup installed forEachDo");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed forEachDo value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "reduce", &lookup_value), "lookup installed reduce");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed reduce value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "member", &lookup_value), "lookup installed member");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed member value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "insert", &lookup_value), "lookup installed insert");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed insert value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "add", &lookup_value), "lookup installed add");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed add value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "remove", &lookup_value), "lookup installed remove");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed remove value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "unitset", &lookup_value), "lookup installed unitset");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed unitset value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "union", &lookup_value), "lookup installed union");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed union value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "UNION", &lookup_value), "lookup installed UNION");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed UNION value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "difference", &lookup_value), "lookup installed difference");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed difference value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "intersection", &lookup_value), "lookup installed intersection");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed intersection value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "subset", &lookup_value), "lookup installed subset");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed subset value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "equal", &lookup_value), "lookup installed equal");
    require_true(lookup_value.kind == ENACT_VALUE_BUILTIN, "installed equal value kind");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "Object", &lookup_value), "lookup installed Object");
    require_true(lookup_value.kind == ENACT_VALUE_CLASS, "installed Object value kind");
    require_true(strcmp(enact_class_name(lookup_value.as.as_class), "Object") == 0, "installed Object class name");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "Set", &lookup_value), "lookup installed Set");
    require_true(lookup_value.kind == ENACT_VALUE_CLASS, "installed Set value kind");
    require_true(strcmp(enact_class_name(lookup_value.as.as_class), "Set") == 0, "installed Set class name");
    require_true(
        strcmp(enact_class_name(enact_class_superclass(lookup_value.as.as_class)), "Object") == 0,
        "installed Set superclass name");
    enact_value_free(&lookup_value);
    require_true(enact_env_lookup(&env, "Bag", &lookup_value), "lookup installed Bag");
    require_true(lookup_value.kind == ENACT_VALUE_CLASS, "installed Bag value kind");
    require_true(strcmp(enact_class_name(lookup_value.as.as_class), "Bag") == 0, "installed Bag class name");
    require_true(
        strcmp(enact_class_name(enact_class_superclass(lookup_value.as.as_class)), "Object") == 0,
        "installed Bag superclass name");
    enact_value_free(&lookup_value);
    enact_diag_reset(&diag);
    require_true(
        enact_builtin_apply_in_env(set_builtin, &env, NULL, 0, &result, &diag),
        "set builtin env apply succeeds");
    require_true(result.kind == ENACT_VALUE_OBJECT, "set builtin result kind");
    require_true(strcmp(enact_class_name(enact_object_class(result.as.as_object)), "Set") == 0, "set object class name");
    require_true(
        enact_object_collection_kind(result.as.as_object) == ENACT_COLLECTION_SET,
        "set object collection kind");
    require_true(enact_object_collection_items(result.as.as_object) == NULL, "set object collection items nil");
    args[0] = result;
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_collection, args, 1, &lookup_value, &diag), "isCollection set apply succeeds");
    require_true(lookup_value.kind == ENACT_VALUE_BOOL, "isCollection set result kind");
    require_true(lookup_value.as.as_bool, "isCollection set result true");
    enact_value_free(&lookup_value);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_set, args, 1, &lookup_value, &diag), "isSet set apply succeeds");
    require_true(lookup_value.kind == ENACT_VALUE_BOOL, "isSet set result kind");
    require_true(lookup_value.as.as_bool, "isSet set result true");
    enact_value_free(&lookup_value);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_bag, args, 1, &lookup_value, &diag), "isBag set apply succeeds");
    require_true(lookup_value.kind == ENACT_VALUE_BOOL, "isBag set result kind");
    require_true(!lookup_value.as.as_bool, "isBag set result false");
    enact_value_free(&lookup_value);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_empty, args, 1, &lookup_value, &diag), "isEmpty set apply succeeds");
    require_true(lookup_value.kind == ENACT_VALUE_BOOL, "isEmpty set result kind");
    require_true(lookup_value.as.as_bool, "isEmpty set result true");
    enact_value_free(&lookup_value);
    {
        const EnactBuiltin *collection_builtin = NULL;
        size_t receiver_index = 999;

        require_true(
            enact_builtin_collection_method(
                ENACT_COLLECTION_SET,
                "isEmpty",
                &collection_builtin,
                &receiver_index),
            "isEmpty set collection method lookup succeeds");
        require_true(collection_builtin == is_empty, "isEmpty set collection method builtin");
        require_true(receiver_index == 0, "isEmpty set collection method receiver index");
    }
    {
        EnactValue query_args[2];
        EnactValue query_result;

        query_args[0] = result;
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(size, query_args, 1, &query_result, &diag), "size set object succeeds");
        require_true(query_result.kind == ENACT_VALUE_INT, "size set object result kind");
        require_true(query_result.as.as_int == 0, "size set object result value");
        enact_value_free(&query_result);

        query_args[0] = enact_value_make_int(1);
        query_args[1] = result;
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(member, query_args, 2, &query_result, &diag), "member set object succeeds");
        require_true(query_result.kind == ENACT_VALUE_BOOL, "member set object result kind");
        require_true(!query_result.as.as_bool, "member set object result false");
        enact_value_free(&query_result);

        query_args[0] = enact_value_make_int(1);
        query_args[1] = result;
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(insert, query_args, 2, &query_result, &diag), "insert set object succeeds");
        require_true(query_result.kind == ENACT_VALUE_OBJECT, "insert set result kind");
        require_true(
            enact_object_collection_kind(query_result.as.as_object) == ENACT_COLLECTION_SET,
            "insert set result collection kind");
        {
            EnactValue inserted_set = query_result;
            EnactValue duplicate_set;
            EnactValue removed_set;
            EnactValue size_result;

            query_args[0] = inserted_set;
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(size, query_args, 1, &size_result, &diag), "size inserted set succeeds");
            require_true(size_result.kind == ENACT_VALUE_INT, "size inserted set result kind");
            require_true(size_result.as.as_int == 1, "size inserted set result value");
            enact_value_free(&size_result);

            query_args[0] = enact_value_make_int(1);
            query_args[1] = inserted_set;
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(insert, query_args, 2, &duplicate_set, &diag), "insert duplicate set succeeds");
            require_true(duplicate_set.kind == ENACT_VALUE_OBJECT, "insert duplicate set result kind");
            query_args[0] = duplicate_set;
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(size, query_args, 1, &size_result, &diag), "size duplicate set succeeds");
            require_true(size_result.kind == ENACT_VALUE_INT, "size duplicate set result kind");
            require_true(size_result.as.as_int == 1, "size duplicate set result value");
            enact_value_free(&size_result);

            query_args[0] = enact_value_make_builtin(atom);
            query_args[1] = duplicate_set;
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(all, query_args, 2, &size_result, &diag), "all set object succeeds");
            require_true(size_result.kind == ENACT_VALUE_BOOL, "all set result kind");
            require_true(size_result.as.as_bool, "all set result true");
            enact_value_free(&size_result);

            query_args[0] = enact_value_make_builtin(is_object);
            query_args[1] = duplicate_set;
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(exists, query_args, 2, &size_result, &diag), "exists set object succeeds");
            require_true(size_result.kind == ENACT_VALUE_BOOL, "exists set result kind");
            require_true(!size_result.as.as_bool, "exists set result false");
            enact_value_free(&size_result);

            query_args[0] = enact_value_make_builtin(atom);
            query_args[1] = duplicate_set;
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(filter, query_args, 2, &size_result, &diag), "filter set object succeeds");
            require_true(size_result.kind == ENACT_VALUE_OBJECT, "filter set result kind");
            require_true(
                enact_object_collection_kind(size_result.as.as_object) == ENACT_COLLECTION_SET,
                "filter set result collection kind");
            enact_value_free(&size_result);

            query_args[0] = enact_value_make_builtin(is_object);
            query_args[1] = duplicate_set;
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(select, query_args, 2, &size_result, &diag), "select set object succeeds");
            require_true(size_result.kind == ENACT_VALUE_OBJECT, "select set result kind");
            query_args[0] = size_result;
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(size, query_args, 1, &removed_set, &diag), "size selected set succeeds");
            require_true(removed_set.kind == ENACT_VALUE_INT, "size selected set result kind");
            require_true(removed_set.as.as_int == 0, "size selected set result value");
            enact_value_free(&removed_set);
            enact_value_free(&size_result);

            query_args[0] = enact_value_make_int(1);
            query_args[1] = duplicate_set;
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(remove, query_args, 2, &removed_set, &diag), "remove set object succeeds");
            require_true(removed_set.kind == ENACT_VALUE_OBJECT, "remove set result kind");
            require_true(
                enact_object_collection_kind(removed_set.as.as_object) == ENACT_COLLECTION_SET,
                "remove set result collection kind");
            query_args[0] = removed_set;
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(size, query_args, 1, &size_result, &diag), "size removed set succeeds");
            require_true(size_result.kind == ENACT_VALUE_INT, "size removed set result kind");
            require_true(size_result.as.as_int == 0, "size removed set result value");
            enact_value_free(&size_result);
            enact_value_free(&removed_set);
            enact_value_free(&duplicate_set);
            enact_value_free(&inserted_set);
        }
    }
    enact_value_free(&result);
    {
        EnactValue constructor_args[1];
        EnactValue query_args[1];
        EnactValue size_result;
        EnactValue one = enact_value_make_int(1);
        EnactList *constructor_tail;
        EnactList *constructor_list;

        constructor_tail = enact_list_cons(&one, NULL);
        require_true(constructor_tail != NULL, "set constructor tail list created");
        constructor_list = enact_list_cons(&one, constructor_tail);
        enact_list_release(constructor_tail);
        require_true(constructor_list != NULL, "set constructor argument list created");
        constructor_args[0] = enact_value_make_list(constructor_list);

        enact_diag_reset(&diag);
        require_true(
            enact_builtin_apply_in_env(set_builtin, &env, constructor_args, 1, &result, &diag),
            "set builtin list env apply succeeds");
        require_true(result.kind == ENACT_VALUE_OBJECT, "set list constructor result kind");
        query_args[0] = result;
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(size, query_args, 1, &size_result, &diag), "size set list constructor succeeds");
        require_true(size_result.kind == ENACT_VALUE_INT, "size set list constructor result kind");
        require_true(size_result.as.as_int == 1, "size set list constructor suppresses duplicate");
        enact_value_free(&size_result);
        enact_value_free(&result);
        enact_value_free(&constructor_args[0]);
    }
    enact_diag_reset(&diag);
    require_true(
        enact_builtin_apply_in_env(bag_builtin, &env, NULL, 0, &result, &diag),
        "bag builtin env apply succeeds");
    require_true(result.kind == ENACT_VALUE_OBJECT, "bag builtin result kind");
    require_true(strcmp(enact_class_name(enact_object_class(result.as.as_object)), "Bag") == 0, "bag object class name");
    require_true(
        enact_object_collection_kind(result.as.as_object) == ENACT_COLLECTION_BAG,
        "bag object collection kind");
    require_true(enact_object_collection_items(result.as.as_object) == NULL, "bag object collection items nil");
    args[0] = result;
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_collection, args, 1, &lookup_value, &diag), "isCollection bag apply succeeds");
    require_true(lookup_value.kind == ENACT_VALUE_BOOL, "isCollection bag result kind");
    require_true(lookup_value.as.as_bool, "isCollection bag result true");
    enact_value_free(&lookup_value);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_set, args, 1, &lookup_value, &diag), "isSet bag apply succeeds");
    require_true(lookup_value.kind == ENACT_VALUE_BOOL, "isSet bag result kind");
    require_true(!lookup_value.as.as_bool, "isSet bag result false");
    enact_value_free(&lookup_value);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_bag, args, 1, &lookup_value, &diag), "isBag bag apply succeeds");
    require_true(lookup_value.kind == ENACT_VALUE_BOOL, "isBag bag result kind");
    require_true(lookup_value.as.as_bool, "isBag bag result true");
    enact_value_free(&lookup_value);
    enact_diag_reset(&diag);
    require_true(enact_builtin_apply(is_empty, args, 1, &lookup_value, &diag), "isEmpty bag apply succeeds");
    require_true(lookup_value.kind == ENACT_VALUE_BOOL, "isEmpty bag result kind");
    require_true(lookup_value.as.as_bool, "isEmpty bag result true");
    enact_value_free(&lookup_value);
    {
        const EnactBuiltin *collection_builtin = NULL;
        size_t receiver_index = 999;

        require_true(
            enact_builtin_collection_method(
                ENACT_COLLECTION_BAG,
                "isEmpty",
                &collection_builtin,
                &receiver_index),
            "isEmpty bag collection method lookup succeeds");
        require_true(collection_builtin == is_empty, "isEmpty bag collection method builtin");
        require_true(receiver_index == 0, "isEmpty bag collection method receiver index");
    }
    {
        EnactValue query_args[2];
        EnactValue query_result;

        query_args[0] = result;
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(size, query_args, 1, &query_result, &diag), "size bag object succeeds");
        require_true(query_result.kind == ENACT_VALUE_INT, "size bag object result kind");
        require_true(query_result.as.as_int == 0, "size bag object result value");
        enact_value_free(&query_result);

        query_args[0] = enact_value_make_int(1);
        query_args[1] = result;
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(member, query_args, 2, &query_result, &diag), "member bag object succeeds");
        require_true(query_result.kind == ENACT_VALUE_BOOL, "member bag object result kind");
        require_true(!query_result.as.as_bool, "member bag object result false");
        enact_value_free(&query_result);

        query_args[0] = enact_value_make_int(1);
        query_args[1] = result;
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(insert, query_args, 2, &query_result, &diag), "insert bag object succeeds");
        require_true(query_result.kind == ENACT_VALUE_OBJECT, "insert bag result kind");
        require_true(
            enact_object_collection_kind(query_result.as.as_object) == ENACT_COLLECTION_BAG,
            "insert bag result collection kind");
        {
            EnactValue inserted_bag = query_result;
            EnactValue duplicate_bag;
            EnactValue removed_bag;
            EnactValue size_result;

            query_args[0] = enact_value_make_int(1);
            query_args[1] = inserted_bag;
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(insert, query_args, 2, &duplicate_bag, &diag), "insert duplicate bag succeeds");
            require_true(duplicate_bag.kind == ENACT_VALUE_OBJECT, "insert duplicate bag result kind");
            query_args[0] = duplicate_bag;
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(size, query_args, 1, &size_result, &diag), "size duplicate bag succeeds");
            require_true(size_result.kind == ENACT_VALUE_INT, "size duplicate bag result kind");
            require_true(size_result.as.as_int == 2, "size duplicate bag result value");
            enact_value_free(&size_result);

            query_args[0] = enact_value_make_builtin(atom);
            query_args[1] = duplicate_bag;
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(all, query_args, 2, &size_result, &diag), "all bag object succeeds");
            require_true(size_result.kind == ENACT_VALUE_BOOL, "all bag result kind");
            require_true(size_result.as.as_bool, "all bag result true");
            enact_value_free(&size_result);

            query_args[0] = enact_value_make_builtin(is_object);
            query_args[1] = duplicate_bag;
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(exists, query_args, 2, &size_result, &diag), "exists bag object succeeds");
            require_true(size_result.kind == ENACT_VALUE_BOOL, "exists bag result kind");
            require_true(!size_result.as.as_bool, "exists bag result false");
            enact_value_free(&size_result);

            query_args[0] = enact_value_make_builtin(atom);
            query_args[1] = duplicate_bag;
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(filter, query_args, 2, &size_result, &diag), "filter bag object succeeds");
            require_true(size_result.kind == ENACT_VALUE_OBJECT, "filter bag result kind");
            require_true(
                enact_object_collection_kind(size_result.as.as_object) == ENACT_COLLECTION_BAG,
                "filter bag result collection kind");
            query_args[0] = size_result;
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(size, query_args, 1, &removed_bag, &diag), "size filtered bag succeeds");
            require_true(removed_bag.kind == ENACT_VALUE_INT, "size filtered bag result kind");
            require_true(removed_bag.as.as_int == 2, "size filtered bag result value");
            enact_value_free(&removed_bag);
            enact_value_free(&size_result);

            query_args[0] = enact_value_make_builtin(is_object);
            query_args[1] = duplicate_bag;
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(select, query_args, 2, &size_result, &diag), "select bag object succeeds");
            require_true(size_result.kind == ENACT_VALUE_OBJECT, "select bag result kind");
            query_args[0] = size_result;
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(size, query_args, 1, &removed_bag, &diag), "size selected bag succeeds");
            require_true(removed_bag.kind == ENACT_VALUE_INT, "size selected bag result kind");
            require_true(removed_bag.as.as_int == 0, "size selected bag result value");
            enact_value_free(&removed_bag);
            enact_value_free(&size_result);

            query_args[0] = enact_value_make_int(1);
            query_args[1] = duplicate_bag;
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(remove, query_args, 2, &removed_bag, &diag), "remove bag object succeeds");
            require_true(removed_bag.kind == ENACT_VALUE_OBJECT, "remove bag result kind");
            require_true(
                enact_object_collection_kind(removed_bag.as.as_object) == ENACT_COLLECTION_BAG,
                "remove bag result collection kind");
            query_args[0] = removed_bag;
            enact_diag_reset(&diag);
            require_true(enact_builtin_apply(size, query_args, 1, &size_result, &diag), "size removed bag succeeds");
            require_true(size_result.kind == ENACT_VALUE_INT, "size removed bag result kind");
            require_true(size_result.as.as_int == 1, "size removed bag result value");
            enact_value_free(&size_result);
            enact_value_free(&removed_bag);
            enact_value_free(&duplicate_bag);
            enact_value_free(&inserted_bag);
        }
    }
    enact_value_free(&result);
    {
        EnactValue constructor_args[1];
        EnactValue query_args[1];
        EnactValue size_result;
        EnactValue one = enact_value_make_int(1);
        EnactList *constructor_tail;
        EnactList *constructor_list;

        constructor_tail = enact_list_cons(&one, NULL);
        require_true(constructor_tail != NULL, "bag constructor tail list created");
        constructor_list = enact_list_cons(&one, constructor_tail);
        enact_list_release(constructor_tail);
        require_true(constructor_list != NULL, "bag constructor argument list created");
        constructor_args[0] = enact_value_make_list(constructor_list);

        enact_diag_reset(&diag);
        require_true(
            enact_builtin_apply_in_env(bag_builtin, &env, constructor_args, 1, &result, &diag),
            "bag builtin list env apply succeeds");
        require_true(result.kind == ENACT_VALUE_OBJECT, "bag list constructor result kind");
        query_args[0] = result;
        enact_diag_reset(&diag);
        require_true(enact_builtin_apply(size, query_args, 1, &size_result, &diag), "size bag list constructor succeeds");
        require_true(size_result.kind == ENACT_VALUE_INT, "size bag list constructor result kind");
        require_true(size_result.as.as_int == 2, "size bag list constructor preserves duplicate");
        enact_value_free(&size_result);
        enact_value_free(&result);
        enact_value_free(&constructor_args[0]);
    }
    enact_diag_reset(&diag);
    require_true(
        !enact_builtin_apply(set_builtin, NULL, 0, &result, &diag),
        "set builtin direct apply without env fails");
    require_true(diag.code == ENACT_ERR_NAME_UNBOUND, "set builtin direct apply error code");
    require_true(!enact_install_builtins(NULL), "install builtins null env fails");

    class_def = enact_ast_new_class_def(
        copy_test_name("Node"),
        make_test_ast_list1(enact_ast_new_identifier(copy_test_name("Object"))));
    require_true(class_def != NULL, "class def ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(class_def, &env, &result, &diag), "class def ast evaluates");
    require_true(result.kind == ENACT_VALUE_CLASS, "class def result kind");
    require_true(strcmp(enact_class_name(result.as.as_class), "Node") == 0, "class def result name");
    require_true(
        strcmp(enact_class_name(enact_class_superclass(result.as.as_class)), "Object") == 0,
        "class def superclass name");
    require_true(enact_env_lookup(&env, "Node", &lookup_value), "class def installs env binding");
    require_true(lookup_value.kind == ENACT_VALUE_CLASS, "class def env binding kind");
    require_true(lookup_value.as.as_class == result.as.as_class, "class def env binding identity");
    enact_value_free(&lookup_value);
    enact_value_free(&result);
    enact_ast_free(class_def);

    new_node = enact_ast_new_unary(AST_NEW, enact_ast_new_identifier(copy_test_name("Node")));
    require_true(new_node != NULL, "new subclass ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(new_node, &env, &result, &diag), "new subclass ast evaluates");
    require_true(result.kind == ENACT_VALUE_OBJECT, "new subclass result kind");
    require_true(
        strcmp(enact_class_name(enact_object_class(result.as.as_object)), "Node") == 0,
        "new subclass object class name");
    enact_value_free(&result);
    enact_ast_free(new_node);

    call = enact_ast_new_call(
        enact_ast_new_identifier(copy_test_name("hd")),
        make_test_ast_list1(enact_ast_new_binary(AST_CONS, enact_ast_new_int(12), enact_ast_new_nil())));
    require_true(call != NULL, "builtin ast call created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(call, &env, &result, &diag), "builtin ast call evaluates");
    require_true(result.kind == ENACT_VALUE_INT, "builtin ast call result kind");
    require_true(result.as.as_int == 12, "builtin ast call result value");
    enact_ast_free(call);

    call = enact_ast_new_call(
        enact_ast_new_identifier(copy_test_name("append")),
        make_test_ast_list2(
            enact_ast_new_binary(AST_CONS, enact_ast_new_int(1), enact_ast_new_nil()),
            enact_ast_new_binary(AST_CONS, enact_ast_new_int(2), enact_ast_new_nil())));
    require_true(call != NULL, "append builtin ast call created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(call, &env, &result, &diag), "append builtin ast call evaluates");
    require_true(result.kind == ENACT_VALUE_LIST, "append builtin ast call result kind");
    require_true(enact_list_head(result.as.as_list)->as.as_int == 1, "append ast first value");
    require_true(enact_list_head(enact_list_tail(result.as.as_list))->as.as_int == 2, "append ast second value");
    enact_value_free(&result);
    enact_ast_free(call);
    enact_env_free(&env);
}

static void test_env_helpers(void)
{
    EnactEnv env;
    EnactEnv clone;
    EnactValue value;
    EnactValue result;
    EnactDiag diag;
    EnactAst *identifier;
    EnactAst *left;
    EnactAst *right;
    EnactAst *sum;
    EnactAst *assignment;
    EnactAst *sequence;
    EnactAst *where_ast;
    EnactAst *function_body;
    EnactAst *function_literal;
    EnactAst *function_call;
    EnactNameList *params;
    EnactAstList *arguments;
    EnactValue string_binding;
    const char *env_input_lines[] = {"env line\n", "clone line\n"};
    TestInput env_input = {env_input_lines, 2, 0};
    char *input_line = NULL;

    enact_env_init(NULL);
    enact_env_free(NULL);
    require_true(!enact_env_clone(NULL, &env), "clone null out fails");
    require_true(!enact_env_clone(&clone, NULL), "clone null in fails");
    require_true(!enact_env_define(NULL, "x", enact_value_make_int(1)), "define null env fails");
    require_true(!enact_env_define(&env, NULL, enact_value_make_int(1)), "define null name fails");
    require_true(!enact_env_lookup(NULL, "x", &value), "lookup null env fails");
    require_true(!enact_env_lookup(&env, NULL, &value), "lookup null name fails");
    require_true(!enact_env_lookup(&env, "x", NULL), "lookup null out fails");

    enact_env_init(&env);
    require_true(!enact_env_lookup(&env, "missing", &value), "missing lookup fails");
    enact_diag_reset(&diag);
    require_true(!enact_env_read_input(&env, &input_line, &diag), "read input without provider fails");
    require_true(diag.code == ENACT_ERR_INPUT_UNAVAILABLE, "read input without provider code");
    enact_env_set_input_provider(&env, test_input_provider, &env_input);
    enact_diag_reset(&diag);
    require_true(enact_env_read_input(&env, &input_line, &diag), "read input with provider succeeds");
    require_true(strcmp(input_line, "env line\n") == 0, "read input value");
    free(input_line);
    input_line = NULL;

    require_true(enact_env_define(&env, "x", enact_value_make_int(7)), "define int binding");
    require_true(enact_env_lookup(&env, "x", &value), "lookup int binding");
    require_true(value.kind == ENACT_VALUE_INT, "lookup int kind");
    require_true(value.as.as_int == 7, "lookup int value");

    require_true(enact_env_define(&env, "flag", enact_value_make_bool(true)), "define bool binding");
    require_true(enact_env_lookup(&env, "flag", &value), "lookup bool binding");
    require_true(value.kind == ENACT_VALUE_BOOL, "lookup bool kind");
    require_true(value.as.as_bool, "lookup bool value");

    string_binding = enact_value_make_string(copy_test_name("text"));
    require_true(enact_env_define(&env, "s", string_binding), "define string binding");
    enact_value_free(&string_binding);
    require_true(enact_env_lookup(&env, "s", &value), "lookup string binding");
    require_true(value.kind == ENACT_VALUE_STRING, "lookup string kind");
    require_true(strcmp(value.as.as_string, "text") == 0, "lookup string value");
    enact_value_free(&value);

    require_true(enact_env_define(&env, "x", enact_value_make_int(9)), "redefine int binding");
    require_true(enact_env_lookup(&env, "x", &value), "lookup redefined int binding");
    require_true(value.as.as_int == 9, "redefined int value");

    require_true(enact_env_clone(&clone, &env), "clone env succeeds");
    enact_diag_reset(&diag);
    require_true(enact_env_read_input(&clone, &input_line, &diag), "read input from cloned provider succeeds");
    require_true(strcmp(input_line, "clone line\n") == 0, "cloned provider input value");
    free(input_line);
    input_line = NULL;
    require_true(enact_env_lookup(&clone, "x", &value), "lookup cloned int binding");
    require_true(value.kind == ENACT_VALUE_INT, "cloned int kind");
    require_true(value.as.as_int == 9, "cloned int value");
    require_true(enact_env_lookup(&clone, "s", &value), "lookup cloned string binding");
    require_true(value.kind == ENACT_VALUE_STRING, "cloned string kind");
    require_true(strcmp(value.as.as_string, "text") == 0, "cloned string value");
    enact_value_free(&value);
    require_true(enact_env_define(&clone, "x", enact_value_make_int(100)), "redefine cloned int binding");
    require_true(enact_env_lookup(&clone, "x", &value), "lookup redefined clone binding");
    require_true(value.as.as_int == 100, "redefined clone value");
    require_true(enact_env_lookup(&env, "x", &value), "lookup original after clone redefine");
    require_true(value.as.as_int == 9, "original unchanged after clone redefine");
    enact_env_free(&clone);

    identifier = enact_ast_new_identifier(copy_test_name("x"));
    require_true(identifier != NULL, "identifier ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(identifier, &env, &result, &diag), "identifier resolves through env");
    require_true(result.kind == ENACT_VALUE_INT, "identifier result kind");
    require_true(result.as.as_int == 9, "identifier result value");
    enact_ast_free(identifier);

    left = enact_ast_new_identifier(copy_test_name("x"));
    right = enact_ast_new_int(1);
    sum = enact_ast_new_binary(AST_ADD, left, right);
    require_true(left != NULL && right != NULL && sum != NULL, "identifier arithmetic ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(sum, &env, &result, &diag), "identifier arithmetic resolves through env");
    require_true(result.kind == ENACT_VALUE_INT, "identifier arithmetic result kind");
    require_true(result.as.as_int == 10, "identifier arithmetic result value");
    enact_ast_free(sum);

    assignment = enact_ast_new_assignment(copy_test_name("z"), enact_ast_new_int(5));
    require_true(assignment != NULL, "assignment ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(assignment, &env, &result, &diag), "assignment evaluates through env");
    require_true(result.kind == ENACT_VALUE_INT, "assignment result kind");
    require_true(result.as.as_int == 5, "assignment result value");
    require_true(enact_env_lookup(&env, "z", &value), "assignment defines env binding");
    require_true(value.kind == ENACT_VALUE_INT, "assignment env binding kind");
    require_true(value.as.as_int == 5, "assignment env binding value");
    enact_ast_free(assignment);

    left = enact_ast_new_assignment(copy_test_name("a"), enact_ast_new_int(1));
    right = enact_ast_new_binary(
        AST_ADD,
        enact_ast_new_identifier(copy_test_name("a")),
        enact_ast_new_int(2));
    sequence = enact_ast_new_binary(AST_SEQUENCE, left, right);
    require_true(left != NULL && right != NULL && sequence != NULL, "sequence ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(sequence, &env, &result, &diag), "sequence evaluates left then right");
    require_true(result.kind == ENACT_VALUE_INT, "sequence result kind");
    require_true(result.as.as_int == 3, "sequence result value");
    enact_ast_free(sequence);

    where_ast = enact_ast_new_where(
        enact_ast_new_identifier(copy_test_name("w")),
        copy_test_name("w"),
        enact_ast_new_int(4));
    require_true(where_ast != NULL, "where ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(where_ast, &env, &result, &diag), "where evaluates through local env");
    require_true(result.kind == ENACT_VALUE_INT, "where result kind");
    require_true(result.as.as_int == 4, "where result value");
    require_true(!enact_env_lookup(&env, "w", &value), "where binding does not leak");
    enact_ast_free(where_ast);

    function_body = enact_ast_new_binary(
        AST_ADD,
        enact_ast_new_identifier(copy_test_name("p")),
        enact_ast_new_int(1));
    {
        const char *names[] = {"p"};
        params = make_test_name_list(names, 1);
    }
    arguments = make_test_ast_list1(enact_ast_new_int(4));
    function_literal = enact_ast_new_function_literal(params, function_body);
    function_call = enact_ast_new_call(function_literal, arguments);
    require_true(params != NULL && arguments != NULL && function_body != NULL && function_literal != NULL && function_call != NULL, "function call ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(function_call, &env, &result, &diag), "function call evaluates through env");
    require_true(result.kind == ENACT_VALUE_INT, "function call result kind");
    require_true(result.as.as_int == 5, "function call result value");
    enact_ast_free(function_call);

    function_body = enact_ast_new_int(12);
    params = enact_name_list_new();
    arguments = enact_ast_list_new();
    function_literal = enact_ast_new_function_literal(params, function_body);
    function_call = enact_ast_new_call(function_literal, arguments);
    require_true(params != NULL && arguments != NULL && function_body != NULL && function_literal != NULL && function_call != NULL, "zero-argument function call ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(function_call, &env, &result, &diag), "zero-argument function call evaluates through env");
    require_true(result.kind == ENACT_VALUE_INT, "zero-argument function call result kind");
    require_true(result.as.as_int == 12, "zero-argument function call result value");
    enact_ast_free(function_call);

    function_body = enact_ast_new_binary(
        AST_ADD,
        enact_ast_new_identifier(copy_test_name("left")),
        enact_ast_new_identifier(copy_test_name("right")));
    {
        const char *names[] = {"left", "right"};
        params = make_test_name_list(names, 2);
    }
    arguments = make_test_ast_list2(enact_ast_new_int(2), enact_ast_new_int(3));
    function_literal = enact_ast_new_function_literal(params, function_body);
    function_call = enact_ast_new_call(function_literal, arguments);
    require_true(params != NULL && arguments != NULL && function_body != NULL && function_literal != NULL && function_call != NULL, "multi-argument function call ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(function_call, &env, &result, &diag), "multi-argument function call evaluates through env");
    require_true(result.kind == ENACT_VALUE_INT, "multi-argument function call result kind");
    require_true(result.as.as_int == 5, "multi-argument function call result value");
    enact_ast_free(function_call);

    function_body = enact_ast_new_binary(
        AST_ADD,
        enact_ast_new_identifier(copy_test_name("left")),
        enact_ast_new_identifier(copy_test_name("right")));
    {
        const char *names[] = {"left", "right"};
        params = make_test_name_list(names, 2);
    }
    arguments = make_test_ast_list1(enact_ast_new_int(2));
    function_literal = enact_ast_new_function_literal(params, function_body);
    function_call = enact_ast_new_call(function_literal, arguments);
    require_true(params != NULL && arguments != NULL && function_body != NULL && function_literal != NULL && function_call != NULL, "partial function call ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(function_call, &env, &result, &diag), "partial function call evaluates through env");
    require_true(result.kind == ENACT_VALUE_FUNCTION, "partial function call result kind");
    require_true(enact_function_arity(result.as.as_function) == 1, "partial function call result arity");
    require_true(strcmp(enact_function_param_name(result.as.as_function, 0), "right") == 0, "partial function call remaining param");
    enact_value_free(&result);
    enact_ast_free(function_call);

    function_body = enact_ast_new_identifier(copy_test_name("only"));
    {
        const char *names[] = {"only"};
        params = make_test_name_list(names, 1);
    }
    arguments = make_test_ast_list2(enact_ast_new_int(1), enact_ast_new_int(2));
    function_literal = enact_ast_new_function_literal(params, function_body);
    function_call = enact_ast_new_call(function_literal, arguments);
    require_true(params != NULL && arguments != NULL && function_body != NULL && function_literal != NULL && function_call != NULL, "arity mismatch call ast created");
    enact_diag_reset(&diag);
    require_true(!enact_eval_ast_with_env(function_call, &env, &result, &diag), "arity mismatch function call fails");
    require_true(diag.code == ENACT_ERR_ARITY_MISMATCH, "arity mismatch function call code");
    enact_ast_free(function_call);

    function_body = enact_ast_new_binary(
        AST_SEQUENCE,
        enact_ast_new_assignment(copy_test_name("x"), enact_ast_new_int(2)),
        enact_ast_new_identifier(copy_test_name("x")));
    {
        const char *names[] = {"x"};
        params = make_test_name_list(names, 1);
    }
    arguments = make_test_ast_list1(enact_ast_new_int(0));
    function_literal = enact_ast_new_function_literal(params, function_body);
    function_call = enact_ast_new_call(function_literal, arguments);
    require_true(params != NULL && arguments != NULL && function_body != NULL && function_literal != NULL && function_call != NULL, "function body assignment ast created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast_with_env(function_call, &env, &result, &diag), "function body assignment evaluates locally");
    require_true(result.kind == ENACT_VALUE_INT, "function body assignment result kind");
    require_true(result.as.as_int == 2, "function body assignment result value");
    require_true(enact_env_lookup(&env, "x", &value), "lookup outer after function body assignment");
    require_true(value.as.as_int == 9, "function body assignment does not leak");
    enact_ast_free(function_call);

    identifier = enact_ast_new_identifier(copy_test_name("missing"));
    require_true(identifier != NULL, "missing identifier ast created");
    enact_diag_reset(&diag);
    require_true(!enact_eval_ast_with_env(identifier, &env, &result, &diag), "missing identifier fails");
    require_true(diag.code == ENACT_ERR_NAME_UNBOUND, "missing identifier code");
    enact_ast_free(identifier);

    enact_env_free(&env);
}

static void test_ast_clone_helpers(void)
{
    EnactAst unknown = {0};
    EnactAst *original;
    EnactAst *clone;
    EnactValue value;
    EnactDiag diag;
    EnactNameList *params;
    EnactAstList *arguments;

    require_true(enact_ast_clone(NULL) == NULL, "clone null ast fails");
    unknown.kind = (EnactAstKind)99;
    require_true(enact_ast_clone(&unknown) == NULL, "clone unknown ast fails");

    original = enact_ast_new_string(NULL);
    require_true(original != NULL, "null string clone source created");
    clone = enact_ast_clone(original);
    require_true(clone != NULL, "null string clone created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(clone, &value, &diag), "null string clone evaluates");
    require_true(value.kind == ENACT_VALUE_STRING, "null string clone result kind");
    require_true(strcmp(value.as.as_string, "") == 0, "null string clone result value");
    enact_value_free(&value);
    enact_ast_free(clone);
    enact_ast_free(original);

    original = enact_ast_new_atom(NULL);
    require_true(original != NULL, "null atom clone source created");
    clone = enact_ast_clone(original);
    require_true(clone != NULL, "null atom clone created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(clone, &value, &diag), "null atom clone evaluates");
    require_true(value.kind == ENACT_VALUE_ATOM, "null atom clone result kind");
    require_true(strcmp(value.as.as_atom, "") == 0, "null atom clone result value");
    enact_value_free(&value);
    enact_ast_free(clone);
    enact_ast_free(original);

    original = enact_ast_new_nil();
    require_true(original != NULL, "nil clone source created");
    clone = enact_ast_clone(original);
    require_true(clone != NULL, "nil clone created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(clone, &value, &diag), "nil clone evaluates");
    require_true(value.kind == ENACT_VALUE_LIST, "nil clone result kind");
    require_true(value.as.as_list == NULL, "nil clone result value");
    enact_value_free(&value);
    enact_ast_free(clone);
    enact_ast_free(original);

    original = enact_ast_new_unary(AST_NEW, enact_ast_new_identifier(copy_test_name("Object")));
    require_true(original != NULL, "new Object clone source created");
    clone = enact_ast_clone(original);
    require_true(clone != NULL, "new Object clone created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(clone, &value, &diag), "new Object clone evaluates");
    require_true(value.kind == ENACT_VALUE_OBJECT, "new Object clone result kind");
    require_true(
        strcmp(enact_class_name(enact_object_class(value.as.as_object)), "Object") == 0,
        "new Object clone result class");
    enact_value_free(&value);
    enact_ast_free(clone);
    enact_ast_free(original);

    original = enact_ast_new_class_def(
        copy_test_name("Node"),
        make_test_ast_list1(enact_ast_new_identifier(copy_test_name("Object"))));
    require_true(original != NULL, "class def clone source created");
    clone = enact_ast_clone(original);
    require_true(clone != NULL, "class def clone created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(clone, &value, &diag), "class def clone evaluates");
    require_true(value.kind == ENACT_VALUE_CLASS, "class def clone result kind");
    require_true(strcmp(enact_class_name(value.as.as_class), "Node") == 0, "class def clone result name");
    require_true(
        strcmp(enact_class_name(enact_class_superclass(value.as.as_class)), "Object") == 0,
        "class def clone superclass");
    enact_value_free(&value);
    enact_ast_free(clone);
    enact_ast_free(original);

    params = make_test_name_list(NULL, 0);
    original = enact_ast_new_method_def(
        enact_ast_new_identifier(copy_test_name("Object")),
        copy_test_name("one"),
        params,
        enact_ast_new_int(1));
    require_true(params != NULL && original != NULL, "method def clone source created");
    clone = enact_ast_clone(original);
    require_true(clone != NULL, "method def clone created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(clone, &value, &diag), "method def clone evaluates");
    require_true(value.kind == ENACT_VALUE_FUNCTION, "method def clone result kind");
    enact_value_free(&value);
    enact_ast_free(clone);
    enact_ast_free(original);

    original = enact_ast_new_attribute(
        enact_ast_new_with(
            enact_ast_new_unary(AST_NEW, enact_ast_new_identifier(copy_test_name("Object"))),
            copy_test_name("x"),
            enact_ast_new_int(42)),
        copy_test_name("x"));
    require_true(original != NULL, "attribute clone source created");
    clone = enact_ast_clone(original);
    require_true(clone != NULL, "attribute clone created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(clone, &value, &diag), "attribute clone evaluates");
    require_true(value.kind == ENACT_VALUE_INT, "attribute clone result kind");
    require_true(value.as.as_int == 42, "attribute clone result value");
    enact_ast_free(clone);
    enact_ast_free(original);

    original = enact_ast_new_attribute_assignment(
        enact_ast_new_with(
            enact_ast_new_unary(AST_NEW, enact_ast_new_identifier(copy_test_name("Object"))),
            copy_test_name("x"),
            enact_ast_new_int(42)),
        copy_test_name("x"),
        enact_ast_new_int(43));
    require_true(original != NULL, "attribute assignment clone source created");
    clone = enact_ast_clone(original);
    require_true(clone != NULL, "attribute assignment clone created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(clone, &value, &diag), "attribute assignment clone evaluates");
    require_true(value.kind == ENACT_VALUE_INT, "attribute assignment clone result kind");
    require_true(value.as.as_int == 43, "attribute assignment clone result value");
    enact_ast_free(clone);
    enact_ast_free(original);

    original = enact_ast_new_binary(AST_CONS, enact_ast_new_int(1), enact_ast_new_nil());
    require_true(original != NULL, "cons clone source created");
    clone = enact_ast_clone(original);
    require_true(clone != NULL, "cons clone created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(clone, &value, &diag), "cons clone evaluates");
    require_true(value.kind == ENACT_VALUE_LIST, "cons clone result kind");
    require_true(enact_list_head(value.as.as_list)->as.as_int == 1, "cons clone head value");
    enact_value_free(&value);
    enact_ast_free(clone);
    enact_ast_free(original);

    original = enact_ast_new_conditional(
        enact_ast_new_bool(1),
        enact_ast_new_string(copy_test_name("yes")),
        enact_ast_new_string(copy_test_name("no")));
    require_true(original != NULL, "conditional clone source created");
    clone = enact_ast_clone(original);
    require_true(clone != NULL, "conditional clone created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(clone, &value, &diag), "conditional clone evaluates");
    require_true(value.kind == ENACT_VALUE_STRING, "conditional clone result kind");
    require_true(strcmp(value.as.as_string, "yes") == 0, "conditional clone result value");
    enact_value_free(&value);
    enact_ast_free(clone);
    enact_ast_free(original);

    {
        const char *names[] = {"x"};
        params = make_test_name_list(names, 1);
    }
    original = enact_ast_new_function_literal(
        params,
        enact_ast_new_identifier(copy_test_name("x")));
    require_true(original != NULL, "function literal clone source created");
    clone = enact_ast_clone(original);
    require_true(clone != NULL, "function literal clone created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(clone, &value, &diag), "function literal clone evaluates");
    require_true(value.kind == ENACT_VALUE_FUNCTION, "function literal clone result kind");
    enact_value_free(&value);
    enact_ast_free(clone);
    enact_ast_free(original);

    {
        const char *names[] = {"x"};
        params = make_test_name_list(names, 1);
    }
    arguments = make_test_ast_list1(enact_ast_new_int(7));
    original = enact_ast_new_call(
        enact_ast_new_function_literal(params, enact_ast_new_identifier(copy_test_name("x"))),
        arguments);
    require_true(params != NULL && arguments != NULL && original != NULL, "call clone source created");
    clone = enact_ast_clone(original);
    require_true(clone != NULL, "call clone created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(clone, &value, &diag), "call clone evaluates");
    require_true(value.kind == ENACT_VALUE_INT, "call clone result kind");
    require_true(value.as.as_int == 7, "call clone result value");
    enact_ast_free(clone);
    enact_ast_free(original);

    {
        const char *fix_names[] = {"f"};
        const char *param_names[] = {"x"};
        EnactNameList *fixed = make_test_name_list(fix_names, 1);

        params = make_test_name_list(param_names, 1);
        original = enact_ast_new_fix(
            fixed,
            enact_ast_new_assignment(
                copy_test_name("f"),
                enact_ast_new_function_literal(
                    params,
                    enact_ast_new_identifier(copy_test_name("x")))));
    }
    require_true(original != NULL, "fix clone source created");
    clone = enact_ast_clone(original);
    require_true(clone != NULL, "fix clone created");
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(clone, &value, &diag), "fix clone evaluates");
    require_true(value.kind == ENACT_VALUE_FUNCTION, "fix clone result kind");
    enact_value_free(&value);
    enact_ast_free(clone);
    enact_ast_free(original);
}

static void test_parser_state_helpers(void)
{
    EnactParseContext context;
    EnactScannerState state;

    memset(&context, 0, sizeof(context));
    memset(&state, 0, sizeof(state));
    enact_set_parse_context(&context);
    enact_set_scanner_state(&state);
    require_true(enact_get_parse_context() == &context, "get parse context");
    require_true(enact_get_scanner_state() == &state, "get scanner state");
    enact_parse_context_take_root(NULL);
    enact_set_parse_context(NULL);
    enact_set_scanner_state(NULL);
    enact_parse_context_take_root(NULL);
    require_true(enact_get_parse_context() == NULL, "clear parse context");
    require_true(enact_get_scanner_state() == NULL, "clear scanner state");
}

static void test_eval_edge_cases(void)
{
    EnactDiag diag;
    EnactValue value;
    EnactAst bogus = {0};
    EnactAst int_node = {0};
    EnactAst unary_node = {0};
    EnactAst int_one = {0};
    EnactAst int_zero = {0};
    EnactAst int_seven = {0};
    EnactAst bool_true = {0};
    EnactAst bool_false = {0};
    EnactAst string_node = {0};
    EnactAst atom_node = {0};
    EnactAst object_identifier = {0};
    EnactAst new_node = {0};
    EnactAst eq_node = {0};
    EnactAst neq_node = {0};
    EnactAst lt_node = {0};
    EnactAst add_node = {0};
    EnactAst div_node = {0};
    EnactAst mod_node = {0};
    EnactAst and_node = {0};
    EnactAst or_node = {0};
    EnactAst not_node = {0};
    EnactAst conditional_node = {0};
    EnactAst *call_node;

    enact_diag_reset(&diag);
    require_true(!enact_eval_ast(NULL, &value, &diag), "null ast fails");
    require_true(diag.code == ENACT_ERR_PARSE_UNEXPECTED_TOKEN, "null ast error code");

    enact_diag_reset(&diag);
    require_true(!enact_eval_ast(&bogus, NULL, &diag), "null value fails");
    require_true(diag.code == ENACT_ERR_PARSE_UNEXPECTED_TOKEN, "null value error code");

    bogus.kind = (EnactAstKind)99;
    enact_diag_reset(&diag);
    require_true(!enact_eval_ast(&bogus, &value, &diag), "bogus ast fails");
    require_true(diag.code == ENACT_ERR_PARSE_UNEXPECTED_TOKEN, "bogus ast error code");

    int_node.kind = AST_INT_LITERAL;
    int_node.as.int_magnitude = 2147483648ULL;
    enact_diag_reset(&diag);
    require_true(!enact_eval_ast(&int_node, &value, &diag), "literal overflow fails");
    require_true(diag.code == ENACT_ERR_INT_OVERFLOW, "literal overflow code");

    unary_node.kind = AST_UNARY_NEG;
    unary_node.as.unary.child = &int_node;
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(&unary_node, &value, &diag), "int32 min unary case succeeds");
    require_true(value.kind == ENACT_VALUE_INT, "int32 min kind");
    require_true(value.as.as_int == INT32_MIN, "int32 min value");

    int_one.kind = AST_INT_LITERAL;
    int_one.as.int_magnitude = 1;
    int_zero.kind = AST_INT_LITERAL;
    int_zero.as.int_magnitude = 0;
    int_seven.kind = AST_INT_LITERAL;
    int_seven.as.int_magnitude = 7;
    bool_true.kind = AST_BOOL_LITERAL;
    bool_true.as.bool_value = 1;
    bool_false.kind = AST_BOOL_LITERAL;
    bool_false.as.bool_value = 0;
    string_node.kind = AST_STRING_LITERAL;
    string_node.as.string_value = "unit";
    atom_node.kind = AST_ATOM_LITERAL;
    atom_node.as.atom_value = "unit";
    object_identifier.kind = AST_IDENTIFIER;
    object_identifier.as.identifier_name = "Object";

    eq_node.kind = AST_EQ;
    eq_node.as.binary.left = &bool_true;
    eq_node.as.binary.right = &int_one;
    enact_diag_reset(&diag);
    require_true(!enact_eval_ast(&eq_node, &value, &diag), "equality mismatch fails");
    require_true(diag.code == ENACT_ERR_TYPE_EQUALITY_MISMATCH, "equality mismatch code");

    eq_node.as.binary.left = &string_node;
    eq_node.as.binary.right = &string_node;
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(&eq_node, &value, &diag), "string equality succeeds");
    require_true(value.kind == ENACT_VALUE_BOOL, "string equality kind");
    require_true(value.as.as_bool, "string equality value");

    neq_node.kind = AST_NEQ;
    neq_node.as.binary.left = &bool_true;
    neq_node.as.binary.right = &bool_false;
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(&neq_node, &value, &diag), "bool inequality succeeds");
    require_true(value.kind == ENACT_VALUE_BOOL, "bool inequality kind");
    require_true(value.as.as_bool, "bool inequality value");

    lt_node.kind = AST_LT;
    lt_node.as.binary.left = &int_zero;
    lt_node.as.binary.right = &int_one;
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(&lt_node, &value, &diag), "integer less-than succeeds");
    require_true(value.kind == ENACT_VALUE_BOOL, "integer less-than kind");
    require_true(value.as.as_bool, "integer less-than value");

    lt_node.as.binary.left = &bool_false;
    lt_node.as.binary.right = &bool_true;
    enact_diag_reset(&diag);
    require_true(!enact_eval_ast(&lt_node, &value, &diag), "bool ordering fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_INT, "bool ordering code");

    not_node.kind = AST_NOT;
    not_node.as.unary.child = &int_one;
    enact_diag_reset(&diag);
    require_true(!enact_eval_ast(&not_node, &value, &diag), "not int fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_BOOL, "not int code");

    add_node.kind = AST_ADD;
    add_node.as.binary.left = &bool_true;
    add_node.as.binary.right = &int_one;
    enact_diag_reset(&diag);
    require_true(!enact_eval_ast(&add_node, &value, &diag), "bool arithmetic fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_INT, "bool arithmetic code");

    div_node.kind = AST_DIV;
    div_node.as.binary.left = &int_one;
    div_node.as.binary.right = &int_zero;

    mod_node.kind = AST_MOD;
    mod_node.as.binary.left = &int_seven;
    mod_node.as.binary.right = &int_one;
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(&mod_node, &value, &diag), "mod succeeds");
    require_true(value.kind == ENACT_VALUE_INT, "mod result kind");
    require_true(value.as.as_int == 0, "mod result value");

    and_node.kind = AST_AND;
    and_node.as.binary.left = &bool_false;
    and_node.as.binary.right = &div_node;
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(&and_node, &value, &diag), "and short-circuits false");
    require_true(value.kind == ENACT_VALUE_BOOL, "and short-circuit kind");
    require_true(!value.as.as_bool, "and short-circuit value");

    or_node.kind = AST_OR;
    or_node.as.binary.left = &bool_true;
    or_node.as.binary.right = &div_node;
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(&or_node, &value, &diag), "or short-circuits true");
    require_true(value.kind == ENACT_VALUE_BOOL, "or short-circuit kind");
    require_true(value.as.as_bool, "or short-circuit value");

    conditional_node.kind = AST_IF_ELSE;
    conditional_node.as.conditional.condition = &bool_true;
    conditional_node.as.conditional.if_true = &int_seven;
    conditional_node.as.conditional.if_false = &div_node;
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(&conditional_node, &value, &diag), "conditional skips false branch");
    require_true(value.kind == ENACT_VALUE_INT, "conditional selected kind");
    require_true(value.as.as_int == 7, "conditional selected value");

    new_node.kind = AST_NEW;
    new_node.as.unary.child = &object_identifier;
    enact_diag_reset(&diag);
    require_true(enact_eval_ast(&new_node, &value, &diag), "new Object ast succeeds");
    require_true(value.kind == ENACT_VALUE_OBJECT, "new Object ast result kind");
    require_true(
        strcmp(enact_class_name(enact_object_class(value.as.as_object)), "Object") == 0,
        "new Object ast class name");
    enact_value_free(&value);

    new_node.as.unary.child = &int_one;
    enact_diag_reset(&diag);
    require_true(!enact_eval_ast(&new_node, &value, &diag), "new non-class ast fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_CLASS, "new non-class ast code");

    call_node = enact_ast_new_call(enact_ast_new_int(1), make_test_ast_list1(enact_ast_new_int(0)));
    require_true(call_node != NULL, "non-function call ast created");
    enact_diag_reset(&diag);
    require_true(!enact_eval_ast(call_node, &value, &diag), "non-function call fails");
    require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_FUNCTION, "non-function call code");
    enact_ast_free(call_node);

    enact_diag_reset(&diag);
    require_true(enact_eval_ast(&string_node, &value, &diag), "string literal ast succeeds");
    require_true(value.kind == ENACT_VALUE_STRING, "string literal ast kind");
    require_true(strcmp(value.as.as_string, "unit") == 0, "string literal ast value");
    enact_value_free(&value);

    enact_diag_reset(&diag);
    require_true(enact_eval_ast(&atom_node, &value, &diag), "atom literal ast succeeds");
    require_true(value.kind == ENACT_VALUE_ATOM, "atom literal ast kind");
    require_true(strcmp(value.as.as_atom, "unit") == 0, "atom literal ast value");
    enact_value_free(&value);
}

static void test_api_and_scan_helpers(void)
{
    EnactResult result;
    EnactResult stateless_result;
    EnactSession session;
    EnactSession bye_session;
    ScriptCapture capture;
    EnactDiag diag;
    EnactList *list;
    const EnactValue *head;
    EnactValue callable_arg;
    EnactValue applied;
    EnactValue non_callable;
    const char *session_ask_lines[] = {"session one\n", "session two\r\n", "closure line\n"};
    TestInput session_ask_input = {session_ask_lines, 3, 0};
    FILE *tmp;
    FILE *load_file;
    const char *load_path = "/tmp/enact_unit_load_script.en";
    char load_command[256];
    char output[256];
    size_t nread;

    result = enact_eval_text(NULL);
    require_true(!result.ok, "null source parse fails");
    require_true(result.error.code == ENACT_ERR_PARSE_MISSING_DOT, "null source missing dot");
    enact_result_free(&result);

    result = enact_eval_text(")");
    require_true(!result.ok, "unexpected token parse fails");
    require_true(result.error.code == ENACT_ERR_PARSE_UNMATCHED_PAREN, "unexpected token code");
    enact_result_free(&result);

    require_true(!enact_session_init(NULL), "session init null fails");
    enact_session_free(NULL);
    result = enact_session_eval_text(NULL, "1.");
    require_true(!result.ok, "session eval null session fails");
    require_true(result.error.code == ENACT_ERR_PARSE_UNEXPECTED_TOKEN, "session eval null session code");
    enact_result_free(&result);

    require_true(enact_session_init(&session), "session init succeeds");
    enact_session_set_input_provider(NULL, test_input_provider, &session_ask_input);
    enact_session_set_input_provider(&session, test_input_provider, &session_ask_input);

    result = enact_session_eval_text(&session, "version().");
    require_true(result.ok, "session has installed builtins");
    require_true(result.value.kind == ENACT_VALUE_STRING, "session builtin result kind");
    require_true(strcmp(result.value.as.as_string, "enact-auto 0.1.0") == 0, "session builtin result value");
    enact_result_free(&result);

    result = enact_session_eval_text(&session, "ask().");
    require_true(result.ok, "session ask succeeds");
    require_true(result.value.kind == ENACT_VALUE_STRING, "session ask result kind");
    require_true(strcmp(result.value.as.as_string, "session one") == 0, "session ask strips newline");
    enact_result_free(&result);

    memset(&capture, 0, sizeof(capture));
    enact_diag_reset(&diag);
    require_true(
        enact_session_eval_script(&session, "ask()\nasker:=()::ask()\nasker()\n", script_capture_result, &capture, &diag),
        "session script ask and closure ask succeed");
    require_true(capture.count == 3, "session script ask result count");
    require_true(capture.values[0].kind == ENACT_VALUE_STRING, "session script ask result kind");
    require_true(strcmp(capture.values[0].as.as_string, "session two") == 0, "session script ask strips CRLF");
    require_true(capture.values[1].kind == ENACT_VALUE_FUNCTION, "session script asker definition kind");
    require_true(capture.values[2].kind == ENACT_VALUE_STRING, "session script closure ask result kind");
    require_true(strcmp(capture.values[2].as.as_string, "closure line") == 0, "session script closure ask value");
    script_capture_free(&capture);

    result = enact_session_eval_text(&session, "ask().");
    require_true(!result.ok, "session ask EOF fails");
    require_true(result.error.code == ENACT_ERR_INPUT_UNAVAILABLE, "session ask EOF code");
    enact_result_free(&result);

    result = enact_session_eval_text(&session, "x:=1.");
    require_true(result.ok, "session assignment succeeds");
    require_true(result.value.kind == ENACT_VALUE_INT, "session assignment result kind");
    require_true(result.value.as.as_int == 1, "session assignment result value");
    enact_result_free(&result);

    result = enact_session_eval_text(&session, "x+2.");
    require_true(result.ok, "session binding persists");
    require_true(result.value.kind == ENACT_VALUE_INT, "session persisted result kind");
    require_true(result.value.as.as_int == 3, "session persisted result value");
    enact_result_free(&result);

    result = enact_session_eval_text(&session, "missing.");
    require_true(!result.ok, "session eval failure reports error");
    require_true(result.error.code == ENACT_ERR_NAME_UNBOUND, "session eval failure code");
    enact_result_free(&result);

    result = enact_session_eval_text(&session, "x.");
    require_true(result.ok, "session survives eval failure");
    require_true(result.value.kind == ENACT_VALUE_INT, "session survives failure result kind");
    require_true(result.value.as.as_int == 1, "session survives failure result value");
    enact_result_free(&result);

    result = enact_session_eval_text(&session, "base:=10.");
    require_true(result.ok, "session base assignment succeeds");
    enact_result_free(&result);
    result = enact_session_eval_text(&session, "add_base(y):=base+y.");
    require_true(result.ok, "session function definition succeeds");
    enact_result_free(&result);
    result = enact_session_eval_text(&session, "base:=20.");
    require_true(result.ok, "session rebinding succeeds");
    enact_result_free(&result);
    result = enact_session_eval_text(&session, "add_base(1).");
    require_true(result.ok, "session function captures definition env");
    require_true(result.value.kind == ENACT_VALUE_INT, "session captured function result kind");
    require_true(result.value.as.as_int == 11, "session captured function result value");
    enact_result_free(&result);

    memset(&capture, 0, sizeof(capture));
    enact_diag_reset(&diag);
    require_true(
        enact_session_eval_script(&session, "script_x:=1.\nscript_x+2.", script_capture_result, &capture, &diag),
        "session script evaluates multiple chunks");
    require_true(capture.count == 2, "session script result count");
    require_true(capture.values[0].kind == ENACT_VALUE_INT, "session script first kind");
    require_true(capture.values[0].as.as_int == 1, "session script first value");
    require_true(capture.values[1].kind == ENACT_VALUE_INT, "session script second kind");
    require_true(capture.values[1].as.as_int == 3, "session script second value");
    script_capture_free(&capture);

    memset(&capture, 0, sizeof(capture));
    enact_diag_reset(&diag);
    require_true(
        enact_session_eval_script(&session, "nl_unit:=6\nnl_unit+1\n", script_capture_result, &capture, &diag),
        "session script accepts newline terminators");
    require_true(capture.count == 2, "session script newline result count");
    require_true(capture.values[0].kind == ENACT_VALUE_INT, "session script newline first kind");
    require_true(capture.values[0].as.as_int == 6, "session script newline first value");
    require_true(capture.values[1].kind == ENACT_VALUE_INT, "session script newline second kind");
    require_true(capture.values[1].as.as_int == 7, "session script newline second value");
    script_capture_free(&capture);

    memset(&capture, 0, sizeof(capture));
    enact_diag_reset(&diag);
    require_true(
        enact_session_eval_script(
            &session,
            "class AttrNode < Object\nattr_n:=new AttrNode with x:=17\nattr_n.x\n",
            script_capture_result,
            &capture,
            &diag),
        "session script accepts dot attribute access");
    require_true(capture.count == 3, "session script attribute result count");
    require_true(capture.values[0].kind == ENACT_VALUE_CLASS, "session script attribute class kind");
    require_true(capture.values[1].kind == ENACT_VALUE_OBJECT, "session script attribute object kind");
    require_true(capture.values[2].kind == ENACT_VALUE_INT, "session script attribute value kind");
    require_true(capture.values[2].as.as_int == 17, "session script attribute value");
    script_capture_free(&capture);

    memset(&capture, 0, sizeof(capture));
    enact_diag_reset(&diag);
    require_true(
        enact_session_eval_script(
            &session,
            "class AssignNode < Object\nassign_n:=new AssignNode with x:=1\nassign_n.x:=2\nassign_n.x\n",
            script_capture_result,
            &capture,
            &diag),
        "session script accepts dot attribute assignment");
    require_true(capture.count == 4, "session script attribute assignment result count");
    require_true(capture.values[0].kind == ENACT_VALUE_CLASS, "session script attribute assignment class kind");
    require_true(capture.values[1].kind == ENACT_VALUE_OBJECT, "session script attribute assignment object kind");
    require_true(capture.values[2].kind == ENACT_VALUE_INT, "session script attribute assignment write kind");
    require_true(capture.values[2].as.as_int == 2, "session script attribute assignment write value");
    require_true(capture.values[3].kind == ENACT_VALUE_INT, "session script attribute assignment read kind");
    require_true(capture.values[3].as.as_int == 2, "session script attribute assignment read value");
    script_capture_free(&capture);

    memset(&capture, 0, sizeof(capture));
    enact_diag_reset(&diag);
    require_true(
        enact_session_eval_script(
            &session,
            "class MethodNode < Object\nMethodNode.set(v):=self.x:=v\nmethod_n:=new MethodNode\nmethod_n.set(12)\nmethod_n.x\n",
            script_capture_result,
            &capture,
            &diag),
        "session script accepts method definition and dispatch");
    require_true(capture.count == 5, "session script method result count");
    require_true(capture.values[0].kind == ENACT_VALUE_CLASS, "session script method class kind");
    require_true(capture.values[1].kind == ENACT_VALUE_FUNCTION, "session script method def kind");
    require_true(capture.values[2].kind == ENACT_VALUE_OBJECT, "session script method object kind");
    require_true(capture.values[3].kind == ENACT_VALUE_INT, "session script method write kind");
    require_true(capture.values[3].as.as_int == 12, "session script method write value");
    require_true(capture.values[4].kind == ENACT_VALUE_INT, "session script method read kind");
    require_true(capture.values[4].as.as_int == 12, "session script method read value");
    script_capture_free(&capture);

    result = enact_session_eval_text(&session, "script_x+3.");
    require_true(result.ok, "session script leaves bindings");
    require_true(result.value.kind == ENACT_VALUE_INT, "session script binding result kind");
    require_true(result.value.as.as_int == 4, "session script binding result value");
    enact_result_free(&result);

    memset(&capture, 0, sizeof(capture));
    enact_diag_reset(&diag);
    require_true(
        enact_session_eval_script(&session, "   % only a comment\n  ", script_capture_result, &capture, &diag),
        "session script accepts trivia-only input");
    require_true(capture.count == 0, "session script trivia-only result count");
    script_capture_free(&capture);

    enact_diag_reset(&diag);
    require_true(
        !enact_session_eval_script(&session, "1.", script_reject_result, NULL, &diag),
        "session script callback failure fails");
    require_true(diag.code == ENACT_ERR_PARSE_UNEXPECTED_TOKEN, "session script callback failure code");

    enact_diag_reset(&diag);
    require_true(
        !enact_session_eval_script(NULL, "1.", script_capture_result, &capture, &diag),
        "session script null session fails");
    require_true(diag.code == ENACT_ERR_PARSE_UNEXPECTED_TOKEN, "session script null session code");

    enact_diag_reset(&diag);
    require_true(
        !enact_session_eval_script(&session, "script_y:=missing.\nscript_x.", script_capture_result, &capture, &diag),
        "session script stops on failure");
    require_true(diag.code == ENACT_ERR_NAME_UNBOUND, "session script failure code");

    result = enact_session_eval_text(&session, "script_x.");
    require_true(result.ok, "session script survives script failure");
    require_true(result.value.kind == ENACT_VALUE_INT, "session script survives failure kind");
    require_true(result.value.as.as_int == 1, "session script survives failure value");
    enact_result_free(&result);

    load_file = fopen(load_path, "w");
    require_true(load_file != NULL, "session load file created");
    if (load_file) {
        fprintf(load_file, "load_unit:=40.\nload_unit+2.");
        fclose(load_file);

        snprintf(load_command, sizeof(load_command), "load \"%s\".", load_path);
        memset(&capture, 0, sizeof(capture));
        enact_diag_reset(&diag);
        require_true(
            enact_session_eval_script(&session, load_command, script_capture_result, &capture, &diag),
            "session script load command succeeds");
        require_true(capture.count == 2, "session script load result count");
        require_true(capture.values[0].kind == ENACT_VALUE_INT, "session script load first kind");
        require_true(capture.values[0].as.as_int == 40, "session script load first value");
        require_true(capture.values[1].kind == ENACT_VALUE_INT, "session script load second kind");
        require_true(capture.values[1].as.as_int == 42, "session script load second value");
        script_capture_free(&capture);

        result = enact_session_eval_text(&session, "load_unit+1.");
        require_true(result.ok, "session script load leaves bindings");
        require_true(result.value.kind == ENACT_VALUE_INT, "session script loaded binding kind");
        require_true(result.value.as.as_int == 41, "session script loaded binding value");
        enact_result_free(&result);

        result = enact_session_eval_text(&session, load_command);
        require_true(!result.ok, "session eval text does not execute load command");
        require_true(result.error.code == ENACT_ERR_PARSE_UNEXPECTED_TOKEN, "session eval text load command code");
        enact_result_free(&result);

        remove(load_path);
    }

    require_true(enact_session_init(&bye_session), "bye session init succeeds");
    require_true(!enact_session_exit_requested(&bye_session), "bye session starts active");

    enact_diag_reset(&diag);
    require_true(
        !enact_session_eval_script(&bye_session, "bye 1\n", script_capture_result, &capture, &diag),
        "bye command rejects trailing expression");
    require_true(diag.code == ENACT_ERR_PARSE_UNEXPECTED_TOKEN, "bye command trailing expression code");
    require_true(!enact_session_exit_requested(&bye_session), "bad bye command does not request exit");

    result = enact_session_eval_text(&bye_session, "bye.");
    require_true(!result.ok, "session eval text does not execute bye command");
    require_true(result.error.code == ENACT_ERR_NAME_UNBOUND, "session eval text bye command code");
    enact_result_free(&result);

    memset(&capture, 0, sizeof(capture));
    enact_diag_reset(&diag);
    require_true(
        enact_session_eval_script(&bye_session, "bye\n1\n", script_capture_result, &capture, &diag),
        "bye command succeeds");
    require_true(capture.count == 0, "bye command produces no result");
    require_true(enact_session_exit_requested(&bye_session), "bye command requests exit");
    script_capture_free(&capture);

    memset(&capture, 0, sizeof(capture));
    enact_diag_reset(&diag);
    require_true(
        enact_session_eval_script(&bye_session, "1\n", script_capture_result, &capture, &diag),
        "exited bye session ignores later script chunks");
    require_true(capture.count == 0, "exited bye session later result count");
    script_capture_free(&capture);
    enact_session_free(&bye_session);

    stateless_result = enact_eval_text("solo:=9.");
    require_true(stateless_result.ok, "stateless assignment succeeds");
    enact_result_free(&stateless_result);
    stateless_result = enact_eval_text("solo.");
    require_true(!stateless_result.ok, "stateless eval does not persist binding");
    require_true(stateless_result.error.code == ENACT_ERR_NAME_UNBOUND, "stateless eval unbound code");
    enact_result_free(&stateless_result);

    enact_session_free(&session);
    result = enact_session_eval_text(&session, "x.");
    require_true(!result.ok, "session eval after free fails");
    require_true(result.error.code == ENACT_ERR_PARSE_UNEXPECTED_TOKEN, "session eval after free code");
    enact_result_free(&result);
    enact_session_free(&session);

    tmp = tmpfile();
    require_true(tmp != NULL, "tmpfile created");
    if (!tmp) {
        return;
    }

    enact_diag_reset(&diag);
    require_true(enact_dump_tokens_text(NULL, tmp, &diag) == 0, "token dump null source");
    rewind(tmp);
    memset(output, 0, sizeof(output));
    nread = fread(output, 1, sizeof(output) - 1, tmp);
    output[nread] = '\0';
    require_true(strcmp(output, "TOK_EOF\n") == 0, "token dump null source stdout");

    freopen(NULL, "w+", tmp);
    enact_diag_reset(&diag);
    require_true(enact_dump_tokens_text("$", tmp, &diag) != 0, "token dump invalid char fails");
    require_true(diag.code == ENACT_ERR_LEX_INVALID_CHAR, "token dump invalid char code");

    freopen(NULL, "w+", tmp);
    require_true(enact_dump_tokens_text("% comment\n1.", tmp, NULL) == 0, "token dump null diag succeeds");
    rewind(tmp);
    memset(output, 0, sizeof(output));
    nread = fread(output, 1, sizeof(output) - 1, tmp);
    output[nread] = '\0';
    require_true(strcmp(output, "TOK_INT_LITERAL TOK_DOT TOK_EOF\n") == 0, "token dump null diag stdout");

    result = enact_eval_text("(1,2,3).");
    require_true(result.ok, "tuple-like list eval succeeds");
    require_true(result.value.kind == ENACT_VALUE_LIST, "tuple-like list result kind");
    if (result.ok && result.value.kind == ENACT_VALUE_LIST) {
        list = result.value.as.as_list;
        head = enact_list_head(list);
        require_true(head != NULL && head->kind == ENACT_VALUE_INT && head->as.as_int == 1, "tuple-like list first element");
        list = enact_list_tail(list);
        head = enact_list_head(list);
        require_true(head != NULL && head->kind == ENACT_VALUE_INT && head->as.as_int == 2, "tuple-like list second element");
        list = enact_list_tail(list);
        head = enact_list_head(list);
        require_true(head != NULL && head->kind == ENACT_VALUE_INT && head->as.as_int == 3, "tuple-like list third element");
        require_true(enact_list_tail(list) == NULL, "tuple-like list terminates with nil");
    }
    enact_result_free(&result);

    result = enact_eval_text("x::x+1.");
    require_true(result.ok, "callable helper source evaluates");
    if (result.ok) {
        callable_arg = enact_value_make_int(4);
        enact_diag_reset(&diag);
        require_true(
            enact_eval_apply_callable(&result.value, &callable_arg, 1, &applied, &diag),
            "callable helper applies function");
        require_true(applied.kind == ENACT_VALUE_INT, "callable helper result kind");
        require_true(applied.as.as_int == 5, "callable helper result value");
        enact_value_free(&applied);

        non_callable = enact_value_make_int(1);
        enact_diag_reset(&diag);
        require_true(
            !enact_eval_apply_callable(&non_callable, &callable_arg, 1, &applied, &diag),
            "callable helper rejects non-function");
        require_true(diag.code == ENACT_ERR_TYPE_EXPECTED_FUNCTION, "callable helper non-function code");
    }
    enact_result_free(&result);

    result = enact_eval_text("()::7.");
    require_true(result.ok, "zero-argument callable source evaluates");
    if (result.ok) {
        enact_diag_reset(&diag);
        require_true(
            enact_eval_apply_callable(&result.value, NULL, 0, &applied, &diag),
            "callable helper applies zero-argument function");
        require_true(applied.kind == ENACT_VALUE_INT, "zero-argument callable result kind");
        require_true(applied.as.as_int == 7, "zero-argument callable result value");
        enact_value_free(&applied);

        callable_arg = enact_value_make_int(4);
        enact_diag_reset(&diag);
        require_true(
            !enact_eval_apply_callable(&result.value, &callable_arg, 1, &applied, &diag),
            "callable helper rejects extra argument for zero-argument function");
        require_true(diag.code == ENACT_ERR_ARITY_MISMATCH, "zero-argument callable extra argument code");
    }
    enact_result_free(&result);
    fclose(tmp);
}

int main(void)
{
    test_runtime_stats_helpers();
    test_diag_helpers();
    test_value_helpers();
    test_builtin_helpers();
    test_env_helpers();
    test_ast_clone_helpers();
    test_parser_state_helpers();
    test_eval_edge_cases();
    test_api_and_scan_helpers();

    if (failures != 0) {
        return 1;
    }

    puts("unit tests passed");
    return 0;
}
