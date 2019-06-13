#!/usr/bin/env python
import datetime
import argparse
import os
import yaml

from kge import Dataset
from kge import Config
from kge.job import Job
from kge.util.misc import get_git_revision_short_hash, kge_base_dir


def argparse_bool_type(v):
    "Type for argparse that correctly treats Boolean values"
    if v.lower() in ("yes", "true", "t", "y", "1"):
        return True
    elif v.lower() in ("no", "false", "f", "n", "0"):
        return False
    else:
        raise argparse.ArgumentTypeError("Boolean value expected.")


def process_meta_command(args, meta_command, fixed_args):
    """Process&update program arguments for meta commands.

    `meta_command` is the name of a special command, which fixes all key-value arguments
    given in `fixed_args` to the specified value. `fxied_args` should contain key
    `command` (for the actual command being run).

    """
    if args.command == meta_command:
        for k, v in fixed_args.items():
            if k != "command" and vars(args)[k] and vars(args)[k] != v:
                raise ValueError(
                    "invalid argument for '{}' command: --{} {}".format(
                        meta_command, k, v
                    )
                )
            vars(args)[k] = v


if __name__ == "__main__":
    # default config
    config = Config()

    # define short option names
    short_options = {
        "dataset.name": "-d",
        "job.type": "-j",
        "train.max_epochs": "-e",
        "model": "-m",
    }

    # create parser for config
    parser_conf = argparse.ArgumentParser(add_help=False)
    for key, value in Config.flatten(config.options).items():
        short = short_options.get(key)
        argtype = type(value)
        if argtype == bool:
            argtype = argparse_bool_type
        if short:
            parser_conf.add_argument("--" + key, short, type=argtype)
        else:
            parser_conf.add_argument("--" + key, type=argtype)

    # create main parsers and subparsers
    parser = argparse.ArgumentParser("kge")
    subparsers = parser.add_subparsers(title="command", dest="command")
    subparsers.required = True

    # start and its meta-commands
    parser_start = subparsers.add_parser(
        "start", help="Start a new job (create and run it)", parents=[parser_conf]
    )
    parser_create = subparsers.add_parser(
        "create", help="Create a new job (but do not run it)", parents=[parser_conf]
    )
    for p in [parser_start, parser_create]:
        p.add_argument("config", type=str, nargs="?")
        p.add_argument("--folder", "-f", type=str, help="Output folder to use")
        p.add_argument(
            "--run",
            default=p is parser_start,
            type=argparse_bool_type,
            help="Whether to immediately run the created job",
        )

    # resume and its meta-commands
    parser_resume = subparsers.add_parser(
        "resume", help="Resume a prior job", parents=[parser_conf]
    )
    parser_eval = subparsers.add_parser(
        "eval", help="Evaluate the result of a prior job", parents=[parser_conf]
    )
    parser_valid = subparsers.add_parser(
        "valid",
        help="Evaluate the result of a prior job using validation data",
        parents=[parser_conf],
    )
    parser_test = subparsers.add_parser(
        "test",
        help="Evaluate the result of a prior job using test data",
        parents=[parser_conf],
    )
    for p in [parser_resume, parser_eval, parser_valid, parser_test]:
        p.add_argument("config", type=str)

    # now parse the arguments
    args = parser.parse_args()

    # process meta-commands
    process_meta_command(args, "create", {"command": "start", "run": False})
    process_meta_command(args, "eval", {"command": "resume", "job.type": "eval"})
    process_meta_command(
        args, "test", {"command": "resume", "job.type": "eval", "eval.data": "test"}
    )
    process_meta_command(
        args, "valid", {"command": "resume", "job.type": "eval", "eval.data": "valid"}
    )

    # start command
    if args.command == "start":
        # use toy config file if no config given
        if args.config is None:
            args.config = "examples/toy.yaml"
            print("WARNING: No configuration specified; using " + args.config)

        print("Loading configuration {}...".format(args.config))
        config.load(args.config)

    # resume command
    if args.command == "resume":
        if os.path.isdir(args.config) and os.path.isfile(args.config + "/config.yaml"):
            args.config += "/config.yaml"
        print("Resuming from configuration {}...".format(args.config))
        config.load(args.config)
        config.folder = os.path.dirname(args.config)
        if not os.path.exists(config.folder):
            raise ValueError(
                "{} is not a valid config file for resuming".format(args.config)
            )

    # overwrite configuration with command line arguments
    for key, value in vars(args).items():
        if key in ["command", "config", "run", "folder"]:
            continue
        if value is not None:
            config.set(key, value)
            if key == "model":
                config._import(value)

    # initialize output folder
    if args.command == "start":
        if args.folder is None:  # means: set default
            config_name = os.path.splitext(os.path.basename(args.config))[0]
            config.folder = os.path.join(
                kge_base_dir(),
                "local",
                "experiments",
                datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + config_name,
            )
        else:
            config.folder = args.folder

    if args.command == "start" and not config.init_folder():
        raise ValueError("output folder {} exists already".format(config.folder))
    config.log("Using folder: {}".format(config.folder))

    # log configuration
    config.log("Configuration:")
    config.log(yaml.dump(config.options), prefix="  ")
    config.log("git commit: {}".format(get_git_revision_short_hash()), prefix="  ")

    if args.command == "start" and not args.run:
        config.log("Job created successfully.")
    else:
        # load data
        dataset = Dataset.load(config)

        # let's go
        job = Job.create(config, dataset)
        if args.command == "resume":
            job.resume()
        job.run()
