# Slice 013: List Core Requirements Analysis

Status: Draft 0.1

Last updated: 2026-06-16

Related PRD: [docs/enact-prd.md](/home/tprover/2606_enact_auto/docs/enact-prd.md)

Prerequisite slice: [docs/slices/012-whitespace-function-application-requirements.md](/home/tprover/2606_enact_auto/docs/slices/012-whitespace-function-application-requirements.md)

## 1. Slice Goal

This slice introduces the smallest runtime list core:

- the empty list `nil`
- cons construction with `:`
- list value copying/freeing
- list printing

The goal is to create a stable data structure foundation before adding list builtins such as `hd`, `tl`, `append`, and `size`.

## 2. Source Basis

The PRD records:

- runtime values shall include lists
- the empty list is written `nil`
- cons construction uses `:`
- singleton list conventions include `99:nil`
- predefined list operations are future requirements

Slices 011-012 already provide function values, currying, and whitespace application, which will later make list builtins ergonomic.

## 3. In Scope

This slice includes:

- lexer support for reserved word `nil`
- lexer support for `:` as `TOK_CONS`
- AST support for list nil and cons
- runtime list value support
- immutable cons cells with safe copy/free behavior
- cons evaluation with a list-valued tail requirement
- printing lists in source-like cons form
- structural list equality
- tests for integer, boolean, string, function, nested, assigned, and local list values

## 4. Out Of Scope

This slice explicitly excludes:

- `hd`, `tl`, `append`, `size`, `map`, `filter`, `all`, and `reduce`
- tuple-like list construction with `(x,y,z)`
- the singleton convention `99:()`
- a `list` builtin
- list comprehensions
- pattern matching
- mutable list updates
- quoted atoms
- object/collection classes

## 5. User-Facing Behavior

Accepted examples:

- `nil.` => `nil`
- `1:nil.` => `1:nil`
- `1:2:nil.` => `1:2:nil`
- `"a":true:nil.` => `"a":true:nil`
- `(1:nil):nil.` => `(1:nil):nil`
- `xs:=1:2:nil; xs.` => `1:2:nil`
- `xs:=1:nil; ys:=0:xs; ys.` => `0:1:nil`
- `1+2:nil.` => `3:nil`
- `1:2:nil == 1:2:nil.` => `true`
- `1:nil != 2:nil.` => `true`

Error examples:

- `1:2.` => `ENACT_ERR_TYPE_EXPECTED_LIST`
- `1:true.` => `ENACT_ERR_TYPE_EXPECTED_LIST`
- `nil:nil + 1.` => `ENACT_ERR_TYPE_EXPECTED_INT`
- `nil < nil.` => `ENACT_ERR_TYPE_EXPECTED_INT`
- `1:.` => `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`
- `:nil.` => `ENACT_ERR_PARSE_UNEXPECTED_TOKEN`

## 6. Syntax Requirements

Add tokens:

```text
"nil" => TOK_NIL
":"   => TOK_CONS
```

The lexer shall match `::` and `:=` before `:`.

Add list syntax:

```text
cons ::= additive ":" cons
       | additive
```

Comparison expressions shall consume `cons` expressions, so list values can participate in equality:

```text
comparison ::= cons
             | cons "==" cons
             | cons "!=" cons
             | ...
```

The `:` operator is right-associative:

```text
1:2:nil
```

parses as:

```text
1:(2:nil)
```

## 7. Semantic Requirements

`nil` evaluates to the empty list.

`head:tail` shall:

1. evaluate `head`
2. evaluate `tail`
3. fail with `ENACT_ERR_TYPE_EXPECTED_LIST` if `tail` is not a list
4. return a new immutable cons list value

List values shall be safe to store in environments, copy, and free.

## 8. Printing Requirements

Lists print in cons syntax:

```text
nil
1:nil
1:2:nil
"a":true:nil
```

Nested list heads print with parentheses:

```text
(1:nil):nil
```

The printer shall still render strings with escapes and functions as `<function>`.

## 9. Equality Requirements

List equality is structural:

- `nil == nil` is `true`
- `1:nil == 1:nil` is `true`
- `1:nil == 2:nil` is `false`
- `1:nil == nil` is `false`
- function elements compare by existing function pointer identity

Comparing lists with non-list values remains `ENACT_ERR_TYPE_EQUALITY_MISMATCH`.

## 10. Boundary Analysis Requirements

The regression suite shall include:

- empty list
- singleton integer list
- two-element integer list
- string and boolean list values
- nested list printing
- assigned list value
- cons with an assigned tail
- cons with arithmetic head precedence
- structural equality true
- structural inequality true
- list in a function argument
- list captured in a closure

## 11. Robustness Requirements

The regression suite shall include:

- cons tail is not a list
- cons tail is a boolean
- missing cons right operand
- leading cons operator
- list in arithmetic
- list in ordering
- list compared with non-list
- `nilx` remains an identifier

## 12. Acceptance Criteria

This slice is accepted when:

- `nil` tokenizes as `TOK_NIL`
- `:` tokenizes as `TOK_CONS`
- list values evaluate and print in cons form
- cons rejects non-list tails
- lists copy/free safely through environments
- list equality is structural
- previous function and whitespace application tests remain green
- handwritten source coverage remains reported separately from generated parser/lexer coverage
