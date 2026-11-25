{
  runCommand,
  haskellPackages,
  Agda,
}:
let
  api = haskellPackages.Agda;
  ghc = haskellPackages.ghcWithPackages (h: [
    h.Agda
    h.aeson
  ]);
in
assert Agda.drvPath == api.drvPath;
runCommand "agda-native-javascript-inspector"
  {
    nativeBuildInputs = [ ghc ];
    passthru.compiler = Agda;
  }
  ''
    mkdir -p "$out/bin"
    ghc -O1 ${../../native/InspectJavascript.hs} -outputdir build -o "$out/bin/agda-javascript-inspect"
  ''
