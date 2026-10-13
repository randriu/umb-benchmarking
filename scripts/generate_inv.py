import os
import sys
import json
from collections import OrderedDict
import random

def save_invjson(inv_json : json, repetitions : int, path : str):
    output = []
    for i in inv_json:
        for r in range(repetitions):
            inv_copy = i.copy()
            inv_copy["log"] = f"{i['id']}_rep{r+1}.log"
            inv_copy["repetition"] = r + 1
            output.append(inv_copy)
    # shuffle output to avoid any ordering effects
    random.seed(55) # fixed seed for reproducibility
    random.shuffle(output)
    with open(path, 'w') as json_file:
        json.dump(output, json_file, ensure_ascii=False, indent='\t')
    print("Saved {} invocations to '{}'.".format(len(output), path))

def ensure_directory(path : str):
    if not os.path.exists(path):
        os.makedirs(path)

# File formats
PRISM_LANGUAGE = "prism"
JANI = "jani"
UMB = "umb"
UMB_XZ = "umb-xz"
UMB_GZ = "umb-gz"
DRN = "drn"
DRN_XZ = "drn-xz"
DRN_GZ = "drn-gz"
TRA = "tra"
TRA_XZ = "tra-xz"
TRA_GZ = "tra-gz"
AUT = "aut"
IMCA = "imca"

# tasks
TASK_CHECK = "check"
TASK_IMPORT = "import"

# Command template placeholders (if one of these is a prefix of another, special care is needed because the order of replacement matters):
# %modest = path to modest binary
# %prism = path to prism binary
# %storm = path to storm binary
# %indir = path to model directory
# %outdir = path to output directory

# Modest
MODEST = "modest"
modest_configurations = OrderedDict()
modest_configurations["default"] = ""
# modest_configurations["unsafe"] = "--unsafe"
# modest_configurations["memory"] = "-S Memory"
# modest_configurations["unsafe-memory"] = "--unsafe -S Memory"

MODEST_INPUT_FORMATS = [JANI, UMB, UMB_XZ, UMB_GZ]
MODEST_OUTPUT_FORMATS = [UMB, UMB_XZ, UMB_GZ, AUT, IMCA]

def modest_command(input_format : str, task : str, configuration : str) -> str:
    cmd = "%modest mcsta"
    # input
    if input_format == JANI:
        cmd += " %indir/model.jani"
    elif input_format == UMB:
        cmd += " %indir/modest.model.umb %indir/modest.umb.properties.txt"
    elif input_format == UMB_XZ:
        cmd += " %indir/modest.model.umb.xz %indir/modest.umbxz.properties.txt -I UMB"
    elif input_format == UMB_GZ:
        cmd += " %indir/modest.model.umb.gz %indir/modest.umbgz.properties.txt -I UMB"
    else:
        raise AssertionError("Unsupported input format: " + input_format)
    # task / output
    if task == TASK_CHECK:
        cmd += ""
    elif task == TASK_IMPORT:
        cmd += " --stop-after Exploration"
    elif task == UMB:
        cmd += " --umb %outdir/model.umb %outdir/umb.properties.txt --stop-after Exploration"
    elif task == UMB_XZ:
        cmd += " --umb %outdir/model.umb.xz %outdir/umbxz.properties.txt --umb-compress XZ --stop-after Exploration"
    elif task == UMB_GZ:
        cmd += " --umb %outdir/model.umb.gz %outdir/umbgz.properties.txt --umb-compress GZIP --stop-after Exploration"
    elif task == AUT:
        cmd += " --statespace %outdir/model.aut AUT --stop-after Exploration"
    elif task == IMCA:
        cmd += " --statespace %outdir/model.mrm IMCA --stop-after Exploration"
    else:
        raise AssertionError("Unsupported task/output format: " + task)
    # configuration
    assert configuration in modest_configurations, "Unknown Modest configuration: " + configuration
    cmd += " " + modest_configurations[configuration] + " -D -Y --exhaustive" # -D for detailed output, -Y for overwriting output
    return cmd

# PRISM
PRISM = "prism"
prism_configurations = OrderedDict()
prism_configurations["ex"] = "-javamaxmem 32g -buildall -ex"

PRISM_INPUT_FORMATS = [PRISM_LANGUAGE, UMB, UMB_GZ, UMB_XZ, TRA, TRA_GZ, TRA_XZ]
PRISM_OUTPUT_FORMATS = [UMB, UMB_GZ, UMB_XZ, TRA, TRA_GZ, TRA_XZ]

