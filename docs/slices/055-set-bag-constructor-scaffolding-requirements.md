# Slice 055: Set/Bag Constructor Scaffolding Core Requirements

## Goal

Slice 055 starts the predefined collection-class track by installing `Set` and `Bag` as runtime classes and adding empty constructors for them.

Update note: Slice 069 later adds argument-bearing `set(list)` and `bag(list)` construction while retaining the zero-argument forms introduced here.

## Requirements

- `Set` and `Bag` shall be installed in every fresh evaluation environment.
- `Set` and `Bag` shall be direct subclasses of `Object`.
- `set` and `bag` shall be predefined constructors with zero-argument forms in this slice.
- `set()` shall return a new object whose class is `Set`.
- `bag()` shall return a new object whose class is `Bag`.
- Constructor results shall participate in the existing object model:
  - `isObject(set())`
  - `classof(set()) == Set`
  - `attrs(set()) == nil`
  - `classes(classof(set())) == (Set,Object)`
- The constructors shall use the current environment binding for `Set` and `Bag`, matching `new Set` and `new Bag` behavior.
- Over-application shall report `ENACT_ERR_ARITY_MISMATCH` before evaluating extra arguments.
- Shadowing `Set` or `Bag` with a non-class value shall make the matching constructor report `ENACT_ERR_TYPE_EXPECTED_CLASS`.
- Shadowing `set` or `bag` with a non-callable value shall preserve existing call diagnostics.

## Regression Requirements

Boundary coverage shall include:

- direct lookup and printing of `Set` and `Bag`.
- direct superclass and inclusive class-chain introspection.
- `set()` and `bag()` object construction.
- constructor aliasing through assignment.
- higher-order use over constructed collection objects.
- subclassing from `Set`.

Robustness coverage shall include:

- arity mismatch for over-applied `set` and `bag` calls.
- arity mismatch with unevaluated failing extra arguments.
- shadowed `Set` and `Bag` class bindings.
- treating constructors or constructor results as classes, lists, integers, booleans, or functions.

## Deferred

- Collection payload storage remains deferred.
- Collection methods such as `insert`, `remove`, `member`, `union`, `difference`, and `intersection` on `Set`/`Bag` objects remain deferred.
- Literal collection syntax remains deferred; Slice 069 later adds argument-bearing ordinary-list construction.
- Custom printing for populated collections is deferred in this slice and later added by Slice 073.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
