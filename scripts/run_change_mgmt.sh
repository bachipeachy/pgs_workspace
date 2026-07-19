#!/usr/bin/env bash
# pgs_change — the single entry point for the change-management lifecycle.
#
# One executable, four lifecycle verbs. The user thinks in phases; stages (S1…S9) and compiler
# mechanics stay internal.
#
#   ./run_change_mgmt.sh author    --worker qwen --model qwen3.5:latest   # S1–S7 automated → CR-IR
#   ./run_change_mgmt.sh author    --guided --stage 1 --export            # S1–S7 guided (export/import)
#   ./run_change_mgmt.sh construct --projection <cr_ir> --domain blockchain --subdomain chain --persist <dir>
#   ./run_change_mgmt.sh validate  --dossier blockchain/chain             # → EXECUTION_VALIDATED
#   ./run_change_mgmt.sh promote   --dossier blockchain/chain --registry-root <path> [--from constructed] --confirm
#
# All verb flags pass straight through to `pgs_change`.
set -euo pipefail

WS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PGS_WORKSPACE="$WS_ROOT"

VENV_PY="$WS_ROOT/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "error: venv python not found at $VENV_PY — run ./bootstrap_pgs.sh first" >&2
  exit 1
fi

echo "PGS_WORKSPACE=$PGS_WORKSPACE"
exec "$VENV_PY" -m pgs_change_mgmt.engine.cli "$@"