# Workaround: PRISM strips the .gz/.xz extension from compressed UMB files (out.umb.gz becomes out.umb),
# so compressed UMB files are named model.umbgz / model.umbxz instead.
def prism_command(input_format : str, task : str, configuration : str) -> str:
    cmd = "%prism"
    # configuration
    assert configuration in prism_configurations, "Unknown Prism configuration: " + configuration
    cmd += " " + prism_configurations[configuration]

    # input
    if input_format == PRISM_LANGUAGE:
        cmd += " %indir/model.prism"
    elif input_format == UMB:
        cmd += " -importmodel %indir/prism.model.umb"
    elif input_format == UMB_GZ:
        cmd += " -importmodel %indir/prism.model.umbgz:format=umb"
    elif input_format == UMB_XZ:
        cmd += " -importmodel %indir/prism.model.umbxz:format=umb"
    elif input_format == TRA:
        cmd += f" -importmodel %indir/prism.model.pexp"
    elif input_format == TRA_GZ:
        cmd += f" -importmodel %indir/prism.model.pexp.gz:format=explicit"
    elif input_format == TRA_XZ:
        cmd += f" -importmodel %indir/prism.model.pexp.xz:format=explicit"
    else:
        raise AssertionError("Unsupported input format for PRISM: " + input_format)
    # task / output
    if task == TASK_IMPORT:
        pass # nothing to add
    elif task == TASK_CHECK:
        cmd += " %indir/property.props"
    elif task == UMB:
        cmd += f" -exportmodel %outdir/model.umb:format=umb,states=false,zip=false"
    elif task == UMB_GZ:
        cmd += f" -exportmodel %outdir/model.umbgz:format=umb,states=false,zip=gzip"
    elif task == UMB_XZ:
        cmd += f" -exportmodel %outdir/model.umbxz:format=umb,states=false,zip=xz"
    elif task == TRA:
        cmd += f" -exportmodel %outdir/model.pexp:format=explicit,states=false,zip=false,precision=17"
    elif task == TRA_GZ:
        cmd += f" -exportmodel %outdir/model.pexp.gz:format=explicit,states=false,zip=gzip,precision=17"
    elif task == TRA_XZ:
        cmd += f" -exportmodel %outdir/model.pexp.xz:format=explicit,states=false,zip=xz,precision=17"
    else:
        raise AssertionError("Unsupported task/output format: " + task)
    return cmd

# Storm
STORM = "storm"
storm_configurations = OrderedDict()
storm_configurations["sparse"] = ""
# storm_configurations["exact"] = "--exact"
storm_configurations["cudd"] = "--engine dd-to-sparse --ddlib cudd --cudd:maxmem 8192"

STORM_INPUT_FORMATS = [PRISM_LANGUAGE, JANI, UMB, UMB_XZ, UMB_GZ, DRN, DRN_XZ, DRN_GZ]
STORM_OUTPUT_FORMATS = [UMB, UMB_XZ, UMB_GZ, DRN, DRN_XZ, DRN_GZ]

def storm_command(input_format : str, task : str, configuration : str) -> str:
    cmd = "%storm "
    # other options
    cmd += "--timemem --buildfull " # additional time and memory output, build full model exhaustively
    exact = ".exact" if configuration == "exact" else ""
    # input
    if input_format == PRISM_LANGUAGE:
        cmd += "--prism %indir/model.prism --prismcompat " # --prismcompat option for CTMC
    elif input_format == JANI:
        cmd += "--jani %indir/model.jani "
    elif input_format == UMB:
        cmd += f"--explicit-umb %indir/storm.model{exact}.umb "
    elif input_format == UMB_XZ:
        cmd += f"--explicit-umb %indir/storm.model{exact}.umb.xz "
    elif input_format == UMB_GZ:
        cmd += f"--explicit-umb %indir/storm.model{exact}.umb.gz "
    elif input_format == DRN:
        cmd += f"--explicit-drn %indir/storm.model{exact}.drn --digits 17 "
    elif input_format == DRN_XZ:
        cmd += f"--explicit-drn %indir/storm.model{exact}.drn.xz --digits 17 "
    elif input_format == DRN_GZ:
        cmd += f"--explicit-drn %indir/storm.model{exact}.drn.gz --digits 17 "
    else:
        raise AssertionError("Unsupported input format: " + input_format)

    # task / output
    if task == TASK_IMPORT:
        pass # nothing to add
    elif task == TASK_CHECK:
        if input_format == JANI:
            cmd += "--janiproperty "
        else:
            cmd += "--prop %indir/property.props"
    elif task == UMB:
        cmd += f"--exportbuild %outdir/model{exact}.umb umb --compression none "
    elif task == UMB_XZ:
        cmd += f"--exportbuild %outdir/model{exact}.umb.xz umb --compression xz "
    elif task == UMB_GZ:
        cmd += f"--exportbuild %outdir/model{exact}.umb.gz umb --compression gzip "
    elif task == DRN:
        cmd += f"--exportbuild %outdir/model{exact}.drn drn --compression none "
    elif task == DRN_XZ:
        cmd += f"--exportbuild %outdir/model{exact}.drn.xz drn --compression xz "
    elif task == DRN_GZ:
        cmd += f"--exportbuild %outdir/model{exact}.drn.gz drn --compression gzip "
    else:
        raise AssertionError("Unsupported task/output format: " + task)
    # configuration
    assert configuration in storm_configurations, "Unknown Storm configuration: " + configuration
    cmd += " " + storm_configurations[configuration]
    return cmd


