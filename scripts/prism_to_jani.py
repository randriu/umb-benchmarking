import os
import subprocess
import sys

if __name__ == "__main__":
    print("Converts the PRISM models to JANI using storm-conv. Usage:\n\tpython {} <storm-conv binary> <model directory>".format(sys.argv[0]))
    if len(sys.argv) != 3:
        print("Invalid number of arguments.")
        sys.exit(1)
    storm_conv, model_directory = [os.path.abspath(p) for p in sys.argv[1:3]]

    if not os.path.exists(storm_conv):
        print("Error: storm-conv binary '{}' not found.".format(storm_conv))
        sys.exit(1)

    errors = []
    for model in sorted(os.listdir(model_directory)):
        model_dir = os.path.join(model_directory, model)
        if not os.path.isdir(model_dir):
            continue
        prism_file = os.path.join(model_dir, "model.prism")
        props_file = os.path.join(model_dir, "property.props")
        if not (os.path.isfile(prism_file) and os.path.isfile(props_file)):
            errors.append("Error: model '{}' does not contain model.prism and property.props. Skipping.".format(model))
            print(errors[-1])
            continue
        jani_file = os.path.join(model_dir, "model.jani")
        print("Converting {} ...".format(model), flush=True)
        # --prismcompat is needed for CTMCs
        cmd = [storm_conv, "--prism", prism_file, "--prismcompat", "--prop", props_file, "--tojani", jani_file]
        if model == "oscillators.8-10-0.1-1-0.1-1.0":
            cmd.append("--compactjson") # exception for very large jani file
        ret = subprocess.run(cmd).returncode
        if ret != 0:
            errors.append("Error: storm-conv failed for {} (return code {}).".format(model, ret))
            print(errors[-1])
    if len(errors) > 0:
        print("Errors:\n{}".format("\n".join(errors)))
        sys.exit(1)
