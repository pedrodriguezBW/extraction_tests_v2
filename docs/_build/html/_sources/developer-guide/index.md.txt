# Guía de desarrollo

Esta guía está dirigida a las personas responsables de mantener, probar o ampliar la aplicación.

## Componentes principales

La aplicación está formada por:

- Un frontend desarrollado con React y TypeScript e integrado con Tauri.
- Un backend desarrollado con FastAPI.
- Un motor Python encargado de generar el PowerPoint editable.
- Los contratos de datos `test_metadata.json` y `evidence.json`.
- Una plantilla PowerPoint utilizada como base del informe.

En las siguientes fases se documentarán la instalación, la arquitectura, las pruebas, los contratos de datos y las guías de ampliación.
