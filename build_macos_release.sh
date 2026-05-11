#!/usr/bin/env bash
set -euo pipefail

VERSION="${1:-1.0.0}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
VENV="$ROOT/.venv"
PY="$VENV/bin/python"
RELEASE_DIR="$ROOT/release"
DIST_DIR="$ROOT/dist"
BUILD_DIR="$ROOT/build"
SPEC="$ROOT/curve_analyzer_macos.spec"
APP_PATH="$DIST_DIR/Curve Analyzer.app"
PACKAGE_DIR="$RELEASE_DIR/Curve Analyzer macOS"
ZIP_PATH="$RELEASE_DIR/Curve_Analyzer_macOS_Portable_v$VERSION.zip"

cd "$ROOT"

if [ ! -x "$PY" ]; then
    echo "Creating virtual environment..."
    "$PYTHON" -m venv "$VENV"
fi

mkdir -p "$RELEASE_DIR"

echo "Installing/updating build dependencies..."
"$PY" -m pip install --upgrade pip
"$PY" -m pip install -r "$ROOT/requirements.txt"
"$PY" -m pip install pyinstaller

echo "Cleaning old build outputs..."
rm -rf "$BUILD_DIR" "$APP_PATH" "$PACKAGE_DIR" "$ZIP_PATH"

echo "Building macOS app with PyInstaller..."
"$PY" -m PyInstaller --noconfirm --clean "$SPEC"

if [ ! -d "$APP_PATH" ]; then
    echo "Build failed: app not found at $APP_PATH" >&2
    exit 1
fi

if command -v codesign >/dev/null 2>&1; then
    echo "Applying ad-hoc code signature..."
    codesign --force --deep --sign - "$APP_PATH" || true
fi

echo "Creating portable zip..."
mkdir -p "$PACKAGE_DIR"
cp -R "$APP_PATH" "$PACKAGE_DIR/"
cp "$ROOT/INSTRUCTIONS.txt" "$PACKAGE_DIR/"
cp "$ROOT/sample_sinusoidal_data.xlsx" "$PACKAGE_DIR/"

(
    cd "$RELEASE_DIR"
    ditto -c -k --sequesterRsrc --keepParent "Curve Analyzer macOS" "$ZIP_PATH"
)

echo "Portable macOS zip: $ZIP_PATH"
echo "Release build complete."
