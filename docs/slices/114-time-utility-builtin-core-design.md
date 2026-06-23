# Slice 114: time Utility Builtin Core Design

## Overview

`time` is implemented as a zero-argument builtin beside `version` in `src/builtin.c`. It calls the host C library `time(NULL)` and returns the result as an `ENACT_VALUE_INT`.

## Runtime Rule

The builtin:

1. ignores its argument array after generic arity validation has accepted zero arguments.
2. calls `time(NULL)`.
3. checks that the returned `time_t` is non-negative and no larger than `INT_MAX`.
4. returns `enact_value_make_int((int32_t)now)`.

The range check keeps the builtin honest while ENACT integers are still represented as signed 32-bit values.

## Metadata

`time` uses the plain `ENACT_BUILTIN("time", 0, enact_builtin_time)` registration. That gives it no visible parameter names, so `callableParams(time)` naturally returns `nil`, matching `version`.

## Tests

Functional tests avoid exact timestamp assertions. Instead they check:

- integer result kind
- non-negative timestamp relation
- first-class callable behavior
- callable arity and parameter metadata
- use through a zero-argument higher-order helper
- ordinary environment shadowing
- arity diagnostics and result misuse diagnostics

Unit tests cover lookup, arity, direct builtin application returning a non-negative integer, and default environment installation.
