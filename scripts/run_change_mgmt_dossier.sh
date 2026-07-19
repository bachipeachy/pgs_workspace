#!/usr/bin/env bash
# Run the change-management dossier pipeline (Stages 1→7) for the seed CR.
#
# The pipeline ends at S7 (Authoring Mandate) — the last artifact derivable from the dossier alone.
# S8 (Authoring Manifest) is a POST-authoring artifact, produced by the authoring tier after the
# .md artifacts are created from the mandate, compiled, and tested (invoke with --stage 8).
#
# `--worker` and `--model` are REQUIRED (no default) — choose the model consciously.
#
# Usage:
#   ./run_change_dossier.sh --worker qwen   --model qwen3.5:latest
#   ./run_change_dossier.sh --worker qwen   --model qwen2.5-coder:32b --stages 1,2,3
#   ./run_change_dossier.sh --worker claude --model claude-opus-4-8    --stage 6b
#
# Any run_dossier flag passes through (--stage / --stages / --max-iters / --quiet / --no-cache / --seed).
set -euo pipefail

WS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PGS_WORKSPACE="$WS_ROOT"

VENV_PY="$WS_ROOT/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "error: venv python not found at $VENV_PY — run ./bootstrap_pgs.sh first" >&2
  exit 1
fi

echo "PGS_WORKSPACE=$PGS_WORKSPACE"
echo "DEPRECATED: use  ./run_change_mgmt.sh author $*  — forwarding ..." >&2
exec "$VENV_PY" -m pgs_change_mgmt.engine.cli author "$@"
