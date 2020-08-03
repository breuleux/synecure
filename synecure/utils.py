import json
import os


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
