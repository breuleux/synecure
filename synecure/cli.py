import os
import sys
import json
import subprocess
import shlex
from coleo import Option, default, run_cli

from .utils import (
    get_config,
    get_config_path,
    edit_config,
    write_config,
    readlines,
    writelines,
    quote,
)
from .version import version as sy_version


def q(message=None):
    sys.exit(message)


def _realpath(filename):
    return os.path.realpath(os.path.expanduser(filename))


def _get_remote(cfg, name):
    if name in cfg:
        return cfg[name]

    return {
        "type": "ssh",
        "url": name,
        "paths": {os.getenv("HOME"): ""},
    }


def _cfg_from_url(name):
    return {
        "type": "ssh",
        "url": name,
        "paths": {os.getenv("HOME"): ""},
    }


def _check_remote(cfg, name, create=False, msg=None):
    if name not in cfg:
        if create:
            cfg[name] = _cfg_from_url(name)
        else:
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
    run_cli(main)


def entry_sy_config():
    commands = {}
    for name, value in globals().items():
        parts = name.replace("_", "-").split("-", 1)
        if parts[0] == "config" and len(parts) > 1:
            curr = commands
            for part in parts[1:-1]:
                curr = curr.setdefault(part, {})
            curr[parts[-1]] = value
    run_cli(commands)


######
# sy #
######


def main():
    # List all sy directories
    # [alias: -l]
    list: Option & bool = default(False)

    # Version information
    version: Option & bool = default(False)
    if version:
        q(f"sy v{sy_version}")

    # Files to synchronize
    # [positional: *]
    files: Option

    # Name of the remote to sync with
    # [alias: -r]
    remote: Option = default(None)

    # Port to connect to
    # [alias: -p]
    port: Option = default(None)

    # Do a dry run
    # [alias: -n]
    dry_run: Option & bool = default(False)

    # List the commands sy will run
    show_plan: Option & bool = default(False)

    # Verbose output
    # [alias: -v]
    verbose: Option & bool = default(False)

    # Prompt for changes (necessary to resolve conflicts)
    # [alias: -i]
    interactive: Option & bool = default(False)

    # Resolve a conflict with "local" or "remote" copy (default: "prompt")
    resolve: Option = default("prompt")
    if resolve not in ("local", "remote", "prompt"):
        sys.exit("ERROR: resolve must be 'local', 'remote' or 'prompt'")

    # Resolve a conflict with local copy
    # [option: -1]
    # [false-options: -2]
    # [false-options-doc: Resolve a conflict with remote copy]
    resolve_local: Option & bool = default(None)
    if resolve_local is True:
        resolve = "local"
    if resolve_local is False:
        resolve = "remote"

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
        filename = _realpath(filename)

        remote_name = _fill_remote(filename, remote, directories)
        remote_config = _get_remote(remotes, remote_name)
        remote_config["port"] = port

        commands += plan_sync(
            filename,
            remote,
            remote_config,
            dry=dry_run,
            verbose=verbose,
            interactive=interactive,
            resolve=resolve,
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


def _fill_remote(path, remote_name, directories):
    if remote_name is None:
        if path not in directories:
            q("Please specify a destination")
        regdest = directories[path]
        assert regdest is not None
        return regdest
    else:
        directories[path] = remote_name
        return remote_name


def _check_dir(url, path, port):
    if url:
        args = ["ssh", url]
        if port:
            args.extend(["-p", str(port)])
        args.append(f"test -d {quote(path)}")
        result = subprocess.call(args)
        return result == 0

    else:
        return os.path.isdir(path)


def plan_sync(
    path,
    remote_name,
    remote,
    dry=False,
    verbose=False,
    interactive=False,
    resolve="prompt",
):

    for pfx, repl in _sort_paths(remote):
        if path.startswith(pfx):
            destpath = os.path.join(repl, path[len(pfx) + 1 :])
            break
    else:
        q(
            f"There is no rule to remap path '{path}' on '{remote_name}'"
            f"\nTry: 'sy-remote path {remote_name} <SRC_PREFIX> <DEST_PREFIX>'"
        )

    print(f"# SYNC LOCAL      {path}")
    if remote["type"] == "ssh":
        dest = f"{remote['url']}:{destpath}"
        print(f"# WITH REMOTE     {dest}")
    elif remote["type"] == "file":
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
            cmdopts.append("-y")

        if resolve == "local":
            cmdopts.append("-1")
        elif resolve == "remote":
            cmdopts.append("-2")

        if remote["type"] == "ssh" and remote["port"]:
            cmdopts.append(f"-p {remote['port']}")

        cmd = ["sy-bsync", *cmdopts, path, dest]
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
                "-e",
                f"ssh ",
                f"-p {remote['port']}" if remote["port"] else "",
                # This is a dirty trick to create the directory on the remote
                "--rsync-path",
                f"mkdir -p {destdir}; rsync",
            ]
        elif remote["type"] == "file":
            commands.append(["mkdir", "-p", destdir])

        cmd1 = [*common, path, dest]
        cmd2 = [*common, dest, path]

        commands += [cmd1, cmd2]

    return commands


