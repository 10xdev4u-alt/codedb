#!/usr/bin/env bash
# Install the repository commit hooks and commit template.
#
# Run once after cloning:
#   bash scripts/install-hooks.sh

set -euo pipefail

root=$(git rev-parse --show-toplevel)
hook="$root/scripts/hooks/commit-msg"
target="$root/.git/hooks/commit-msg"

if [[ ! -f "$hook" ]]; then
  printf 'missing %s\n' "$hook" >&2
  exit 1
fi

install -m 0755 "$hook" "$target"
git -C "$root" config commit.template "$root/.gitmessage"

printf 'installed commit-msg hook and commit template\n'
