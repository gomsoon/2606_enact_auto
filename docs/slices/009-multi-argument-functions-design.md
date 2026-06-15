# Slice 009: Multi-Argument Named Functions and Calls Design

Status: Draft 0.1

Last updated: 2026-06-15

Related requirements: [docs/slices/009-multi-argument-functions-requirements.md](/home/tprover/2606_enact_auto/docs/slices/009-multi-argument-functions-requirements.md)

Prerequisite design: [docs/slices/008-single-argument-functions-design.md](/home/tprover/2606_enact_auto/docs/slices/008-single-argument-functions-design.md)

## 1. Design Objective

This document defines the minimal generalization from single-argument functions to one-or-more argument functions.

The design deliberately keeps comma local to function parameter and argument lists. Tuple/list comma remains deferred.

## 2. Design Decisions Summary

- Function definitions continue to lower from call-shaped assignment left-hand sides.
- Parameter and argument lists must contain at least one item.
- Function values store an owned list of parameter names.
- Call AST nodes store an owned list of argument ASTs.
- Calls check arity before evaluating arguments.
- Arguments evaluate eagerly from left to right in the caller environment.
- Duplicate parameter names are syntax errors.
- Zero-argument calls and definitions remain out of scope.

## 3. List Representation

Add two small owned list types in the AST layer:

```c
typedef struct EnactNameList EnactNameList;
typedef struct EnactAstList EnactAstList;
```

`EnactNameList` owns `char *` entries.

`EnactAstList` owns `EnactAst *` entries.

Both lists support:

- create
- append
- count
- indexed access
- clone where needed
- free

This keeps function and call ownership explicit without adding a general runtime list value.

## 4. Parser Design

Add token:

```c
TOK_COMMA
```

Add grammar:

```text
argument_list ::= assignment
                | argument_list "," assignment

call          ::= call "(" argument_list ")"
                | primary
```

Function definitions still use:

```text
assignment ::= call ":=" assignment
             | conditional
```

The lowering helper accepts two left-hand-side forms:

- bare identifier assignment: `x:=value`
- call-shaped function definition: `f(x,y):=body`

For function definition lowering, the callee must be a bare identifier and every call argument must be a bare identifier.

Rejected examples:

```text
f():=1
f(x,x):=x
f((x),y):=x
f(x,1):=x
(f)(x):=x
```

## 5. AST Design

Change `AST_FUNCTION_LITERAL` payload from a single parameter name to:

```c
struct {
    EnactNameList *param_names;
    EnactAst *body;
} function_literal;
```

Change `AST_CALL` from the binary payload to:

```c
struct {
    EnactAst *callee;
    EnactAstList *arguments;
} call;
```

`enact_ast_clone` clones both lists deeply enough for function bodies to outlive parse trees.

## 6. Function Value Design

Change `EnactFunction` from a single `param_name` to an owned `EnactNameList`.

Expose:

```c
EnactFunction *enact_function_new(const EnactNameList *param_names, const EnactAst *body, const EnactEnv *env);
size_t enact_function_arity(const EnactFunction *function);
const char *enact_function_param_name(const EnactFunction *function, size_t index);
```

The function constructor clones the parameter-name list and rejects null or empty lists.

## 7. Evaluation Design

`AST_FUNCTION_LITERAL` evaluation passes the parameter list to `enact_function_new`.

`AST_CALL` evaluation:

1. evaluate callee
2. require function
3. compare `argument_count` and `function_arity`
4. report `ENACT_ERR_ARITY_MISMATCH` on mismatch
5. allocate a temporary value array
6. evaluate argument ASTs left-to-right into the array
7. clone captured env
8. define each parameter name with the corresponding argument value
9. evaluate body in the local env
10. free local env, argument values, and callee value

Arity mismatch does not evaluate argument expressions.

## 8. Static Binding Examples

Definition-time capture remains unchanged:

```text
x:=10; addx(a,b):=x+a+b; x:=20; addx(1,2).
```

returns `13`.

Returned closures can carry multi-argument functions:

```text
make(a):=sum(b,c):=a+b+c; s:=make(1); s(2,3).
```

returns `6`.

## 9. Side Effect Boundary

Arguments are eager and left-to-right:

```text
pick(a,b):=b; x:=0; pick(x:=1,x:=2); x.
```

returns `2`.

Arity errors happen before argument evaluation:

```text
one(x):=x; one(1,1/0).
```

fails with `ENACT_ERR_ARITY_MISMATCH`, not division by zero.

## 10. Test Design

Integration tests should cover:

- token output for comma in definitions and calls
- two- and three-argument functions
- string and boolean parameters
- single-argument compatibility
- static capture with multiple parameters
- higher-order multi-argument calls
- returned multi-argument closures
- side-effecting arguments
- arity mismatch
- malformed comma placement
- duplicate and invalid parameters
- non-function multi-argument calls

Unit tests should cover:

- name list and AST list ownership helpers
- function arity and parameter accessors
- direct AST multi-argument call evaluation
- arity mismatch from direct AST evaluation

## 11. Review Checklist

This design is ready for implementation if:

- Bison introduces no parser conflicts
- comma remains scoped to function parameter and argument lists
- all temporary argument values are freed on success and failure paths
- existing single-argument behavior remains green
