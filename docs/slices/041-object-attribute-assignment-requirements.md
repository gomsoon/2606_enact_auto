# Slice 041: Object Attribute Assignment Requirements

## Scope

Slice 041 adds assignment through dot attribute left-hand sides:

```text
object.name := value
```

This completes the first mutable object-state core on top of Slice 039's `with` initialization and dot read.

Method definitions, method dispatch, `self`, inherited attributes, and class-level attributes remain out of scope.

## Functional Requirements

### Dot Assignment

- `object.name := value` shall evaluate `object`, require an object value, evaluate `value`, store the value on that object, and return the assigned value.
- Assigning to an existing attribute shall replace the previous value.
- Assigning to a missing attribute shall create that attribute on the object.
- Assigned values may be any normal runtime value, including integers, booleans, strings, atoms, lists, functions, classes, and objects.
- The stored value shall be copied into the object using the normal value ownership rules.

Accepted:

```text
class Node < Object
n := new Node with x:=1
n.x := 2
n.x
```

```text
class Node < Object
n := new Node
n.child := new Node
classof(n.child) == Node
```

### Evaluation Order

- The left-hand object expression shall be evaluated before the right-hand side value.
- If the left-hand object expression fails or is not an object, the right-hand side shall not be evaluated.
- The right-hand side shall be evaluated only after the target object has been validated.
- The expression result shall be the assigned value, matching ordinary identifier assignment.

### Syntax Boundaries

Accepted:

```text
n.x := 1
(n := new Node).x := 1
n.child.x := 7
setx(o,v) := o.x := v
```

Rejected or deferred:

```text
1.x := 2
Node.x := 2
n.x(1) := 2
n. := 1
method definition through dot-call syntax
```

## Regression Requirements

Boundary coverage shall include:

- tokenization of dot assignment
- replacement of an existing attribute
- creation of a missing attribute
- assignment result used as an expression
- right-hand side reading the previous attribute value
- nested object attribute assignment
- object-valued, function-valued, class-valued, and list-valued assignment
- assignment inside a named function body
- higher-order list builtin composition
- newline-terminated script execution with dot assignment

Robustness coverage shall include:

- dot assignment on non-object values
- dot assignment on class values
- unbound left-hand object names
- failing right-hand side expressions
- returned assigned values misused as booleans or functions
- malformed dot assignment syntax
- dot-call assignment syntax reserved for future method definitions

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
