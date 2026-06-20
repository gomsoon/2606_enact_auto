# Slice 079: General Bound Object Method Values Core Requirements

## Goal

Slice 079 lets user-defined object methods be read as callable values:

```text
object.method
```

The resulting value captures the receiver object and can be called later.

## Requirements

- Reading a user-defined method from an object shall return a callable value.
- Calling that value shall behave like the corresponding object method call with the original receiver captured as `self`.
- Bound object method values shall print as `<function>`.
- Bound object method values shall be accepted anywhere an existing callable is accepted, including `map`, `filter`, `all`, `exists`, `collect`, `forEachDo`, and `reduce`.
- Bound object method values shall support partial application when at least one new argument is supplied and fewer than the method arity has been reached.
- Zero-argument calls to non-zero-arity bound object methods shall report `ENACT_ERR_ARITY_MISMATCH`.
- Over-application shall report `ENACT_ERR_ARITY_MISMATCH` before evaluating impossible extra arguments.
- Argument evaluation errors for valid-arity calls shall propagate normally.
- Object attributes shall continue to shadow class methods for bare reads and calls.
- Inherited method lookup shall use the existing class linearization and consistency diagnostics.
- A method value shall capture the method function selected at read time.
- A method value shall retain the receiver object selected at read time, while still observing later mutations to that object.
- Direct dot-calls such as `object.method(args)` shall keep the existing exact-arity behavior in this slice and shall not create partial method values. Slice 080 later adds direct dot-call partial application for user-defined methods.
- User-defined collection class methods shall shadow native collection method values for bare reads, matching existing dot-call shadowing.
- Native collection method values shall continue to work when no user-defined class method shadows the native name.

## Regression Requirements

Boundary coverage shall include:

- bare zero-argument method reads.
- zero-argument bound method calls.
- one-argument and multi-argument bound method calls.
- bound method partial application.
- inherited method values.
- overridden method values.
- object attribute shadowing.
- higher-order use with list traversal builtins.
- dynamic observation of later receiver attribute mutation.
- read-time method function capture across later method replacement.
- read-time receiver capture across later variable rebinding.
- user-defined collection method shadowing native collection methods.
- bound methods returning `self`.
- bound methods stored in lists and assigned to variables.
- root `Object` method values.

Robustness coverage shall include:

- missing methods remaining unbound.
- non-object attribute reads.
- wrong arity for zero-, one-, and multi-argument bound methods.
- impossible extra arguments not being evaluated after arity rejection.
- valid-arity argument evaluation errors.
- partial bound method arity errors.
- method body runtime errors.
- callable arity validation inside higher-order builtins.
- predicate result validation.
- object attributes shadowing methods with non-callable values.
- misuse of bound method values as integers, booleans, and lists.
- inconsistent class linearization diagnostics during method lookup.

## Deferred

- Direct dot-call partial application remains deferred in this slice and is later added by Slice 080.
- `super` calls remain deferred.
- Method signature or source introspection remains deferred.
- Native collection method-table integration remains deferred.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
