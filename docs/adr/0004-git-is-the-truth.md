# 4. The git checkout is the source of truth

**Status:** Accepted  
**Date:** 2026-10-21

## Context

A package manager with its own database can drift from what's on disk: someone updates a tool by hand, or an old installer cloned it.

## Decision

kosha reads each package's version from its checkout (`git describe --tags`). Its state file only adds what git can't know: pinned, linked. Clones found on disk are adopted as they are.

## Consequences

- Hand-made changes are reported correctly.
- Existing installs move to kosha without re-downloading.
