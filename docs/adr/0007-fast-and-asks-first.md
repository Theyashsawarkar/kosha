# 7. Show the plan, ask, then do the slow work in parallel

**Status:** Accepted  
**Date:** 2026-10-21

## Context

kosha 0.1 printed one line per step and did everything one package at a time:
an update of many tools waited on each `git fetch` in turn, and nothing said
what was about to change before it changed. People coming from nala and
pacman expect to see the transaction and confirm it, and expect a package
manager to feel instant for read-only commands.

## Decision

- Every command that changes something shows a table of what will happen and
  a summary line, then asks `Do you want to continue? [Y/n]` (`-y` skips it;
  without a terminal the default is assumed, so scripts and installers work).
- Network work runs in parallel with a live line per package; the local part
  (checkout, links, post-install commands, which may ask for a password) runs
  afterwards in dependency order, one at a time.
- "Newest release" answers are cached for 15 minutes for read-only commands
  (`list`, `info`, `outdated`); `update` always asks again. Versions on disk
  are read in parallel. New clones are blobless.

## Consequences

- `kosha list` answers in about 0.2 s with a warm cache; updates take about as
  long as the slowest repository.
- The interface is drawn with ANSI escapes; without a terminal (or with
  `NO_COLOR`) it falls back to plain lines.
