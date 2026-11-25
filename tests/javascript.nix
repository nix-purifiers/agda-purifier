{
  pkgs,
  src ? ./fixtures/javascript,
  moduleFile ? "Answer.agda",
  expected ? 42,
}:
let
  build = pkgs.agda-purifier.buildAgdaProject {
    inherit src;
    javascriptTargets.answer = moduleFile;
    javascriptWebjars.answer = {
      groupId = "org.example.agda";
      artifactId = "native-proof";
      version = "1.0";
    };
  };
  producer = build.javascript.answer;
  resources = build.projections.answer.web;
in
pkgs.runCommand "agda-native-javascript-consumers"
  {
    nativeBuildInputs = [
      pkgs.nodejs
      pkgs.chromium
      pkgs.python3
      pkgs.jdk
    ];
    FONTCONFIG_FILE = pkgs.makeFontsConf { fontDirectories = [ pkgs.dejavu_fonts ]; };
    passthru = { inherit producer resources build; };
  }
  ''
        export HOME="$TMPDIR/home"
        mkdir -p "$HOME" "$out"
        node ${./javascript-consumers.mjs} ${producer} ${resources.directory} ${toString expected}
        cp ${producer}/nix-support/agda-javascript/selection.json "$out/selection.json"
        python ${./javascript-http.py} ${resources.directory} "$out/selection.json" port > "$TMPDIR/http.log" 2>&1 &
        server=$!
        trap 'status=$?; if [ "$status" -ne 0 ]; then cat "$TMPDIR/http.log" "$TMPDIR/chromium.log" >&2; fi; kill "$server" || true; exit "$status"' EXIT
        for attempt in $(seq 1 100); do test -s port && break; sleep 0.05; done
        test -s port
        chromium --headless --no-sandbox --disable-gpu --disable-dev-shm-usage \
          --user-data-dir="$TMPDIR/profile" --dump-dom "http://127.0.0.1:$(cat port)/" \
          > "$out/dom.html" 2> "$TMPDIR/chromium.log"
        grep 'data-answer="${toString expected}"' "$out/dom.html"
        cp ${./JavascriptResource.java} JavascriptResource.java
    javac JavascriptResource.java
    java -cp .:${build.projections.answer.java-resources.classPath} JavascriptResource ${producer}/javascript/*.mjs
    python ${./javascript-webjar.py} ${producer} ${build.projections.answer.maven}
  ''
