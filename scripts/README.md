# Benchmarking scripts

Python 3 scripts for benchmarking model import/export of Modest, PRISM and Storm
(UMB, DRN, TRA, AUT, ... formats).

## Setup

The scripts expect the tools in a directory `bin/` (in the repository root, ignored by git) as symbolic links:

```bash
mkdir -p bin
ln -s /path/to/modest/modest                bin/modest      # Modest Toolset (mcsta is run as `modest mcsta`)
ln -s /path/to/prism/bin/prism              bin/prism
ln -s /path/to/storm/build/bin/storm        bin/storm
ln -s /path/to/storm/build/bin/storm-conv   bin/storm-conv  # only for prism_to_jani.py
ln -s /path/to/cadp/bin.x64/bcg_io          bin/bcgio       # only for aut_to_bcg.py (CADP's bcg_io is called bcgio here)
```

- Use absolute paths and no trailing `/` in the link target. A link such as `.../bin/storm/` cannot be executed.
- `generate_inv.py` and `run.py` need `modest`, `prism`, and `storm`. `storm-conv` and `bcgio` are only needed for the
  conversions below (they are passed to the scripts as `bin/storm-conv` and `bin/bcgio`).
- The paper uses PRISM 4.11 (`f118f0b`), Storm 1.14.0 (`2c6a7c2`), mcsta v3.1.311 (`g14c460466`), and CADP 2025-l.
- Without CADP, leave out `bin/bcgio`: the scripts then skip the bcg conversion (no BCG columns in the results).
- Check the setup with `for t in modest prism storm; do test -x bin/$t || echo "bin/$t is missing"; done`.

## Quick start

Three scripts in the repository root run the whole pipeline (steps 1, 2, 4, 5 below) in their own directory:

| Script | Models | Time limit, repetitions | Takes about | Directory |
| --- | --- | --- | --- | --- |
| `./smoketest.sh` | `consensus.4-4` | 100 s, 1 | 2 minutes | `experiments-smoketest/` |
| `./subset.sh` | 20 representative models | 1800 s, 1 | 5.5 hours | `experiments-subset/` |
| `./all.sh` | all 36 models of the paper | 7200 s, 5 | days (run the invocations in parallel jobs) | `experiments-all/` |

The models are listed explicitly in the `MODELS` array at the top of each script (with their type and an estimate of their
runtime), so you can handpick your own subset by editing it. `subset.sh` and `all.sh` end by running `paper_numbers.py`,
which prints the numbers quoted in the paper, and `create_tex.py`, which creates `plots.tex` with the plots of the paper
(compile it with `pdflatex plots.tex`, twice). The scripts run `aut_to_bcg.py` only if `bin/bcgio` exists, and
not `prism_to_jani.py` (see the comments in the scripts). The results are in `<directory>/csv` and `<directory>/html/index.html`.
If the directory already exists, the scripts ask whether to delete it to start a fresh experiment. If you answer no (or
run non-interactively), they keep it and continue in it; files of earlier runs, e.g., logs and models that are no longer
in the `MODELS` list, then remain and show up in the results.

## Step by step

```bash
mkdir -p experiments && cd experiments
cp -r ../models .   # can also copy just a subset to check in more reasonable time

# (re-)generate jani files from prism (optional, overwrites models/*/model.jani)
# python3 ../scripts/prism_to_jani.py ../bin/storm-conv models

# generate invocations (7200s time limit, 5 repetitions)
python3 ../scripts/generate_inv.py ../bin models logs 7200 5

# run the exporters (the exported files are written to the model directories)
python3 ../scripts/run.py inv_export.json all

# run the importers/checkers
python3 ../scripts/run.py inv_import.json all

# convert the exported aut files to bcg, if bin/bcgio (CADP's bcg_io) exists
if [ -e ../bin/bcgio ]; then
    python3 ../scripts/aut_to_bcg.py ../bin/bcgio models logs
fi

# results
mkdir -p csv html
(cd csv && python3 ../../scripts/create_csv.py ../logs ../models)
(cd html && python3 ../../scripts/create_html.py ../csv ../logs ../models)

# numbers quoted in the paper
python3 ../scripts/paper_numbers.py csv models

# plots of the paper (creates plots.tex, compile it with pdflatex, twice)
python3 ../scripts/create_tex.py csv
```

