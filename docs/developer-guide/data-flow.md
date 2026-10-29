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

Si el usuario analiza SIMPATI, el frontend solicita la inspección de la adquisición. Las gráficas guardadas se escriben en `04_Report/_RenderedAssets` con un JSON de metadatos y el backend devuelve el inventario genérico actualizado.

### Graphtec

Si la fuente es Graphtec, el frontend envía `test_root` y `relative_path` a `POST /projects/graphtec/inspect`. La previsualización y el guardado envían además la configuración de la gráfica; el backend vuelve a leer el archivo y renderiza la imagen. Las gráficas Graphtec se guardan en `04_Report/_RenderedAssets` y pasan a formar parte del mismo inventario.

### Imágenes del informe

Tras la inspección y tras cada guardado, el frontend consulta `POST /projects/rendered-assets` y muestra todas las imágenes compatibles de `_RenderedAssets` con una casilla de selección (marcada por defecto). Al generar el informe envía en `selected_rendered_assets` la lista ordenada de rutas relativas seleccionadas; el backend valida cada una y el motor inserta exactamente esas imágenes.

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
