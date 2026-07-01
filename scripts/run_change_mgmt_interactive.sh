#!/usr/bin/env bash
# Guided Authoring Mode — export a governed Stage Package, then import a human/Claude-Code response.
#
# The third execution mode of the authoring trifecta: same validation / handoff / figure-of-merit as
# the automated dossier runner, only the transport differs (a human pastes a model's reply instead of
# an in-loop worker producing it). Export is pure governance (no model); import ingress-validates the
# pasted response at the human mutation boundary, then runs the engine for that one stage.
#
# Two phases per stage (worker-authored stages: 1 → 2 → 3 → 4 → 5 → 6 → 6b → 7):
#
#   # 1. EXPORT the Stage Package (stamps the live snapshot hash)
#   ./run_change_mgmt_interactive.sh --stage 1 --export
#      → open  <dossier>/_packages/stage_1/{system,user}_prompt.md  in a chat LLM
#      → ground each token in  stage_1/context/grounding_spec.json  via  `pi vocab search <TOKEN>`
#      → paste the model's full reply into  <dossier>/_packages/stage_1/response.md
#
#   # 2. IMPORT — ingress-validate the paste, then run the engine for the stage
#   ./run_change_mgmt_interactive.sh --stage 1 --import --model-label claude-code --diagnose
#
# Stage 8 (Build Sheet Set) is ASSEMBLED, not authored — project it with the automated runner
# (./run_change_mgmt_dossier.sh ... --stage 8), not this script.
#
# Any run_interactive flag passes through (--seed / --stage / --export / --import / --dir /
# --model-label / --quiet / --no-cache / --diagnose).
set -euo pipefail

WS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PGS_WORKSPACE="$WS_ROOT"

VENV_PY="$WS_ROOT/.venv/bin/python"
if [[ ! -x "$VENV_PY" ]]; then
  echo "error: venv python not found at $VENV_PY — run ./bootstrap_pgs.sh first" >&2
  exit 1
fi

echo "PGS_WORKSPACE=$PGS_WORKSPACE"
exec "$VENV_PY" -m pgs_change_mgmt.engine.run_interactive "$@"
