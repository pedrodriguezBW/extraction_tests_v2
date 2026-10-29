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
- Selección de fuente de datos y archivo.
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

## Selección de fuente y archivo

`src/services/dataSourceSelection.ts` contiene el reducer de la selección (fuente, archivo y resultado SIMPATI asociado) y las reglas que deciden qué archivos se muestran, cuándo se deshabilita el selector de archivo y cuándo puede analizarse SIMPATI. `src/components/DataSourceSelector.tsx` presenta los dos selectores. Cambiar de fuente limpia el archivo y el resultado SIMPATI; cambiar de archivo limpia el resultado SIMPATI.

## Graphtec

`src/components/GraphtecAnalysis.tsx` muestra el resumen, la configuración, la previsualización y el guardado. Su estado está en `src/services/graphtecChart.ts` (reducer y validaciones puras). `App.tsx` lo monta con `key` igual a la ruta del archivo, de modo que cambiar de archivo o de fuente descarta el análisis, la configuración y la previsualización. Tras guardar una gráfica, el inventario de imágenes del informe se actualiza con la respuesta del backend.

## Componentes SIMPATI

`SimpatiChart.tsx` presenta y guarda la gráfica actual. Las gráficas guardadas no tienen una lista propia: se muestran en la sección genérica de imágenes del informe.

## Imágenes del informe (`Report images`)

`src/services/renderedAssetSelection.ts` contiene el reducer puro del inventario de `04_Report/_RenderedAssets` y de la selección: las imágenes detectadas se seleccionan por defecto; al refrescar el inventario se conserva la selección de las que siguen existiendo, se seleccionan las nuevas y desaparecen las eliminadas; `toggled`, `selectAll`, `clearSelection` y `removed` modifican la selección. `selectedRenderedAssetPaths` devuelve las rutas seleccionadas en el orden del inventario y es la lista exacta que `generateReport` envía en `selected_rendered_assets`. `renderedAssetSelectionSummary` produce los textos `N of M images selected for the report.`, `No rendered images were found. The report can still be generated.` y `No rendered images are selected. The report will be generated without them.`.

`src/components/RenderedAssets.tsx` muestra cada imagen una sola vez, sea cual sea su origen, con casilla accesible, miniatura, nombre, procedencia, tamaño, estado (seleccionada, no seleccionada, no disponible, en eliminación), `Open image` y `Delete`, además de `Select all` y `Clear selection`. Los archivos no compatibles devueltos en `warnings` se listan como no disponibles.

`App.tsx` mantiene este estado con `useReducer`, lo refresca tras la inspección y tras cada guardado (SIMPATI o Graphtec) y, al generar el informe, envía la selección explícita, aunque esté vacía.

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
