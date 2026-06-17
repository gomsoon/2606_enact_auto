# Slice 042: Single-Class Method Definition + Dispatch Core Design

Related requirements: [docs/slices/042-single-class-method-definition-dispatch-requirements.md](/home/tprover/2606_enact_auto/docs/slices/042-single-class-method-definition-dispatch-requirements.md)

## Design Objective

Add the smallest useful method system on top of the completed object-state core:

- classes own directly defined methods
- method definitions produce function values
- object dot-calls can dispatch to direct class methods
- method bodies receive `self`

The design deliberately avoids superclass lookup so later inheritance slices can add it with focused tests.

## Class Method Storage

`EnactClass` gains a method table implemented as a linked list:

```c
typedef struct EnactMethod {
    char *name;
    EnactFunction *function;
    struct EnactMethod *next;
} EnactMethod;
```

The class owns copied method names and retained `EnactFunction` pointers. Releasing a class releases all stored methods.

Runtime API:

```c
int enact_class_define_method(EnactClass *class_value, const char *name, EnactFunction *function);
EnactFunction *enact_class_lookup_method(const EnactClass *class_value, const char *name);
```

Lookup returns a retained function pointer. Callers release it after use.

## AST

Add:

```c
AST_METHOD_DEF
```

with payload:

```c
EnactAst *class_expr;
char *name;
EnactNameList *param_names;
EnactAst *body;
```

Clone/free support mirrors function literal and class definition ownership.

## Parser Lowering

The existing assignment rule remains:

```text
assignment:
    call ":=" assignment
```

When the assignment left-hand side is a call whose callee is an attribute expression:

```text
Class.method(args) := body
```

the parser lowers it to:

```text
AST_METHOD_DEF(class_expr=Class, name=method, params=args, body=body)
```

Existing identifier assignment and named function definition lowering remain unchanged.

Method parameter names reuse the existing function-parameter validation path. Duplicate parameters and non-identifiers fail during parsing. The name `self` is additionally rejected for method parameters because dispatch owns that binding.

## Method Definition Evaluation

`AST_METHOD_DEF` evaluation:

1. evaluates `class_expr`
2. requires `ENACT_VALUE_CLASS`
3. creates an `EnactFunction` from the method parameters, body, and current environment
4. stores the function on the class method table
5. returns the function value

The function captures its definition environment before later top-level rebindings, matching ordinary function semantics.

## Dot-Call Dispatch

`enact_eval_call` gains a special path when the callee AST is `AST_ATTRIBUTE`.

For:

```text
receiver.name(args)
```

evaluation proceeds as follows:

1. evaluate `receiver`
2. require an object
3. first try object attribute lookup for `name`
4. if the attribute exists, call it through the existing callable path
5. otherwise look up a direct method named `name` on `classof(receiver)`
6. bind `self` to the receiver object
7. bind method arguments
8. evaluate the method body

Attribute-call behavior intentionally has priority over method dispatch. This preserves existing function-valued attribute behavior and lets object state shadow class methods.

## Arity

Methods require exact arity in this slice. Unlike ordinary functions and builtins, method dispatch does not produce partial method applications yet.

This keeps `self` lifetime and later inheritance semantics simple:

```text
Node.add(a,b) := a+b
(new Node).add(1)     -> ENACT_ERR_ARITY_MISMATCH
```

## Deferred Work

Later slices should add:

- superclass method lookup
- override ordering and inherited dispatch
- multiple inheritance and ambiguity diagnostics
- method partial application
- exposing bound methods as first-class values
- class-side dispatch
- `super`
