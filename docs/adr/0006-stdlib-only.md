# 6. Python standard library only

**Status:** Accepted  
**Date:** 2026-10-21

## Context

kosha installs everything else, so it has to work on a fresh system before anything else is installed.

## Decision

kosha needs only git and Python 3.11 (for tomllib); no third-party modules.

## Consequences

- Installs anywhere with one command.
- Some conveniences (rich tables, progress bars) are written by hand or left out.
