# Slice 051: Multiple-Inheritance Introspection Linearization Requirements

## Goal

Slice 051 updates class introspection so `superiors(Class)` and `classes(Class)` reflect multiple-superclass class definitions from Slice 050.

## Requirements

- `supers(Class)` shall remain direct-only and shall keep returning direct superclasses in declared order.
- `superiors(Class)` shall return the transitive superclass linearization for a class.
- `classes(Class)` shall return the inclusive class linearization:
  - the class itself
  - followed by `superiors(Class)`
- Multiple inheritance shall use declared superclass order as the local precedence order.
- Common superclasses shall appear only once in `superiors` and `classes`.
- For `class C < (A,B)` where both `A` and `B` extend `Object`:
  - `superiors(C)` shall return `<class A>:<class B>:<class Object>:nil`
  - `classes(C)` shall return `<class C>:<class A>:<class B>:<class Object>:nil`
- Single-inheritance behavior shall remain unchanged.
- `superiors` and `classes` shall preserve existing arity, type, and shadowing diagnostics.

## Deferred

- Ambiguous or inconsistent multiple-inheritance graphs shall not receive a dedicated diagnostic in this slice.
- Method dispatch shall keep the existing left-to-right recursive lookup policy.
- Inherited method introspection remains deferred.
