# Slice 022: Recursive Named Functions Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-16

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/021-atom-builtin-requirements.md](/home/tprover/2606_enact_auto/docs/slices/021-atom-builtin-requirements.md)

## 1. Slice Goal

This slice allows named function definitions to call themselves:

```text
fact(n):=1 if n==0 else n*fact(n-1)
```

The goal is to unlock the functional-core milestone examples for factorial, nfib, reverse, and other simple recursive functions without adding the full `fix` expression yet.

## 2. Source Basis

The PRD records:

- fixed-point recursive definitions are part of the language surface
- function definitions and higher-order functions are part of the functional core
- Milestone 2 expects manual examples for `factorial`, `nfib`, `reverse`, and `twice`

Earlier slices intentionally left recursive self-binding unsupported because functions captured their environment before assignment wrote the function name.

## 3. In Scope

This slice includes:

- self-recursion for named function definition syntax
- parenthesized definitions such as `fact(n):=...`
- whitespace definitions such as `fact n:=...`
- multi-argument recursive functions
- recursive named functions that are partially applied
- recursive functions passed as first-class values
- static capture of outer variables
- unit tests for recursive function metadata and partial capture

## 4. Out Of Scope

This slice explicitly excludes:

- general `fix`
- mutual recursion
- recursive local `where` definitions
- recursive assignment-bound lambdas such as `f:=x::f(x)`
- tail-call optimization
- recursion depth limits or stack management
- object methods and `self`

## 5. Named Function Semantics

Named function definition syntax shall create a function value that remembers its definition name:

```text
f(x):=body
f x:=body
```

When that function is called, its local evaluation environment shall bind `f` to the function itself before binding call parameters.

Therefore:

```text
fact(n):=1 if n==0 else n*fact(n-1); fact(5).
```

returns `120`.

## 6. Lambda Assignment Boundary

Assignment-bound lambdas remain non-recursive in this slice:

```text
f:=x::f(x); f(1).
```

still fails with `ENACT_ERR_NAME_UNBOUND`.

This keeps Slice 022 focused on named function definitions and leaves general recursive values to a future `fix` slice.

## 7. Static Capture Requirements

Recursive named functions shall preserve existing static capture behavior for free variables:

```text
step:=2;
count(n):=0 if n==0 else step+count(n-1);
step:=10;
count(3).
```

returns `6`, not `30`.

Recursive self-binding is added at call time, but other free variables still come from the definition-time captured environment.

## 8. Partial Application Requirements

Recursive named functions shall continue to support currying and partial application:

```text
sum(a,b):=b if a==0 else sum(a-1,b+a);
sum(3)(0).
```

returns `6`.

A partial recursive function shall preserve a binding to the original full function so that recursive calls in the body can still use the full named function arity.

## 9. Rebinding Requirements

If a recursive function value is saved before the original name is rebound, recursive calls through the saved value shall continue to refer to the saved function:

```text
f(n):=1 if n==0 else f(n-1)+1;
old:=f;
f(n):=100;
old(3).
```

returns `4`.

## 10. User-Facing Behavior

Accepted examples:

- `fact(n):=1 if n==0 else n*fact(n-1); fact(5).` => `120`
- `nfib(n):=1 if n<2 else nfib(n-1)+nfib(n-2); nfib(5).` => `8`
- `sumdown(n):=0 if n==0 else n+sumdown(n-1); sumdown(5).` => `15`
- `len(xs):=0 if atom(xs) else 1+len(tl(xs)); len((1,2,3)).` => `3`
- `reverse(xs):=nil if atom(xs) else append(reverse(tl(xs)), hd(xs):nil); reverse((1,2,3)).` => `3:2:1:nil`
- `sum(a,b):=b if a==0 else sum(a-1,b+a); sum(3)(0).` => `6`
- `apply(f,x):=f(x); fact(n):=1 if n==0 else n*fact(n-1); apply(fact,4).` => `24`
- `down n:=0 if n==0 else down(n-1)+1; down 4.` => `4`

Error examples:

- `f:=x::f(x); f(1).` => `ENACT_ERR_NAME_UNBOUND`
- `f(x):=f(x,1); f(1).` => `ENACT_ERR_ARITY_MISMATCH`
- `fact(n):=1 if n==0 else n*fact(n-1); fact(true).` => `ENACT_ERR_TYPE_EQUALITY_MISMATCH`
- `bad(n):=1 if n==0 else true+bad(n-1); bad(1).` => `ENACT_ERR_TYPE_EXPECTED_INT`
- `even(n):=true if n==0 else odd(n-1); odd(n):=false if n==0 else even(n-1); even(2).` => `ENACT_ERR_NAME_UNBOUND`

## 11. Boundary Analysis Requirements

The regression suite shall include:

- factorial recursion
- nfib recursion
- integer sum recursion
- list length recursion using `atom`
- list reverse recursion using `append`, `hd`, and `tl`
- multi-argument recursive function
- curried recursive call
- assigned partial recursive function
- higher-order recursive function call
- static outer capture through recursion
- nested named recursive function
- saved recursive function after rebinding
- self value identity inside body
- recursive function value observed by `atom`
- whitespace recursive function definition
- recursive function used through `map`

## 12. Robustness Requirements

The regression suite shall include:

- assignment-bound lambda remains non-recursive
- single-argument recursive self-call arity mismatch
- multi-argument recursive self-call arity mismatch
- whitespace recursive self-call arity mismatch
- recursive call argument type failure
- recursive over-application does not evaluate impossible extra arguments
- recursive body type failure
- recursive body list failure
- parameter shadowing the function name
- mutual recursion remains unsupported
- partial recursive self-call arity mismatch
- recursive over-application with recursive body not evaluated

## 13. Acceptance Criteria

This slice is accepted when:

- named function definitions can call themselves
- assignment-bound lambdas remain non-recursive
- recursive functions preserve static capture of ordinary free variables
- recursive functions preserve self-reference through partial application
- saved recursive functions keep their own self-reference after rebinding the original name
- previous Slice 001 through Slice 021 behavior remains green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
