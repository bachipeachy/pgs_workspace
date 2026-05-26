#!/usr/bin/env bash
# start_http_server.sh — Start the PGS HTTP gateway with all registered domains.
#
# Usage:
#   cd /Users/bp/pgs_workspace
#   source .venv/bin/activate
#   ./scripts/start_http_server.sh
#
# Optional overrides:
#   PORT=9000 ./scripts/start_http_server.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE="$(dirname "$SCRIPT_DIR")"
BASE_DIR="$(cd "$WORKSPACE/.." && pwd)"

PORT="${PORT:-8000}"
DATA_ROOT="${PGS_DATA_ROOT:-$WORKSPACE/data}"

BLOCKCHAIN_STATIC="$BASE_DIR/pgs_blockchain/pgs_blockchain/testbed/static"
AGENT_GOV_STATIC="$BASE_DIR/pgs_ai_governance/pgs_ai_governance/testbed/agent_governance/static"
COLLATZ_STATIC="$BASE_DIR/pgs_ai_governance/pgs_ai_governance/testbed/collatz_conjecture/static"

echo "PGS HTTP Gateway"
echo "  Workspace  : $WORKSPACE"
echo "  Data root  : $DATA_ROOT"
echo "  Port       : $PORT"
echo ""

python -m pgs_runtime.server \
  --port "$PORT" \
  --workspace "$WORKSPACE" \
  --data-root "$DATA_ROOT" \
  --domain "blockchain=$BLOCKCHAIN_STATIC" \
  --domain "agent_governance=$AGENT_GOV_STATIC" \
  --domain "collatz_conjecture=$COLLATZ_STATIC"
