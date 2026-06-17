# Slice 043: Inherited Method Dispatch Phase 1 Requirements

## Scope

Slice 043 extends object method dispatch from direct class lookup to single-superclass chain lookup:

```text
class Node < Object
Node.value() := 1
class Leaf < Node
(new Leaf).value()
```

The slice keeps the inheritance model intentionally narrow. Classes still have one superclass, and method dispatch walks that chain from the receiver class toward `Object`.

## Functional Requirements

### Method Lookup

- `object.method(args)` shall first check an object attribute named `method`, preserving existing attribute-call behavior.
- If no object attribute exists, dispatch shall search for a method on `classof(object)`.
- If the direct class does not define the method, dispatch shall continue through its superclass chain.
- The first method found while walking from subclass to superclass shall be selected.
- A subclass method shall override a same-named superclass method.
- A method inherited from a superclass shall bind `self` to the original receiver object.
- A method inherited through multiple single-superclass levels shall be callable.

### Evaluation Boundaries

- Receiver evaluation and object type checking shall keep the Slice 042 behavior.
- Object attributes shall continue to shadow inherited methods.
- Missing methods across the whole superclass chain shall report `ENACT_ERR_ATTRIBUTE_UNBOUND`.
- Method arity shall still require an exact argument count.
- If a subclass override has the wrong arity for a call, dispatch shall report `ENACT_ERR_ARITY_MISMATCH` and shall not fall back to a superclass method with a matching arity.
- Impossible extra arguments for a wrong-arity inherited method shall not be evaluated.
- Runtime errors inside inherited method bodies shall propagate unchanged.

## Regression Requirements

Boundary coverage shall include:

- inherited zero-argument method dispatch
- inherited one-argument and multi-argument methods
- subclass override priority
- superclass method remaining callable on superclass instances after subclass override
- multi-level superclass chain lookup
- inherited method `self` binding to the subclass receiver
- inherited method calls inside higher-order list builtins
- object attribute callable shadowing an inherited method
- lexical capture for inherited methods
- inherited method lookup from `Object`

Robustness coverage shall include:

- missing method across the superclass chain
- wrong inherited method arity without evaluating impossible arguments
- runtime error inside an inherited method body
- non-callable object attribute shadowing an inherited method
- wrong-arity subclass override not falling back to superclass
- wrong-arity direct method on subclass overriding an `Object` method

## Out of Scope

This slice does not implement:

- multiple inheritance
- ambiguity diagnostics
- `super`
- method partial application
- method values returned by `object.method` without a call
- class-level method dispatch
- class-level attributes or default attributes

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
