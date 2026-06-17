# Slice 038: Class Definition Runtime Core Requirements

## Scope

Slice 038 turns the `class` keyword from parser scaffolding into a minimal runtime feature:

- `class Name < Super`
- class values installed in the current environment
- object creation from user-defined classes with `new Name`
- single-superclass tracking

Attributes, methods, dot lookup, `with`, inheritance lookup, and multiple inheritance remain out of scope.

## Functional Requirements

### Class Definition

- `class Node < Object` shall evaluate successfully.
- A class definition shall return the newly defined class value.
- A class definition shall bind the class name in the current environment.
- Printing a user-defined class shall use `<class Name>`.
- Class definitions shall work with top-level newline and dot termination.

### Superclass

- The superclass operand shall be an identifier in this slice.
- The superclass identifier shall be evaluated in the current environment.
- If the superclass name is unbound, evaluation shall report `ENACT_ERR_NAME_UNBOUND`.
- If the superclass value is not a class, evaluation shall report `ENACT_ERR_TYPE_EXPECTED_CLASS`.
- The newly defined class shall retain its superclass.

### Object Creation

- `new Node` shall create an object whose class is `Node`.
- Printing that object shall produce `<object Node>`.
- Class aliases shall work naturally:

```text
Base := Object
class Node < Base
new Node
```

### Equality and Predicates

- Repeated lookup of the same class binding shall compare equal.
- Different class values shall compare unequal.
- Comparing a class value and an object value shall keep the existing different-kind equality error.
- `isObject(new Node)` shall return `true`.
- `isObject(Node)` shall return `false`.
- `atom(Node)` shall return `true`, following the current non-list atom rule.

## Syntax Boundaries

Accepted:

```text
class Node < Object
class Leaf < Node
```

Rejected for this slice:

```text
class Node Object
class Node < 1
class Node < Object + 1
class Node < (Object)
class Node < (Object,Other)
```

## Regression Requirements

Boundary coverage shall include:

- class definition result printing
- lookup of the defined class
- `new` over a user-defined class
- superclass aliasing
- class equality by identity
- subclass chains
- list and higher-order builtin composition with user-defined objects

Robustness coverage shall include:

- missing superclass
- non-class superclass
- malformed class syntax
- class/object misuse in arithmetic, boolean, list, equality, and call contexts

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
