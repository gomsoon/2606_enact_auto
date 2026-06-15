# Slice 005: Assignment and Sequencing Core Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-15

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/004-identifiers-environment-requirements.md](/home/tprover/2606_enact_auto/docs/slices/004-identifiers-environment-requirements.md)

## 1. Slice Goal

This slice makes the flat environment introduced in Slice 004 user-visible through:

- assignment using `:=`
- sequencing using `;`
- identifier lookup after assignment within the same input expression

The purpose is to create the smallest mutable binding core before introducing `where`, functions, or REPL-level persistent bindings.

## 2. Source Basis

The PRD records:

- assignment expressions use `:=`
- sequencing uses `;`
- assignment has lower precedence than conditionals
- sequencing has lower precedence than assignment

This slice implements a narrow project-default subset:

- assignment left-hand side is a bare identifier only
- assignment stores runtime values in the current flat environment
- sequencing evaluates left-to-right and returns the rightmost result

## 3. In Scope

This slice includes:

- lexer tokens for `:=` and `;`
- parser support for identifier assignment
- parser support for sequencing expressions
- AST nodes for assignment and sequence
- evaluator support for mutating the per-expression environment
- tests for assignment values, reassignment, sequencing order, type interactions, and malformed syntax

## 4. Out Of Scope

This slice explicitly excludes:

- REPL bindings that persist across separate input lines
- local definitions using `where`
- function definitions such as `f(x):=x+1`
- assignment to object attributes or other lvalues
- destructuring or tuple assignment
- nested lexical scopes
- `load` file-level persistent environments
- sequence as a top-level statement type distinct from expressions

## 5. User-Facing Behavior

Representative accepted examples:

- `x:=1.` => `1`
- `x:=1; x.` => `1`
- `x:=1; x+2.` => `3`
- `x:=true; x and false.` => `false`
- `x:=1; x:=2; x.` => `2`
- `x:=1; y:=x+2; y.` => `3`
- `x:=1 if true else 2; x.` => `1`
- `(x:=1; x)+2.` => `3`

Bindings exist only while evaluating the current input expression. A later input line does not see previous bindings in this slice.

## 6. Lexical Requirements

The lexer shall recognize:

- `:=` as `TOK_ASSIGN`
- `;` as `TOK_SEMI`

The lexer shall ensure:

- `:=` is matched before any future single `:` token
- both tokens set operand expectation to true after emission
- bare `=` remains rejected with `ENACT_ERR_LEX_BARE_EQUALS`

## 7. Syntax Requirements

The parser shall accept this conceptual grammar:

```text
expr       ::= sequence
sequence   ::= assignment
             | sequence ";" assignment
assignment ::= conditional
             | identifier ":=" assignment
```

This yields:

- sequencing is left-associative
- assignment is right-associative
- assignment binds looser than conditionals
- sequencing binds looser than assignment

The parser shall reject:

- `1:=2.`
- `x:=.`
- `;x.`
- `x; .`
- `x:=1; .`

## 8. Semantic Requirements

The evaluator shall:

- evaluate the right-hand side of assignment
- define or update the identifier in the current environment
- return the assigned value
- evaluate sequences left-to-right
- return the right expression's value from a sequence
- allow assigned values of any runtime kind currently supported
- preserve existing type rules for arithmetic, comparison, boolean logic, and conditionals

The evaluator shall not:

- carry bindings across separate public `enact_eval_text` calls
- coerce assigned values
- evaluate the right side of a sequence before the left side

## 9. Error Requirements

The implementation shall detect and report, at minimum:

- missing right-hand side after `:=`
- non-identifier assignment left-hand side
- missing right side after `;`
- leading `;`
- use of an unbound identifier before assignment
- assignment followed by type-invalid usage, such as `x:=true; x+1.`

Existing diagnostic codes are sufficient:

- `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `ENACT_ERR_NAME_UNBOUND`
- `ENACT_ERR_TYPE_EXPECTED_INT`
- `ENACT_ERR_TYPE_EXPECTED_BOOL`

If environment mutation fails due to allocation, report `ENACT_ERR_OUT_OF_MEMORY`.

## 10. Boundary Analysis Requirements

The regression suite shall include:

- assignment of integer values
- assignment of boolean values
- reassignment
- assignment from another identifier
- assignment from conditional expressions
- sequencing with three or more expressions
- parenthesized sequence inside arithmetic
- assignment result used immediately

## 11. Robustness Requirements

The regression suite shall include malformed or risky cases such as:

- `x:=.`
- `:=1.`
- `1:=2.`
- `x:=1;.`
- `;x.`
- `x; .`
- `x:=true; x+1.`
- `x+1; x:=2.`

## 12. Acceptance Criteria

This slice is accepted when:

- `:=` and `;` tokenize correctly
- assignment and sequence parse with documented precedence
- assignments mutate the current expression environment
- sequence evaluation is left-to-right
- public evaluation remains per-input, not persistent across calls
- all previous slice tests remain green
