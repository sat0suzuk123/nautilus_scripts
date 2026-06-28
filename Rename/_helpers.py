"""Shared helpers for Nautilus Rename scripts.

This file has NO executable bit, so it does not appear in the Scripts menu.
Each script does `sys.path.insert(0, os.path.dirname(...))` and imports from here.
"""
from __future__ import annotations

import os
import subprocess
import urllib.parse
from pathlib import Path


def _smb_uri_to_path(uri: str) -> Path:
    """smb://host/share/path -> /run/user/$UID/gvfs/smb-share:server=host,share=share/path"""
    from urllib.parse import urlparse
    p = urlparse(uri)
    host = p.netloc
    raw = p.path.lstrip("/")
    if not raw:
        raise ValueError(f"smb URI missing share: {uri}")
    share, _, rest = raw.partition("/")
    share = urllib.parse.unquote(share)
    rest = urllib.parse.unquote(rest)
    base = Path(f"/run/user/{os.getuid()}/gvfs/smb-share:server={host},share={share}")
    return base / rest if rest else base


def _uri_to_path(uri: str) -> Path:
    """Convert a Nautilus URI to a local filesystem Path.

    Supports file:// directly, smb:// via the GVFS FUSE mount convention,
    and falls back to (cwd + url-decoded basename) for anything else.
    """
    from urllib.parse import urlparse
    scheme = urlparse(uri).scheme
    if scheme == "file":
        return Path(urllib.parse.unquote(urlparse(uri).path))
    if scheme == "smb":
        return _smb_uri_to_path(uri)
    # Last-resort fallback: assume cwd is the FUSE mount of the parent
    base = urllib.parse.unquote(uri.rsplit("/", 1)[-1])
    return Path(os.getcwd()) / base


def get_selected_paths() -> list[Path]:
    """Selected items as Path objects.

    Uses NAUTILUS_SCRIPT_SELECTED_FILE_PATHS when populated (local files).
    Falls back to URI→FUSE-path conversion when it's empty (GVFS mounts).
    Diagnostic info is appended to /tmp/nautilus-rename.log.
    """
    raw_paths = os.environ.get("NAUTILUS_SCRIPT_SELECTED_FILE_PATHS", "")
    raw_uris = os.environ.get("NAUTILUS_SCRIPT_SELECTED_URIS", "")
    _log(f"get_selected_paths: cwd={os.getcwd()!r} PWD={os.environ.get('PWD')!r}")
    _log(f"  SELECTED_FILE_PATHS={raw_paths!r}")
    _log(f"  SELECTED_URIS={raw_uris!r}")

    paths = [Path(p) for p in raw_paths.splitlines() if p]
    if paths:
        _log(f"  -> using FILE_PATHS: {[str(p) for p in paths]}")
        return paths
    result = [_uri_to_path(u) for u in raw_uris.splitlines() if u]
    _log(f"  -> using URIS:       {[str(p) for p in result]}")
    return result


def _zenity(*args: str, capture: bool = False) -> str | None:
    """Run zenity. Returns stdout (str) on success, None on cancel/error."""
    result = subprocess.run(
        ["zenity", *args],
        capture_output=capture,
        text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout.rstrip("\n") if capture else ""


def zenity_entry(title: str, text: str, entry_text: str = "") -> str | None:
    """Show an --entry dialog. Returns the string (possibly empty), or None on cancel."""
    return _zenity(
        "--entry",
        f"--title={title}",
        f"--text={text}",
        f"--entry-text={entry_text}",
        capture=True,
    )


def zenity_info(title: str, text: str) -> None:
    _zenity("--info", f"--title={title}", f"--text={text}")


def zenity_warning(title: str, text: str) -> None:
    _zenity("--warning", f"--title={title}", f"--text={text}")


def zenity_radio(title: str, text: str, options: list[tuple[bool, str, str]]) -> str | None:
    """Show a --list --radiolist. options is [(default_selected, label, hint)].
    Returns the chosen label, or None on cancel."""
    rows: list[str] = []
    for default, label, hint in options:
        rows.extend(["TRUE" if default else "FALSE", label, hint])
    return _zenity(
        "--list",
        f"--title={title}",
        f"--text={text}",
        "--radiolist",
        "--column=Pick",
        "--column=Source",
        "--column=Format",
        *rows,
        capture=True,
    )


_LOG_PATH = "/tmp/nautilus-rename.log"


def _log(msg: str) -> None:
    try:
        from datetime import datetime
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")
    except OSError:
        pass


def safe_rename(src: Path, dst: Path) -> bool:
    """Like `mv -n`: do nothing (return False) if dst already exists.
    Returns True on success, False on skip or error.
    Logs every attempt to /tmp/nautilus-rename.log (for diagnostics)."""
    try:
        exists = dst.exists()
    except OSError as e:
        _log(f"EXISTS-CHECK-ERROR: {dst} ({e!r})")
        return False
    if exists:
        _log(f"SKIP (dst exists): {dst}")
        return False
    try:
        src.rename(dst)
        # Verify the rename actually took effect (catches GVFS silent failures)
        try:
            still_there = src.exists()
        except OSError:
            still_there = False
        if still_there:
            _log(f"PHANTOM-RENAME: src still exists after rename: {src}")
            return False
        _log(f"OK: {src.name} -> {dst.name}")
        return True
    except OSError as e:
        _log(f"RENAME-ERROR: {src} -> {dst}: {e!r}")
        return False


def report(title: str, counts: dict[str, int]) -> None:
    """Display a summary of non-zero counts via zenity_info."""
    lines = [f"{k}: {v}" for k, v in counts.items() if v]
    if lines:
        zenity_info(title, "\n".join(lines))