#############
# sy-remote #
#############


def config_add():
    """Add a new remote or edit an existing one."""
    # Name of the remote
    # [positional]
    name: Option

    # URL of the remote
    # [positional]
    url: Option

    if "://" not in url:
        q(
            "URL should be formatted as type://url -- currently accepted are:"
            "\n* SSH:              ssh://user@host"
            "\n* Local directory:  file:///path/from/root"
        )

    typ, url = url.split("://", 1)
    if typ not in ("ssh", "file"):
        q(f"Unknown protocol: '{typ}'. Accepted protocols are 'ssh' and 'file'.")

    if typ == "file":
        url = _realpath(url)

    cfg = get_config("remotes.json")
    if name in cfg:
        entry = cfg[name]
        entry["type"] = typ
        entry["url"] = url
    else:
        entry = {"type": typ, "url": url, "paths": {os.getenv("HOME"): ""}}
        cfg[name] = entry

    print(json.dumps(entry, indent=4))

    write_config("remotes.json", cfg)


def config_view():
    """View configuration for a remote."""
    # Name of the remote
    # [positional: ?]
    name: Option

    cfg = get_config("remotes.json")
    if name is not None:
        cfg = _check_remote(cfg, name)

    print(json.dumps(cfg, indent=4))


def config_list():
    """List existing remotes and paths."""
    cfg = get_config("remotes.json")
    for name, defn in cfg.items():
        print(f"{name:30} ({defn['type']}) {defn['url']}")
        for local_path, remote_path in defn["paths"].items():
            print(f"    {local_path:30} -> :{remote_path}")


def config_edit():
    """Edit the configuration file directly."""
    edit_config("remotes.json")


def config_ssh():
    """Edit your SSH configuration file."""
    edit_config(_realpath("~/.ssh/config"))


def _list_paths(remote):
    for s, d in _sort_paths(remote):
        print(f"{s:30}:{d}")


def config_add_path():
    """Add a path mapping for a remote."""
    # Name of the remote
    # [positional]
    name: Option

    # Source path
    # [positional]
    source: Option

    # Destination path
    # [positional]
    dest: Option

    cfg = get_config("remotes.json")
    remote = _check_remote(cfg, name, create=True)

    paths = remote["paths"]
    paths[source] = dest
    _list_paths(remote)
    write_config("remotes.json", cfg)


def config_list_paths():
    """List paths for a remote"""
    # Name of the remote
    # [positional]
    name: Option

    cfg = get_config("remotes.json")
    remote = _check_remote(cfg, name, create=False)
    _list_paths(remote)


def config_remove_path():
    """Remove a path mapping for a remote"""
    # Name of the remote
    # [positional]
    name: Option

    # Source path
    # [positional]
    source: Option

    cfg = get_config("remotes.json")
    remote = _check_remote(cfg, name, create=False)

    if source not in remote["paths"]:
        q(f"Source path '{source}' is not mapped")
    del remote["paths"][source]
    _list_paths(remote)
    write_config("remotes.json", cfg)


def config_remove():
    """Remove a remote."""
    # Name of the remote
    # [positional]
    name: Option

    cfg = get_config("remotes.json")
    _check_remote(cfg, name, create=False, msg="Nothing to remove")
    del cfg[name]
    write_config("remotes.json", cfg)


def config_ignore():
    """Add/remove global ignore patterns."""
    # Patterns to ignore
    # [positional: *]
    patterns: Option = default([])

    # List the ignores
    # [alias: -l]
    list: Option & bool = default(False)

    # Remove the ignores
    # [alias: -r]
    # [nargs: *]
    remove: Option = default([])

    ign = get_config_path("ignore")

    if list:
        print(open(ign).read(), end="")
        sys.exit(0)

    if not patterns:
        edit_config("ignore")
        sys.exit(0)

    lines = readlines(ign)
    new_lines = []

    for line in lines:
        if line in remove:
            print(f"-{line}")
        else:
            print(f" {line}")
            new_lines.append(line)

    no_add = {*lines, *remove}

    for pattern in patterns:
        if pattern not in no_add:
            print(f"+{pattern}")
            lines.append(pattern)

    writelines(ign, lines)
