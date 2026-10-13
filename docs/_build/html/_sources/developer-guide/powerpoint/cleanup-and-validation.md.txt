# Limpieza y validación final

## Objetivo de la limpieza

La plantilla contiene más material del necesario para un informe climático concreto. La versión actual elimina del resultado las diapositivas que no forman parte del informe final.

## Contenido conservado

El informe climático terminado mantiene:

- La portada.
- `Tested Parts`.
- `TEST A` y sus continuaciones generadas.
- La diapositiva editable `Conclusions`.

## Contenido eliminado

La limpieza elimina elementos de plantilla que no se utilizan en este flujo, incluidos:

- Resúmenes LEG y diapositivas explicativas sin uso.
- `TEST B` y `TEST C`.
- `Sample Analysis`.
- `Teardown`.
- `Additional Information`.
- Firmas.
- Diapositivas vacías finales.

Después de la limpieza, las diapositivas restantes se renumeran.

## Tipografía generada

La versión actual establece:

- Tamaño mínimo de texto generado de 12 pt.
- Valores principales generados de 16 pt.
- Mayor separación entre campos principales.

## Pruebas relacionadas

El proyecto incluye comprobaciones de:

- Eliminación de diapositivas no utilizadas.
- Tipografía generada.
- Salida de la generación.
- Continuaciones y contenido dinámico según los casos cubiertos por la suite.

## Validación recomendada

Ejecuta primero las pruebas automatizadas:

```powershell
python -m unittest discover -s tests
```

Después genera un informe de control y revisa visualmente:

- Orden de las secciones.
- Diapositivas de continuación.
- Tamaños de texto.
- Tablas y gráficas editables.
- Encaje de fotografías.
- Conservación de `Conclusions`.
- Ausencia de diapositivas sobrantes.
- Numeración final.

La revisión visual es necesaria porque una presentación puede ser técnicamente válida y, aun así, presentar desbordamientos, solapamientos o desequilibrios de composición.
