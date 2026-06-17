# Slice 039: Object Attributes Phase 1 Requirements

## Scope

Slice 039 introduces the first user-visible object state:

- `new Class with name:=value`
- chained `with` attribute initialization
- dot attribute reads with `object.name`

Methods, inherited attributes, dot method dispatch, and assignment into an existing object's attribute remain out of scope.

## Functional Requirements

### Attribute Initialization

- `new Node with value:=1` shall evaluate to the same object value produced by `new Node`, with attribute `value` stored on that object.
- Chained initialization shall be accepted:

```text
new Node with x:=1 with y:=2
```

- Reusing the same attribute name in a chained initializer shall replace the previous value for this slice.
- Attribute values may be ordinary evaluated values, including integers, booleans, strings, atoms, lists, functions, classes, and objects.
- Attribute values shall be copied into the object using the normal value ownership rules.

### Dot Attribute Read

- `object.name` shall read attribute `name` from an object value.
- Attribute reads shall compose with existing call syntax, list syntax, arithmetic, predicates, and higher-order list builtins.
- Dot reads shall work in top-level newline-terminated scripts without the script splitter treating the attribute dot as an expression terminator.
- Missing attributes shall report `ENACT_ERR_ATTRIBUTE_UNBOUND`.
- Dot reads on non-object values shall report `ENACT_ERR_TYPE_EXPECTED_OBJECT`.

### Syntax Boundaries

Accepted:

```text
n.value
(new Node with value:=1).value
f.inc(4)
```

Rejected or deferred:

```text
with x:=1
new Node with :=1
n.value := 2
n.method dispatch semantics
inherited attribute lookup
```

## Regression Requirements

Boundary coverage shall include:

- tokenization of `obj.value`
- object initialization with one attribute
- chained attributes
- attribute value expressions
- object-valued attributes
- function-valued attributes called through dot read
- parenthesized object dot read
- attribute replacement
- list, class, and higher-order builtin composition

Robustness coverage shall include:

- unbound initializer object
- missing attributes
- dot read from non-object values
- malformed `with` syntax
- failing initializer expressions
- attribute reads misused as integer, boolean, or function values

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
