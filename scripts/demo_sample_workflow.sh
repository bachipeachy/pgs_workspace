#!/usr/bin/env bash
set -e

WS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DATA_ROOT="$WS_ROOT/data"
TRACE_ROOT="$WS_ROOT/traces"

PAYLOAD="$WS_ROOT/seeds/register_actor_unverified_payload.json"
HTTP_PORT=8000

source "$WS_ROOT/env.sh"

echo "======================================="
echo "PGS DEMO — Protocol-Governed Execution"
echo "======================================="

echo ""
echo "[1] Running workflow (Run #1)..."

OUT1=$(mktemp)

pgs_runtime run \
  --wf blockchain::WF_REGISTER_ACTOR_UNVERIFIED_V0 \
  --payload "$PAYLOAD" \
  --data-root "$DATA_ROOT" \
  --workspace "$WS_ROOT" | tee "$OUT1"

TRACE1=$(grep "Trace ID:" "$OUT1" | awk '{print $3}')

echo ""
echo "[2] Running workflow again (Run #2)..."

OUT2=$(mktemp)

pgs_runtime run \
  --wf blockchain::WF_REGISTER_ACTOR_UNVERIFIED_V0 \
  --payload "$PAYLOAD" \
  --data-root "$DATA_ROOT" \
  --workspace "$WS_ROOT" | tee "$OUT2"

TRACE2=$(grep "Trace ID:" "$OUT2" | awk '{print $3}')

TRACE2_PATH=$(find "$TRACE_ROOT" -name "$TRACE2.jsonl" 2>/dev/null | head -1)
if [ -n "$TRACE2_PATH" ] && pgs_runtime examine "$TRACE2_PATH"; then
  echo ""
else
  echo ""
  echo "[warn] Trace examiner unavailable"
fi

echo ""
echo "[3] HTTP Transport Demo..."
echo ""

HTTP_LOG=$(mktemp)

# Kill any stale server already occupying the port
if lsof -ti :"$HTTP_PORT" >/dev/null 2>&1; then
  lsof -ti :"$HTTP_PORT" | xargs kill 2>/dev/null || true
  sleep 0.5
fi

# Start HTTP server in background; trap ensures it is killed on script exit
"$WS_ROOT/scripts/start_http_server.sh" > "$HTTP_LOG" 2>&1 &
HTTP_PID=$!
trap "kill $HTTP_PID 2>/dev/null; wait $HTTP_PID 2>/dev/null" EXIT

# Poll until server is ready (max 5 seconds, 10 x 0.5s)
HTTP_READY=0
for i in $(seq 1 10); do
  if curl -s -o /dev/null "http://localhost:$HTTP_PORT/"; then
    HTTP_READY=1
    break
  fi
  sleep 0.5
done

if [[ $HTTP_READY -eq 0 ]]; then
  echo "[warn] HTTP server did not start — skipping HTTP demo"
  echo ""
  echo "Server log:"
  cat "$HTTP_LOG"
else
  # Open domain selector in browser
  open "http://localhost:$HTTP_PORT/" 2>/dev/null || true

  echo "  Live:  http://localhost:$HTTP_PORT/"
  echo ""
  echo "  Explore the thin client — workflows execute via TI-declared HTTP routes."
  echo "  Route /api/v0/register_actor is declared as a TI_ artifact in the snapshot,"
  echo "  not hardcoded in the server."
  echo ""
  read -rp "  Press Enter when done exploring to continue the demo... "

  echo ""
  echo "→ Executing via TI-declared HTTP route: POST /api/v0/register_actor"
  echo ""

  HTTP_RESPONSE=$(curl -s -X POST "http://localhost:$HTTP_PORT/api/v0/register_actor" \
    -H "Content-Type: application/json" \
    -d @"$PAYLOAD")

  echo "$HTTP_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$HTTP_RESPONSE"

  echo ""
  echo "  Same workflow. Same protocol. Different transport adapter."
fi

echo ""
echo "[4] Data state"

echo ""
echo "→ Actor Registry:"
cat "$DATA_ROOT/blockchain/identity/registry/actors.json"

echo ""
echo ""
echo "→ Event Stream (last 2 records):"
tail -n 2 "$DATA_ROOT/blockchain/identity/events/identity_events.jsonl"

echo ""
echo "[5] Interpretation"

echo "  - First run creates actor"
echo "  - Second run:"
echo "      • Registry enforces uniqueness"
echo "      • Event stream preserves history"
echo ""
echo "  → State is constrained. History is preserved."

echo ""
echo "[6] Key Observation"

echo "  You did not write execution code."
echo "  Behavior is governed by protocol + side-effect semantics."

echo ""
echo "======================================="
echo "END DEMO"
echo "======================================="
