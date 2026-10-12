import os,sys,shutil
import tarfile

if __name__ == "__main__":
    print("Copies generated files to the models folder. Usage:\n\tpython {} <output directory> <model directory>".format(sys.argv[0]))
    if len(sys.argv) != 3:
        print("Invalid number of arguments.")
        sys.exit(1)

    file_dir = sys.argv[1]
    model_dir = sys.argv[2]
    cfgs_prioritized = [
        "bcgio_from-aut_to-bcg_default",
        "modest_from-jani_to-aut_default",
        "modest_from-jani_to-imca_default",
        "modest_from-jani_to-umb_default",
        "modest_from-jani_to-umb_memory",
        "modest_from-jani_to-umb-gz_default",
        "modest_from-jani_to-umb-xz_default",
        "prism_from-prism_to-tra_ex",
        "prism_from-prism_to-tra-gz_ex",
        "prism_from-prism_to-tra-xz_ex",
        "prism_from-prism_to-tra_default",
        "prism_from-prism_to-umb_ex",
        "prism_from-prism_to-umb_default",
        "prism_from-prism_to-umb-gz_ex",
        "prism_from-prism_to-umb-xz_ex",
        "prism_from-prism_to-umb-gz_default",
        "prism_from-prism_to-tra_norewards",
        "prism_from-prism_to-umb-gz_norewards",
        "prism_from-prism_to-umb_norewards",
        "storm_from-jani_to-drn_sparse",
        "storm_from-jani_to-drn_cudd",
        "storm_from-jani_to-drn_exact",
        "storm_from-jani_to-drn-gz_sparse",
        "storm_from-jani_to-drn-gz_cudd",
        "storm_from-jani_to-drn-gz_exact",
        "storm_from-jani_to-drn-xz_sparse",
        "storm_from-jani_to-drn-xz_cudd",
        "storm_from-jani_to-drn-xz_exact",
        "storm_from-jani_to-umb_sparse",
        "storm_from-jani_to-umb_cudd",
        "storm_from-jani_to-umb_exact",
        "storm_from-jani_to-umb-gz_sparse",
        "storm_from-jani_to-umb-gz_cudd",
        "storm_from-jani_to-umb-gz_exact",
        "storm_from-jani_to-umb-xz_sparse",
        "storm_from-jani_to-umb-xz_cudd",
        "storm_from-jani_to-umb-xz_exact",
        "storm_from-prism_to-jani_sparse"
    ]
    for cfg in os.listdir(file_dir):
        if cfg not in cfgs_prioritized and "_none_" not in cfg:
            print("ERROR: unexpected configuration folder {}".format(cfg))
            exit(-1)
    cfgs = []
    for cfg in cfgs_prioritized:
        if cfg in os.listdir(file_dir):
            print("Found config folder {}".format(cfg))
            cfgs.append(cfg)

    def file_exists(path):
        return os.path.exists(path) and (os.path.isdir(path) or os.path.getsize(path) > 0)


    for model in os.listdir(model_dir):
        for cfg in cfgs:
            tool = cfg.split("_")[0]
            source_path = os.path.join(file_dir, cfg, model)
            for file_name in ["model.umb", "model.umb.xz", "model.umb.gz", "model.exact.umb", "model.exact.umb.xz", "model.exact.umb.gz",
                              "model.drn", "model.drn.xz", "model.drn.gz", "model.exact.drn", "model.exact.drn.xz", "model.exact.drn.gz",
                              "model.pexp", "model.pexp.xz", "model.pexp.gz",
                              "model.umbgz", "model.umbxz",
                              "model.tra",
                              "umb.properties.txt", "umbxz.properties.txt", "umbgz.properties.txt",
                              "model.aut", "model.mrm",
                              "model.jani"]:
                file_path = os.path.join(source_path, file_name)
                if file_exists(file_path):
                    if file_name == "model.tra":
                        file_name = "model.tradir"
                    dest_path = os.path.join(model_dir, model, tool + "." + file_name)
                    if not file_exists(dest_path):
                        if file_name == "model.tradir":
                            print("Creating tra directory for {} in {}".format(file_path, dest_path))
                            os.makedirs(dest_path, exist_ok=True)
                            shutil.copyfile(file_path, os.path.join(dest_path, "model.tra"))
                            shutil.copyfile(file_path[:-3] + "lab", os.path.join(dest_path, "model.lab"))
                            if file_exists(file_path[:-3] + "srew"):
                                shutil.copyfile(file_path[:-3] + "srew", os.path.join(dest_path, "model.srew"))
                            if file_exists(file_path[:-3] + "trew"):
                                shutil.copyfile(file_path[:-3] + "trew", os.path.join(dest_path, "model.trew"))
                        else:
                            print("Copying {} to {}".format(file_path, dest_path))
                            shutil.copyfile(file_path, dest_path)