All scripts print their usage when called with the wrong number of arguments.

## Conventions

- **Model directory** (`models/`): one subdirectory per benchmark containing `model.prism`, `model.jani` and
  `property.props`. Model names must not contain `_`, because `_` is the separator in config, invocation and log names.
- **Invocation id**: `<tool>_from-<input>_<task>_<config>_<model>`, e.g. `storm_from-jani_to-umb_sparse_<model>`.
  Task is `check`, `import` or `to-<format>` (export). Logs are named `<invocation id>_rep<N>.log`.
- Command templates use placeholders `%indir`, `%outdir`, `%modest`, `%prism`, `%storm`;
  `generate_inv.py` resolves the tool paths and `run.py` resolves the directories (see below).

## 1. `generate_inv.py` – create invocation files

```bash
python scripts/generate_inv.py <bin dir> <model dir> <logs dir> <time limit [s]> <repetitions>
```

Builds the command line for every tool/format/configuration combination and every model, and writes JSON files
**into the current working directory**:

| File | Content |
| --- | --- |
| `inv_export.json` / `inv_import.json` | all exports / all imports (+`check`) |
| `inv_all.json` | exports and imports mixed (shuffled, fixed seed); don't run it sequentially, since imports need the exported files: run `inv_export.json` and then `inv_import.json` |
| `inv_{modest,prism,storm}_{export,import}.json` | per tool |

- `<bin dir>` must contain the `modest`, `prism` and `storm` binaries.
- Exported files are written to the model directories as `<model dir>/<model>/<tool>.<file>` (e.g. `storm.model.umb.xz`,
  `modest.umb.properties.txt`, `prism.model.pexp.gz`), where the import invocations read them. Files of earlier runs are
  overwritten. `generate_inv.py` prints a warning if several command templates (e.g. two configurations of a tool) write
  the same file name, or if an output file would overwrite a model file (`model.prism`, `model.jani`, `property.props`) or a bcg file.
- Each invocation is repeated `<repetitions>` times and the list is shuffled.
- To change which tools/formats/configurations are generated, edit the `*_configurations` dicts, the
  `*_INPUT/OUTPUT_FORMATS` lists and the bottom of the script.
- Only models containing `model.prism`, `model.jani` and `property.props` are used; others are skipped with a warning.

## 2. `run.py` – execute invocations

```bash
python scripts/run.py <invocation json> <index>|all [<time limit override [s]>]
```

Runs one invocation (by index) or all of them sequentially. For each one it copies the input files into a temporary
directory, runs the commands (with timeout; the process group is killed on timeout), writes the log (command, wall
time, return code, output, sizes of output files) to `<logs dir>/<log name>`, and copies the output files to the
invocation's output directory (the model directory; first repetition only). An invocation without a `time-limit` runs
without a timeout. It prints one status line per invocation
(`done`, `timeout`, `error (<code>)`).

Example: `python scripts/run.py inv_storm_export.json all` or `python scripts/run.py inv_all.json 17 600`.
Several indices can be distributed over parallel/cluster jobs by calling the script with different indices.

## 3. Conversions: `prism_to_jani.py` and `aut_to_bcg.py`

```bash
python scripts/prism_to_jani.py <storm-conv binary> <model dir>
python scripts/aut_to_bcg.py    <bcgio binary> <model dir> <logs dir>
```

Both run each conversion once, without time limit:

- `prism_to_jani.py` converts `model.prism` + `property.props` of every model in `<model dir>` to JANI with the given
  `storm-conv` binary. It calls storm-conv directly (output goes to stdout, no log files) and **writes `model.jani` into
  the model directory, overwriting an existing one**. Run it before `generate_inv.py`, which requires `model.jani`.
  It exits with an error if a model lacks `model.prism`/`property.props` or if a conversion fails.
- `aut_to_bcg.py` (builds invocations and executes them with `run.py`) converts `modest.model.aut` (so run it after the exports) to `bcgio.model.bcg` with
  the given `bcgio` binary, and additionally compresses the result with `xz` and `gzip` (one invocation/log each).
  Output: `<model dir>/<model>/bcgio.model.bcg[.xz|.gz]`.
  The logs are named `modest_bcgio_aut-to-bcg[-xz|-gz]_default_<model>_rep1.log` so that `create_csv.py` reports the
  sizes next to the Modest exports.

