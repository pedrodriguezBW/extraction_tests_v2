# Backend FastAPI

## Punto de entrada

El backend se inicia desde:

```text
backend/app/main.py
```

Este módulo crea la aplicación FastAPI, configura CORS, registra el router de proyectos y expone `GET /health`.

## Router de proyectos

Las operaciones del proyecto se agrupan bajo el prefijo:

```text
/projects
```

Los endpoints actuales son:

```text
POST /projects/inspect
POST /projects/generate-report
POST /projects/simpati/inspect
POST /projects/simpati/save-chart
POST /projects/simpati/charts
GET  /projects/simpati/chart
POST /projects/simpati/delete-chart
```

## Organización interna

```text
backend/app/
├── main.py
├── api/
├── models/
└── services/
```

### `api/`

Define los endpoints y traduce las peticiones HTTP a llamadas de servicio.

### `models/`

Define las estructuras de petición y respuesta utilizadas por FastAPI.

### `services/`

Implementa la lógica de aplicación que conecta la API con el motor de informes.

## Flujo de una operación

```text
Petición HTTP
    ↓
Modelo de entrada
    ↓
Endpoint
    ↓
Servicio
    ↓
Motor report_generator
    ↓
Modelo de respuesta o error HTTP
```

## Inspección

`POST /projects/inspect` recibe la carpeta del ensayo y devuelve el estado de la estructura, metadata, evidencias, fuentes de datos y plantilla.

`data` contiene `directory`, una entrada por fuente (`simpati`, `graphtec`, `canoe`) y `simpati_file`. Cada fuente incluye `files`, con `name`, `relative_path` (relativa a la raíz del ensayo, con `/`), `extension` (en minúsculas) y `size` (bytes). Solo se listan archivos regulares situados directamente en la carpeta de la fuente, ordenados sin distinguir mayúsculas; las subcarpetas, los archivos ocultos y los archivos de bloqueo de Office se excluyen. La inspección no lee el contenido de los archivos.

## Generación

`POST /projects/generate-report` genera el PowerPoint desde el `test_metadata.json` existente. El endpoint contempla respuestas de error de aplicación para peticiones inválidas, problemas de acceso y fallos internos.

## SIMPATI

Los endpoints SIMPATI permiten inspeccionar la adquisición opcional, guardar una gráfica, listar las gráficas persistidas, abrir una imagen validada y eliminar una gráfica.

## Graphtec

El motor está en `src/report_generator/graphtec/`:

- `models.py`: registro normalizado y errores controlados.
- `txt_tabulated.py`: parser del TXT tabulado (DCW e IR). Cada formato es un módulo independiente; el otro formato Graphtec conocido se añadirá como un módulo nuevo registrado en `formats.py`.
- `formats.py`: selección del formato a partir del contenido. La extensión solo limita qué formatos se prueban.
- `timeline.py`: cálculo de `elapsed_time_seconds` (documentado en el propio módulo).
- `files.py`: reconstrucción segura de la ruta. Rechaza rutas absolutas, `..`, archivos de SIMPATI o CANoe, subcarpetas, enlaces que salen de la carpeta y archivos externos.
- `charts.py`: gráfica Matplotlib con doble eje Y, marcadores de límite y separadores de fase.

`src/report_generator/rendered_assets.py` reúne la creación de `_RenderedAssets`, la validación de PNG, la asignación de nombres sin sobrescritura y la resolución segura de gráficas guardadas. SIMPATI y Graphtec lo comparten.

Endpoints (`backend/app/services/graphtec_inspection.py`):

| Método | Ruta | Uso |
|---|---|---|
| POST | `/projects/graphtec/inspect` | Analiza `test_root` + `relative_path`. |
| POST | `/projects/graphtec/preview-chart` | Devuelve un PNG en Base64. No guarda nada. |
| POST | `/projects/graphtec/save-chart` | Renderiza en el servidor y guarda `graphtec_chart_NN.png` y su JSON. |
| POST | `/projects/graphtec/charts` | Lista las gráficas Graphtec guardadas. |
| GET | `/projects/graphtec/chart` | Sirve una gráfica guardada. |
| POST | `/projects/graphtec/delete-chart` | Elimina la gráfica y su JSON. |

Los errores se devuelven como `ApiError` sin traza: `graphtec_invalid_path` (400), `graphtec_invalid_file` y `graphtec_invalid_line` (400), `graphtec_invalid_chart_config` (400), `graphtec_unsupported_format` (415) y `graphtec_failed` (500).

Las gráficas Graphtec no contienen `simpati_acquisition` en el nombre, por lo que `find_test_result_charts` no las incluye en el PowerPoint.

## Documentación interactiva

Con el backend iniciado, FastAPI genera documentación OpenAPI interactiva. Se puede consultar mediante las rutas locales `/docs` y `/redoc` del backend.
