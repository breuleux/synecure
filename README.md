
# Synecure

Synecure provides a command line program called `sy` that allows easy synchronization of files and directories over SSH between different machines. It is mostly a wrapper around [bsync](https://github.com/dooblem/bsync), which is itself based on the standard UNIX tool `rsync`.

This is beta software and comes with **NO GUARANTEES** that it will keep your data safe. It should not be used as backup solution.


## Install

```bash
pip install synecure
```


## Usage

```bash
# Sync local ~/directory with remote $HOME/directory on me@awesome.person
sy ~/directory -r me@awesome.person

# Sync current directory with the same path on me@awesome.person, port 2222
sy -r me@awesome.person -p 2222

# Register a remote under a short name
sy-config add me me@awesome.person -p 2222

# Synchronize to a named remote
sy -r me

# Synchronize the current directory to the last used remote (for that directory)
sy
```

By default, `sy` can take on any path within your `$HOME` and will set the corresponding path on the remote's `$HOME`. It is possible to change this behavior or synchronize paths outside of `$HOME` using the `sy-config path` command.

`sy` with no argument will sync the current directory using the last remote for that directory (you will need to use the -r flag the first time, but not subsequently).


## Howto


### Ignore files

Add a `.bsync-ignore` file in the root directory to sync with a filename or glob pattern on each line, and they will be ignored. It works more or less like `.gitignore`.

Putting `.bsync-ignore` files in subdirectories to ignore files in these subdirectories will unfortunately not work, so `sy ~/x` and `sy ~/x/y` may synchronize the contents of `~/x/y` differently if both directories contain different `.bsync-ignore` files, or if one has an ignore file and the other does not.


### Global ignores

The `sy-config ignore` command can be used to generally ignore files or directories:

```bash
# Edit the ignore file using $EDITOR, if it is set
sy-config ignore

# List all existing ignores
sy-config ignore -l

# Ignore all files that end with ~
# Do not forget the single quotes here, to avoid shell expansion!
sy-config ignore '*~'

# Unignore files that end with ~
sy-config ignore -r '*~'
```

The ignores work mostly like `.gitignore` or `.bsync-ignore` above, but they apply globally. Note that `sy` will also read *remote-side* global ignores when syncing to a remote. Global ignores are located at `$HOME/.config/synecure/ignore`, so a remote can define some global ignores even without installing `sy` remote-side. Global ignores local-side, remote-side, as well as `.bsync-ignore` files local-side and remote-side are all merged together.


### Customize synchronization paths

To synchronize local `/etc` to remote `/etcetera`, for named remote `desktop`:

```bash
sy-config path desktop /etc /etcetera
```

Obviously, this will only work if the remote user has the permissions to write to `/etcetera`. You can have multiple remotes for the same host with different users, if that helps.

To synchronize local `~/hello` to remote `~/bonjour`:

```bash
sy-config path desktop ~/hello bonjour
```

Don't use `~` for the remote path, it will complete to the wrong thing.

To list available remotes and paths:

```bash
sy-config list
```

### Sync local directories

```bash
sy-config add dropbox ~/Dropbox
```

## Other options

### Dry run

Use the `-n` flag to perform a "dry run": `sy` (well, `bsync`) will report all the transfers that would occur but it will not perform them.

Use `--show-plan` to get the sequence of commands that `sy` will run.

### Conflict resolution

Whenever a file was modified on both ends since the last sync, `sy` will ask which one you want to keep.

Use `sy <options> --resolve local` (or `sy <options> -1`) to always keep the local file without prompting, or `--resolve remote` (or `-2`) to always keep the remote file.

### List directories

`sy -l` will list all directories that have been previously synced using the tool, along with the last remote they were synced to (remember that `sy` without the `-r` option will sync to the last remote).

## Configuration files

* `~/.config/synecure/remotes.json` defines named remotes and paths.
  * You can open an editor for that file with `sy-config edit`
* `~/.config/synecure/ignore` lists global ignores.
  * You can open an editor for that file with `sy-config ignore`
* `~/.config/synecure/directories.json` maps directories to last used remotes.
