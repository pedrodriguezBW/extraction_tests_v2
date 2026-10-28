# Estructura de la carpeta del ensayo

## Estructura

```text
TEST - 001/
├── 01_Inputs/
├── 02_Evidences/
│   └── <carpeta de evidencia>/
│       ├── evidence.json
│       └── <fotografías>
├── 03_Data/
│   ├── 01_SIMPATI/
│   ├── 02_Graphtec/
│   └── 03_CANoe/
└── 04_Report/
    ├── test_metadata.json
    ├── _RenderedAssets/
    └── _Working/
```

## Raíz seleccionada

La ruta entregada a la aplicación debe ser la carpeta individual del ensayo. No debe apuntar a `04_Report`, a una subcarpeta de evidencias ni a la raíz del repositorio.

## Elementos necesarios para generar

- `04_Report/` debe existir.
- `04_Report/test_metadata.json` debe existir y ser válido.
- La plantilla PowerPoint configurada debe estar accesible.

## Elementos opcionales inspeccionados

- `01_Inputs/`.
- `02_Evidences/`.
- `03_Data/`.
- Fuentes SIMPATI (`03_Data/01_SIMPATI`), Graphtec (`03_Data/02_Graphtec`) y CANoe (`03_Data/03_CANoe`).

CSV es un formato de archivo y no una fuente independiente.

Su ausencia puede producir advertencias sin bloquear necesariamente la generación.

## Carpetas creadas o utilizadas por la aplicación

### `_RenderedAssets`

Almacena gráficas SIMPATI guardadas para su inclusión posterior en `Test Results`.

### `_Working`

Se utiliza durante el montaje del PowerPoint. El informe terminado se guarda finalmente en `04_Report`.

## Regla de aislamiento

Los datos reales del ensayo y los archivos generados no forman parte del código fuente. Las carpetas del ensayo, los JSON generados, las imágenes, las adquisiciones y los PowerPoint deben permanecer fuera del control de versiones salvo ejemplos anonimizados creados expresamente para documentación o pruebas.
