/** Comprobación del flujo real con backend y Vite locales; solo datos sintéticos. */
import fs from "node:fs/promises";
import path from "node:path";
import {createRequire} from "node:module";
import {fileURLToPath} from "node:url";

const require = createRequire(import.meta.url);
const {chromium} = require(process.argv[2] || "playwright");
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const output = path.join(root, "examples/generated");
const testRoot = path.join(output, "phase2");
const browser = await chromium.launch({headless: true, channel: "msedge"});
const page = await browser.newPage({viewport: {width: 1440, height: 1100}});
const errors = [];
page.on("pageerror", error => errors.push(error.message));
await page.addInitScript(({testRoot}) => {
  window.__TAURI_INTERNALS__ = {invoke: async command => {
    if (command === "plugin:dialog|open") return testRoot;
    throw new Error(`Unexpected native command: ${command}`);
  }};
}, {testRoot});
try {
  await page.goto("http://127.0.0.1:1420/");
  await page.getByRole("button", {name: "Browse", exact: true}).click();
  await page.getByRole("button", {name: "Inspect project", exact: true}).click();
  await page.getByRole("heading", {name: "Configuración del ensayo"}).waitFor();
  await page.getByLabel("Data source", {exact: true}).selectOption("simpati");
  await page.getByLabel("File", {exact: true}).selectOption(process.env.SIMPATI_UI_TEST_FILE || "03_Data/01_SIMPATI/synthetic_NOK.x02");
  await page.getByRole("button", {name: "Analyze SIMPATI", exact: true}).click();
  await page.getByText("Mostrar tolerancias", {exact: true}).waitFor();
  await page.getByLabel("Mostrar tolerancias", {exact: true}).check();
  await page.getByText("Tolerancias: NOK (1 tramo fuera)", {exact: true}).waitFor();
  const markersBelongToCurve = await page.locator(".simpati-chart svg").evaluate(svg => {
    const points = [...svg.querySelectorAll('polyline[stroke="#005a9c"]')]
      .flatMap(line => (line.getAttribute("points") || "").split(" "));
    const markers = [...svg.querySelectorAll('circle[fill="#d72631"]')];
    return markers.length > 0 && markers.every(marker =>
      points.includes(`${marker.getAttribute("cx")},${marker.getAttribute("cy")}`) && marker.querySelector("title"));
  });
  if (!markersBelongToCurve) throw new Error("Hay marcadores que no pertenecen a la curva medida");
  await page.locator(".simpati-chart").screenshot({path: path.join(output, "ui_tolerances.png")});
  await page.getByRole("button", {name: "Save current chart", exact: true}).click();
  await page.getByText(/Chart saved:/).waitFor();
  await page.getByLabel("location 1", {exact: true}).fill("UI autosave validation");
  const [generation] = await Promise.all([
    page.waitForResponse(response => response.url().endsWith("/projects/generate-report")),
    page.getByRole("button", {name: "Generate PowerPoint", exact: true}).click(),
  ]);
  if (!generation.ok()) throw new Error(`Generation failed: ${await generation.text()}`);
  const saved = JSON.parse(await fs.readFile(path.join(testRoot, "04_Report/_Working/report_inputs.json"), "utf8"));
  if (saved.measurement_points[0].location !== "UI autosave validation") throw new Error("Autosave did not persist edits");
  await page.locator(".test-configuration").screenshot({path: path.join(output, "ui_configuration.png")});
  if (errors.length) throw new Error(errors.join("\n"));
  console.log("UI: selección, precarga, NOK, guardado PNG/JSON y generación con guardado automático correctos.");
} finally {
  await browser.close();
}
