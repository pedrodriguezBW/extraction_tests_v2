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

## Generación

`POST /projects/generate-report` genera el PowerPoint desde el `test_metadata.json` existente. El endpoint contempla respuestas de error de aplicación para peticiones inválidas, problemas de acceso y fallos internos.

## SIMPATI

Los endpoints SIMPATI permiten inspeccionar la adquisición opcional, guardar una gráfica, listar las gráficas persistidas, abrir una imagen validada y eliminar una gráfica.

## Documentación interactiva

Con el backend iniciado, FastAPI genera documentación OpenAPI interactiva. Se puede consultar mediante las rutas locales `/docs` y `/redoc` del backend.
