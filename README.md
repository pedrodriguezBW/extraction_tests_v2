# Generador de informes PowerPoint

La aplicación genera un informe PowerPoint editable a partir del
`test_metadata.json` de un ensayo. Ese JSON lo produce un agente externo:
la aplicación ya no abre el Excel de inputs ni extrae datos de él.

Flujo:

```
Seleccionar ensayo
→ inspeccionar estructura y test_metadata.json
→ revisar los recursos detectados
→ generar PowerPoint
```

## Estructura del ensayo

La aplicación recibe la carpeta individual de un ensayo:

```
TEST - 001
├── 01_Inputs
├── 02_Evidences
│   └── <carpeta de evidencia>/evidence.json
├── 03_Data
│   ├── 01_SIMPATI
│   ├── 02_CSV
│   ├── 03_Datalogger
│   └── 04_Graphtec
└── 04_Report
    ├── test_metadata.json
    ├── _RenderedAssets
    └── _Working
```

- `04_Report` y un `test_metadata.json` válido son obligatorios para
  generar el informe.
- `01_Inputs`, `02_Evidences` y `03_Data` se comprueban y se informan,
  pero su ausencia solo produce advertencias.
- Las fuentes SIMPATI, CSV, Datalogger y Graphtec son opcionales.
- El PowerPoint final se guarda directamente en `04_Report`. Se monta en
  `04_Report/_Working` y se mueve a `04_Report` cuando está completo.
- Las gráficas SIMPATI guardadas se almacenan en
  `04_Report/_RenderedAssets` y se incluyen en *Test Results*.

Todas las rutas se definen en `src/report_generator/paths.py`.

## Evidencias

Cada subcarpeta de `02_Evidences` puede contener un `evidence.json`
(`schemaVersion`, `id`, `type`, `title`, `reference`, `notes`, `sequence`,
`folder`, `photos`). Las evidencias se descubren dinámicamente, se validan
y se ordenan por `sequence`; el nombre de la carpeta no determina el orden
ni el tipo. La ruta de cada fotografía es la carpeta que contiene el
descriptor más `savedName`. Se informa de los descriptores inválidos y de
las fotografías referenciadas que no existen.

En esta versión las evidencias se detectan y se muestran, pero todavía no
se generan sus diapositivas.

## Uso por consola

- `python generate_report.py`: genera el PowerPoint desde el
  `test_metadata.json` existente.
- `python run_pipeline.py`: mismo flujo, mostrando también el JSON usado.
- `python -m src.report_generator.assets.simpati_extractor`: ventana
  interactiva para guardar gráficas SIMPATI en `04_Report/_RenderedAssets`.

## Organización del código

- `src/report_generator/paths.py`: contrato de carpetas del ensayo.
- `src/report_generator/metadata.py`: lectura y validación de
  `test_metadata.json`.
- `src/report_generator/evidences.py`: descubrimiento y validación de
  evidencias.
- `src/report_generator/data_sources.py`: fuentes de `03_Data`.
- `src/report_generator/media.py`: utilidades neutrales de imágenes.
- `src/report_generator/powerpoint/` y `sections/`: motor de generación.
- `src/report_generator/powerpoint/charts.py`: gráficas climática y DUT
  nativas y editables, creadas con los puntos de perfil del JSON.
- `backend/`: API FastAPI y servicios que conectan con el motor.
- `frontend/`: interfaz React + TypeScript con integración de escritorio
  Tauri.

## API

- `POST /projects/inspect`: estructura, `test_metadata.json`, evidencias,
  fuentes de datos, plantilla, errores y advertencias.
- `POST /projects/generate-report`: genera el PowerPoint en `04_Report`.
- `POST /projects/simpati/inspect`, `POST /projects/simpati/save-chart`,
  `POST /projects/simpati/charts`, `GET /projects/simpati/chart` y
  `POST /projects/simpati/delete-chart`: flujo de gráficas SIMPATI.

## Pruebas

- Python: `python -m unittest discover -s tests`
- Frontend: `cd frontend` y `npm test`

## Interfaz de escritorio

El frontend React + TypeScript y la configuración de Tauri están en
`frontend/`.

1. Inicia el backend:

   `python -m uvicorn backend.app.main:app --reload`

2. En otra consola, instala las dependencias del frontend:

   `cd frontend`

   `npm install`

3. Inicia la aplicación de escritorio:

   `npm run tauri dev`

La URL del backend se configura mediante `VITE_API_BASE_URL`. Si no se
especifica, se utiliza `http://127.0.0.1:8000`.
