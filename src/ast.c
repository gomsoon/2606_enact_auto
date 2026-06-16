#include <stdlib.h>
#include <string.h>

#include "ast.h"

static EnactAst *enact_ast_alloc(EnactAstKind kind)
{
    EnactAst *ast = calloc(1, sizeof(*ast));
    if (!ast) {
        return NULL;
    }

    ast->kind = kind;
    ast->span.start_offset = -1;
    ast->span.end_offset = -1;
    return ast;
}

static char *enact_ast_copy_text(const char *text)
{
    size_t length;
    char *copy;

    if (!text) {
        text = "";
    }

    length = strlen(text);
    copy = malloc(length + 1);
    if (!copy) {
        return NULL;
    }

    memcpy(copy, text, length + 1);
    return copy;
}

static int enact_name_list_reserve(EnactNameList *list, size_t needed)
{
    char **grown;
    size_t capacity;

    if (!list) {
        return 0;
    }
    if (list->capacity >= needed) {
        return 1;
    }

    capacity = list->capacity == 0 ? 4 : list->capacity;
    while (capacity < needed) {
        capacity *= 2;
    }

    grown = realloc(list->items, capacity * sizeof(*grown));
    if (!grown) {
        return 0;
    }

    list->items = grown;
    list->capacity = capacity;
    return 1;
}

static int enact_ast_list_reserve(EnactAstList *list, size_t needed)
{
    EnactAst **grown;
    size_t capacity;

    if (!list) {
        return 0;
    }
    if (list->capacity >= needed) {
        return 1;
    }

    capacity = list->capacity == 0 ? 4 : list->capacity;
    while (capacity < needed) {
        capacity *= 2;
    }

    grown = realloc(list->items, capacity * sizeof(*grown));
    if (!grown) {
        return 0;
    }

    list->items = grown;
    list->capacity = capacity;
    return 1;
}

EnactNameList *enact_name_list_new(void)
{
    return calloc(1, sizeof(EnactNameList));
}

int enact_name_list_append(EnactNameList *list, char *name)
{
    if (!list || !name) {
        return 0;
    }

    if (!enact_name_list_reserve(list, list->count + 1)) {
        return 0;
    }

    list->items[list->count] = name;
    list->count += 1;
    return 1;
}

EnactNameList *enact_name_list_clone(const EnactNameList *list)
{
    EnactNameList *copy;
    size_t index;

    if (!list) {
        return NULL;
    }

    copy = enact_name_list_new();
    if (!copy) {
        return NULL;
    }

    for (index = 0; index < list->count; index += 1) {
        char *name = enact_ast_copy_text(list->items[index]);

        if (!name || !enact_name_list_append(copy, name)) {
            free(name);
            enact_name_list_free(copy);
            return NULL;
        }
    }

    return copy;
}

size_t enact_name_list_count(const EnactNameList *list)
{
    return list ? list->count : 0;
}

const char *enact_name_list_get(const EnactNameList *list, size_t index)
{
    if (!list || index >= list->count) {
        return "";
    }

    return list->items[index];
}

int enact_name_list_contains(const EnactNameList *list, const char *name)
{
    size_t index;

    if (!list || !name) {
        return 0;
    }

    for (index = 0; index < list->count; index += 1) {
        if (strcmp(list->items[index], name) == 0) {
            return 1;
        }
    }

    return 0;
}

void enact_name_list_free(EnactNameList *list)
{
    size_t index;

    if (!list) {
        return;
    }

    for (index = 0; index < list->count; index += 1) {
        free(list->items[index]);
    }
    free(list->items);
    free(list);
}

EnactAstList *enact_ast_list_new(void)
{
    return calloc(1, sizeof(EnactAstList));
}

int enact_ast_list_append(EnactAstList *list, EnactAst *ast)
{
    if (!list || !ast) {
        return 0;
    }

    if (!enact_ast_list_reserve(list, list->count + 1)) {
        return 0;
    }

    list->items[list->count] = ast;
    list->count += 1;
    return 1;
}

EnactAstList *enact_ast_list_clone(const EnactAstList *list)
{
    EnactAstList *copy;
    size_t index;

    if (!list) {
        return NULL;
    }

    copy = enact_ast_list_new();
    if (!copy) {
        return NULL;
    }

    for (index = 0; index < list->count; index += 1) {
        EnactAst *ast = enact_ast_clone(list->items[index]);

        if (!ast || !enact_ast_list_append(copy, ast)) {
            enact_ast_free(ast);
            enact_ast_list_free(copy);
            return NULL;
        }
    }

    return copy;
}

size_t enact_ast_list_count(const EnactAstList *list)
{
    return list ? list->count : 0;
}

