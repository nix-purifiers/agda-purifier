"""Preserve and bind original authored inputs and compiler runtime bytes."""
import hashlib
import json
from pathlib import Path
import sys

source, output, selection_file, expected_sdk_data, compiler, destination = sys.argv[1:]
selection = json.loads(Path(selection_file).read_text())
data = Path(selection["sdkData"]).resolve()
assert data.is_relative_to(Path(expected_sdk_data).resolve()), "Foreign Agda SDK data"
runtime = data / "JS/agda-rts.mjs"
installed = Path(output) / "agda-rts.mjs"
assert runtime.read_bytes() == installed.read_bytes(), "Native runtime bytes changed"
inputs = {}
for original in sorted(Path(source).rglob("*")):
    if original.is_file():
        relative = original.relative_to(source)
        assert original.read_bytes() == Path(relative).read_bytes(), relative
        inputs[str(relative)] = hashlib.sha256(original.read_bytes()).hexdigest()
Path(destination).write_text(json.dumps({
    "selection": selection,
    "compiler": compiler,
    "compilerSha256": hashlib.sha256(Path(compiler).read_bytes()).hexdigest(),
    "originalRuntime": str(runtime),
    "originalRuntimeSha256": hashlib.sha256(runtime.read_bytes()).hexdigest(),
    "authoredInputs": inputs,
}, sort_keys=True, indent=2) + "\n")
