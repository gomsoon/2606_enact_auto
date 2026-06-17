# Slice 044: attrs(obj) Basic Introspection Design

Related requirements: [docs/slices/044-attrs-basic-introspection-requirements.md](/home/tprover/2606_enact_auto/docs/slices/044-attrs-basic-introspection-requirements.md)

## Design Objective

Add a low-risk object introspection builtin that exposes direct object state without changing parser, AST, evaluator, method dispatch, or class semantics.

The runtime surface is:

```text
attrs(obj)
```

and the result is a list of atom values:

```text
'x:'y:nil
```

## Object Runtime Helper

`object.c` keeps attribute storage private. To avoid exposing `EnactAttribute`, the runtime adds:

```c
int enact_object_attribute_names(const EnactObject *object, EnactList **out);
```

The helper returns a newly allocated list of atom values. Callers own the returned list and release it through normal value/list ownership.

Attributes are internally prepended when first defined. The helper walks the storage list and prepends each exported name to the result list, reversing storage order so the public result follows first-definition order.

Redefining an existing attribute updates the stored value in place and keeps the original name position.

## Builtin

`builtin.c` adds:

```c
static int enact_builtin_attrs(...)
```

The builtin:

1. requires an object argument
2. calls `enact_object_attribute_names`
3. wraps the returned `EnactList *` in `ENACT_VALUE_LIST`

The generic builtin application layer continues to enforce arity before the callback runs, so impossible extra arguments are not evaluated.

## Scope Boundaries

`attrs` reports direct object attributes only. It does not include:

- class methods
- inherited methods
- superclass names
- future class/default attributes

This keeps the builtin useful for object-state testing now and leaves method/class introspection for later slices.

## Deferred Work

Later slices may add:

- method introspection
- superclass introspection
- class/default attribute introspection
- ambiguity-oriented helpers such as `badAttrs`