EnactAst *enact_ast_list_get(const EnactAstList *list, size_t index)
{
    if (!list || index >= list->count) {
        return NULL;
    }

    return list->items[index];
}

void enact_ast_list_free(EnactAstList *list)
{
    size_t index;

    if (!list) {
        return;
    }

    for (index = 0; index < list->count; index += 1) {
        enact_ast_free(list->items[index]);
    }
    free(list->items);
    free(list);
}

EnactAst *enact_ast_new_int(uint64_t int_magnitude)
{
    EnactAst *ast = enact_ast_alloc(AST_INT_LITERAL);
    if (!ast) {
        return NULL;
    }

    ast->as.int_magnitude = int_magnitude;
    return ast;
}

EnactAst *enact_ast_new_bool(int bool_value)
{
    EnactAst *ast = enact_ast_alloc(AST_BOOL_LITERAL);
    if (!ast) {
        return NULL;
    }

    ast->as.bool_value = bool_value != 0;
    return ast;
}

EnactAst *enact_ast_new_string(char *value)
{
    EnactAst *ast = enact_ast_alloc(AST_STRING_LITERAL);
    if (!ast) {
        return NULL;
    }

    ast->as.string_value = value;
    return ast;
}

EnactAst *enact_ast_new_nil(void)
{
    return enact_ast_alloc(AST_NIL);
}

EnactAst *enact_ast_new_identifier(char *name)
{
    EnactAst *ast = enact_ast_alloc(AST_IDENTIFIER);
    if (!ast) {
        return NULL;
    }

    ast->as.identifier_name = name;
    return ast;
}

EnactAst *enact_ast_new_unary(EnactAstKind kind, EnactAst *child)
{
    EnactAst *ast = enact_ast_alloc(kind);
    if (!ast) {
        return NULL;
    }

    ast->as.unary.child = child;
    return ast;
}

EnactAst *enact_ast_new_binary(EnactAstKind kind, EnactAst *left, EnactAst *right)
{
    EnactAst *ast = enact_ast_alloc(kind);
    if (!ast) {
        return NULL;
    }

    ast->as.binary.left = left;
    ast->as.binary.right = right;
    return ast;
}

EnactAst *enact_ast_new_conditional(EnactAst *condition, EnactAst *if_true, EnactAst *if_false)
{
    EnactAst *ast = enact_ast_alloc(AST_IF_ELSE);
    if (!ast) {
        return NULL;
    }

    ast->as.conditional.condition = condition;
    ast->as.conditional.if_true = if_true;
    ast->as.conditional.if_false = if_false;
    return ast;
}

EnactAst *enact_ast_new_where(EnactAst *body, char *name, EnactAst *value)
{
    EnactAst *ast = enact_ast_alloc(AST_WHERE);
    if (!ast) {
        return NULL;
    }

    ast->as.where_expr.body = body;
    ast->as.where_expr.name = name;
    ast->as.where_expr.value = value;
    return ast;
}

EnactAst *enact_ast_new_fix(EnactNameList *names, EnactAst *body)
{
    EnactAst *ast = enact_ast_alloc(AST_FIX);
    if (!ast) {
        return NULL;
    }

    ast->as.fix_expr.names = names;
    ast->as.fix_expr.body = body;
    return ast;
}

static EnactAst *enact_ast_new_assignment_with_flag(char *name, EnactAst *value, int recursive_function)
{
    EnactAst *ast = enact_ast_alloc(AST_ASSIGN);
    if (!ast) {
        return NULL;
    }

    ast->as.assignment.name = name;
    ast->as.assignment.value = value;
    ast->as.assignment.recursive_function = recursive_function;
    return ast;
}

EnactAst *enact_ast_new_assignment(char *name, EnactAst *value)
{
    return enact_ast_new_assignment_with_flag(name, value, 0);
}

EnactAst *enact_ast_new_recursive_assignment(char *name, EnactAst *value)
{
    return enact_ast_new_assignment_with_flag(name, value, 1);
}

EnactAst *enact_ast_new_function_literal(EnactNameList *param_names, EnactAst *body)
{
    EnactAst *ast = enact_ast_alloc(AST_FUNCTION_LITERAL);
    if (!ast) {
        return NULL;
    }

    ast->as.function_literal.param_names = param_names;
    ast->as.function_literal.body = body;
    return ast;
}

EnactAst *enact_ast_new_call(EnactAst *callee, EnactAstList *arguments)
{
    EnactAst *ast = enact_ast_alloc(AST_CALL);
    if (!ast) {
        return NULL;
    }

    ast->as.call.callee = callee;
    ast->as.call.arguments = arguments;
    return ast;
}

