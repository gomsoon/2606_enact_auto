# Slice 084: suppliers(Class, attr) Ambiguity Supplier Introspection Core Design

Related requirements: [docs/slices/084-suppliers-ambiguity-supplier-introspection-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/084-suppliers-ambiguity-supplier-introspection-core-requirements.md)

## Manual Mapping

The ENACT manual describes `suppliers(obj, attr)` as the classes that supply an attribute to an object. In the current implementation, class-level inherited behavior is represented by methods, while object attributes are instance-local.

Therefore Slice 084 maps the operation to method suppliers:

```text
class A < Object
class B < Object
A.f():=1
B.f():=2
class C < (A,B)
suppliers(C,'f)        -> <class A>:<class B>:nil
```

The result is an ordinary ENACT list of class values. This matches the existing class introspection style and keeps native Set-returning manual compatibility for a later collection-focused slice.

## Effective Suppliers

`suppliers` reuses the effective supplier model introduced for `badAttrs`:

1. Direct methods on a class supply that method name from that class.
2. Direct methods mask same-named inherited methods from that class's superclasses.
3. Inherited suppliers that are not masked are merged by supplier class identity.

This makes common-ancestor diamonds deduplicate to the single supplier:

```text
class Top < Object
Top.f():=0
class A < Top
class B < Top
class C < (A,B)
suppliers(C,'f)        -> <class Top>:nil
```

But a branch override creates two suppliers:

```text
class Top < Object
Top.f():=0
class A < Top
A.f():=1
class B < Top
class C < (A,B)
suppliers(C,'f)        -> <class A>:<class Top>:nil
```

## Target-Class Masking

The queried class's own direct method is returned as the single supplier:

```text
class A < Object
class B < Object
A.f():=1
B.f():=2
class C < (A,B)
C.f():=3
suppliers(C,'f)        -> <class C>:nil
```

This keeps `suppliers` aligned with the effective behavior seen by users and makes direct disambiguation inspectable.

## Diagnostics

The first argument uses the existing class type diagnostic. The second argument must be a quoted atom, so Slice 084 adds `ENACT_ERR_TYPE_EXPECTED_ATOM` with message `atom value required`.

## Inconsistent Linearization

`suppliers` does not call the class linearization helper. It walks direct superclass links and effective suppliers directly, so it remains available even when `classes(Class)`, `superiors(Class)`, and method dispatch would report `ENACT_ERR_INCONSISTENT_LINEARIZATION`.

This mirrors `badAttrs`: both operations inspect an inheritance problem without depending on a successful method resolution order.

## Deferred Work

This slice does not add object-argument `suppliers(obj, attr)`, native Set-returning manual compatibility, native collection method introspection, `super`, method signature introspection, or method source introspection.

Existing `OK(Class)` remains the Slice 053 linearization-consistency predicate. A later slice can decide whether to add a separate manual-style attribute-uniqueness predicate or extend `OK` with method-name ambiguity once the compatibility contract is explicit.
