# 2. One registry file, in kosha's repository

**Status:** Accepted  
**Date:** 2026-10-21

## Context

kosha needs to know every package: where it lives, its kind, what it needs. That could live in each package's repository (a manifest kosha discovers) or in one index.

## Decision

Every package is a table in `registry.toml` in kosha's repository. kosha ships with it and `kosha refresh` downloads the newest; whichever copy is newer is used. Adding a package is a pull request.

## Consequences

- One place to review what kosha may install (it runs `post` commands).
- Listing and searching need no network.
- A package's details change through kosha's repository, not its own.
