{ root, lockFile }:
let
  pkgs = import (builtins.toPath "@nixpkgs@") { };
  lib = pkgs.lib;
  Agda = pkgs.agda.unwrapped;
  purifier = import ((builtins.toPath "@purifier@") + "/nix/lib") { inherit lib; };
  nativeResolver = pkgs.callPackage ./native.nix { };
  sdkVersion = import ./sdk-version.nix {
    nixpkgsSrc = (builtins.toPath "@nixpkgs@");
    inherit Agda;
  };
  lock = purifier.checkLock (
    import ./read-lock.nix { inherit lib; } {
      src = /. + root;
      lockFile = /. + lockFile;
    }
  );
  prepared =
    pkgs.callPackage ./environment.nix
      {
        inherit
          nativeResolver
          purifier
          sdkVersion
          Agda
          ;
      }
      {
        inherit lock;
      };
in
assert lib.assertMsg (lock.data.sdk == sdkVersion) "Agda frontend SDK changed; update the lock";
prepared.output
