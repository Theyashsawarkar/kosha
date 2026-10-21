# Changelog

Newest first. Releases are tags (`vX.Y.Z`) with `VERSION` in `kosha/__init__.py`.

## v0.2.0 -- 2026-10-21

A new interface, faster, and help for every command.

- **Looks like nala**: boxed tables, a full-width header per step, coloured
  status (● up to date, ▲ update, ● pinned, ◆ linked), and a summary line
  (`Summary: Install 2 · Upgrade 3`). Install, update and remove show what
  will happen first and ask `Do you want to continue? [Y/n]` (`-y` skips it;
  scripts without a terminal aren't asked).
- **Live progress**: downloads run in parallel, one animated line per package,
  ending in ✓ or ✗; then each update's changelog under "What's new in …", and
  the total time.
- **Faster**: newest releases are remembered for 15 minutes (`-r` asks again),
  every package's version is read in parallel, clones are blobless, and
  installs download everything at once before finishing in dependency order.
  `kosha list` takes about 0.2 s with a warm cache.
- **Help**: `kosha help` groups every command (Find, Install, Maintain,
  Develop, Help) with options and examples; `kosha help <command>` or
  `kosha <command> --help` shows one command in detail; a mistyped command or
  package suggests the right one ("did you mean kosha install?").
- **Aliases**: `ls`, `find`, `show`, `i`, `add`, `up`, `upgrade`, `rm`, `log`, `check`.
- **Tab completion**: `kosha completions zsh|bash` (commands and package names).
- `-q` for quiet output, `--no-color` (or `NO_COLOR`).

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
