# Slice 080: Method Dot-Call Partial Application Requirements

## Goal

Slice 080 lets direct user-defined object method dot-calls produce partial bound method values when too few, but at least one, arguments are supplied:

```text
object.method(arg)
```

for a method that requires more arguments.

## Requirements

- A direct user-defined method dot-call with fewer than the method arity and at least one supplied argument shall return a bound object method value.
- Calling that returned value shall complete the original method call with the same captured receiver and already-supplied method arguments.
- Exact-arity direct method dot-calls shall keep their existing behavior.
- Zero-argument direct method dot-calls to non-zero-arity methods shall keep reporting `ENACT_ERR_ARITY_MISMATCH`.
- Over-applied direct method dot-calls shall keep reporting `ENACT_ERR_ARITY_MISMATCH` before evaluating impossible extra arguments.
- Valid-arity argument evaluation errors shall propagate normally.
- Direct method dot-call partial values shall print as `<function>`.
- Direct method dot-call partial values shall be accepted anywhere an existing callable is accepted, including `map`, `filter`, `all`, `exists`, `collect`, `forEachDo`, and `reduce`.
- Object attributes shall continue to shadow class methods. If the attribute is callable, the existing callable partial-application behavior shall apply.
- Inherited and overridden methods shall use the existing method lookup and class linearization order before a partial value is created.
- The partial method value shall retain the selected receiver and method function at the time the partial is created.
- Later receiver attribute mutation shall remain visible through the retained receiver.
- Later variable rebinding shall not change the retained receiver.
- Later class method replacement shall not change existing partial method values.
- User-defined collection class methods shall support direct dot-call partial application.
- Native collection dot-call bridge methods shall keep the exact-arity behavior from Slices 074 through 077.

## Regression Requirements

Boundary coverage shall include:

- one missing argument on a direct method dot-call.
- immediate completion through chained call syntax.
- assignment of a partial direct method call and later completion.
- multi-argument partial application with more than one supplied argument.
- inherited method partial calls.
- overridden method partial calls.
- root `Object` inherited method partial calls.
- object attribute callable shadowing with partial application.
- later receiver attribute mutation observed by the partial.
- later variable rebinding not changing the retained receiver.
- later class method replacement not changing an existing partial.
- partial methods returning `self`.
- higher-order use with `map` and `filter`.
- user-defined collection class method partial calls.
- mutating method bodies completed through partial calls.
- exact-arity zero-argument methods still calling normally.
- partial values stored in lists.

Robustness coverage shall include:

- zero-argument calls to non-zero-arity methods.
- over-applied direct method calls without evaluating impossible extra arguments.
- valid-arity argument evaluation errors.
- zero-argument completion attempts on partial values.
- over-applied partial completion without evaluating impossible extra arguments.
- valid-arity partial completion argument evaluation errors.
- method body runtime errors after partial completion.
- non-callable object attributes shadowing methods.
- missing methods.
- non-object receivers.
- inconsistent class linearization diagnostics.
- native collection dot-call methods remaining exact-arity.
- user-defined collection method zero-argument arity mismatch.
- misuse of partial method values as integers.
- predicate result validation for direct method partials.
- reducer arity validation for direct method partials.

## Deferred

- `super` calls remain deferred.
- Method signature or source introspection remains deferred.
- Native collection method-table integration remains deferred.
- Native collection dot-call partial application remains deferred.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
