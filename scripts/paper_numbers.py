import os
import sys
import csv
import statistics

# Prints the numbers quoted in the experiments section of the paper (Format Efficiency), in the order of the paper,
# so that they can be validated. The numbers are derived from the csv files created by create_csv.py and from the
# model files. If only a subset of the models was run, the numbers differ from the ones in the paper.
#
# Conventions (as in the paper): a "median factor" is the median over all models for which both values exist;
# times below 0.1 seconds are counted as 0.1 seconds (but not for the "largest factor" and for file sizes).

# Column names: <tool>_from-<input>_<task>_<configuration>
S, M, P = "storm_from-jani_to-", "modest_from-jani_to-", "prism_from-prism_to-"  # export columns
BCG = "modest_bcgio_aut-to-bcg"

def load(csv_dir, name):
    """ Returns {model: {column: cell}} for the given csv file. """
    with open(os.path.join(csv_dir, name + ".csv"), newline="") as f:
        rows = list(csv.reader(f, delimiter="\t"))
    return {row[0]: dict(zip(rows[0][1:], row[1:])) for row in rows[1:]}

def value(table, model, column):
    """ Returns the number in the cell (of a median csv file) or None if there is none (nan, missing column, ...). """
    try:
        x = float(table[model][column])
    except (KeyError, ValueError):
        return None
    return None if x != x else x

def floor_time(x):
    return max(x, 0.1)

def factors(table, numerator, denominator, floor=True):
    """ Returns {model: numerator/denominator} for all models that have both values. """
    result = dict()
    for model in table:
        a, b = value(table, model, numerator), value(table, model, denominator)
        if a is None or b is None:
            continue
        if floor:
            a, b = floor_time(a), floor_time(b)
        if b == 0:
            continue
        result[model] = a / b
    return result

def median(values):
    values = list(values)
    return statistics.median(values) if values else None

def show(label, result, fmt="{:.1f}", suffix=""):
    print("  {:<70} {}".format(label, fmt.format(result) + suffix if result is not None else "n/a (no data)"))

def show_median_factor(label, table, numerator, denominator, floor=True, fmt="{:.2f}"):
    f = factors(table, numerator, denominator, floor)
    show("{} [{} models]".format(label, len(f)), median(f.values()), fmt)

def failure_codes(cell):
    """ Returns the set of failure codes (TO, MO, NS, ERR) in a cell of a raw csv file. """
    return {x.strip() for x in cell.strip("[]").split(",") if x.strip() in ["TO", "MO", "NS", "ERR"]}

def section(title):
    print("\n## " + title)

