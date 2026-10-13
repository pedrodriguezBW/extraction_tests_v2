# Imágenes y gráficas

## Fotografías de evidencias

Las fotografías se resuelven desde la carpeta que contiene `evidence.json` utilizando el campo `savedName` de cada elemento de `photos`.

La inspección informa de las fotografías referenciadas que no existen. El generador utiliza las imágenes válidas para `Test Assembly` y `Test Results` según el tipo y la secuencia de la evidencia.

## Inserción de imágenes

Las utilidades comunes de imagen se encuentran bajo:

```text
src/report_generator/powerpoint/
```

El módulo de secciones de montaje utiliza una función para añadir imágenes contenidas en el área disponible, evitando que la lógica de encaje quede duplicada en cada sección.

## Gráficas climáticas y DUT

`src/report_generator/powerpoint/charts.py` construye gráficas nativas de PowerPoint a partir de los puntos de perfil.

Las series solo utilizan valores numéricos válidos. Para el perfil climático, los campos de referencia incluyen `time_min` y `temperature_c`; el módulo también contempla otras series disponibles, como humedad o actuación cuando contienen datos utilizables.

## Gráficas SIMPATI

Las gráficas SIMPATI guardadas son imágenes persistentes almacenadas en:

```text
04_Report/_RenderedAssets
```

Antes de generar el informe, el sistema actualiza la lista de gráficas guardadas. Las gráficas existentes se incorporan a `Test Results`.

## Editabilidad

- Las gráficas climáticas y DUT son objetos editables en PowerPoint.
- Las gráficas SIMPATI guardadas se incorporan como recursos de imagen.
- Las fotografías se incorporan como imágenes.

## Comprobaciones tras un cambio

Cuando se modifica el tratamiento de imágenes o gráficas, debe revisarse:

- Que la imagen no se deforme.
- Que el encaje respete el área disponible.
- Que las fotografías aparezcan en la evidencia correcta.
- Que las series y ejes de las gráficas nativas sean editables.
- Que las gráficas SIMPATI guardadas se incluyan en `Test Results`.
