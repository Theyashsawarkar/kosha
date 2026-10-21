# Contributing to kosha

Thanks for helping. New packages, bug reports, ideas and pull requests are
all welcome.

## Adding a package

Add a table to `registry.toml` (the README's "Adding a package" lists the
fields) and run `python -m unittest discover -s tests`: it checks every
package has a repository, a known kind and a description, and that the
dependencies exist and have no cycles. The package's repository needs
release tags (`v1.2.3`) and a `CHANGELOG.md` with `## v1.2.3` sections.

## Development setup

```sh
git clone https://github.com/Theyashsawarkar/kosha ~/code/kosha
cd ~/code/kosha
python -m py_compile bin/kosha kosha/*.py
python -m unittest discover -s tests -v
HOME=$(mktemp -d) bin/kosha install ganit     # try it without touching your real installs
```

## How it fits together

- `bin/kosha`: the commands and their output.
- `kosha/core.py`: the registry, packages (where each kind installs, versions
  from git), dependency order, and the install/update/remove actions.
- `registry.toml`: every package.

## Rules

- **The checkout is the truth**: read versions from git, never only from
  kosha's state file.
- **Never lose someone's work**: refuse to update or remove a dirty clone
  without `--force`, and make `--force` recoverable (stash, not reset).
- **Releases, not commits**: install and update move between release tags.
- **Standard library only**: kosha must install on a fresh system with only
  git and Python.
- Every change gets a `CHANGELOG.md` entry; releases are tags `vX.Y.Z` with
  `VERSION` in `kosha/__init__.py` bumped. The website is generated:
  `python3 scripts/build-site.py` after changing the README, CHANGELOG or ADRs.

## Pull requests

Describe what and why, and tick the template's checklist. By contributing
you agree your work is released under the [MIT License](LICENSE).
