import json
from pathlib import Path
import subprocess
import sys

resolver, directory, libraries, expected_file = sys.argv[1:]
root = Path(directory).resolve()
expected = json.loads(Path(expected_file).read_text())
data = json.loads(
    subprocess.check_output([resolver, "--metadata", libraries], text=True)
)
records = []
for item in data["libraries"]:
    file = Path(item["file"]).resolve()
    if file == root / expected["file"]:
        records.append(
            {
                **item,
                "file": str(file.relative_to(root)),
                "includes": [
                    str(Path(p).resolve().relative_to(root)) for p in item["includes"]
                ],
            }
        )
if records != [
    {k: expected[k] for k in ("name", "file", "includes", "dependencies", "requests")}
]:
    raise SystemExit("Native Agda library metadata differs from the lock")
if (root / expected["file"]).read_text() != expected["content"]:
    raise SystemExit("Native Agda library contents differ from the lock")
