# Arquitectura general

## Vista de alto nivel

```text
Usuario
  │
  ▼
Frontend React + TypeScript
  │
  ├── Selección de carpeta mediante Tauri
  └── Peticiones HTTP
          │
          ▼
Backend FastAPI
  │
  ├── Inspección del proyecto
  ├── Gestión de gráficas SIMPATI
  └── Generación del informe
          │
          ▼
Motor Python report_generator
  │
  ├── Contrato de carpetas
  ├── Lectura y validación de metadata
  ├── Descubrimiento de evidencias
  ├── Detección de fuentes de datos
  └── Generación PowerPoint
          │
          ▼
04_Report
```

## Responsabilidades por capa

### Frontend

Presenta el flujo de trabajo, mantiene el estado de la interfaz, solicita la carpeta mediante Tauri y consume la API local.

### Tauri

Proporciona la ventana de escritorio y la integración necesaria para seleccionar una carpeta local. La lógica principal del informe no reside en Rust.

### Backend

Expone las operaciones mediante FastAPI, valida los modelos de petición y respuesta, llama a los servicios y convierte los errores de aplicación en respuestas HTTP.

### Motor de informes

Contiene la lógica independiente de la interfaz: rutas, metadata, evidencias, fuentes de datos, tratamiento de imágenes y modificación de la presentación.

## Entradas principales

- Carpeta individual del ensayo.
- `04_Report/test_metadata.json`.
- Descriptores `02_Evidences/*/evidence.json`.
- Recursos opcionales en `03_Data`.
- Plantilla PowerPoint configurada.

## Salidas principales

- PowerPoint editable en `04_Report`.
- Recursos SIMPATI guardados en `04_Report/_RenderedAssets`.
- Archivos de trabajo temporales en `04_Report/_Working`.

## Límite importante

La generación de `test_metadata.json` pertenece a un proceso externo. El proyecto actual lee y valida el JSON existente, pero no abre el Excel de inputs para regenerarlo.
