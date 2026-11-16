/** Renderiza el SVG de producción con Sharp para los ejemplos sintéticos. */
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const output = path.join(root, "examples/generated");
const require = createRequire(path.join(root, "frontend/package.json"));
const esbuild = require("esbuild");
const sharp = require(process.argv[2] || "sharp");
const bundle = await esbuild.build({entryPoints: [path.join(root, "frontend/src/services/chartExport.ts")], bundle: true, platform: "node", format: "cjs", write: false});
const modulePath = path.join(output, "chart-export.cjs");
await fs.writeFile(modulePath, bundle.outputFiles[0].text);
const {buildChartExportSvg} = require(modulePath);
for (const label of ["OK", "NOK"]) {
  const model = JSON.parse(await fs.readFile(path.join(output, `chart_${label}.json`), "utf8"));
  const svg = buildChartExportSvg(model);
  await fs.writeFile(path.join(output, `chart_${label}.svg`), svg);
  await sharp(Buffer.from(svg)).png().toFile(path.join(output, `chart_${label}.png`));
}
