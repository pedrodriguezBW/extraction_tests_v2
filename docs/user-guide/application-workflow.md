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

Desde esta sección también puedes ejecutar **Analyze SIMPATI**. Este paso es opcional y no bloquea por sí solo la generación del PowerPoint.

## 4. Generate report

El botón **Generate PowerPoint** se habilita cuando:

- Hay una carpeta seleccionada.
- El backend está conectado.
- La inspección es válida.
- `test_metadata.json` existe y es válido.
- No hay otra operación en curso.

Antes de generar, la aplicación indica cuántas gráficas SIMPATI guardadas se incluirán en `Test Results`.

Pulsa **Generate PowerPoint** y espera a que aparezca **Report generated**. La aplicación mostrará el nombre y la ruta del archivo creado.
