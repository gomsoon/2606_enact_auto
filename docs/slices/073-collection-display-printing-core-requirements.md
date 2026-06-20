# Slice 073: Collection Display / Printing Core Requirements

## Goal

Slice 073 changes command-line value printing for object-backed `Set` and `Bag` values so collection payloads are visible in normal REPL and script output.

## Requirements

- Empty `Set` collection objects shall print as `set()`.
- Empty `Bag` collection objects shall print as `bag()`.
- Non-empty `Set` collection objects shall print as `set(payload)`, where `payload` uses the existing ENACT cons-list printer.
- Non-empty `Bag` collection objects shall print as `bag(payload)`, where `payload` uses the existing ENACT cons-list printer.
- Collection display shall apply to objects whose class inherits from `Set` or `Bag`.
- Collection display shall be based on runtime collection kind, not the concrete class name.
- Runtime class and attributes shall remain observable through `classof` and `attrs`; this slice shall not encode them in the printed collection form.
- Set display shall expose the current hidden payload order. It shall not promise sorted or mathematical canonical ordering.
- Bag display shall preserve duplicate occurrences in the current hidden payload order.
- Nested lists, strings, atoms, classes, functions, ordinary objects, and nested collection objects inside a collection shall reuse the existing value printers.
- Non-collection objects shall keep the existing `<object ClassName>` display.
- Value printing changes shall not alter evaluation semantics, equality semantics, collection membership, class identity, attributes, or diagnostics.

## Regression Requirements

Boundary coverage shall include:

- empty Set and Bag display.
- direct display of inserted Set and Bag values.
- Set duplicate suppression display.
- Bag duplicate preservation display.
- constructor-based display for Set and Bag payloads.
- binary Set and Bag algebra result display.
- aggregate Bag `UNION` result display.
- nested list payload display.
- nested collection payload display.
- string, atom, and ordinary object payload display.
- subclass collection display.
- ordinary lists containing collection objects.

Robustness coverage shall include:

- primitive operator misuse of displayed Set and Bag values.
- list-only builtin misuse of displayed Set and Bag values.
- equality mismatch against non-collection values.
- mixed Set/Bag operation rejection.
- invalid collection constructor arguments.
- invalid `Set` or `Bag` environment bindings.
- shadowed constructor names.

## Deferred

- Sorted or canonical collection display ordering remains deferred.
- Class-qualified collection display remains deferred.
- Attribute-inclusive object display remains deferred.
- Tuple-like or comma-style collection display remains deferred; this slice reuses the existing cons-list printer.
- Dot-method collection syntax remains deferred in this slice; Slice 074 begins Phase 1 for `size`, `member`, `insert`, and `remove`.

## Coverage

Coverage shall continue to report handwritten source coverage separately from generated lexer/parser coverage.
