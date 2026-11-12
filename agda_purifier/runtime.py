import hashlib
import json
import os
from pathlib import Path
import subprocess

from .common import environment, load, metadata, resolve


def prepare(root, companion):
    data = load(root, companion)
    state = root / ".agda-purifier"
    state.mkdir(exist_ok=True)
    profile = state / "environment-profile"
    expression = f"import {json.dumps(os.environ['AGDA_PURIFIER_SDK'] + '/lib/agda-purifier/pkgs/build-agda-project/realize.nix')} {{root={json.dumps(str(root))};lockFile={json.dumps(str(companion))};}}"
    built = subprocess.run(
        [
            "nix",
            "build",
            "--impure",
            "--expr",
            expression,
            "--out-link",
            str(profile),
            "--print-out-paths",
        ],
        text=True,
        capture_output=True,
    )
    if built.returncode:
        raise ValueError(built.stdout + built.stderr)
    output = Path(built.stdout.strip())
    manifest = json.loads((output / "manifest.json").read_text())
    env = dict(environment(), AGDA_DIR=str(state / "config"))
    config = state / "config"
    config.mkdir(exist_ok=True)
    (config / "libraries").write_text(Path(manifest["libraries"]).read_text())
    (config / "defaults").write_text("")
    (config / "executables").write_text("")
    selected = resolve(root, manifest["libraries"], env)
    actual = [metadata(p, root) for p in selected["project"]]
    if actual != data["project"]:
        raise ValueError("Native Agda project selection differs from the lock")
    if manifest["version"] != data["compiler"] or manifest["sdk"] != data["sdk"]:
        raise ValueError("Compiler or frontend SDK differs from the lock")
    generation = hashlib.sha256(
        companion.read_bytes() + os.environ["AGDA_PURIFIER_SDK"].encode()
    ).hexdigest()[:20]
    # The paths must carry Nix string context, rather than plain JSON strings.
    expr = (
        "let p=import "
        + os.environ["AGDA_PURIFIER_NIXPKGS"]
        + " {};e=builtins.storePath "
        + json.dumps(str(output))
        + ";s=builtins.storePath "
        + json.dumps(os.environ["AGDA_PURIFIER_SDK"])
        + ';in p.writeText "agda-session.json" (builtins.toJSON {environment="${e}";sdk="${s}";})'
    )
    rooted = subprocess.run(
        [
            "nix",
            "build",
            "--impure",
            "--expr",
            expr,
            "--out-link",
            str(state / ("session-" + generation)),
        ],
        text=True,
        capture_output=True,
    )
    if rooted.returncode:
        raise ValueError(rooted.stderr)
    return manifest, env
