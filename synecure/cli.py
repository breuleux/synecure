import os
import sys
import json
import subprocess
import shlex
from coleo import Argument, auto_cli, default

from .utils import get_config, get_config_path, write_config, readlines, writelines, quote


def q(message=None):
    if message:
        print(message)
    sys.exit(1)


def _check_remote(cfg, name, msg=None):
    if name not in cfg:
        print(f"ERROR: remote '{name}' is not defined")
        if msg:
            print(msg)
        q()
    return cfg[name]


def _sort_paths(remote):
    return sorted(remote["paths"].items(), key=lambda kv: -len(kv[0]))


################
# Entry points #
################


def entry_bsync():
    from . import bsync


def entry_sy():
    auto_cli(main)


def entry_sy_config():
    commands = {}
    for name, value in globals().items():
        parts = name.split("_")
        if parts[0] == "config" and len(parts) > 1:
            curr = commands
            for part in parts[1:-1]:
                curr = curr.setdefault(part, {})
            curr[parts[-1]] = value
    auto_cli(commands)


######
# sy #
######


def main():
    # List all sy directories
    # [alias: -l]
    list: Argument & bool = default(False)

    # Files to synchronize
    # [positional: *]
    files: Argument

    # Name of the remote to sync with
    # [alias: -r]
    remote: Argument = default(None)

    # Do a dry run
    # [alias: -n]
    dry_run: Argument & bool = default(False)

    # List the commands sy will run
    show_plan: Argument & bool = default(False)

    # Verbose output
    # [alias: -v]
    verbose: Argument & bool = default(False)

    # Prompt for changes (necessary to resolve conflicts)
    # [alias: -i]
    interactive: Argument & bool = default(False)

    remotes = get_config("remotes.json")
    directories = get_config("directories.json")

    if list:
        for path, dest in directories.items():
            print(f"{path:50} {dest}")
        return

    commands = []
    if not files:
        files.append(".")

    for filename in files:
        filename = os.path.realpath(os.path.expanduser(filename))
        commands += plan_sync(
            filename, remote, remotes, directories,
            dry=dry_run,
            verbose=verbose,
            interactive=interactive
        )

    for command in commands:
        if verbose or show_plan:
            if isinstance(command, str):
                print(command)
            else:
                print(" ".join(map(shlex.quote, command)))
        if not show_plan:
            subprocess.run(command)

    write_config("directories.json", directories, silent=True)


def _check_dir(url, path, port):
    if url:
        args = ["ssh", url]
        if port:
            args.extend(["-p", "22005"])
        args.append(f"test -d {quote(path)}")
        result = subprocess.call(args)
        return result == 0

    else:
        return os.path.isdir(path)


def plan_sync(path, remote_name, remotes, directories,
              dry=False, verbose=False, interactive=False):
    if remote_name is None:
        if path not in directories:
            q("Please specify a destination")
        regdest = directories[path]
        assert regdest is not None
        return plan_sync(path, regdest, remotes, directories,
            dry=dry,
            interactive=interactive
        )

    directories[path] = remote_name

    remote = _check_remote(remotes, remote_name)
    for pfx, repl in _sort_paths(remote):
        if path.startswith(pfx):
            destpath = os.path.join(repl, path[len(pfx) + 1:])
            break
    else:
        q(f"There is no rule to remap path '{path}' on '{remote_name}'"
          f"\nTry: 'sy-remote path {remote_name} <SRC_PREFIX> <DEST_PREFIX>'")

    print(f"# SYNC LOCAL      {path}")
    if remote["type"] == "ssh":
        dest = f"{remote['url']}:{destpath}"
        print(f"# WITH REMOTE     {dest}")
    elif remote["type"] == "local":
        dest = destpath
        print(f"# WITH LOCAL      {dest}")
    else:
        print(f"# Unknown remote type: {remote['type']}")

    commands = []

    if os.path.exists(path):
        isdir = os.path.isdir(path)
    else:
        isdir = _check_dir(remote["url"], destpath, remote["port"])

    if isdir:
        # Use bsync to synchronize both directories

        cmdopts = ["-d"]
        if dry:
            cmdopts.append("-n")
        elif interactive:
            pass
        else:
            cmdopts.append("-b")

        if remote["type"] == "ssh":
            cmdopts.append(f"-p {remote['port']}")

        cmd = ["bsync", *cmdopts, path, dest]
        commands.append(cmd)

    else:
        # Use two rsync commands to synchronize a single file
        # This will never erase the file
        destdir = os.path.dirname(destpath)

        common = ["rsync", "-ptu"]
        if verbose:
            common.append("-v")
        if remote["type"] == "ssh":
            common += [
                "-e", f"ssh -p {remote['port']}",
                # This is a dirty trick to create the directory on the remote
                "--rsync-path", f"mkdir -p {destdir}; rsync",
            ]
        elif remote["type"] == "local":
            commands.append(["mkdir", "-p", destdir])

        cmd1 = [*common, path, dest]
        cmd2 = [*common, dest, path]

        commands += [cmd1, cmd2]

    return commands


