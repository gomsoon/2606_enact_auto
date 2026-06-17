# Slice 037: Root Object Runtime Core Requirements

## Scope

Slice 037 introduces the first runtime-visible object model values:

- a root class value named `Object`
- object instances created by `new Object`
- object-aware printing and `isObject`

This slice is intentionally small. It does not implement class declarations, fields, methods, inheritance, `with`, dot access, or class reflection helpers.

## Functional Requirements

### Root Class

- A fresh default environment shall define `Object`.
- `Object` shall evaluate to a class value.
- Printing `Object` shall produce `<class Object>`.
- `Object` is a normal environment binding for this slice and can be rebound by assignment.

### Object Creation

- `new Object` shall evaluate to a fresh object instance whose class is `Object`.
- Printing an instance shall produce `<object Object>`.
- `new` shall require the class expression to evaluate to a class value.
- When the target name is unbound, the existing unbound-name diagnostic shall be reported.
- When the target evaluates to a non-class value, evaluation shall report `ENACT_ERR_TYPE_EXPECTED_CLASS`.

### Syntax Boundaries

- `new` shall be parsed as `new` followed by an identifier.
- `new Object` shall be accepted with both `.` and top-level newline termination.
- `new(Object)` and `new Object()` shall remain out of scope and shall fail to parse.
- `new 1` shall fail to parse.

### Equality and Predicates

- Two references to the same object shall compare equal.
- Two separately created objects shall compare unequal.
- Two references to the same class value shall compare equal.
- Comparing an object and a class with `==` shall keep the existing different-kind equality error.
- `isObject(new Object)` shall return `true`.
- `isObject(Object)` shall return `false`.
- `atom(new Object)` shall return `true`, following the current rule that non-list values are atoms.

## Regression Requirements

Boundary regression coverage shall include:

- root class lookup and printing
- object creation and printing
- `isObject` true/false boundaries
- object identity through assignment
- fresh object inequality
- object values inside lists and higher-order builtin flows
- aliased class creation through `C := Object; new C`

Robustness regression coverage shall include:

- unbound class name
- rebound `Object` as a non-class
- unsupported creation syntax
- using an object where an int, bool, list, or same-kind equality operand is required

## Coverage

Coverage shall continue to be measured against handwritten source files separately from generated lexer/parser files.
