#!/usr/bin/env python3
"""Register every script in this repository as a macOS Finder Quick Action.

For each executable file in Rename/ and Clipboard/, writes
`~/Library/Services/<script name>.workflow`: a Quick Action that receives
files or folders in Finder and runs the script with the selection as
arguments. The workflows hold the absolute path of this checkout, so re-run
this installer after moving the repository.

Usage: python3 install_quick_actions.py

Re-running replaces workflows created by this installer. A workflow of the
same name that this installer did not create is left untouched and reported.
"""
from __future__ import annotations

import os
import plistlib
import shlex
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

# %%
# Constants

REPOSITORY_DIR = Path(__file__).resolve().parent
SCRIPT_DIRS = ("Rename", "Clipboard")
SERVICES_DIR = Path.home() / "Library" / "Services"
# Marks a workflow as ours; only bundles carrying this prefix are overwritten.
BUNDLE_ID_PREFIX = "local.nautilus-scripts."
RUN_SHELL_SCRIPT_ACTION = Path("/System/Library/Automator/Run Shell Script.action")
SHELL = "/bin/zsh"
# "Pass input" popup of Run Shell Script: 0 = to stdin, 1 = as arguments.
INPUT_AS_ARGUMENTS = 1
# Refreshes the Services registry so new Quick Actions show up without a logout.
PBS = "/System/Library/CoreServices/pbs"


# %%
# Helper functions

def find_scripts() -> list[Path]:
    """Executable regular files in SCRIPT_DIRS (so `_helpers.py` is excluded)."""
    scripts = []
    for directory in SCRIPT_DIRS:
        for path in sorted((REPOSITORY_DIR / directory).iterdir()):
            if path.is_file() and os.access(path, os.X_OK):
                scripts.append(path)
    return scripts


def bundle_identifier(script: Path) -> str:
    slug = "-".join(script.name.lower().split())
    return f"{BUNDLE_ID_PREFIX}{slug}"


def build_info_plist(script: Path) -> dict:
    """Info.plist: a Finder-only service that accepts any file or folder."""
    return {
        "CFBundleDevelopmentRegion": "en_US",
        "CFBundleIdentifier": bundle_identifier(script),
        "CFBundleName": script.name,
        "CFBundleShortVersionString": "1.0",
        "NSServices": [{
            "NSBackgroundColorName": "background",
            "NSIconName": "NSActionTemplate",
            "NSMenuItem": {"default": script.name},
            "NSMessage": "runWorkflowAsService",
            "NSRequiredContext": {"NSApplicationIdentifier": "com.apple.finder"},
            "NSSendFileTypes": ["public.item"],
        }],
    }


