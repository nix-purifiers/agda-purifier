import hashlib
import json
import os
from pathlib import Path
import subprocess


def environment():
    return {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("AGDA_", "GHC_", "GHC_PACKAGE"))
        and k not in ("GHCRTS", "GHC_ENVIRONMENT")
    }


def command(args, **kwargs):
    result = subprocess.run(args, capture_output=True, text=True, **kwargs)
    if result.returncode:
        raise ValueError(result.stdout + result.stderr)
    return result.stdout.strip()


def resolve(root, libraries, env=None):
    return json.loads(
        command(
            [os.environ["AGDA_PURIFIER_RESOLVER"], str(root), str(libraries)], env=env
        )
    )


def relative(path, root):
    value = Path(path).resolve()
    if not value.is_relative_to(root):
        raise ValueError("Library metadata must refer to paths inside its source tree")
    return str(value.relative_to(root))


def metadata(record, root):
    return {
        **record,
        "file": relative(record["file"], root),
        "includes": [relative(p, root) for p in record["includes"]],
    }


def inputs(root, names):
    result = {}
    for name in sorted(set(names)):
        f = root / name
        if (
            Path(name).is_absolute()
            or ".." in Path(name).parts
            or not f.is_file()
            or f.is_symlink()
        ):
            raise ValueError("Selection inputs must be regular project files")
        result[name] = {"sha256": hashlib.sha256(f.read_bytes()).hexdigest()}
    return result


def load(root, companion):
    data = json.loads(companion.read_text())
    if data.get("version") != 1 or data.get("purifier") != "agda":
        raise ValueError("Unsupported Agda lock")
    if data["sdk"] != os.environ["AGDA_PURIFIER_SDK_VERSION"]:
        raise ValueError("Agda frontend SDK changed; update the lock")
    names = data["extraInputs"] + [p["file"] for p in data["project"]]
    if inputs(root, names) != data["inputs"]:
        raise ValueError("Selection inputs changed; update the lock")
    return data
