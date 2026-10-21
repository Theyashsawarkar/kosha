## What and why

<!-- What this changes: a new package, a fix, a feature. -->

## Checklist

- [ ] `python -m unittest discover -s tests` passes (it validates the registry)
- [ ] Tested with a throwaway home: `HOME=$(mktemp -d) bin/kosha install <pkg>`
- [ ] A `CHANGELOG.md` entry (not needed for a registry-only change)
- [ ] A new package has release tags and a CHANGELOG with `## vX.Y.Z` sections
