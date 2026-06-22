# Slice 107: hasAttr Predicate Requirements

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slices:

- [docs/slices/039-object-attributes-phase-1-requirements.md](/home/tprover/2606_enact_auto/docs/slices/039-object-attributes-phase-1-requirements.md)
- [docs/slices/041-object-attribute-assignment-requirements.md](/home/tprover/2606_enact_auto/docs/slices/041-object-attribute-assignment-requirements.md)
- [docs/slices/106-hasmethod-predicate-requirements.md](/home/tprover/2606_enact_auto/docs/slices/106-hasmethod-predicate-requirements.md)

## Goal

Add a small runtime predicate for testing whether an object currently owns an attribute:

```text
hasAttr(object, 'attrName)
```

This mirrors Slice 106's `hasMethod` predicate but stays focused on object attributes rather than method dispatch.

## Functional Requirements

- Add a builtin named `hasAttr`.
- `hasAttr` shall have arity two.
- The first argument shall be an object value.
- The second argument shall be an atom naming the attribute.
- The result shall be `true` when the object has the named runtime attribute.
- The result shall be `false` when the object does not have the named runtime attribute.
- The result shall be boolean and shall not expose the attribute value.
- `hasAttr` shall be a normal first-class builtin and support existing builtin partial-application behavior.
- User shadowing of `hasAttr` shall behave like other builtins.

## Boundary Examples

```text
hasAttr(new Object, 'x) -> false
hasAttr(new Object with x:=1, 'x) -> true
hasAttr(new Object with x:=false, 'x) -> true
hasAttr(new Object with x:=nil, 'x) -> true
```

`hasAttr` observes runtime attributes only:

```text
class Node < Object
Node.x():=1
hasAttr(new Node, 'x) -> false
hasMethod(new Node, 'x) -> true
```

Collections are objects, so ordinary object attributes on collections are visible:

```text
hasAttr(set() with tag:=true, 'tag) -> true
hasAttr(set(), 'size) -> false
```

## Error Requirements

- Non-object first arguments shall fail with `ENACT_ERR_TYPE_EXPECTED_OBJECT`.
- Non-atom second arguments shall fail with `ENACT_ERR_TYPE_EXPECTED_ATOM`.
- Arity errors shall use the existing builtin arity diagnostics.

## Non-Goals

- Do not add class-level attribute declarations.
- Do not consult method lookup, native collection method tables, `badAttrs`, or `suppliers`.
- Do not return supplier metadata, attribute values, or structured records.

## Regression Requirements

- Add boundary tests for present, missing, reassigned, false-valued, nil-valued, function-valued, nested-object, class-instance, and collection attributes.
- Add robustness tests for arity mismatch, invalid receiver types, invalid name types, boolean-result misuse, partial-application misuse, and user shadowing.
- Keep handwritten source coverage reporting unchanged.
