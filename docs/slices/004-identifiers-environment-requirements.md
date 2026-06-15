# Slice 004: Identifiers and Environment Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-15

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/003-relational-operators-requirements.md](/home/tprover/2606_enact_auto/docs/slices/003-relational-operators-requirements.md)

## 1. Slice Goal

This slice introduces the smallest name-resolution core:

- identifier lexical recognition
- identifier AST nodes
- a runtime environment mapping names to values
- identifier evaluation through environment lookup
- stable diagnostics for unbound identifiers

The purpose is to create the foundation required by later slices for assignment, local definitions, functions, and built-ins.

## 2. Source Basis

The PRD records the manual-derived lexical rule that identifiers are formed from letters, digits, and underscore, and may not start with a digit.

This slice adopts that rule for project-default syntax:

- identifiers start with an ASCII letter or underscore
- identifiers continue with ASCII letters, digits, or underscore
- reserved words remain reserved

## 3. In Scope

This slice includes:

- `TOK_IDENTIFIER` token emission with a copied identifier name payload
- identifier AST construction and destruction
- an `EnactEnv` runtime structure
- environment definition and lookup helpers
- evaluator support for resolving identifiers through an environment
- public default evaluation against an empty environment
- regression tests for tokenization, unbound-name diagnostics, reserved-word behavior, and environment lookup through unit tests

## 4. Out Of Scope

This slice explicitly excludes:

- assignment `:=`
- sequencing `;`
- local definitions using `where`
- function definitions and function application
- lambda expressions
- closures or static binding capture
- built-in functions
- object attributes or dynamic object lookup
- identifier namespaces beyond one flat environment

This means user input such as `x.` can parse, but it fails at evaluation until a later slice introduces binding syntax.

## 5. User-Facing Behavior

Representative behavior:

- `x.` parses as an identifier expression and fails with `ENACT_ERR_NAME_UNBOUND`
- `foo_bar123.` parses as an identifier expression and fails with `ENACT_ERR_NAME_UNBOUND`
- `x+1.` parses and fails with `ENACT_ERR_NAME_UNBOUND`
- `1+x.` parses and fails with `ENACT_ERR_NAME_UNBOUND`
- reserved words such as `true`, `false`, `not`, `and`, `or`, `if`, and `else` keep their existing token meanings
- longer names containing reserved words such as `trueValue.` and `and_then.` are identifiers

At this stage, every accepted input remains a single expression followed by `.`.

## 6. Lexical Requirements

The lexer shall recognize identifiers matching:

```text
[A-Za-z_][A-Za-z0-9_]*
```

The lexer shall ensure:

- reserved-word rules are checked before the identifier fallback rule
- exact reserved words remain keyword tokens
- longer names that merely contain reserved words are identifiers
- identifier text is copied before returning the token
- allocation failure for identifier text reports `ENACT_ERR_OUT_OF_MEMORY`

## 7. Syntax Requirements

The parser shall accept identifiers as primary expressions:

```text
primary ::= integer
          | boolean
          | identifier
          | "(" expr ")"
```

Identifiers shall work wherever primary expressions already work:

- arithmetic operands
- comparison operands
- boolean operands
- conditional branches and conditions

The parser does not perform name binding or type checking.

## 8. Environment Requirements

The runtime shall provide a small environment abstraction:

```c
typedef struct EnactEnv EnactEnv;

void enact_env_init(EnactEnv *env);
void enact_env_free(EnactEnv *env);
int enact_env_define(EnactEnv *env, const char *name, EnactValue value);
int enact_env_lookup(const EnactEnv *env, const char *name, EnactValue *out);
```

Requirements:

- names are copied when defined
- values are stored by value
- redefining a name updates the existing binding
- lookup returns false when no binding exists
- freeing an environment releases all copied names

Nested scopes are intentionally deferred.

## 9. Semantic Requirements

The evaluator shall:

- evaluate identifier AST nodes by looking up the name in the current environment
- return the stored value when a binding exists
- fail with `ENACT_ERR_NAME_UNBOUND` when no binding exists
- preserve all existing arithmetic, comparison, boolean, and conditional behavior

Default public evaluation through `enact_eval_text` shall use an empty environment.

An internal or public evaluator entrypoint may accept an explicit `EnactEnv` for tests and later slices.

## 10. Error Requirements

The implementation shall detect and report, at minimum:

- unbound identifier expression such as `x.`
- unbound identifier inside arithmetic such as `x+1.`
- unbound identifier inside conditionals such as `1 if flag else 2.`
- malformed identifier starts such as `$x.`
- missing final `.` after an identifier

New diagnostic code:

- `ENACT_ERR_NAME_UNBOUND`

Existing diagnostic codes remain in force for malformed syntax and invalid characters.

## 11. Boundary Analysis Requirements

The regression suite shall include:

- `x.`
- `_x.`
- `x1.`
- `foo_bar123.`
- `trueValue.`
- `and_then.`
- `x+1.`
- `1+x.`
- `x==1.`
- `1 if flag else 2.`

Unit tests shall include environment lookup for at least:

- integer binding
- boolean binding
- redefinition
- missing binding

## 12. Robustness Requirements

The regression suite shall include:

- `x`
- `$x.`
- `1abc.`
- `trueValue`
- `_`
- a long identifier

The implementation must not leak identifier payloads during parse success or parse failure.

## 13. Acceptance Criteria

This slice is accepted when:

- identifiers tokenize correctly
- reserved words still tokenize as keywords
- identifiers parse as primary expressions
- identifier AST nodes own and free copied names
- evaluator name lookup works through `EnactEnv`
- public default evaluation reports unbound identifiers
- existing Slice 001 through Slice 003 behavior remains green
