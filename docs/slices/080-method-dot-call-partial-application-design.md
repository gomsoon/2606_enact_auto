# Slice 080: Method Dot-Call Partial Application Design

Related requirements: [docs/slices/080-method-dot-call-partial-application-requirements.md](/home/tprover/2606_enact_auto/docs/slices/080-method-dot-call-partial-application-requirements.md)

## Reuse The Bound Method Callable Path

Slice 079 introduced `ENACT_VALUE_BOUND_OBJECT_METHOD` for bare reads:

```text
object.method
```

Slice 080 makes direct user-defined method dot-calls reuse that same callable value internally:

```text
object.method(args)
```

When method lookup finds a user-defined method, the evaluator:

1. creates a bound object method value from the selected method and receiver.
2. calls the existing generic callable application helper with the dot-call argument ASTs.

This removes the previous exact-only direct method call helper and makes direct dot-calls follow the same arity, partial application, argument evaluation, and method-body application rules as any other bound object method value.

## Arity Behavior

The generic bound object method callable path already enforces the desired Slice 080 rules:

- exact arity evaluates and runs the method body.
- under-arity with at least one supplied argument returns a new bound object method value.
- zero supplied arguments for a non-zero-arity method reports `ENACT_ERR_ARITY_MISMATCH`.
- too many supplied arguments reports `ENACT_ERR_ARITY_MISMATCH` before evaluating impossible extra arguments.

Therefore:

```text
n.add(1)
```

now behaves like:

```text
f:=n.add
f(1)
```

when `add` needs more than one argument.

## Lookup And Shadowing

The existing dot-call lookup order is unchanged:

1. receiver object attributes.
2. user-defined class methods through class linearization.
3. native collection method bridge.

If an object attribute exists, the evaluator still calls that attribute value through the generic callable path. This preserves function-valued attribute shadowing and non-callable attribute diagnostics.

If a user-defined class method exists, the evaluator creates a bound object method value and applies it. Inherited methods, overridden methods, and inconsistent linearization diagnostics continue to come from the existing method lookup helper.

If no user-defined method exists and the receiver is a collection object, the native collection method bridge remains unchanged.

## Native Collection Boundary

Native collection dot-call methods continue to use the exact-arity bridge from Slices 074 through 077:

```text
set((1,2)).reduce((acc,x)::acc+x)
```

still reports `ENACT_ERR_ARITY_MISMATCH` because native collection dot-call partial application is outside this slice. Users can still get partial native collection method values through bare reads introduced in Slice 078:

```text
r:=set((1,2)).reduce
p:=r((acc,x)::acc+x)
p(0)
```

## Capture Semantics

Direct method dot-call partial values use the same capture semantics as Slice 079 bound object methods:

- the selected method function is retained when the partial is created.
- the receiver object is retained when the partial is created.
- later receiver attribute mutation remains visible through `self`.
- later variable rebinding does not affect the retained receiver.
- later class method replacement does not affect existing partial values.

## Deferred Work

This slice does not add `super`, method signature introspection, method source introspection, native collection method-table integration, or native collection dot-call partial application.
