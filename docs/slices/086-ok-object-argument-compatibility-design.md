# Slice 086: OK Object-Argument Compatibility Design

Related requirements: [docs/slices/086-ok-object-argument-compatibility-requirements.md](/home/tprover/2606_enact_auto/docs/slices/086-ok-object-argument-compatibility-requirements.md)

## Compatibility Mapping

Slice 086 reuses the class-or-object argument resolver introduced for Slice 085:

1. Class values are used directly.
2. Object values are mapped to `enact_object_class(object)`.
3. Other values report `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT`.

After this mapping, `OK` delegates to the same linearization-consistency helper it used before:

```text
OK(new C) == OK(classof(new C))
```

## Predicate Scope

`OK` remains the Slice 053 linearization-consistency predicate. It answers whether the selected class can be linearized under the current multiple-inheritance rule.

This slice deliberately does not fold `badAttrs` or `suppliers` ambiguity into `OK`. Method-name ambiguity can still be inspected explicitly:

```text
badAttrs(x)
suppliers(x,'f)
```

## Higher-Order Behavior

Because `OK` is a normal builtin, accepting object values also makes the higher-order forms work naturally:

```text
map(OK, (new A, new B, new C))
filter(OK, (new A, new B, new C))
all(OK, (new Object, new A))
```

The returned list elements from `filter` remain the original object values. `OK` only reads each object's class; it does not replace values with class values.

## Deferred Work

This slice does not make other class introspection helpers accept object arguments. Slice 087 later adds that compatibility for `supers` and `superiors`; Slice 088 later adds it for `classes` and `methods`. This slice also does not change `OK` into an attribute-ambiguity predicate.
