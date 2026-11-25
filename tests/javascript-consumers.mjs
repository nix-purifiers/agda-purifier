import fs from "node:fs";
import path from "node:path";
import {pathToFileURL} from "node:url";
import assert from "node:assert/strict";
const [producer, resources, expectedArg] = process.argv.slice(2);
const expected = BigInt(expectedArg);
const meta = JSON.parse(fs.readFileSync(path.join(producer,"nix-support/agda-javascript/selection.json")));
const graph = JSON.parse(fs.readFileSync(path.join(producer,"nix-support/agda-javascript/modules.json")));
for (const file of Object.keys(graph.files))
  assert.deepEqual(fs.readFileSync(path.join(producer,"javascript",file)),fs.readFileSync(path.join(resources,file)));
const {default: api} = await import(pathToFileURL(path.join(resources,meta.nativeOutput)).href);
for (let i=0n;i<100n;i++) assert.equal(api.answer(i), i+expected-1n);
const large = 2n ** 100n;
assert.equal(api.answer(large),large+expected-1n);
console.log("Original Agda ESM Nat API, resource bytes and 100 native calls PASS");
