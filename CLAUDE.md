# kosha -- notes for agents

The package manager for Vayu's tools: each tool is its own git repository,
and kosha installs, updates, pins and removes them by release tag. Its own
repo, pulled into Vayu (github.com/Theyashsawarkar/vayu, whose CLAUDE.md
"Plugins" rules apply); it must work without Vayu.

- `bin/kosha`: the commands. `kosha/core.py`: registry, packages, versions,
  dependency order, actions. `registry.toml`: every package.
- A new Vayu tool gets a table in `registry.toml` (and release tags and a
  CHANGELOG in its own repo); Vayu's install.sh installs from the registry.
- The checkout is the truth (versions come from git). Never update or remove a
  clone with local changes without `--force`; `--force` stashes.
- Standard library only. `python -m py_compile bin/kosha kosha/*.py` and
  `python -m unittest discover -s tests` must pass.
- Test with a throwaway HOME (`HOME=$(mktemp -d) bin/kosha ...`), never on the
  user's real installs unless asked.
- Every change: a CHANGELOG.md entry; releases are tags with `VERSION` bumped.
- The website (docs/, GitHub Pages) is generated: after changing README.md, CHANGELOG.md or docs/adr/, run `python3 scripts/build-site.py` and commit docs/ (CI checks it). A significant design decision gets a new ADR in docs/adr/ (next number; supersede, never rewrite).
