# Plantilla y secciones

## Papel de la plantilla

La aplicación parte de una plantilla PowerPoint configurada. La plantilla proporciona la estructura base sobre la que el motor inserta contenido y crea continuaciones.

La ruta de la plantilla se valida antes de generar el informe. Si la plantilla no está disponible, la inspección y la generación deben informar del problema.

## Secciones generadas

El motor está organizado por módulos dentro de:

```text
src/report_generator/sections/
```

Las capacidades documentadas del generador incluyen:

- `Test Description`.
- `Tested Parts`.
- `Test Assembly`.
- `Test Inputs` climáticos y DUT.
- `Test Results`.
- Diapositivas de continuación cuando el contenido supera la capacidad disponible.

## `Tested Parts`

La sección se genera dinámicamente a partir de la lista de muestras de `test_metadata.json`.

## `Test Description`

Utiliza los datos generales del ensayo y el procedimiento declarados en los metadatos.

## `Test Assembly`

Utiliza las fotografías del estado inicial descubierto mediante `02_Evidences/*/evidence.json`. La versión actual ya no depende de rutas heredadas dentro de `test_metadata.json`.

## `Test Inputs`

Incluye los parámetros climáticos, las tablas paginadas de perfil y las gráficas editables. Cuando existe contenido DUT, también genera su información y perfil.

## `Test Results`

Conserva la secuencia real definida por `sequence` en cada descriptor de evidencia. Puede incluir títulos, referencias, notas y fotografías, además de las gráficas SIMPATI previamente guardadas.

## `Conclusions`

La diapositiva `Conclusions` se conserva en el informe final para que el ingeniero complete o modifique manualmente su contenido.

## Precaución al modificar la plantilla

Las funciones de generación localizan y modifican diapositivas de la plantilla. Cualquier cambio de títulos, estructura, placeholders o diapositivas base debe comprobarse con una generación real y con las pruebas de limpieza.
