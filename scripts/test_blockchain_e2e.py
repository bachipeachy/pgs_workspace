#!/usr/bin/env python3
"""
Blockchain E2E test orchestrator — BACHI TESTNET.

Seed files (source of truth):
  seeds/genesis_actor.json                              — Genesis Actor (pre-seeded)
  seeds/validator_population.json                       — 4 validator actors + BLS keys
  seeds/actor_population.json                           — 5 individual actors + wallet type declarations
  seeds/blockchain/orchestration/chain_simulation_config.json — simulation params + pre-expanded slot_schedule + tx_specs
  seeds/wallets.json                                    — system wallets (MINT/BURN/POOL) pre-seeded

Phases:
  0. Genesis    — register Genesis Actor (seeded; ALREADY_EXISTS expected)
  1a. Validators — register 4 validator actors (idempotent)
  1b. Validators — register validator records with discovered actor_ids (idempotent)
  2. Identity   — register 5 individual actors (idempotent)
  3. Wallets    — create PRIVATE + BUSINESS wallets per actor_population wallet_types (idempotent)
  4. Simulation — resolve tx_specs → tx_sequence; invoke WF_RUN_CHAIN_SIMULATION_V0 once
  5. Chain (BRIDGE HACK) — materialize the consensus BLOCKS store as the hash-linked `chain`
       module: first block → WF_BOOTSTRAP_GENESIS_CHAIN_V0, rest → WF_COMMIT_BLOCK_V0 (predecessor
       continuum). TEMPORARY driver. The target pipeline is
         actor → registration → wallet → transaction → mempool → blocks → attestation → finalization → chain
       (attestation + finalization not built yet); once those exist, block execution commits to the
       chain in the protocol topology and this bridge is deleted.

Usage:
  python3 scripts/test_blockchain_e2e.py              # idempotent setup + simulation
  python3 scripts/test_blockchain_e2e.py --clean      # wipe data/ first, then run
  python3 scripts/test_blockchain_e2e.py --no-delay   # pass tx_interval_seconds=0
  python3 scripts/test_blockchain_e2e.py --max-txs 1  # run only first N tx_specs (e.g. 1 for concurrency debug)
  python3 scripts/test_blockchain_e2e.py --max-slots 4 # run only first N slots
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
WS_ROOT      = SCRIPT_DIR.parent
DATA_ROOT    = WS_ROOT / "data"
SEEDS_DIR    = WS_ROOT / "seeds"
CLEAN_SCRIPT = Path.home() / "pgs" / "pgs_compiler" / "scripts" / "clean_outputs_dir.sh"

# Seed files
GENESIS_ACTOR_SEED    = SEEDS_DIR / "genesis_actor.json"
ACTOR_POPULATION      = SEEDS_DIR / "actor_population.json"
VALIDATOR_POPULATION  = SEEDS_DIR / "validator_population.json"
CHAIN_SIM_CONFIG      = SEEDS_DIR / "blockchain" / "orchestration" / "chain_simulation_config.json"

# Runtime state (written by WFs; read for ID resolution)
IDENTITY_EVENTS   = DATA_ROOT / "blockchain" / "identity" / "events" / "identity_events.jsonl"
WALLET_STATE      = DATA_ROOT / "blockchain" / "wallet" / "state" / "wallets.json"
SLOT_CLOCK_STATE  = DATA_ROOT / "blockchain" / "orchestration" / "state" / "slot_clock.json"
SIM_SUMMARY       = DATA_ROOT / "blockchain" / "orchestration" / "events" / "simulation_summary.jsonl"
BLOCKS_STATE      = DATA_ROOT / "blockchain" / "block" / "blocks" / "blocks.json"
BLOCK_EVENTS      = DATA_ROOT / "blockchain" / "block" / "events" / "block_events.jsonl"
MEMPOOL_STATE     = DATA_ROOT / "blockchain" / "mempool" / "state" / "mempool.json"
TX_EVENTS         = DATA_ROOT / "blockchain" / "transaction" / "events" / "transaction_events.jsonl"
CHAIN_STATE       = DATA_ROOT / "blockchain" / "chain" / "chain.jsonl"
CHAIN_HEAD        = DATA_ROOT / "blockchain" / "chain" / "chain_head.json"

# ── Protocol constants (from seeds) ───────────────────────────────────────────
GENESIS_ACTOR_ID = "A_7a77a0461083f938"
POOL_WALLET_ID   = "W_c97b4e66dc1d4a16"

# ── Terminal output ────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):      print(f"  {GREEN}✓  {msg}{RESET}")
def skip(msg):    print(f"  {YELLOW}→  {msg}{RESET}")
def fail(msg):    print(f"  {RED}✗  {msg}{RESET}")
def info(msg):    print(f"  {BOLD}   {msg}{RESET}")
def section(msg): print(f"\n{BOLD}{'─'*60}\n  {msg}\n{'─'*60}{RESET}")


# ── Runtime state readers ──────────────────────────────────────────────────────

def load_actor_lookup() -> dict:
    """
    Build email → actor_id from identity_events.jsonl.
    Reads EV_ACTOR_REGISTERED_UNVERIFIED_V0 events (JSONL, one record per line).
    """
    lookup = {}
    if not IDENTITY_EVENTS.exists():
        return lookup
    with open(IDENTITY_EVENTS) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            record = rec.get("record", {})
            if record.get("event_code") == "EV_ACTOR_REGISTERED_UNVERIFIED_V0":
                actor_id = record.get("actor_id")
                email = record.get("payload", {}).get("email_registration")
                if actor_id and email:
                    lookup[email] = actor_id
    return lookup


def load_wallet_lookup() -> dict:
    """
    Build (actor_id, wallet_type) → wallet_id from runtime wallets.json.
    """
    lookup = {}
    if not WALLET_STATE.exists():
        return lookup
    with open(WALLET_STATE) as f:
        wallets = json.load(f)
    for wallet in wallets.values():
        if not isinstance(wallet, dict):
            continue
        actor_id    = wallet.get("actor_id")
        wallet_type = wallet.get("wallet_type")
        wallet_id   = wallet.get("wallet_id")
        if actor_id and wallet_type and wallet_id:
            lookup[(actor_id, wallet_type.upper())] = wallet_id
    return lookup


# ── Seed loaders ───────────────────────────────────────────────────────────────

def load_genesis_actor() -> dict:
    with open(GENESIS_ACTOR_SEED) as f:
        ga = json.load(f)
    return {
        "first_name":         ga["first_name"],
        "last_name":          ga["last_name"],
        "email_registration": ga["email_registration"],
    }


def load_actor_population() -> list:
    with open(ACTOR_POPULATION) as f:
        return json.load(f)


def load_validator_population() -> list:
    with open(VALIDATOR_POPULATION) as f:
        return json.load(f)


def load_chain_sim_config() -> dict:
    with open(CHAIN_SIM_CONFIG) as f:
        return json.load(f)


def build_actor_records_by_email(actor_pop, validator_pop, genesis) -> dict:
    """email → {first_name, last_name, email_registration}"""
    records = {}
    for a in actor_pop:
        records[a["email_registration"]] = {
            "first_name":         a["first_name"],
            "last_name":          a["last_name"],
            "email_registration": a["email_registration"],
        }
    for v in validator_pop:
        ar = v["actor_record"]
        records[ar["email_registration"]] = {
            "first_name":         ar["first_name"],
            "last_name":          ar["last_name"],
            "email_registration": ar["email_registration"],
        }
    records[genesis["email_registration"]] = genesis
    return records


# ── TX spec resolver ───────────────────────────────────────────────────────────

def resolve_tx(spec_tx: dict, actor_lookup: dict, wallet_lookup: dict,
               actor_records: dict) -> dict:
    """
    Resolve a tx spec (email + wallet_type references) to a concrete WF tx payload.
    Raises RuntimeError if any reference cannot be resolved.
    """
    tx_type = spec_tx["tx_type"]
    G = GENESIS_ACTOR_ID

    def wid(email: str, wtype: str) -> str:
        actor_id = actor_lookup.get(email)
        if not actor_id:
            raise RuntimeError(f"Actor not registered: {email}")
        key = (actor_id, wtype)
        if key not in wallet_lookup:
            raise RuntimeError(f"Wallet not found: {email} / {wtype} (actor_id={actor_id})")
        return wallet_lookup[key]

    def ar(email: str) -> dict:
        if email not in actor_records:
            raise RuntimeError(f"Actor record not found: {email}")
        return actor_records[email]

    if tx_type == "MINT":
        return {
            "tx_type":      "MINT",
            "to_wallet_id": wid(spec_tx["to_actor_email"], spec_tx["to_wallet_type"]),
            "amount":       spec_tx["amount"],
            "triggered_by": G,
        }

    elif tx_type == "POOL":
        return {
            "tx_type":       "POOL",
            "pool_wallet_id": POOL_WALLET_ID,
            "amount":         spec_tx["amount"],
            "triggered_by":   G,
        }

    elif tx_type == "REWARD":
        return {
            "tx_type":      "REWARD",
            "to_wallet_id":  wid(spec_tx["to_actor_email"], spec_tx["to_wallet_type"]),
            "amount":        spec_tx["amount"],
            "block_hash":    spec_tx.get("block_hash", "0x" + "0" * 63 + "a"),
            "triggered_by":  G,
        }

    elif tx_type == "SLASH":
        return {
            "tx_type":        "SLASH",
            "from_wallet_id":  wid(spec_tx["from_actor_email"], spec_tx["from_wallet_type"]),
            "validator_index": spec_tx.get("validator_index", 0),
            "amount":          spec_tx["amount"],
            "triggered_by":    G,
        }

    elif tx_type == "TRANSFER":
        return {
            "tx_type":       "TRANSFER",
            "actor_record":   ar(spec_tx["actor_email"]),
            "from_wallet_id": wid(spec_tx["from_actor_email"], spec_tx["from_wallet_type"]),
            "to_address":     wid(spec_tx["to_actor_email"],   spec_tx["to_wallet_type"]),
            "amount":         spec_tx["amount"],
        }

    elif tx_type == "BURN":
        return {
            "tx_type":       "BURN",
            "from_wallet_id": wid(spec_tx["from_actor_email"], spec_tx["from_wallet_type"]),
            "amount":         spec_tx["amount"],
            "triggered_by":   G,
        }

    elif tx_type == "STAKE":
        return {
            "tx_type":       "STAKE",
            "actor_record":   ar(spec_tx["actor_email"]),
            "from_wallet_id": wid(spec_tx["from_actor_email"], spec_tx["from_wallet_type"]),
            "amount":         spec_tx["amount"],
        }

    elif tx_type == "UNSTAKE":
        return {
            "tx_type":        "UNSTAKE",
            "actor_record":    ar(spec_tx["actor_email"]),
            "validator_index": spec_tx.get("validator_index", 0),
            "amount":          spec_tx["amount"],
            "to_wallet_id":    wid(spec_tx["to_actor_email"], spec_tx["to_wallet_type"]),
        }

    else:
        raise RuntimeError(f"Unknown tx_type in tx_spec: {tx_type!r}")


# ── Runtime invocation ─────────────────────────────────────────────────────────

def run_wf(wf_fqdn: str, payload: dict, *, behavior_logic: bool = False) -> tuple[str, str]:
    """
    Invoke `pgs_runtime run` with a payload dict.
    Returns (status, full_output).
    """
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, dir="/tmp"
    ) as f:
        json.dump(payload, f)
        payload_path = f.name

    cmd = [
        "pgs_runtime", "run",
        "--wf",        wf_fqdn,
        "--payload",   payload_path,
        "--data-root", str(DATA_ROOT),
        "--workspace", str(WS_ROOT),
    ]
    if behavior_logic:
        cmd.append("--behavior-logic")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout + result.stderr
        for line in output.splitlines():
            stripped = line.strip()
            if stripped.startswith("Status:"):
                status = stripped.split("Status:", 1)[-1].strip()
                return status, output
        return "ERROR", output
    finally:
        os.unlink(payload_path)


# ── Phase runner ───────────────────────────────────────────────────────────────

def run_phase(
    phase_label: str,
    steps: list[tuple[str, str, dict]],
    *,
    skip_on: tuple[str, ...] = ("ALREADY_EXISTS",),
    fail_on: tuple[str, ...] = ("VIOLATION", "ERROR"),
    behavior_logic: bool = False,
) -> int:
    """
    Execute a list of (label, wf_fqdn, payload) steps.
    Returns number of failures.
    """
    section(phase_label)
    failures = 0

    for label, wf_fqdn, payload in steps:
        status, output = run_wf(wf_fqdn, payload, behavior_logic=behavior_logic)

        if status == "SUCCESS":
            ok(label)
        elif status in skip_on:
            skip(f"{label}  [{status}]")
        elif status in fail_on:
            fail(f"{label}  [{status}]")
            tail = output.strip().splitlines()
            for line in tail[-6:]:
                print(f"       {line}")
            failures += 1
        else:
            fail(f"{label}  [unexpected status: {status}]")
            failures += 1

    return failures


# ── Entry point ────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Blockchain E2E test orchestrator — BACHI TESTNET"
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Wipe data/ and traces/ via clean_outputs_dir.sh before running",
    )
    parser.add_argument(
        "--no-delay",
        action="store_true",
        help="Override tx_interval_seconds to 0 (skip inter-TX delay)",
    )
    parser.add_argument(
        "--behavior-logic",
        action="store_true",
        dest="behavior_logic",
        help="Render execution-path PNG after each workflow run (requires graphviz)",
    )
    parser.add_argument(
        "--max-txs",
        type=int,
        default=None,
        metavar="N",
        dest="max_txs",
        help="Limit tx_sequence to first N tx_specs from config (default: all)",
    )
    parser.add_argument(
        "--max-slots",
        type=int,
        default=None,
        metavar="N",
        dest="max_slots",
        help="Limit slot_schedule to first N slots from config (default: all)",
    )
    args = parser.parse_args()
    bl = args.behavior_logic

    print(f"\n{BOLD}{'='*60}")
    print("  Blockchain E2E — BACHI TESTNET")
    print(f"{'='*60}{RESET}")
    print(f"  Workspace   : {WS_ROOT}")
    print(f"  Data root   : {DATA_ROOT}")
    if bl:
        print(f"  Behavior    : --behavior-logic (PNG render per run)")

    # ── Optional clean ─────────────────────────────────────────────────────────
    if args.clean:
        print(f"\n{BOLD}[clean]{RESET} {CLEAN_SCRIPT.name} ...")
        result = subprocess.run(["bash", str(CLEAN_SCRIPT)])
        if result.returncode != 0:
            print(f"{RED}[clean] FAILED — aborting.{RESET}")
            sys.exit(1)

    # ── Load seeds ─────────────────────────────────────────────────────────────
    genesis_actor    = load_genesis_actor()
    actor_pop        = load_actor_population()
    validator_pop    = load_validator_population()
    sim_config       = load_chain_sim_config()
    actor_records    = build_actor_records_by_email(actor_pop, validator_pop, genesis_actor)

    total_failures = 0

    # ── Phase 0: Genesis Actor ─────────────────────────────────────────────────
    total_failures += run_phase(
        "Phase 0 — Genesis Actor Bootstrap",
        [(
            f"{genesis_actor['first_name']} {genesis_actor['last_name']}"
            f" <{genesis_actor['email_registration']}>",
            "blockchain::WF_REGISTER_ACTOR_UNVERIFIED_V0",
            {"actor_record": genesis_actor},
        )],
        behavior_logic=bl,
    )

    # ── Phase 1a: Register validator actors ────────────────────────────────────
    validator_actor_steps = [
        (
            f"{v['actor_record']['first_name']} {v['actor_record']['last_name']}"
            f" <{v['actor_record']['email_registration']}>",
            "blockchain::WF_REGISTER_ACTOR_UNVERIFIED_V0",
            {"actor_record": v["actor_record"]},
        )
        for v in validator_pop
    ]
    total_failures += run_phase(
        "Phase 1a — Validator Actors: Register",
        validator_actor_steps,
        behavior_logic=bl,
    )

    # ── Phase 1b: Register validator records (requires actor_ids) ──────────────
    actor_lookup = load_actor_lookup()
    validator_steps = []
    for vdata in validator_pop:
        email    = vdata["actor_record"]["email_registration"]
        name     = f"{vdata['actor_record']['first_name']} {vdata['actor_record']['last_name']}"
        actor_id = actor_lookup.get(email)
        if not actor_id:
            fail(f"actor_id not found for {email} — cannot register validator record")
            total_failures += 1
            continue
        validator_steps.append((
            f"{name} (validator record, actor_id={actor_id})",
            "blockchain::WF_REGISTER_VALIDATOR_V0",
            {
                "validator_record": {
                    "actor_id":                      actor_id,
                    "pubkey":                         vdata["pubkey"],
                    "withdrawal_credentials":         vdata["withdrawal_credentials"],
                    "status":                         "PENDING_INITIALIZED",
                    "slashed":                        False,
                    "effective_balance":              vdata["effective_balance"],
                    "balance":                        vdata["balance"],
                    "activation_eligibility_epoch":   None,
                    "activation_epoch":               None,
                    "exit_epoch":                     None,
                    "withdrawable_epoch":             None,
                }
            },
        ))
    total_failures += run_phase(
        "Phase 1b — Validators: Register Records",
        validator_steps,
        behavior_logic=bl,
    )

    # ── Phase 2: Register individual actors ────────────────────────────────────
    individual_steps = [
        (
            f"{a['first_name']} {a['last_name']} <{a['email_registration']}>",
            "blockchain::WF_REGISTER_ACTOR_UNVERIFIED_V0",
            {"actor_record": {
                "first_name":         a["first_name"],
                "last_name":          a["last_name"],
                "email_registration": a["email_registration"],
            }},
        )
        for a in actor_pop
    ]
    total_failures += run_phase(
        "Phase 2 — Identity: Register Individual Actors",
        individual_steps,
        behavior_logic=bl,
    )

    # ── Phase 3: Create actor wallets ──────────────────────────────────────────
    wallet_steps = []
    for a in actor_pop:
        for wtype in a.get("wallet_types", []):
            wallet_steps.append((
                f"{a['first_name']} {a['last_name']} — {wtype} wallet",
                "blockchain::WF_CREATE_WALLET_V0",
                {
                    "actor_record": {
                        "first_name":         a["first_name"],
                        "last_name":          a["last_name"],
                        "email_registration": a["email_registration"],
                    },
                    "wallet_type": wtype,
                },
            ))
    total_failures += run_phase(
        "Phase 3 — Wallets: Create Actor Wallets",
        wallet_steps,
        behavior_logic=bl,
    )

    # ── Phase 4: Chain Simulation — single WF_RUN_CHAIN_SIMULATION_V0 invocation
    section("Phase 4 — Chain Simulation: WF_RUN_CHAIN_SIMULATION_V0")

    # Refresh lookups after Phase 2–3
    actor_lookup  = load_actor_lookup()
    wallet_lookup = load_wallet_lookup()

    # Resolve tx_specs → tx_sequence with concrete wallet IDs
    tx_specs = sim_config.get("tx_specs", [])
    tx_sequence = []
    resolution_failures = 0
    for idx, spec in enumerate(tx_specs):
        try:
            tx_sequence.append(resolve_tx(spec, actor_lookup, wallet_lookup, actor_records))
        except RuntimeError as exc:
            fail(f"tx_spec[{idx}] [{spec.get('tx_type', '?')}] — resolution error: {exc}")
            resolution_failures += 1

    if resolution_failures > 0:
        total_failures += resolution_failures
        info(f"Aborting simulation — {resolution_failures} tx_spec(s) could not be resolved")
    else:
        # Apply --max-txs / --max-slots overrides (slice from full config)
        slot_schedule = sim_config["slot_schedule"]
        if args.max_slots is not None:
            slot_schedule = slot_schedule[:args.max_slots]

        if args.max_txs is not None:
            tx_sequence = tx_sequence[:args.max_txs]

        tx_interval = 0 if args.no_delay else sim_config.get("tx_interval_seconds", 2)

        wf_payload = {
            "simulation_id":         sim_config["simulation_id"],
            "slot_duration_seconds": sim_config["slot_duration_seconds"],
            "max_slots":             len(slot_schedule),
            "tx_interval_seconds":   tx_interval,
            "max_transactions":      len(tx_sequence),
            "slot_schedule":         slot_schedule,
            "tx_sequence":           tx_sequence,
            "triggered_by":          sim_config["triggered_by"],
        }

        info(f"simulation_id    : {sim_config['simulation_id']}")
        info(f"slot_schedule    : {len(slot_schedule)} slots" +
             (f"  (--max-slots {args.max_slots})" if args.max_slots is not None else ""))
        info(f"tx_sequence      : {len(tx_sequence)} transactions" +
             (f"  (--max-txs {args.max_txs})" if args.max_txs is not None else ""))
        info(f"tx_interval_s    : {tx_interval}s" + ("  (--no-delay)" if args.no_delay else ""))

        status, output = run_wf(
            "blockchain::WF_RUN_CHAIN_SIMULATION_V0", wf_payload, behavior_logic=bl
        )

        if status == "SUCCESS":
            ok(f"WF_RUN_CHAIN_SIMULATION_V0  [{sim_config['simulation_id']}]")
        elif status == "PARTIAL_FAILURE":
            skip(f"WF_RUN_CHAIN_SIMULATION_V0  [{sim_config['simulation_id']}]  [PARTIAL_FAILURE — summary recorded]")
            total_failures += 1
        else:
            fail(f"WF_RUN_CHAIN_SIMULATION_V0  [{sim_config['simulation_id']}]  [{status}]")
            tail = output.strip().splitlines()
            for line in tail[-8:]:
                print(f"       {line}")
            total_failures += 1

        _print_simulation_diagnostics(sim_config["simulation_id"], slot_schedule)

    # ── Phase 5: Chain bridge — materialize consensus blocks as the hash-linked chain ──────────
    total_failures += run_chain_bridge(behavior_logic=bl)

    # ── Summary ────────────────────────────────────────────────────────────────
    print(f"\n{BOLD}{'='*60}{RESET}")
    if total_failures == 0:
        print(f"  {GREEN}{BOLD}ALL PASSED{RESET}")
    else:
        print(f"  {RED}{BOLD}{total_failures} FAILURE(S) — see output above{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")

    sys.exit(0 if total_failures == 0 else 1)


def _print_simulation_diagnostics(sim_id: str, slot_schedule: list) -> None:
    """Print slot-by-slot execution status and mempool drain summary."""
    section("Simulation Diagnostics")

    # ── Slot clock ────────────────────────────────────────────────────────────
    current_slot = 0
    if SLOT_CLOCK_STATE.exists():
        try:
            with open(SLOT_CLOCK_STATE) as f:
                clock = json.load(f)
            raw_cs = clock.get(sim_id, {}).get("current_slot", 0)
            current_slot = int(raw_cs) if isinstance(raw_cs, (int, float)) else 0
        except Exception:
            pass

    # ── Derive slots_executed from simulation summary (authoritative) ─────────
    # Detect worker type by output field presence — not by numeric code (codes shift
    # when new CCs are compiled into the snapshot and numeric assignments change).
    slots_executed = 0
    if SIM_SUMMARY.exists():
        try:
            with open(SIM_SUMMARY) as f:
                for raw_line in f:
                    raw_line = raw_line.strip()
                    if not raw_line:
                        continue
                    rec = json.loads(raw_line)
                    record = rec.get("record", {})
                    if record.get("simulation_id") != sim_id:
                        continue
                    for w in record.get("worker_results", []):
                        outputs = w.get("outputs", {})
                        if "slots_executed" in outputs:
                            slots_executed = int(outputs.get("slots_executed", 0))
        except Exception:
            pass

    # Use slots_executed as the authoritative count (slot_clock may store template string)
    effective_slot = max(current_slot, slots_executed)
    info(f"Slot clock  — slots_executed: {slots_executed} / {len(slot_schedule)} scheduled")

    # ── Worker results ────────────────────────────────────────────────────────
    if SIM_SUMMARY.exists():
        try:
            with open(SIM_SUMMARY) as f:
                for raw_line in f:
                    raw_line = raw_line.strip()
                    if not raw_line:
                        continue
                    rec = json.loads(raw_line)
                    record = rec.get("record", {})
                    sim_outcome = record.get("simulation_outcome", "?")
                    workers = record.get("worker_results", [])
                    if record.get("simulation_id") != sim_id:
                        continue
                    label = (GREEN + "SUCCESS" + RESET if sim_outcome == "SUCCESS"
                             else YELLOW + sim_outcome + RESET if sim_outcome == "PARTIAL_FAILURE"
                             else RED + sim_outcome + RESET)
                    info(f"Outcome     — {label}")
                    for w in workers:
                        wstatus = w.get("result_status", "?")
                        outputs = w.get("outputs", {})
                        wlabel = GREEN + "OK" + RESET if wstatus == "SUCCESS" else RED + wstatus + RESET
                        if "slots_executed" in outputs:
                            info(f"  Slot worker [{wlabel}] — slots_executed: {outputs.get('slots_executed', 0)}")
                        elif "tx_submitted" in outputs:
                            info(f"  TX worker   [{wlabel}] — tx_submitted: {outputs.get('tx_submitted', 0)}")
        except Exception as e:
            info(f"  (simulation summary unreadable: {e})")

    # ── Slot-by-slot from block events ────────────────────────────────────────
    # Index block events by slot number
    slot_blocks: dict = {}
    if BLOCK_EVENTS.exists():
        try:
            with open(BLOCK_EVENTS) as f:
                for raw_line in f:
                    raw_line = raw_line.strip()
                    if not raw_line:
                        continue
                    ev = json.loads(raw_line)
                    record = ev.get("record", {})
                    slot_n = record.get("slot")
                    if slot_n is not None:
                        slot_blocks[slot_n] = record
        except Exception:
            pass

    # Load block state for tx counts
    blocks_state: dict = {}
    if BLOCKS_STATE.exists():
        try:
            with open(BLOCKS_STATE) as f:
                blocks_state = json.load(f)
        except Exception:
            pass

    print(f"\n  {'Slot':>5}  {'Status':<12}  {'Block ID':<22}  {'Txs':<5}  {'Proposer'}")
    print(f"  {'─'*5}  {'─'*12}  {'─'*22}  {'─'*5}  {'─'*20}")
    for entry in slot_schedule:
        slot_num = entry.get("slot_number", "?")
        ev = slot_blocks.get(slot_num)
        if ev:
            block_id = ev.get("block_id", "?")
            block_id_short = (block_id[:20] + "…") if len(str(block_id)) > 21 else block_id
            block_rec = blocks_state.get(block_id, {})
            tx_ids = block_rec.get("tx_ids", ev.get("tx_ids", []))
            tx_count = len(tx_ids) if isinstance(tx_ids, list) else 0
            proposer = ev.get("proposer_id", "?")
            if isinstance(proposer, str) and len(proposer) > 20:
                proposer = proposer[:18] + "…"
            print(f"  {slot_num:>5}  {GREEN}EXECUTED    {RESET}  {block_id_short:<22}  {tx_count:<5}  {proposer}")
        elif isinstance(slot_num, int) and slot_num <= current_slot:
            print(f"  {slot_num:>5}  {YELLOW}NO_BLOCK    {RESET}  (slot passed but no block event)")
        else:
            print(f"  {slot_num:>5}  {RED}PENDING     {RESET}")

    # ── Mempool ─────────────────────────────────────────────────────────────
    # Drained txs are deleted from the mempool store (not marked CONFIRMED),
    # so confirmed count comes from block events (tx_ids in formed blocks).
    confirmed_in_blocks = sum(
        len(rec.get("tx_ids", []))
        for rec in slot_blocks.values()
        if isinstance(rec.get("tx_ids"), list)
    )
    if MEMPOOL_STATE.exists():
        try:
            with open(MEMPOOL_STATE) as f:
                mempool = json.load(f)
            txs = mempool.get("transactions", {})
            pending = sum(1 for tx in txs.values() if tx.get("status") == "PENDING")
            claimed = sum(1 for tx in txs.values() if tx.get("status") == "CLAIMED")
            total_mp = len(txs)
            info(f"\nMempool     — total: {total_mp}  pending: {pending}  claimed: {claimed}  confirmed_in_blocks: {confirmed_in_blocks}")
        except Exception as e:
            info(f"  (mempool unreadable: {e})")
    print()


def run_chain_bridge(behavior_logic: bool = False) -> int:
    """Phase 5 (BRIDGE HACK) — materialize the consensus BLOCKS store as the hash-linked `chain`.

    TEMPORARY driver: read the blocks the PoS simulation produced (BLOCKS store), resolve each
    block's tx_ids to transaction content, and commit them to the `chain` module in slot order —
    first block → genesis, the rest → predecessor-linked commits. This stands in for the eventual
    protocol path (blocks → attestation → finalization → chain); once attestors/finalizers exist,
    block execution commits to the chain in the topology and this function is deleted.
    """
    section("Phase 5 — Chain: materialize consensus blocks (BRIDGE HACK → future protocol)")
    if not BLOCKS_STATE.exists():
        skip("no BLOCKS store — run the simulation (Phase 4) first")
        return 0
    raw = json.load(open(BLOCKS_STATE))
    blocks = sorted((raw.values() if isinstance(raw, dict) else raw), key=lambda b: b.get("slot", 0))
    if not blocks:
        skip("BLOCKS store empty — nothing to materialize")
        return 0

    # tx_id → payload (resolve each block's tx_ids to transaction content)
    txmap: dict = {}
    if TX_EVENTS.exists():
        with open(TX_EVENTS) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sid, payload = r.get("stream_id"), r.get("record", {}).get("payload")
                if sid and payload:
                    txmap[sid] = payload

    def resolve(b) -> list:
        return [{"tx_type":   txmap.get(t, {}).get("tx_type", "TRANSFER"),
                 "amount":     txmap.get(t, {}).get("amount", 0),
                 "from_wallet": txmap.get(t, {}).get("from_wallet_id"),
                 "to_wallet":   txmap.get(t, {}).get("to_wallet_id")}
                for t in b.get("tx_ids", [])]

    # start a fresh chain from this run's blocks
    CHAIN_STATE.unlink(missing_ok=True)
    CHAIN_HEAD.unlink(missing_ok=True)

    failures, committed = 0, 0
    g = blocks[0]
    status, output = run_wf(
        "blockchain::WF_BOOTSTRAP_GENESIS_CHAIN_V0",
        {"genesis_block_content": {"predecessor_hash": "0x" + "0"*64, "height": 0,
                                   "transactions": resolve(g)}},
        behavior_logic=behavior_logic)
    if status == "SUCCESS":
        ok(f"slot {g.get('slot')}  {g.get('block_id')}  → genesis")
        committed = 1
    else:
        fail(f"slot {g.get('slot')}  {g.get('block_id')}  → genesis  [{status}]")
        for line in output.strip().splitlines()[-6:]:
            print(f"       {line}")
        return 1

    for h, b in enumerate(blocks[1:], start=1):
        if not CHAIN_HEAD.exists():
            fail("chain head missing — cannot continue"); failures += 1; break
        head = json.load(open(CHAIN_HEAD))["head"]
        status, output = run_wf(
            "blockchain::WF_COMMIT_BLOCK_V0",
            {"proposed_block": {"predecessor_hash": head, "height": h, "transactions": resolve(b)}},
            behavior_logic=behavior_logic)
        if status == "SUCCESS":
            ok(f"slot {b.get('slot')}  {b.get('block_id')}  → commit h{h}")
            committed += 1
        else:
            fail(f"slot {b.get('slot')}  {b.get('block_id')}  → commit h{h}  [{status}]")
            for line in output.strip().splitlines()[-6:]:
                print(f"       {line}")
            failures += 1
            break

    # render the materialized chain
    recs = ([json.loads(l)["record"] for l in CHAIN_STATE.read_text().splitlines()]
            if CHAIN_STATE.exists() else [])
    print(f"\n  {'h':>2}  {'predecessor':<14}  {'slot':>4}  {'block_id':<20}  {'tx':>2}  Proposer")
    print(f"  {'─'*2}  {'─'*14}  {'─'*4}  {'─'*20}  {'─'*2}  {'─'*20}")
    for cb, rec in zip(blocks, recs):
        prop = cb.get("proposer_id", "?")
        if isinstance(prop, str) and len(prop) > 20:
            prop = prop[:18] + "…"
        print(f"  {rec['height']:>2}  {rec['predecessor_hash'][:12]}…  {cb.get('slot','?'):>4}  "
              f"{str(cb.get('block_id','?')):<20}  {len(rec['transactions']):>2}  {prop}")
    info(f"\n{committed}/{len(blocks)} consensus blocks committed to the chain (BRIDGE — future protocol)")
    return failures


if __name__ == "__main__":
    main()
