# Slice 105: Native Collection Effective Method Listing Requirements

## Goal

Slice 105 extends dispatch-facing method listing so native collection dot methods are discoverable:

```text
effectiveMethods(class_or_object)
```

Set-like and Bag-like classes or objects shall include the builtin-backed native collection method names that dot-call dispatch can use.

## Requirements

- `effectiveMethods` shall continue to be a normal first-class builtin with arity one.
- The argument shall continue to accept either a class value or an object value.
- Object arguments shall continue to use the object's runtime class.
- User-defined effective method names shall keep the same checked linearization order as Slice 091.
- If the class is Set-like or Bag-like, append native collection method names after user-defined effective method names.
- Native collection method names shall follow native collection method-table order.
- Method names shall appear at most once in the result.
- User-defined effective method names shall mask same-named native collection method names.
- `methods(class_or_object)` shall remain direct-only and shall not list native collection method-table entries.
- `methodSupplier(class_or_object, attr)` shall remain user-defined-method-only.
- If class linearization is inconsistent, report `ENACT_ERR_INCONSISTENT_LINEARIZATION`.
- Existing type errors and user shadowing behavior shall remain unchanged.

## Semantics

Native collection effective methods are discoverable:

```text
effectiveMethods(set()) -> 'size:'union:...:'reduce:nil
effectiveMethods(Set)   -> 'size:'union:...:'reduce:nil
effectiveMethods(bag()) -> 'size:'union:...:'reduce:nil
```

Subclasses inherit native collection method listing through their Set-like or Bag-like class kind:

```text
class MySet < Set
effectiveMethods(MySet) -> 'size:'union:...:'reduce:nil
```

User-defined methods keep priority and avoid duplicate names:

```text
Set.member(x):=x
effectiveMethods(set()) -> 'member:'size:'union:...:'reduce:nil
```

The direct method helper remains unchanged:

```text
methods(Set) -> nil
```

## Non-Goals

- This slice shall not expose native collection method suppliers through `methodSupplier`.
- This slice shall not add native collection methods to direct `methods`.
- This slice shall not add method source or body introspection.
- This slice shall not change dot-call dispatch order or method signature introspection semantics.

## Regression Requirements

Boundary coverage shall include:

- Set and Bag object arguments.
- Set and Bag class arguments.
- subclass arguments.
- native method-table ordering.
- native method count.
- native method membership checks.
- missing method names remaining absent.
- `methods` direct-only contrast.
- `methodSupplier` native invisibility.
- `methodArity` compatibility with native signatures.
- user-defined method name masking.
- higher-order use through `map` and `filter`.
- user shadowing of `effectiveMethods`.

Robustness coverage shall include:

- arity mismatch.
- result misuse as integer, boolean, or callable.
- native atom result misuse as integer.
- native list result misuse as callable.
- invalid higher-order predicate result types.
- empty filtered native result misuse.
- inconsistent linearization for class and object arguments.
- user shadowing with a non-function.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
