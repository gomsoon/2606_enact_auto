# Slice 079: General Bound Object Method Values Core Design

Related requirements: [docs/slices/079-general-bound-object-method-values-core-requirements.md](/home/tprover/2606_enact_auto/docs/slices/079-general-bound-object-method-values-core-requirements.md)

## Runtime Value

Slice 079 adds a callable runtime value:

```c
ENACT_VALUE_BOUND_OBJECT_METHOD
```

The payload stores:

- the selected user-defined method function.
- a copied receiver value.
- zero or more already-supplied method arguments for partial application.

The receiver copy retains the original object, so later rebinding the source variable does not change the method value. Because objects are reference values, later attribute mutation on that retained receiver is still observed by the method body through `self`.

## Lookup Policy

Bare attribute read keeps the same shadowing order used by dot-calls:

1. receiver object attributes.
2. user-defined class methods through class linearization.
3. native collection method bridge.

When step 2 finds a method, the evaluator returns a bound object method value. This is the main behavior change from earlier method slices, where bare method reads reported `ENACT_ERR_ATTRIBUTE_UNBOUND`.

For collection objects, user-defined class methods still shadow native collection methods. For example:

```text
Set.size():=99
set().size
```

returns a bound object method value for the user-defined `Set.size` method. The native collection bridge is consulted only when no object attribute and no user-defined class method exist.

## Calling Policy

Applying a bound object method reuses the existing method-body evaluator:

```text
object.method(args) -> method body with self bound to object
m := object.method
m(args)             -> same method body with self bound to object
```

The evaluator combines any captured method arguments with the current call's arguments, then calls the existing method application helper. This preserves lexical capture, `self` binding, runtime diagnostics, and inherited dispatch selection.

## Partial Application

Bound object method values can capture method arguments:

```text
class Node < Object
Node.add(a,b):=self.base+a+b
n:=new Node with base:=10
f:=n.add
g:=f(1)
g(2)
```

Direct dot-call partial application remains outside this slice. Therefore:

```text
n.add(1)
```

continues to report `ENACT_ERR_ARITY_MISMATCH` when `add` requires two arguments. Users can write `f:=n.add; f(1)` or `(n.add)(1)` to create a partial bound method value.

## Read-Time Capture

The selected method function is retained when the bound value is created. If the class later replaces a method with the same name, existing bound method values keep calling the previously selected function.

The receiver object is also retained when the bound value is created. If the original variable is rebound to a different object, existing bound method values keep using the original receiver.

## Printing And Equality

Bound object methods print as `<function>`.

Runtime equality is pointer identity for bound object method payloads, matching builtin partial and bound collection method values. Copies of the same bound value compare equal; separate reads create distinct bound values.

## Deferred Work

This slice does not add `super`, direct dot-call partial application, method signature introspection, method source introspection, or native collection method-table integration.
