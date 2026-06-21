# Slice 094: super.method(...) Dot-Call Core Requirements

## Goal

Slice 094 exposes the first user-facing `super` method call form:

```text
super.method(args)
```

The feature reuses the Slice 092 super lookup helper and the Slice 093 method execution supplier context.

## Requirements

- `super.method(args)` shall be recognized as a special dot-call form.
- The lexer shall continue to tokenize `super` as an ordinary identifier.
- Bare `super` shall remain ordinary identifier syntax.
- `super.method(args)` shall only be valid while evaluating a user-defined method body with a known current supplier class.
- Super lookup shall use the receiver's runtime class and the current method supplier class from the active method execution context.
- Lookup shall begin strictly after the current method supplier in `classes(classof(self))`.
- The current supplier's method shall not be reselected.
- The selected super method shall execute with the same receiver object as `self`.
- Nested super calls shall update the current supplier to the class that supplied the selected super method.
- `super.method(args)` shall ignore instance attributes on `self` and search only user-defined class methods.
- Under-application of a selected super method shall reuse existing bound object method partial-application behavior.
- If no active method context exists, `super.method(args)` shall report the existing unbound-name diagnostic.
- If no later method is found, `super.method(args)` shall report the existing unbound-attribute diagnostic.
- If the receiver class has inconsistent linearization, `super.method(args)` shall report `ENACT_ERR_INCONSISTENT_LINEARIZATION`.

## Evaluation Boundaries

- Single-inheritance override calls shall reach the overridden superclass method.
- Multi-level override chains shall advance one supplier at a time.
- Multiple-inheritance calls shall follow the checked class linearization order.
- Inherited methods shall use their own supplier as the starting point for super lookup.
- Partially applied super methods shall complete through the existing bound method path.
- Instance attributes on `self` shall not shadow `super.method(...)`.

## Regression Requirements

Boundary coverage shall include:

- simple `super.f()` in a subclass override.
- chained `super.f()` calls across multiple overriding classes.
- multiple-inheritance ordering.
- `super.f()` inside an inherited method.
- `super.f(x)(y)` partial method completion.
- instance attribute shadow bypass.

Robustness coverage shall include:

- `super.method(...)` outside a method body.
- no superclass method found.
- missing super method names.
- missing arguments to selected super methods.
- extra arguments to selected super methods.
- first-class `super.method` reads remaining out of scope.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
