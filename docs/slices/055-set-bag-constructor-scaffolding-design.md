# Slice 055: Set/Bag Constructor Scaffolding Core Design

Related requirements: [docs/slices/055-set-bag-constructor-scaffolding-requirements.md](/home/tprover/2606_enact_auto/docs/slices/055-set-bag-constructor-scaffolding-requirements.md)

Update note: Slice 069 extends these constructors with `set(list)` and `bag(list)` using builtin minimum/maximum arity metadata.

## Runtime Shape

`Set` and `Bag` are installed as ordinary classes with `Object` as their direct superclass. This keeps the first collection slice aligned with the existing object runtime:

```text
classes(Set) == Set:Object:nil
classes(Bag) == Bag:Object:nil
```

The constructors return ordinary empty objects:

```text
set() -> <object Set>
bag() -> <object Bag>
```

No collection payload is stored yet, so `attrs(set())` and `attrs(bag())` remain `nil`.

## Builtin Evaluation

Most builtins are pure callbacks that do not need the evaluation environment. `set()` and `bag()` need the current `Set` or `Bag` binding, so the builtin apply path now has an environment-aware variant:

```c
int enact_builtin_apply_in_env(..., EnactEnv *env, ...);
int enact_builtin_partial_apply_in_env(..., EnactEnv *env, ...);
int enact_eval_apply_callable_in_env(..., EnactEnv *env, ...);
```

The existing `enact_builtin_apply`, `enact_builtin_partial_apply`, and `enact_eval_apply_callable` functions remain as wrappers that pass a null environment. This preserves the existing C API and unit-test surface.

## Constructor Policy

`set()` and `bag()` look up `Set` and `Bag` in the current environment. That intentionally mirrors `new Set` and `new Bag`:

- if the class binding is present and is a class, a fresh object is returned.
- if the class binding was shadowed with a non-class value, `ENACT_ERR_TYPE_EXPECTED_CLASS` is reported.
- if a constructor is called without an evaluation environment through the low-level C API, `ENACT_ERR_NAME_UNBOUND` is reported.

Slice 069 keeps this environment-binding policy and adds the one-argument ordinary-list form.

## Deferred Payload

This slice avoids hidden storage decisions. Future collection-method slices can choose the payload model without exposing temporary implementation attributes through `attrs()`.
