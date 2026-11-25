"""Join original captured dependency sources to the actual prepared libraries."""
import hashlib
import json
from pathlib import Path
import sys

records = []
extensions = tuple(json.loads(Path(sys.argv[3]).read_text())["sourceExtensions"] + [".agda-lib"])
for dependency in json.loads(Path(sys.argv[1]).read_text()):
    original = Path(dependency["original"])
    installed = Path(dependency["installed"])
    sources = {}
    for file in sorted(original.rglob("*")):
        if file.is_file() and file.name.endswith(extensions):
            relative = file.relative_to(original)
            assert file.read_bytes() == (installed / relative).read_bytes(), relative
            sources[str(relative)] = hashlib.sha256(file.read_bytes()).hexdigest()
    interfaces = {str(file.relative_to(installed)): hashlib.sha256(file.read_bytes()).hexdigest()
                  for file in sorted(installed.rglob("*.agdai"))}
    assert sources and interfaces, dependency["name"]
    records.append({**dependency, "originalSources": sources, "compiledInterfaces": interfaces})
Path(sys.argv[2]).write_text(json.dumps(records, indent=2, sort_keys=True) + "\n")
