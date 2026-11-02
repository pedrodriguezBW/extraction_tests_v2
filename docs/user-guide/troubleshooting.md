# Solución de problemas

## El backend aparece como no disponible

Síntoma:

- La cabecera muestra **Backend unavailable**.
- Las acciones de inspección y generación no están disponibles.

Comprobaciones:

1. Verifica que el backend esté iniciado.
2. Pulsa **Retry**.
3. Si continúa el error, revisa la URL configurada para el backend.

## No puedo pulsar Inspect project

Comprueba que:

- Has seleccionado una carpeta.
- El backend aparece como conectado.
- No hay otra operación en curso.

## El proyecto aparece como inválido

Revisa el panel **Errors**. Las causas principales que muestra la inspección pueden incluir:

- Falta la carpeta `04_Report`.
- Falta `test_metadata.json`.
- `test_metadata.json` no es válido.
- La plantilla PowerPoint no está configurada o no se encuentra.

Corrige el problema y repite **Inspect project**.

## Aparecen advertencias sobre carpetas opcionales

La ausencia de `01_Inputs`, `02_Evidences`, `03_Data` o alguna fuente de adquisición puede mostrarse como advertencia.

Revisa si el recurso debería existir para ese ensayo. Una advertencia no equivale necesariamente a un error bloqueante.

## Faltan fotografías de una evidencia

La lista de evidencias muestra cuántas fotografías se han encontrado respecto a las referenciadas.

Comprueba:

- Que el `evidence.json` referencia el nombre correcto.
- Que la fotografía existe en la carpeta correspondiente.
- Que no se ha cambiado el nombre del archivo después de crear el descriptor.

Después, vuelve a inspeccionar el proyecto.

## No se encuentra una adquisición SIMPATI

Comprueba que los archivos `.x01`-`.x99` originales estén directamente en:

```text
03_Data/01_SIMPATI
```

Los archivos convertidos a `.txt` o `.csv` y las extensiones `.x00` no se consideran adquisiciones.

Si el ensayo no necesita SIMPATI, puedes continuar y generar el informe sin gráficas guardadas.

## Una adquisición SIMPATI aparece como incompatible

La tabla de adquisiciones muestra el motivo. Suele indicar que el archivo no tiene la estructura de una exportación SIMPATI (cabecera de canales, fila de unidades y registros con fecha `dd.mm.aaaa hh:mm:ss`) o que está dañado. Las demás adquisiciones pueden analizarse y representarse con normalidad.

Si el estado es **No representable channels**, el archivo es válido pero ningún perfil reconoce sus canales térmicos; sus canales siguen disponibles como canales avanzados.

## Generate PowerPoint sigue deshabilitado

Comprueba que:

- La inspección finaliza como **Valid project**.
- `test_metadata.json` existe y es válido.
- La plantilla PowerPoint está disponible.
- El backend está conectado.
- No hay una inspección, análisis, guardado o eliminación en curso.

## El informe se genera sin gráficas SIMPATI

Revisa el mensaje situado antes del botón de generación. Si indica que no hay gráficas guardadas, guarda las gráficas necesarias y vuelve a generar el informe.
