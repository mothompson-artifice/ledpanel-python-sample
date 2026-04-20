#!/usr/bin/env bash
# setup.sh — bootstrap the native-module toolchain for armv6m (RP2040)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
MPY_DIR="${MPY_DIR:-$REPO_ROOT/../micropython}"

echo "=== Checking prerequisites ==="

# --- arm-none-eabi-gcc ---
if ! command -v arm-none-eabi-gcc &>/dev/null; then
    echo "arm-none-eabi-gcc not found. Install it:"
    echo "  Ubuntu/Debian : sudo apt install gcc-arm-none-eabi binutils-arm-none-eabi"
    echo "  Arch          : sudo pacman -S arm-none-eabi-gcc arm-none-eabi-binutils"
    echo "  macOS         : brew install --cask gcc-arm-embedded"
    exit 1
fi
echo "  arm-none-eabi-gcc : $(arm-none-eabi-gcc --version | head -1)"

# --- make ---
if ! command -v make &>/dev/null; then
    echo "GNU make not found. Install it (e.g. sudo apt install make)"
    exit 1
fi
echo "  make              : $(make --version | head -1)"

# --- Python 3 + pyelftools ---
if ! python3 -c "import elftools" &>/dev/null; then
    echo "pyelftools not found — installing..."
    pip3 install 'pyelftools>=0.25'
fi
ELFTOOLS_VER=$(python3 -c "import elftools; print(elftools.__version__)")
echo "  pyelftools        : $ELFTOOLS_VER"

# --- MicroPython repo ---
if [ ! -d "$MPY_DIR/py/dynruntime.mk" ] && [ ! -f "$MPY_DIR/py/dynruntime.mk" ]; then
    echo ""
    echo "MicroPython repo not found at: $MPY_DIR"
    echo "Cloning (shallow)..."
    git clone --depth 1 https://github.com/micropython/micropython.git "$MPY_DIR"
else
    echo "  MicroPython repo  : $MPY_DIR"
fi

echo ""
echo "=== All prerequisites satisfied ==="
echo ""
echo "Build the module:"
echo "  cd $(realpath --relative-to="$PWD" "$SCRIPT_DIR")"
echo "  make"
echo ""
echo "Or override MPY_DIR explicitly:"
echo "  make MPY_DIR=/your/path/to/micropython"
