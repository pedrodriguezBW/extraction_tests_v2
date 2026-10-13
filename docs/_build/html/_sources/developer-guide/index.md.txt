# Guía de desarrollo

Esta guía explica cómo preparar el entorno, comprender la arquitectura, ejecutar la aplicación, modificar sus capas y validar los cambios.

Está dirigida a las personas responsables de mantener o ampliar el proyecto.

```{toctree}
:maxdepth: 2

development-setup
architecture
frontend
backend
data-flow
testing
data-structures/index
powerpoint/index
extending/index
reference/index
```

## Componentes principales

La aplicación está formada por:

- Un frontend desarrollado con React y TypeScript.
- Una capa de escritorio basada en Tauri.
- Un backend local desarrollado con FastAPI.
- Un motor Python encargado de inspeccionar el ensayo y generar el PowerPoint.
- Las estructuras `test_metadata.json`, `evidence.json` y la organización de carpetas del ensayo.
- Una plantilla PowerPoint utilizada como base del informe editable.

## Principio de funcionamiento

La aplicación no genera `test_metadata.json`. Ese archivo se crea externamente y la aplicación lo utiliza como entrada para inspeccionar el ensayo y generar el informe.
