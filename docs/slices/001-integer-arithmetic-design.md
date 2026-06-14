# Slice 001: Integer Arithmetic Design

Status: Draft 0.1

Last updated: 2026-06-14

Related requirements: [docs/slices/001-integer-arithmetic-requirements.md](/home/tprover/2606_enact_auto/docs/slices/001-integer-arithmetic-requirements.md)

## 1. Design Objective

This document defines the implementation design for the first ENACT language slice:

- integer literals
- unary minus
- binary `+`, `-`, `*`, `/`
- parentheses
- expression termination with `.`

The design is intentionally narrow. It should produce a correct, testable arithmetic core that later slices can extend without reworking the foundations.

## 2. Scope Boundaries

This design covers:

- lexer behavior for arithmetic-only input
- parser grammar and precedence
- AST structure
- runtime value representation
- arithmetic evaluation semantics
- diagnostics needed for this slice
- regression test structure

This design does not yet cover:

- identifiers and variables
- `mod`
- booleans, strings, atoms, lists, sets, objects, or functions
- assignment, sequencing, or local definitions
- REPL UX beyond single-expression parse/evaluate/print behavior

## 3. Design Decisions Summary

The following design decisions are fixed for Slice 001:

- Project-default negative syntax is standard unary `-`, not historical `~`.
- The lexer will explicitly distinguish unary minus from binary subtraction.
- Unary minus will be emitted as a dedicated token `TOK_UMINUS`.
- The parser will model unary minus explicitly rather than treating negative numbers as a separate surface syntax rule.
- Runtime integer values will be represented as signed 32-bit integers.
- Arithmetic evaluation will use checked semantics, not silent overflow.
- Division semantics will truncate toward zero.
- Division by zero will be a runtime error.
- Parser and evaluator diagnostics will expose stable error codes suitable for regression tests.

## 4. Module Layout

The implementation for this slice should be organized into the following components:

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

The test layout should begin with:

- `tests/lexer/`
- `tests/parser/`
- `tests/eval/`

## 5. Public API Shape

This slice should expose one small integration entrypoint that later tests and the REPL can both reuse.

Recommended interface:

```c
typedef struct EnactResult EnactResult;

EnactResult enact_eval_text(const char *source);
void enact_result_free(EnactResult *result);
```

`EnactResult` should contain:

- success or failure flag
- value payload for successful evaluation
- error code for failure
- optional source span or token position
- printable message buffer or message key

This keeps tests independent from CLI behavior and lets us validate lexer, parser, and evaluator through one stable surface.

## 6. Lexical Design

### 6.1 Token Set

The lexer should emit the following token set for Slice 001:

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

### 6.2 Integer Literal Payload

`TOK_INT_LITERAL` should carry the parsed digit magnitude as an unsigned 64-bit value.

Reason:

- it keeps lexing simple
- it allows the parser to accept magnitudes larger than `INT32_MAX` temporarily
- it allows the evaluator to support `-2147483648` through unary minus without needing a positive signed 32-bit intermediate
- it gives us clean range-checking in one place

The lexer should accept only decimal digits in this slice.

### 6.3 Unary Minus Classification

The lexer should maintain a single piece of significant-token state:

- `expect_operand = true`
- `expect_operand = false`

Initial state:

- at start of input, `expect_operand = true`

Behavior for `-`:

- if `expect_operand = true`, emit `TOK_UMINUS`
- if `expect_operand = false`, emit `TOK_MINUS`

After emitting these tokens, state updates as follows:

- after `TOK_INT_LITERAL`, set `expect_operand = false`
- after `TOK_RPAREN`, set `expect_operand = false`
- after `TOK_PLUS`, `TOK_MINUS`, `TOK_STAR`, `TOK_SLASH`, `TOK_UMINUS`, set `expect_operand = true`
- after `TOK_LPAREN`, set `expect_operand = true`
- after `TOK_DOT`, set `expect_operand = true`

Whitespace and comments do not change state.

Examples:

- `-1.` => `TOK_UMINUS TOK_INT_LITERAL TOK_DOT`
- `1-2.` => `TOK_INT_LITERAL TOK_MINUS TOK_INT_LITERAL TOK_DOT`
- `1*-2.` => `TOK_INT_LITERAL TOK_STAR TOK_UMINUS TOK_INT_LITERAL TOK_DOT`
- `1--2.` => `TOK_INT_LITERAL TOK_MINUS TOK_UMINUS TOK_INT_LITERAL TOK_DOT`
- `--1.` => `TOK_UMINUS TOK_UMINUS TOK_INT_LITERAL TOK_DOT`

