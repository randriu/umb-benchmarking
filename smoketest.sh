#!/usr/bin/env bash
set -e

# Runs the benchmarks on a small model, which takes about 2 minutes
# (with the time limit of 100 seconds and one repetition used below).
cd "$(dirname "${BASH_SOURCE[0]}")"

# The estimated runtime (in minutes) is based on the logs in experiments-paper/logs
MODELS=(
    consensus.4-4  # mdp,   2
)

mkdir -p experiments-smoketest && cd experiments-smoketest
mkdir -p models
for model in "${MODELS[@]}"; do
    cp -r "../models/$model" models/
done

# (re-)generate jani files from prism (optional, overwrites models/*/model.jani)
# python3 ../scripts/prism_to_jani.py ../bin/storm-conv models

# generate invocations (100 time limit, 1 repetition)
python3 ../scripts/generate_inv.py ../bin models logs 100 1

# run the exporters (the exported files are written to the model directories)
python3 ../scripts/run.py inv_export.json all

# run the importers/checkers (requires to have the exported files first)
python3 ../scripts/run.py inv_import.json all

# if a bcgio binary is available (needs the exported modest.model.aut):
# python3 ../scripts/aut_to_bcg.py ../bin/bcgio models logs

# results
mkdir -p csv html
(cd csv && python3 ../../scripts/create_csv.py ../logs ../models)
(cd html && python3 ../../scripts/create_html.py ../csv ../logs ../models)
