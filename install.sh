#!/usr/bin/env bash
# kosha's installer: clones kosha into ~/.local/share/kosha, links
# ~/.local/bin/kosha, and adopts the tools already installed. No root.
#
#   curl -fsSL https://raw.githubusercontent.com/Theyashsawarkar/kosha/main/install.sh | bash
#   ./install.sh [package ...]     also install these packages
set -euo pipefail
dest="${XDG_DATA_HOME:-$HOME/.local/share}/kosha"
bin="$HOME/.local/bin"
command -v git >/dev/null || { echo "kosha needs git" >&2; exit 1; }
command -v python3 >/dev/null || { echo "kosha needs python3 (3.11 or newer)" >&2; exit 1; }
python3 -c 'import sys, tomllib; sys.exit(sys.version_info < (3, 11))' 2>/dev/null ||
  { echo "kosha needs Python 3.11 or newer" >&2; exit 1; }
if [ -d "$dest/.git" ]; then
  git -C "$dest" fetch -q --tags origin
else
  git clone -q https://github.com/Theyashsawarkar/kosha "$dest"
fi
latest=$(git -C "$dest" tag -l 'v*' --sort=-v:refname | head -1)
[ -n "$latest" ] && git -C "$dest" -c advice.detachedHead=false checkout -q "$latest"
mkdir -p "$bin"
ln -sfn "$dest/bin/kosha" "$bin/kosha"
"$bin/kosha" install kosha >/dev/null
echo "kosha ${latest:-(main)} installed: $bin/kosha"
case ":$PATH:" in *":$bin:"*) ;; *) echo "add $bin to your PATH" ;; esac
if [ "$#" -gt 0 ]; then "$bin/kosha" install "$@"; fi
