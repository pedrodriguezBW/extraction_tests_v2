# Gráficas SIMPATI

El tratamiento de SIMPATI es opcional. El informe puede generarse aunque no exista un archivo de adquisición o no haya gráficas guardadas.

## Analizar la adquisición

Después de inspeccionar el proyecto:

1. En **Data source**, selecciona **SIMPATI**.
2. En **File**, selecciona la adquisición SIMPATI detectada.
3. Pulsa **Analyze SIMPATI**.
4. Si se encuentra una adquisición, revisa el nombre del archivo, la codificación, el número de registros y el intervalo temporal mostrado.
5. Configura la gráfica desde el componente disponible en la interfaz.
6. Guarda la gráfica cuando quieras incorporarla al informe.

Las adquisiciones SIMPATI se buscan en:

```text
03_Data/01_SIMPATI
```

## Gráficas guardadas

Las gráficas guardadas se almacenan en:

```text
04_Report/_RenderedAssets
```

Una vez guardada, la gráfica aparece en la sección **Report images**, junto con las gráficas Graphtec y cualquier otra imagen compatible de esa carpeta, con la procedencia `SIMPATI`. Allí puede abrirse, eliminarse y marcarse o desmarcarse para el informe. Consulta [Imágenes del informe](report-images.md).

## Inclusión en el informe

Las gráficas recién guardadas quedan seleccionadas por defecto. Solo las imágenes marcadas en **Report images** se insertan en `Test Results`; el mensaje de la sección de generación indica cuántas se incluirán.

Si no hay ninguna, el informe puede generarse igualmente.
