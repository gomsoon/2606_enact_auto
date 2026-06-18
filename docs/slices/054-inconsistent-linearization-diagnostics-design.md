# Slice 054: Inconsistent Linearization Diagnostics Core Design

Related requirements: [docs/slices/054-inconsistent-linearization-diagnostics-requirements.md](/home/tprover/2606_enact_auto/docs/slices/054-inconsistent-linearization-diagnostics-requirements.md)

## Diagnostic

Slice 054 adds:

```c
ENACT_ERR_INCONSISTENT_LINEARIZATION
```

The user-facing message is:

```text
inconsistent class linearization
```

This keeps inconsistent multiple-inheritance graphs distinct from allocation failure and ordinary missing attributes.

## Runtime API

The object runtime now exposes checked linearization:

```c
int enact_class_linearization_checked(EnactClass *class_value, EnactList **out, int *consistent);
```

The function returns `0` for allocation or invalid internal arguments. It returns `1` and sets `*consistent = 0` when the class graph is inconsistent.

Method lookup now follows the same pattern:

```c
int enact_class_lookup_method(
    EnactClass *class_value,
    const char *name,
    EnactFunction **out,
    int *consistent);
```

This lets evaluator code distinguish:

- runtime allocation/internal lookup failure
- inconsistent class graph
- missing method
- found method

## Policy

Operations that require linearization now reject inconsistent graphs:

- `classes(Class)`
- `superiors(Class)`
- dot-call method dispatch

Operations that do not need linearization remain available:

- `OK(Class)`
- `supers(Class)`
- `methods(Class)`
- `new Class`
- `classof(object)`
- direct object attributes and `attrs(object)`

This gives users a way to inspect and repair the graph without allowing method dispatch to silently use the Slice 053 fallback order.
