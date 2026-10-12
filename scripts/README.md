# Benchmarking scripts

Python 3 scripts (standard library only) for benchmarking model import/export of Modest, PRISM and Storm
(UMB, DRN, TRA, AUT, ... formats). Typical pipeline:

```
generate_inv.py  ->  run.py  ->  copy_modelfiles.py  ->  run.py (import)  ->  create_csv.py  ->  create_html.py
```

All scripts print their usage when called with the wrong number of arguments. Paths below are examples.

## Conventions

- **Model directory** (`models/`): one subdirectory per benchmark containing `model.prism`, `model.jani` and
  `property.props`. Model names must not contain `_`, because `_` is the separator in config, invocation and log names.
- **Invocation id**: `<tool>_from-<input>_<task>_<config>_<model>`, e.g. `storm_from-jani_to-umb_sparse_<model>`.
  Task is `check`, `import` or `to-<format>` (export). Logs are named `<invocation id>_rep<N>.log`.
- Command templates use placeholders `%indir`, `%outdir`, `%modest`, `%prism`, `%storm`, `%storm-conv`;
  `generate_inv.py` resolves the tool paths and `run.py` resolves the directories (see below).

## 1. `generate_inv.py` – create invocation files

```bash
python scripts/generate_inv.py <bin dir> <model dir> <output dir> <logs dir> <time limit [s]> <repetitions>
```

Builds the command line for every tool/format/configuration combination and every model, and writes JSON files
**into the current working directory**:

| File | Content |
| --- | --- |
| `inv_export.json` / `inv_import.json` | all exports / all imports (+`check`) |
| `inv_all.json` | exports followed by imports (shuffled, fixed seed) |
| `inv_{modest,prism,storm}_{export,import}.json` | per tool |
| `inv_storm_prism_to_jani.json`, `inv_bcgio_export.json` | PRISM→JANI conversion, AUT→BCG |

- `<bin dir>` must contain the `modest`, `prism` and `storm` (and `storm-conv`) binaries.
- `<output dir>` receives exported files as `<output dir>/<tool>_from-<in>_to-<out>_<config>/<model>/`.
- Each invocation is repeated `<repetitions>` times and the list is shuffled.
- To change which tools/formats/configurations are generated, edit the `*_configurations` dicts, the
  `*_INPUT/OUTPUT_FORMATS` lists and the bottom of the script.
- Only models containing `model.prism`, `model.jani` and `property.props` are used; others are skipped with a warning.
- The `bcgio` binary (for `inv_bcgio_export.json`) is also expected in `<bin dir>`.

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

## 3. `copy_modelfiles.py` – make exported files available as import inputs

```bash
python scripts/copy_modelfiles.py <output dir> <model dir>
```

Copies the files produced by the export runs (`<output dir>/<config>/<model>/model.umb`, `.drn`, `.tra`, `.aut`, ...)
into `<model dir>/<model>/` as `<tool>.<file>` (e.g. `storm.model.umb.xz`, `prism.model.tradir`). The import
invocations from step 1 read these files via `%indir`. Existing non-empty files are not overwritten.
Run it after the export invocations and before the import invocations. The script aborts if `<output dir>`
contains an unknown config folder (the allowed ones are listed in the script).

## 4. `create_csv.py` – parse logs into CSV files

```bash
python scripts/create_csv.py <logs dir>
```

Parses all `*.log` files and writes (tab-separated, into the current directory):

- `import_time.csv`, `full_time.csv`, `export_time.csv`, `export_size.csv`: one row per model, one column per
  `<tool>_<from>_<task>_<config>`, cells are lists of the repetitions' values;
- `*_median.csv`: median per cell;
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
