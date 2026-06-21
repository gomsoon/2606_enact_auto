# Slice 095: First-Class super.method Bound Values Core Requirements

## Goal

Slice 095 makes `super.method` readable as a first-class bound method value inside method bodies.

This complements the Slice 094 call form:

```text
super.method(args)
```

with the value form:

```text
super.method
```

## Requirements

- `super.method` shall be recognized as a special attribute-read form.
- The lexer shall continue to tokenize `super` as an ordinary identifier.
- Bare `super` shall remain ordinary identifier syntax.
- `super.method` shall only be valid while evaluating a user-defined method body with a known current supplier class.
- The selected super method shall be wrapped as a bound object method value.
- The bound value shall capture:
  - the same receiver object as `self`.
  - the class that supplied the selected super method.
  - any future partial-application arguments through the existing bound method path.
- Calling a captured `super.method` value later shall execute with the selected supplier as the current method supplier.
- `super.method` shall ignore instance attributes on `self` and search only user-defined class methods.
- Higher-order builtins shall accept `super.method` values wherever bound object method values are already accepted.
- If no active method context exists, `super.method` shall report the existing unbound-name diagnostic.
- If no later method is found, `super.method` shall report the existing unbound-attribute diagnostic.
- If the receiver class has inconsistent linearization, `super.method` shall report `ENACT_ERR_INCONSISTENT_LINEARIZATION`.

## Evaluation Boundaries

- Reading `super.method` in a subclass method shall return a callable bound object method value.
- The bound value shall remain callable after it is assigned to a local or returned from a method.
- Inherited methods shall use their own supplier as the starting point for `super.method` lookup.
- Higher-order list builtins shall apply `super.method` values.
- Bound `super.method` values shall support existing partial-application behavior.
- Multiple-inheritance lookups shall follow the checked class linearization order.

## Regression Requirements

Boundary coverage shall include:

- direct `super.method` read and call.
- higher-order builtin use with `super.method`.
- inherited method supplier context.
- partial application from a `super.method` value.
- nested supplier capture after returning a `super.method` value.
- multiple-inheritance supplier ordering.

Robustness coverage shall include:

- `super.method` outside a method body.
- no superclass method found.
- missing method names.
- missing arguments after reading a super method value.
- extra arguments after reading a super method value.
- numeric misuse of the returned bound method value.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
