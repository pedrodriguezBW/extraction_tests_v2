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

## Imágenes de resultados (`_RenderedAssets`)

Las imágenes de resultados son archivos PNG, JPG o JPEG almacenados en:

```text
04_Report/_RenderedAssets
```

Pueden proceder de SIMPATI, de Graphtec, de una copia manual o de fuentes futuras como CANoe. El motor PowerPoint no las descubre ni las filtra por nombre, prefijo o procedencia: `populate_test_results` recibe en `result_image_paths` la lista ya validada de imágenes seleccionadas por el usuario y las inserta en `4. Test Results` en ese mismo orden, en grupos de cuatro por diapositiva, creando continuaciones cuando hacen falta. Una lista vacía genera la sección solo con las evidencias.

`generate_climatic_report` recibe `selected_rendered_assets` (rutas relativas al ensayo). Una lista, aunque esté vacía, es una selección explícita y se valida con `select_rendered_assets`; `None` (parámetro omitido, como en los scripts de consola) utiliza todas las imágenes válidas del inventario en su orden estable.

## Editabilidad

- Las gráficas climáticas y DUT son objetos editables en PowerPoint.
- Las imágenes de resultados se incorporan como recursos de imagen, sin deformarlas.
- Las fotografías se incorporan como imágenes.

## Comprobaciones tras un cambio

Cuando se modifica el tratamiento de imágenes o gráficas, debe revisarse:

- Que la imagen no se deforme.
- Que el encaje respete el área disponible.
- Que las fotografías aparezcan en la evidencia correcta.
- Que las series y ejes de las gráficas nativas sean editables.
- Que `Test Results` contenga exactamente las imágenes seleccionadas, en el orden recibido, y ninguna otra.
