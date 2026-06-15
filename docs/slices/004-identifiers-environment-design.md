# Slice 004: Identifiers and Environment Design

Status: Draft 0.1

Last updated: 2026-06-15

Related requirements: [docs/slices/004-identifiers-environment-requirements.md](/home/tprover/2606_enact_auto/docs/slices/004-identifiers-environment-requirements.md)

Prerequisite design: [docs/slices/003-relational-operators-design.md](/home/tprover/2606_enact_auto/docs/slices/003-relational-operators-design.md)

## 1. Design Objective

This document defines the implementation design for identifier recognition and a minimal runtime environment.

The slice intentionally stops before assignment and local definitions. It only introduces the representation and lookup machinery those later slices need.

## 2. Design Decisions Summary

The following decisions are fixed for Slice 004:

- identifiers are ASCII-only for now
- identifier names are copied in the lexer
- reserved words remain distinct tokens
- identifiers are primary expressions
- identifier AST nodes own their copied names
- environment bindings store copied names and values by value
- public `enact_eval_text` evaluates with an empty environment
- unbound identifiers fail with `ENACT_ERR_NAME_UNBOUND`
- no global mutable user environment is introduced yet

## 3. Lexer Design

Add:

```text
IDENT_START [A-Za-z_]
IDENT_CONT  [A-Za-z0-9_]
IDENTIFIER  {IDENT_START}{IDENT_CONT}*
```

The identifier rule should appear after all keyword rules.

Token:

- `TOK_IDENTIFIER`

Payload:

- `char *text`

The lexer must allocate a NUL-terminated copy of `yytext`.

On allocation failure:

- set `ENACT_ERR_OUT_OF_MEMORY`
- return `TOK_ERROR`

## 4. Parser Design

Extend `%union`:

```c
char *text;
```

Add token:

```bison
%token <text> TOK_IDENTIFIER
```

Add destructors:

```bison
%destructor { free($$); } <text>
```

Add primary rule:

```bison
primary:
    TOK_IDENTIFIER
    {
        $$ = enact_make_identifier($1);
        if (!$$) {
            free($1);
            YYABORT;
        }
    }
```

Ownership rule:

- on successful AST construction, the AST owns the payload
- on failed construction, the parser action frees the payload

## 5. AST Design

Add:

```c
AST_IDENTIFIER
```

AST shape:

```c
char *identifier_name;
```

Constructor:

```c
EnactAst *enact_ast_new_identifier(char *name);
```

This constructor takes ownership of `name`. It does not copy again.

Destruction:

- `AST_IDENTIFIER` frees `identifier_name`

## 6. Environment Design

Add `src/env.h` and `src/env.c`.

Recommended shape:

```c
typedef struct EnactEnvEntry EnactEnvEntry;

typedef struct EnactEnv {
    EnactEnvEntry *head;
} EnactEnv;
```

Each entry stores:

- copied `char *name`
- `EnactValue value`
- next pointer

Operations:

- `enact_env_init`
- `enact_env_free`
- `enact_env_define`
- `enact_env_lookup`

Definition behavior:

- existing name: replace stored value
- new name: allocate an entry and copy the name

## 7. Evaluation Design

`enact_eval_ast` should become a wrapper:

1. create an empty `EnactEnv`
2. call `enact_eval_ast_with_env`
3. free the temporary environment

Add:

```c
int enact_eval_ast_with_env(const EnactAst *ast, const EnactEnv *env, EnactValue *value, EnactDiag *diag);
```

Internal recursive evaluation helpers should accept `const EnactEnv *env`.

`AST_IDENTIFIER` evaluation:

1. require non-null env
2. lookup `ast->as.identifier_name`
3. return the value if found
4. set `ENACT_ERR_NAME_UNBOUND` otherwise

## 8. Diagnostics

Add:

```c
ENACT_ERR_NAME_UNBOUND
```

Message:

```text
unbound identifier
```

The diagnostic does not include the identifier name yet because diagnostics currently use static messages.

## 9. Test Design

Integration tests:

- token dump for identifiers
- token dump proving exact reserved words remain keywords
- unbound identifier failures
- invalid identifier-start characters
- missing final dot after identifier

Unit tests:

- environment init/free with null safety
- define and lookup integer binding
- define and lookup boolean binding
- redefine an existing name
- missing lookup
- evaluator resolves an identifier AST through an explicit environment
- evaluator reports unbound name with empty environment

## 10. Review Checklist

This design is ready for implementation if:

- lexer keyword precedence is preserved
- identifier payload ownership is explicit
- parse failure frees identifier payloads
- AST destruction frees identifier names
- environment ownership is independent of AST ownership
- public evaluation remains backward compatible
