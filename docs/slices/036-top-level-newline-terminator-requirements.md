# Slice 036: Top-Level Newline Expression Terminator Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-17

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/035-oo-keyword-parser-scaffolding-requirements.md](/home/tprover/2606_enact_auto/docs/slices/035-oo-keyword-parser-scaffolding-requirements.md)

## 1. Slice Goal

This slice lets top-level newline terminate expressions and top-level commands in script/session execution:

```text
1+2
```

now evaluates as:

```text
3
```

The existing dot terminator remains supported.

## 2. Source Basis

The reference manual uses full stop as the historical expression terminator, but project discussion identified a usability need for modern top-level entry where pressing Enter is enough to evaluate a complete expression.

This is a project-default ergonomics extension. It should preserve dot compatibility while improving REPL, script, and `load` use.

## 3. In Scope

This slice includes:

- top-level newline termination in `enact_session_eval_script`
- TTY evaluation through the existing session/script path
- non-TTY stdin script execution
- loaded file execution
- comments ending at newline
- newlines inside parentheses not terminating the outer expression
- strings still protecting their contents from chunk splitting
- regression and unit tests for the script API and CLI/TTY behavior

## 4. Out Of Scope

This slice explicitly excludes:

- changing the single-expression parser grammar
- changing `enact_eval_text` or `enact_session_eval_text` to accept newline-only source
- adding a lexer token for newline
- allowing implicit continuation after top-level infix operators
- using EOF without dot/newline as an expression terminator
- object dot-member access
- changing token-dump behavior

## 5. API Boundary

`enact_session_eval_script` is the modernization boundary.

The lower-level single-expression parser still expects:

```text
expr "."
```

This keeps parser behavior stable while making the public CLI, REPL, batch script, and `load` paths more usable.

## 6. User-Facing Behavior

Accepted examples:

- `1+2\n` => `3`
- `x:=1\nx+2\n` => `1\n3`
- `x:=1.\nx+2\n` => `1\n3`
- `x:=1 % comment\n.\nx+1.` remains compatible and evaluates to `1\n2`
- `1 % comment with .\n2\n` => `1\n2`
- `(1,\n2)\n` => `1:2:nil`
- `add(x,y):=x+y\nadd(2,3)\n` => `<function>\n5`
- `load "file"\n` executes the file
- a loaded file may itself use newline terminators

Rejected examples:

- `1+\n2\n` => `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `x:=1\nx` => `ENACT_ERR_PARSE_MISSING_DOT`
- `(1,2\n` => `ENACT_ERR_PARSE_UNMATCHED_PAREN`
- `"unterminated\n1\n` => `ENACT_ERR_LEX_BAD_STRING`

EOF without a final dot or newline remains an unterminated expression.

## 7. Boundary Analysis Requirements

The regression suite shall include:

- a single expression terminated by newline
- multiple newline-terminated expressions
- mixed dot and newline terminators
- blank lines between expressions
- comments ending at newline
- a redundant standalone dot after a newline-terminated expression
- parenthesized newline that does not terminate early
- function definition and call across newline chunks
- `load` command without dot
- loaded file using newline terminators
- TTY Enter-key evaluation

## 8. Robustness Requirements

The regression suite shall include:

- top-level newline after an incomplete expression
- script stop on failure after an earlier newline-terminated success
- newline-terminated load failure
- incomplete load command
- type failure in a later newline-terminated chunk
- unmatched parenthesis with newline inside
- unterminated string
- EOF without final dot or newline
- parser rejection for reserved OO scaffold keywords under newline termination
- TTY recovery after a newline-terminated failure

## 9. Acceptance Criteria

This slice is accepted when:

- script/session execution accepts top-level newline as a terminator
- dot termination remains compatible
- newline inside parentheses does not split an expression
- comments and strings retain correct chunking behavior
- `load "file"\n` works
- TTY input evaluates on Enter without requiring `.`
- all regression and unit tests pass
