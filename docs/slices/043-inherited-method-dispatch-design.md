# Slice 043: Inherited Method Dispatch Phase 1 Design

Related requirements: [docs/slices/043-inherited-method-dispatch-requirements.md](/home/tprover/2606_enact_auto/docs/slices/043-inherited-method-dispatch-requirements.md)

## Design Objective

Use the existing single-superclass pointer from Slice 038 and the method table from Slice 042 to make inherited methods callable with the smallest runtime change.

The dispatch surface remains:

```text
object.method(args)
```

No parser or AST changes are required.

## Class Method Lookup

`enact_class_lookup_method` keeps its existing retained-result contract but changes its search scope:

1. start at the receiver class
2. scan that class's method table
3. if not found, continue to the superclass
4. stop at the first matching method or the end of the chain

This naturally implements override ordering because subclass tables are searched before superclass tables.

## Dot-Call Dispatch

`enact_eval_dot_call` keeps the Slice 042 order:

1. evaluate the receiver expression
2. require an object
3. look up an object attribute with the call name
4. if present, call the attribute value with existing callable rules
5. otherwise call `enact_class_lookup_method`

Because `enact_class_lookup_method` now searches the superclass chain, no extra evaluation code is needed.

## Self Binding

Inherited methods use the same `enact_eval_apply_method` path as direct methods. The receiver value passed to the evaluator is still the original object, so `self` refers to the subclass instance even when the method body was found on a superclass.

## Arity and Fallback

Method dispatch still requires exact arity. Once lookup selects the nearest method by name, arity is checked on that method. Dispatch does not search farther up the chain for a method with a different arity.

That rule keeps override behavior deterministic:

```text
Node.value() := 1
Leaf.value(x) := x
(new Leaf).value()  -> ENACT_ERR_ARITY_MISMATCH
```

## Deferred Work

Later slices should add:

- `super` calls for explicit superclass dispatch
- multiple inheritance and method ambiguity diagnostics
- bound method values, later added by Slice 079
- method partial application
- class-side dispatch
