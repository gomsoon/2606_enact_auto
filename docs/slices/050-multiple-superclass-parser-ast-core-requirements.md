# Slice 050: Multiple-Superclass Parser + AST Core Requirements

## Goal

Slice 050 exposes the direct-superclass list runtime from Slice 049 through the class-definition syntax and AST.

## Requirements

- The parser shall accept the existing single-superclass form:
  - `class C < A`
- The parser shall accept a tuple-like multiple-superclass form:
  - `class C < (A,B)`
  - `class C < (A,B,D)`
- Multiple-superclass syntax shall require at least two identifiers inside parentheses.
- Superclass entries shall be identifier names in this slice.
- `AST_CLASS_DEF` shall store an ordered `EnactAstList` of superclass expressions instead of one superclass expression.
- Class definition evaluation shall evaluate superclass entries left-to-right as class values.
- A class definition shall fail with `ENACT_ERR_NAME_UNBOUND` when any superclass identifier is unbound.
- A class definition shall fail with `ENACT_ERR_TYPE_EXPECTED_CLASS` when any superclass identifier resolves to a non-class value.
- `EnactClass` construction shall support an ordered list of direct superclasses.
- `supers(C)` shall return all direct superclasses in declared order.
- Existing single-superclass behavior shall remain compatible.

## Deferred

- Ambiguous method-resolution diagnostics are deferred.
- A full multiple-inheritance linearization rule is deferred.
- `superiors(Class)` and `classes(Class)` keep following the existing first-direct-superclass chain in this slice.
