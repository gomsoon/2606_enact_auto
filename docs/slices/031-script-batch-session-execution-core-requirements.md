# Slice 031: Script / Batch Session Execution Core Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-17

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/030-stateful-repl-session-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/030-stateful-repl-session-core-requirements.md)

## 1. Slice Goal

This slice extends the Slice 030 evaluation session into non-interactive script execution. A source stream containing several top-level expressions shall run each expression in order against one shared session environment:

```text
x:=1.
x+2.
```

When passed through stdin, this script shall print:

```text
1
3
```

## 2. Source Basis

The PRD requires a REPL and a future file loader for batch execution of ENACT scripts. Slice 030 added a reusable session environment but kept non-TTY stdin as one-shot evaluation. This slice connects the session core to script-like input without adding `load` syntax yet.

## 3. In Scope

This slice includes:

- a public session script execution API
- splitting non-TTY source into top-level dot-terminated chunks
- preserving one session environment across all chunks
- printing each successful top-level result from CLI script execution
- stopping script execution on the first parse or evaluation failure
- preserving successful earlier session bindings when a later chunk fails
- ignoring dots inside strings, comments, and parenthesized subexpressions while finding top-level boundaries
- regression tests for API behavior and CLI script behavior

## 4. Out Of Scope

This slice explicitly excludes:

- `load "filename"` syntax
- file path resolution
- include recursion or load-cycle prevention
- multi-AST parser grammar changes
- transactional rollback for an expression that mutates before failing later
- changing TTY line-by-line REPL behavior
- changing `--tokens`; token mode continues to dump tokens for the whole input

## 5. User-Facing Behavior

Accepted script examples:

- `x:=1.\nx+2.` => `1\n3`
- `% boot\nx:=1.\nx:=x+1.\nx.` => `1\n2\n2`
- `base:=10.\nadd_base(y):=base+y.\nbase:=20.\nadd_base(1).` => `10\n<function>\n20\n11`
- `fact(n):=n==0 then 1 else n*fact(n-1).\nfact(5).` => `<function>\n120`
- `add(x,y):=x+y.\ninc:=add(1).\ninc(4).` => `<function>\n<function>\n5`
- `s:="a.b".\ns.` => `"a.b"\n"a.b"`
- `x:=1 % . ignored inside comment\n.\nx+1.` => `1\n2`
- `xs:=("a.b","c.d").\nsize(xs).` => `"a.b":"c.d":nil\n2`
- `version().\nisObject(version()).` => `"enact-auto 0.1.0"\nfalse`

Error examples:

- `x:=1.\nmissing.` => `ENACT_ERR_NAME_UNBOUND`
- `x:=1.\n(.` => `ENACT_ERR_PARSE_UNMATCHED_PAREN`
- `x:=1.\nx+true.` => `ENACT_ERR_TYPE_EXPECTED_INT`
- `x:=1.\nx` => `ENACT_ERR_PARSE_MISSING_DOT`
- `x:=1.\ny:=missing.\nx.` => `ENACT_ERR_NAME_UNBOUND`
- `x:=1.\nf():=9.\nf(x:=2).\nx.` => `ENACT_ERR_ARITY_MISMATCH`

## 6. Script Boundary Requirements

Script execution shall scan the source and produce chunks ending at a top-level `.`.

A `.` is a top-level expression terminator only when:

- it is not inside a double-quoted string
- it is not inside a `%` line comment
- it is not inside balanced parentheses

If the scanner reaches end-of-input with non-trivia text still pending, that trailing chunk shall be parsed as-is so the normal parser can report the same diagnostic family as one-shot evaluation, such as missing dot, bad string, or unmatched parenthesis.

Trivia-only script input shall succeed without producing values.

## 7. Evaluation Requirements

Each chunk shall be evaluated with the same `EnactSession`.

Successful chunks shall make their bindings visible to later chunks:

```text
x:=1.
x+2.
```

The second chunk sees `x`.

Script execution shall stop at the first failing chunk. Previously successful bindings remain in the session, but later chunks are not executed.

## 8. API Requirements

The public API shall expose:

```c
typedef int (*EnactScriptResultCallback)(const EnactResult *result, void *user_data);

int enact_session_eval_script(
    EnactSession *session,
    const char *source,
    EnactScriptResultCallback callback,
    void *user_data,
    EnactDiag *diag);
```

For each successful chunk, the callback shall receive the result before the API releases it. A null callback is allowed and simply discards successful results.

If the callback returns false, script execution shall fail with `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`.

## 9. Boundary Analysis Requirements

The regression suite shall include:

- assignment persistence across non-TTY script chunks
- reassignment using a previous script binding
- function definitions across chunks
- recursive functions across chunks
- partial application stored in the script session
- string literals containing `.`
- comments containing `.`
- tuple-like list construction across chunks
- higher-order list operations using script bindings
- builtins in script mode
- trailing whitespace and comments
- direct API tests for callback capture and trivia-only input

## 10. Robustness Requirements

The regression suite shall include:

- null session script execution
- callback rejection
- unbound-name failure after a successful earlier chunk
- parse failure after a successful earlier chunk
- type failure after a successful earlier chunk
- missing final dot in a trailing chunk
- failed assignment right-hand side
- arity failure with an impossible side-effecting extra argument
- shadowed builtin call failure

## 11. Acceptance Criteria

This slice is accepted when:

- non-TTY stdin evaluates multiple top-level expressions in one session
- each successful top-level expression prints one result
- script execution stops on the first failing chunk
- dots in strings, comments, and parenthesized expressions do not split chunks
- TTY REPL behavior from Slice 030 remains green
- token mode remains unchanged
- previous Slice 001 through Slice 030 behavior remains green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
