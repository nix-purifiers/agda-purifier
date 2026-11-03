{
  lib,
  runCommand,
  fetchgit,
  fetchurl,
  writeText,
  callPackage,
  agdaPackages,
  Agda,
  nativeResolver,
  python3,
  purifier,
  sdkVersion,
  gnutar,
  gzip,
}@scope:
{
  src,
  lockFile ? src + "/agda-purifier.lock.json",
  fetchers ? { },
  libraryOverrides ? { },
  nativeBuildInputs ? [ ],
  doCheck ? false,
  checkCommand ? "",
  buildCommand ? "agda --build-library",
}:
let
  lock = purifier.checkLock (import ./read-lock.nix { inherit lib; } { inherit src lockFile; });
  prepared = import ./environment.nix (builtins.removeAttrs scope [
    "gnutar"
    "gzip"
  ]) { inherit lock fetchers libraryOverrides; };
  rawSource = lib.cleanSourceWith {
    inherit src;
    filter =
      path: type:
      !(builtins.elem (baseNameOf path) [
        ".git"
        ".agda-purifier"
        "_build"
        "MAlonzo"
        "result"
        "__pycache__"
      ]);
  };
  source = runCommand "agda-validated-source" { } ''
    ${python3}/bin/python3 ${../agda_purifier/validate-project.py} ${nativeResolver}/bin/agda-resolve ${rawSource} ${prepared.libraryFile} ${writeText "agda-project.json" (builtins.toJSON lock.data.project)}
    mkdir -p "$out"
    cp -pr ${rawSource}/. "$out/"
  '';
  project =
    runCommand "agda-project"
      {
        nativeBuildInputs = [ Agda ] ++ nativeBuildInputs;
        inherit doCheck;
      }
      ''
        cp -pr ${source} source
        chmod -R u+w source
        cd source
        export AGDA_DIR="$TMPDIR/agda-config"
        mkdir -p "$AGDA_DIR"
        cp ${prepared.libraryFile} "$AGDA_DIR/libraries"
        : > "$AGDA_DIR/defaults"
        : > "$AGDA_DIR/executables"
        ${buildCommand}
        ${lib.optionalString doCheck checkCommand}
        mkdir -p "$out"
        cp -pr . "$out/"
      '';
  release =
    runCommand "agda-native-release"
      {
        nativeBuildInputs = [
          gnutar
          gzip
        ];
      }
      ''
        mkdir -p "$out" source/project
        cp -pr ${source}/. source/project/
        chmod -R u+rwX source
        tar --sort=name --mtime=@1 --owner=0 --group=0 --numeric-owner -czf "$out/agda-source.tar.gz" -C source project
      '';
in
assert lib.assertMsg (
  lock.data.sdk == sdkVersion && lock.data.compiler == Agda.version
) "Agda compiler or frontend SDK changed; update the lock";
{
  packages = {
    default = project;
    inherit project;
    environment = prepared.output;
  };
  tests = project;
  inherit release;
  fetches = lock.entries;
}
