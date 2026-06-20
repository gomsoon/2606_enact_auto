# Slice 081: Native Collection Dot-Call Partial Application Design

Related requirements: [docs/slices/081-native-collection-dot-call-partial-application-requirements.md](/home/tprover/2606_enact_auto/docs/slices/081-native-collection-dot-call-partial-application-requirements.md)

## Reuse The Bound Collection Method Path

Slice 078 introduced `ENACT_VALUE_BOUND_COLLECTION_METHOD` for bare native collection method reads:

```text
collection.reduce
```

That value already supports partial application and knows how to insert the captured receiver into the underlying builtin argument list.

Slice 081 makes direct native collection dot-calls reuse that same callable value internally:

```text
collection.reduce(args)
```

When ordinary object attributes and user-defined class methods do not match, and the receiver is a collection object, the evaluator now:

1. creates a bound collection method value from the selected native collection builtin and receiver.
2. calls the existing generic callable application helper with the dot-call argument ASTs.

This removes the previous exact-only native collection dot-call helper and makes direct native collection dot-calls follow the same arity, partial application, argument evaluation, and builtin application rules as any other bound collection method value.

## Arity Behavior

The generic bound collection method callable path enforces the desired Slice 081 rules:

- exact arity evaluates and applies the builtin.
- under-arity with at least one supplied method argument returns a new bound collection method value.
- zero supplied arguments for a non-zero-arity native method reports `ENACT_ERR_ARITY_MISMATCH`.
- too many supplied arguments reports `ENACT_ERR_ARITY_MISMATCH` before evaluating impossible extra arguments.

Therefore:

```text
set((1,2)).reduce((acc,x)::acc+x)
```

now behaves like:

```text
r:=set((1,2)).reduce
r((acc,x)::acc+x)
```

and can later be completed with the remaining initial value:

```text
set((1,2)).reduce((acc,x)::acc+x)(0)
```

## Lookup And Shadowing

The existing dot-call lookup order is unchanged:

1. receiver object attributes.
2. user-defined class methods through class linearization.
3. native collection method bridge.

If a receiver object attribute exists, the evaluator still calls that attribute value through the generic callable path. This preserves function-valued attribute shadowing and non-callable attribute diagnostics.

If a user-defined class method exists, the evaluator creates a bound object method value and applies it. This means user-defined methods on `Set`, `Bag`, or subclasses still shadow native collection method names.

Only when no attribute or user-defined class method exists does the evaluator create a bound native collection method value.

## Exact Calls Still Share Diagnostics

Exact native collection dot-calls now pass through the bound collection method path too:

```text
set((1,2)).size()
set((1,2)).member(2)
set((set(list(1)),set(list(2)))).UNION()
```

The bound collection method application helper still delegates to `enact_builtin_apply_in_env`, so builtin diagnostics, collection class preservation, attribute preservation, Set duplicate suppression, Bag multiplicity, and aggregate semantics remain unchanged.

## Deferred Work

This slice does not add native collection method-table integration, `super`, method signature introspection, method source introspection, or collection display refinements.
