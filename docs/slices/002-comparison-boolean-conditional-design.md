# Slice 002: Comparison, Boolean, and Conditional Core Design

Status: Draft 0.1

Last updated: 2026-06-15

Related requirements: [docs/slices/002-comparison-boolean-conditional-requirements.md](/home/tprover/2606_enact_auto/docs/slices/002-comparison-boolean-conditional-requirements.md)

Prerequisite design: [docs/slices/001-integer-arithmetic-design.md](/home/tprover/2606_enact_auto/docs/slices/001-integer-arithmetic-design.md)

## 1. Design Objective

This document defines the implementation design for the second ENACT language slice:

- equality comparison using `==`
- boolean literals `true` and `false`
- unary `not`
- binary `and` and `or`
- conditional expressions written as `true_expr if condition else false_expr`

The design is intentionally narrow. It should add a correct, testable decision-making core on top of Slice 001 without yet introducing identifiers, assignment, or broader control-flow syntax.

## 2. Scope Boundaries

This design covers:

- lexer behavior for `==`, boolean keywords, and conditional keywords
- parser grammar and precedence for comparison, boolean logic, and conditional expressions
- AST extensions for booleans, equality, logic, and conditionals
- runtime value representation for booleans
- evaluator semantics for type checking, short-circuit behavior, and lazy branch selection
- diagnostics needed for this slice
- regression test structure for the current test harness

This design does not yet cover:

- relational operators other than `==`
- historical equality `=`
- historical or alternate `then`-led conditional forms
- identifiers, variables, assignment, sequencing, `where`, `fix`, or `load`
- strings, atoms, lists, sets, objects, or functions
- truthiness rules
- equality across future non-primitive runtime kinds

## 3. Design Decisions Summary

The following design decisions are fixed for Slice 002:

- Project-default equality syntax is `==`, not historical `=`.
- The lexer will emit a dedicated equality token `TOK_EQEQ`.
- A bare `=` will be treated as a lexical error, not silently tolerated.
- Boolean literals will be represented by the keywords `true` and `false`.
- The lexer will emit `TOK_TRUE` and `TOK_FALSE` rather than a generic identifier token.
- The parser will admit one canonical conditional surface form only: `true_expr if condition else false_expr`.
- Conditional expressions will be represented semantically as `condition`, `if_true`, and `if_false` even though the surface syntax places the true branch first.
- `==` will be non-associative by grammar shape rather than by post-parse rewriting.
- `and` and `or` will short-circuit.
- Conditional evaluation will evaluate only the selected branch.
- Conditions must be boolean-valued.
- Equality is defined only for `int == int` and `bool == bool` in this slice.
- Cross-type equality such as `true==1.` will be a runtime type error.
- The public evaluation entrypoint will remain `enact_eval_text(const char *source)`.

## 4. Module Layout

Slice 002 should extend the existing Slice 001 layout rather than introducing new modules.

The primary touched files should be:

- `src/enact.l`
- `src/enact.y`
- `src/ast.h`
- `src/ast.c`
- `src/value.h`
- `src/eval.h`
- `src/eval.c`
- `src/diag.h`
- `src/diag.c`
- `src/api.h`
- `src/api.c`
- `src/main.c`
- `tests/run_tests.py`
- `tests/unit_tests.c`

No new subsystem is required. This slice is still small enough to stay inside the current parser, AST, evaluator, and integration-test surfaces.

## 5. Public API Shape

The public integration entrypoint from Slice 001 should remain unchanged:

```c
typedef struct EnactResult EnactResult;

EnactResult enact_eval_text(const char *source);
void enact_result_free(EnactResult *result);
```

The result surface should continue to expose:

- success or failure flag
- value payload for successful evaluation
- stable error code for failure
- optional offset and human-readable message

The key change is internal:

- `EnactValue` must now represent either an integer or a boolean

This preserves the integration contract for the CLI and tests while allowing the runtime domain to expand.

## 6. Lexical Design

### 6.1 Token Set

The lexer should emit the following additional token set for Slice 002:

- `TOK_EQEQ`
- `TOK_TRUE`
- `TOK_FALSE`
- `TOK_NOT`
- `TOK_AND`
- `TOK_OR`
- `TOK_IF`
- `TOK_ELSE`

The Slice 001 token set remains in force:

