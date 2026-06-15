# ENACT Product Requirements Document

Status: Draft 0.1

Last updated: 2026-06-15

Owner: `2606_enact_auto`

## 1. Purpose

This document defines the product requirements for a new implementation of the ENACT executable specification language, based on the ENACT reference manual found in [260614_enact_manual.pdf](/home/tprover/2606_enact_auto/260614_enact_manual.pdf) and implemented with `flex`, `bison`, and `C`.

The immediate goal is not to invent a new language from scratch. The immediate goal is to reconstruct a compatible ENACT core faithfully enough to run manual-derived examples, then extend it carefully where needed.

## 2. Product Vision

ENACT should become a small, test-first, executable specification language implementation with the following characteristics:

- Reference-compatible with the ENACT manual where behavior is explicitly described.
- Implemented as a REPL plus file loader.
- Built in `C` with a `flex` lexer and `bison` parser.
- Suitable for incremental grammar growth from example-driven regression tests.
- Shipped with strict quality gates from the first development milestone.

## 3. Source Basis

This PRD is based on the ENACT reference material visible in Appendix 1 of the supplied PDF, especially the pages rendered as 223-239 in the appendix.

The following items are confirmed directly from the manual:

- ENACT is a read-eval-print loop language.
- Expressions are terminated by a hard full stop `.` followed by whitespace, usually end-of-line.
- Comments start with `%` and continue to the next newline.
- Identifiers are formed from letters, digits, and underscore, and may not start with a digit.
- Historical ENACT uses `~` rather than unary minus for negative numbers.
- ENACT is expression-based and operator precedence is central to parsing.
- Functions are first-class values.
- Lambda expressions, currying, local definitions, and fixed-point style recursive definitions are supported.
- ENACT supports classes, objects, methods, attributes, `self`, inheritance, and multiple inheritance.
- ENACT includes list processing and predefined collection classes including `Set` and `Bag`.
- Variables are statically bound at function definition time, while object attributes are dynamically observed through objects.

The following items are not yet fully confirmed from the current manual slice and must be treated as design decisions rather than reference facts:

- A distinct `string` runtime type separate from quoted symbols or atoms.
- Exact lexical and semantic rules for all quoting forms beyond the examples shown.
- Full semantics of collection class definitions from Appendix 2.
- Exact method resolution details in all multiple inheritance edge cases.

For this project, we make one explicit extension decision early:

- Double-quoted literals such as `"hello world"` will be interpreted as immutable `string` values in the project-default mode.
- Atom or symbol values will remain available separately via bare identifiers and single-quote forms such as `'hello`.
- The project-default syntax will use the standard `-` sign for negative integer literals and unary arithmetic negation instead of historical `~`.
- Lexical analysis and parsing must explicitly distinguish unary minus from binary subtraction, using a dedicated `UNARY_MINUS` handling strategy or an equivalent implementation with the same observable behavior.
- The project-default syntax will use `==` for equality comparison instead of historical `=`.
- The project-default syntax will use `!=` for inequality comparison instead of historical `<>`.
- Assignment will remain `:=`, so the equality modernization must not blur assignment semantics.

## 4. Product Goals

- Reconstruct a usable ENACT interpreter that can execute the reference manual examples.
- Preserve ENACT's mixed functional and object-oriented style.
- Support incremental language growth driven by regression tests.
- Make grammar changes safe through automated parser and evaluator tests.
- Provide enough internal structure to later add diagnostics, tracing, and compatibility modes.

## 5. Non-Goals For Initial Delivery

- Native code generation or optimization.
- JIT compilation.
- Full source-to-source compatibility with any unpublished historical ENACT implementation details not evidenced by available material.
- Aggressive performance tuning before semantic compatibility is stable.
- Premature introduction of features that conflict with the manual.

## 6. Target Users

- Language implementers reconstructing ENACT behavior.
- Researchers or developers exploring executable specification languages.
- Users who want to run and evolve ENACT examples from the Henderson material.
- Developers who need a small reference interpreter for experimentation and regression testing.

## 7. Product Principles

- Reference before invention: when manual evidence exists, the implementation should follow it.
- Tests before expansion: every newly supported syntax or semantic rule must arrive with regression coverage.
- Small semantic core: surface syntax may grow incrementally, but runtime semantics should stay simple and explicit.
- Explain ambiguity: when the manual leaves behavior unclear, the implementation must document the chosen rule.

