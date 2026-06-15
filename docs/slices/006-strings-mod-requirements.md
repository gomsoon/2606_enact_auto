# Slice 006: String Literals and Mod Operator Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-15

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/005-assignment-sequencing-requirements.md](/home/tprover/2606_enact_auto/docs/slices/005-assignment-sequencing-requirements.md)

## 1. Slice Goal

This slice adds two small pieces of the primitive expression language:

- immutable double-quoted string literals
- integer `mod` arithmetic

The goal is to introduce the third primitive runtime value kind while completing the arithmetic operator family deferred from Slice 001.

## 2. Source Basis

The PRD records:

- double-quoted literals should be interpreted as immutable strings in project-default mode
- `mod` is part of the arithmetic operator family
- `mod` shares precedence with `*` and `/`
- unary `-` binds more tightly than `*`, `/`, and `mod`

## 3. In Scope

This slice includes:

- lexer support for string literal tokens
- parser support for string literal primary expressions
- runtime string value representation
- string value copying and cleanup across results, environments, and temporaries
- CLI printing for string values
- lexer/parser/evaluator support for the `mod` operator
- regression tests for string literals, escapes, assignment, equality, and arithmetic edge cases

## 4. Out Of Scope

This slice explicitly excludes:

- string concatenation
- substring, length, formatting, interpolation, or indexing
- mutable string buffers
- non-ASCII or Unicode escape decoding
- atom or symbol syntax
- ordering comparisons over strings
- implicit conversion between strings and integers or booleans

## 5. User-Facing Behavior

Accepted examples:

- `"hello".` => `"hello"`
- `"hello world".` => `"hello world"`
- `"line\n".` => `"line\n"`
- `"quote: \"".` => `"quote: \""`
- `x:="hi"; x.` => `"hi"`
- `"a"=="a".` => `true`
- `"a"!="b".` => `true`
- `7 mod 3.` => `1`
- `-7 mod 3.` => `-1`
- `7 mod -3.` => `1`
- `8 mod 3*2.` => `4`

The printed representation for strings is a double-quoted escaped representation so the string type remains visible in CLI output.

## 6. String Lexical Requirements

The lexer shall recognize string literals beginning and ending with `"`.

Supported escape sequences:

- `\\` for a backslash
- `\"` for a double quote
- `\n` for newline
- `\r` for carriage return
- `\t` for tab

The lexer shall reject:

- unterminated strings
- strings crossing a physical source newline
- unknown escape sequences such as `\q`

Existing memory allocation failures should report `ENACT_ERR_OUT_OF_MEMORY`.

Malformed string literals should report `ENACT_ERR_LEX_BAD_STRING`.

## 7. Mod Lexical Requirements

The lexer shall recognize the exact reserved word `mod` as `TOK_MOD`.

Identifier-like words that merely contain `mod`, such as `modern`, remain identifiers.

`TOK_MOD` shall set operand expectation to true after emission.

## 8. Syntax Requirements

String literals shall be primary expressions:

```text
primary ::= string_literal
```

`mod` shall be part of the multiplicative layer:

```text
multiplicative ::= multiplicative "*" unary
                 | multiplicative "/" unary
                 | multiplicative "mod" unary
                 | unary
```

This preserves:

- unary minus binding tighter than `mod`
- `*`, `/`, and `mod` left associativity
- additive, comparison, boolean, assignment, and sequencing precedence above this layer unchanged

## 9. Semantic Requirements

String literal evaluation shall:

- produce an immutable runtime string value
- preserve decoded escape payloads internally
- return a heap-owned value that can outlive the AST
- be safe when assigned into and read from environments

String equality shall:

- allow `==` and `!=` between two string values
- reject equality between strings and non-strings with `ENACT_ERR_TYPE_EQUALITY_MISMATCH`

Other operators shall not coerce strings.

`mod` evaluation shall:

- require integer operands
- fail with `ENACT_ERR_DIVIDE_BY_ZERO` when the right operand is zero
- fail with `ENACT_ERR_INT_OVERFLOW` for `-2147483648 mod -1`
- otherwise use C99-style integer remainder semantics, with the sign following the left operand

## 10. Boundary Analysis Requirements

The regression suite shall include:

- empty string
- string with spaces
- string escape decoding
- string equality and inequality
- string assignment and lookup through the environment
- string chosen by conditional
- `mod` with zero, positive, and negative dividends/divisors
- `mod` precedence with `*`, `/`, unary `-`, and `+`
- `INT32_MIN mod -1` overflow

## 11. Robustness Requirements

The regression suite shall include malformed or risky cases such as:

- unterminated string literal
- newline inside a string literal
- unknown string escape
- string used with arithmetic
- string used as a boolean condition
- string used with ordering
- `mod` missing a left or right operand
- `mod` by zero
- non-integer `mod` operands

## 12. Acceptance Criteria

This slice is accepted when:

- strings tokenize and parse as primary expressions
- supported escapes decode and print predictably
- string values are copied and freed through result and environment paths
- `mod` parses at multiplicative precedence
- `mod` evaluates with documented integer semantics
- all previous slice tests remain green