static EnactAst *enact_ast_clone_unary(const EnactAst *ast)
{
    EnactAst *child = enact_ast_clone(ast->as.unary.child);
    EnactAst *copy;

    if (!child) {
        return NULL;
    }

    copy = enact_ast_new_unary(ast->kind, child);
    if (!copy) {
        enact_ast_free(child);
        return NULL;
    }

    return copy;
}

static EnactAst *enact_ast_clone_binary(const EnactAst *ast)
{
    EnactAst *left = enact_ast_clone(ast->as.binary.left);
    EnactAst *right;
    EnactAst *copy;

    if (!left) {
        return NULL;
    }

    right = enact_ast_clone(ast->as.binary.right);
    if (!right) {
        enact_ast_free(left);
        return NULL;
    }

    copy = enact_ast_new_binary(ast->kind, left, right);
    if (!copy) {
        enact_ast_free(left);
        enact_ast_free(right);
        return NULL;
    }

    return copy;
}

static EnactAst *enact_ast_clone_conditional(const EnactAst *ast)
{
    EnactAst *condition = enact_ast_clone(ast->as.conditional.condition);
    EnactAst *if_true;
    EnactAst *if_false;
    EnactAst *copy;

    if (!condition) {
        return NULL;
    }

    if_true = enact_ast_clone(ast->as.conditional.if_true);
    if (!if_true) {
        enact_ast_free(condition);
        return NULL;
    }

    if_false = enact_ast_clone(ast->as.conditional.if_false);
    if (!if_false) {
        enact_ast_free(condition);
        enact_ast_free(if_true);
        return NULL;
    }

    copy = enact_ast_new_conditional(condition, if_true, if_false);
    if (!copy) {
        enact_ast_free(condition);
        enact_ast_free(if_true);
        enact_ast_free(if_false);
        return NULL;
    }

    return copy;
}

static EnactAst *enact_ast_clone_where(const EnactAst *ast)
{
    EnactAst *body = enact_ast_clone(ast->as.where_expr.body);
    EnactAst *value;
    char *name;
    EnactAst *copy;

    if (!body) {
        return NULL;
    }

    name = enact_ast_copy_text(ast->as.where_expr.name);
    if (!name) {
        enact_ast_free(body);
        return NULL;
    }

    value = enact_ast_clone(ast->as.where_expr.value);
    if (!value) {
        enact_ast_free(body);
        free(name);
        return NULL;
    }

    copy = enact_ast_new_where(body, name, value);
    if (!copy) {
        enact_ast_free(body);
        free(name);
        enact_ast_free(value);
        return NULL;
    }

    return copy;
}

static EnactAst *enact_ast_clone_fix(const EnactAst *ast)
{
    EnactNameList *names = enact_name_list_clone(ast->as.fix_expr.names);
    EnactAst *body;
    EnactAst *copy;

    if (!names) {
        return NULL;
    }

    body = enact_ast_clone(ast->as.fix_expr.body);
    if (!body) {
        enact_name_list_free(names);
        return NULL;
    }

    copy = enact_ast_new_fix(names, body);
    if (!copy) {
        enact_name_list_free(names);
        enact_ast_free(body);
        return NULL;
    }

    return copy;
}

static EnactAst *enact_ast_clone_assignment(const EnactAst *ast)
{
    char *name = enact_ast_copy_text(ast->as.assignment.name);
    EnactAst *value;
    EnactAst *copy;

    if (!name) {
        return NULL;
    }

    value = enact_ast_clone(ast->as.assignment.value);
    if (!value) {
        free(name);
        return NULL;
    }

    copy = enact_ast_new_assignment_with_flag(name, value, ast->as.assignment.recursive_function);
    if (!copy) {
        free(name);
        enact_ast_free(value);
        return NULL;
    }

    return copy;
}

static EnactAst *enact_ast_clone_function_literal(const EnactAst *ast)
{
    EnactNameList *param_names = enact_name_list_clone(ast->as.function_literal.param_names);
    EnactAst *body;
    EnactAst *copy;

    if (!param_names) {
        return NULL;
    }

    body = enact_ast_clone(ast->as.function_literal.body);
    if (!body) {
        enact_name_list_free(param_names);
        return NULL;
    }

    copy = enact_ast_new_function_literal(param_names, body);
    if (!copy) {
        enact_name_list_free(param_names);
        enact_ast_free(body);
        return NULL;
    }

    return copy;
}

