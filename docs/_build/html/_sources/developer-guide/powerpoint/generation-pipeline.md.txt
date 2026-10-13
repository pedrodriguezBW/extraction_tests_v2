# Flujo de generación

## Punto de entrada

La función pública del motor es `generate_climatic_report`. La generación utiliza el `test_metadata.json` existente y no abre el Excel de inputs.

## Recorrido general

```text
Carpeta del ensayo
        ↓
Resolución de rutas
        ↓
Validación de la plantilla
        ↓
Lectura de test_metadata.json
        ↓
Descubrimiento de evidence.json
        ↓
Preparación de 04_Report/_Working
        ↓
Copia de trabajo de la plantilla
        ↓
Generación de secciones
        ↓
Limpieza de diapositivas no utilizadas
        ↓
Renumeración
        ↓
PowerPoint final en 04_Report
```

## Responsabilidades de `generator.py`

El orquestador conecta las funciones de presentación con los módulos de secciones. La separación principal es:

- Preparación del archivo de trabajo.
- Lectura de datos.
- Ejecución secuencial de las funciones que completan las secciones.
- Limpieza final.
- Guardado del resultado.

## Directorios de salida

La presentación se monta en:

```text
04_Report/_Working
```

El archivo terminado se guarda en:

```text
04_Report
```

Las gráficas SIMPATI persistentes utilizadas por `Test Results` se almacenan en:

```text
04_Report/_RenderedAssets
```

## Principio funcional

El PowerPoint generado permanece editable. Las gráficas climática y DUT se crean como objetos nativos a partir de los puntos de perfil, en lugar de utilizar capturas exportadas desde Excel.
