"""Native Agda/editor, source edits, private configuration and ordinary consumer."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

repo = Path(__file__).resolve().parent.parent
cli = (
    Path(
        subprocess.check_output(
            ["nix", "build", str(repo) + "#", "--no-link", "--print-out-paths"],
            text=True,
        ).strip()
    )
    / "bin"
)


def call(cwd, *args, env=None, expected=0, input=None):
    result = subprocess.run(
        [str(cli / args[0]), *args[1:]],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        input=input,
    )
    assert result.returncode == expected, (args, result)
    return result


with tempfile.TemporaryDirectory(prefix="agda proof with spaces ") as temp:
    temp = Path(temp)
    root = temp / "project"
    shutil.copytree(
        repo / "examples/minimal",
        root,
        ignore=shutil.ignore_patterns("_build", ".agda-purifier"),
    )
    poison = temp / "poison"
    poison.mkdir()
    (poison / "libraries").write_text("/missing/host-library.agda-lib\n")
    (poison / "defaults").write_text("unlocked-host-library\n")
    env = dict(os.environ, AGDA_DIR=str(poison), GHC_PACKAGE_PATH="/missing/host-ghc")
    call(root, "agda", "Proof.agda", env=env)
    manifest = json.loads(
        (
            (root / ".agda-purifier/environment-profile").resolve() / "manifest.json"
        ).read_text()
    )
    library = Path(next(iter(manifest["packages"].values())))
    assert list(library.rglob("Prelude.agda")) and list(library.rglob("Prelude.agdai"))
    proof = root / "Proof.agda"
    original = proof.read_text()
    proof.write_text(original.replace("id 42", "id 43"))
    failed = subprocess.run(
        [cli / "agda", "Proof.agda"], cwd=root, text=True, capture_output=True, env=env
    )
    assert (
        failed.returncode != 0
        and "43" in failed.stdout + failed.stderr
        and "42" in failed.stdout + failed.stderr
    ), failed
    proof.write_text(original.replace("42", "43"))
    call(root, "agda", "Proof.agda", env=env)
    proof.write_text(original)
    call(root, "agda", "Proof.agda", env=env)
    editor = call(
        root,
        "agda",
        "--interaction-json",
        env=env,
        input='IOTCM "Proof.agda" NonInteractive Direct (Cmd_load "Proof.agda" [])\n',
    )
    messages = []
    for line in editor.stdout.replace("JSON> ", "").splitlines():
        if line.startswith("{"):
            messages.append(json.loads(line))
    assert any(m.get("status", {}).get("checked") for m in messages)
    assert any(
        str(library) + "/src/Prelude/Function.agda" in json.dumps(m) for m in messages
    ), editor.stdout
    before = (root / "proof.agda-lib").read_text()
    (root / "proof.agda-lib").write_text(before + "flags: --safe\n")
    stale = subprocess.run(
        [cli / "agda", "Proof.agda"], cwd=root, text=True, capture_output=True
    )
    assert stale.returncode == 1 and "Selection inputs changed" in stale.stderr, stale
    (root / "proof.agda-lib").write_text(before)
    subdir = root / "subdir"
    subdir.mkdir()
    call(subdir, "agda", str(proof))
    companion = temp / "external.json"
    (root / "agda-purifier.lock.json").rename(companion)
    external = dict(
        env, AGDA_PURIFIER_PROJECT=str(root), AGDA_PURIFIER_LOCK=str(companion)
    )
    call(subdir, "agda", str(proof), env=external)
    call(root, "agda-purifier", "prefetch", "--lock", str(companion))
    sessions = list((root / ".agda-purifier").glob("session-*"))
    assert sessions
    refs = subprocess.check_output(
        ["nix-store", "--query", "--requisites", str(sessions[0].resolve())], text=True
    )
    assert str(cli.parent) in refs and str(library) in refs
    archive = Path(
        call(root, "agda-purifier", "bundle", "--lock", str(companion)).stdout.strip()
    )
    fake_gh = temp / "fake-gh"
    fake_gh.write_text(
        "#!/usr/bin/env python3\nimport pathlib,sys\n"
        "assert sys.argv[1:4]==['release','upload','v0.1.0']\n"
        "pathlib.Path(__file__).with_suffix('.uploaded').write_bytes(pathlib.Path(sys.argv[4]).read_bytes())\n"
    )
    fake_gh.chmod(0o755)
    publication = dict(os.environ, AGDA_PURIFIER_GH=str(fake_gh))
    call(
        root,
        "agda-purifier",
        "publish",
        "--lock",
        str(companion),
        "--tag",
        "v0.1.0",
        env=publication,
    )
    assert fake_gh.with_suffix(".uploaded").read_bytes() == archive.read_bytes()
    consumer = temp / "ordinary"
    consumer.mkdir()
    with tarfile.open(archive) as tar:
        tar.extractall(consumer, filter="data")
    # No lock: same wrapper delegates to its original native compiler.
    (consumer / "project/agda-purifier.lock.json").unlink(missing_ok=True)
    native = call(
        consumer / "project",
        "agda",
        "--library-file=" + manifest["libraries"],
        "--no-default-libraries",
        "Proof.agda",
    )
    assert "ordinary impure" in native.stderr
    fallback = temp / "fallback"
    fallback.mkdir()
    result = call(fallback, "agda", "--version")
    assert "ordinary impure" in result.stderr and "2.8.0" in result.stdout
    fake = temp / "fake-agda"
    fake.write_text("#!/bin/sh\nprintf native-out\nprintf native-err >&2\nexit 7\n")
    fake.chmod(0o755)
    # Call the Python entry directly to exercise streams and status delegation.
    e = dict(os.environ, AGDA_PURIFIER_ORIGINAL=str(fake))
    entry = cli.parent / "lib/agda-purifier"
    e["PYTHONPATH"] = str(entry)
    result = subprocess.run(
        ["python3", "-m", "agda_purifier.cli", "--native"],
        cwd=fallback,
        env=e,
        text=True,
        capture_output=True,
    )
    assert (
        result.returncode == 7
        and result.stdout == "native-out"
        and result.stderr.endswith("native-err")
    ), result
print(
    "Native Agda/editor, source edits, private config, GC roots and ordinary consumer passed"
)
