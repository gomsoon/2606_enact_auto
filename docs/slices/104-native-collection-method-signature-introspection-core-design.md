# Slice 104: Native Collection Method Signature Introspection Core Design

Related requirements: [docs/slices/104-native-collection-method-signature-introspection-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/104-native-collection-method-signature-introspection-core-requirements.md)

## Contract

Slice 104 keeps the existing method introspection surface:

```text
methodArity(class_or_object, 'methodName)
methodParams(class_or_object, 'methodName)
```

The change is a focused fallback: after checked user-defined method lookup fails, Set-like and Bag-like classes may resolve signatures through the native collection method table.

## Lookup Order

The lookup order intentionally matches normal dot-call behavior:

1. Resolve the first argument to a class, using the object's runtime class when needed.
2. Run checked user-defined method lookup.
3. If a user-defined method is selected, report that method's signature.
4. Otherwise, if the class is Set-like or Bag-like, search the native collection method table.
5. If no native method is selected, return `nil`.

This preserves user-defined method priority:

```text
Set.member(x,y):=x
methodArity(set(), 'member)  -> 2
methodParams(set(), 'member) -> 'x:'y:nil
```

## Native Signature Shape

Native collection method table entries point at an existing builtin plus a receiver argument index. Method introspection reuses that metadata but hides the receiver, because callers see the method as receiver-bound:

```text
member(value, collection)
methodArity(set(), 'member)  -> 1
methodParams(set(), 'member) -> 'value:nil

reduce(function, initial, collection)
methodArity(set(), 'reduce)  -> 2
methodParams(set(), 'reduce) -> 'function:'initial:nil
```

Zero-visible-argument native methods report the same shape as zero-argument user methods:

```text
methodArity(set(), 'size)  -> 0
methodParams(set(), 'size) -> nil
```

## Runtime Reuse

`enact_class_collection_kind` is now available outside `object.c`, allowing builtin introspection to classify Set-like and Bag-like classes with the same inheritance-aware helper used by object construction and collection behavior.

`methodParams` shares the native collection parameter-list builder with `callableParams` for bound native collection method values. The helper skips the receiver index and, when needed, any already captured method arguments.

## Introspection Boundaries

Slice 104 only exposes arity and parameter names for native collection methods. The rest of the method introspection family remains user-defined-method-only:

- `methods`
- `effectiveMethods`
- `methodSupplier`
- `methodSuppliers`

This avoids implying a source class or supplier for builtin-backed table entries before there is a richer native method provenance model.

## Deferred Work

This slice does not add native method supplier metadata, native methods to method-name listings, callable source/body metadata, or richer signature records.
