# Slice 054: Inconsistent Linearization Diagnostics Core Requirements

## Goal

Slice 054 turns the consistency predicate from Slice 053 into a runtime diagnostic policy for operations that require a valid class linearization.

## Requirements

- A new diagnostic code shall report inconsistent multiple-inheritance linearization:

```text
ENACT_ERR_INCONSISTENT_LINEARIZATION
```

- `OK(Class)` shall keep returning `false` for inconsistent class graphs.
- `classes(Class)` shall report `ENACT_ERR_INCONSISTENT_LINEARIZATION` when `OK(Class)` would be `false`.
- `superiors(Class)` shall report `ENACT_ERR_INCONSISTENT_LINEARIZATION` when `OK(Class)` would be `false`.
- Method dispatch shall report `ENACT_ERR_INCONSISTENT_LINEARIZATION` before selecting any method on an inconsistent receiver class.
- The same diagnostic shall propagate through subclasses whose direct or transitive superclass graph is inconsistent.
- Direct-only helpers shall remain usable on inconsistent classes:
  - `supers(Class)`
  - `methods(Class)`
- Object construction, `classof`, direct object attributes, and `attrs` shall remain usable on objects whose class graph is inconsistent.
- Existing type and arity diagnostics shall remain unchanged for non-class arguments and over-application.
- Consistent class graphs shall preserve existing `classes`, `superiors`, and method dispatch behavior.

## Regression Requirements

Boundary coverage shall include:

- `OK` still returning `false` without raising an error.
- `supers` and `methods` still succeeding on an inconsistent class.
- `classof` and `attrs` still succeeding for objects of inconsistent classes.
- higher-order use of `OK` over mixed consistent and inconsistent classes.
- normal `classes` and method dispatch still succeeding for consistent multiple-inheritance graphs.

Robustness coverage shall include:

- `classes` on an inconsistent class.
- `superiors` on an inconsistent class.
- `classes(classof(object))` for an inconsistent object class.
- `superiors(classof(object))` for an inconsistent object class.
- higher-order list builtins that force `classes` on an inconsistent class.
- method dispatch with methods available on root, direct, and indirect superclasses.
- subclasses of an inconsistent class.

## Deferred

- Detailed conflict reports naming the conflicting classes remain deferred.
- `suppliers` remains deferred. `badAttrs` is later added by Slice 083.
- Class-definition-time rejection of inconsistent graphs remains deferred; the diagnostic is raised when linearization-dependent behavior is requested.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
