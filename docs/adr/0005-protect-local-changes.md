# 5. Never lose local changes

**Status:** Accepted  
**Date:** 2026-10-21

## Context

People edit tools in place, and Vayu's own workflow links development checkouts into place.

## Decision

A clone with local changes is never updated or removed without `--force`, and `--force` stashes the changes rather than discarding them. `kosha link` swaps in a development checkout and keeps the release aside for `kosha unlink`.

## Consequences

- Updates can refuse; the message says why and how to proceed.
