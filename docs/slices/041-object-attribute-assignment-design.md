# Slice 041: Object Attribute Assignment Design

Related requirements: [docs/slices/041-object-attribute-assignment-requirements.md](/home/tprover/2606_enact_auto/docs/slices/041-object-attribute-assignment-requirements.md)

## Design Objective

Support object attribute mutation without introducing method syntax. The existing grammar already parses assignment left-hand sides through the `call` nonterminal, so dot assignment can be added by accepting an `AST_ATTRIBUTE` left-hand side in the assignment-lowering helper.

## AST

Add:

```c
AST_ATTRIBUTE_ASSIGN
```

with payload:

```c
EnactAst *object;
char *name;
EnactAst *value;
```

The node owns the object expression, attribute name, and value expression. Clone/free support mirrors `AST_WITH`.

## Parser Lowering

The existing assignment rule remains:

```text
assignment:
    call ":=" assignment
```

`enact_make_assignment_from_lhs` gains one new accepted shape:

```text
AST_ATTRIBUTE(object, name) := value
```

which lowers to:

```text
AST_ATTRIBUTE_ASSIGN(object, name, value)
```

Bare identifier assignment and function definition lowering remain unchanged.

Dot-call assignment remains rejected:

```text
n.x(1) := 2
```

This keeps the future method-definition syntax separate from instance attribute assignment.

## Evaluation

`AST_ATTRIBUTE_ASSIGN` evaluation:

1. evaluates the object expression
2. requires `ENACT_VALUE_OBJECT`
3. evaluates the right-hand value expression
4. stores a copied value on the object with `enact_object_define_attribute`
5. returns the evaluated right-hand value

Returning the right-hand value matches ordinary identifier assignment:

```text
(n.x := 2) + 3
```

The object expression is validated before the right-hand side is evaluated. This means:

```text
1.x := missing
```

reports `ENACT_ERR_TYPE_EXPECTED_OBJECT`, not `ENACT_ERR_NAME_UNBOUND`.

## Attribute Creation

Attribute assignment uses the same object storage primitive as `with`:

```c
enact_object_define_attribute(...)
```

Therefore assignment creates a missing attribute and replaces an existing one. This gives method-body slices a simple future target for patterns such as:

```text
self.count := self.count + 1
```

## Deferred Work

This slice deliberately excludes:

- class-level attributes
- inherited attribute lookup or inherited defaults
- method definition and dispatch
- `self`
- assigning through method-call forms
- attribute deletion
- attribute enumeration
