#!/bin/bash
# usage: install_maps.sh <map-id> <pr-id>...  — copy the blind maps into each skill-maps checkout
EV="$(cd "$(dirname "$0")" && pwd)"; mid=$1; shift
for pid in "$@"; do
  repo="$EV/runs/$pid/skill-maps/repo"
  for f in ARCHITECTURE.md REUSE_INDEX.md REVIEW_INDEX.md; do
    cp "$EV/maps/$mid/repo/$f" "$repo/$f" || exit 1
    grep -qx "/$f" "$repo/.git/info/exclude" || echo "/$f" >> "$repo/.git/info/exclude"
  done
  echo "$pid: maps from $mid installed; status: $(git -C "$repo" status --short | tr '\n' ' ')"
done