- `TOK_INT_LITERAL`
- `TOK_UMINUS`
- `TOK_PLUS`
- `TOK_MINUS`
- `TOK_STAR`
- `TOK_SLASH`
- `TOK_LPAREN`
- `TOK_RPAREN`
- `TOK_DOT`
- `TOK_EOF`
- `TOK_ERROR`

### 6.2 Keyword Strategy

Because identifiers are still out of scope, boolean and conditional words can be handled directly as reserved literal tokens:

- `true`
- `false`
- `not`
- `and`
- `or`
- `if`
- `else`

This is simpler than introducing an identifier token and then reserving keywords through a symbol table.

When identifiers arrive in a later slice:

- these reserved-word rules should remain above the identifier rule in `flex`

### 6.3 Equality Tokenization

The lexer should:

- match `==` before any fallback rule
- emit `TOK_EQEQ`
- set `expect_operand = true` after `TOK_EQEQ`

A single `=` should:

- set a dedicated lexical diagnostic
- return `TOK_ERROR`

This keeps the modernization from `=` to `==` explicit and testable.

### 6.4 Operand-Expectation State

Slice 001 already classifies `-` as unary or binary through `expect_operand`.

That same state machine should be extended as follows:

- after `TOK_INT_LITERAL`, `TOK_TRUE`, `TOK_FALSE`, and `TOK_RPAREN`, set `expect_operand = false`
- after `TOK_PLUS`, `TOK_MINUS`, `TOK_STAR`, `TOK_SLASH`, `TOK_UMINUS`, `TOK_EQEQ`, `TOK_NOT`, `TOK_AND`, `TOK_OR`, `TOK_IF`, `TOK_ELSE`, `TOK_LPAREN`, and `TOK_DOT`, set `expect_operand = true`

Examples:

- `1==-2.` => `TOK_INT_LITERAL TOK_EQEQ TOK_UMINUS TOK_INT_LITERAL TOK_DOT`
- `true and not false.` => `TOK_TRUE TOK_AND TOK_NOT TOK_FALSE TOK_DOT`
- `1 if 2==3 else 4.` => `TOK_INT_LITERAL TOK_IF TOK_INT_LITERAL TOK_EQEQ TOK_INT_LITERAL TOK_ELSE TOK_INT_LITERAL TOK_DOT`

### 6.5 EOF And Parse-Error Support

To improve parse diagnostics for Slice 002, the lexer should ensure scanner state can distinguish:

- unexpected token before `.` versus
- actual end-of-input without a terminating `.`

Recommended rule:

- in the `<<EOF>>` rule, set `state->last_token = 0` before returning `0`

This allows parser error handling to treat:

- EOF without `.` as `ENACT_ERR_PARSE_MISSING_DOT`
- all other malformed parse states as `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`, unless a more specific diagnostic is already set

### 6.6 Comments And Whitespace

Whitespace and `%` line comments should behave exactly as in Slice 001:

- skip spaces, tabs, carriage returns, and newlines
- skip `%` comments until newline or EOF

## 7. Parser Design

### 7.1 Grammar

Recommended `bison` grammar structure:

```text
input              ::= expr TOK_DOT
expr               ::= conditional
conditional        ::= logical_or
                     | logical_or TOK_IF logical_or TOK_ELSE conditional
logical_or         ::= logical_or TOK_OR logical_and
                     | logical_and
logical_and        ::= logical_and TOK_AND logical_not
                     | logical_not
logical_not        ::= TOK_NOT logical_not
                     | equality
equality           ::= additive
                     | additive TOK_EQEQ additive
additive           ::= additive TOK_PLUS multiplicative
                     | additive TOK_MINUS multiplicative
                     | multiplicative
multiplicative     ::= multiplicative TOK_STAR unary
                     | multiplicative TOK_SLASH unary
                     | unary
unary              ::= TOK_UMINUS unary
                     | primary
primary            ::= TOK_INT_LITERAL
                     | TOK_TRUE
                     | TOK_FALSE
                     | TOK_LPAREN expr TOK_RPAREN
```

### 7.2 Associativity

Associativity should be encoded structurally:

- `logical_or` is left-recursive
- `logical_and` is left-recursive
- `logical_not` is right-recursive
- `conditional` is right-recursive in its false branch
- `equality` is not recursive

This yields:

- `true or false or true` => `(true or false) or true`
- `true and false and true` => `(true and false) and true`
- `not not true` => `not (not true)`
- `1 if false else 2 if true else 3` => `1 if false else (2 if true else 3)`
- `1==2==3` => rejected

