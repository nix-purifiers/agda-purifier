"""Native Agda version selection, Git capture and native metadata binding."""

import json
from pathlib import Path
import shutil
import subprocess
import tempfile

repo = Path(__file__).resolve().parent.parent
cli = (
    Path(
        subprocess.check_output(
            ["nix", "build", str(repo) + "#", "--no-link", "--print-out-paths"],
            text=True,
        ).strip()
    )
    / "bin/agda-purifier"
)
expr = (
    "let f=builtins.getFlake "
    + json.dumps(str(repo))
    + ";p=import f.inputs.nixpkgs {overlays=[f.overlays.default];};in p.agda-purifier.nativeResolver"
)
resolver = (
    Path(
        subprocess.check_output(
            [
                "nix",
                "build",
                "--impure",
                "--expr",
                expr,
                "--no-link",
                "--print-out-paths",
            ],
            text=True,
        ).strip()
    )
    / "bin/agda-resolve"
)


def call(root, companion, *args, expected=0):
    result = subprocess.run(
        [cli, *args, "--project", root, "--lock", companion],
        text=True,
        capture_output=True,
    )
    assert result.returncode == expected, result
    return result


with tempfile.TemporaryDirectory(prefix="agda-native-capture-") as temp:
    temp = Path(temp)
    fixture = temp / "fixture"
    fixture.mkdir()
    (fixture / "test.agda-lib").write_text("name: test\ninclude: .\ndepend: library\n")
    registry = temp / "libraries"
    files = []
    for version in ["1", "2"]:
        lib = temp / ("library-" + version + ".agda-lib")
        lib.write_text("name: library-" + version + "\ninclude: .\n")
        files.append(lib)
    registry.write_text("".join(str(f) + "\n" for f in files))
    result = subprocess.run(
        [resolver, fixture, registry], text=True, capture_output=True, check=True
    )
    assert [n["name"] for n in json.loads(result.stdout)["libraries"]] == ["library-2"]
    alias = temp / "alias.agda-lib"
    alias.write_text("name: library-02\ninclude: .\n")
    registry.write_text(registry.read_text() + str(alias) + "\n")
    result = subprocess.run(
        [resolver, fixture, registry], text=True, capture_output=True
    )
    assert result.returncode != 0 and "AmbiguousLib" in result.stdout, result
    unversioned = temp / "plain.agda-lib"
    unversioned.write_text("name: library\ninclude: .\n")
    registry.write_text(registry.read_text() + str(unversioned) + "\n")
    result = subprocess.run(
        [resolver, fixture, registry], text=True, capture_output=True, check=True
    )
    assert [n["name"] for n in json.loads(result.stdout)["libraries"]] == ["library"]
    root = temp / "project"
    shutil.copytree(
        repo / "examples/minimal",
        root,
        ignore=shutil.ignore_patterns("_build", ".agda-purifier"),
    )
    companion = root / "agda-purifier.lock.json"
    original = companion.read_bytes()
    call(root, companion, "lock")
    assert companion.read_bytes() == original
    source = temp / "source"
    subprocess.run(
        [
            "git",
            "clone",
            "--quiet",
            "https://github.com/UlfNorell/agda-prelude",
            source,
        ],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            source,
            "checkout",
            "--quiet",
            "4230566d3ae229b6a00258587651ac7bfd38d088",
        ],
        check=True,
    )
    registry.write_text(str(source / "agda-prelude.agda-lib") + "\n")
    (root / "selection.txt").write_text("Tracked selection\n")
    call(
        root,
        companion,
        "lock",
        "--update",
        "--libraries",
        str(registry),
        "--input",
        "selection.txt",
    )
    data = json.loads(companion.read_text())
    assert (
        data["extraInputs"] == ["selection.txt"]
        and data["nodes"][0]["rev"] == "4230566d3ae229b6a00258587651ac7bfd38d088"
    )
    call(root, companion, "prefetch")
    (source / "src/Prelude.agda").write_text(
        (source / "src/Prelude.agda").read_text() + "\n"
    )
    assert (
        "clean"
        in call(
            root,
            companion,
            "lock",
            "--update",
            "--libraries",
            str(registry),
            expected=1,
        ).stderr
    )
    assert json.loads(companion.read_text()) == data
    data["nodes"][0]["content"] += "\n"
    companion.write_text(json.dumps(data))
    failed = call(root, companion, "prefetch", expected=1)
    assert "metadata differs" in failed.stderr or "contents differ" in failed.stderr, (
        failed
    )
print("Native Agda version selection, Git capture and metadata binding passed")
