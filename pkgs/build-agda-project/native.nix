{ runCommand, haskellPackages }:
let
  ghc = haskellPackages.ghcWithPackages (h: [
    h.Agda
    h.aeson
  ]);
in
runCommand "agda-native-resolver" { nativeBuildInputs = [ ghc ]; } ''
  mkdir -p "$out/bin"
  ghc -O1 ${../../native/Resolve.hs} -outputdir build -o "$out/bin/agda-resolve"
''
