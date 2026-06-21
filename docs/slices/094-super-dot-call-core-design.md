# Slice 094: super.method(...) Dot-Call Core Design

Related requirements: [docs/slices/094-super-dot-call-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/094-super-dot-call-core-requirements.md)

## Syntax Strategy

Slice 094 does not add a lexer keyword or a new AST node.

The parser continues to read:

```text
super.f()
```

as a normal call whose callee is an attribute expression:

```text
AST_CALL(AST_ATTRIBUTE(AST_IDENTIFIER("super"), "f"), args)
```

The evaluator recognizes this exact call shape and routes it to a super-specific dot-call path. This keeps bare `super` as ordinary identifier syntax and avoids invalidating existing tokenization.

## Evaluation Rule

When the evaluator sees `super.method(args)`:

1. It checks that a current method execution context exists.
2. It reads the receiver object, receiver class, and current supplier class from that context.
3. It calls:

```c
enact_class_lookup_super_method_with_supplier(
    receiver_class,
    current_supplier,
    method_name,
    &method,
    &supplier,
    &consistent);
```

4. It wraps the selected method as a bound object method with the same receiver and the selected supplier class.
5. It applies that bound method through the existing callable path.

Reusing the bound method path gives super calls the same arity diagnostics, partial-application behavior, argument evaluation, and method-body context push/pop as ordinary method calls.

## Lookup And Shadowing

`super.method(...)` is intentionally class-method lookup only. It does not evaluate `super` as a value, and it does not inspect instance attributes on `self`.

This differs from ordinary `self.method(...)`, where an instance attribute named `method` shadows class method dispatch. The purpose of `super.method(...)` is to continue class method lookup after the current supplier.

## Nested Super Calls

The selected super method is applied with its supplier class. If that method body calls `super.other(...)`, the next lookup starts after the selected supplier, not after the original subclass supplier.

For example:

```text
classes(C) -> C:B:A:Object:nil
C.f() supplied by C
super.f() selects B.f
inside B.f, super.f() starts after B and can select A.f
```

## Diagnostics

This slice deliberately reuses existing diagnostics:

- no active method/supplier context: `ENACT_ERR_NAME_UNBOUND`.
- no later method found: `ENACT_ERR_ATTRIBUTE_UNBOUND`.
- inconsistent receiver class linearization: `ENACT_ERR_INCONSISTENT_LINEARIZATION`.
- arity mismatch: `ENACT_ERR_ARITY_MISMATCH`.

A dedicated invalid-super-context diagnostic remains deferred.

## Deferred Work

This slice does not add bare `super` values, first-class `super.method` reads, `super` attribute assignment, native collection `super` lookup, a dedicated super-context diagnostic, or method source/signature metadata.
