# Slice 056: Collection Payload Core + size/member for Set/Bag Design

Related requirements: [docs/slices/056-collection-payload-size-member-requirements.md](/home/tprover/2606_enact_auto/docs/slices/056-collection-payload-size-member-requirements.md)

## Hidden Payload

`EnactObject` now carries hidden collection metadata:

```c
EnactCollectionKind collection_kind;
EnactList *collection_items;
```

The payload is separate from user attributes, so `attrs(set())` and `attrs(bag())` continue to return `nil`.

## Collection Kind Detection

Object construction derives the collection kind from the object's class:

- `Set` or a subclass of `Set` becomes `ENACT_COLLECTION_SET`.
- `Bag` or a subclass of `Bag` becomes `ENACT_COLLECTION_BAG`.
- all other objects remain `ENACT_COLLECTION_NONE`.

This makes `set()`, `new Set`, and `new SubclassOfSet` share the same empty-payload behavior.

## Builtin Bridge

`size` and `member` now use a shared list-or-collection input helper. Lists continue to pass through unchanged. Collection objects expose their hidden list payload to these read-only builtins. Since Slice 056 only creates empty payloads, the observed collection results are:

```text
size(set()) == 0
member(x,set()) == false
```

Non-collection objects still use the established list diagnostic:

```text
ENACT_ERR_TYPE_EXPECTED_LIST
```

## Deliberately Narrow Scope

Other list builtins remain list-only for this slice. That keeps collection payload introduction separate from collection mutation and set-operation semantics.
