# Benchmarking scripts

Python 3 scripts for benchmarking model import/export of Modest, PRISM and Storm
(UMB, DRN, TRA, AUT, ... formats).

tl;dr:

```bash
mkdir experiments && cd experiments
cp -r ../models .   # can also copy just a subset to check in more reasonable time

# (re-)generate jani files from prism (optional, overwrites models/*/model.jani)
# python3 ../scripts/prism_to_jani.py ../bin/storm-conv models

# generate invocations (7200s time limit, 5 repetitions)
python3 ../scripts/generate_inv.py ../bin models logs 7200 5

# run the exporters (the exported files are written to the model directories)
python3 ../scripts/run.py inv_export.json all

# run the importers/checkers
python3 ../scripts/run.py inv_import.json all

# if a bcgio binary is available (needs the exported modest.model.aut):
# python3 ../scripts/aut_to_bcg.py ../bin/bcgio models logs

# results
mkdir csv html
(cd csv && python3 ../../scripts/create_csv.py ../logs ../models)
(cd html && python3 ../../scripts/create_html.py ../csv ../logs ../models)
```

All scripts print their usage when called with the wrong number of arguments.

## Smoke test

```bash
./smoketest.sh [<bin dir>]
```

Runs the whole pipeline (conversions, steps 1–5) once on the model `wlan.4-0`, with all files in `./smoketest_workdir`
(it asks before deleting an existing one). `<bin dir>` defaults to `./bin` and must contain `modest`, `prism`, `storm`,
`storm-conv` and `bcgio` (see below for a dummy). It starts with the conversion of the PRISM file to JANI. Afterwards it checks that every configuration produced output, that the
csv files contain no `ERR`/`TO`/`MO`/empty cells for the model and that the html pages exist.

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
invocation's output directory (first repetition only). It prints one status line per invocation
(`done`, `timeout`, `error (<code>)`).

Example: `python scripts/run.py inv_storm_export.json all` or `python scripts/run.py inv_all.json 17 600`.
Several indices can be distributed over parallel/cluster jobs by calling the script with different indices.

## Conversions: `prism_to_jani.py` and `aut_to_bcg.py`

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

- `style.css`, `index.md`, `_config.yml` (GitHub Pages / Jekyll ready),
- `models/<model>/` with `model.prism`, `property.props`, `model.jani` and an `index.html` page,
- `<tool>_<csv name>/index.html` for tool ∈ {modest, prism, storm} and csv name ∈ {`export_size`, `export_time`,
  `import_time`, `full_time`}: sortable tables (median ± max deviation, best value highlighted, TO/MO/NS/ERR colored)
  with links to per-cell log pages.

The `<csv dir>` must contain the raw (non-median) CSVs from step 4. Logs are embedded unmodified.

## 6. `paper_numbers.py` – recompute the numbers quoted in the paper

```bash
python scripts/paper_numbers.py <csv dir> <model dir>
```

Reads the `*_median.csv` files from step 4 and prints all numbers quoted in the experiments section of the paper
(median factors of import/export times and file sizes, number of models with results, total time factors, size of
the high-level model files, ...). Times below 0.1 seconds count as 0.1 seconds, except for the "largest factor".
