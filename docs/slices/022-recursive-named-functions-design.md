# Slice 022: Recursive Named Functions Design

Status: Draft 0.1

Last updated: 2026-06-16

Related requirements: [docs/slices/022-recursive-named-functions-requirements.md](/home/tprover/2606_enact_auto/docs/slices/022-recursive-named-functions-requirements.md)

Prerequisite design: [docs/slices/021-atom-builtin-design.md](/home/tprover/2606_enact_auto/docs/slices/021-atom-builtin-design.md)

## 1. Design Summary

The parser already lowers:

```text
f(x):=body
```

into:

```text
f := x::body
```

For this slice, that lowered assignment needs to remember that it came from named function syntax.

Add a flag to `AST_ASSIGN`:

```c
int recursive_function;
```

Only the named-function lowering path sets this flag. Ordinary assignments such as:

```text
f:=x::f(x)
```

keep the flag clear and remain non-recursive.

## 2. Parser Design

`enact_make_assignment_from_lhs` already distinguishes:

- identifier LHS: ordinary assignment
- call LHS rooted at an identifier: named function definition

The call-LHS branch now creates a recursive assignment:

```c
result = enact_make_recursive_assignment(name, function);
```

The identifier-LHS branch still creates an ordinary assignment.

No lexer tokens or grammar productions are added.

## 3. Function Metadata

Add optional recursive-name metadata to `EnactFunction`:

```c
char *recursive_name;
```

Add constructor:

```c
EnactFunction *enact_function_new_recursive(
    const EnactNameList *param_names,
    const EnactAst *body,
    const EnactEnv *env,
    const char *recursive_name);
```

`enact_function_new` remains the non-recursive constructor.

## 4. Assignment Evaluation

When evaluating `AST_ASSIGN`:

1. if `recursive_function` is set and the RHS is an `AST_FUNCTION_LITERAL`, create the function with `enact_function_new_recursive`
2. define the resulting function value in the current environment under the assignment name
3. return the function value as before

Ordinary assignment evaluation remains unchanged.

## 5. Call-Time Self Binding

Recursive functions do not store themselves inside their captured environment. That would create a reference-count cycle:

```text
function -> captured_env -> self value -> same function
```

Instead, exact function call evaluation does this after cloning the captured environment:

```text
local = clone(function.captured_env)
if function.recursive_name:
    local[recursive_name] = function
bind parameters
evaluate body
```

This keeps the self binding available during body evaluation without making it permanently cyclic.

## 6. Partial Application

Partial application needs one extra rule.

When partially applying a recursive function, the partial function's captured environment stores the original full function under the recursive name before prefix parameters are bound.

This preserves examples such as:

```text
sum(a,b):=b if a==0 else sum(a-1,b+a);
sum(3)(0).
```

The partial function itself does not carry `recursive_name`. Its body resolves the name through its captured environment, where it points to the original full function.

This avoids accidentally rebinding the recursive name to the partial and changing the callable arity inside the body.

## 7. Shadowing

Parameter binding still occurs after self binding.

Therefore a parameter with the same name as the function shadows the recursive self binding:

```text
f(f):=0 if f==0 else f(f-1)
```

Inside the body, `f` is the parameter value, not the function. A recursive-style call on that parameter fails with `ENACT_ERR_TYPE_EXPECTED_FUNCTION`.

## 8. Rebinding Stability

Because the self binding uses the function being called, not a fresh lookup from the outer environment, saved function values keep their own recursive identity:

```text
f(n):=1 if n==0 else f(n-1)+1;
old:=f;
f(n):=100;
old(3).
```

The call through `old` binds `f` to `old`'s function object while evaluating the old body.

## 9. Ownership

`recursive_name` is an owned string on `EnactFunction` and is freed with the function.

Call-time self binding uses a temporary value wrapper around the current function pointer. `enact_env_define` copies that value and retains the function for the lifetime of the local environment only.

Partial recursive capture stores a retained reference to the original full function in the partial's captured environment. This is not cyclic because the original function does not retain the partial.

## 10. Test Strategy

Regression tests cover:

- factorial and nfib
- list length and reverse recursion
- multi-argument recursion
- currying and assigned partials
- higher-order recursive function calls
- static outer capture
- nested recursive function definitions
- rebinding stability
- self identity
- whitespace named function syntax
- recursive use through `map`
- assignment-bound lambdas remaining non-recursive
- arity, type, list, shadowing, and mutual-recursion failures

Unit tests cover:

- recursive constructor input validation
- recursive-name accessor
- partial recursive functions capturing the original self binding
- partial recursive functions clearing their own recursive metadata

## 11. Future Extension Notes

This slice does not implement general `fix`.

A later `fix` slice can build on the same call-time self-binding ideas, but it will need a first-class recursive value construction rule rather than relying on named function definition syntax.
