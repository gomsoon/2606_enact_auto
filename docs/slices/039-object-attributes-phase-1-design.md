# Slice 039: Object Attributes Phase 1 Design

## Object Storage

`EnactObject` gains a small owned attribute table implemented as a linked list:

```c
typedef struct EnactAttribute {
    char *name;
    EnactValue value;
    struct EnactAttribute *next;
} EnactAttribute;
```

The object owns copied attribute names and copied attribute values. Releasing an object frees all stored attributes.

The runtime exposes:

```c
int enact_object_define_attribute(EnactObject *object, const char *name, EnactValue value);
int enact_object_lookup_attribute(const EnactObject *object, const char *name, EnactValue *out);
```

Lookup copies the stored value into `out`, matching existing environment lookup behavior.

## Diagnostics

Add:

```c
ENACT_ERR_TYPE_EXPECTED_OBJECT
ENACT_ERR_ATTRIBUTE_UNBOUND
```

The first is used when `with` or dot read sees a non-object value. The second is used when an object does not have the requested attribute.

## AST

Add:

```c
AST_WITH
AST_ATTRIBUTE
```

`AST_WITH` owns:

```c
object expression
attribute name
value expression
```

`AST_ATTRIBUTE` owns:

```c
object expression
attribute name
```

Clone and free support mirrors `AST_WHERE` and other named-expression payloads.

## Parser

`with` is parsed at an expression level below assignment and above lambdas:

```text
with_expr:
    with_expr "with" IDENTIFIER ":=" lambda
    | lambda
```

This makes chained initializers apply to the same object expression:

```text
new Node with x:=1 with y:=2
```

Dot read is parsed as a call-level postfix:

```text
call:
    call "." IDENTIFIER
```

The final expression terminator remains the outer `input: expr "."` token, so `n.value.` uses the first dot as attribute access and the second dot as termination.

## Evaluation

`AST_WITH` evaluation:

1. evaluates the object expression
2. requires `ENACT_VALUE_OBJECT`
3. evaluates the attribute value expression
4. stores a copied value on the object
5. returns the original object value

`AST_ATTRIBUTE` evaluation:

1. evaluates the object expression
2. requires `ENACT_VALUE_OBJECT`
3. looks up the attribute by name
4. returns a copied attribute value

## Script Splitting

The script chunk splitter treats `.` followed immediately by an identifier start after an identifier-like character or `)` as an attribute dot, not an expression terminator. This keeps newline-driven scripts such as:

```text
n.value
```

as one parse chunk.

## Deferred Work

This slice deliberately excludes:

- inherited attribute lookup
- class-level default attributes
- method lookup and dispatch
- assigning through dot, such as `n.value := 2`
- object printing that exposes attributes
- attribute enumeration
