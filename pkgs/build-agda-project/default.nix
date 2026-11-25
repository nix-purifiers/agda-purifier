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
  javascriptInspector,
  nodejs,
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
  javascriptTargets ? { },
  javascriptWebjars ? { },
}:
let
  lock = purifier.checkLock (
    import ../../lib-overlays/default/read-lock.nix { inherit lib; } { inherit src lockFile; }
  );
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
    ${python3}/bin/python3 ${../../agda_purifier/validate-project.py} ${nativeResolver}/bin/agda-resolve ${rawSource} ${prepared.libraryFile} ${writeText "agda-project.json" (builtins.toJSON lock.data.project)}
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
  javascript = lib.mapAttrs (
    name: moduleFile:
    assert lib.assertMsg (
      javascriptInspector.compiler.drvPath == Agda.drvPath
    ) "Agda JavaScript metadata API must belong to the selected native compiler";
    assert lib.assertMsg (
      builtins.match "[A-Za-z][A-Za-z0-9_-]*" name != null
    ) "Agda JavaScript target names must be simple identifiers";
    assert lib.assertMsg (
      builtins.isString moduleFile
      && moduleFile != ""
      && !(lib.hasPrefix "/" moduleFile)
      && !(builtins.elem ".." (lib.splitString "/" moduleFile))
    ) "Agda JavaScript targets select relative source files";
    assert lib.assertMsg (
      lock.data.project != [ ]
    ) "Agda JavaScript targets require captured native library metadata";
    runCommand "agda-${name}-javascript"
      {
        nativeBuildInputs = [
          Agda
          nodejs
        ];
      }
      ''
        cp -pr ${source} source
        chmod -R u+w source
        cd source
        export AGDA_DIR="$TMPDIR/agda-config"
        mkdir -p "$AGDA_DIR" "$out/nix-support/agda-javascript"
        cp ${prepared.libraryFile} "$AGDA_DIR/libraries"
        : > "$AGDA_DIR/defaults"
        : > "$AGDA_DIR/executables"
        ${javascriptInspector}/bin/agda-javascript-inspect ${lib.escapeShellArg moduleFile} \
          > "$out/nix-support/agda-javascript/selection.json"
        agda --js --js-es6 --compile-dir "$out/javascript" ${lib.escapeShellArg moduleFile}
        node --experimental-vm-modules ${./javascript-graph.mjs} "$out/javascript" \
          "$out/nix-support/agda-javascript/selection.json" \
          > "$out/nix-support/agda-javascript/modules.json"
        ${python3}/bin/python3 ${./javascript-proof.py} ${source} "$out/javascript" \
          "$out/nix-support/agda-javascript/selection.json" ${lib.getOutput "data" Agda} \
          ${lib.getExe Agda} "$out/nix-support/agda-javascript/proof.json"
        ${python3}/bin/python3 ${./javascript-dependencies.py} \
          ${
            writeText "agda-javascript-dependencies.json" (
              builtins.toJSON (
                map (node: {
                  inherit (node) name rev;
                  original = "${prepared.tree}/${node.entry}";
                  installed = toString prepared.libraries.${node.name};
                }) lock.data.nodes
              )
            )
          } \
          "$out/nix-support/agda-javascript/dependencies.json" \
          "$out/nix-support/agda-javascript/selection.json"
      ''
  ) javascriptTargets;
  projections = lib.mapAttrs (
    name: _:
    let
      producer = javascript.${name};
      resources = purifier.resourceProjections {
        inherit producer runCommand python3;
        roots."." = "javascript";
        name = "agda-${name}-javascript-resources";
      };
    in
    resources
    // lib.optionalAttrs (javascriptWebjars ? ${name}) (
      assert lib.assertMsg (
        builtins.isAttrs javascriptWebjars.${name}
        &&
          builtins.attrNames (
            builtins.removeAttrs javascriptWebjars.${name} [
              "groupId"
              "artifactId"
              "version"
            ]
          ) == [ ]
        && javascriptWebjars.${name} ? artifactId
        && javascriptWebjars.${name} ? version
      ) "Agda WebJar options require artifactId/version and optional groupId";
      purifier.webjarProjections (
        {
          inherit producer runCommand python3;
          assets = resources.web.directory;
          name = "agda-${name}-javascript-webjar";
        }
        // javascriptWebjars.${name}
      )
    )
  ) javascriptTargets;
in
assert lib.assertMsg (builtins.all (name: javascriptTargets ? ${name}) (
  builtins.attrNames javascriptWebjars
)) "Agda WebJar coordinates require a selected JavaScript target";
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
  inherit release javascript projections;
  fetches = lock.entries;
}
