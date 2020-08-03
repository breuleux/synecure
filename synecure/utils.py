import json
import os
import re


def get_config_path(name=None):
    path = os.path.expanduser("~/.config/synecure")
    if name is not None:
        path = os.path.join(path, name)
    return path


def get_config(name):
    path = get_config_path(name)
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        return json.load(f)


def write_config(name, cfg, silent=False):
    path = get_config_path(name)
    cdir = os.path.dirname(path)
    os.makedirs(cdir, exist_ok=True)
    with open(path, "w") as f:
        json.dump(cfg, f, indent=4)
    if not silent:
        print(f"Written config at: {path}")


def sort_paths(remote):
    return sorted(remote["paths"].items(), key=lambda kv: -len(kv[0]))


def readlines(filename):
    if not os.path.exists(filename):
        return []
    else:
        return [l.strip() for l in open(filename, "r").readlines()]


def writelines(filename, lines):
    with open(filename, "w") as f:
        for line in lines:
            print(line, file=f)

_find_unsafe = re.compile(r'[^\w@%+=:,./-]', re.ASCII).search


# from python3.3 tree: Lib/shlex.py (shlex.quote not in python3.2)
def quote(s):
    """Return a shell-escaped version of the string *s*."""
    if not s:
        return "''"
    if _find_unsafe(s) is None:
        return s
    # use single quotes, and put single quotes into double quotes
    # the string $'b is then quoted as '$'"'"'b'
    return "'" + s.replace("'", "'\"'\"'") + "'"
