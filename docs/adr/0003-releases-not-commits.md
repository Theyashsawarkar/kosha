# 3. Install and update release tags, not commits

**Status:** Accepted  
**Date:** 2026-10-21

## Context

Tools change often on their main branches. Following main means unreleased work lands on every machine and nobody can say which version they run.

## Decision

A version is a `vX.Y.Z` tag. Installing checks out the newest; updating moves to a newer one; `pkg@version` installs and pins an older one. Newest versions come from `git ls-remote --tags`.

## Consequences

- Every machine runs a version with a changelog entry and a GitHub release.
- A fix reaches users only when it's released.
- A repository with no tags stays on its default branch.