## 8. Functional Requirements

### 8.1 Runtime Model

The system shall provide:

- A REPL that reads ENACT expressions, evaluates them, and prints results.
- A file loader via `load "filename"` for batch execution of ENACT scripts.
- A runtime value model that supports at minimum integers, booleans, strings, lists, functions, classes, objects, sets, and bags.
- Immutable string values. A string value may be bound to variables and passed to functions, but its contents may not be modified in place.

### 8.2 Lexical Rules

The lexer shall support at minimum:

- Identifiers.
- Integer literals.
- Negative integer notation using `-`.
- Explicit unary-minus classification for minus signs used in unary position.
- Double-quoted string literals.
- Dot `.` as expression terminator.
- Parentheses, comma, semicolon, colon, and dot-member access.
- Quoted atoms or symbols, including examples such as `'hello`.
- Line comments beginning with `%`.
- Reserved words and operators including `class`, `new`, `with`, `then`, `else`, `if`, `where`, `loop`, `load`, and `fix`.
- Equality comparison written as `==` in the project-default mode.

### 8.3 Expression Syntax

The parser shall support at minimum:

- Arithmetic expressions using unary `-`, binary `+`, binary `-`, `*`, `/`, and `mod`.
- Relational expressions using `==`, `!=`, `<`, `>`, `<=`, `>=`.
- Logical expressions using `and`, `or`, and unary `not`.
- Conditional expressions using `a then b`, `b if a`, and `c else d`.
- Assignment expressions using `:=`.
- Sequencing using `;`.
- Local definitions using `where`.
- Fixed-point recursive definitions using `fix`.
- Function application in both parenthesized and whitespace-applied forms.

### 8.4 Function Features

The evaluator shall support:

- Function definitions such as `f(x):=x+1` and `f x := x+1`.
- Multi-argument function definitions such as `g(x,y):=x+y`.
- Function application such as `f(99)` and `f 99`.
- Higher-order functions.
- Lambda expressions using `::`.
- Currying and partial application.
- Eager evaluation semantics. Lazy evaluation is not required for compatibility.
- Static binding of free variables at function definition time.

### 8.5 List Features

The evaluator shall support:

- The empty list `nil`.
- Cons construction using `:`.
- Tuple-like list construction using `(x,y,z,...)`.
- Predefined list operations including `hd`, `tl`, `append`, `size`, `map`, `filter`, `all`, and `reduce`.
- The documented singleton list conventions such as `99:nil`, `99:()`, and `list 99`.

### 8.6 Object-Oriented Features

The evaluator shall support:

- Root object/class behavior centered on `Object`.
- Class definition syntax such as `class Node < Object.` and `class C < (A,B).`
- Object construction using `new`.
- Attribute initialization using repeated `with`.
- Attribute access using `a.attr`.
- Method definition on classes using syntax such as `A.f(x,y):=...`.
- `self` binding within methods.
- Inheritance of methods and attributes.
- Multiple inheritance.
- Ambiguity inspection functions described by the manual, including `classes`, `supers`, `superiors`, `suppliers`, `OK`, and `badAttrs`.

### 8.7 Collection Features

The evaluator shall support:

- Predefined collection classes `Set` and `Bag`.
- Constructors such as `set()` and `bag()`.
- Collection methods such as `member`, `size`, `insert`, `remove`, `collect`, `forEachDo`, `select`, `reduce`, `locate`, `all`, and `exists`.
- Set-specific operations including `add`, `subset`, `equal`, `union`, `difference`, `intersection`, and `UNION`.
- Identity-sensitive object membership behavior consistent with the manual's warning that ENACT sets are not exact mathematical sets.

### 8.8 Built-in Functions And Utilities

The initial built-in library shall include:

- `not`, `hd`, `tl`, `atom`, `isObject`, `append`, `size`, `map`, `filter`, `all`, `reduce`.
- Set helper functions such as `union`, `difference`, `intersection`, `member`, `remove`, and `unitset`.
- Introspection and utility functions including `classof`, `attrs`, `time`, `cells`, `maxcells`, `version`, `bye`, and `ask`.

## 9. Operator Precedence Requirements

The parser shall respect the precedence table documented in the manual:

