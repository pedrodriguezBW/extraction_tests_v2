# Imágenes del informe

La sección **Report images** aparece dentro de **3. Review project resources** después de inspeccionar el proyecto. Muestra todas las imágenes compatibles de:

```text
04_Report/_RenderedAssets
```

con independencia de su origen:

- Gráficas SIMPATI guardadas desde la aplicación (procedencia `SIMPATI`).
- Gráficas Graphtec guardadas desde la aplicación (procedencia `Graphtec`).
- Imágenes PNG, JPG o JPEG copiadas a mano en la carpeta (procedencia `Manual`).

La procedencia es solo informativa: cualquier imagen compatible puede incluirse en el informe.

## Formatos admitidos

Se admiten archivos `.png`, `.jpg` y `.jpeg`, sin distinguir mayúsculas de minúsculas, situados directamente en `_RenderedAssets`. Los demás archivos (PDF, SVG, TXT, CSV, JSON, GIF, subcarpetas...) no bloquean el listado ni la generación: se enumeran como **Files not available for the report** y no pueden seleccionarse.

## Selección

Cada imagen muestra una casilla de selección, una miniatura, su nombre, su procedencia, su tamaño y su estado (`Included in the report` o `Not included`).

- Las imágenes detectadas están **seleccionadas por defecto**.
- Puedes marcar y desmarcar cada imagen individualmente, o usar **Select all** y **Clear selection**.
- El contador indica, por ejemplo, `3 of 5 images selected for the report.`
- Una gráfica recién guardada desde SIMPATI o Graphtec se añade seleccionada.
- Al refrescar el inventario se conserva tu selección para las imágenes que siguen existiendo.

Si no hay imágenes se muestra `No rendered images were found. The report can still be generated.`; si las hay pero ninguna está marcada, `No rendered images are selected. The report will be generated without them.`

## Abrir y eliminar

**Open image** muestra la imagen a tamaño completo. **Delete** elimina el archivo (y su JSON de metadatos, si existe) de `_RenderedAssets`; la imagen desaparece del inventario y de la selección.

## Inclusión en el PowerPoint

Al pulsar **Generate PowerPoint**, la aplicación envía la lista ordenada de imágenes seleccionadas. En `4. Test Results` se insertan exactamente esas imágenes, en el orden mostrado, de dos en dos por diapositiva, en dos columnas, con las continuaciones necesarias y sin deformarlas. Cada imagen ocupa el mayor tamaño posible entre el subtítulo y el pie; una gráfica sola aprovecha todo el ancho útil. Una imagen desmarcada nunca aparece en el informe, y el informe puede generarse sin ninguna imagen.
