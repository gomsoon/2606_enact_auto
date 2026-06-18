# Slice 050: Multiple-Superclass Parser + AST Core Design

## Syntax

`class_definition` now accepts a superclass list:

```text
class C < A
class C < (A,B)
class C < (A,B,D)
```

The parenthesized form is intentionally tuple-like but limited to identifiers. Empty lists and one-element parenthesized lists are parse errors.

## AST

`AST_CLASS_DEF` stores:

```c
struct {
    char *name;
    EnactAstList *superclasses;
} class_def;
```

The single-superclass syntax is represented as a one-element `EnactAstList`, so the evaluator has only one path.

## Evaluation

Class definition evaluation walks the superclass AST list left-to-right. It recursively builds the tail first after each current value has been checked, which preserves declared order in the final `EnactList`.

Each superclass expression must evaluate to `ENACT_VALUE_CLASS`. The evaluator reuses the existing class type check so non-class bindings keep returning `ENACT_ERR_TYPE_EXPECTED_CLASS`.

## Runtime

`enact_class_new_with_superclasses(name, superclasses)` copies the direct-superclass value list into the class runtime link list. The existing `enact_class_new_with_superclass` API remains and delegates to the same ordered-link shape.

`enact_class_superclasses` continues to materialize a fresh list of class values for `supers(Class)`.

## Current Resolution Policy

Method lookup already traverses the direct-superclass link list left-to-right from Slice 049, then recurses into each parent. Slice 050 preserves that behavior without adding ambiguity detection.

`superiors(Class)` and `classes(Class)` still use `enact_class_superclass`, which returns the first direct superclass. That keeps this slice small while leaving full multiple-inheritance linearization for a later slice.
