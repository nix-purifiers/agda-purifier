{ nixpkgsSrc, Agda }:
builtins.hashString "sha256" (
  builtins.toJSON {
    nixpkgs = toString nixpkgsSrc;
    version = Agda.version;
    resolver = builtins.hashFile "sha256" ../native/Resolve.hs;
  }
)
