# Gráficas SIMPATI

El tratamiento de SIMPATI es opcional. El informe puede generarse aunque no exista ninguna adquisición o no haya gráficas guardadas.

## Adquisiciones admitidas

Cada exportación original de SIMPATI con extensión `.x01`, `.x02`, … `.x99` es una adquisición. Se buscan directamente en:

```text
03_Data/01_SIMPATI
```

- Se detectan todas las adquisiciones presentes, aunque falten índices intermedios (por ejemplo `.x01`, `.x03` y `.x07`).
- Se ordenan por el número de la extensión (`x02` antes que `x10`).
- Se ignoran `.x00`, `.xABC`, `.txt`, `.csv`, las subcarpetas y los archivos ocultos o temporales.
- La extensión solo identifica la adquisición. La codificación, la cabecera, las unidades y los canales se obtienen del contenido del archivo, por lo que cámaras distintas (por ejemplo una climática y una de choque térmico) se analizan con el mismo flujo.

## Analizar las adquisiciones

Después de inspeccionar el proyecto:

1. En **Data source**, selecciona **SIMPATI**.
2. En **File**, selecciona una adquisición `.xNN`.
3. Pulsa **Analyze SIMPATI**.

La aplicación analiza todas las adquisiciones de la carpeta de forma independiente y muestra una tabla con:

- índice `xNN` y nombre del archivo;
- codificación detectada;
- número de registros e intervalo temporal;
- número de canales detectados y canales térmicos representables;
- estado: **Ready**, **No representable channels**, **Incompatible** o **Read error**, con el mensaje de error cuando existe.

El resumen indica cuántas adquisiciones se han encontrado, procesado, cuántas no tienen canales representables y cuántas son incompatibles. Una adquisición incompatible no impide trabajar con las demás.

La adquisición seleccionada se abre en el editor de gráficas. Para trabajar con otra, pulsa **Open** en su fila de la tabla (o elígela en **File** y vuelve a pulsar **Analyze SIMPATI**).

## Canales representables

El editor muestra por defecto los canales térmicos que la adquisición contiene realmente, por ejemplo:

- cámara climática: temperatura y consigna de cámara, aire de impulsión y aire de retorno;
- cámara de choque térmico: temperatura y consigna de cesta, cámara caliente y cámara fría, y temperatura de probeta.

El resto de canales (posiciones, ciclos, límites, contadores, salidas digitales…) se conservan y pueden añadirse desde los canales avanzados.

## Ajustar la vista

La vista se ajusta arrastrando directamente sobre el área de la gráfica; durante el arrastre se dibuja la zona seleccionada:

- **Selección horizontal**: reduce el intervalo temporal (eje X). El eje Y no se reajusta: conserva el rango que tenía.
- **Selección vertical**: ajusta el rango de valores (eje Y) sin cambiar el intervalo temporal.
- **Selección rectangular** (en diagonal): ajusta ambos ejes a la vez.

El eje Y no tiene ajuste automático al intervalo visible. Al abrir la gráfica (o al restablecer la vista) muestra el rango completo de los canales activados y solo cambia cuando lo amplías con una selección vertical o rectangular, igual que el eje X.

Cada selección se aplica sobre la vista actual, de modo que pueden encadenarse varias ampliaciones. Un clic sin arrastrar no cambia la vista. Para volver a la vista completa, haz doble clic sobre la gráfica (restablece solo los ejes) o pulsa **Reset view** (restablece los ejes y los canales térmicos por defecto).

**Save current chart** guarda exactamente lo que se ve en pantalla: intervalo temporal, rango de valores, canales activados, título y leyenda. Los límites no se recalculan al guardar. La imagen se genera con el formato del informe (1800 × 1125 px, proporción 1,6:1), con textos y líneas más grandes que en el visor para que se lean bien en PowerPoint; las fechas del eje X se escriben en dos líneas (fecha y hora).

## Gráficas guardadas

Las gráficas guardadas se almacenan en:

```text
04_Report/_RenderedAssets
```

Cada gráfica se nombra según su adquisición de origen, `chart_simpati_xNN_MM.png` (por ejemplo `chart_simpati_x01_01.png` o `chart_simpati_x04_02.png`), de modo que las gráficas de adquisiciones distintas nunca se sobrescriben. El título de la imagen indica el índice y el archivo de origen, y el JSON que la acompaña guarda el archivo de origen.

Una vez guardada, la gráfica aparece en la sección **Report images**, junto con las gráficas Graphtec y cualquier otra imagen compatible de esa carpeta, con la procedencia `SIMPATI`. Allí puede abrirse, eliminarse y marcarse o desmarcarse para el informe. Consulta [Imágenes del informe](report-images.md).

## Inclusión en el informe

Las gráficas recién guardadas quedan seleccionadas por defecto. Solo las imágenes marcadas en **Report images** se insertan en `Test Results`, en el orden de la lista (las de `x01` antes que las de `x04`); el subtítulo de la diapositiva indica la adquisición de origen. El mensaje de la sección de generación indica cuántas se incluirán.

Si no hay ninguna, el informe puede generarse igualmente.
