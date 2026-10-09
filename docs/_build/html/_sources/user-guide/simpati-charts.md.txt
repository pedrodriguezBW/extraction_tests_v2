# Gráficas SIMPATI

El tratamiento de SIMPATI es opcional. El informe puede generarse aunque no exista un archivo de adquisición o no haya gráficas guardadas.

## Analizar la adquisición

Después de inspeccionar el proyecto:

1. Pulsa **Analyze SIMPATI**.
2. Si se encuentra una adquisición, revisa el nombre del archivo, la codificación, el número de registros y el intervalo temporal mostrado.
3. Configura la gráfica desde el componente disponible en la interfaz.
4. Guarda la gráfica cuando quieras incorporarla al informe.

Las adquisiciones SIMPATI se buscan en:

```text
03_Data/01_SIMPATI
```

## Gráficas guardadas

Las gráficas guardadas se almacenan en:

```text
04_Report/_RenderedAssets
```

La interfaz permite:

- Consultar las gráficas guardadas.
- Abrir una gráfica.
- Eliminar una gráfica.

Al eliminar una gráfica, esta deja de incluirse en `Test Results`.

## Inclusión en el informe

Antes de generar el PowerPoint, la aplicación actualiza la lista de gráficas guardadas. El mensaje situado en la sección de generación indica cuántas se incluirán.

Si no hay ninguna, el informe puede generarse igualmente.