### 7.3 Precedence

The intended precedence ladder for Slice 002 is:

- `primary`
- unary minus from Slice 001
- `*`, `/`
- `+`, `-`
- `==`
- `not`
- `and`
- `or`
- `if ... else ...`

This implies:

- `1+2==3` parses as `(1+2)==3`
- `not 1==2` parses as `not (1==2)`
- `not false and true` parses as `(not false) and true`
- `true or false if false else true` parses as `(true or false) if false else true`

### 7.4 Conditional Shape And Parenthesization

The chosen conditional grammar keeps the slice small by allowing:

- any `logical_or` as the true branch
- any `logical_or` as the condition
- any `conditional` as the false branch

Consequences:

- nested conditionals in the false branch work without parentheses
- nested conditionals in the true branch or condition require parentheses

Examples:

- `1 if false else 2 if true else 3.` is accepted
- `(1 if false else 2) if true else 3.` is accepted
- `1 if (2 if true else 3) else 4.` is accepted only with parentheses around the nested condition

This restriction is acceptable for the slice because it keeps the parser deterministic and avoids premature generalization.

### 7.5 Parse Conflicts

This grammar should produce zero shift/reduce conflicts for Slice 002.

If a conflict appears, the design should be revisited before implementation continues. The slice is still small enough that parser conflicts are a design smell rather than an unavoidable tradeoff.

## 8. AST Design

### 8.1 Node Kinds

Recommended AST node kinds:

- `AST_INT_LITERAL`
- `AST_BOOL_LITERAL`
- `AST_UNARY_NEG`
- `AST_NOT`
- `AST_ADD`
- `AST_SUB`
- `AST_MUL`
- `AST_DIV`
- `AST_EQ`
- `AST_AND`
- `AST_OR`
- `AST_IF_ELSE`

### 8.2 AST Shape

Recommended C shape:

```c
typedef enum {
    AST_INT_LITERAL,
    AST_BOOL_LITERAL,
    AST_UNARY_NEG,
    AST_NOT,
    AST_ADD,
    AST_SUB,
    AST_MUL,
    AST_DIV,
    AST_EQ,
    AST_AND,
    AST_OR,
    AST_IF_ELSE
} EnactAstKind;

typedef struct EnactSourceSpan {
    int start_offset;
    int end_offset;
} EnactSourceSpan;

typedef struct EnactAst EnactAst;

struct EnactAst {
    EnactAstKind kind;
    EnactSourceSpan span;
    union {
        uint64_t int_magnitude;
        int bool_value;
        struct {
            EnactAst *child;
        } unary;
        struct {
            EnactAst *left;
            EnactAst *right;
        } binary;
        struct {
            EnactAst *condition;
            EnactAst *if_true;
            EnactAst *if_false;
        } conditional;
    } as;
};
```

Using `int` for the stored boolean payload is acceptable inside the AST, but the runtime value layer should use `bool`.

### 8.3 Constructor Strategy

Recommended AST constructors:

```c
EnactAst *enact_ast_new_int(uint64_t int_magnitude);
EnactAst *enact_ast_new_bool(int bool_value);
EnactAst *enact_ast_new_unary(EnactAstKind kind, EnactAst *child);
EnactAst *enact_ast_new_binary(EnactAstKind kind, EnactAst *left, EnactAst *right);
EnactAst *enact_ast_new_conditional(EnactAst *condition, EnactAst *if_true, EnactAst *if_false);
```

This keeps AST construction explicit and avoids overloading the binary shape for a ternary construct.

## 9. Runtime Value Design

Slice 002 needs two runtime value kinds.

Recommended shape:

```c
#include <stdbool.h>
#include <stdint.h>

typedef enum {
    ENACT_VALUE_INT,
    ENACT_VALUE_BOOL
} EnactValueKind;

typedef struct {
    EnactValueKind kind;
    union {
        int32_t as_int;
        bool as_bool;
    } as;
} EnactValue;
```

Recommended helper constructors:

```c
EnactValue enact_value_make_int(int32_t value);
EnactValue enact_value_make_bool(bool value);
```

This is slightly more verbose than the Slice 001 integer-only struct, but it keeps future slices extensible and makes type checks explicit.

## 10. Evaluation Design

### 10.1 Literal Evaluation

Evaluation of `AST_BOOL_LITERAL` should:

