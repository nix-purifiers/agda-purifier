import json
from pathlib import Path
import subprocess
import sys

resolver, directory, libraries, expected_file = sys.argv[1:]
root = Path(directory).resolve()
expected = json.loads(Path(expected_file).read_text())
data = json.loads(subprocess.check_output([resolver, str(root), libraries], text=True))
actual = []
for item in data["project"]:
    actual.append(
        {
            **item,
            "file": str(Path(item["file"]).resolve().relative_to(root)),
            "includes": [
                str(Path(p).resolve().relative_to(root)) for p in item["includes"]
            ],
        }
    )
if actual != expected:
    raise SystemExit("Native Agda project selection differs from the lock")
