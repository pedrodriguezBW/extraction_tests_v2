# Paginación y diapositivas de continuación

## Motivo

Las cantidades de muestras, equipos, puntos de perfil, evidencias y fotografías varían entre ensayos. El generador divide el contenido cuando no cabe en una única diapositiva.

## Utilidades de navegación

Las utilidades comunes se encuentran dentro de `src/report_generator/powerpoint/`. Los módulos de sección pueden:

- Dividir colecciones en grupos.
- Localizar una diapositiva dentro de una sección.
- Limpiar contenido anterior de la plantilla.
- Crear diapositivas de continuación.

## Contenido paginado

Las capacidades actuales incluyen:

- Paginación dinámica de `Tested Parts`: la altura de cada fila se estima según
  las líneas que ocupa la descripción y las continuaciones se crean al agotarse
  el espacio disponible, antes del pie de página.
- Tablas paginadas de perfiles climáticos y DUT.
- Continuaciones de secciones cuando el contenido supera la capacidad.
- Continuaciones automáticas para evidencias con más de dos fotografías (`<título> (cont.)`).
- Continuación `2. Test Assembly (cont.)` para las fotografías 3 y 4 del montaje.

Una descripción individual que necesite más espacio del disponible en una
diapositiva se informa como error en lugar de generar una tabla desbordada.

## Secuencia de evidencias

Las evidencias se ordenan por el campo `sequence`. La paginación no debe alterar ese orden.

## Regla de mantenimiento

Cuando se cambie la capacidad de una diapositiva, el tamaño de fuente, el tamaño de imagen o el espaciado:

1. Revisa el tamaño del grupo utilizado por la sección.
2. Comprueba la primera diapositiva y las continuaciones.
3. Prueba el caso vacío, el caso mínimo y un caso que fuerce varias diapositivas.
4. Verifica que no se duplique ni se pierda contenido.
5. Revisa la numeración después de la limpieza final.
