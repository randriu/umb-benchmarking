import os, sys, subprocess, threading, time, signal, json, traceback, shutil
from collections import OrderedDict
from datetime import datetime
from tempfile import TemporaryDirectory

def load_json(path : str):
    with open(path, 'r', encoding='utf-8-sig') as json_file:
        return json.load(json_file, object_pairs_hook=OrderedDict)

def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

class CommandExecution(object):
    """ Represents the execution of a single command line argument. """
    def __init__(self):
        self.is_aborted = None
        self.return_code = None
        self.output = None
        self.wall_time = None
        self.proc = None

    def abort(self):
        self.is_aborted = True
        sys.stdout.write("sending termination request... ")
        sys.stdout.flush()
        try:
            os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM) # Send the signal to all the process groups
        except ProcessLookupError:
            pass

    def send_sigkill(self):
        sys.stdout.write("killing process... ")
        sys.stdout.flush()
        try:
            os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL) # Send the signal to all the process groups
        except ProcessLookupError:
            pass
            

    def run(self, command_line, time_limit):
        # We need to make sure that the process and all its childs are killed properly. Therefore, work with processgroups
        # From https://stackoverflow.com/a/4791612
        # The os.setsid() is passed in the argument preexec_fn so
        # it's run after the fork() and before  exec() to run the shell.
        self.proc = subprocess.Popen(command_line.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)
        start_time = time.time()
        self.is_aborted = False
        self.output = ""
        timers = []
        if time_limit is not None: # no time limit if None
            timers.append(threading.Timer(time_limit, self.abort))
            timers.append(threading.Timer(time_limit + 60, self.send_sigkill)) # give the program 60 seconds to terminate by itself, send SIGKILL afterwards
        for timer in timers:
            timer.start()
        try:
            stdout, stderr = self.proc.communicate()
        except KeyboardInterrupt:
            stdout = None
            stderr = None
            self.output += "Execution aborted after {:.2f} seconds.\n".format(time.time() - start_time)
            self.is_aborted = True
            sys.stdout.write("aborting after {:.2f} seconds ...".format(time.time() - start_time))
            sys.stdout.flush()
            # give the user time for another interrupt
            time.sleep(2)
        except Exception as e:
            self.output = self.output + "Error when executing the command:\n{}\n".format(e)
        finally:
            for timer in timers:
                timer.cancel()
            self.wall_time = time.time() - start_time
            self.return_code = self.proc.returncode
        if stdout is not None:
            self.output = self.output + stdout.decode('utf8')
        if stderr is not None and len(stderr) > 0:
            self.output = self.output + "\n" + "#"*30 + "Output to stderr" + "#"*30 + "\n" + stderr.decode('utf8')
        if self.is_aborted and time_limit is not None and self.wall_time <= time_limit:
            print("WARN: Execution was aborted. The measured time is {} seconds which is still below the time limit of {} seconds".format(self.wall_time, time_limit))

def execute_command_lines(command_lines, time_limits):
    """
    Executes the given command lines with the given time limits (in seconds).
    :returns the output of the command (including the output to stderr, if present), the runtime of the command and either the return code or None (in case of a time_limit)
    """
    assert len(command_lines) == len(time_limits), "Number of command lines and time limits must be the same."
    output = ""
    walltime = 0.0
    for command_line_str, time_limit in zip(command_lines, time_limits):
        execution = CommandExecution()
        execution.run(command_line_str, time_limit)
        if execution.output is not None and execution.output != "":
            output += execution.output + ("" if execution.output.endswith("\n") else "\n")
        if execution.wall_time is not None:
            walltime += execution.wall_time
        if execution.is_aborted:
            return output, walltime, None
        if execution.return_code is not None and execution.return_code != 0:
            return output, walltime, execution.return_code
    return output, walltime, 0

def run_invocation(inv : json, overwrite_time_limit = None):
    commands = inv["commands"]
    time_limits = [overwrite_time_limit if overwrite_time_limit is not None else inv.get("time-limit")] * len(commands) # None = no time limit
    tmp_indir = TemporaryDirectory(suffix=inv["id"] + "_tmp_indir_", ignore_cleanup_errors=True)
    tmp_outdir = TemporaryDirectory(suffix=inv["id"] + "_tmp_outdir_", ignore_cleanup_errors=True)
    log = ""
    for infile in inv["input-files"]:
        infile_path = os.path.join(inv["input-directory"], infile)
        if os.path.exists(infile_path):
            shutil.copy(infile_path, os.path.join(tmp_indir.name, infile))
    tmp_commands = [c.replace("%indir", tmp_indir.name).replace("%outdir", tmp_outdir.name) for c in commands]
    output, walltime, ret = execute_command_lines(tmp_commands, time_limits)
    log += "Command(s):\n{}\nWallclock time: {:.3f} seconds\nReturn code: {}{}\n".format("\n".join(commands), walltime, ret, " (timeout)" if ret is None else "")
    log += "#"*30 + "\n" + output
    if "output-files" in inv:
        log += "\n" + "#"*30 + " Output files " + "#"*30 + "\n"
        for outfile in inv["output-files"]:
            log += f"{outfile}:\t"
            if os.path.exists(os.path.join(tmp_outdir.name, outfile)):
                log += "Size of output file is {} bytes\n".format(os.path.getsize(os.path.join(tmp_outdir.name, outfile)))
                if inv["repetition"] == 1:
                    # copy output file to non-temp directory for the first repetition
                    shutil.copy(os.path.join(tmp_outdir.name, outfile), os.path.join(inv["output-directory"], outfile))
            else:
                log += "File does not exist.\n"
    # save logfile
    with open(os.path.join(inv["log-dir"], inv["log"]), 'w', encoding="utf-8") as logfile:
        logfile.write(log)
    return "done ({:.1f}s)".format(walltime) if ret == 0 else ("timeout" if ret is None else "error ({})".format(ret))

def run_invocations(invs, indices, overwrite_time_limit = None):
    """ Runs the invocations with the given indices one after another and prints a status line for each. """
    print(f"{now()} - Beginning execution of {len(indices)} invocations...")
    for i in indices:
        inv = invs[i]
        sys.stdout.write("{} - Executing invocation #{:2d}{}: {} ... ".format(now(), i, "/{}".format(len(indices)-1) if len(indices) > 1 else "", inv["id"]))
        sys.stdout.flush()
        status = ""
        try:
            status = run_invocation(inv, overwrite_time_limit)
        except KeyboardInterrupt as e:
            print("\n{} - Interrupt while processing invocation #{}: {}\n".format(now(),i, inv['id']))
            print("Continuing in 5 seconds")
            time.sleep(5)
        except Exception:
            print("\n{} - ERROR while processing invocation #{}: {}".format(now(),i, inv['id']))
            traceback.print_exc()
        print(status)
    print(f"{now()} - Finished execution of invocations.")

if __name__ == "__main__":
    print("runs invocation files. Usage:\n\tpython {} <invocation json file> <index>|all [<overwrite_time_limit>]".format(sys.argv[0]))
    if len(sys.argv) not in [3,4]:
        print("Invalid number of arguments.")
        sys.exit(1)
    invs = load_json(sys.argv[1])
    print("Loaded invocations file with {} invocations.".format(len(invs)))
    indices = [int(sys.argv[2])] if sys.argv[2] != "all" else range(len(invs))
    overwrite_time_limit = None
    if len(sys.argv) == 4:
        overwrite_time_limit = int(sys.argv[3])
        print(f"Overwriting time limit to {overwrite_time_limit} seconds.")
    run_invocations(invs, indices, overwrite_time_limit)