| Level | Operators |
| --- | --- |
| 1 | `'`, `new` |
| 2 | `.` |
| 3 | application |
| 4 | `*`, `/`, `mod` |
| 5 | `+`, `-`, `:` |
| 6 | `==`, `!=`, `>`, `<`, `>=`, `<=` |
| 7 | `with`, `::`, `where` |
| 8 | `and`, `loop` |
| 9 | `or` |
| 10 | `if`, `then` |
| 11 | `else` |
| 12 | `:=` |
| 13 | `;`, `class`, `load`, `fix` |

Because the manual presentation around assignment precedence is subtle, implementation notes must explicitly explain any parser strategy used to resolve apparent overlaps.

Project extension note:

- The project-default grammar introduces unary minus as a modernized replacement for historical `~`.
- Unary minus should bind more tightly than `*`, `/`, and `mod`.
- Lexer and parser design must make unary minus explicit enough that regression tests can distinguish it reliably from binary subtraction.
- The project-default grammar introduces `==` as a modernized replacement for historical equality `=`.
- The project-default grammar introduces `!=` as a modernized replacement for historical inequality `<>`.
- Equality and assignment must stay visually distinct: `==` for comparison, `:=` for assignment.

## 10. Compatibility Strategy

The product shall define two compatibility layers:

- `Reference ENACT Core`: behavior directly evidenced in the manual and used as the compatibility baseline.
- `Project Extensions`: features desired by this project but not yet confirmed by the manual, such as a first-class `string` type if we choose to add one.

If a proposed extension conflicts with manual-derived syntax or semantics, the reference-compatible behavior wins unless an explicit compatibility mode is introduced.

Current recommendation:

- The project-default behavior should interpret double-quoted literals as immutable strings.
- The project-default behavior should interpret equality comparison as `==`.
- The project-default behavior should interpret inequality comparison as `!=`.
- A future strict compatibility mode may reinterpret double-quoted literals according to historical ENACT behavior if strong reference evidence requires it.
- A future strict compatibility mode may accept historical equality `=` if strong reference evidence or compatibility goals require it.
- A future strict compatibility mode may accept historical inequality `<>` if strong reference evidence or compatibility goals require it.

## 11. Initial Scope Recommendation

The first compatibility target should include:

- REPL and expression terminator handling.
- Integer, boolean, string, list, atom, function, class, object, and set values.
- Arithmetic, comparison, logic, conditionals, assignment, sequencing, and local definitions.
- Function definition, application, lambda, and currying.
- Class definition, `new`, `with`, attribute access, method calls, and multiple inheritance.
- Manual-derived predefined functions needed to run the appendix examples.

The following should be deferred to a later milestone unless manual review proves they are required immediately:

- Rich string operations, formatting, interpolation, or mutable string buffers.
- Full Appendix 2 collection class source compatibility.
- Performance tuning beyond correctness.
- Extended tooling such as debugger, formatter, or LSP support.

## 12. Test And Quality Requirements

Testing is a primary product requirement, not a follow-up task.

The project shall adopt the following rules from the first implementation milestone:

- Every supported syntax form must have at least one parser acceptance test.
- Every semantic rule must have at least one evaluator regression test.
- Every bug fix must be accompanied by a regression test that fails before the fix and passes after it.
- Boundary analysis tests must exist for all core value types and key syntactic forms.
- Robustness tests must exist for malformed input, precedence ambiguity, invalid method access, inheritance ambiguity, assignment side-effects, and collection edge cases.
- Statement coverage must be at least 95%.
- Branch coverage must be at least 90%.

Recommended test categories:

- Lexer tests.
- Parser acceptance tests.
- Parser rejection tests.
- AST shape tests where useful.
- Evaluator golden tests from manual examples.
- Error-message tests for malformed programs.
- Regression tests for multiple inheritance ambiguity.
- Memory-management and teardown tests for runtime values.

Representative boundary and robustness coverage must include:

- Empty input and missing final `.`.
- Negative integers using unary `-`.
- Singleton list ambiguity.
- Curried functions with zero, one, and many applications.
- Nested `then` and `else` expressions.
- Recursive definitions using `fix`.
- Multiple inheritance with and without conflicting inherited attributes.
- Empty and non-empty sets and bags.
- Set operations involving duplicate-like object identities.

## 13. Technical Approach

The implementation shall be written in `C` and should be organized into the following layers:

- `lexer`: tokenization in `flex`.
- `parser`: syntax analysis in `bison`.
- `ast`: syntax tree definitions and builders.
- `runtime`: value types, environments, class/object model, collection model.
- `evaluator`: expression execution and built-in dispatch.
- `repl`: interactive loop and file loading.
- `tests`: lexer, parser, evaluator, and regression suites.

