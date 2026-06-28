#!/usr/bin/env bash
#
# Pre-commit cleanup for the MedPartners repo.
# Removes caches, venvs, OS junk, scratch archives and typo'd files.
# Safe to re-run; prints what it removed.
#
set -euo pipefail

cd "$(dirname "$0")"

removed=0
rm_item() {
    local target="$1"
    if [ -e "$target" ]; then
        rm -rf -- "$target"
        echo "  - removed: $target"
        removed=$((removed + 1))
    fi
}

echo "Cleaning caches and generated artifacts..."
find . -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find . -type d -name '.pytest_cache' -prune -exec rm -rf {} + 2>/dev/null || true
find . -type d -name '.mypy_cache' -prune -exec rm -rf {} + 2>/dev/null || true

echo "Removing virtual environments..."
rm_item ".venv"
rm_item "venv"
rm_item "env"

echo "Removing OS-specific junk..."
find . -name '.DS_Store' -delete 2>/dev/null || true
find . -name '._*' -delete 2>/dev/null || true

echo "Removing scratch / test archives and typo'd files..."
rm_item "dummy_archive"
rm_item "test_archive.zip"
rm_item "new_test_archive.zip"
# Match the typo'd one-off file (name accidentally glued to a pip command).
find . -maxdepth 1 -name 'automated_test*' -delete 2>/dev/null || true
# One-off repair scripts that should not ship.
for f in fix_frontend.py clean_vibe.py run_all_fixes.py; do
    rm_item "$f"
done

echo "Done. Items removed: $removed"
