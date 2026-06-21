# Slice 083: badAttrs(Class) Ambiguity Introspection Core Requirements

## Goal

Slice 083 adds the PRD/manual-named ambiguity helper:

```text
badAttrs(Class)
```

The manual describes `badAttrs` as the attributes, including inherited attributes, that are inherited from more than one superclass. The current runtime does not have class-level data attributes, so this slice applies that rule to class method names.

## Requirements

- `badAttrs(class)` shall return a list of atom values naming ambiguous inherited methods.
- `badAttrs(Object)` shall return `nil`.
- A class with no inherited method-name ambiguity shall return `nil`.
- If two or more distinct superclass supplier classes provide the same effective method name, `badAttrs` shall include that method name.
- A method directly defined on the queried class shall mask same-named inherited methods and remove that name from `badAttrs`.
- A shared ancestor that is the only supplier class for a method name shall not make that method bad, even when reached through multiple superclass paths.
- If one superclass overrides a shared ancestor method and another superclass inherits the ancestor method, the two distinct supplier classes shall make that method bad.
- Ambiguity inherited through a superclass shall remain visible to subclasses until masked by a direct method definition.
- `badAttrs(classof(object))` shall work by composing existing `classof` introspection with `badAttrs`.
- `badAttrs(object)` is later added by Slice 085 as a compatibility shorthand for `badAttrs(classof(object))`.
- `badAttrs` shall remain usable on classes with inconsistent linearization because it does not need to choose a method dispatch order.
- `badAttrs` shall be a normal first-class builtin and shall compose with `map`, `filter`, `member`, `size`, `all`, and conditionals.
- User bindings shall be able to shadow `badAttrs`, matching existing builtin behavior.
- Existing `OK(Class)` behavior remains a linearization-consistency predicate in this slice; integrating method-name ambiguity into `OK` remains deferred.

## Evaluation Boundaries

- `badAttrs` shall have arity one.
- Over-application shall report `ENACT_ERR_ARITY_MISMATCH` without evaluating impossible extra arguments.
- Non-class, non-object arguments shall report `ENACT_ERR_TYPE_EXPECTED_CLASS_OR_OBJECT` after Slice 085.
- Object values are later accepted directly by Slice 085.
- Misusing the returned list as an integer, boolean, or callable shall follow existing list-value error behavior.

## Regression Requirements

Boundary coverage shall include:

- root class.
- class with no superclasses.
- unrelated superclass methods.
- two direct superclasses supplying the same method name.
- direct child method masking inherited ambiguity.
- shared common ancestor supplying a method through multiple paths without ambiguity.
- one branch overriding a shared ancestor method.
- ambiguity inherited through an intermediate superclass.
- `classof` composition.
- `member` and `size` composition.
- `map` over class lists.
- `filter` over class lists.
- conditional use.
- first-class builtin use.
- builtin shadowing.
- inconsistent linearization still allowing `badAttrs`.
- direct masking on an inconsistent class.
- multiple bad method names.

Robustness coverage shall include:

- zero-argument call.
- over-application without evaluating an impossible extra argument.
- non-class primitive values.
- list, object, function, and builtin values.
- list result misuse as an integer.
- list result misuse as a boolean.
- list result misuse as a callable.
- shadowed non-function `badAttrs`.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
