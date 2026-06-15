#!/usr/bin/env node
import { generateLoungeGeometry } from "../../modules/loungeGenerator/generator.ts";

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (chunk) => {
      data += chunk;
    });
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
}

try {
  const raw = await readStdin();
  const payload = raw ? JSON.parse(raw) : {};
  const params = payload.params || payload;
  const result = generateLoungeGeometry(params);
  process.stdout.write(JSON.stringify({ ok: true, result }));
} catch (error) {
  process.stdout.write(JSON.stringify({
    ok: false,
    errors: [error && error.stack ? error.stack : String(error)],
  }));
  process.exitCode = 1;
}
