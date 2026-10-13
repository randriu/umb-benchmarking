import os
import sys
from collections import OrderedDict

from run import run_invocations

CONFIG_ID = "bcgio_from-aut_to-bcg_default"  # name of the output directory
# Log names have the form <tool>_<format>_<task>_<config>_<model>_rep<N>.log. The bcg logs pretend to be
# modest logs so that create_csv.py / create_html.py report their sizes next to the modest exports.
LOG_PREFIX = "modest_bcgio_"
BCG_FILE = "bcgio.model.bcg"
INPUT_FILE = "modest.model.aut"  # the aut file exported by modest (see copy_modelfiles.py)

# task name -> (additional command, output file whose size is reported)
TASKS = OrderedDict([
    ("aut-to-bcg", (None, BCG_FILE)),
    ("aut-to-bcg-xz", ("xz -k -f %outdir/" + BCG_FILE, BCG_FILE + ".xz")),
    ("aut-to-bcg-gz", ("gzip -k -f %outdir/" + BCG_FILE, BCG_FILE + ".gz")),
])

if __name__ == "__main__":
    print("Converts the aut files exported by modest to (compressed) bcg files using bcgio. Usage:\n\tpython {} <bcgio binary> <model directory> <output directory> <logs directory>".format(sys.argv[0]))
    if len(sys.argv) != 5:
        print("Invalid number of arguments.")
        sys.exit(1)
    bcgio, model_directory, output_directory, logs_directory = [os.path.abspath(p) for p in sys.argv[1:5]]

    if not os.path.exists(bcgio):
        print("Error: bcgio binary '{}' not found.".format(bcgio))
        sys.exit(1)
    os.makedirs(logs_directory, exist_ok=True)

    invocations = []
    for model in sorted(os.listdir(model_directory)):
        model_dir = os.path.join(model_directory, model)
        if not os.path.isdir(model_dir):
            continue
        if not os.path.exists(os.path.join(model_dir, INPUT_FILE)):
            print("Warning: model '{}' does not contain {}. Skipping.".format(model, INPUT_FILE))
            continue
        assert "_" not in model, "Underscores are not allowed in model path names. Got: " + model
        model_output_dir = os.path.join(output_directory, CONFIG_ID, model)
        os.makedirs(model_output_dir, exist_ok=True)
        for task, (compress_command, output_file) in TASKS.items():
            inv = OrderedDict()
            inv["id"] = "{}{}_default_{}".format(LOG_PREFIX, task, model)
            inv["log-dir"] = logs_directory
            inv["log"] = "{}_rep1.log".format(inv["id"])
            inv["input-directory"] = model_dir
            inv["input-files"] = [INPUT_FILE]
            inv["output-directory"] = model_output_dir
            inv["output-files"] = [output_file]
            inv["commands"] = ["{} %indir/{} %outdir/{}".format(bcgio, INPUT_FILE, BCG_FILE)]
            if compress_command is not None:
                inv["commands"].append(compress_command)
            inv["repetition"] = 1
            invocations.append(inv)

    run_invocations(invocations, range(len(invocations)))
