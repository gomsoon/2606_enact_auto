# Slice 083: badAttrs(Class) Ambiguity Introspection Core Design

Related requirements: [docs/slices/083-badattrs-ambiguity-introspection-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/083-badattrs-ambiguity-introspection-core-requirements.md)

## Manual Mapping

The ENACT manual describes `badAttrs obj` as inherited attributes that come from more than one superclass. In the current implementation, class-level attributes are represented by methods, while ordinary object attributes are instance-local and are not inherited through classes.

Therefore Slice 083 maps `badAttrs(Class)` to inherited method-name ambiguity:

```text
class A < Object
class B < Object
A.f():=1
B.f():=2
class C < (A,B)
badAttrs(C)        -> 'f:nil
```

The result is an ordinary ENACT list of atom names, matching the existing `methods(Class)` and `attrs(object)` result style.

## Effective Suppliers

The runtime computes effective method suppliers per class branch:

1. Direct methods on a class supply that method name from that class.
2. Direct methods mask same-named inherited methods from that class's superclasses.
3. Inherited suppliers that are not masked are merged by supplier class identity.

This makes common-ancestor diamonds non-ambiguous when the same ancestor is the only supplier:

```text
class Top < Object
Top.f():=0
class A < Top
class B < Top
class C < (A,B)
badAttrs(C)        -> nil
```

But a branch override creates two supplier classes:

```text
class Top < Object
Top.f():=0
class A < Top
A.f():=1
class B < Top
class C < (A,B)
badAttrs(C)        -> 'f:nil
```

## Target-Class Masking

The queried class's own direct methods mask inherited ambiguity:

```text
class A < Object
class B < Object
A.f():=1
B.f():=2
class C < (A,B)
C.f():=3
badAttrs(C)        -> nil
```

This follows the manual's disambiguation guidance: redefining the attribute in the common child masks the inherited occurrences.

## Inconsistent Linearization

`badAttrs` does not call the class linearization helper. It walks direct superclass links and effective suppliers directly, so it remains available even when `classes(Class)`, `superiors(Class)`, and method dispatch would report `ENACT_ERR_INCONSISTENT_LINEARIZATION`.

This makes `badAttrs` an inspection tool for problematic graphs rather than another operation blocked by the same problem.

## Deferred Work

This slice does not add `suppliers(obj, attr)`, native collection method introspection, `super`, method signature introspection, or method source introspection. `suppliers(Class, attr)` is later added by Slice 084.

Existing `OK(Class)` remains the Slice 053 linearization-consistency predicate. A later slice can decide whether to add a separate manual-style attribute-uniqueness predicate or extend `OK` with method-name ambiguity once the compatibility contract is explicit.