if __name__ == "__main__":
    print("Prints the numbers quoted in the paper. Usage:\n\tpython {} <csv directory> <models directory>".format(sys.argv[0]))
    if len(sys.argv) != 3:
        print("Invalid number of arguments.")
        sys.exit(1)
    csv_dir, models_dir = sys.argv[1:3]
    imp, exp, size, full = (load(csv_dir, n + "_median") for n in ["import_time", "export_time", "export_size", "full_time"])
    raw_exp = load(csv_dir, "export_time")
    models = sorted(size)
    print("Models in the csv files: {}".format(len(models)))

    # ---------------------------------------------------------------- Benchmarks
    section("Benchmarks")
    tools = [("storm", S + "umb_sparse"), ("mcsta", M + "umb_default"), ("prism", P + "umb_ex")]
    print("  Models for which the tool wrote a UMB file (we obtain UMB files and measurements for ...):")
    for tool, column in tools:
        show(tool, sum(1 for m in models if value(size, m, column) is not None), "{}", " models")
    print("  Models without UMB file, with the failure codes of the UMB export (TO: timeout, MO: memout, NS: not supported, ERR: other error):")
    for tool, column in tools:
        failed = ["{} ({})".format(m, "/".join(sorted(failure_codes(raw_exp.get(m, {}).get(column, "")))) or "no result")
                  for m in models if value(size, m, column) is None]
        print("  {:<7} {}".format(tool, ", ".join(failed) if failed else "none"))
    models_failed_by_all = [m for m in models if all(value(size, m, c) is None for _, c in tools)]
    print("  Models on which all three tools failed: {}".format(", ".join(models_failed_by_all) if models_failed_by_all else "none"))

    # ---------------------------------------------------------------- Measurements
    section("Measurements")
    column = "modest_from-umb_import_default"
    times = [value(imp, m, column) for m in models if value(imp, m, column) is not None]
    show("mcsta reports 0.0 seconds for ... of the uncompressed UMB files", sum(1 for t in times if t == 0), "{} of " + str(len(times)))

    # ---------------------------------------------------------------- Import time
    section("Import Time")
    print("  Median factor of loading an uncompressed UMB file vs. ...")
    show_median_factor("Storm: building from JANI", imp, "storm_from-jani_import_sparse", "storm_from-umb_import_sparse")
    show_median_factor("Storm: building from the PRISM language", imp, "storm_from-prism_import_sparse", "storm_from-umb_import_sparse")
    show_median_factor("Storm: parsing the .drn file", imp, "storm_from-drn_import_sparse", "storm_from-umb_import_sparse")
    for label, column in [("UMB", "storm_from-umb_import_sparse"), ("JANI", "storm_from-jani_import_sparse"), ("DRN", "storm_from-drn_import_sparse")]:
        show("Storm: longest import time from " + label, max([v for m in models if (v := value(imp, m, column)) is not None], default=None), "{:.1f}", " s")
    dd = factors(imp, "storm_from-jani_import_cudd", "storm_from-jani_import_sparse", floor=False)
    show("Storm: JANI (dd) is faster than the explicit JANI import for", sum(1 for f in dd.values() if f < 1), "{} of " + str(len(dd)), " models")
    dd_umb = [(value(imp, m, "storm_from-jani_import_cudd"), value(imp, m, "storm_from-umb_import_sparse")) for m in models]
    dd_umb = [(a, b) for a, b in dd_umb if a is not None and b is not None]
    show("Storm: JANI (dd) is slower than loading UMB for", sum(1 for a, b in dd_umb if a > b), "{} of " + str(len(dd_umb)), " models")
    show_median_factor("mcsta: exploring JANI", imp, "modest_from-jani_import_default", "modest_from-umb_import_default")
    show_median_factor("prism: building from the PRISM language", imp, "prism_from-prism_import_ex", "prism_from-umb_import_ex")
    print("  Compression (Storm), median factor of loading ... vs. uncompressed UMB")
    show_median_factor("GZip-compressed UMB", imp, "storm_from-umb-gz_import_sparse", "storm_from-umb_import_sparse")
    show_median_factor("XZ-compressed UMB", imp, "storm_from-umb-xz_import_sparse", "storm_from-umb_import_sparse")
    xz = "storm_from-umb-xz_import_sparse"
    for label, column in [("JANI", "storm_from-jani_import_sparse"), ("PRISM language", "storm_from-prism_import_sparse"), ("uncompressed DRN", "storm_from-drn_import_sparse")]:
        slower = {m: "{:.0f}% longer".format((floor_time(value(imp, m, xz)) / floor_time(value(imp, m, column)) - 1) * 100)
                  for m in models if value(imp, m, xz) is not None and value(imp, m, column) is not None
                  and floor_time(value(imp, m, xz)) > floor_time(value(imp, m, column))}
        print("  Models where loading XZ-compressed UMB is slower than {}: {}".format(label, slower if slower else "none"))

    # ---------------------------------------------------------------- Export time and file size
    section("Export Time and File Size")
    print("  Median factor of writing ... vs. writing uncompressed UMB (export time)")
    show_median_factor("Storm: .drn", exp, S + "drn_sparse", S + "umb_sparse", fmt="{:.1f}")
    show_median_factor("prism: .tra", exp, P + "tra_ex", P + "umb_ex", fmt="{:.1f}")
    show_median_factor("mcsta: .mrm", exp, M + "imca_default", M + "umb_default", fmt="{:.1f}")
    show_median_factor("mcsta: .aut", exp, M + "aut_default", M + "umb_default", fmt="{:.1f}")
    print("  Median factor of writing compressed .drn files vs. compressed UMB files (Storm)")
    show_median_factor("GZip", exp, S + "drn-gz_sparse", S + "umb-gz_sparse")
    show_median_factor("XZ", exp, S + "drn-xz_sparse", S + "umb-xz_sparse")
    print("  Median factor of the file size of ... vs. uncompressed UMB")
    show_median_factor("Storm: .drn", size, S + "drn_sparse", S + "umb_sparse", False)
    show_median_factor("mcsta: .aut", size, M + "aut_default", M + "umb_default", False)
    show_median_factor("prism: .tra", size, P + "tra_ex", P + "umb_ex", False)
    show_median_factor("mcsta: .mrm", size, M + "imca_default", M + "umb_default", False)
    print("  Median factor by which compression reduces the size of UMB files")
    show_median_factor("Storm: GZip", size, S + "umb_sparse", S + "umb-gz_sparse", False, "{:.1f}")
    show_median_factor("Storm: XZ", size, S + "umb_sparse", S + "umb-xz_sparse", False, "{:.1f}")
    show_median_factor("mcsta: GZip", size, M + "umb_default", M + "umb-gz_default", False, "{:.1f}")
    show_median_factor("mcsta: XZ", size, M + "umb_default", M + "umb-xz_default", False, "{:.1f}")
    show_median_factor("Storm: XZ-compressed .drn vs. XZ-compressed UMB", size, S + "drn-xz_sparse", S + "umb-xz_sparse", False)
    print("  BCG (converted from .aut)")
    if any(BCG + "_default" in row for row in size.values()):
        show_median_factor("uncompressed UMB vs. uncompressed BCG", size, M + "umb_default", BCG + "_default", False)
        smaller = factors(size, M + "umb-xz_default", BCG + "_default", False)
        show("XZ-compressed UMB is smaller than uncompressed BCG for", sum(1 for f in smaller.values() if f < 1), "{} of " + str(len(smaller)), " models")
        show_median_factor("XZ-compressed BCG vs. XZ-compressed UMB", size, BCG + "-xz_default", M + "umb-xz_default", False)
    else:
        print("  n/a (no bcgio columns in the csv files, see aut_to_bcg.py)")
    print("  Size of the high-level model files vs. the UMB files written by Storm")
    prism_sizes, jani_sizes, umb_sizes, larger = [], [], [], []
    for model in models:
        prism_file, jani_file = (os.path.join(models_dir, model, f) for f in ["model.prism", "model.jani"])
        if not (os.path.isfile(prism_file) and os.path.isfile(jani_file)):
            continue
        prism_sizes.append(os.path.getsize(prism_file))
        jani_sizes.append(os.path.getsize(jani_file))
        umb_size = value(size, model, S + "umb_sparse")
        if umb_size is not None:
            umb_sizes.append(umb_size)
            if max(prism_sizes[-1], jani_sizes[-1]) > umb_size:
                larger.append((model, prism_sizes[-1], jani_sizes[-1], umb_size))
    kib, mib = 1024, 1024 ** 2
    show("median size of the PRISM language files [{} models]".format(len(prism_sizes)), median(prism_sizes) / kib if prism_sizes else None, "{:.1f}", " KiB")
    show("median size of the JANI files [{} models]".format(len(jani_sizes)), median(jani_sizes) / kib if jani_sizes else None, "{:.0f}", " KiB")
    show("median size of the UMB files [{} models]".format(len(umb_sizes)), median(umb_sizes) / mib if umb_sizes else None, "{:.0f}", " MiB")
    for model, p, j, u in larger:
        print("  Models whose PRISM or JANI file is larger than its UMB file: {} (PRISM {:.1f} MiB, JANI {:.1f} MiB, UMB {:.1f} MiB)".format(model, p / mib, j / mib, u / mib))
    if not larger:
        print("  Models whose PRISM or JANI file is larger than its UMB file: none")

    # ---------------------------------------------------------------- Total model checking time
    section("Total Model Checking Time")
    checks = [("Storm", "storm_from-jani_check_sparse", "storm_from-umb_check_sparse"),
              ("mcsta", "modest_from-jani_check_default", "modest_from-umb_check_default"),
              ("prism", "prism_from-prism_check_ex", "prism_from-umb_check_ex")]
    slowdowns = []
    for tool, high, umb in checks:
        f, raw = factors(full, high, umb), factors(full, high, umb, floor=False)
        print("  {} (UMB input vs. high-level input)".format(tool))
        if not f:
            print("    n/a (no data)")
            continue
        show("  median factor [{} models]".format(len(f)), median(f.values()), "{:.1f}")
        show("  total time at least halves for", sum(1 for x in f.values() if x >= 2), "{} of " + str(len(f)), " models")
        show("  largest factor (without rounding up times)", max(raw.values()), "{:.0f}")
        slower = [(1 / x - 1) * 100 for x in f.values() if x < 1]
        slowdowns += slower
        show("  models where the UMB input is slower: maximal difference [{} models]".format(len(slower)), max(slower) if slower else 0, "{:.1f}", " %")
    show("Maximal difference over all tools on models where UMB is slower", max(slowdowns) if slowdowns else 0, "{:.1f}", " %")
    print("  Median share of the import time in the total time for the high-level input")
    for tool, imp_column, full_column in [("Storm", "storm_from-jani_import_sparse", "storm_from-jani_check_sparse"),
                                          ("mcsta", "modest_from-jani_import_default", "modest_from-jani_check_default"),
                                          ("prism (explicit engine)", "prism_from-prism_import_ex", "prism_from-prism_check_ex")]:
        shares = [100 * value(imp, m, imp_column) / value(full, m, full_column) for m in models
                  if value(imp, m, imp_column) is not None and value(full, m, full_column)]
        show("{} [{} models]".format(tool, len(shares)), median(shares), "{:.0f}", " %")

    section("Explicit Encodings in High-Level Languages")
    print("  (these numbers stem from a separate experiment with random models and are not computed here)")
