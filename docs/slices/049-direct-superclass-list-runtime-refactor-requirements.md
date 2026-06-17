# Slice 049: Direct Superclass List Runtime Refactor Requirements

## Scope

Slice 049 refactors the class runtime so each class stores direct superclasses as an internal list instead of a single superclass pointer.

This slice is intentionally behavior-preserving for the public language. The parser still accepts only the existing single-superclass class definition form:

```text
class Node < Object
```

Multiple-superclass syntax such as `class C < (A,B)` remains deferred.

## Functional Requirements

- `EnactClass` shall store direct superclasses as an ordered runtime list.
- The existing `enact_class_new_with_superclass(name, superclass)` constructor shall keep creating either:
  - no direct superclasses when `superclass` is null
  - one direct superclass when `superclass` is non-null
- `enact_class_superclass(class)` shall remain available for single-inheritance compatibility and return the first direct superclass.
- A new runtime helper shall expose the direct superclass list as an `EnactList` of class values.
- `supers(Class)` shall read from the direct superclass list helper.
- `supers(Object)` shall continue to return `nil`.
- `supers(Node)` shall continue to return `<class Object>:nil`.
- `superiors(Class)` shall preserve existing single-inheritance behavior.
- `classes(Class)` shall preserve existing inclusive single-inheritance behavior.
- Inherited method dispatch shall preserve existing subclass-to-superclass lookup order.
- Direct method introspection via `methods(Class)` shall remain direct-only and shall not include inherited methods.
- Existing object construction, `classof`, `attrs`, `with`, and dot read/write behavior shall not change.

## Evaluation Boundaries

- No lexer, parser, AST, or evaluator grammar behavior shall change.
- Single-superclass class definitions shall keep the same diagnostics for missing or non-class superclass operands.
- Existing `supers`, `superiors`, and `classes` arity and type diagnostics shall remain unchanged.
- Over-application of `supers`, `superiors`, or `classes` shall still report `ENACT_ERR_ARITY_MISMATCH` without evaluating impossible extra arguments.

## Regression Requirements

Boundary coverage shall include:

- root direct superclass list remains empty through `supers`
- one-level direct superclass list
- multi-level direct superclass preservation
- `superiors` chain preservation
- `classes` chain preservation
- direct-superclass head ordering
- `classes(Class) == append(list(Class), superiors(Class))`
- `map(size,map(supers,...))` across a class chain
- `map(size,map(classes,...))` across a class chain
- inherited method dispatch preservation
- subclass override preservation
- direct method introspection still excluding inherited methods
- object attributes unaffected by superclass storage
- first-class builtin use for `supers`
- `classof` identity preservation

Robustness coverage shall include:

- zero-argument `supers`
- over-applied `supers`
- object misuse with `supers`
- subclass object misuse with `supers`
- non-class misuse with `superiors`
- over-applied `superiors`
- non-class misuse with `classes`
- over-applied `classes`
- object misuse with `classes`
- list result misuse as an integer
- list result misuse as a boolean
- shadowed non-function `supers`
- shadowed non-function `classes`

## Out of Scope

This slice does not implement:

- multiple-superclass parser syntax
- class definitions with more than one direct superclass
- multiple-inheritance method lookup
- multiple-inheritance `superiors` or `classes` traversal
- ambiguity detection
- `suppliers`, `OK`, or `badAttrs`
- `super` method calls

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
