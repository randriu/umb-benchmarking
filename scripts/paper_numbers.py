import os
import sys
import csv
import statistics

# Recomputes the numbers quoted in the experiments section of the paper from the *_median.csv files.
# Conventions (as in the paper): a "median factor" is the median over all models for which both values exist;
# times below 0.1 seconds are counted as 0.1 seconds (but not for "largest factor" and file sizes).

def load(csv_dir, name):
    with open(os.path.join(csv_dir, name + "_median.csv"), newline="") as f:
        rows = list(csv.reader(f, delimiter="\t"))
    return {row[0]: dict(zip(rows[0][1:], row[1:])) for row in rows[1:]}

def value(table, model, column):
    try:
        x = float(table[model][column])
    except (KeyError, ValueError):
        return None
    return None if x != x else x  # nan -> None

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
        result[model] = a / b
    return result

def report(label, values, fmt="{:.2f}"):
    print("{:<48} {}".format(label, fmt.format(values) if values is not None else "n/a"))

def median_factor(label, table, numerator, denominator, floor=True):
    f = factors(table, numerator, denominator, floor)
    report("{} (n={})".format(label, len(f)), statistics.median(f.values()) if f else None)

if __name__ == "__main__":
    print("Prints the numbers quoted in the paper. Usage:\n\tpython {} <csv directory> <models directory>".format(sys.argv[0]))
    if len(sys.argv) != 3:
        print("Invalid number of arguments.")
        sys.exit(1)
    csv_dir, models_dir = sys.argv[1:3]
    imp, exp, size, full = (load(csv_dir, n) for n in ["import_time", "export_time", "export_size", "full_time"])
    S, M, P = "storm_from-jani_to-", "modest_from-jani_to-", "prism_from-prism_to-"

    print("\n## Models with a UMB import result")
    for tool, column in [("storm", "storm_from-umb_import_sparse"), ("mcsta", "modest_from-umb_import_default"), ("prism", "prism_from-umb_import_ex")]:
        report(tool, sum(1 for m in imp if value(imp, m, column) is not None), "{}")

    print("\n## Import time (median factor of loading UMB vs. ...)")
    median_factor("storm: JANI", imp, "storm_from-jani_import_sparse", "storm_from-umb_import_sparse")
    median_factor("storm: PRISM language", imp, "storm_from-prism_import_sparse", "storm_from-umb_import_sparse")
    median_factor("storm: DRN", imp, "storm_from-drn_import_sparse", "storm_from-umb_import_sparse")
    median_factor("storm: JANI (dd)", imp, "storm_from-jani_import_cudd", "storm_from-umb_import_sparse")
    median_factor("mcsta: JANI", imp, "modest_from-jani_import_default", "modest_from-umb_import_default")
    median_factor("prism: PRISM language", imp, "prism_from-prism_import_ex", "prism_from-umb_import_ex")
    median_factor("storm: UMB gz vs. UMB", imp, "storm_from-umb-gz_import_sparse", "storm_from-umb_import_sparse")
    median_factor("storm: UMB xz vs. UMB", imp, "storm_from-umb-xz_import_sparse", "storm_from-umb_import_sparse")
    for label, column in [("UMB", "storm_from-umb_import_sparse"), ("JANI", "storm_from-jani_import_sparse"), ("DRN", "storm_from-drn_import_sparse")]:
        report("storm: slowest import from " + label + " [s]", max(v for m in imp if (v := value(imp, m, column)) is not None), "{:.1f}")
    xz = "storm_from-umb-xz_import_sparse"
    for label, column in [("JANI", "storm_from-jani_import_sparse"), ("PRISM language", "storm_from-prism_import_sparse"), ("DRN", "storm_from-drn_import_sparse")]:
        slower = {m: round(value(imp, m, xz) / value(imp, m, column), 2) for m in imp
                  if value(imp, m, xz) is not None and value(imp, m, column) is not None and floor_time(value(imp, m, xz)) > floor_time(value(imp, m, column))}
        print("storm: models where XZ-UMB is slower than {}: {}".format(label, slower if slower else "none"))
    dd = factors(imp, "storm_from-jani_import_cudd", "storm_from-jani_import_sparse", floor=False)
    report("storm: models where JANI (dd) is faster than JANI", sum(1 for f in dd.values() if f < 1), "{} of " + str(len(dd)))

    print("\n## Export time (median factor of writing ... vs. UMB)")
    median_factor("storm: DRN", exp, S + "drn_sparse", S + "umb_sparse")
    median_factor("prism: TRA", exp, P + "tra_ex", P + "umb_ex")
    median_factor("mcsta: MRM", exp, M + "imca_default", M + "umb_default")
    median_factor("mcsta: AUT", exp, M + "aut_default", M + "umb_default")
    median_factor("storm: DRN gz vs. UMB gz", exp, S + "drn-gz_sparse", S + "umb-gz_sparse")
    median_factor("storm: DRN xz vs. UMB xz", exp, S + "drn-xz_sparse", S + "umb-xz_sparse")

    print("\n## File size (median factor)")
    median_factor("storm: DRN / UMB", size, S + "drn_sparse", S + "umb_sparse", False)
    median_factor("mcsta: AUT / UMB", size, M + "aut_default", M + "umb_default", False)
    median_factor("prism: TRA / UMB", size, P + "tra_ex", P + "umb_ex", False)
    median_factor("mcsta: MRM / UMB", size, M + "imca_default", M + "umb_default", False)
    median_factor("storm: UMB / UMB gz", size, S + "umb_sparse", S + "umb-gz_sparse", False)
    median_factor("storm: UMB / UMB xz", size, S + "umb_sparse", S + "umb-xz_sparse", False)
    median_factor("storm: DRN xz / UMB xz", size, S + "drn-xz_sparse", S + "umb-xz_sparse", False)
    bcg = "modest_bcgio_aut-to-bcg_default"
    if any(bcg in row for row in size.values()):
        median_factor("mcsta: UMB / BCG", size, M + "umb_default", bcg, False)
        median_factor("mcsta: BCG xz / UMB xz", size, "modest_bcgio_aut-to-bcg-xz_default", M + "umb-xz_default", False)
        both = factors(size, M + "umb-xz_default", bcg, False)
        report("mcsta: models where UMB xz < BCG", sum(1 for f in both.values() if f < 1), "{} of " + str(len(both)))
    else:
        print("(no bcgio columns in the csv files)")

    print("\n## Total time")
    for tool, high, umb in [("storm", "storm_from-jani_check_sparse", "storm_from-umb_check_sparse"),
                            ("mcsta", "modest_from-jani_check_default", "modest_from-umb_check_default"),
                            ("prism", "prism_from-prism_check_ex", "prism_from-umb_check_ex")]:
        f = factors(full, high, umb)
        if not f:
            print("{}: no data".format(tool))
            continue
        raw = factors(full, high, umb, floor=False)
        report("{}: median factor (n={})".format(tool, len(f)), statistics.median(f.values()))
        report("{}: total time at least halves".format(tool), sum(1 for x in f.values() if x >= 2), "{} of " + str(len(f)))
        report("{}: largest factor (no floor)".format(tool), max(raw.values()), "{:.0f}")
        slower = [(1 / x - 1) * 100 for x in f.values() if x < 1]
        report("{}: models where UMB is slower / max slowdown [%]".format(tool), max(slower) if slower else 0, str(len(slower)) + " / {:.1f}")
    print("\n## Share of the import time in the total time with the high-level input [%]")
    for tool, imp_col, full_col in [("storm", "storm_from-jani_import_sparse", "storm_from-jani_check_sparse"),
                                    ("mcsta", "modest_from-jani_import_default", "modest_from-jani_check_default"),
                                    ("prism", "prism_from-prism_import_ex", "prism_from-prism_check_ex")]:
        shares = [100 * value(imp, m, imp_col) / value(full, m, full_col) for m in imp
                  if value(imp, m, imp_col) is not None and value(full, m, full_col)]
        report("{} (n={})".format(tool, len(shares)), statistics.median(shares) if shares else None, "{:.1f}")

    print("\n## Size of the high-level models vs. UMB files written by storm")
    prism_sizes, jani_sizes, umb_sizes = [], [], []
    larger = []
    for model in sorted(os.listdir(models_dir)):
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
    report("median PRISM file [KiB] (all models)", statistics.median(prism_sizes) / kib, "{:.1f}")
    report("median JANI file [KiB] (all models)", statistics.median(jani_sizes) / kib, "{:.1f}")
    report("median UMB file [MiB] (n={})".format(len(umb_sizes)), statistics.median(umb_sizes) / mib, "{:.0f}")
    for model, p, j, u in larger:
        print("high-level file larger than UMB: {} (PRISM {:.1f} MiB, JANI {:.1f} MiB, UMB {:.1f} MiB)".format(model, p / mib, j / mib, u / mib))
