# Frontend React y Tauri

## Ubicación

El frontend se encuentra en:

```text
frontend/
```

Su configuración de escritorio Tauri se encuentra dentro de:

```text
frontend/src-tauri/
```

## Punto de entrada

`frontend/src/main.tsx` crea la raíz de React, carga `App` e importa los estilos principales.

El flujo inicial es:

```text
index.html
    ↓
src/main.tsx
    ↓
src/App.tsx
    ↓
componentes y servicios
```

## Componente principal

`src/App.tsx` coordina actualmente:

- Comprobación del backend.
- Selección y limpieza de la carpeta.
- Inspección del proyecto.
- Resumen de recursos.
- Análisis y gestión de SIMPATI.
- Generación del PowerPoint.
- Estados de carga, mensajes y errores.

Antes de modificarlo, identifica si el cambio pertenece a presentación, estado, acceso a la API o lógica reutilizable. La funcionalidad reutilizable debe mantenerse en servicios, tipos o componentes específicos cuando sea posible.

## Servicios HTTP

`src/services/api.ts` centraliza las operaciones realizadas contra FastAPI. Los componentes no deberían construir manualmente URLs o cuerpos de petición cuando ya existe una función de servicio.

## Estado derivado

`src/services/projectStatus.ts` contiene reglas utilizadas para traducir los resultados de inspección a estados visibles y decidir si el informe puede generarse.

## Tipos

Los contratos recibidos desde el backend se representan mediante tipos TypeScript bajo `src/types/`. Cuando cambie un modelo Pydantic o una respuesta de la API, revisa también su tipo equivalente en el frontend.

## Componentes SIMPATI

Los componentes específicos presentan y gestionan la gráfica actual y las gráficas guardadas. La eliminación de una gráfica debe actualizar el estado mostrado y su futura inclusión en `Test Results`.

## Desarrollo y compilación

Desde `frontend/`:

```powershell
npm run dev
npm run build
npm test
npm run tauri dev
```

- `npm run dev` inicia Vite.
- `npm run build` comprueba TypeScript y genera la compilación del frontend.
- `npm test` ejecuta Vitest.
- `npm run tauri dev` abre la aplicación de escritorio en modo desarrollo.

## Regla práctica

- Cambios visuales: componentes TSX y CSS.
- Comunicación HTTP: `src/services/api.ts`.
- Reglas de estado del proyecto: `src/services/projectStatus.ts`.
- Contratos de datos: `src/types/`.
- Configuración de escritorio: `src-tauri/`.