#############
# sy-remote #
#############


def remote_add():
    # Name of the remote
    # [positional]
    name: Argument

    # URL of the remote
    # [positional]
    url: Argument

    # Port to connect to
    # [alias: -p]
    port: Argument = default(22)

    cfg = get_config("remotes.json")
    if "@" in url:
        cfg[name] = {
            "type": "ssh",
            "url": url,
            "port": port,
            "paths": {
                os.getenv("HOME"): ""
            }
        }
    else:
        cfg[name] = {
            "type": "local",
            "url": "localhost",
            "port": None,
            "paths": {
                os.getenv("HOME"): os.path.realpath(os.path.expanduser(url))
            }
        }
    write_config("remotes.json", cfg)


def config_view():
    # Name of the remote
    # [positional: ?]
    name: Argument

    cfg = get_config("remotes.json")
    if name is not None:
        cfg = _check_remote(cfg, name)

    print(json.dumps(cfg, indent=4))


def config_list():
    cfg = get_config("remotes.json")
    for name, defn in cfg.items():
        if defn['port'] in (None, 22):
            port = ""
        else:
            port = f":{defn['port']}"
        print(f"{name:30} {defn['url']}{port}")
        for local_path, remote_path in defn["paths"].items():
            print(f"    {local_path:30} -> :{remote_path}")


def config_path():
    # Name of the remote
    # [positional]
    name: Argument

    # Source path
    # [positional: ?]
    source: Argument

    # Destination path
    # [positional: ?]
    dest: Argument

    # List path mappings
    # [alias: -l]
    list: Argument & bool = default(False)

    # Whether to remove the path
    # [alias: -r]
    remove: Argument = default(None)

    cfg = get_config("remotes.json")
    remote = _check_remote(cfg, name, msg="Nothing to do")

    if list:
        for s, d in _sort_paths(remote):
            print(f"{s:30}:{d}")

    elif remove is not None:
        if remove not in remote["paths"]:
            q(f"Source path '{remove}' is not mapped")
        del remote["paths"][remove]
        write_config("remotes.json", cfg)

    else:
        if source is None:
            q("SOURCE must be specified")
        if dest is None:
            q("DEST must be specified")
        paths = remote["paths"]
        paths[source] = dest
        write_config("remotes.json", cfg)


def config_remove():
    # Name of the remote
    # [positional]
    name: Argument

    cfg = get_config("remotes.json")
    _check_remote(cfg, name, msg="Nothing to remove")
    del cfg[name]
    write_config("remotes.json", cfg)


def config_ignore():
    # Patterns to ignore
    # [positional: *]
    patterns: Argument = default([])

    ign = get_config_path("ignore")
    lines = readlines(ign)

    for line in lines:
        print(f" {line}")
    for pattern in patterns:
        if pattern not in lines:
            print(f"+{pattern}")
            lines.append(pattern)

    writelines(ign, lines)


def config_unignore():
    # Patterns to ignore
    # [positional: *]
    patterns: Argument = default([])

    ign = get_config_path("ignore")
    lines = readlines(ign)

    new_lines = []
    for line in lines:
        if line in patterns:
            print(f"-{line}")
        else:
            print(f" {line}")
            new_lines.append(line)

    writelines(ign, new_lines)
