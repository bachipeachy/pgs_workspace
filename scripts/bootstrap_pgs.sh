#!/usr/bin/env bash
# PGS WORKSPACE BOOTSTRAP
# Usage:
#   ./bootstrap_pgs.sh                 # default: --env local
#   ./bootstrap_pgs.sh --env local     # all packages from local editable source
#   ./bootstrap_pgs.sh --env remote    # published packages (pgs_runtime, pgs_compiler, ...) from PyPI

set -e

# --------------------------------------------------
# Parse arguments
# --------------------------------------------------

PGS_ENV="local"

while [[ $# -gt 0 ]]; do
  case $1 in
    --env)
      PGS_ENV="$2"
      shift 2
      ;;
    *)
      echo "[ERROR] Unknown flag: $1"
      echo "Usage: $0 [--env local|remote]"
      exit 1
      ;;
  esac
done

if [[ "$PGS_ENV" != "local" && "$PGS_ENV" != "remote" ]]; then
  echo "[ERROR] --env must be 'local' or 'remote', got: $PGS_ENV"
  exit 1
fi

echo "======================================="
echo "PGS Workspace Bootstrap"
echo "  env: $PGS_ENV"
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
# Wipe all .venv directories across all eight repos
# --------------------------------------------------

echo ""
echo "[1/9] Removing stale .venv directories across all repos..."

for repo in pgs_runtime pgs_governance pgs_compiler pgs_transport pgs_capabilities pgs_blockchain pgs_ai_governance pgs_workspace; do
  venv_path="$BASE_DIR/$repo/.venv"
  if [ -d "$venv_path" ]; then
    echo "  [rm] $venv_path"
    rm -rf "$venv_path"
  else
    echo "  [skip] $repo — no .venv"
  fi
done

# --------------------------------------------------
# Create virtual environment
# --------------------------------------------------

echo ""
echo "[2/9] Creating virtual environment in pgs_workspace..."

python3.12 -m venv .venv
source .venv/bin/activate

# --------------------------------------------------
# Upgrade tooling
# --------------------------------------------------

echo ""
echo "[3/9] Upgrading pip..."

pip install --upgrade pip

# --------------------------------------------------
# Repo installer helper
# --------------------------------------------------

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

# --------------------------------------------------
# Install runtime substrate
# --------------------------------------------------

echo ""
if [ "$PGS_ENV" = "local" ]; then
  echo "[4/9] Installing pgs_runtime from local source..."
  install_repo "pgs_runtime"
else
  echo "[4/9] Installing pgs_runtime from PyPI..."
  pip install pgs_runtime
fi

# --------------------------------------------------
# Install governance + compiler
# --------------------------------------------------

echo ""
echo "[5/9] Installing governance + compiler..."

install_repo "pgs_governance"
install_repo "pgs_compiler"

# --------------------------------------------------
# Install transport + capabilities
# --------------------------------------------------

echo ""
echo "[6/9] Installing transport + capabilities..."

install_repo "pgs_transport"
install_repo "pgs_capabilities"

# --------------------------------------------------
# Install domains
# --------------------------------------------------

echo ""
echo "[7/9] Installing domains..."

install_repo "pgs_blockchain"
install_repo "pgs_ai_governance"

# --------------------------------------------------
# Generate environment activation helper
# --------------------------------------------------

echo ""
echo "[8/9] Generating environment activation helper..."

cat > "$WS_ROOT/env.sh" <<EOF
#!/usr/bin/env bash

export PGS_WORKSPACE="$WS_ROOT"
export PGS_DATA_ROOT="$WS_ROOT/data"

source "$WS_ROOT/.venv/bin/activate"
EOF

chmod +x "$WS_ROOT/env.sh"

# --------------------------------------------------
# Create workspace directories and seed data
# --------------------------------------------------

echo ""
echo "[9/9] Creating workspace directories and installing seed data..."

mkdir -p "$WS_ROOT/data"
mkdir -p "$WS_ROOT/traces"
mkdir -p "$WS_ROOT/protocol_snapshot"

# Install seed data — seeds/ is the committed source of truth
# Data is organized by domain/subdomain for human-inspectable isolation
mkdir -p "$WS_ROOT/data/ai_governance/ai_licensing"
cp "$WS_ROOT/seeds/license_facts.json" "$WS_ROOT/data/ai_governance/ai_licensing/license_facts.json"
echo "  [seed] license_facts.json → data/ai_governance/ai_licensing/"

echo ""
echo "---------------------------------------"
echo "PGS Bootstrap Complete (env: $PGS_ENV)"
echo "---------------------------------------"

echo ""
echo "Activate:"
echo "  source env.sh"

echo ""
echo "Then compile and build:"
echo "  cd ../pgs_compiler"
echo "  python -m pgs_compiler.cli compile --structure STRUCTURE_BUILD_PLATFORM_CONFIG_V0"
echo "  python -m pgs_compiler.cli compile --structure STRUCTURE_BUILD_BLOCKCHAIN_CONFIG_V0"
echo "  python -m pgs_compiler.cli compile --structure STRUCTURE_BUILD_AI_GOVERNANCE_CONFIG_V0"
echo "  cd ../pgs_workspace"
echo "  python ../pgs_compiler/scripts/pgs_build.py --workspace \$(pwd)"

echo ""
