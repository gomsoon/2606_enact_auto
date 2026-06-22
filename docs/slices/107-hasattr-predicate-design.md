# Slice 107: hasAttr Predicate Design

Related requirements: [docs/slices/107-hasattr-predicate-requirements.md](/home/tprover/2606_enact_auto/docs/slices/107-hasattr-predicate-requirements.md)

## Contract

The new builtin is:

```text
hasAttr(object, 'attrName)
```

It returns a boolean and does not return or copy the attribute value to the caller. The implementation only uses a temporary value copy so it can reuse the existing object lookup primitive.

## Runtime Lookup

The lookup flow is intentionally narrow:

1. Validate that the first argument is an object.
2. Validate that the second argument is an atom.
3. Call `enact_object_lookup_attribute`.
4. Return `true` for a positive lookup and `false` for a missing attribute.
5. Treat a negative lookup result as allocation failure.

Missing attributes are therefore ordinary predicate `false` results, not `ENACT_ERR_ATTRIBUTE_UNBOUND`.

## Attribute And Method Separation

`hasAttr` does not call class method lookup and does not consult native collection method tables:

```text
class Node < Object
Node.x():=1
hasAttr(new Node, 'x)  -> false
hasMethod(new Node, 'x)-> true
```

Native collection methods are also not attributes:

```text
hasAttr(set(), 'size) -> false
hasMethod(set(), 'size) -> true
```

If a collection carries an ordinary runtime attribute, that attribute is visible because collections are objects:

```text
hasAttr(set() with tag:=true, 'tag) -> true
```

## First-Class Behavior

`hasAttr` is registered as a normal builtin with parameter metadata:

```text
callableParams(hasAttr) -> 'object:'attr:nil
```

Existing builtin partial application covers cases such as:

```text
p:=hasAttr(new Object with x:=1)
p('x) -> true
```

## Deferred Work

This slice does not add class-level attribute declarations, attribute supplier metadata, or a structured attribute-info API. It also does not change `attrs`, `badAttrs`, `suppliers`, or dot-read behavior.
