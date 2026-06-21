# Slice 089: Method Lookup Supplier Metadata Core Requirements

## Goal

Slice 089 records the class that supplied a selected user-defined method during method lookup.

This is an internal runtime slice. It does not add new surface syntax, new printed output, or new user-facing introspection helpers. Its purpose is to preserve method provenance for later work such as `super` and effective-method metadata without changing current dispatch behavior.

## Requirements

- Method lookup shall continue to use the checked `classes(Class)` linearization order introduced by Slice 052.
- A new runtime lookup API shall return both:
  - the retained method function selected for dispatch.
  - the class in the linearization that directly owns the selected method.
- The existing `enact_class_lookup_method` API shall remain available and keep its retained-function result contract.
- Direct method lookup shall report the receiver class as the supplier.
- Inherited method lookup shall report the superclass that directly owns the selected method.
- Subclass method overrides shall report the subclass as the supplier.
- Missing method lookup shall return null method and null supplier while still reporting a consistent linearization.
- Inconsistent class linearization shall continue to report inconsistency before returning any method or supplier.
- Bound object method values created from user-defined method lookup shall retain the supplier class metadata.
- Bound object method partial application shall preserve the supplier class metadata.
- Bound object methods created through the older constructor shall remain valid and simply have no supplier metadata.
- User-visible method dispatch, attribute shadowing, native collection method bridging, printing, equality, and diagnostics shall remain unchanged.

## Evaluation Boundaries

- Object attributes shall still shadow user-defined class methods.
- User-defined class methods shall still shadow native collection dot-method bridges.
- Attribute reads and dot-calls shall both attach supplier metadata when they bind a user-defined object method.
- Over-application shall still report `ENACT_ERR_ARITY_MISMATCH` without evaluating impossible extra arguments.
- Non-object attribute receivers shall still report `ENACT_ERR_TYPE_EXPECTED_OBJECT`.
- Missing attributes or methods shall still report `ENACT_ERR_ATTRIBUTE_UNBOUND`.
- Inconsistent method lookup shall still report `ENACT_ERR_INCONSISTENT_LINEARIZATION`.

## Regression Requirements

Boundary coverage shall include:

- direct method attribute reads.
- direct method dot-calls.
- inherited method attribute reads.
- inherited method dot-calls.
- subclass overrides.
- multiple-inheritance linearization selection.
- bound method partial application.
- attribute shadowing over methods.
- retained receiver behavior for partial bound methods.
- C unit coverage for supplier identity and supplier preservation.

Robustness coverage shall include:

- missing method attribute reads.
- missing method dot-calls.
- inconsistent linearization during attribute reads.
- inconsistent linearization during dot-calls.
- inherited method over-application.
- attribute shadowing with non-callable values.
- non-object attribute receivers.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
