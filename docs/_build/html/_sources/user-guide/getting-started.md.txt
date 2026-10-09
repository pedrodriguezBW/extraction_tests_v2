# Primeros pasos

## Qué hace la aplicación

La aplicación genera un informe PowerPoint editable a partir de los recursos de un ensayo climático.

El proceso parte de un archivo `test_metadata.json` ya existente. La aplicación no abre el Excel de inputs ni extrae sus datos. Antes de generar el informe, inspecciona la carpeta del ensayo y muestra los recursos encontrados, los errores y las advertencias.

## Antes de empezar

Comprueba que:

- La carpeta del ensayo corresponde a un ensayo individual, por ejemplo `TEST - 001`.
- Existe la carpeta `04_Report`.
- Existe un archivo válido `04_Report/test_metadata.json`.
- La plantilla PowerPoint configurada está disponible.
- El backend aparece como conectado en la cabecera de la aplicación.

Las carpetas `01_Inputs`, `02_Evidences` y `03_Data` se inspeccionan, pero su ausencia puede mostrarse como advertencia y no siempre impide generar el informe.

## Estados de conexión

La cabecera de la aplicación muestra uno de estos estados:

- **Checking connection:** se está comprobando la conexión con el backend.
- **Backend connected:** el backend está disponible.
- **Backend unavailable:** no se ha podido establecer la conexión.

Cuando el backend no está disponible, utiliza **Retry** después de comprobar que el servicio está iniciado.
