# Estructura de `evidence.json`

## Finalidad

Cada descriptor representa un estado o acontecimiento documentado durante el ensayo. La aplicación descubre estos archivos dinámicamente, valida sus fotografías y ordena las evidencias por `sequence`.

## Ubicación

```text
02_Evidences/<carpeta de evidencia>/evidence.json
```

## Ejemplo

```json
{
  "schemaVersion": 1,
  "id": "21394a62-e341-4620-931b-0fb03a356a74",
  "type": "initial",
  "title": "Initial condition",
  "reference": {
    "type": "none",
    "value": ""
  },
  "notes": "",
  "sequence": 0,
  "folder": "00_Initial",
  "photos": [
    {
      "id": "d9a8ba7e-bbf1-4efe-8342-c78f305d4f78",
      "originalName": "PA285482.JPG",
      "savedName": "251028_Evidence_01.jpg",
      "captureDate": "2025-10-28T18:43:18",
      "mime": "image/jpeg",
      "size": 2580919
    }
  ]
}
```

## Campos principales

### `schemaVersion`

Versión numérica del descriptor. Los ejemplos actuales utilizan `1`.

### `id`

Identificador único de la evidencia.

### `type`

Categoría del estado documentado. Los tipos utilizados por el organizador actual son:

- `initial`
- `planned_inspection`
- `unplanned_stop`
- `incident`
- `restart`
- `final`
- `other`

### `title`

Título que identifica la evidencia en la interfaz y en el informe.

### `reference`

Describe el punto del ensayo al que corresponde la evidencia.

Los tipos utilizados actualmente son:

- `cycles`
- `hours`
- `stage`
- `date_time`
- `none`

`value` contiene el valor asociado y puede estar vacío cuando el tipo es `none`.

### `notes`

Texto libre asociado a la evidencia. Puede estar vacío.

### `sequence`

Define el orden real de las evidencias. El nombre de la carpeta no sustituye este campo.

La evidencia inicial observada utiliza `0`; las evidencias posteriores continúan la secuencia y la evidencia final aparece al final del recorrido.

### `folder`

Nombre declarado de la carpeta que contiene el descriptor y sus fotografías.

### `photos`

Lista de fotografías asociadas.

## Campos de cada fotografía

- `id`: identificador de la fotografía.
- `originalName`: nombre del archivo antes de guardarlo en la estructura.
- `savedName`: nombre del archivo que debe resolverse junto al descriptor.
- `captureDate`: fecha y hora declaradas para la captura.
- `mime`: tipo MIME.
- `size`: tamaño declarado en bytes.

La aplicación resuelve la imagen utilizando la carpeta del descriptor y `savedName`. Si el archivo no existe, la inspección informa de la fotografía ausente.

## Uso en el PowerPoint

- La evidencia `initial` alimenta las fotografías de `Test Assembly` (máximo 4 seleccionadas).
- El resto de evidencias se incorpora cronológicamente a `Test Results` (sin límite de fotografías).
- El usuario elige qué fotografías se insertan en cada sección; la identificación de cada una es `02_Evidences/<carpeta>/<savedName>`.
- Títulos, referencias, notas y fotografías pueden aparecer en las diapositivas.
- Se colocan dos fotografías por diapositiva; el generador crea diapositivas de continuación cuando hacen falta.

## Reglas de mantenimiento

- No utilices el nombre de la carpeta como único criterio de orden.
- No cambies `savedName` sin renombrar también el archivo físico.
- Conserva identificadores únicos.
- Mantén coordinados descriptor, fotografías y tests.
- Si se añade un tipo o referencia nuevos, actualiza el organizador, la validación, el frontend y la documentación.