- produce `ENACT_VALUE_BOOL`
- store either `true` or `false`

Evaluation of `AST_INT_LITERAL` remains exactly as in Slice 001.

### 10.2 Equality Evaluation

Evaluation of `AST_EQ` should:

1. evaluate both child nodes
2. compare their runtime kinds
3. fail with `ENACT_ERR_TYPE_EQUALITY_MISMATCH` if the kinds differ
4. compare integer payloads when both are `ENACT_VALUE_INT`
5. compare boolean payloads when both are `ENACT_VALUE_BOOL`
6. return `ENACT_VALUE_BOOL`

This slice does not define coercion rules.

Examples:

- `1==1.` => `true`
- `1==2.` => `false`
- `true==false.` => `false`
- `true==1.` => type error

### 10.3 Unary `not` Evaluation

Evaluation of `AST_NOT` should:

- evaluate the child node
- require `ENACT_VALUE_BOOL`
- fail with `ENACT_ERR_TYPE_EXPECTED_BOOL` otherwise
- return logical negation as `ENACT_VALUE_BOOL`

### 10.4 Logical `and` Evaluation

Evaluation of `AST_AND` should:

1. evaluate the left child
2. require `ENACT_VALUE_BOOL`
3. if the left result is `false`, return `false` immediately
4. otherwise evaluate the right child
5. require `ENACT_VALUE_BOOL` on the right
6. return the right boolean result

This enforces left-to-right short-circuit behavior.

### 10.5 Logical `or` Evaluation

Evaluation of `AST_OR` should:

1. evaluate the left child
2. require `ENACT_VALUE_BOOL`
3. if the left result is `true`, return `true` immediately
4. otherwise evaluate the right child
5. require `ENACT_VALUE_BOOL` on the right
6. return the right boolean result

This enforces left-to-right short-circuit behavior.

### 10.6 Conditional Evaluation

Evaluation of `AST_IF_ELSE` should:

1. evaluate `condition`
2. require `ENACT_VALUE_BOOL`
3. if the condition is `true`, evaluate and return `if_true`
4. if the condition is `false`, evaluate and return `if_false`

The non-selected branch must not be evaluated.

This is important because later slices will introduce side effects and richer errors, but the lazy branch rule should already be frozen now.

### 10.7 Arithmetic Interaction

Slice 001 arithmetic rules remain unchanged, but the evaluator must now protect arithmetic operators from boolean operands.

Recommended rule:

- `AST_ADD`, `AST_SUB`, `AST_MUL`, `AST_DIV`, and `AST_UNARY_NEG` should require integer-typed child results
- if a boolean reaches an arithmetic operator, fail with `ENACT_ERR_TYPE_EXPECTED_INT`

Examples:

- `true+1.` => type error
- `-true.` => type error
- `1 if true else false.` => accepted
- `(1 if true else false)+2.` => type error if the selected branch is boolean

### 10.8 Branch Type Policy

The conditional operator should not require both branches to have the same type.

Reason:

- the selected branch is returned unchanged
- this keeps the slice simple
- it generalizes naturally when later runtime kinds arrive

Examples:

- `1 if true else false.` is allowed and returns `1`
- `1 if false else false.` is allowed and returns `false`

No branch-type reconciliation is required in this slice.

## 11. Diagnostic Design

### 11.1 Stable Error Codes

Recommended minimum error enum:

```c
typedef enum {
    ENACT_OK = 0,
    ENACT_ERR_LEX_INVALID_CHAR,
    ENACT_ERR_LEX_BAD_INTEGER,
    ENACT_ERR_LEX_BARE_EQUALS,
    ENACT_ERR_PARSE_UNEXPECTED_TOKEN,
    ENACT_ERR_PARSE_MISSING_DOT,
    ENACT_ERR_PARSE_UNMATCHED_PAREN,
    ENACT_ERR_DIVIDE_BY_ZERO,
    ENACT_ERR_INT_OVERFLOW,
    ENACT_ERR_TYPE_EXPECTED_BOOL,
    ENACT_ERR_TYPE_EXPECTED_INT,
    ENACT_ERR_TYPE_EQUALITY_MISMATCH,
    ENACT_ERR_OUT_OF_MEMORY
} EnactErrorCode;
```

### 11.2 Message Strategy

For Slice 002, error messages should remain:

- human-readable
- deterministic
- short

Suggested examples:

