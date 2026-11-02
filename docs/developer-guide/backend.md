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
POST /projects/rendered-assets
GET  /projects/rendered-asset
POST /projects/rendered-assets/delete
POST /projects/graphtec/inspect
POST /projects/graphtec/preview-chart
POST /projects/graphtec/save-chart
```

## Imágenes del informe (`_RenderedAssets`)

`04_Report/_RenderedAssets` es el repositorio genérico de imágenes renderizadas que pueden seleccionarse para el PowerPoint. SIMPATI y Graphtec escriben allí sus gráficas; una imagen compatible copiada a mano también es válida. La procedencia se conserva como metadato informativo (`source`) y nunca decide si una imagen puede incluirse.

`backend/app/services/rendered_assets.py` expone el inventario sobre `src/report_generator/rendered_assets.py`:

| Método | Ruta | Uso |
|---|---|---|
| POST | `/projects/rendered-assets` | Lista las imágenes PNG, JPG y JPEG (extensión sin distinguir mayúsculas, contenido validado) situadas directamente en la carpeta, en orden natural estable. Los archivos no compatibles se devuelven en `warnings` y no bloquean el listado. |
| GET | `/projects/rendered-asset` | Sirve una imagen a partir de `test_root` y `relative_path`. |
| POST | `/projects/rendered-assets/delete` | Elimina la imagen y su JSON de metadatos y devuelve el inventario actualizado. |

Cada recurso (`RenderedAssetResult`) incluye `name`, `relative_path` (relativa al ensayo, con `/`, por ejemplo `04_Report/_RenderedAssets/graphtec_chart_01.png`), `extension`, `size`, `source` (`simpati`, `graphtec`, `manual`, `unknown`...) y `metadata_name`. La ruta relativa identifica el recurso en todas las peticiones.

Toda ruta recibida se valida en el servidor: debe ser relativa, sin componentes `.` ni `..`, resolverse como hijo directo de `_RenderedAssets` (los enlaces que salen de la carpeta se rechazan), existir, ser un archivo regular con extensión admitida y contener una imagen válida. Los errores son `rendered_asset_invalid_path` (400), `rendered_asset_not_found` (404), `rendered_asset_unsupported` (415), `rendered_asset_permission_denied` (403) y `rendered_asset_failed` (500).

`POST /projects/generate-report` acepta `selected_rendered_assets`: la lista ordenada de rutas relativas que se insertarán en `Test Results`. El backend valida cada ruta (rechaza duplicados, rutas inválidas, recursos externos o inexistentes) antes de escribir nada y pasa exactamente esa lista al motor. Una lista vacía genera el informe sin imágenes de resultados y nunca se sustituye por el inventario. Si el campo se omite (`null`), no se ha realizado ninguna selección y se incluyen todas las imágenes válidas del inventario (comportamiento de los scripts de consola). La respuesta indica `rendered_assets_count` y `rendered_assets`.

### Fotografías de evidencias

`POST /projects/inspect` devuelve, para cada evidencia, `report_section` (`assembly` para el tipo `initial`, `results` para el resto) y, para cada fotografía, `relative_path` (`02_Evidences/<carpeta>/<savedName>`) y `selectable` (existe y es una imagen admitida). `evidences.assembly_max_photos` (4) y `evidences.photos_per_slide` (2) informan de los límites.

`GET /projects/evidence-photo?test_root=...&relative_path=...` sirve una fotografía declarada por una evidencia válida. Errores: `evidence_photo_invalid_path` (400), `evidence_photo_not_found` (404), `evidence_photo_unsupported` (415), `evidence_photo_permission_denied` (403), `evidence_photo_failed` (500).

`POST /projects/generate-report` acepta `selected_assembly_photos` (máximo 4, solo evidencias `initial`) y `selected_result_photos` (sin límite, resto de evidencias). Se validan antes de escribir nada; el motor usa siempre el orden automático. `null` mantiene el comportamiento sin selección (4 primeras de Assembly, todas las de Results); `[]` no inserta ninguna. Errores: `report_generation_evidence_photo_limit` (400), `report_generation_invalid_evidence_photo` (400, incluye fotografías de la otra sección), `report_generation_evidence_photo_not_found` (404) y `report_generation_evidence_photo_unsupported` (415). La respuesta añade `assembly_photos_count`, `assembly_photos`, `result_photos_count` y `result_photos`.

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

`data` contiene `directory`, una entrada por fuente (`simpati`, `graphtec`, `canoe`), `simpati_acquisitions` (todas las adquisiciones `.x01`-`.x99` con `index`, `label`, `name`, `relative_path` y `size`, ordenadas por su número) y `simpati_file` (primera adquisición, solo por compatibilidad). Cada fuente incluye `files`, con `name`, `relative_path` (relativa a la raíz del ensayo, con `/`), `extension` (en minúsculas) y `size` (bytes). Solo se listan archivos regulares situados directamente en la carpeta de la fuente, ordenados sin distinguir mayúsculas; las subcarpetas, los archivos ocultos y los archivos de bloqueo de Office se excluyen. La inspección no lee el contenido de los archivos.

## Generación

`POST /projects/generate-report` genera el PowerPoint desde el `test_metadata.json` existente. El endpoint contempla respuestas de error de aplicación para peticiones inválidas, problemas de acceso y fallos internos.

## SIMPATI

El motor está en `src/report_generator/simpati/` y separa las responsabilidades:

- `files.py`: descubrimiento de todas las adquisiciones `.x01`-`.x99` de `03_Data/01_SIMPATI`, ordenadas por el número de la extensión, y resolución segura de una ruta recibida del cliente.
- `decoding.py`: prueba UTF-16 (con BOM o detectado por los bytes nulos), `utf-8-sig`, `cp1252` y `latin-1`. Una codificación solo se acepta si el texto tiene una estructura SIMPATI válida y no contiene caracteres de control, de modo que `latin-1` no produce falsos positivos.
- `structure.py`: detección dinámica de la fila de cabecera, la fila de unidades `[...]`, el preámbulo (equipo, programa, inicio y fin) y validación de los registros (marca temporal `%d.%m.%Y %H:%M:%S`, número de campos coherente y valores numéricos).
- `parser.py`: construcción del `DataFrame`. Conserva todos los canales con nombres únicos y estables (`_2`, `Unnamed_NN`), ignora los campos vacíos finales, rellena solo campos finales ausentes, rechaza (sin desplazar valores) los registros con más campos que canales, convierte la coma decimal, ordena por fecha y elimina las fechas duplicadas conservando la última. `attrs` incluye `source_file`, `encoding`, `acquisition_index`, `rejected_rows` y `preamble`.
- `channels.py`: clasificación semántica mediante perfiles de alias ampliables (`CHANNEL_PROFILES`): temperatura y consigna de cámara, aire de impulsión y de retorno, cesta, cámara caliente, cámara fría y probeta. Exige unidad de temperatura y datos numéricos. Los canales no reconocidos se conservan con `role = None`.
- `analysis.py`: análisis aislado de cada adquisición con estado `ready`, `no_thermal_channels`, `incompatible` o `error`.
- `outputs.py`: nombres `chart_simpati_xNN_MM.png` y metadatos de las gráficas (`source_file`, `source_relative_path`, `acquisition_index`, `acquisition_label`).

`src/report_generator/assets/simpati_extractor.py` mantiene la ruta de importación histórica y la herramienta de consola, que abre el editor Matplotlib para cada adquisición representable.

| Método | Ruta | Descripción |
| --- | --- | --- |
| POST | `/projects/simpati/inspect` | Analiza todas las adquisiciones (`acquisitions`, con su estado y error) y devuelve la vista previa de `relative_path` o, sin él, de la primera adquisición con canales representables. Incluye `found_count`, `processed_count`, `ready_count`, `without_thermal_count` e `incompatible_count`. Una adquisición incompatible no produce un error HTTP. |
| POST | `/projects/simpati/save-chart` | Recibe `relative_path` de la adquisición de origen y guarda `chart_simpati_xNN_MM.png` y su JSON sin sobrescribir nada. |

El servicio guarda en memoria el análisis de cada archivo mientras no cambian su fecha de modificación ni su tamaño.

## Graphtec

El motor está en `src/report_generator/graphtec/`:

- `models.py`: registro normalizado y errores controlados.
- `txt_tabulated.py`: parser del TXT tabulado (DCW e IR). Cada formato es un módulo independiente; el otro formato Graphtec conocido se añadirá como un módulo nuevo registrado en `formats.py`.
- `formats.py`: selección del formato a partir del contenido. La extensión solo limita qué formatos se prueban.
- `timeline.py`: cálculo de `elapsed_time_seconds` (documentado en el propio módulo).
- `files.py`: reconstrucción segura de la ruta. Rechaza rutas absolutas, `..`, archivos de SIMPATI o CANoe, subcarpetas, enlaces que salen de la carpeta y archivos externos.
- `charts.py`: gráfica Matplotlib con doble eje Y, marcadores de límite y separadores de fase.

`src/report_generator/rendered_assets.py` reúne la creación de `_RenderedAssets`, la validación de PNG, la asignación de nombres sin sobrescritura, el inventario genérico (`list_rendered_assets`), la resolución segura de una imagen (`resolve_rendered_asset`) y de una selección ordenada (`select_rendered_assets`) y la eliminación (`delete_rendered_asset`). SIMPATI y Graphtec lo comparten para guardar; el listado, la apertura y la eliminación son genéricos.

Endpoints (`backend/app/services/graphtec_inspection.py`):

| Método | Ruta | Uso |
|---|---|---|
| POST | `/projects/graphtec/inspect` | Analiza `test_root` + `relative_path`. |
| POST | `/projects/graphtec/preview-chart` | Devuelve un PNG en Base64. No guarda nada. |
| POST | `/projects/graphtec/save-chart` | Renderiza en el servidor, guarda `graphtec_chart_NN.png` y su JSON y devuelve el inventario de `_RenderedAssets` actualizado. |

Los errores se devuelven como `ApiError` sin traza: `graphtec_invalid_path` (400), `graphtec_invalid_file` y `graphtec_invalid_line` (400), `graphtec_invalid_chart_config` (400), `graphtec_unsupported_format` (415) y `graphtec_failed` (500).

Una gráfica Graphtec guardada es un recurso más de `_RenderedAssets`: aparece en el inventario con `source` igual a `graphtec` y el usuario decide si se incluye en el PowerPoint. El guardado SIMPATI (`/projects/simpati/save-chart`) funciona igual y escribe también un JSON con `source` igual a `simpati`.

## Documentación interactiva

Con el backend iniciado, FastAPI genera documentación OpenAPI interactiva. Se puede consultar mediante las rutas locales `/docs` y `/redoc` del backend.
