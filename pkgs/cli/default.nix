{
  lib,
  stdenvNoCC,
  makeWrapper,
  python3,
  nix,
  gh,
  git,
  nix-prefetch-git,
  Agda,
  nativeResolver,
  sdkVersion,
  nixpkgsSrc,
  purifierSrc,
  cacert,
}:
stdenvNoCC.mkDerivation {
  pname = "agda-purifier";
  version = "0.1.0";
  src = ../..;
  nativeBuildInputs = [ makeWrapper ];
  dontBuild = true;
  installPhase = ''
    mkdir -p "$out/bin" "$out/lib/agda-purifier"
    cp -r agda_purifier pkgs lib-overlays native "$out/lib/agda-purifier/"
    install -m755 bin/agda-purifier "$out/bin/agda-purifier"
    for file in realize release; do
      substituteInPlace "$out/lib/agda-purifier/pkgs/build-agda-project/$file.nix" \
        --replace-fail '@nixpkgs@' '${nixpkgsSrc}' \
        --replace-fail '@purifier@' '${purifierSrc}'
    done
    wrapProgram "$out/bin/agda-purifier" \
      --prefix PATH : ${
        lib.makeBinPath [
          python3
          nix
          gh
          git
        ]
      } \
      --set-default SSL_CERT_FILE ${cacert}/etc/ssl/certs/ca-bundle.crt \
      --set-default AGDA_PURIFIER_GH ${gh}/bin/gh \
      --set AGDA_PURIFIER_ORIGINAL ${lib.getExe Agda} \
      --set AGDA_PURIFIER_RESOLVER ${nativeResolver}/bin/agda-resolve \
      --set AGDA_PURIFIER_PREFETCH_GIT ${nix-prefetch-git}/bin/nix-prefetch-git \
      --set AGDA_PURIFIER_COMPILER_VERSION ${Agda.version} \
      --set AGDA_PURIFIER_SDK_VERSION ${sdkVersion} \
      --set AGDA_PURIFIER_NIXPKGS ${nixpkgsSrc} \
      --set AGDA_PURIFIER_SDK "$out"
    makeWrapper "$out/bin/agda-purifier" "$out/bin/agda" --add-flags '--native'
  '';
  meta = {
    description = "Native Agda with locked Nix-resolved libraries";
    homepage = "https://nix-purifiers.github.io/";
    license = lib.licenses.mit;
    platforms = [
      "x86_64-linux"
      "aarch64-linux"
    ];
    mainProgram = "agda-purifier";
  };
}
