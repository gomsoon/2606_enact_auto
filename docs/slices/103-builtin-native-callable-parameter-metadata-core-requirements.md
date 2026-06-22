# Slice 103: Builtin / Native Callable Parameter Metadata Core Requirements

## Goal

Slice 103 extends callable parameter introspection to builtin callables and native collection dot-method callables:

```text
callableParams(callable)
```

Slice 100 introduced `callableParams` for user-defined functions and bound object methods. Slice 103 fills in the builtin and native collection method metadata that was intentionally deferred.

## Functional Requirements

- Builtins shall carry stable public parameter-name metadata.
- `callableParams(builtin)` shall return the builtin's parameter names as a list of atoms in call order.
- `callableParams(builtin_partial)` shall return only the remaining parameter names after captured arguments.
- `callableParams(bound_native_collection_method)` shall omit the already-bound receiver parameter.
- `callableParams(partial_bound_native_collection_method)` shall omit both the already-bound receiver parameter and captured method arguments.
- Zero-argument builtins shall return `nil`.
- Existing user-defined function, lambda, partial function, and bound object method behavior shall remain unchanged.
- Non-callable values shall continue to report `ENACT_ERR_TYPE_EXPECTED_FUNCTION`.
- User shadowing of `callableParams` shall continue to behave like other builtins.

## Initial Metadata Names

The initial names are intentionally small and descriptive:

```text
hd(list)
tl(list)
atom(value)
isObject(value)
classof(object)
attrs(object)
methods(target)
effectiveMethods(target)
classes(target)
supers(target)
superiors(target)
OK(target)
badAttrs(target)
suppliers(target, attr)
methodSupplier(target, method)
methodArity(target, method)
methodParams(target, method)
callableArity(callable)
callableMinArity(callable)
callableParams(callable)
callableArityRange(callable)
list(value)
set(items)
bag(items)
append(left, right)
size(collection)
map(function, collection)
collect(function, collection)
filter(predicate, collection)
select(predicate, collection)
all(predicate, collection)
exists(predicate, collection)
locate(predicate, collection)
forEachDo(function, collection)
reduce(function, initial, collection)
member(value, collection)
insert(value, collection)
add(value, collection)
remove(value, collection)
unitset(value)
union(left, right)
UNION(collections)
difference(left, right)
intersection(left, right)
subset(left, right)
equal(left, right)
```

## Examples

```text
callableParams(hd)              -> 'list:nil
callableParams(append)          -> 'left:'right:nil
callableParams(append(nil))     -> 'right:nil
callableParams(set)             -> 'items:nil
callableParams(version)         -> nil

callableParams(set().size)      -> nil
callableParams(set().member)    -> 'value:nil
callableParams(set().union)     -> 'right:nil
callableParams(set().reduce)    -> 'function:'initial:nil
callableParams(set().reduce(f)) -> 'initial:nil
```