if __name__ == "__main__":
    print("Creates invocation files in the current working directory. Usage:\n\tpython {} <bin directory> <model directory> <output directory> <logs directory> <time limit in seconds> <repititions>".format(sys.argv[0]))
    if len(sys.argv) != 7:
        print("Invalid number of arguments.")
        sys.exit(1)

    # read settings and ensure directories and executables exist
    bin_directory = sys.argv[1]
    input_directory = sys.argv[2]
    output_directory = sys.argv[3]
    logs_directory = sys.argv[4]
    time_limit = int(sys.argv[5])
    repetitions = int(sys.argv[6])
    for dir_path in [input_directory, output_directory, logs_directory]:
        ensure_directory(dir_path)
    for tool in [STORM]:
        bin_path = os.path.join(bin_directory, tool)
        if not os.path.exists(bin_path):
            print("Warning: {} binary '{}' not found.".format(tool, bin_path))

    # find models in input directory
    models = []
    for model in os.listdir(input_directory):
        model_input_dir = os.path.join(input_directory, model)
        if not os.path.isdir(model_input_dir): continue
        model_ok = True
        for filename in ["model.jani", "model.prism", "property.props"]:
            if not os.path.exists(os.path.join(model_input_dir, filename)):
                print("Warning: model '{}' does not contain a {} file. Skipping.".format(model, filename))
                model_ok = False
        if model_ok:
            # we use underscores as separators, so they are not allowed in model names
            assert "_" not in model, "Underscores are not allowed in model path names. Got: " + model
            models.append(model)
    print("Found {} models in input directory:\n\t{}".format(len(models), "\n\t".join(models)))

    def add_cmd_template(templates : OrderedDict,tool : str, input_format : str, task : str, configuration : str):
        for s in [tool, input_format, task, configuration]:
            # we use underscores as separators, so they are not allowed in identifiers
            assert "_" not in s, "Underscores are not allowed in template identifiers. Found in '" + s + "'."
        task_str = "no-task" if task == "" else (task if task in [TASK_CHECK, TASK_IMPORT] else "to-" + task)
        template_id = f"{tool}_from-{input_format}_{task_str}_{configuration}"
        if tool == MODEST:
            templates[template_id] = modest_command(input_format, task, configuration)
        elif tool == PRISM:
            templates[template_id] = prism_command(input_format, task, configuration)
        elif tool == STORM:
            templates[template_id] = storm_command(input_format, task, configuration)
        else:
            raise AssertionError("Unsupported tool: " + tool)
    def generate_invocations(cmd_templates):
        invocations = []
        for cmd_id in cmd_templates:
            print("Command template '{}':\n\t{}".format(cmd_id, cmd_templates[cmd_id]))
            for model in models:
                model_input_dir = os.path.join(input_directory, model)
                model_output_dir = os.path.join(output_directory, cmd_id, model)
                invocation_id = f"{cmd_id}_{model}"
                command = cmd_templates[cmd_id]
                # command = command.replace("%indir", model_input_dir)
                invocation = OrderedDict()
                invocation["id"] = invocation_id
                invocation["time-limit"] = time_limit
                invocation["log-dir"] = logs_directory
                invocation["log"] = f"{invocation_id}.log"
                if "%indir" in command:
                    invocation["input-directory"] = model_input_dir
                    infiles = []
                    for infilestring in command.split("%indir/")[1:]:
                        infilename = infilestring.split(" ")[0].split(":")[0]
                        if infilename.endswith(".all"):
                            infiles.append(infilename[:-3] + "tra")
                            infiles.append(infilename[:-3] + "lab")
                            infiles.append(infilename[:-3] + "srew")
                            infiles.append(infilename[:-3] + "trew")
                        else:
                            if infilename not in infiles: infiles.append(infilename)
                    invocation["input-files"] = infiles
                if "%outdir" in command:
                    ensure_directory(model_output_dir)
                    invocation["output-directory"] = model_output_dir
                    outfiles = []
                    for outfilestring in command.split("%outdir/")[1:]:
                        outfilename = outfilestring.split(" ")[0].split(":")[0]
                        if outfilename not in outfiles:
                            outfiles.append(outfilename)
                    invocation["output-files"] = outfiles
                    # command = command.replace("%outdir", model_output_dir)
                command = command.replace("%modest", os.path.join(bin_directory, MODEST))
                command = command.replace("%prism", os.path.join(bin_directory, PRISM))
                command = command.replace("%storm", os.path.join(bin_directory, STORM))
                invocation["commands"] = [c.strip() for c in command.split(";")]
                invocations.append(invocation)
        return invocations

    all_export = []
    all_import = []

    print("\n" + "#" * 40 + "\nGenerating Modest export invocations...\n" + "#" * 40)
    modest_exprt_templates = OrderedDict()
    for out_format in MODEST_OUTPUT_FORMATS:
        add_cmd_template(modest_exprt_templates, MODEST, JANI, out_format, "default")
    # for cfg in [ "memory" ]:
    #     for out_format in [UMB]:
    #         add_cmd_template(modest_exprt_templates, MODEST, JANI, out_format, cfg)

    modest_exprt_invs = generate_invocations(modest_exprt_templates)
    all_export += modest_exprt_invs

    print("\n" + "#" * 40 + "\nGenerating Modest import invocations...\n" + "#" * 40)
    modest_import_templates = OrderedDict()
    for in_format in MODEST_INPUT_FORMATS:
        for cfg in modest_configurations.keys():
            add_cmd_template(modest_import_templates, MODEST, in_format, TASK_IMPORT, cfg)
    add_cmd_template(modest_import_templates, MODEST, JANI, TASK_CHECK, "default")
    add_cmd_template(modest_import_templates, MODEST, UMB, TASK_CHECK, "default")
    modest_import_invs = generate_invocations(modest_import_templates)
    all_import += modest_import_invs

    print("\n" + "#" * 40 + "\nGenerating Prism export invocations...\n" + "#" * 40)
    prism_exprt_templates = OrderedDict()
    for out_format in PRISM_OUTPUT_FORMATS:
        for cfg in prism_configurations.keys():
            add_cmd_template(prism_exprt_templates, PRISM, PRISM_LANGUAGE, out_format, cfg)
    prism_exprt_invs = generate_invocations(prism_exprt_templates)
    all_export += prism_exprt_invs

    print("\n" + "#" * 40 + "\nGenerating Prism import invocations...\n" + "#" * 40)
    prism_import_templates = OrderedDict()
    for in_format in PRISM_INPUT_FORMATS:
        for cfg in prism_configurations.keys():
            add_cmd_template(prism_import_templates, PRISM, in_format, TASK_IMPORT, cfg)
    add_cmd_template(prism_import_templates, PRISM, PRISM_LANGUAGE, TASK_CHECK, "ex")
    add_cmd_template(prism_import_templates, PRISM, UMB, TASK_CHECK, "ex")
    prism_import_invs = generate_invocations(prism_import_templates)
    all_import += prism_import_invs

    print("\n" + "#" * 40 + "\nGenerating Storm export invocations...\n" + "#" * 40)
    storm_exprt_templates = OrderedDict()
    for out_format in STORM_OUTPUT_FORMATS:
        add_cmd_template(storm_exprt_templates, STORM, JANI, out_format, "sparse")
    storm_exprt_invs = generate_invocations(storm_exprt_templates)
    all_export += storm_exprt_invs

    print("\n" + "#" * 40 + "\nGenerating Storm import invocations...\n" + "#" * 40)
    storm_import_templates = OrderedDict()
    for in_format in STORM_INPUT_FORMATS:
        add_cmd_template(storm_import_templates, STORM, in_format, TASK_IMPORT, "sparse")
    add_cmd_template(storm_import_templates, STORM, JANI, TASK_CHECK, "sparse")
    add_cmd_template(storm_import_templates, STORM, UMB, TASK_CHECK, "sparse")
    add_cmd_template(storm_import_templates, STORM, JANI, TASK_IMPORT, "cudd")
    storm_import_invs = generate_invocations(storm_import_templates)
    all_import += storm_import_invs

    print("\n" + "#" * 40 + "\nSaving invocations to json...\n" + "#" * 40)
    save_invjson(modest_exprt_invs, repetitions, "inv_modest_export.json")
    save_invjson(modest_import_invs, repetitions, "inv_modest_import.json")
    save_invjson(prism_exprt_invs, repetitions, "inv_prism_export.json")
    save_invjson(prism_import_invs, repetitions, "inv_prism_import.json")
    save_invjson(storm_exprt_invs, repetitions, "inv_storm_export.json")
    save_invjson(storm_import_invs, repetitions, "inv_storm_import.json")
    save_invjson(all_export, repetitions, "inv_export.json")
    save_invjson(all_import, repetitions, "inv_import.json")
    save_invjson(all_export + all_import, repetitions, "inv_all.json")

