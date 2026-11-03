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
  builder = pkgs.callPackage ./build-project.nix {
    inherit
      nativeResolver
      purifier
      sdkVersion
      Agda
      ;
  };
in
(builder {
  src = /. + root;
  lockFile = /. + lockFile;
}).release
