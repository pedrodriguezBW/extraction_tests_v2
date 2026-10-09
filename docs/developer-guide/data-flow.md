# Flujo de datos

## 1. Inicio

El frontend comprueba `GET /health`. Si la respuesta es correcta, muestra el backend como conectado y conserva la versión recibida.

## 2. Selección de carpeta

Tauri abre el selector nativo de directorios. El frontend guarda la ruta seleccionada y limpia los resultados asociados a una selección anterior.

## 3. Inspección

El frontend envía la ruta a:

```text
POST /projects/inspect
```

El backend inspecciona el contrato del ensayo y devuelve:

- Validez general.
- Carpetas encontradas.
- Estado de `test_metadata.json`.
- Evidencias y fotografías.
- Fuentes de datos.
- Estado de la plantilla.
- Errores y advertencias.

El frontend transforma esa respuesta en filas de inspección, métricas y condiciones de habilitación.

## 4. SIMPATI

Si el usuario analiza SIMPATI, el frontend solicita la inspección de la adquisición. Las gráficas guardadas se escriben en `04_Report/_RenderedAssets` y se listan nuevamente antes de generar el informe.

## 5. Generación

Antes de solicitar el PowerPoint, el frontend actualiza la lista de gráficas SIMPATI guardadas. Después llama a:

```text
POST /projects/generate-report
```

El backend delega en el servicio de generación y este utiliza el motor `report_generator`.

## 6. Motor PowerPoint

El motor:

1. Resuelve las rutas del ensayo.
2. Lee y valida `test_metadata.json`.
3. Descubre y ordena las evidencias mediante `evidence.json`.
4. Localiza recursos opcionales y gráficas guardadas.
5. Prepara una copia de trabajo de la plantilla.
6. Genera las secciones y diapositivas necesarias.
7. Limpia las diapositivas no utilizadas.
8. Guarda el PowerPoint editable en `04_Report`.

## 7. Respuesta

El backend devuelve el resultado estructurado. El frontend muestra el nombre y la ruta del informe generado o el error recibido.
