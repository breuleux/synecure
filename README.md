
# Synecure

Synecure provides a command line program called `sy` that allows easy synchronization of files and directories over SSH between different machines. It is mostly a wrapper around [bsync](https://github.com/dooblem/bsync), which is itself based on the standard UNIX tool `rsync`.

This is beta software and comes with **NO GUARANTEES** that it will keep your data safe. It should not be used as backup solution.


## Install

```bash
pip install synecure
```


## Usage

1. Set up a remote (to which you must already have SSH access)

```bash
sy-config add desktop user@some.remote.address
```

2. Synchronize a directory to that remote

```bash
$ sy ~/directory -r desktop
# SYNC LOCAL      /home/me/directory
# WITH REMOTE     user@some.remote.address:directory
...
```

By default, `sy` can take on any path within your `$HOME` and will set the corresponding path on the remote's `$HOME`. It is possible to change this behavior or synchronize paths outside of `$HOME` using the `sy-config path` command.

`sy` with no argument will sync the current directory using the last remote for that directory (you will need to use the -r flag the first time, but not subsequently).

```bash
sy  # equivalent to sy . with last remote used
```


## Howto


### Ignore files

Add a `.bsync-ignore` file in the root directory to sync with a filename or glob pattern on each line, and they will be ignored. It works more or less like `.gitignore`.

Putting `.bsync-ignore` files in subdirectories to ignore files in these subdirectories will unfortunately not work, so `sy ~/x` and `sy ~/x/y` may synchronize the contents of `~/x/y` differently if both directories contain different `.bsync-ignore` files, or if one has an ignore file and the other does not.


### Customize synchronization paths

To synchronize local `/etc` to remote `/etcetera`:

```bash
sy-config path add desktop /etc /etcetera
```

Obviously, this will only work if the remote user has the permissions to write to `/etcetera`. You can have multiple remotes for the same host with different users, if that helps.

To synchronize local `~/hello` to remote `~/bonjour`:

```bash
sy-config path add desktop ~/hello bonjour
```

Don't use `~` for the remote path, it will complete to the wrong thing.

To list available paths:

```bash
sy-config list
```

### Sync local directories

```bash
sy-config add dropbox ~/Dropbox
```

### Dry run

Use the `-n` flag to perform a "dry run": `sy` (well, `bsync`) will report all the transfers that would occur but it will not perform them.

Use `--show-plan` to get the sequence of commands that `sy` will run.
