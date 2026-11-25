"""Actual owning native compiler and graph rejections."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

repo = Path(__file__).resolve().parent.parent
with tempfile.TemporaryDirectory(prefix="agda-js-controls-") as temporary:
    for case in ("invalid-type", "external-import", "module-identity", "stale-metadata", "foreign-compiler"):
        root = Path(temporary) / case
        shutil.copytree(repo / "tests/fixtures/javascript", root,
                        ignore=shutil.ignore_patterns("_build", ".agda-purifier"))
        module = "Answer.agda"
        override = ""
        if case == "invalid-type":
            (root / module).write_text("module Answer where\nopen import Prelude\nanswer : Nat\nanswer = true\n")
            expected = "ConstructorDoesNotTargetGivenType"
        elif case == "external-import":
            with (root / module).open("a") as stream:
                stream.write('\npostulate unavailable : Nat\n{-# COMPILE JS unavailable = null; import missing from "missing-agda-runtime"; exports["unavailable"] = null #-}\n')
            expected = "Unsupported external JavaScript import"
        elif case == "module-identity":
            module = "Other.agda"
            shutil.copyfile(root / "Answer.agda", root / module)
            expected = "ModuleDefinedInOtherFile"
        elif case == "stale-metadata":
            with (root / "proof.agda-lib").open("a") as stream:
                stream.write("-- changed native metadata\n")
            expected = "Invalid or stale Agda lock"
        else:
            override = '.override { Agda = p.agda.unwrapped.overrideAttrs (_: { pname = "foreign-agda-compiler"; }); }'
            expected = "metadata API must belong to the selected native compiler"
        core = os.environ.get("AGDA_TEST_CORE_SOURCE")
        core_override = ('.override { purifier = import (/. + ' + json.dumps(core) +
                         ' + "/nix/lib") { inherit (p) lib; }; }') if core else ""
        expression = f'''let
          f = builtins.getFlake {json.dumps(str(repo))};
          p = import f.inputs.nixpkgs {{system=builtins.currentSystem; overlays=[f.overlays.default];}};
          original = p.agda-purifier.buildAgdaProject{core_override};
          builder = original{override};
        in (builder {{src=/. + {json.dumps(str(root))}; javascriptTargets.answer={json.dumps(module)};}}).javascript.answer'''
        result = subprocess.run(["nix", "build", "--impure", "--no-link", "-L", "--expr", expression],
                                text=True, capture_output=True)
        assert result.returncode != 0, (case, "unexpected success")
        assert expected in result.stderr, (case, result.stderr)
        print(json.dumps({"case": case, "exitCode": result.returncode, "diagnostic": result.stderr}))