For testing without CADP, `tools/bcgiodummy/bcgio` is a stand-in for `bcgio` that checks that the input exists and
copies the pre-computed `.bcg` file of the model from `tools/bcgiodummy/bcg/<model>.bcg`.
Link it into the bin directory: `ln -s $PWD/tools/bcgiodummy/bcgio bin/bcgio`.

## 4. `create_csv.py` – parse logs into CSV files

```bash
python scripts/create_csv.py <logs dir> <model dir>
```

Parses all `*.log` files and writes (tab-separated, into the current directory):

- `import_time.csv`, `full_time.csv`, `export_time.csv`, `export_size.csv`: one row per model, one column per
  `<tool>_<from>_<task>_<config>`, cells are lists of the repetitions' values;
- `*_median.csv`: median per cell, plus a column `model_type` (`dtmc`, `ctmc`, `mdp`, as given in the `type` field of the
  model's `model.jani` in `<model dir>`; used for the marker classes of the scatter plots);
- `*_quantile.csv`: sorted values per column (for quantile/cactus plots).

Failures are encoded as `TO` (timeout), `MO` (memout), `NS` (not supported), `ERR` (other error); an empty cell means
the input file did not exist (e.g. a previous export failed). The log patterns for each tool are in the `parse_*_log`
and `is_*` functions.

## 5. `create_html.py` – create the result website

```bash
python scripts/create_html.py <csv dir> <logs dir> <model dir>
```

Run it in an empty output directory (it writes into the current directory). It creates:

- `style.css`, `index.html` (a list of links to the tables below, each with the plot of the paper that it belongs to,
  e.g., "data for the plot in the middle of the top row of Fig. 5"), `_config.yml`,
- `models/<model>/` with `model.prism`, `property.props`, `model.jani` and an `index.html` page,
- `<tool>_<csv name>/index.html` for tool ∈ {modest, prism, storm} and csv name ∈ {`export_size`, `export_time`,
  `import_time`, `full_time`}: sortable tables (median ± max deviation, best value highlighted, TO/MO/NS/ERR colored)
  with links to per-cell log pages.

The `<csv dir>` must contain the raw (non-median) CSVs from step 4. Logs are embedded unmodified.

## 6. `paper_numbers.py` – recompute the numbers quoted in the paper

```bash
python scripts/paper_numbers.py <csv dir> <model dir>
```

Prints the numbers quoted in the experiments section of the paper, in the order of the paper, so that they can be
validated: the models with results and the reasons for the failures, median factors of import times, export times and
file sizes, the sizes of the high-level model files, and the statistics of the total model checking time. It reads the
`export_time.csv` and the `*_median.csv` files from step 4 and the `model.prism`/`model.jani` files from `<model dir>`.
Times below 0.1 seconds count as 0.1 seconds, except for the "largest factor". `subset.sh` and `all.sh` call it at the
end; the numbers in the paper are the ones for all 36 models (`all.sh`). For a subset of the models, or if `aut_to_bcg.py`
was not run, the numbers differ or are reported as n/a.

## 7. `create_tex.py` – recreate the plots of the paper

```bash
python scripts/create_tex.py <csv dir>
pdflatex plots.tex && pdflatex plots.tex
```

Creates `plots.tex` in the current directory, a standalone LaTeX document (needs `pgfplots` and `pgfplotstable`) that
reproduces the plots of the paper from the csv files of step 4, so that they can be compared with the paper: the
quantile plots of the import time, export time and file size with one row per tool, and the scatter plots of the total
model checking time. It contains the same plot definitions, lines, labels and colors as the paper, and the figures are numbered as in the paper
(Fig. 5: format efficiency, Fig. 6: total model checking time). Lines whose data is
missing (e.g., the BCG files if `aut_to_bcg.py` was not run) are left out with a warning, and only the models of the csv
files are shown. The `<csv dir>` is referenced by the path given on the command line, so compile `plots.tex` in the
directory from which that path is valid. The second `pdflatex` run is needed for the legend of the scatter plots.
