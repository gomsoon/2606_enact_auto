# Slice 105: Native Collection Effective Method Listing Design

Related requirements: [docs/slices/105-native-collection-effective-method-listing-requirements.md](/home/tprover/2606_enact_auto/docs/slices/105-native-collection-effective-method-listing-requirements.md)

## Contract

Slice 105 keeps the public helper unchanged:

```text
effectiveMethods(class_or_object)
```

The result now includes both:

- user-defined effective methods selected by checked class linearization.
- native collection dot methods for Set-like and Bag-like classes.

## Lookup Shape

The builtin still starts with the Slice 091 helper:

```c
enact_class_effective_method_names(...)
```

That preserves user-defined method ordering, override masking, and inconsistent-linearization diagnostics.

After that succeeds, the builtin classifies the target with:

```c
enact_class_collection_kind(...)
```

For non-collection classes, the result is unchanged. For Set-like and Bag-like classes, native method names are copied from the native collection method table and appended to the user-defined list.

## Ordering And Masking

User-defined names stay first because they are the methods that class dispatch would select before the native collection bridge:

```text
class MySet < Set
MySet.local():=1
effectiveMethods(MySet) -> 'local:'size:'union:...:'reduce:nil
```

If a user-defined method has the same name as a native collection method, the native name is skipped:

```text
Set.member(x):=x
effectiveMethods(set()) -> 'member:'size:'union:...:'reduce:nil
```

This mirrors Slice 104's signature policy: user-defined method metadata wins first, and native metadata fills in only the discoverability gap.

## Boundaries

`methods` remains direct-only and continues to report only methods explicitly defined on the class. `methodSupplier` also remains user-defined-only because native collection table entries do not yet have class supplier provenance.

`effectiveMethods` therefore answers the dispatch-facing discovery question, while supplier and direct-declaration helpers keep their narrower meanings.

## Deferred Work

This slice does not add native supplier metadata, native method source/body metadata, or richer method records. Those can be added later if the native method table grows a provenance model.
