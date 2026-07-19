#!/usr/bin/env bash
set -u

ROOT="/Users/yl/Desktop/skills/ChemKit"
PLUGIN_ROOT="$ROOT/plugins"
SOURCES="$PLUGIN_ROOT/sources"
VENV="$PLUGIN_ROOT/.venv-ocsr"
INSTALL_PYTHON=0
PREFER_GIT=0

for arg in "$@"; do
  case "$arg" in
    --install-python) INSTALL_PYTHON=1 ;;
    --prefer-git) PREFER_GIT=1 ;;
    -h|--help)
      echo "Usage: $0 [--install-python] [--prefer-git]"
      exit 0
      ;;
    *)
      echo "Unknown argument: $arg" >&2
      exit 2
      ;;
  esac
done

mkdir -p "$SOURCES" "$PLUGIN_ROOT/cache" "$PLUGIN_ROOT/outputs"

download_zip() {
  local owner_repo="$1"
  local branch="$2"
  local dest="$3"
  local tmp_zip="$PLUGIN_ROOT/cache/${owner_repo//\//-}-${branch}.zip"
  local tmp_dir="$PLUGIN_ROOT/cache/${owner_repo//\//-}-${branch}"

  rm -rf "$tmp_zip" "$tmp_dir" "$dest"
  curl -L --retry 3 --retry-delay 3 \
    "https://codeload.github.com/${owner_repo}/zip/refs/heads/${branch}" \
    -o "$tmp_zip"
  unzip -q "$tmp_zip" -d "$tmp_dir"
  local unpacked
  unpacked="$(find "$tmp_dir" -mindepth 1 -maxdepth 1 -type d | head -1)"
  if [[ -z "$unpacked" ]]; then
    echo "Could not unpack $owner_repo" >&2
    return 1
  fi
  mv "$unpacked" "$dest"
}

fetch_repo() {
  local name="$1"
  local owner_repo="$2"
  local branch="$3"
  local dest="$4"

  if [[ -d "$dest/.git" || -f "$dest/README.md" || -f "$dest/setup.py" || -f "$dest/pyproject.toml" ]]; then
    echo "$name already present: $dest"
    return 0
  fi

  rm -rf "$dest"
  echo "Fetching $name..."
  if [[ "$PREFER_GIT" -eq 1 ]]; then
    if git -c http.version=HTTP/1.1 clone --depth 1 "https://github.com/${owner_repo}.git" "$dest"; then
      return 0
    fi
    echo "git clone failed for $name; trying codeload zip..."
  fi
  download_zip "$owner_repo" "$branch" "$dest"
}

fetch_repo "MolScribe" "thomas0809/MolScribe" "main" "$SOURCES/MolScribe"
fetch_repo "ReactionDataExtractor2" "dmw51/reactiondataextractor2" "master" "$SOURCES/reactiondataextractor2"
fetch_repo "DECIMER Image Transformer" "Kohulan/DECIMER-Image_Transformer" "master" "$SOURCES/DECIMER-Image_Transformer"
fetch_repo "RxnScribe" "thomas0809/RxnScribe" "main" "$SOURCES/RxnScribe"

if [[ "$INSTALL_PYTHON" -eq 1 ]]; then
  python3 -m venv "$VENV"
  "$VENV/bin/python" -m pip install --upgrade pip setuptools wheel
  "$VENV/bin/python" -m pip install MolScribe decimer
  echo "Python OCSR venv: $VENV"
  echo "ReactionDataExtractor2 still needs its conda/native-dependency install path."
fi

python3 "$ROOT/scripts/check_ocsr_plugins.py"
