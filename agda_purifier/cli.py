import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from .capture import capture
from .runtime import prepare


def locate(start):
    for directory in [start, *start.parents]:
        companion = directory / "agda-purifier.lock.json"
        if companion.exists():
            return directory, companion
    return start, start / "agda-purifier.lock.json"


def main():
    args = sys.argv[1:]
    if args and args[0] == "--native":
        args = args[1:]
        root, companion = locate(Path.cwd())
        root = Path(os.environ.get("AGDA_PURIFIER_PROJECT", root)).resolve()
        companion = Path(os.environ.get("AGDA_PURIFIER_LOCK", companion)).resolve()
        if not companion.exists():
            print(
                "agda-purifier: no lockfile; using ordinary impure Agda resolution",
                file=sys.stderr,
            )
            os.execv(
                os.environ["AGDA_PURIFIER_ORIGINAL"],
                [os.environ["AGDA_PURIFIER_ORIGINAL"], *args],
            )
        if any(a == "--library-file" or a.startswith("--library-file=") for a in args):
            raise ValueError(
                "The locked wrapper supplies its library registry; update the lock to change libraries"
            )
        manifest, env = prepare(root, companion)
        os.execve(
            manifest["compiler"],
            [
                manifest["compiler"],
                "--library-file=" + manifest["libraries"],
                "--no-default-libraries",
                *args,
            ],
            env,
        )
    parser = argparse.ArgumentParser(description="Lock native Agda libraries")
    parser.add_argument(
        "action", choices=["lock", "prefetch", "exec", "bundle", "publish"]
    )
    parser.add_argument("--project", type=Path)
    parser.add_argument("--lock", type=Path)
    parser.add_argument("--libraries", type=Path)
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--input", action="append", default=[])
    parser.add_argument("--tag")
    opts, remaining = parser.parse_known_args(args)
    root, companion = locate(Path.cwd())
    if opts.project:
        root = opts.project.resolve()
    companion = opts.lock.resolve() if opts.lock else root / "agda-purifier.lock.json"
    if opts.action == "lock":
        if remaining:
            parser.error("Unexpected arguments: " + " ".join(remaining))
        capture(root, companion, opts.libraries, opts.update, opts.input)
    elif opts.action in ("prefetch", "exec"):
        manifest, env = prepare(root, companion)
        if opts.action == "exec":
            if remaining and remaining[0] == "--":
                remaining = remaining[1:]
            if not remaining:
                parser.error("exec requires a command")
            env["PATH"] = (
                str(Path(os.environ["AGDA_PURIFIER_SDK"]) / "bin")
                + os.pathsep
                + env["PATH"]
            )
            env.update(
                AGDA_PURIFIER_PROJECT=str(root), AGDA_PURIFIER_LOCK=str(companion)
            )
            os.execvpe(remaining[0], remaining, env)
    else:
        from .common import load

        load(root, companion)
        expression = (
            "import "
            + json.dumps(
                os.environ["AGDA_PURIFIER_SDK"] + "/lib/agda-purifier/pkgs/build-agda-project/release.nix"
            )
            + " {root="
            + json.dumps(str(root))
            + ";lockFile="
            + json.dumps(str(companion))
            + ";}"
        )
        result = subprocess.run(
            [
                "nix",
                "build",
                "--impure",
                "--expr",
                expression,
                "--no-link",
                "--print-out-paths",
            ],
            check=True,
            text=True,
            capture_output=True,
        )
        artifact = Path(result.stdout.strip()) / "agda-source.tar.gz"
        if opts.action == "bundle":
            print(artifact)
        else:
            if not opts.tag:
                parser.error("publish requires --tag")
            subprocess.run(
                [
                    os.environ.get("AGDA_PURIFIER_GH", "gh"),
                    "release",
                    "upload",
                    opts.tag,
                    str(artifact),
                    "--clobber",
                ],
                cwd=root,
                check=True,
            )


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        print("agda-purifier: " + str(error), file=sys.stderr)
        raise SystemExit(1)
