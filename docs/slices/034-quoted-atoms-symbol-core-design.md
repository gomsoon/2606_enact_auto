# Slice 034: Quoted Atoms / Symbol Core Design

Status: Draft 0.1

Last updated: 2026-06-17

Related requirements: [docs/slices/034-quoted-atoms-symbol-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/034-quoted-atoms-symbol-core-requirements.md)

Prerequisite design: [docs/slices/021-atom-builtin-design.md](/home/tprover/2606_enact_auto/docs/slices/021-atom-builtin-design.md)

## 1. Design Summary

Implement quoted atoms as a new literal and runtime value kind:

```text
'name
```

Atoms are deliberately not strings. This keeps the symbol-like value space ready for later object-oriented features where names, selectors, or tags should be data values rather than text strings.

## 2. Lexer

Add `TOK_ATOM_LITERAL` for:

```text
"'"{IDENTIFIER}
```

The lexer strips the leading quote and stores only the payload in `yylval.text`.

The rule appears before the ordinary identifier rule. That means:

- `'true` is one atom token, not quote plus `TOK_TRUE`
- `'load` is one atom token, not quote plus `TOK_LOAD`
- malformed forms such as `'1` still fail through the existing invalid-character path

## 3. Parser And AST

Add `AST_ATOM_LITERAL` with `as.atom_value`.

The parser accepts `TOK_ATOM_LITERAL` in the same expression positions as string literals:

- `primary`
- `application_argument`

The atom literal is not accepted as an assignment target or `where` binding name.

## 4. Runtime Value

Add `ENACT_VALUE_ATOM` with `as.as_atom`.

Runtime support mirrors string ownership:

- `enact_value_copy` deep-copies the payload
- `enact_value_free` releases the payload
- `enact_value_equal` compares atom payloads with `strcmp`

Evaluator literal execution creates an atom value and copies it into the output value.

## 5. Printing

`enact_print_value_inner` prints atoms with a leading quote:

```text
'hello
```

List printing reuses normal value printing, so atom lists print naturally:

```text
'a:'b:nil
```

## 6. Builtin Interaction

No builtin requires a dedicated atom branch in this slice.

The existing type behavior is enough:

- `atom('x)` returns `true` because atoms are non-list values
- `member`, `remove`, `union`, `difference`, and `intersection` use value equality
- `map`, `filter`, `all`, `exists`, and `reduce` carry atom values through existing callable/list helpers
- arithmetic, boolean, relational, call, and list-tail checks reject atoms with their existing diagnostics

## 7. String Distinction

Atoms and strings are different kinds.

The evaluator already rejects equality between different value kinds before asking `enact_value_equal`, so:

```text
'hello=="hello".
```

fails with `ENACT_ERR_TYPE_EQUALITY_MISMATCH`.

This is intentional and preserves atoms as symbols rather than text aliases.

## 8. Test Strategy

Regression tests cover:

- token output for quoted atoms
- reserved-word atom payloads
- direct evaluation and printing
- assignment and lookup
- equality and inequality
- list construction
- set/list builtins
- higher-order builtins
- atom values loaded from a script file
- malformed literal forms and type misuse

Unit tests cover:

- value copy/equality/free behavior
- AST clone/free behavior
- evaluator literal behavior
