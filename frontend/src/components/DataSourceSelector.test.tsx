import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { DataSourceSelector } from "./DataSourceSelector";
import {
  dataSourceOptions,
  fileSelectorHint,
  isFileSelectorDisabled,
  pendingSourceMessage,
  sourceFiles,
} from "../services/dataSourceSelection";
import { buildInspection } from "../services/testFixtures";
import type { DataSourceKey } from "../types/project";

function render(
  sourceKey: DataSourceKey | null,
  fileRelativePath: string | null = null,
): string {
  const inspection = buildInspection();
  return renderToStaticMarkup(
    <DataSourceSelector
      options={dataSourceOptions(inspection)}
      selectedSourceKey={sourceKey}
      files={sourceFiles(inspection, sourceKey)}
      selectedFileRelativePath={fileRelativePath}
      fileSelectorDisabled={isFileSelectorDisabled(inspection, sourceKey)}
      fileHint={fileSelectorHint(inspection, sourceKey)}
      pendingMessage={pendingSourceMessage(inspection, sourceKey)}
      disabled={false}
      onSourceChange={() => undefined}
      onFileChange={() => undefined}
    />,
  );
}

function fileSelect(markup: string): string {
  const start = markup.indexOf('<select id="data-source-file"');
  return markup.slice(start, markup.indexOf("</select>", start));
}

describe("DataSourceSelector", () => {
  it("shows the three data sources", () => {
    const markup = render(null);

    expect(markup).toContain('<option value="simpati">SIMPATI (1 file)</option>');
    expect(markup).toContain(
      '<option value="graphtec">Graphtec (2 files)</option>',
    );
    expect(markup).toContain('<option value="canoe">CANoe (0 files)</option>');
  });

  it("disables the file selector until a source is selected", () => {
    const select = fileSelect(render(null));

    expect(select).toContain("disabled");
    expect(select).toContain("Select a source first");
  });

  it("lists the files of the selected source", () => {
    const simpati = fileSelect(render("simpati"));
    const graphtec = fileSelect(render("graphtec"));

    expect(simpati).toContain("acquisition.x03");
    expect(simpati).not.toContain("run_01.csv");
    expect(graphtec).toContain("run_01.csv");
    expect(graphtec).toContain("run_02.csv");
    expect(graphtec).not.toContain("acquisition.x03");
    expect(graphtec).not.toContain("disabled");
  });

  it("disables the file selector when the source has no files", () => {
    const markup = render("canoe");

    expect(fileSelect(markup)).toContain("disabled");
    expect(markup).toContain("No files were found in the CANoe folder.");
  });

  it("shows a neutral message for sources that cannot be read yet", () => {
    expect(render("graphtec")).toContain(
      "Reading Graphtec files will be added in a later increment.",
    );
    expect(render("canoe")).toContain(
      "Reading CANoe files will be added in a later increment.",
    );
    expect(render("simpati")).not.toContain("later increment");
  });
});
