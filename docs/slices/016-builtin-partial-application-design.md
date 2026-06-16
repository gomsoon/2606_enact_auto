# Slice 016: Builtin Partial Application Core Design

Status: Draft 0.1

Last updated: 2026-06-16

Related requirements: [docs/slices/016-builtin-partial-application-requirements.md](/home/tprover/2606_enact_auto/docs/slices/016-builtin-partial-application-requirements.md)

Prerequisite design: [docs/slices/015-list-builtins-phase-2-design.md](/home/tprover/2606_enact_auto/docs/slices/015-list-builtins-phase-2-design.md)

## 1. Design Summary

Keep immutable builtin descriptors as static `EnactBuiltin` values.

Add a separate heap object for partially-applied builtins:

```c
typedef struct EnactBuiltinPartial EnactBuiltinPartial;
```

This object owns evaluated prefix arguments and points back to the static builtin descriptor.

## 2. Value Model

Add a runtime value kind:

```c
ENACT_VALUE_BUILTIN_PARTIAL
```

and payload:

```c
EnactBuiltinPartial *as_builtin_partial;
```

Value behavior:

- copy retains the partial object
- free releases the partial object
- equality uses object pointer identity
- printing uses `<function>`

This mirrors user-defined function value behavior closely enough for the current runtime.

## 3. Builtin Partial API

Extend `src/builtin.h`:

```c
typedef struct EnactBuiltinPartial EnactBuiltinPartial;

EnactBuiltinPartial *enact_builtin_partial_new(
    const EnactBuiltin *builtin,
    const EnactValue *arguments,
    size_t argument_count);
EnactBuiltinPartial *enact_builtin_partial_extend(
    const EnactBuiltinPartial *partial,
    const EnactValue *arguments,
    size_t argument_count);
EnactBuiltinPartial *enact_builtin_partial_retain(EnactBuiltinPartial *partial);
void enact_builtin_partial_release(EnactBuiltinPartial *partial);
const EnactBuiltin *enact_builtin_partial_builtin(const EnactBuiltinPartial *partial);
size_t enact_builtin_partial_argument_count(const EnactBuiltinPartial *partial);
int enact_builtin_partial_apply(
    const EnactBuiltinPartial *partial,
    const EnactValue *arguments,
    size_t argument_count,
    EnactValue *out,
    EnactDiag *diag);
```

`new` and `extend` return partial objects only when the resulting captured prefix remains smaller than the builtin arity.

## 4. Ownership

`EnactBuiltinPartial` stores:

```c
struct EnactBuiltinPartial {
    size_t ref_count;
    const EnactBuiltin *builtin;
    EnactValue *arguments;
    size_t argument_count;
};
```

Each captured argument is copied with `enact_value_copy`.

Release frees each captured value, then the array, then the object.

## 5. Call Evaluator

The call evaluator recognizes three callable value kinds:

```text
ENACT_VALUE_FUNCTION
ENACT_VALUE_BUILTIN
ENACT_VALUE_BUILTIN_PARTIAL
```

For `ENACT_VALUE_BUILTIN`:

```text
argument_count == 0      -> ENACT_ERR_ARITY_MISMATCH
argument_count < arity   -> evaluate args, return EnactBuiltinPartial
argument_count == arity  -> evaluate args, apply builtin
argument_count > arity   -> ENACT_ERR_ARITY_MISMATCH before evaluating args
```

For `ENACT_VALUE_BUILTIN_PARTIAL`:

```text
argument_count == 0                         -> ENACT_ERR_ARITY_MISMATCH
captured_count + argument_count < arity     -> evaluate args, return extended partial
captured_count + argument_count == arity    -> evaluate args, apply builtin
captured_count + argument_count > arity     -> ENACT_ERR_ARITY_MISMATCH before evaluating args
```

## 6. Apply Helper

`enact_builtin_partial_apply` builds a borrowed temporary array:

```text
captured prefix + newly supplied suffix
```

and calls `enact_builtin_apply`.

The temporary array does not own values; it only arranges borrowed `EnactValue` structs for the duration of the call.

## 7. Type Timing

Partial creation validates only arity and allocation/copying.

Builtin-specific type checks are delayed until full application:

```text
append(1)       -> <function>
append(1)(nil)  -> ENACT_ERR_TYPE_EXPECTED_LIST
```

This matches user-defined partial functions, where body-level type errors are delayed until the function has enough arguments to execute.

## 8. Test Strategy

Regression tests:

- direct partial creation and completion
- assignment and higher-order passing
- prefix capture timing
- equality/identity behavior
- over-application and delayed type failures

Unit tests:

- partial constructor, retain/copy/free
- partial extension
- partial direct apply
- partial lookup through ordinary `EnactValue` copy/equality paths

## 9. Future Extension Notes

This slice makes `map`, `filter`, `all`, and `reduce` easier because builtins now behave more like user functions at the call boundary.

Those higher-order builtins still need an internal helper that can apply any `EnactValue` callable from C. That should be a separate slice, because it touches evaluator structure more deeply than builtin partials do.
