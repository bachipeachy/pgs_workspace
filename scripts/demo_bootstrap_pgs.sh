#!/usr/bin/env bash
# EXTERNAL FEDERATED DEMO BOOTSTRAP
# Uses PyPI omnibachi + federated source repos

set -e

echo "======================================="
echo "PGS Workspace Bootstrap"
echo "======================================="

# --------------------------------------------------
# Resolve paths
# --------------------------------------------------

WS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_DIR="$(cd "$WS_ROOT/.." && pwd)"

echo "[info] Workspace: $WS_ROOT"
echo "[info] Base dir:  $BASE_DIR"

cd "$WS_ROOT"

# --------------------------------------------------
# Create virtual environment
# --------------------------------------------------

echo ""
echo "[1/9] Creating virtual environment..."

python3 -m venv .venv
source .venv/bin/activate

# --------------------------------------------------
# Upgrade tooling
# --------------------------------------------------

echo ""
echo "[2/9] Upgrading pip..."

pip install --upgrade pip

# --------------------------------------------------
# Install stable runtime substrate
# --------------------------------------------------

echo ""
echo "[3/9] Installing omnibachi from PyPI..."

pip install omnibachi

# --------------------------------------------------
# Install federated repos as editable installs
# --------------------------------------------------

echo ""
echo "[4/9] Installing federated repos (editable)..."

install_repo () {
  local repo_name=$1
  local repo_path="$BASE_DIR/$repo_name"

  if [ ! -d "$repo_path" ]; then
    echo ""
    echo "[ERROR] Missing repo: $repo_path"
    exit 1
  fi

  echo "  [install] $repo_name"
  pip install -e "$repo_path"
}

install_repo "pgs_governance"
install_repo "pgs_compiler"
install_repo "pgs_transport"
install_repo "pgs_capabilities"
install_repo "pgs_blockchain"
install_repo "pgs_ai_governance"

# --------------------------------------------------
# Generate environment activation helper
# --------------------------------------------------

echo ""
echo "[5/9] Generating environment activation helper..."

cat > "$WS_ROOT/env.sh" <<EOF
#!/usr/bin/env bash

export PGS_WORKSPACE="$WS_ROOT"
export PGS_DATA_ROOT="$WS_ROOT/data"

source "$WS_ROOT/.venv/bin/activate"
EOF

chmod +x "$WS_ROOT/env.sh"

# --------------------------------------------------
# Create standard workspace dirs + seed data
# --------------------------------------------------

echo ""
echo "[6/9] Creating workspace directories and installing seed data..."

mkdir -p "$WS_ROOT/data"
mkdir -p "$WS_ROOT/traces"
mkdir -p "$WS_ROOT/protocol_snapshot"

mkdir -p "$WS_ROOT/data/ai_governance/ai_licensing"
cp "$WS_ROOT/seeds/license_facts.json" "$WS_ROOT/data/ai_governance/ai_licensing/license_facts.json"
echo "  [seed] license_facts.json -> data/ai_governance/ai_licensing/"

# --------------------------------------------------
# Compile protocol artifacts (Phase A then Phase B)
# --------------------------------------------------

echo ""
echo "[7/9] Compiling protocol artifacts..."

cd "$BASE_DIR/pgs_compiler"

echo "  [Phase A] STRUCTURE_BUILD_PLATFORM_CONFIG_V0"
python -m pgs_compiler.compiler.cli --structure STRUCTURE_BUILD_PLATFORM_CONFIG_V0

echo "  [Phase A] STRUCTURE_BUILD_BLOCKCHAIN_CONFIG_V0"
python -m pgs_compiler.compiler.cli --structure STRUCTURE_BUILD_BLOCKCHAIN_CONFIG_V0

echo "  [Phase A] STRUCTURE_BUILD_AI_GOVERNANCE_CONFIG_V0"
python -m pgs_compiler.compiler.cli --structure STRUCTURE_BUILD_AI_GOVERNANCE_CONFIG_V0

echo "  [Phase B] STRUCTURE_BUILD_VOCABULARY_AGGREGATE_V0"
python -m pgs_compiler.compiler.cli --structure STRUCTURE_BUILD_VOCABULARY_AGGREGATE_V0

cd "$WS_ROOT"

# --------------------------------------------------
# Build and validate snapshot
# --------------------------------------------------

echo ""
echo "[8/9] Building and validating snapshot..."

python "$BASE_DIR/pgs_compiler/scripts/pgs_build.py" --workspace "$WS_ROOT"

# --------------------------------------------------
# Activate environment
# --------------------------------------------------

echo ""
echo "[9/9] Activating environment..."

source "$WS_ROOT/env.sh"

echo ""
echo "---------------------------------------"
echo "PGS Federated Demo Environment Ready"
echo "---------------------------------------"

echo ""
echo "Run runtime help:"
echo "  omnibachi run --help"

echo ""
echo "Run demo:"
echo "  ./scripts/demo_sample_workflow.sh"

echo ""



