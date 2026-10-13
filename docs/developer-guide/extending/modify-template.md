# Modificar la plantilla PowerPoint

## Riesgo principal

El generador localiza y modifica elementos de una plantilla existente. Cambiar títulos, placeholders, orden o estructura puede romper la localización de una diapositiva o provocar que la limpieza final conserve o elimine contenido incorrecto.

## 1. Conservar una copia de referencia

Antes de editar, conserva una copia de la plantilla funcional y registra qué versión utiliza la aplicación.

## 2. Identificar los elementos consumidos

Revisa en el código:

- Títulos utilizados para localizar diapositivas.
- Placeholders limpiados o reutilizados.
- Layouts empleados para continuaciones.
- Secciones conservadas por la limpieza.
- Diapositivas eliminadas expresamente.

## 3. Aplicar el cambio mínimo

Modifica solamente los elementos necesarios. Evita cambiar simultáneamente título, layout, orden y diseño de varias secciones porque dificulta localizar una regresión.

## 4. Comprobar la configuración

La ruta de la plantilla se configura actualmente desde `config.py`. Verifica que la aplicación apunta al archivo modificado y que la inspección lo detecta.

:::{note}
La ruta actual está asociada a un archivo local. Para transferir la aplicación a otro equipo será preferible sustituirla por una configuración externa o una ruta relativa controlada.
:::

## 5. Ejecutar pruebas y generación real

Ejecuta:

```powershell
python -m unittest discover -s tests
```

Después genera un informe y revisa:

- Portada.
- `Tested Parts`.
- Secciones de `TEST A`.
- Continuaciones.
- `Conclusions`.
- Eliminación de secciones sobrantes.
- Numeración final.

## 6. Documentar la dependencia

Actualiza la documentación cuando cambie:

- La ubicación de la plantilla.
- Un título utilizado como identificador.
- La capacidad de una diapositiva.
- Un layout base.
- El conjunto de diapositivas conservadas.
