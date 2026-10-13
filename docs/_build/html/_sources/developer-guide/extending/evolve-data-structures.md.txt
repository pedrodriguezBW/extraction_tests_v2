# Evolucionar las estructuras de datos

## Alcance

Esta guía se aplica a cambios en:

- `test_metadata.json`.
- `evidence.json`.
- Organización de la carpeta del ensayo.

## 1. Clasificar el cambio

Determina si el cambio es:

- Compatible: añade información opcional sin romper lectores existentes.
- Incompatible: cambia nombres, tipos, significado, obligatoriedad o ubicación.

Si es incompatible, actualiza la versión del esquema correspondiente.

## 2. Actualizar el productor

`test_metadata.json` se genera externamente. Cualquier cambio debe coordinarse con ese proceso para que produzca exactamente la estructura esperada.

Los descriptores `evidence.json` también deben mantenerse coordinados con la herramienta que organiza las evidencias.

## 3. Actualizar la validación Python

Modifica la lectura y validación antes de utilizar el nuevo campo. Define cómo se comportará la aplicación ante:

- Campo ausente.
- Valor `null`.
- Tipo incorrecto.
- Lista vacía.
- Versión desconocida.

## 4. Actualizar el motor

Localiza las secciones del PowerPoint que consumen la estructura. Evita introducir valores inventados cuando falte información; representa fielmente la fuente o aplica el comportamiento vacío definido.

## 5. Actualizar backend y frontend

Si la estructura aparece en una respuesta de inspección:

- Actualiza los modelos Pydantic.
- Actualiza los tipos TypeScript.
- Revisa resúmenes, mensajes y reglas de habilitación.

## 6. Añadir ejemplos y pruebas

Mantén casos para:

- Estructura completa.
- Campos opcionales vacíos.
- Error de tipo.
- Versión no soportada.
- Migración desde una versión anterior, si se admite.

## 7. Actualizar documentación

Modifica las páginas de `data-structures/` y las secciones del generador afectadas.
