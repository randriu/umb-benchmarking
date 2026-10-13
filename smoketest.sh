#!/usr/bin/env bash
# Smoke test: runs the whole benchmarking pipeline on one small model, with all files in ./smoketest_workdir.
# Usage: ./smoketest.sh [<bin dir>]     (default: ./bin, must contain modest, prism, storm, storm-conv)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS="$ROOT/scripts"
BIN="$(cd "${1:-$ROOT/bin}" && pwd)"
WORK="$ROOT/smoketest_workdir"
MODEL="embedded.8-12"
TIME_LIMIT=600

for tool in modest prism storm storm-conv; do
    [ -x "$BIN/$tool" ] || { echo "ERROR: '$BIN/$tool' does not exist or is not executable." >&2; exit 1; }
done

if [ -e "$WORK" ]; then
    read -r -p "'$WORK' already exists. Delete it? [y/N] " answer
    [[ "$answer" =~ ^[Yy]$ ]] || { echo "Aborting."; exit 1; }
    rm -rf "$WORK"
fi
mkdir -p "$WORK/models/$MODEL"
cp "$ROOT/models/$MODEL/model.prism" "$ROOT/models/$MODEL/property.props" "$WORK/models/$MODEL/"
cd "$WORK"

echo "== PRISM to JANI"
python3 "$SCRIPTS/prism_to_jani.py" "$BIN/storm-conv" models

echo "== Generating invocations"
python3 "$SCRIPTS/generate_inv.py" "$BIN" models out logs "$TIME_LIMIT" 1 > generate_inv.out

echo "== Export"
python3 "$SCRIPTS/run.py" inv_export.json all
python3 "$SCRIPTS/copy_modelfiles.py" out models > copy_modelfiles.out

echo "== AUT to BCG"
python3 "$SCRIPTS/aut_to_bcg.py" "$BIN/bcgio" models out logs

echo "== Import"
python3 "$SCRIPTS/run.py" inv_import.json all

echo "== CSV and HTML"
mkdir csv html
(cd csv && python3 "$SCRIPTS/create_csv.py" ../logs ../models > ../create_csv.out)
(cd html && python3 "$SCRIPTS/create_html.py" ../csv ../logs ../models > ../create_html.out)

echo "== Sanity checks"
failed=0
fail() { echo "FAIL: $1"; failed=1; }

# every configuration (incl. conversions) produced a non-empty output file for the model
for dir in out/*/"$MODEL"; do
    [ -n "$(find "$dir" -type f -size +0c)" ] || fail "no output in $dir"
done
# raw csv files contain a row for the model and no failed (ERR/TO/MO) or empty ([]) cells
for name in export_size export_time import_time full_time; do
    grep -q "^$MODEL" "csv/$name.csv" || fail "csv/$name.csv has no row for $MODEL"
    grep -wE "ERR|TO|MO" "csv/$name.csv" > /dev/null && fail "csv/$name.csv contains ERR/TO/MO cells"
done
for name in export_size import_time full_time; do
    grep -F "[]" "csv/$name.csv" > /dev/null && fail "csv/$name.csv contains empty cells"
done
# html pages exist
for page in index.md models/$MODEL/index.html {modest,prism,storm}_{export_size,export_time,import_time,full_time}/index.html; do
    [ -s "html/$page" ] || fail "missing html/$page"
done

[ "$failed" = 0 ] || { echo "Smoke test FAILED (see $WORK)."; exit 1; }
echo "Smoke test passed (results in $WORK)."
