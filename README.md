<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/banner-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="assets/banner-light.svg">
    <img alt="kosha" src="assets/banner-dark.svg" width="560">
  </picture>
</p>

<p align="center">
  <b>The package manager for Vayu's tools: install, update, pin and remove them with one command.</b><br>
  Every tool is its own git repository; kosha knows them all, installs released versions, and tells you what changed.
</p>

<p align="center">
  <a href="https://github.com/Theyashsawarkar/kosha/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/Theyashsawarkar/kosha/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://github.com/Theyashsawarkar/kosha/releases"><img alt="Release" src="https://img.shields.io/github/v/release/Theyashsawarkar/kosha?color=f9e2af&label=release"></a>
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-f5e0dc"></a>
  <img alt="Python 3.11+, no dependencies" src="https://img.shields.io/badge/python-3.11%2B%2C%20stdlib%20only-a6e3a1">
</p>

> *Kosha* (कोश) is Sanskrit for "treasury, storehouse": where all the
> tools are kept.

[Vayu](https://github.com/Theyashsawarkar/vayu)'s tools each live in their
own repository: the [Vyom](https://github.com/Theyashsawarkar/vyom) panels
and their fourteen tools, [nāda](https://github.com/Theyashsawarkar/nada),
[anumati](https://github.com/Theyashsawarkar/anumati),
[sangam](https://github.com/Theyashsawarkar/sangam), and whatever comes
next. That keeps each one independent, but leaves you with many clones to
keep track of. kosha does it for you: it knows where each tool goes,
installs its newest **release**, installs what it depends on first, checks
for updates in one go, shows the changelog when it updates, and lets you pin
a version or work on a tool from your own checkout.

## Contents

- [Features](#features)
- [Install](#install)
- [Usage](#usage)
- [Packages](#packages)
- [How it works](#how-it-works)
- [Adding a package](#adding-a-package)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Features

- **One list of everything**: `kosha list` shows every package, the version
  you have, the newest release, and whether it's pinned, linked or out of date.
- **Released versions**: installs and updates move between release tags
  (`v0.1.4`), never onto unreleased commits. `kosha install ganit@0.1.2`
  installs and pins an older one.
- **Dependencies first**: installing a Vyom tool installs Vyom; removing
  Vyom is refused while a tool needs it.
- **See what's new before you update**: `kosha fetch` asks GitHub for the
  newest package list and every package's newest release (metadata only,
  nothing on disk changes) and shows each installed package next to
  GitHub's: updates, development checkouts with unreleased commits, and
  what the package list added or changed. Then `kosha update` installs.
- **Updates that tell you what changed**: `kosha update` updates everything
  in parallel and prints each tool's changelog since your version.
- **Adopts what's already there**: tools you cloned by hand (or an older
  installer did) are recognised and managed as they are, nothing re-downloaded.
- **Safe with your work**: a clone with local changes is never updated or
  removed without `--force`, and `--force` stashes rather than discards.
- **Develop in place**: `kosha link nada ~/code/nada` runs your checkout
  instead of the release; `kosha unlink nada` puts the release back.
- **System packages**: when a tool needs a program you don't have, kosha says
  which, and on Arch offers to install it (through
  [anumati](https://github.com/Theyashsawarkar/anumati) when it's there).
- **Scriptable**: `kosha list --json`, `kosha fetch --json`, `kosha outdated --json`, meaningful
  exit codes, `NO_COLOR` respected.
- **No dependencies** beyond git and Python 3.11's standard library.

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/Theyashsawarkar/kosha/main/install.sh | bash
```

It clones kosha into `~/.local/share/kosha`, links `~/.local/bin/kosha`,
and needs no root. Or by hand:

```sh
git clone https://github.com/Theyashsawarkar/kosha ~/.local/share/kosha
ln -s ~/.local/share/kosha/bin/kosha ~/.local/bin/kosha
kosha install kosha          # kosha manages itself from now on
```

Then install what you want, e.g. the launcher, the calculator and the music player:

```sh
kosha install dvara ganit nada
```

## Usage

`kosha help` shows every command, grouped, with examples; `kosha help <command>`
(or `kosha <command> --help`) explains one. A typo gets a suggestion.

```
kosha help [<command>]                 every command, or one in detail
kosha list [--installed] [--json]      packages: installed version, newest release
kosha search <words>                   find packages by name or description
kosha info <pkg>                       details, where it lives, what it needs
kosha install <pkg>[@version] ...      install (newest release, or a pinned one) with its dependencies
kosha update [<pkg> ...] [--force]     update to the newest release (everything, without names)
kosha fetch [--json]                   ask GitHub what's new, show how it differs from yours (changes nothing)
kosha outdated [--json]                what has a newer release
kosha remove <pkg> ...                 uninstall
kosha pin <pkg> | unpin <pkg>          keep a package on its version / let it update again
kosha link <pkg> <path> | unlink <pkg> use a development checkout in place of the release
kosha changelog <pkg> [<from>]         what changed (since a version)
kosha doctor                           check every installed package
kosha refresh                          download the newest package list
kosha self-update                      update kosha itself
kosha completions zsh|bash             tab completion for commands and packages

Options: -y/--yes (don't ask), -v/--verbose (every step and git command), -q/--quiet, -r/--refresh (ask GitHub now),
         --json (list, fetch, outdated), --no-color (or NO_COLOR=1)
```

Every step shows a live row per package (what it's doing now, then its
result and time). Install, update and remove check each package, show a table
of what will happen, and ask before doing it:

```console
$ kosha update
━━ Upgrading ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
╭─────────┬───────────┬───┬────────┬───────────╮
│ Package │ Installed │   │ New    │ Kind      │
├─────────┼───────────┼───┼────────┼───────────┤
│ dvara   │ v0.1.3    │ → │ v0.1.5 │ vyom tool │
│ ganit   │ v0.1.2    │ → │ v0.1.4 │ vyom tool │
╰─────────┴───────────┴───┴────────┴───────────╯
Summary:  Upgrade 2
? Do you want to continue? [Y/n]
━━ Downloading ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 2 packages
✓ dvara  downloaded
✓ ganit  downloaded
✓ dvara v0.1.3 → v0.1.5
✓ ganit v0.1.2 → v0.1.4
━━ What's new in dvara ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
v0.1.5 -- 2026-10-21
  - A website (GitHub Pages): the README as a home page, the changelog…
━━ 2 upgraded in 2.1s
```

Tab completion, for zsh (with oh-my-zsh or `compinit`):

```sh
source <(kosha completions zsh)        # in ~/.zshrc
```

```console
$ kosha list --installed
package  installed  latest  kind         status
nada     v0.1.1     v0.1.1  app          up to date
vyom     v0.2.8     v0.2.8  vyom         up to date
ganit    v0.1.2     v0.1.4  vyom-tool    pinned
dvara    v0.1.5     v0.1.5  vyom-tool    linked (dev)
```

Exit codes: `0` success, `1` something failed (each failure is printed),
`2` a usage error.

## Packages

`kosha list` and `kosha search` show the current list. Today:

| Package | Kind | What it is |
|---|---|---|
| [vyom](https://theyashsawarkar.github.io/vyom/) | runtime | keyboard-driven panels for Wayland |
| [dvara](https://theyashsawarkar.github.io/dvara/), [ganit](https://theyashsawarkar.github.io/ganit/), [smriti](https://theyashsawarkar.github.io/smriti/), [bhava](https://theyashsawarkar.github.io/bhava/), [tarang](https://theyashsawarkar.github.io/tarang/), [setu](https://theyashsawarkar.github.io/setu/), [doot](https://theyashsawarkar.github.io/doot/), [patra](https://theyashsawarkar.github.io/patra/), [suchana](https://theyashsawarkar.github.io/suchana/), [raga](https://theyashsawarkar.github.io/raga/), [mudra](https://theyashsawarkar.github.io/mudra/), [urja](https://theyashsawarkar.github.io/urja/), [vishram](https://theyashsawarkar.github.io/vishram/), [kendra](https://theyashsawarkar.github.io/kendra/) | Vyom tools | apps, calculator, clipboard, emoji, Wi‑Fi, Bluetooth, phone, Docker, notifications, YouTube, keybindings, battery, power menu, quick settings |
| [nada](https://theyashsawarkar.github.io/nada/) | app | music player: your files and YouTube, lyrics, autoplay |
| [anumati](https://theyashsawarkar.github.io/anumati/) | app | root commands for AI agents, with your approval |
| [vesha](https://theyashsawarkar.github.io/vesha/) | app | every Claude Code account, one key away; switches at the usage limit |
| [kaushal](https://github.com/Theyashsawarkar/kaushal) | app | skills and tools for every AI agent, in every session |
| [varna](https://theyashsawarkar.github.io/varna/) | app | one theme for every tool, live |
| [vinyasa](https://theyashsawarkar.github.io/vinyasa/) | app | Vayu's settings app (needs varna) |
| [sangam](https://theyashsawarkar.github.io/sangam/) | tmux plugin | review and merge pull requests in the terminal |
| kosha | app | this package manager |

Where each kind installs:

| Kind | Folder | Command linked |
|---|---|---|
| `vyom` | `~/.local/share/vyom/core` | `~/.local/bin/vyom` |
| `vyom-tool` | `~/.local/share/vyom/plugins/<name>` | none (Vyom loads it; kosha runs `vyom reload`) |
| `app` | `~/.local/share/<name>` | `~/.local/bin/<name>` |
| `tmux-plugin` | `~/.tmux/plugins/<name>` (where TPM looks) | `~/.local/bin/<name>` if it has one |

## How it works

- **The registry** (`registry.toml`) lists every package: its repository,
  kind, dependencies, the commands it needs and the Arch packages that
  provide them, and an optional command to run after installing. kosha uses
  whichever is newer of the copy it shipped with and the one `kosha refresh`
  downloaded.
- **A package is a git clone** in the folder its kind prescribes. A version
  is a release tag; installing checks out the newest, updating fetches and
  checks out a newer one. Newest releases are asked of GitHub with
  `git ls-remote` (no clone needed), all packages in parallel.
- **The checkout is the truth.** kosha reads the version from git, so a tool
  updated by hand is still reported correctly. `~/.local/state/kosha/installed.json`
  only adds what git can't know (pinned, linked); `history.log` next to it
  records every install, update and removal.
- **Post-install commands** run in the package's folder (anumati's
  `install.sh`, which installs it root-owned and asks for your password).

The design decisions, with their reasons, are on the
[website](https://theyashsawarkar.github.io/kosha/adr/).

## Adding a package

A pull request adding a table to [`registry.toml`](registry.toml):

```toml
[packages.mytool]
repo = "you/mytool"            # GitHub owner/name, or a full git URL
kind = "vyom-tool"             # vyom | vyom-tool | app | tmux-plugin
description = "One line: what it is"
requires = ["vyom"]            # other kosha packages
commands = ["qalc"]            # programs it needs on PATH
arch = ["libqalculate"]        # Arch packages that provide them
post = "./install.sh"          # optional: run after install and update
```

The repository needs release tags (`v1.2.3`) and a `CHANGELOG.md` with one
`## v1.2.3` section per release, which `kosha update` prints. CI checks the
registry is valid.

## Troubleshooting

- **"has local changes".** Commit or stash them in the folder kosha names,
  or `kosha update --force` (stashes them; `git stash pop` brings them back).
- **"couldn't check".** GitHub was unreachable for that package; the rest
  still updated. Run it again later.
- **A command isn't found after installing.** `~/.local/bin` must be on your
  `PATH`; `kosha doctor` says so.
- **anumati's update asks for a password and fails in a script.** Its
  installer needs `sudo`: run `kosha update anumati` in a terminal.
- **Anything else**: `kosha doctor`, and `~/.local/state/kosha/history.log`.

## Contributing

Bug reports, ideas and pull requests are welcome: see
[CONTRIBUTING.md](CONTRIBUTING.md), and [CHANGELOG.md](CHANGELOG.md) for
what changed in each release. New packages are pull requests to the registry.

## License

[MIT](LICENSE)
