#!/usr/bin/env bash
# Wait for every GitHub Actions run of a commit, print one line per run,
# exit non-zero if any run failed. Run it inside the repo.
# Usage: ci-wait.sh [rev]   (default HEAD)
set -euo pipefail

sha=$(git rev-parse "${1:-HEAD}")
if [[ ! -d "$(git rev-parse --show-toplevel)/.github/workflows" ]]; then
  echo "no .github/workflows: nothing to wait for"
  exit 0
fi
ids=""
# Right after a push the run is not listed yet; watching an empty id 404s.
for _ in $(seq 1 30); do
  ids=$(gh run list --commit "$sha" --json databaseId -q '.[].databaseId')
  [[ -n "$ids" ]] && break
  sleep 4
done
if [[ -z "$ids" ]]; then
  echo "no CI run for ${sha:0:7} after 120s" >&2
  exit 2
fi

rc=0
for id in $ids; do
  gh run watch "$id" --exit-status >/dev/null 2>&1 || rc=1
  gh run view "$id" --json name,conclusion,url -q '"\(.name): \(.conclusion) \(.url)"'
done
exit "$rc"
