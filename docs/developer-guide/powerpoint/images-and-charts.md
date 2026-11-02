# Imágenes y gráficas

## Fotografías de evidencias

Las fotografías se resuelven desde la carpeta que contiene `evidence.json` utilizando el campo `savedName` de cada elemento de `photos`.

La inspección informa de las fotografías referenciadas que no existen. Cada fotografía se identifica por su ruta relativa al ensayo (`02_Evidences/<carpeta>/<savedName>`) y pertenece a una única sección según el tipo de su evidencia (`src/report_generator/evidence_photos.py`):

- `assembly`: evidencias `initial` → `2. Test Assembly`, como máximo `ASSEMBLY_MAX_PHOTOS` (4).
- `results`: resto de evidencias → `4. Test Results`, sin límite.

`select_evidence_photos(discovery, section, selection)` valida la selección (ruta relativa sin `.`/`..` dentro de `02_Evidences`, declarada por una evidencia válida, existente, formato admitido, sin duplicados, de la sección correcta y, en Assembly, sin superar 4) y la devuelve siempre en el orden automático. `None` mantiene el comportamiento sin selección: las 4 primeras de Assembly y todas las de Results.

Ambas secciones colocan `EVIDENCE_PHOTOS_PER_SLIDE` (2) fotografías por diapositiva. En `Test Assembly` las fotografías 3 y 4 van en una continuación `2. Test Assembly (cont.)` insertada justo después de la diapositiva principal (antes de las continuaciones de equipamiento). En `Test Results` cada evidencia ocupa al menos una diapositiva, aunque no tenga fotografías seleccionadas; sus continuaciones repiten el título con `(cont.)` y el tipo/referencia, sin las notas.

## Inserción de imágenes

Las utilidades comunes de imagen se encuentran bajo:

```text
src/report_generator/powerpoint/
```

El módulo de secciones de montaje utiliza una función para añadir imágenes contenidas en el área disponible, evitando que la lógica de encaje quede duplicada en cada sección.

## Gráficas climáticas y DUT

`src/report_generator/powerpoint/charts.py` construye gráficas nativas de PowerPoint a partir de los puntos de perfil.

Las series solo utilizan valores numéricos válidos. Para el perfil climático, los campos de referencia incluyen `time_min` y `temperature_c`; el módulo también contempla otras series disponibles, como humedad o actuación cuando contienen datos utilizables.

## Imágenes de resultados (`_RenderedAssets`)

Las imágenes de resultados son archivos PNG, JPG o JPEG almacenados en:

```text
04_Report/_RenderedAssets
```

Pueden proceder de SIMPATI, de Graphtec, de una copia manual o de fuentes futuras como CANoe. El motor PowerPoint no las descubre ni las filtra por nombre, prefijo o procedencia: `populate_test_results` recibe en `result_image_paths` la lista ya validada de imágenes seleccionadas por el usuario y las inserta en `4. Test Results` en ese mismo orden, en grupos de dos por diapositiva (dos columnas, nunca apiladas), creando continuaciones cuando hacen falta. Una lista vacía genera la sección solo con las evidencias.

### Formato de exportación

Todas las gráficas que la aplicación guarda en `_RenderedAssets` comparten un formato común, definido en `src/report_generator/chart_export.py` (Graphtec y la herramienta de consola SIMPATI) y replicado en `frontend/src/services/chartExport.ts` (botón **Save current chart** del visor SIMPATI):

- 1800 × 1125 px, proporción 1,6:1.
- Diseño al ancho físico de una columna de `Test Results` (`(CONTENT_WIDTH_CM − RESULT_HORIZONTAL_GAP_CM) / 2` ≈ 14,4 cm, unos 317 ppp), de modo que los tamaños en puntos son los que se ven en la diapositiva con dos gráficas.
- Título 13 pt (negrita, en varias líneas si es largo), etiquetas de ejes 12 pt, valores de los ejes 11 pt, leyenda 11 pt, notas 10 pt.
- Líneas de 1,8 pt (series secundarias y consignas 1,5 pt), rejilla de 0,6 pt.
- Márgenes mínimos (diseño `constrained` en Matplotlib; cálculo explícito en el SVG): título, leyenda y notas se reservan su espacio y nunca se recortan.
- Eje X con un máximo de 6 marcas equiespaciadas; en SIMPATI las fechas se escriben en dos líneas (fecha y hora) y se reduce el número de marcas hasta que no se solapan.
- Sin desplazamiento (`offset`) en el eje Y: un rango estrecho muestra sus valores reales, con los decimales necesarios.

El formato no se aplica a las fotografías de evidencias ni a las gráficas nativas de `Test Inputs`.

### Colocación en `Test Results`

`result_chart_area` calcula el espacio útil a partir de la plantilla real:

- laterales: el marcador de contenido del diseño de la diapositiva (2,12 cm y 29,63 cm en la plantilla corporativa), limitado a los márgenes de la diapositiva;
- arriba: debajo del subtítulo con la procedencia (`RESULT_SUBTITLE_TOP_CM + RESULT_SUBTITLE_HEIGHT_CM + RESULT_CHARTS_TOP_GAP_CM`);
- abajo: el elemento más alto del pie (número, texto, línea o logotipo de la diapositiva, su diseño o su patrón) menos `RESULT_CHARTS_FOOTER_GAP_CM`.

`result_chart_boxes` reparte ese área: una gráfica ocupa todo el ancho útil; dos gráficas, dos columnas iguales separadas por `RESULT_HORIZONTAL_GAP_CM`. `add_centered_image` inserta cada imagen con el mayor tamaño que cabe en su caja, sin deformarla y centrada en ambos ejes. Con la plantilla corporativa, dos gráficas 1,6:1 miden 14,42 × 9,01 cm cada una y una sola 17,41 × 10,88 cm.

`generate_climatic_report` recibe `selected_rendered_assets` (rutas relativas al ensayo). Una lista, aunque esté vacía, es una selección explícita y se valida con `select_rendered_assets`; `None` (parámetro omitido, como en los scripts de consola) utiliza todas las imágenes válidas del inventario en su orden estable.

## Editabilidad

- Las gráficas climáticas y DUT son objetos editables en PowerPoint.
- Las imágenes de resultados se incorporan como recursos de imagen, sin deformarlas.
- Las fotografías se incorporan como imágenes.

## Comprobaciones tras un cambio

Cuando se modifica el tratamiento de imágenes o gráficas, debe revisarse:

- Que la imagen no se deforme.
- Que el encaje respete el área disponible.
- Que las fotografías aparezcan en la evidencia correcta.
- Que cada sección contenga exactamente las fotografías seleccionadas, dos por diapositiva, y que Test Assembly no supere 4.
- Que las series y ejes de las gráficas nativas sean editables.
- Que `Test Results` contenga exactamente las imágenes seleccionadas, en el orden recibido, y ninguna otra.
- Que las gráficas no invadan el encabezado, el subtítulo ni el pie, y que haya como máximo dos por diapositiva.
