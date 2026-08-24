#!/usr/bin/env sh
set -eu
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -n "${CHEMKIT_PYTHON:-}" ] && command -v "$CHEMKIT_PYTHON" >/dev/null 2>&1; then
  exec "$CHEMKIT_PYTHON" "$SCRIPT_DIR/scripts/install_chemkit.py" "$@"
fi
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    exec "$candidate" "$SCRIPT_DIR/scripts/install_chemkit.py" "$@"
  fi
done
if command -v uv >/dev/null 2>&1; then
  echo "No Python found; using uv to bootstrap Python 3.11."
  exec uv run --python 3.11 --no-project "$SCRIPT_DIR/scripts/install_chemkit.py" "$@"
fi
cat >&2 <<'EOF'
ChemKit could not find Python or uv.
Install one bootstrap runtime (Python 3.9+ or uv), then run ./install.sh again.
The Agent skill itself cannot create an operating-system runtime when no executable exists.
EOF
exit 2
