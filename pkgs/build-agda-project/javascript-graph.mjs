import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import crypto from "node:crypto";

const [rootArg, selectionPath] = process.argv.slice(2);
const root = fs.realpathSync(rootArg);
const selection = JSON.parse(fs.readFileSync(selectionPath, "utf8"));
const files = fs.readdirSync(root).sort();
const records = {};
for (const name of files) {
  const filename = path.join(root, name);
  if (!name.endsWith(".mjs") || !fs.lstatSync(filename).isFile())
    throw new Error("Expected original native ES module files: " + name);
  const bytes = fs.readFileSync(filename);
  const module = new vm.SourceTextModule(bytes.toString("utf8"), {identifier: filename});
  const imports = module.dependencySpecifiers;
  for (const specifier of imports) {
    if (!specifier.startsWith("./")) throw new Error("Unsupported external JavaScript import: " + specifier);
    const resolved = fs.realpathSync(path.resolve(root, specifier));
    if (!resolved.startsWith(root + path.sep) || !files.includes(path.relative(root, resolved)))
      throw new Error("JavaScript import escapes native output: " + specifier);
  }
  records[name] = {sha256: crypto.createHash("sha256").update(bytes).digest("hex"), imports};
}
if (!(selection.nativeOutput in records)) throw new Error("Native module entry is missing");
if (!("agda-rts.mjs" in records)) throw new Error("Native runtime is missing");
console.log(JSON.stringify({selection, files: records}, null, 2));