def build_document(script: Path) -> dict:
    """document.wflow: a single Run Shell Script action, input as arguments."""
    action_info = plistlib.loads((RUN_SHELL_SCRIPT_ACTION / "Contents" / "Info.plist").read_bytes())
    action_version = action_info["CFBundleVersion"]
    string_list = {"Container": "List", "Types": ["com.apple.cocoa.string"]}
    parameter_names = ("COMMAND_STRING", "CheckedForUserDefaultShell", "inputMethod", "shell", "source")
    action = {
        "AMAccepts": {**string_list, "Optional": True},
        "AMActionVersion": action_version,
        "AMApplication": ["Automator"],
        "AMParameterProperties": {name: {} for name in parameter_names},
        "AMProvides": string_list,
        "ActionBundlePath": str(RUN_SHELL_SCRIPT_ACTION),
        "ActionName": "Run Shell Script",
        "ActionParameters": {
            "COMMAND_STRING": f'{shlex.quote(str(script))} "$@"',
            "CheckedForUserDefaultShell": True,
            "inputMethod": INPUT_AS_ARGUMENTS,
            "shell": SHELL,
            "source": "",
        },
        "BundleIdentifier": action_info["CFBundleIdentifier"],
        "CFBundleVersion": action_version,
        "CanShowSelectedItemsWhenRun": False,
        "CanShowWhenRun": True,
        "Category": ["AMCategoryUtilities"],
        "Class Name": action_info["NSPrincipalClass"],
        "InputUUID": str(uuid.uuid4()).upper(),
        "Keywords": ["Shell", "Script", "Command", "Run", "Unix"],
        "OutputUUID": str(uuid.uuid4()).upper(),
        "UUID": str(uuid.uuid4()).upper(),
        "UnlocalizedApplications": ["Automator"],
        "arguments": {},
        "isViewVisible": 1,
        "nibPath": str(RUN_SHELL_SCRIPT_ACTION / "Contents" / "Resources" / "Base.lproj" / "main.nib"),
    }
    return {
        "AMApplicationBuild": "530",
        "AMApplicationVersion": "2.10",
        "AMDocumentVersion": "2",
        "actions": [{"action": action, "isViewVisible": 1}],
        "connectors": {},
        "workflowMetaData": {
            "applicationBundleID": "com.apple.finder",
            "applicationPath": "/System/Library/CoreServices/Finder.app",
            "inputTypeIdentifier": "com.apple.Automator.fileSystemObject",
            "outputTypeIdentifier": "com.apple.Automator.nothing",
            "presentationMode": 15,
            "processesInput": False,
            "serviceApplicationBundleID": "com.apple.finder",
            "serviceApplicationPath": "/System/Library/CoreServices/Finder.app",
            "serviceInputTypeIdentifier": "com.apple.Automator.fileSystemObject",
            "serviceOutputTypeIdentifier": "com.apple.Automator.nothing",
            "serviceProcessesInput": False,
            "useAutomaticInputType": False,
            "workflowTypeIdentifier": "com.apple.Automator.servicesMenu",
        },
    }


def is_ours(workflow: Path) -> bool:
    """True when `workflow` was created by this installer (by bundle identifier)."""
    try:
        info = plistlib.loads((workflow / "Contents" / "Info.plist").read_bytes())
    except (OSError, plistlib.InvalidFileException):
        return False
    return str(info.get("CFBundleIdentifier", "")).startswith(BUNDLE_ID_PREFIX)


def install_workflow(script: Path) -> str:
    """Write the Quick Action for `script`. Returns "installed", "replaced" or "foreign"."""
    workflow = SERVICES_DIR / f"{script.name}.workflow"
    outcome = "installed"
    if workflow.exists():
        if not is_ours(workflow):
            return "foreign"
        shutil.rmtree(workflow)
        outcome = "replaced"
    contents = workflow / "Contents"
    contents.mkdir(parents=True)
    (contents / "Info.plist").write_bytes(plistlib.dumps(build_info_plist(script)))
    (contents / "document.wflow").write_bytes(plistlib.dumps(build_document(script)))
    return outcome


# %%
# Main

def main() -> int:
    if sys.platform != "darwin":
        print("This installer is for macOS only.", file=sys.stderr)
        return 1
    if not RUN_SHELL_SCRIPT_ACTION.is_dir():
        print(f"Automator action not found: {RUN_SHELL_SCRIPT_ACTION}", file=sys.stderr)
        return 1
    scripts = find_scripts()
    if not scripts:
        print(f"No executable scripts found under {REPOSITORY_DIR}", file=sys.stderr)
        return 1

    SERVICES_DIR.mkdir(parents=True, exist_ok=True)
    outcomes = {script: install_workflow(script) for script in scripts}

    foreign = [script.name for script, outcome in outcomes.items() if outcome == "foreign"]
    if foreign:
        print(
            f"NOT INSTALLED ({len(foreign)}): a workflow with the same name exists in {SERVICES_DIR} "
            f"and was not created by this installer: {', '.join(foreign)}",
            file=sys.stderr,
        )
    for script, outcome in outcomes.items():
        if outcome != "foreign":
            print(f"{outcome}: {script.name}")

    subprocess.run([PBS, "-update"], check=False)
    return 1 if foreign else 0


if __name__ == "__main__":
    sys.exit(main())
