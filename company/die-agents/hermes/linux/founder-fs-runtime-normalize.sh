#!/usr/bin/env bash
set -euo pipefail
# Service-user-safe normalizer for private runtime directories that may be
# recreated by Hermes/upstream dependencies. File contents remain owner-private.
for p in   /var/lib/die/hermes/income-operator/pending_messages   /var/lib/die/hermes/.local/state/tirith/sessions
do
  [[ -e "$p" ]] || continue
  owner="$(stat -c %U "$p")"; group="$(stat -c %G "$p")"
  [[ "$owner" == "die-hermes" && "$group" == "die-runtime" ]] || {
    echo "E_FA340_RUNTIME_OWNER:$p:$owner:$group" >&2
    exit 73
  }
  chmod 2750 "$p"
done
