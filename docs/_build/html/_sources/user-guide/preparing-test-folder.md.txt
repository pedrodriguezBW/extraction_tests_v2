# Preparación de la carpeta del ensayo

## Estructura esperada

La aplicación recibe la carpeta individual de un ensayo:

```text
TEST - 001/
├── 01_Inputs/
├── 02_Evidences/
│   └── <carpeta de evidencia>/
│       ├── evidence.json
│       └── <fotografías>
├── 03_Data/
│   ├── 01_SIMPATI/
│   ├── 02_CSV/
│   ├── 03_Datalogger/
│   └── 04_Graphtec/
└── 04_Report/
    ├── test_metadata.json
    ├── _RenderedAssets/
    └── _Working/
```

## Elementos obligatorios

Para habilitar la generación del PowerPoint deben existir:

- La carpeta `04_Report`.
- El archivo `04_Report/test_metadata.json`.
- Una plantilla PowerPoint válida y accesible para la aplicación.

Además, `test_metadata.json` debe superar la validación realizada durante la inspección.

## Elementos opcionales

La aplicación también comprueba:

- `01_Inputs`.
- `02_Evidences`.
- `03_Data`.
- Las fuentes SIMPATI, CSV, Datalogger y Graphtec.

La ausencia de estos recursos se muestra como advertencia cuando no bloquea la generación.

## Evidencias

Cada subcarpeta de `02_Evidences` puede contener un descriptor `evidence.json`. La aplicación utiliza esos descriptores para identificar, validar y ordenar las evidencias.

El orden cronológico depende del campo `sequence` del descriptor, no del nombre de la carpeta. Las fotografías referenciadas deben existir en la ubicación indicada por el descriptor.

## Recomendación antes de inspeccionar

No selecciones `04_Report` ni la carpeta general del programa. Selecciona directamente la carpeta individual del ensayo, por ejemplo `TEST - 001`.
