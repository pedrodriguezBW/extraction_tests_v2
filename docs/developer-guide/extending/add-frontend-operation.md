# Añadir una operación al frontend

## 1. Definir los tipos

Añade o actualiza los tipos bajo:

```text
frontend/src/types/
```

Los nombres y tipos deben coincidir con la respuesta real del backend.

## 2. Añadir el servicio HTTP

Centraliza la llamada en:

```text
frontend/src/services/api.ts
```

La función debe encargarse de construir la petición, interpretar la respuesta y convertir un error HTTP en un error utilizable por la interfaz.

No construyas la misma URL directamente desde varios componentes.

## 3. Separar reglas derivadas

Si la operación necesita calcular disponibilidad, estados o resúmenes a partir de la respuesta, ubica la regla reutilizable en un servicio específico, siguiendo el patrón de `projectStatus.ts`.

## 4. Integrar el estado de interfaz

Gestiona expresamente:

- Estado inicial.
- Carga.
- Resultado correcto.
- Error.
- Limpieza al cambiar de proyecto.
- Bloqueo de peticiones duplicadas.

Revisa la variable general de actividad cuando la nueva operación deba impedir simultáneamente inspección, guardado o generación.

## 5. Crear o ampliar componentes

Mantén en `App.tsx` la coordinación del flujo y extrae a componentes independientes las áreas visuales con comportamiento propio.

## 6. Añadir pruebas

Cubre:

- Servicio HTTP correcto.
- Error del backend.
- Reglas derivadas.
- Habilitación y deshabilitación de acciones.
- Reinicio del estado al cambiar la carpeta.

## 7. Validar

Desde `frontend/`:

```powershell
npm test
npm run build
npm run tauri dev
```

Comprueba además el flujo real contra el backend local.
