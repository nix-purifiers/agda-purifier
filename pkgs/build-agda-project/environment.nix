{
  lib,
  runCommand,
  fetchgit,
  fetchurl,
  writeText,
  agdaPackages,
  Agda,
  nativeResolver,
  python3,
  purifier,
  sdkVersion,
  ...
}@scope:
{
  lock,
  fetchers ? { },
  libraryOverrides ? { },
}:
let
  data = lock.data;
  tree = purifier.tree (
    {
      name = "agda-locked-sources";
      entries = lock.entries;
      inherit
        runCommand
        fetchgit
        fetchurl
        python3
        writeText
        ;
    }
    // fetchers
  );
  definitions = builtins.listToAttrs (
    map (n: {
      name = n.name;
      value = n;
    }) data.nodes
  );
  libraries = lib.mapAttrs (
    name: node:
    let
      dependencyNames = map (item: item.key) (
        builtins.genericClosure {
          startSet = map (name: { key = name; }) node.dependencies;
          operator = item: map (name: { key = name; }) definitions.${item.key}.dependencies;
        }
      );
      deps = map (n: libraries.${n}) dependencyNames;
      source = purifier.tree (
        {
          name = "agda-library-source";
          entries = builtins.filter (e: e.path == node.entry) lock.entries;
          inherit
            runCommand
            fetchgit
            fetchurl
            python3
            writeText
            ;
        }
        // fetchers
      );
      registration = writeText "agda-validation-libraries" (
        lib.concatMapStrings (p: "${p}/${p.libraryFile}\n") deps
      );
    in
    agdaPackages.mkDerivation (
      {
        pname = "agda-${name}";
        version = builtins.substring 0 12 node.rev;
        src = runCommand "agda-source" { } ''
          mkdir -p "$out"
          cp -pr ${source}/${node.entry}/. "$out/"
        '';
        libraryName = name;
        libraryFile = node.file;
        buildInputs = deps;
        preBuild = ''
          { printf '%s\n' "$PWD/${node.file}"; cat ${registration}; } > "$TMPDIR/validation-libraries"
          ${python3}/bin/python3 ${../../agda_purifier/check-metadata.py} ${nativeResolver}/bin/agda-resolve "$PWD" \
            "$TMPDIR/validation-libraries" \
            ${writeText "agda-library.json" (builtins.toJSON node)}
        '';
        buildPhase = ''
          runHook preBuild
          (cd ${lib.escapeShellArg (dirOf node.file)}; agda --build-library)
          runHook postBuild
        '';
        meta = { };
      }
      // (libraryOverrides.${name} or { })
    )
  ) definitions;
  libraryFile = writeText "agda-locked-libraries" (
    lib.concatMapStrings (p: "${p}/${p.libraryFile}\n") (builtins.attrValues libraries)
  );
  manifest = writeText "agda-environment.json" (
    builtins.toJSON {
      compiler = lib.getExe Agda;
      libraries = libraryFile;
      packages = libraries;
      version = Agda.version;
      sdk = sdkVersion;
    }
  );
  output = runCommand "agda-locked-environment" { } ''
    mkdir -p "$out"
    ln -s ${manifest} "$out/manifest.json"
    ln -s ${libraryFile} "$out/libraries"
  '';
in
{
  inherit
    tree
    libraries
    libraryFile
    output
    ;
}
