# Añadir una operación al backend

## Organización actual

El backend separa:

```text
backend/app/
├── api/
├── models/
└── services/
```

- `models/` define peticiones y respuestas.
- `services/` implementa la lógica de aplicación.
- `api/` expone la operación mediante FastAPI.

## 1. Definir los modelos

Crea o amplía los modelos Pydantic necesarios. Separa claramente:

- Datos de entrada.
- Resultado correcto.
- Error estructurado.

No devuelvas detalles internos o trazas al frontend.

## 2. Implementar el servicio

Añade la lógica en `backend/app/services/`. El servicio debe conectar la API con el motor y transformar sus errores en errores de aplicación controlados.

Mantén fuera del endpoint la lógica de negocio y el acceso complejo al sistema de archivos.

## 3. Registrar el endpoint

Añade la ruta en el router correspondiente dentro de `backend/app/api/`. Las operaciones de proyecto existentes utilizan el prefijo `/projects`.

Declara el modelo de respuesta y los códigos de error previstos.

## 4. Añadir pruebas

Comprueba:

- Petición válida.
- Validación de entrada.
- Recurso ausente.
- Problema de permisos o acceso, cuando aplique.
- Error interno controlado.
- Forma exacta de la respuesta.

## 5. Actualizar consumidores

Si el frontend utiliza la nueva operación, continúa con la guía **Añadir una operación al frontend**.

## 6. Actualizar documentación

Documenta el propósito, petición, respuesta, errores y efectos sobre archivos. Comprueba también la especificación OpenAPI generada por FastAPI.
