# Security policy

## Supported versions

Only the latest release of kosha gets fixes.

## Reporting a vulnerability

Please **don't open a public issue**. Report it privately through
[GitHub's security advisories](https://github.com/Theyashsawarkar/kosha/security/advisories/new),
with what an attacker could do and how to reproduce it. You'll get a reply
within a week; a fix and a release follow as soon as it's confirmed, with
credit to you unless you'd rather not.

kosha runs as your user. It installs code from the repositories in its registry and runs their
`post` commands: a change to the registry is reviewed like code.
