# Slice 008: Single-Argument Named Functions and Parenthesized Calls Design

Status: Draft 0.1

Last updated: 2026-06-15

Related requirements: [docs/slices/008-single-argument-functions-requirements.md](/home/tprover/2606_enact_auto/docs/slices/008-single-argument-functions-requirements.md)

Prerequisite design: [docs/slices/007-local-definitions-where-design.md](/home/tprover/2606_enact_auto/docs/slices/007-local-definitions-where-design.md)

## 1. Design Objective

This document defines the smallest function implementation that supports named, single-argument functions and explicit parenthesized calls.

The design favors a small closure value over grammar generalization. Future slices can add multi-argument functions, recursion, local definition lists, or anonymous functions on top of this base.

## 2. Design Decisions Summary

- Function definition syntax is `name(parameter):=body`.
- Function calls use `callee(argument)`.
- Function values capture a clone of the definition-time environment.
- Arguments are evaluated eagerly in the caller environment.
- Function bodies evaluate in a clone of the captured environment with the parameter bound.
- Function values use reference counting because environments copy values.
- Function body ASTs are cloned into function objects so they outlive the parse tree.
- Functions are not recursively bound in this slice.
- Function equality is identity equality for now.

## 3. Parser Design

Extend assignment with a function-definition alternative before ordinary assignment:

```text
assignment ::= identifier "(" identifier ")" ":=" assignment
             | identifier ":=" assignment
             | conditional
```

The parser lowers:

```text
f(x):=x+1
```

into:

```text
AST_ASSIGN(name="f", value=AST_FUNCTION_LITERAL(param="x", body=x+1))
```

Parentheses are preserved as `AST_GROUP` so assignment lowering can reject parenthesized left-hand sides such as `(x):=1` and `(f)(x):=x`.

Add a postfix call layer:

```text
multiplicative ::= multiplicative "*" unary
                 | multiplicative "/" unary
                 | multiplicative "mod" unary
                 | unary

unary          ::= "-" unary
                 | call

call           ::= call "(" assignment ")"
                 | primary
```

This permits:

```text
f(1)+2
g(f(3))
1(2)
```

The last expression parses successfully and fails semantically as a non-function call.

## 4. AST Design

Add node kinds:

```c
AST_GROUP,
AST_FUNCTION_LITERAL,
AST_CALL
```

Add payload:

```c
struct {
    char *param_name;
    EnactAst *body;
} function_literal;
```

`AST_CALL` uses the existing binary payload:

- `left`: callee
- `right`: argument

`AST_GROUP` uses the existing unary payload and evaluates transparently to its child.

Add constructor:

```c
EnactAst *enact_ast_new_function_literal(char *param_name, EnactAst *body);
```

Add clone helper:

```c
EnactAst *enact_ast_clone(const EnactAst *ast);
```

Function values use cloned AST bodies because the parsed root AST is freed after public evaluation.

## 5. Function Value Design

Add an opaque `EnactFunction` object:

```c
typedef struct EnactFunction EnactFunction;
```

The object stores:

- reference count
- parameter name
- cloned body AST
- cloned captured environment

Expose:

```c
EnactFunction *enact_function_new(const char *param_name, const EnactAst *body, const EnactEnv *env);
EnactFunction *enact_function_retain(EnactFunction *function);
void enact_function_release(EnactFunction *function);
const char *enact_function_param_name(const EnactFunction *function);
const EnactAst *enact_function_body(const EnactFunction *function);
const EnactEnv *enact_function_env(const EnactFunction *function);
```

Extend `EnactValueKind`:

```c
ENACT_VALUE_FUNCTION
```

`enact_value_copy` retains function values, and `enact_value_free` releases them.

## 6. Evaluation Design

`AST_FUNCTION_LITERAL` evaluation:

1. allocate an `EnactFunction`
2. copy the parameter name
3. clone the function body AST
4. clone the current environment
5. return `ENACT_VALUE_FUNCTION`

`AST_CALL` evaluation:

1. evaluate the callee
2. require `ENACT_VALUE_FUNCTION`
3. evaluate the argument
4. clone the captured environment
5. define the parameter in the clone
6. evaluate the body in the clone
7. release temporary values and local environment

Definition:

```text
f(x):=x+1
```

is regular assignment of a function value, so it reuses the existing assignment semantics.

## 7. Static Binding Examples

Definition-time capture:

```text
x:=10; f(y):=x+y; f(1).
```

returns `11`.

Outer rebinding does not affect the captured value:

```text
x:=10; f(y):=x+y; x:=20; f(1).
```

also returns `11`.

Function-body assignment is local to the call:

```text
f(x):=(x:=2; x); x:=1; f(0); x.
```

returns `1`.

## 8. Recursion Boundary

The captured environment is cloned while evaluating the function literal, before the function name is written into the surrounding environment by assignment.

Therefore:

```text
f(x):=f(x); f(1).
```

fails with `ENACT_ERR_NAME_UNBOUND`.

Recursive binding can be added later with an explicit self-binding or fixed-point design.

## 9. Output Design

The CLI prints function values as:

```text
<function>
```

This gives function definitions a stable observable result without exposing implementation addresses.

## 10. Test Design

Integration tests should cover:

- token output for function definition and call syntax
- direct integer, boolean, and string functions
- static capture and rebinding stability
- sequence and `where` inside a function body
- function definition result printing
- indirect calls through variables
- higher-order single-argument calls
- returned closure calls
- non-function call diagnostics
- malformed function definitions and calls
- non-recursive self-call failure

Unit tests should cover:

- function value copy/free ownership
- direct AST function call evaluation
- function body assignment isolation
- function diagnostic helper coverage

## 11. Review Checklist

This design is ready for implementation if:

- Bison introduces no parser conflicts
- function values survive environment copies
- function body ASTs outlive the parsed root AST
- call-local environments are freed on every success and failure path