- `bare '=' is not supported; use '=='`
- `unexpected token 'else'`
- `boolean value required`
- `integer value required`
- `cannot compare values of different kinds`

Regression tests should continue to assert error codes first and exact strings second.

## 12. Memory Management Design

Slice 002 should keep the Slice 001 ownership rules:

- every AST constructor allocates exactly one node
- parser failure frees any partially built tree
- evaluator returns values by value rather than heap-allocating them
- result objects own diagnostic message storage only if dynamic text is introduced

Additional rule for this slice:

- `AST_IF_ELSE` destruction must recursively free exactly three child nodes

No heap allocation is needed for booleans themselves.

## 13. Test Design

### 13.1 Lexer Tests

Lexer tests in `tests/run_tests.py` should assert token sequences for:

- `true.`
- `false.`
- `1==2.`
- `true and false.`
- `not false.`
- `1 if true else 2.`
- bare `=`

Representative token outputs:

- `true and false.` => `TOK_TRUE TOK_AND TOK_FALSE TOK_DOT TOK_EOF`
- `1==2.` => `TOK_INT_LITERAL TOK_EQEQ TOK_INT_LITERAL TOK_DOT TOK_EOF`

### 13.2 Parser And Evaluator Golden Tests

Golden tests should cover:

- `true.` => `true`
- `false.` => `false`
- `1==1.` => `true`
- `1==2.` => `false`
- `1+2==3.` => `true`
- `not false.` => `true`
- `not true.` => `false`
- `true and false.` => `false`
- `false or true.` => `true`
- `1 if true else 2.` => `1`
- `1 if false else 2.` => `2`
- `1 if 1==1 else 2.` => `1`
- `1 if false else 2 if true else 3.` => `2`
- `false and 1/0==0.` => `false`
- `true or 1/0==0.` => `true`

### 13.3 Negative Tests

Negative tests should cover:

- `=`
- `1==.`
- `1==2==3.`
- `not.`
- `true and.`
- `1 and true.`
- `1 or false.`
- `1 if true.`
- `1 if 1 else 2.`
- `true==1.`
- `true+1.`

### 13.4 Boundary Tests

Boundary tests should cover:

- `0==0.`
- `-2147483648==-2147483648.`
- `2147483647==2147483647.`
- `true==true.`
- `false==false.`
- `true==false.`
- `not not true.`
- nested parenthesized forms such as `((true)).`
- conditionals returning different runtime kinds

### 13.5 Unit Tests

`tests/unit_tests.c` should add lower-level coverage for:

- new diagnostic code names and messages
- boolean value construction and tagging
- equality over matching and mismatching kinds
- short-circuit behavior using deliberately invalid or divide-by-zero right branches
- conditional branch laziness using deliberately invalid unselected branches

## 14. Review Checklist

This design is ready for development only if the following are true:

- `==` tokenization is fully specified
- bare `=` behavior is explicit and testable
- keyword tokenization does not interfere with unary-minus classification
- grammar implies the intended precedence without parser conflicts
- `==` non-associativity is enforced structurally
- short-circuit behavior is explicit and testable
- conditional lazy-branch behavior is explicit and testable
- integer/boolean type discipline is explicit and testable
- stable diagnostic codes exist for lexical, parse, and runtime type failures

## 15. Deferred Decisions

These decisions are intentionally left for later slices:

- adding `<`, `>`, `<=`, `>=`, and `<>`
- deciding whether historical `=` should be accepted in a future strict mode
- adding `then`-led conditional syntax
- adding identifiers and environments
- deciding how booleans interact with future runtime kinds such as strings, atoms, or objects
- introducing pattern matching or richer control-flow constructs

## 16. Recommended Implementation Order

Implementation should proceed in this order:

1. Extend diagnostics with lexical bare-equals and runtime type-error codes.
2. Extend `EnactValue` with boolean support.
3. Extend AST kinds and constructors for booleans, equality, logic, and conditionals.
4. Update the lexer for `==`, boolean keywords, and `if` / `else`.
5. Update parser grammar and parse tree construction.
6. Update evaluator logic for equality, `not`, `and`, `or`, and conditionals.
7. Update CLI printing for boolean values.
8. Add lexer and integration regression tests in `tests/run_tests.py`.
9. Add focused helper and lazy-evaluation tests in `tests/unit_tests.c`.
10. Verify coverage impact and review outcomes before starting Slice 003.
