# Slice 042: Single-Class Method Definition + Dispatch Core Requirements

## Scope

Slice 042 introduces the first executable object methods:

```text
Class.method(args) := body
object.method(args)
```

The slice is intentionally limited to methods defined directly on the receiver object's class. Superclass lookup, overriding semantics across inheritance, multiple inheritance, method ambiguity, and class-level dispatch remain out of scope.

## Functional Requirements

### Method Definition

- `Class.method(args) := body` shall define a method named `method` on the class value produced by `Class`.
- Zero-argument methods shall be accepted:

```text
Node.get() := self.x
```

- Multi-argument methods shall be accepted:

```text
Node.add(a,b) := a+b
```

- A method definition shall return the created function value, matching named function definition behavior.
- Method bodies shall capture the lexical environment at definition time, like ordinary functions.
- Defining a method with an existing name on the same class shall replace the previous method.
- Method parameters shall be unique.
- `self` shall be reserved as the receiver binding inside method bodies and shall not be accepted as a method parameter name.

### Method Dispatch

- `object.method(args)` shall dispatch to a method on `classof(object)` when no object attribute named `method` exists.
- Method dispatch shall bind `self` to the receiver object while evaluating the method body.
- Method arguments shall bind to method parameters using existing function argument rules, except that this slice requires exact arity and does not produce partial method applications.
- Attribute reads and assignments through `self` shall work in method bodies:

```text
Node.set(v) := self.x := v
Node.get() := self.x
```

- Function-valued object attributes shall keep existing behavior and shadow same-named class methods for dot calls:

```text
n.value := x::x+10
n.value(5)
```

### Evaluation Boundaries

- The receiver expression shall be evaluated before method lookup.
- If the receiver is not an object, dispatch shall report `ENACT_ERR_TYPE_EXPECTED_OBJECT`.
- If neither an object attribute nor a direct class method exists for the dot-call name, dispatch shall report `ENACT_ERR_ATTRIBUTE_UNBOUND`.
- If the method arity does not exactly match the supplied argument count, dispatch shall report `ENACT_ERR_ARITY_MISMATCH` before evaluating impossible extra arguments.
- If a dot-call name exists as a non-callable object attribute, existing attribute-call behavior shall report `ENACT_ERR_TYPE_EXPECTED_FUNCTION`.

## Regression Requirements

Boundary coverage shall include:

- tokenization of method definition syntax
- zero-argument method definition and dispatch
- one-argument and multi-argument methods
- `self` attribute read
- `self` attribute assignment
- object-valued return through `self`
- lexical capture at method definition time
- method replacement on the same class
- function-valued attribute shadowing a method
- higher-order list builtin composition with method calls
- class alias method definition
- newline-terminated script execution

Robustness coverage shall include:

- missing methods
- wrong method arity without evaluating impossible extra arguments
- method definition on a non-class value
- dispatch on a non-object value
- dispatch on a class value
- method body runtime failures
- reserved `self` parameter rejection
- duplicate method parameter rejection
- non-identifier method parameters
- lack of superclass method lookup in this slice
- non-callable attribute shadowing a method

## Out of Scope

This slice does not implement:

- superclass method lookup
- method override ordering across inheritance
- multiple inheritance
- class-level method dispatch
- method partial application
- method values returned by `object.method` without a call, later added by Slice 079
- `super`
- method visibility or access control

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
