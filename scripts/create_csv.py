import os,sys
from collections import OrderedDict

IMPORT_TIME = "import_time"
EXPORT_TIME = "export_time"
EXPORT_SIZE = "export_size"
FULL_TIME = "full_time"

def is_number(value):
    try:
        float(value)
        return True
    except:
        return False

def save_csv(csv, name : str):
    CSV_SEPARATOR="\t"
    with open(name + ".csv", 'w') as csv_file:
        for line in csv:
            line_strs = []
            for cell in line:
                if isinstance(cell, list):
                    line_strs.append("[{}]".format(", ".join(str(y) for y in cell)))
                else:
                    line_strs.append(str(cell))
            csv_file.write(CSV_SEPARATOR.join(line_strs) + "\n")
    print("Saved results invocations to '{}'.".format(name + ".csv"))

def median_csv(csv, name : str):
    a = [csv[0]]  # header
    for row in csv[1:]:
        new_row = [row[0]]  # first column is the model name
        for entry in row[1:]:
            if not isinstance(entry, list):
                new_row.append("nan")
            else:
                values = [float(x) for x in entry if is_number(x)]
                if len(values) == 0:
                    new_row.append("nan")
                else:
                    values = sorted(values)
                    median = values[len(values) // 2] if len(values) % 2 == 1 else (values[len(values) // 2 - 1] + values[len(values) // 2]) / 2
                    new_row.append(median)
        a.append(new_row)
    save_csv(a, name + "_median")
    return a

def quantile_csv(csv, name : str):
    columns = [[] for _ in csv[0][1:]]
    for row in csv[1:]:
        for i, entry in enumerate(row[1:]):
            if entry == "" or entry == "nan":
                continue
            assert isinstance(entry, float), "Unexpected entry type: {}".format(entry)
            columns[i].append(entry)
    for column in columns:
        column.sort()
    output = [["n"] + csv[0][1:]]
    for n in range(len(csv) - 1):
        line = [n + 1]
        for m in range(len(columns)):
            if n >= len(columns[m]):
                line.append("")
            else:
                line.append(columns[m][n])
        output.append(line)
    save_csv(output, name + "_quantile")

def parse_float(text : str, before : str, after : str):
    start = text.find(before)
    if start == -1:
        return None
    start += len(before)
    end = text.find(after, start)
    if end == -1:
        return None
    value_str = text[start:end].strip()
    try:
        value = float(value_str)
        return value
    except:
        return None
def parse_float_or_zero(text : str, before : str, after : str):
    value = parse_float(text, before, after)
    if value is None:
        return 0.0
    return value

def is_bcgio_log(log : str):
    """ bcgio logs pretend to be modest logs (see aut_to_bcg.py). Either the command line in the log header or the
    output file names mention bcgio (old logs created by create_bcg_size_logs.py can have an empty command line). """
    return "bcgio" in log.split("Wallclock time:")[0] or "bcgio.model.bcg" in log

def is_timeout(log : str):
    return "Return code: None (timeout)" in log

def is_memout(log : str):
    messages = [
        "error: Out of memory.", # mcsta
        "java.lang.OutOfMemoryError: Java heap space", # prism
        "Return code: -9", # storm
        "Maximum memory exceeded.", #storm
        "std::bad_alloc" #storm
    ]
    return any(m in log for m in messages)

def is_not_supported(log : str):

    messages = [
        "Complex initial states specifications are not yet supported", # mcsta
        "Error: Syntax error" # prism
    ]
    return any(m in log for m in messages)

def is_input_file_not_found(log : str):
    # mcsta
    pos = log.find("##############################Output to stderr##############################\nFile \"")
    if pos != -1 and "not found" in log[pos:]:
        return True
    # bcgio
    if "Size of output file is 0 bytes" in log:
        return True
    if "File does not exist." in log and is_bcgio_log(log):
        return True
    # storm
    if "Unable to read from non-existing file " in log:
        return True
    pos = log.find("The given path '")
    if pos != -1 and "does not exist." in log[pos:log.find("\n",pos)]:
        return True
    if "Lzma library error:  No progress is possible." in log or "truncated gzip input" in log:
        return True
    # prism
    if "Error: Error importing from UMB: Could not open UMB file:" in log:
        return True
    pos = log.find("Error: File \"")
    if pos != -1 and "\" not found." in log[pos:log.find("\n",pos)]:
        return True
    pos = log.find("Parsing PRISM model file \"")
    if pos != -1 and "/property.props\"..." in log[pos:log.find("\n",pos)]:
        return True
    return False

def parse_walltime(log : str):
    return parse_float(log, "Wallclock time: ", " seconds")

def parse_prism_log(log : str, what : str):
    if what == FULL_TIME:
        if "Time for model checking" in log:
            return parse_walltime(log)
    if what == IMPORT_TIME:
        return parse_float(log, "Time for model construction: ", "seconds.")
    elif what == EXPORT_TIME:
        return parse_float(log, "Time for exporting: ", "seconds.")
    elif what == EXPORT_SIZE:
        if parse_prism_log(log, EXPORT_TIME) is None:
            return None
        sublog = log
        size = 0
        while "Size of output file is " in sublog:
            size += parse_float(sublog, "Size of output file is ", " bytes")
            sublog = sublog[sublog.find("Size of output file is ") + 1:]
        return size if size > 0 else None

def parse_modest_log(log : str, what : str):
    if what == FULL_TIME:
        pos1 = log.find("+ Property")
        if pos1 != -1 and log.find("Time", pos1) != -1:
            return parse_walltime(log)
    elif what == IMPORT_TIME:
        start_pos = log.find("State space")
        if start_pos == -1:
            return None
        sublog = log[start_pos:]
        sublog = sublog[:sublog.find("\n\n")]
        assert "Time" in sublog, "Unexpected modest log format: {}".format(log)
        importtime = parse_float_or_zero(sublog, "Time (exploration): ", " s")
        importtime += parse_float_or_zero(sublog, "Time (merging): ", " s")
        # importtime += parse_float_or_zero(sublog, "Time (decompress): ", " s")
        # importtime += parse_float_or_zero(sublog, "Time (validate): ", " s")
        importtime += parse_float_or_zero(sublog, "Time (load): ", " s")
        return importtime
    elif what == EXPORT_TIME:
        if is_bcgio_log(log):
            return ""
        start_pos = log.find("+ UMB export")
        if start_pos == -1:
            start_pos = log.find("+ Export to ")
        if start_pos == -1:
            return None
        sublog = log[start_pos:]
        exporttime = parse_float(sublog, "Time: ", " s")
        return exporttime
    elif what == EXPORT_SIZE:
        if parse_modest_log(log, EXPORT_TIME) is None:
            return None
        sublog = log
        size = 0
        while "Size of output file is " in sublog:
            size += parse_float(sublog, "Size of output file is ", " bytes")
            sublog = sublog[sublog.find("Size of output file is ") + 1:]
        return size if size > 0 else None


def parse_storm_log(log : str, what : str):
    jani_parsing = parse_float_or_zero(log, "Time for model input parsing: ", "s.\n")
    construction = parse_float(log, "Time for model construction: ", "s.\n")
    preprocessing = parse_float_or_zero(log, "Time for model preprocessing: ", "s.\n")
    export = parse_float(log, "Time for model export: ", "s.\n")
    if what == FULL_TIME:
        if "Time for model checking" in log:
            return parse_walltime(log)
    elif what == IMPORT_TIME:
        if construction is None or "(sparse)" not in log:
            return None
        else:
            return jani_parsing + construction + preprocessing
    elif what == EXPORT_TIME:
        return export
    elif what == EXPORT_SIZE:
        if parse_storm_log(log, EXPORT_TIME) is None:
            return None
        sublog = log
        size = 0
        while "Size of output file is " in sublog:
            size += parse_float(sublog, "Size of output file is ", " bytes")
            sublog = sublog[sublog.find("Size of output file is ") + 1:]
        return size if size > 0 else None

def create_csv(log_dir : str, what : str):
    row_headers = []
    column_headers = []
    contents = dict() # rows -> columns --> values
    for logfile in sorted(os.listdir(log_dir)):
        if not logfile.endswith(".log"):
            continue
        parts = logfile[:-4].split("_")
        if len(parts) != 6:
            print("Warning: unexpected log file name format: {}".format(logfile))
            continue
        tool = parts[0]
        src_format = parts[1]
        task = parts[2]
        cfg = parts[3]
        is_export_task = (task.startswith("to-") or task.startswith("aut-to-bcg"))
        if what in [IMPORT_TIME, FULL_TIME] and is_export_task:
            continue
        if what == FULL_TIME and task == "import":
            continue
        if what in [EXPORT_TIME, EXPORT_SIZE] and not is_export_task:
            continue
        column = "_".join(parts[0:4])
        row = parts[4]
        rep = int(parts[5].replace("rep", "")) - 1
        if row not in row_headers:
            row_headers.append(row)
        if column not in column_headers:
            column_headers.append(column)
        if row not in contents:
            contents[row] = dict()
        if column not in contents[row]:
            contents[row][column] = []
        while len(contents[row][column]) <= rep:
            contents[row][column].append("")
        with open(os.path.join(log_dir, logfile), "r") as f:
            log_content = f.read()
        if tool == "storm":
            value = parse_storm_log(log_content, what)
        elif tool == "prism":
            value = parse_prism_log(log_content, what)
        elif tool == "modest":
            value = parse_modest_log(log_content, what)
        else:
            raise AssertionError("Unexpected tool: {}".format(tool))
        if value is None:
            if is_timeout(log_content):
                contents[row][column][rep] = "TO"
            elif is_memout(log_content):
                contents[row][column][rep] = "MO"
            elif is_input_file_not_found(log_content):
                contents[row][column][rep] = ""
            elif is_not_supported(log_content):
                contents[row][column][rep] = "NS"
            else:
                contents[row][column][rep] = "ERR"
        else:
            contents[row][column][rep] = value
    column_headers.sort()
    row_headers.sort()
    csv_lines = [["Model"] + column_headers]
    for row in row_headers:
        line = [row]
        for column in column_headers:
            if row in contents and column in contents[row]:
                line.append(contents[row][column])
            else:
                line.append("")
        csv_lines.append(line)
    return csv_lines

if __name__ == "__main__":
    print("Creates csv files from logs. Usage:\n\tpython {} <log directory>".format(sys.argv[0]))
    if len(sys.argv) != 2:
        print("Invalid number of arguments.")
        sys.exit(1)
    log_dir = sys.argv[1]

    # raw data
    import_csv = create_csv(log_dir, IMPORT_TIME)
    save_csv(import_csv, IMPORT_TIME)
    imp_t = median_csv(import_csv, IMPORT_TIME)
    full_csv = create_csv(log_dir, FULL_TIME)
    save_csv(full_csv, FULL_TIME)
    full_t = median_csv(full_csv, FULL_TIME)
    export_csv = create_csv(log_dir, EXPORT_TIME)
    save_csv(export_csv, EXPORT_TIME)
    exp_t = median_csv(export_csv, EXPORT_TIME)
    size_csv = create_csv(log_dir, EXPORT_SIZE)
    save_csv(size_csv, EXPORT_SIZE)
    size = median_csv(size_csv, EXPORT_SIZE)

    # quantile
    quantile_csv(imp_t, IMPORT_TIME)
    quantile_csv(full_t, FULL_TIME)
    quantile_csv(exp_t, EXPORT_TIME)
    quantile_csv(size, EXPORT_SIZE)