### 6.4 Comments And Whitespace

The lexer should:

- skip spaces, tabs, carriage returns, and newlines
- skip `%` comments until the next newline or EOF

### 6.5 Lexical Errors

The lexer should emit `TOK_ERROR` or equivalent diagnostic signaling for:

- invalid characters
- malformed numeric text that cannot be converted to an unsigned 64-bit magnitude

Malformed unary minus such as `-.` is not a lexical error. It should tokenize as `TOK_UMINUS TOK_DOT` and fail in the parser.

## 7. Parser Design

### 7.1 Grammar

Recommended `bison` grammar structure:

```text
input              ::= expr TOK_DOT TOK_EOF
expr               ::= additive
additive           ::= additive TOK_PLUS multiplicative
                     | additive TOK_MINUS multiplicative
                     | multiplicative
multiplicative     ::= multiplicative TOK_STAR unary
                     | multiplicative TOK_SLASH unary
                     | unary
unary              ::= TOK_UMINUS unary
                     | primary
primary            ::= TOK_INT_LITERAL
                     | TOK_LPAREN expr TOK_RPAREN
```

### 7.2 Associativity

Associativity should be encoded structurally in the grammar:

- `additive` is left-recursive
- `multiplicative` is left-recursive
- `unary` is right-recursive

This yields:

- `1-2-3` => `(1-2)-3`
- `- - 1` => `-( -1 )`

### 7.3 Precedence

Precedence is encoded by nonterminal layering:

- `primary`
- `unary`
- `multiplicative`
- `additive`

This ensures:

- unary minus binds tighter than `*` and `/`
- multiplication and division bind tighter than addition and subtraction

### 7.4 Parse Conflicts

This grammar should produce zero shift/reduce conflicts for Slice 001.

If a conflict appears, the design should be revisited before implementation continues. This slice is small enough that conflicts are a design smell rather than an unavoidable parser tradeoff.

## 8. AST Design

### 8.1 Node Kinds

Recommended AST node kinds:

- `AST_INT_LITERAL`
- `AST_UNARY_NEG`
- `AST_ADD`
- `AST_SUB`
- `AST_MUL`
- `AST_DIV`

### 8.2 AST Shape

Recommended C shape:

```c
typedef enum {
    AST_INT_LITERAL,
    AST_UNARY_NEG,
    AST_ADD,
    AST_SUB,
    AST_MUL,
    AST_DIV
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
        struct {
            EnactAst *child;
        } unary;
        struct {
            EnactAst *left;
            EnactAst *right;
        } binary;
    } as;
};
```

### 8.3 Why Store Unsigned Magnitude

Literal AST nodes should store raw unsigned magnitude rather than immediately storing signed 32-bit values.

Reason:

- `2147483648` should be parseable as literal text even though it is out of range for a positive `int32_t`
- `-2147483648` should be accepted through `TOK_UMINUS` applied to that magnitude
- positive `2147483648.` should fail with an integer-range runtime error

## 9. Runtime Value Design

Slice 001 only needs one runtime value kind, but it should still use an extensible tagged representation.

Recommended shape:

```c
typedef enum {
    ENACT_VALUE_INT
} EnactValueKind;

typedef struct {
    EnactValueKind kind;
    int32_t as_int;
} EnactValue;
```

This avoids redesigning every evaluation interface in Slice 002.

## 10. Evaluation Design

### 10.1 Literal Evaluation

Evaluation of `AST_INT_LITERAL` should:

- succeed if `int_magnitude <= INT32_MAX`
- fail with `ENACT_ERR_INT_OVERFLOW` if `int_magnitude > INT32_MAX`

### 10.2 Unary Minus Evaluation

Evaluation of `AST_UNARY_NEG` should:

1. inspect whether the child is an `AST_INT_LITERAL`
2. if so, allow one special literal case:
   `2147483648` under unary minus evaluates to `INT32_MIN`
3. otherwise evaluate the child normally and apply checked negation

Checked negation should fail with `ENACT_ERR_INT_OVERFLOW` if asked to negate `INT32_MIN`.

### 10.3 Binary Arithmetic Evaluation

