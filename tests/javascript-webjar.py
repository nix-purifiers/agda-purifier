import os
from pathlib import Path
import subprocess
import sys
import zipfile

producer, repository = map(Path, sys.argv[1:])
files = sorted((producer / "javascript").glob("*.mjs"))
jars = list(repository.rglob("*.jar"))
assert len(jars) == 1, jars
prefixes = set()
with zipfile.ZipFile(jars[0]) as jar:
    for file in files:
        entries = [name for name in jar.namelist() if name.endswith("/" + file.name)]
        assert len(entries) == 1, (file, entries)
        assert jar.read(entries[0]) == file.read_bytes(), file
        prefixes.add(entries[0][:-len(file.name)])
assert len(prefixes) == 1, prefixes
prefix = prefixes.pop()
assert prefix.startswith("META-INF/resources/webjars/"), prefix
subprocess.run(["java", "-Dprefix=/" + prefix, "-cp", "." + os.pathsep + str(jars[0]),
                "JavascriptResource", *map(str, files)], check=True)
print("Native Agda WebJar and ordinary Java classloader byte joins PASS")
