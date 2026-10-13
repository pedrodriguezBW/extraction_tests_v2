# Añadir una sección al PowerPoint

## Cuándo utilizar esta guía

Utiliza este recorrido cuando el informe necesite una sección nueva o cuando una sección existente deba dividirse en un módulo independiente.

## 1. Definir la entrada

Determina qué datos necesita la sección y de dónde proceden:

- `test_metadata.json`.
- `evidence.json`.
- Recursos de `03_Data`.
- Archivos de `_RenderedAssets`.

No leas directamente desde el frontend datos que pertenecen al motor de informes.

## 2. Crear o ampliar el módulo de sección

Las secciones se mantienen bajo:

```text
src/report_generator/sections/
```

La función debe recibir los datos ya resueltos que necesite y modificar la presentación de trabajo. Reutiliza las utilidades existentes de `powerpoint/` para estilos, imágenes, navegación y layouts.

## 3. Integrar la sección en el orquestador

Añade la llamada correspondiente en `generator.py` respetando el orden del informe.

Comprueba que la sección se ejecuta después de que sus datos y recursos hayan sido validados y antes de la limpieza final.

## 4. Gestionar capacidad y continuaciones

Define:

- Capacidad de la primera diapositiva.
- Capacidad de las continuaciones.
- Comportamiento sin contenido.
- Orden de los elementos.
- Tratamiento de textos largos e imágenes ausentes.

Utiliza las funciones comunes para dividir colecciones y crear continuaciones. No dupliques manualmente diapositivas mediante código específico si ya existe una utilidad equivalente.

## 5. Revisar la limpieza final

Si la nueva sección depende de una diapositiva de plantilla, comprueba que la limpieza no la elimine. Si crea diapositivas dinámicas, verifica que permanezcan en el orden correcto y se renumeren.

## 6. Añadir pruebas

Cubre como mínimo:

- Caso sin contenido.
- Caso mínimo.
- Caso que llena una diapositiva.
- Caso que fuerza continuaciones.
- Orden del contenido.
- Conservación de la sección tras la limpieza.

## 7. Validar visualmente

Genera un informe de control y revisa:

- Títulos y numeración.
- Tipografía mínima.
- Solapamientos.
- Saltos entre diapositivas.
- Encaje de imágenes.
- Editabilidad de tablas y gráficas.

## Archivos que normalmente se revisan

```text
src/report_generator/generator.py
src/report_generator/sections/
src/report_generator/powerpoint/
tests/
docs/developer-guide/powerpoint/
```