For `+`, `-`, `*`, `/`:

- evaluate both child nodes recursively
- require both results to be integer values
- use `int64_t` intermediate arithmetic
- range-check the result against `INT32_MIN` and `INT32_MAX`
- return `ENACT_ERR_INT_OVERFLOW` on overflow

### 10.4 Division Semantics

Division semantics for this project-default slice:

- division truncates toward zero
- divisor `0` produces `ENACT_ERR_DIVIDE_BY_ZERO`
- `INT32_MIN / -1` produces `ENACT_ERR_INT_OVERFLOW`

Reason:

- truncation toward zero matches modern user expectation
- it is easy to explain and regression test
- it provides deterministic project behavior even if historical evidence remains incomplete

## 11. Diagnostic Design

### 11.1 Stable Error Codes

Recommended minimum error enum:

```c
typedef enum {
    ENACT_OK = 0,
    ENACT_ERR_LEX_INVALID_CHAR,
    ENACT_ERR_LEX_BAD_INTEGER,
    ENACT_ERR_PARSE_UNEXPECTED_TOKEN,
    ENACT_ERR_PARSE_MISSING_DOT,
    ENACT_ERR_PARSE_UNMATCHED_PAREN,
    ENACT_ERR_DIVIDE_BY_ZERO,
    ENACT_ERR_INT_OVERFLOW
} EnactErrorCode;
```

### 11.2 Message Strategy

For Slice 001, error messages should be:

- human-readable
- deterministic
- short

Suggested examples:

- `unexpected token '.' after unary minus`
- `missing terminating '.'`
- `division by zero`
- `integer overflow`

Regression tests should prefer asserting error codes first and exact strings second.

## 12. Memory Management Design

Slice 001 should own and free AST memory explicitly.

Recommended rules:

- every AST constructor allocates exactly one node
- parser failure must free any partially built tree
- evaluator does not allocate new heap objects for integer results
- result objects own diagnostic message storage if dynamic text is used

Keeping runtime integers stack-allocated or returned by value is preferred for this slice.

## 13. Test Design

### 13.1 Lexer Tests

Lexer tests should assert token sequences for:

- `-1.`
- `1-2.`
- `1*-2.`
- `1--2.`
- `--1.`
- `(1+2).`
- `% x\n1+2.`

### 13.2 Parser And Evaluator Golden Tests

Golden tests should cover:

- `1+2.` => `3`
- `1+2*3.` => `7`
- `(1+2)*3.` => `9`
- `1+2*3+4*5+6.` => `33`
- `-4+10.` => `6`
- `1*-2.` => `-2`
- `1--2.` => `3`
- `--1.` => `1`
- `-(1+2).` => `-3`
- `8/2.` => `4`

### 13.3 Negative Tests

Negative tests should cover:

- `1`
- `.`
- `-.`
- `1+.`
- `(1+2.`
- `1+2).`
- `1/0.`
- `2147483648.`
- `-2147483649.`

### 13.4 Boundary Tests

Boundary tests should cover:

- `2147483647.`
- `-2147483648.`
- `2147483647+0.`
- `2147483647+1.` => overflow
- `-2147483648-1.` => overflow
- `46340*46340.` => success
- `46341*46341.` => overflow
- `-2147483648/-1.` => overflow

## 14. Review Checklist

This design is ready for development only if the following are true:

- unary minus classification is fully specified
- grammar implies the intended precedence without parser conflicts
- `-2147483648` handling is explicitly accounted for
- overflow behavior is explicit and testable
- divide-by-zero behavior is explicit and testable
- stable error codes exist for regression tests
- the AST and result APIs are small enough to implement in one focused change set

## 15. Deferred Decisions

These decisions are intentionally left for later slices:

- adding `mod`
- adding identifiers and environments
- deciding whether identifier lexing lands before or together with expression slices beyond arithmetic
- richer source spans such as line and column reporting
- historical compatibility mode for `~`

## 16. Recommended Implementation Order

Implementation should proceed in this order:

1. Define diagnostics and result API.
2. Implement lexer tokenization with `TOK_UMINUS` classification.
3. Implement AST constructors and destructors.
4. Implement `bison` grammar and parse tree construction.
5. Implement checked integer evaluator.
6. Add lexer regression tests.
7. Add parser/evaluator golden and negative tests.
8. Verify coverage impact and review outcomes before starting Slice 002.