static EnactAst *enact_ast_clone_call(const EnactAst *ast)
{
    EnactAst *callee = enact_ast_clone(ast->as.call.callee);
    EnactAstList *arguments;
    EnactAst *copy;

    if (!callee) {
        return NULL;
    }

    arguments = enact_ast_list_clone(ast->as.call.arguments);
    if (!arguments) {
        enact_ast_free(callee);
        return NULL;
    }

    copy = enact_ast_new_call(callee, arguments);
    if (!copy) {
        enact_ast_free(callee);
        enact_ast_list_free(arguments);
        return NULL;
    }

    return copy;
}

EnactAst *enact_ast_clone(const EnactAst *ast)
{
    EnactAst *copy = NULL;
    char *text;

    if (!ast) {
        return NULL;
    }

    switch (ast->kind) {
    case AST_INT_LITERAL:
        copy = enact_ast_new_int(ast->as.int_magnitude);
        break;
    case AST_BOOL_LITERAL:
        copy = enact_ast_new_bool(ast->as.bool_value);
        break;
    case AST_STRING_LITERAL:
        text = enact_ast_copy_text(ast->as.string_value);
        if (!text) {
            return NULL;
        }
        copy = enact_ast_new_string(text);
        if (!copy) {
            free(text);
        }
        break;
    case AST_NIL:
        copy = enact_ast_new_nil();
        break;
    case AST_IDENTIFIER:
        text = enact_ast_copy_text(ast->as.identifier_name);
        if (!text) {
            return NULL;
        }
        copy = enact_ast_new_identifier(text);
        if (!copy) {
            free(text);
        }
        break;
    case AST_GROUP:
    case AST_UNARY_NEG:
    case AST_NOT:
        copy = enact_ast_clone_unary(ast);
        break;
    case AST_ADD:
    case AST_SUB:
    case AST_MUL:
    case AST_DIV:
    case AST_MOD:
    case AST_EQ:
    case AST_NEQ:
    case AST_LT:
    case AST_GT:
    case AST_LTE:
    case AST_GTE:
    case AST_CONS:
    case AST_AND:
    case AST_OR:
    case AST_SEQUENCE:
        copy = enact_ast_clone_binary(ast);
        break;
    case AST_CALL:
        copy = enact_ast_clone_call(ast);
        break;
    case AST_IF_ELSE:
        copy = enact_ast_clone_conditional(ast);
        break;
    case AST_WHERE:
        copy = enact_ast_clone_where(ast);
        break;
    case AST_FIX:
        copy = enact_ast_clone_fix(ast);
        break;
    case AST_ASSIGN:
        copy = enact_ast_clone_assignment(ast);
        break;
    case AST_FUNCTION_LITERAL:
        copy = enact_ast_clone_function_literal(ast);
        break;
    }

    if (copy) {
        copy->span = ast->span;
    }

    return copy;
}

void enact_ast_free(EnactAst *ast)
{
    if (!ast) {
        return;
    }

    switch (ast->kind) {
    case AST_INT_LITERAL:
    case AST_BOOL_LITERAL:
    case AST_NIL:
        break;
    case AST_STRING_LITERAL:
        free(ast->as.string_value);
        break;
    case AST_IDENTIFIER:
        free(ast->as.identifier_name);
        break;
    case AST_GROUP:
    case AST_UNARY_NEG:
    case AST_NOT:
        enact_ast_free(ast->as.unary.child);
        break;
    case AST_ADD:
    case AST_SUB:
    case AST_MUL:
    case AST_DIV:
    case AST_MOD:
    case AST_EQ:
    case AST_NEQ:
    case AST_LT:
    case AST_GT:
    case AST_LTE:
    case AST_GTE:
    case AST_CONS:
    case AST_AND:
    case AST_OR:
    case AST_SEQUENCE:
        enact_ast_free(ast->as.binary.left);
        enact_ast_free(ast->as.binary.right);
        break;
    case AST_CALL:
        enact_ast_free(ast->as.call.callee);
        enact_ast_list_free(ast->as.call.arguments);
        break;
    case AST_IF_ELSE:
        enact_ast_free(ast->as.conditional.condition);
        enact_ast_free(ast->as.conditional.if_true);
        enact_ast_free(ast->as.conditional.if_false);
        break;
    case AST_WHERE:
        enact_ast_free(ast->as.where_expr.body);
        free(ast->as.where_expr.name);
        enact_ast_free(ast->as.where_expr.value);
        break;
    case AST_FIX:
        enact_name_list_free(ast->as.fix_expr.names);
        enact_ast_free(ast->as.fix_expr.body);
        break;
    case AST_ASSIGN:
        free(ast->as.assignment.name);
        enact_ast_free(ast->as.assignment.value);
        break;
    case AST_FUNCTION_LITERAL:
        enact_name_list_free(ast->as.function_literal.param_names);
        enact_ast_free(ast->as.function_literal.body);
        break;
    }

    free(ast);
}
