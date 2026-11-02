# Uso de la aplicación

La interfaz organiza el trabajo en cuatro etapas principales. Los nombres de botones y secciones se reproducen tal como aparecen en la aplicación.

## 1. Select project

1. Pulsa **Browse**.
2. Selecciona la carpeta individual del ensayo.
3. Comprueba la ruta mostrada en **Test folder**.

La selección de la carpeta no modifica su contenido.

Si has seleccionado una carpeta incorrecta, pulsa **Clear** y selecciona otra.

## 2. Inspect project

Pulsa **Inspect project**.

La aplicación comprueba:

- `01_Inputs`.
- `02_Evidences`.
- `03_Data`.
- `04_Report`.
- `test_metadata.json`.
- La plantilla PowerPoint configurada.

El resultado general aparece como:

- **Valid project:** la inspección permite continuar.
- **Invalid project:** existen errores que deben corregirse.

### Errores y advertencias

- Los **Errors** bloquean la generación del informe.
- Los **Warnings** informan de recursos opcionales ausentes o incompletos y deben revisarse antes de continuar.

Corrige los errores en la carpeta del ensayo y vuelve a ejecutar **Inspect project**.

## 3. Review project resources

Esta sección resume los metadatos, las evidencias y las fuentes de adquisición detectadas.

Para cada evidencia se muestra:

- Su posición en la secuencia.
- Su identificación o título.
- El número de fotografías encontradas respecto a las referenciadas.

Revisa cualquier evidencia marcada con advertencia, especialmente cuando falten fotografías.

Debajo de la lista, **Evidence photos** permite elegir qué fotografías se insertan en **2. Test Assembly** (evidencias `initial`, máximo 4) y en **4. Test Results** (resto de evidencias, sin límite). Consulta [Fotografías de evidencias](evidence-photos.md).

### Data source y File

Después de la inspección aparecen dos selectores:

- **Data source:** SIMPATI, Graphtec o CANoe.
- **File:** archivos encontrados directamente en la carpeta de la fuente elegida.

El selector **File** permanece deshabilitado si no hay fuente seleccionada, si la carpeta de la fuente no existe o si no contiene archivos. Cambiar de fuente o de archivo no analiza nada automáticamente y descarta el análisis SIMPATI mostrado anteriormente.

Para CANoe se muestra un aviso indicando que su lectura se añadirá en un incremento posterior. Para Graphtec se muestra **Analyze Graphtec**; consulta [Gráficas Graphtec](graphtec-charts.md).

### Analyze SIMPATI

**Analyze SIMPATI** se habilita cuando la fuente seleccionada es SIMPATI y el archivo seleccionado es una adquisición `.x01`-`.x99` detectada en la inspección. Se analizan todas las adquisiciones de la carpeta y la seleccionada se abre en el editor de gráficas; consulta [Gráficas SIMPATI](simpati-charts.md). Este paso es opcional y no bloquea por sí solo la generación del PowerPoint.

## 4. Generate report

El botón **Generate PowerPoint** se habilita cuando:

- Hay una carpeta seleccionada.
- El backend está conectado.
- La inspección es válida.
- `test_metadata.json` existe y es válido.
- No hay otra operación en curso.

Antes de generar, revisa la sección **Report images** y marca las imágenes de `04_Report/_RenderedAssets` que deben aparecer en `Test Results` (todas están marcadas por defecto). El mensaje de la sección de generación indica cuántas se incluirán; el informe puede generarse sin ninguna. Consulta [Imágenes del informe](report-images.md).

Pulsa **Generate PowerPoint** y espera a que aparezca **Report generated**. La aplicación mostrará el nombre y la ruta del archivo creado.
