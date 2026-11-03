{ lib }:
{
  src,
  lockFile ? src + "/agda-purifier.lock.json",
}:
let
  raw = if builtins.pathExists lockFile then builtins.fromJSON (builtins.readFile lockFile) else { };
  data = if builtins.isAttrs raw then raw else { };
  entries = data.entries or [ ];
  nodes = data.nodes or [ ];
  relative =
    s:
    builtins.isString s
    && s != ""
    && !(lib.hasPrefix "/" s)
    && !(builtins.elem ".." (lib.splitString "/" s));
  safe =
    s:
    builtins.isString s
    && builtins.match "[A-Za-z0-9_+.-]+" s != null
    && !(builtins.elem s [
      "."
      ".."
    ]);
  commit = s: builtins.isString s && builtins.match "[a-f0-9]{40}" s != null;
  record =
    n:
    builtins.isAttrs n
    && safe (n.name or null)
    && relative (n.file or null)
    && builtins.isList (n.includes or null)
    && builtins.all relative n.includes
    && builtins.isList (n.dependencies or null)
    && builtins.all safe n.dependencies
    && builtins.isList (n.requests or null)
    && builtins.all builtins.isString n.requests;
  names = map (n: n.name) nodes;
  shape =
    (data.version or null) == 1
    && (data.purifier or null) == "agda"
    && builtins.isString (data.sdk or null)
    && builtins.isString (data.compiler or null)
    && builtins.isList entries
    && builtins.all (
      e:
      builtins.isAttrs e
      && relative (e.path or null)
      && builtins.isString (e.hash or null)
      && builtins.match "sha256-[A-Za-z0-9+/]{43}=" e.hash != null
      && builtins.isAttrs (e.git or null)
      && builtins.isString (e.git.url or null)
      && commit (e.git.rev or null)
      && (e.git.submodules or null) == false
      && (e.git.leaveDotGit or null) == false
      && (e.git.commitObject or null) == null
    ) entries
    && builtins.isList nodes
    && builtins.all (
      n:
      record n
      && builtins.isString (n.content or null)
      && builtins.isString (n.url or null)
      && commit (n.rev or null)
      && relative (n.entry or null)
      && builtins.any (e: e.path == n.entry && e.git.url == n.url && e.git.rev == n.rev) entries
    ) nodes
    && builtins.isList (data.project or null)
    && data.project != [ ]
    && builtins.all record data.project
    && builtins.isList (data.extraInputs or null)
    && builtins.all relative data.extraInputs
    && builtins.isAttrs (data.inputs or null);
  valid =
    shape
    && builtins.length names == builtins.length (lib.unique names)
    && builtins.all (n: builtins.all (d: builtins.elem d names) n.dependencies) (nodes ++ data.project)
    && !(lib.toposort (a: b: builtins.elem a.name b.dependencies) nodes ? cycle)
    &&
      builtins.attrNames data.inputs
      == builtins.sort builtins.lessThan (lib.unique (data.extraInputs ++ map (p: p.file) data.project))
    && builtins.all (
      name:
      relative name
      && builtins.pathExists (src + "/${name}")
      && builtins.isAttrs data.inputs.${name}
      && builtins.hashFile "sha256" (src + "/${name}") == (data.inputs.${name}.sha256 or null)
    ) (builtins.attrNames data.inputs);
in
{
  purifier = "agda";
  inherit data entries;
  outputs = {
    packages = [
      "default"
      "environment"
      "project"
    ];
    tests = [ "default" ];
    release = [ "default" ];
  };
  problems = lib.optional (!valid) "Invalid or stale Agda lock; update the lock";
}
