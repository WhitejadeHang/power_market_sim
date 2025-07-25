import sys
import argparse
import subprocess
import os
from pprint import pprint
from simpower.config import parse_command_line_config, scheduler_config, user_config


def main():
    """
    a wrapper to make the simpower script work with cluster schedulers
    or with an ssh call that you start on your laptop and then close the
    connection.
    """

    default_simpower_config = dict(user_config).copy()
    parser = argparse.ArgumentParser(
        description="Simpower scheduler command line interface"
    )

    parser.add_argument(
        "--scheduler_mode",
        default=scheduler_config.scheduler_mode,
        choices=["qsub", "nohup", "pass"],
        help="""Mode of scheduler operation:
        qsub: use the qsub cluster scheduler
        nohup: use nohup, call as subprocess, and redirect stdin, stderr
        pass: just call simpower as a child process (for debugging)
        """,
    )
    parser.add_argument(
        "--verbose", action="store_true", default=scheduler_config.verbose
    )
    parser.add_argument(
        "--dry_run", action="store_true", help="just show, don't do", default=False
    )

    qsub_opts = parser.add_argument_group(
        "qsub options", description="the following options only apply if using qsub"
    )
    qsub_opts.add_argument(
        "--email",
        default=scheduler_config.email,
        help="email on scheduler job completion",
    )
    qsub_opts.add_argument(
        "--memory",
        type=int,
        default=scheduler_config.memory,
        help="gigabytes of memory to limit job to",
    )
    qsub_opts.add_argument(
        "--hours_limit",
        type=int,
        default=scheduler_config.hours_limit,
        help="hours of runtime to limit job to",
    )

    args, simpower_args_raw = parser.parse_known_args()

    simpower_parser = argparse.ArgumentParser("simpower")
    simpower_args = parse_command_line_config(
        simpower_parser, preparsed_args=simpower_args_raw
    )

    # scheduler config can be loaded from the case directory
    parser.set_defaults(**dict(scheduler_config))
    args, __ = parser.parse_known_args()

    # subprocess style
    simpower_args["standalone"] = True
    simpower_args["pid"] = simpower_args["pid"] if simpower_args["pid"] else os.getpid()

    if args.scheduler_mode == "qsub":
        # qsub makes all of its script calls from the home directory
        # so it requires an absolute path
        simpower_args["directory"] = os.path.abspath(simpower_args["directory"])

        if (
            "scenarios_directory" in simpower_args
            and simpower_args["scenarios_directory"]
        ):
            simpower_args["scenarios_directory"] = os.path.abspath(
                simpower_args["scenarios_directory"]
            )

    if args.verbose:
        pprint(simpower_args)

    scheduler_call = []
    simpower_call = ["simpower"]
    stdout = sys.stdout
    stderr = subprocess.STDOUT

    def arg2str(k, v):
        if k == "directory":
            s = v
        elif v == True:
            s = "--{k}".format(k=k)
        else:
            s = "--{k}={v}".format(k=k, v=v)
        return s

    # make a big chain of args
    simpower_call.extend(
        sorted(
            [
                arg2str(k, v)
                for k, v in list(simpower_args.items())
                if (k == "directory")
                or (
                    (k in default_simpower_config) and (v != default_simpower_config[k])
                )
            ]
        )
    )

    mode = args.scheduler_mode
    if mode == "pass":
        # just let all the commands pass through
        pass
    elif mode == "nohup":
        scheduler_call = ["nohup"]
        if args.dry_run:
            print(
                (
                    "would have opened files to write"
                    + "\n\tstdout: {p}.out\n\tstderr: {p}.err".format(p=os.getpid())
                )
            )
        else:
            stdout = open("{}.out".format(os.getpid()), "w")
            stderr = open("{}.err".format(os.getpid()), "w")
    elif mode == "qsub":
        # see https://sig.washington.edu/itsigs/Hyak_Job_Scheduler
        # default walltime limit is only one hour - must set this
        scheduler_call = [
            "qsub",
            "-l nodes=1:ppn=12,feature=12core,mem={m}gb,walltime={h}:00:00".format(
                m=args.memory, h=args.hours_limit
            ),
        ]

        if args.email:
            scheduler_call.extend(
                ["-m ae", "-M {e}".format(e=args.email)]  # mail on completion/failure
            )

        # need to write a script to disk to call with qsub
        if simpower_args["standalone_restart"]:
            # write to the same script, but comment out the original call
            script_name = "./{}.sh".format(simpower_args["pid"])
            if args.dry_run:
                print(
                    (
                        "would have commented out the original call in {}".format(
                            script_name
                        )
                    )
                )
            else:
                with open(script_name, "r") as f:
                    old_script = "\n".join(
                        ["# original call"]
                        + ["#" + ln for ln in f.readlines()]
                        + ["", ""]
                    )
                with open(script_name, "w") as f:
                    f.write(old_script)
            script_mode = "a"
        else:
            script_name = "./{}.sh".format(os.getpid())
            script_mode = "w+"
        if args.dry_run:
            print(
                (
                    "would have written script {f}: \n{c}".format(
                        f=script_name, c=" ".join(simpower_call)
                    )
                )
            )
        else:
            with open(script_name, script_mode) as f:
                f.write(" ".join(simpower_call))
        simpower_call = [script_name]

    # actually make the call
    if args.dry_run:
        print(
            (
                "would have executed as a {p}:\n{c}".format(
                    p="child process" if mode == "pass" else "subprocess",
                    c=" ".join((scheduler_call + simpower_call)),
                )
            )
        )
    else:
        if mode == "pass":
            subprocess.call(scheduler_call + simpower_call)
            pid = None
        else:

            pid = subprocess.Popen(
                scheduler_call + simpower_call,
                stdout=stdout,
                stderr=stderr,
            ).pid

    if args.verbose:
        print(("parent process {}".format(os.getpid())))
        print(("starting run {}".format(pid)))


if __name__ == "__main__":
    main()
