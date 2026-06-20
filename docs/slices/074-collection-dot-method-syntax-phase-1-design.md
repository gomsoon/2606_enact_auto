# Slice 074: Collection Dot-Method Syntax Phase 1 Design

Related requirements: [docs/slices/074-collection-dot-method-syntax-phase-1-requirements.md](/home/tprover/2606_enact_auto/docs/slices/074-collection-dot-method-syntax-phase-1-requirements.md)

## Runtime Shape

The parser already represents `receiver.name(args)` as a call whose callee is an attribute expression. Existing evaluator dispatch therefore remains the natural integration point:

1. evaluate the receiver.
2. require an object receiver.
3. check object attributes.
4. check user-defined class methods through the class linearization.
5. if no attribute or class method exists, check for a supported collection dot method.

This preserves the established OO shadowing rule: direct object attributes win over class methods, and user-defined class methods win over the collection bridge.

## Collection Bridge

The bridge is intentionally narrow in this phase. It recognizes these names only:

```text
size
member
insert
remove
```

Each name maps to the existing builtin table entry. The receiver is inserted into the builtin argument array at the same position used by the free builtin form:

```text
collection.size()          -> size(collection)
collection.member(value)   -> member(value, collection)
collection.insert(value)   -> insert(value, collection)
collection.remove(value)   -> remove(value, collection)
```

The method surface uses exact arity. A wrong-arity dot call reports `ENACT_ERR_ARITY_MISMATCH` before evaluating impossible extra argument expressions, matching the safety policy already used by ordinary method dispatch.

## Environment Semantics

The bridge uses `enact_builtin_lookup` directly rather than looking up same-named values in the current environment. This makes collection dot methods part of the collection surface, not a dynamic alias for top-level bindings. For example, rebinding `size` can break `size(set())` without changing `set().size()`.

## Non-Collection Objects

Non-collection objects do not get synthetic methods from this bridge. If an ordinary object has no matching attribute or class method, the existing `ENACT_ERR_ATTRIBUTE_UNBOUND` diagnostic remains unchanged.

## Deferred Work

This slice deliberately avoids a native method-table refactor. A later slice can add builtin-backed class methods if the project wants `methods(Set)` to expose native collection operations or wants bound collection method values. The focused evaluator bridge keeps this phase small while unlocking the manual-style call surface for the most common collection operations. Slice 075 later extends the same bridge to collection algebra and predicate helpers.
