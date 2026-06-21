# Slice 093: Method Execution Supplier Context Core Requirements

## Goal

Slice 093 carries the supplier class selected by method dispatch into the runtime execution context for the method body.

This prepares the evaluator for a future `super.method(...)` syntax without exposing new source syntax yet.

## Requirements

- The evaluator shall track a current method execution context while evaluating a user-defined method body.
- The context shall include:
  - the receiver's runtime class.
  - the class that supplied the currently executing method.
  - a link to the previous method context for nested method calls.
- Direct dot-calls shall keep using the existing supplier-aware method lookup path.
- Bound object method calls shall pass their retained supplier class into method-body execution.
- Partially applied bound object methods shall preserve supplier metadata through the existing bound method extension path.
- Methods created through the older no-supplier bound method constructor shall remain valid and shall execute with no supplier context.
- The context shall not be stored as a normal `EnactEnv` binding.
- Ordinary functions, lambdas, builtins, native collection methods, and top-level evaluation shall keep existing behavior.
- `super` shall remain ordinary identifier syntax in user programs for this slice.

## Evaluation Boundaries

- Inherited bound method reads shall still call the inherited method.
- Partially applied inherited bound methods shall still complete correctly.
- Direct dot-call partial application shall still complete correctly.
- Nested `self.method(...)` calls shall still work inside method bodies.
- Higher-order builtin calls from a method body shall continue to call bound object methods correctly.
- Multiple-inheritance method dispatch shall keep using the existing linearization order.

## Regression Requirements

Boundary coverage shall include:

- inherited bound method read and call.
- inherited bound method partial application.
- direct dot-call partial application.
- nested `self` method calls.
- higher-order builtin use from a method body.
- multiple-inheritance dispatch guardrails.

Robustness coverage shall include:

- `super` as an ordinary unbound identifier inside a method body.
- missing arguments for inherited bound methods.
- over-application of partially applied bound methods.
- missing bound method reads.
- non-callable object attributes shadowing methods.
- inconsistent-linearization diagnostics for method reads.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
