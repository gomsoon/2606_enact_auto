# Slice 096: Super Context Diagnostics Core Design

Related requirements: [docs/slices/096-super-context-diagnostics-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/096-super-context-diagnostics-core-requirements.md)

## Diagnostic Scope

The parser still reads:

```text
super.f
super.f()
```

as ordinary attribute and call AST shapes whose receiver expression is the identifier `super`.

The evaluator is the only layer that treats this shape specially. Slice 096 keeps that strategy and narrows the new diagnostic to the special evaluator path. Bare `super` continues through ordinary identifier lookup.

## Error Code

The new diagnostic is:

```c
ENACT_ERR_INVALID_SUPER_CONTEXT
```

with the message:

```text
super method access requires an active method context
```

This code is emitted only when the evaluator has recognized a super method access form but cannot find a complete current method context.

## Runtime Path

Slice 095 factored super lookup into:

```c
enact_eval_make_super_bound_method(...)
```

Both `super.f` and `super.f(...)` call this helper. Slice 096 changes the helper's context guard from:

```text
missing context -> ENACT_ERR_NAME_UNBOUND
```

to:

```text
missing context -> ENACT_ERR_INVALID_SUPER_CONTEXT
```

The rest of the lookup path remains unchanged.

## Ordinary super Names

This slice does not make `super` a lexer keyword or a standalone runtime value. These remain ordinary:

```text
super:=7
super
super:=x::x+1
super(2)
obj.super
self.super
```

Only `super.name` and calls whose callee is `super.name` enter the super-specific evaluator path.

## Escaped Function Behavior

The method context is dynamic evaluator state, not lexical environment state. A function that evaluates `super.f` after the method body has returned does not retain a super context:

```text
B.make():=()::super.f
m:=(new B).make()
m()
```

The final call reports `ENACT_ERR_INVALID_SUPER_CONTEXT`.

This keeps Slice 095's first-class `super.f` value as the intended way to capture a super method supplier.

## Deferred Work

This slice does not add bare `super` values, `super` attribute assignment, native collection `super` lookup, method source/signature metadata, or source-offset precision for super diagnostics.