The parser should be example-driven. Grammar rules should be added only alongside example coverage and should not be generalized prematurely without tests.

## 14. Milestones

### Milestone 1: Language Skeleton

- Build system established.
- `flex` and `bison` integrated.
- REPL can read expressions and recognize terminators.
- Basic lexer tests and parser smoke tests exist.

### Milestone 2: Functional Core

- Arithmetic, comparison, logic, function definition, application, lambda, currying, and `where` work.
- Manual examples for `factorial`, `nfib`, `reverse`, and `twice` pass.

### Milestone 3: Object Core

- `class`, `new`, `with`, attributes, methods, `self`, inheritance, and multiple inheritance work.
- Manual examples for `Leaf`, `Tree`, parent recomputation, and class conflict examples pass.

### Milestone 4: Collections And Introspection

- `Set`, `Bag`, predefined collection methods, and ambiguity-analysis helpers work.
- Manual examples for `set()`, `collect`, `union`, `difference`, `UNION`, and `badAttrs` pass.

### Milestone 5: Hardening

- Coverage gates are enforced in CI.
- Robustness tests expanded.
- Error handling improved.
- Documentation aligned with implemented behavior.

## 15. Iterative Delivery Workflow

Development should proceed in small language slices, each slice covering one coherent feature area such as:

- one lexical rule family
- one operator group
- one expression form
- one function feature
- one object model feature
- one collection feature

Every slice should follow the same lifecycle:

1. Requirements analysis
   Confirm what the manual proves, what the project is choosing as an extension, what inputs must be accepted, and what outputs or side-effects are expected.

2. Design
   Define the lexer impact, parser impact, AST shape, runtime behavior, evaluator rule, error behavior, and required tests before implementation begins.

3. Review
   Check the design for grammar conflicts, precedence risks, semantic ambiguity, compatibility risk, and testability. No implementation should start until the slice is small enough and the acceptance criteria are clear.

4. Development
   Implement the slice in `flex`, `bison`, runtime, and evaluator code. Keep the change set narrowly scoped to the slice under development.

5. Regression testing
   Add and run positive tests, negative tests, boundary-analysis tests, and robustness tests for the slice. All previously passing tests must remain green.

6. Result review
   Review parser behavior, runtime behavior, diagnostics, and coverage impact. Record any follow-up issues, ambiguities, or deferred work before moving to the next slice.

Each slice should produce the following minimum artifacts:

- a short requirement note or issue description
- a design note if semantics or grammar are non-trivial
- implementation changes
- regression tests
- a short review summary capturing what was confirmed and what remains open

Recommended execution rules:

- Never combine unrelated language features in one slice.
- Prefer slices small enough to review in one sitting.
- Treat regression tests as part of development, not as a final validation step.
- If a slice reveals an ambiguity in the manual, freeze the discovered behavior in tests and document the decision explicitly.

## 16. Risks

- Whitespace-sensitive function application may introduce parser conflicts.
- Assignment, `where`, `if/then/else`, and `fix` may interact in subtle precedence-dependent ways.
- Multiple inheritance semantics may be under-specified in edge cases outside the examples.
- Set equality and membership semantics for objects are not mathematical and must mirror ENACT's object identity behavior.
- A separate `string` type may conflict with the atom model if introduced too early.

## 17. Open Questions

- Which escape sequences, if any, should be recognized inside double-quoted string literals in the first implementation?
- Should `Set` and `Bag` be required before the first public compatibility release, or may they land after the object model is stable?
- Do we want a strict reference mode and an extension mode, or only one evolving implementation?
- How closely do we want to emulate the original printing behavior for objects, invented names, and collection display?
- Do we want to preserve 32-bit integer arithmetic exactly, or allow wider host arithmetic internally with compatibility tests around overflow-sensitive cases?

## 18. Acceptance Criteria For PRD Approval

This PRD should be considered approved for implementation only if we agree on the following:

- The project will prioritize ENACT reference compatibility over speculative modernization.
- The initial implementation language and parser technology will be `C`, `flex`, and `bison`.
- Testing and coverage thresholds are mandatory, not aspirational.
- The project-default implementation will treat double-quoted literals as immutable strings, while atom-like symbolic values remain separate.
- The first coding milestone will target a working functional and object-oriented reference subset rather than the full historical distribution.
