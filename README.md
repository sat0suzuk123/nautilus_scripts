# nautilus_scripts

Python 3 utilities for GNOME Files (Nautilus), with first-class support
for GVFS-mounted SMB shares. The same scripts also run on macOS as Finder
Quick Actions (see [macOS](#macos)).

## Features

### Rename — right-click selected files → Scripts → Rename → …

| Script | What it does |
| --- | --- |
| `Add prefix` | Prepend a user-input string to each filename |
| `Add suffix` | Insert a user-input string before each filename's extension (handles `file.tar.gz` correctly) |
| `Number prefix` | Sequential `00_`, `01_`, … in Nautilus selection order (no wizard — one click) |
| `Remove prefix` | Strip the leading `XXX_` segment up to the first separator |
| `Replace` | Plain-text find/replace within filenames (empty replacement = delete) |
| `Insert date` | Prepend a date — today / today+time / per-file mtime / custom string |
| `Flatten directory` | Move every entry from `<dir>/` to its parent, prepended with `<dir>_`; remove empty source dir |
| `Group by common prefix` | Sort the selected items into several directories at once: items whose names start with the same N characters (minimum prefix length, default 3, adjustable in the dialog, which previews the groups) go into a directory named after their shared prefix, cut back to a word boundary. Names are kept; items with no partner stay in place. |

### Clipboard — right-click selected files → Scripts → …

| Script | What it does |
| --- | --- |
| `Copy contents` | Copy the text contents of the selected file(s) to the clipboard. One file → its raw text; N files → concatenated with `===== <name> =====` headers. Directories and non-UTF-8/binary files are skipped and reported. Wayland (`wl-copy`) and X11 (`xclip`/`xsel`) aware. |

All operations are **non-overwriting** (`mv -n` semantics) — collisions are
counted and reported via `zenity`, never silently overwritten.

## SMB / GVFS support

Nautilus leaves `NAUTILUS_SCRIPT_SELECTED_FILE_PATHS` empty for GVFS-mounted
URIs (`smb://`, `sftp://`, etc.) and only sets `NAUTILUS_SCRIPT_SELECTED_URIS`.
`_helpers.py` converts these URIs directly to FUSE paths
(`/run/user/$UID/gvfs/smb-share:server=…,share=…/…`) so the scripts work
identically on local files and NAS shares.

Currently `smb://` and `file://` are supported. Other schemes fall back to
`os.getcwd() + URL-decoded basename`.

## Install

```sh
mkdir -p ~/.local/share/nautilus/scripts
cp -r Rename ~/.local/share/nautilus/scripts/
chmod +x ~/.local/share/nautilus/scripts/Rename/{Add\ prefix,Add\ suffix,Number\ prefix,Remove\ prefix,Replace,Insert\ date,Flatten\ directory,Group\ by\ common\ prefix}
# _helpers.py must NOT be executable (so it stays out of the Scripts menu)

# Clipboard tools (self-contained — no _helpers.py dependency)
install -m 755 "Clipboard/Copy contents" ~/.local/share/nautilus/scripts/
```

Requirements (Linux): Python 3.8+, `zenity` (Rename scripts). `Copy contents`
needs a clipboard writer (`wl-copy` on Wayland, or `xclip`/`xsel` on X11) and
uses `notify-send`/`zenity` for feedback when available.

If new entries don't appear in the Scripts submenu, restart Nautilus:

```sh
nautilus -q
```

## macOS

The scripts take the selection from the command-line arguments when the
Nautilus environment variables are absent, and use `osascript` dialogs,
`pbcopy` and Notification Center instead of `zenity`, `wl-copy`/`xclip` and
`notify-send`. No extra packages are needed; the system `/usr/bin/python3`
(3.9) is enough.

Finder has no scripts folder, so each script is registered as a Quick Action.
The installer does this for every executable in `Rename/` and `Clipboard/`:

```sh
python3 install_quick_actions.py
```

It writes one `<script name>.workflow` per script into `~/Library/Services/`
(Quick Action, receives files or folders in Finder, runs the script with the
selection as arguments). They appear under right-click → Quick Actions; which
ones are shown can be changed in System Settings → Keyboard → Keyboard
Shortcuts → Services.

* The workflows hold the absolute path of this checkout. Re-run the installer
  after moving the repository or adding a script.
* Re-running replaces only workflows the installer created; a same-named
  workflow of yours is left alone and reported.
* To uninstall, delete the `.workflow` bundles from `~/Library/Services/`.

The same scripts can be run from a terminal on either platform:
`"Rename/Add prefix" file1 file2`.

SMB shares need no special handling on macOS: Finder mounts them under
`/Volumes/`, so the paths passed to the scripts are ordinary paths.

## Diagnostics

Every rename attempt is logged to `/tmp/nautilus-rename.log` with the
src/dst paths and the outcome (`OK`, `SKIP`, `RENAME-ERROR`,
`PHANTOM-RENAME`, `EXISTS-CHECK-ERROR`). Useful when something silently
fails on a network mount.

## Related work

[cfgnunes/nautilus-scripts](https://github.com/cfgnunes/nautilus-scripts) is
the dominant general-purpose collection (Bash). Its `Rename files/` focuses
on case/whitespace/punctuation transforms; the structural renames here
(prefix/suffix/number/date/flatten) are complementary.

## License

MIT — see [`LICENSE`](LICENSE).
