#!/bin/bash
set -euo pipefail

export PATH="$HOME/.local/bin:/usr/local/bin:$PATH"

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

python3 compile_weekly.py
