import json
import os
from pathlib import Path
import re

from .common import command, inputs, load, metadata, resolve


def capture(root, companion, libraries=None, update=False, extra=()):
    if companion.exists() and not update:
        load(root, companion)
        return
    previous = json.loads(companion.read_text()) if companion.exists() else {}
    extra = list(extra or previous.get("extraInputs", []))
    if libraries is None:
        appdir = command([os.environ["AGDA_PURIFIER_ORIGINAL"], "--print-agda-app-dir"])
        libraries = Path(appdir) / "libraries"
    selected = resolve(root, libraries)
    projects = [metadata(p, root) for p in selected["project"]]
    if not projects:
        raise ValueError("Create a native .agda-lib file before locking this project")
    nodes, entries, trees = [], [], {}
    for record in selected["libraries"]:
        file = Path(record["file"]).resolve()
        tree = Path(
            command(["git", "-C", str(file.parent), "rev-parse", "--show-toplevel"])
        ).resolve()
        if command(["git", "-C", str(tree), "status", "--porcelain"]):
            raise ValueError("Registered dependency Git trees must be clean")
        rev = command(["git", "-C", str(tree), "rev-parse", "HEAD"])
        url = command(["git", "-C", str(tree), "remote", "get-url", "origin"])
        if not re.fullmatch("[a-f0-9]{40}", rev):
            raise ValueError("Dependencies require exact Git commits")
        if not re.fullmatch("[A-Za-z0-9_+.-]+", record["name"]) or record["name"] in (
            ".",
            "..",
        ):
            raise ValueError("Unsupported native library name")
        node = metadata(record, tree)
        if "." in node["dependencies"]:
            raise ValueError(
                "Dependency libraries cannot depend on the mutable project directory"
            )
        key = (url, rev)
        if key not in trees:
            fetched = json.loads(
                command(
                    [
                        os.environ["AGDA_PURIFIER_PREFETCH_GIT"],
                        "--url",
                        url,
                        "--rev",
                        rev,
                    ]
                )
            )
            entry = "sources/" + str(len(entries))
            entries.append(
                {
                    "path": entry,
                    "hash": fetched["hash"],
                    "git": {
                        "url": url,
                        "rev": rev,
                        "submodules": False,
                        "leaveDotGit": False,
                        "commitObject": None,
                    },
                }
            )
            trees[key] = entry
        node.update(entry=trees[key], url=url, rev=rev)
        node["content"] = file.read_text()
        nodes.append(node)
    data = {
        "version": 1,
        "purifier": "agda",
        "sdk": os.environ["AGDA_PURIFIER_SDK_VERSION"],
        "compiler": os.environ["AGDA_PURIFIER_COMPILER_VERSION"],
        "project": projects,
        "nodes": sorted(nodes, key=lambda n: n["name"]),
        "entries": entries,
        "extraInputs": extra,
        "inputs": inputs(root, extra + [p["file"] for p in projects]),
    }
    companion.parent.mkdir(parents=True, exist_ok=True)
    temporary = companion.with_name(companion.name + ".tmp")
    temporary.write_text(json.dumps(data, sort_keys=True, indent=2) + "\n")
    temporary.replace(companion)
