{
  description = "Locked, Nix-resolved Agda libraries";
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
  inputs.purifier = {
    url = "github:nix-purifiers/purifier";
    flake = false;
  };
  outputs =
    {
      self,
      nixpkgs,
      purifier,
    }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAll = nixpkgs.lib.genAttrs systems;
      overlay = final: prev: {
        agda-purifier = final.lib.makeScope final.newScope (scope: {
          Agda = final.agda.unwrapped;
          nativeResolver = scope.callPackage ./nix/native.nix { };
          sdkVersion = import ./nix/sdk-version.nix {
            nixpkgsSrc = nixpkgs;
            Agda = scope.Agda;
          };
          cli = scope.callPackage ./nix/cli.nix {
            nixpkgsSrc = nixpkgs;
            purifierSrc = purifier;
          };
          buildAgdaProject = scope.callPackage ./nix/build-project.nix {
            purifier = import (purifier + "/nix/lib") { inherit (final) lib; };
          };
        });
      };
      pkgsFor =
        system:
        import nixpkgs {
          inherit system;
          overlays = [ overlay ];
        };
    in
    {
      overlays.default = overlay;
      packages = forAll (system: {
        default = (pkgsFor system).agda-purifier.cli;
        cli = self.packages.${system}.default;
      });
      apps = forAll (system: {
        default = {
          type = "app";
          program = "${self.packages.${system}.default}/bin/agda-purifier";
          meta.description = "Lock native Agda libraries";
        };
      });
      lib.agda-purifier.readLock = import ./nix/read-lock.nix { lib = nixpkgs.lib; };
      checks = forAll (
        system:
        let
          pkgs = pkgsFor system;
          build = pkgs.agda-purifier.buildAgdaProject {
            src = ./examples/minimal;
            doCheck = true;
            checkCommand = "agda Proof.agda";
          };
        in
        {
          inherit (build.packages) environment project;
          release = build.release;
          cli = self.packages.${system}.default;
        }
      );
      formatter = forAll (system: (pkgsFor system).nixfmt-tree);
    };
}
