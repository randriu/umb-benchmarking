#!/usr/bin/env bash
set -e

# Runs the benchmarks on a representative subset of the models, which takes about 5.5 hours
# (with the time limit of 1800 seconds and one repetition used below).
cd "$(dirname "${BASH_SOURCE[0]}")"

# The subset has 5 DTMCs, 5 CTMCs, and 10 MDPs.
# It spans small, medium, and large models, and includes herman.15, which mcsta does not support.
# The estimated runtime (in minutes) is based on the logs in experiments-paper/logs, with each invocation limited to
# 1800 seconds; it is 5.5 hours in total, and no timeouts are expected.
MODELS=(
    haddad-monmege.100-0.7          # dtmc,  2
    crowds.5-20                     # dtmc, 10
    nand.40-4                       # dtmc, 10
    herman.15                       # dtmc, 16
    crowds.6-20                     # dtmc, 46
    embedded.8-12                   # ctmc,  2
    mapk-cascade.4-30               # ctmc,  6
    majority.2100                   # ctmc, 38
    kanban.5                        # ctmc, 40
    cluster.64-2000-20              # ctmc, 73
    consensus.4-4                   # mdp,   2
    wlan.4-0                        # mdp,   3
    firewire.false-36-800           # mdp,   3
    csma.4-2                        # mdp,   5
    pnueli-zuck.5                   # mdp,   5
    csma.3-4                        # mdp,   6
    resource-gathering.1300-100-100 # mdp,   9
    zeroconf.1000-8-false           # mdp,  11
    eajs.5-250-11                   # mdp,  16
    wlan.6-0                        # mdp,  28
)

mkdir -p experiments-subset && cd experiments-subset
mkdir -p models
for model in "${MODELS[@]}"; do
    cp -r "../models/$model" models/
done

# (re-)generate jani files from prism (optional, overwrites models/*/model.jani)
# python3 ../scripts/prism_to_jani.py ../bin/storm-conv models

# generate invocations (1800s time limit, 1 repetition)
python3 ../scripts/generate_inv.py ../bin models logs 1800 1

# run the exporters (the exported files are written to the model directories)
python3 ../scripts/run.py inv_export.json all

# run the importers/checkers (requires to have the exported files first)
python3 ../scripts/run.py inv_import.json all

# if a bcgio binary is available (needs the exported modest.model.aut):
# python3 ../scripts/aut_to_bcg.py ../bin/bcgio models logs

# results
mkdir csv html
(cd csv && python3 ../../scripts/create_csv.py ../logs ../models)
(cd html && python3 ../../scripts/create_html.py ../csv ../logs ../models)
