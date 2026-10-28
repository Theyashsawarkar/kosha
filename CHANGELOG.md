# Changelog

Newest first. Releases are tags (`vX.Y.Z`) with `VERSION` in `kosha/__init__.py`.

## Unreleased

- **kaushal** joins the registry: Vayu's skills and MCP tools for every AI
  agent (Claude Code, Codex, opencode, Gemini CLI), synced on install and
  update.

## v0.4.0 -- 2026-10-28

- **`kosha fetch`**: see what's new on GitHub before updating. It downloads
  the newest package list and asks every installed package's repository
  for its newest release (`git ls-remote`: metadata only, no checkout
  changes), then shows each package next to GitHub's: `▲ update`,
  `● pinned`, `● up to date`, and for a linked checkout whether a newer
  release is out or how many unreleased commits it's past its tag. Below
  that, packages new in the list, ones removed, and entries of yours that
  changed (their `post`, `arch`...). `kosha update` then installs the
  updates; `--json` for scripts.

## v0.3.1 -- 2026-10-21

- **Follows your theme**: with [varna](https://github.com/Theyashsawarkar/varna)
  installed, kosha's output takes the current theme's colours (its own pick
  under `tools.kosha`, else the desktop's); without it, as before.

## v0.3.0 -- 2026-10-21

You see what kosha is doing for each package, at every step.

- **A live board per step**: one row per package, with what it's doing right
  now ("checking v0.1.3…", "cloning…", "fetching v0.1.5…", "checking out
  v0.1.5"), then its result and how long it took; a footer counts done,
  running, waiting and failed, with the time so far. Long lists fit the screen
  (running rows first). `update` and `install` check every package this way
  before showing the plan; `list`, `outdated`, `remove` and `doctor` use it too.
- **`-v` / `--verbose`**: every step as a timestamped line, and every git
  command with its exit code and time.
- **Doctor**: a row per package, then the findings, each with the command that fixes it.
- **The `[Y/n]` question** takes a single key and prints the answer (Yes/No);
  Esc or Ctrl-C mean no.
- **Robust**: one kosha changes things at a time (a lock); an interrupted or
  failed clone leaves no half-made folder; Ctrl-C marks what didn't finish as
  cancelled and restores the cursor; offline and missing-repository errors say
  so in plain words; git that hangs times out.
- Tab completion asks kosha for package names instantly (`kosha _names`), never the network.
- Linted with ruff (`ruff.toml`; CI runs it). The site builder no longer needs Python 3.12.

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
