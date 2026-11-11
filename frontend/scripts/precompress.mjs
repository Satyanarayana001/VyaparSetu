// Writes .br files next to built assets; the API serves them to browsers that accept Brotli (smaller than gzip on slow networks).
import { brotliCompressSync, constants } from "node:zlib";
import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const walk = (d) => readdirSync(d).flatMap((f) => (statSync(join(d, f)).isDirectory() ? walk(join(d, f)) : [join(d, f)]));
let n = 0, before = 0, after = 0;
for (const f of walk("dist")) {
  if (!/\.(js|css|html|svg|webmanifest|json)$/.test(f)) continue;
  const buf = readFileSync(f);
  if (buf.length < 500) continue;
  const br = brotliCompressSync(buf, { params: { [constants.BROTLI_PARAM_QUALITY]: 11, [constants.BROTLI_PARAM_SIZE_HINT]: buf.length } });
  writeFileSync(f + ".br", br); n++; before += buf.length; after += br.length;
}
console.log(`precompress: ${n} files, ${(before / 1024).toFixed(1)} KB -> ${(after / 1024).toFixed(1)} KB brotli`);
