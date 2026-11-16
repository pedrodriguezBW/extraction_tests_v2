import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { TestConfiguration } from "./TestConfiguration";
import { emptyInputs } from "../types/reportInputs";

describe("panel de configuración", () => {
  it("muestra el catálogo recibido y avisa de los canales guardados ausentes", () => {
    const markup = renderToStaticMarkup(<TestConfiguration inputs={{...emptyInputs(), measurement_points: [
      {channel: "A", location: "Puerta", sensor_type: "T", function: "control"},
    ]}} catalog={{Nb: {name: "Change of temperature", standard: "IEC"}}} channels={["B"]} detected disabled={false}
      warnings={[]} onChange={() => {}} onSave={() => {}}/>);
    expect(markup).toContain("no encontrado en los logs");
    expect(markup).toContain("Puerta");
    expect(markup).toContain("Guardar");
    expect(markup).toContain("Nb – Change of temperature");
  });
});
