# Changelog

Newest first. Releases are tags (`vX.Y.Z`) with `VERSION` in `kosha/__init__.py`.

## v0.1.0 -- 2026-10-21

First release.

- `list`, `search`, `info`, `install` (newest release, or `pkg@version` to pin),
  `update` (everything, in parallel, with each tool's changelog since your
  version), `outdated`, `remove`, `pin`/`unpin`, `link`/`unlink` (run a
  development checkout), `changelog`, `doctor`, `refresh`, `self-update`.
- Dependencies are installed first and protected from removal.
- Tools already on disk are adopted as they are.
- Missing programs are reported, and on Arch offered for install through anumati.
- The registry: Vyom and its fourteen tools, nāda, anumati, sangam, kosha.
- `--json` for `list` and `outdated`; a no-root installer.
