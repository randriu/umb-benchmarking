#!/usr/bin/env bash
set -e

# Runs the benchmarks on all models of the paper, with the settings of the paper (one run takes days, see below).
# To run only some of the models, remove (or comment out) the others in the list below.
cd "$(dirname "${BASH_SOURCE[0]}")"

TIME_LIMIT=7200  # seconds per invocation
REPETITIONS=5

# The 36 models of the paper (10 DTMCs, 9 CTMCs, 17 MDPs) with their type and an estimate of the runtime of
# one repetition with all invocations run one after the other. The estimate is based on the logs in
# experiments-paper/logs; it is 68 hours for one repetition, so about 341 hours for the five repetitions of
# this script. On a cluster, run the invocations in parallel jobs instead: run.py can run a single invocation
# of the json files by its index.
MODELS=(
    haddad-monmege.100-0.7           # dtmc, 2 min
    crowds.5-20                      # dtmc, 10 min
    nand.40-4                        # dtmc, 10 min
    herman.15                        # dtmc, 16 min
    crowds.6-20                      # dtmc, 46 min
    nand.60-4                        # dtmc, 48 min
    oscillators.8-10-0.1-1-0.1-1.0   # dtmc, 50 min
    egl.10-2                         # dtmc, 2.7 h
    egl.10-8                         # dtmc, 4.1 h
    bluetooth.1                      # dtmc, 18.1 h
    embedded.8-12                    # ctmc, 2 min
    mapk-cascade.4-30                # ctmc, 6 min
    majority.2100                    # ctmc, 38 min
    kanban.5                         # ctmc, 40 min
    cluster.64-2000-20               # ctmc, 1.2 h
    fms.8                            # ctmc, 1.4 h
    speed-ind.2100                   # ctmc, 2.3 h
    polling.18-16                    # ctmc, 4.5 h
    cluster.128-2000-20              # ctmc, 5.7 h
    consensus.4-4                    # mdp, 2 min
    wlan.4-0                         # mdp, 3 min
    firewire.false-36-800            # mdp, 3 min
    csma.4-2                         # mdp, 4 min
    pnueli-zuck.5                    # mdp, 5 min
    csma.3-4                         # mdp, 6 min
    wlan.5-0                         # mdp, 7 min
    resource-gathering.1300-100-100  # mdp, 9 min
    zeroconf.1000-8-false            # mdp, 11 min
    consensus.6-2                    # mdp, 14 min
    eajs.5-250-11                    # mdp, 16 min
    wlan.6-0                         # mdp, 28 min
    eajs.6-300-13                    # mdp, 45 min
    pacman.60                        # mdp, 3.1 h
    rabin.10                         # mdp, 4.5 h
    pacman.100                       # mdp, 4.9 h
    pnueli-zuck.10                   # mdp, 8.6 h
)

EXPERIMENT_DIR=experiments-all
if [ -e "$EXPERIMENT_DIR" ]; then
    read -r -p "'$EXPERIMENT_DIR' already exists. Delete it to start a fresh experiment? [y/N] " answer || answer=n
    if [[ "$answer" =~ ^[Yy]$ ]]; then
        rm -rf -- "$EXPERIMENT_DIR"
    else
        echo "Keeping '$EXPERIMENT_DIR': files of earlier runs stay there (and are overwritten where the new run writes the same files)."
    fi
fi
mkdir -p "$EXPERIMENT_DIR" && cd "$EXPERIMENT_DIR"
mkdir -p models
for model in "${MODELS[@]}"; do
    cp -r "../models/$model" models/
done

# (re-)generate jani files from prism (optional, overwrites models/*/model.jani)
# python3 ../scripts/prism_to_jani.py ../bin/storm-conv models

# generate invocations
python3 ../scripts/generate_inv.py ../bin models logs "$TIME_LIMIT" "$REPETITIONS"

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

# plots of the paper (for the models of this run): compile plots.tex with pdflatex (twice)
python3 ../scripts/create_tex.py csv

# numbers of the paper (for the models of this run)
python3 ../scripts/paper_numbers.py csv models