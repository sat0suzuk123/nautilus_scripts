# nautilus_scripts

Python 3 rename utilities for GNOME Files (Nautilus), with first-class support
for GVFS-mounted SMB shares.

## Features

Right-click selected files in Nautilus → Scripts → Rename → …

| Script | What it does |
| --- | --- |
| `Add prefix` | Prepend a user-input string to each filename |
| `Add suffix` | Insert a user-input string before each filename's extension (handles `file.tar.gz` correctly) |
| `Number prefix` | Sequential `00_`, `01_`, … in Nautilus selection order (no wizard — one click) |
| `Remove prefix` | Strip the leading `XXX_` segment up to the first separator |
| `Replace` | Plain-text find/replace within filenames (empty replacement = delete) |
| `Insert date` | Prepend a date — today / today+time / per-file mtime / custom string |
| `Flatten directory` | Move every entry from `<dir>/` to its parent, prepended with `<dir>_`; remove empty source dir |

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
chmod +x ~/.local/share/nautilus/scripts/Rename/{Add\ prefix,Add\ suffix,Number\ prefix,Remove\ prefix,Replace,Insert\ date,Flatten\ directory}
# _helpers.py must NOT be executable (so it stays out of the Scripts menu)
```

Requirements: Python 3.8+, `zenity`.

If new entries don't appear in the Scripts submenu, restart Nautilus:

```sh
nautilus -q
```

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
