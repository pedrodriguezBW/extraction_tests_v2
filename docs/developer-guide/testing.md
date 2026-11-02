# Pruebas y validación

## Pruebas Python

Desde la raíz del repositorio:

```powershell
python -m unittest discover -s tests

```

Estas pruebas validan el motor, los contratos de carpetas, la inspección, el backend y la generación del informe según los casos cubiertos en `tests/`. `test_simpati_parser.py` cubre el descubrimiento de adquisiciones `.xNN`, la detección de codificación y estructura, los registros variables, la clasificación de canales y los ejemplos reales de `tests/fixtures/simpati` (`.x01` de cámara climática y `.x04` de choque térmico, sin modificar); `test_simpati_inspection.py` cubre el servicio y los endpoints con varias adquisiciones. `test_chart_export.py` cubre el formato común de las gráficas de `_RenderedAssets` (tamaño, tipografía, títulos, leyendas y fechas visibles y sin solapes, rangos Y estrechos) y su colocación en `Test Results` (una a cuatro gráficas, dos columnas, continuaciones). `test_rendered_assets.py` cubre el inventario de `_RenderedAssets`, la seguridad de rutas y la inserción en el PowerPoint de exactamente las imágenes seleccionadas; `test_rendered_assets_api.py` cubre el servicio y los endpoints genéricos.

## Pruebas del frontend

Desde `frontend/`:

```powershell
npm test
```

El comando ejecuta Vitest. La versión actual incluye pruebas para los servicios HTTP, las reglas de estado del proyecto, la selección de fuente y archivo, la lista de adquisiciones SIMPATI (`components/SimpatiAcquisitions.test.tsx`), el zoom del visor de gráficas (`services/chartZoom.test.ts` y `components/SimpatiChart.test.tsx`), la exportación de las gráficas para el informe (`services/chartExport.test.ts`), el panel Graphtec y la selección de imágenes del informe (`services/renderedAssetSelection.test.ts` y `components/RenderedAssets.test.tsx`).

## Compilación del frontend

```powershell
cd frontend
npm run build
```

Este comando ejecuta la comprobación de TypeScript y la compilación de Vite.

## Compilación de la documentación

Desde la raíz:

```powershell
python -m sphinx -W --keep-going -b html docs docs/_build/htmll
```

Las advertencias de Sphinx se consideran fallos para evitar referencias rotas o páginas mal incluidas.

## Comprobación recomendada antes de un commit

```powershell
python -m unittest discover -s tests
cd frontend
npm test
npm run build
cd ..
python -m sphinx -W --keep-going -b html docs docs\_build\html
git status --short
```

## Alcance de las pruebas

La superación de los tests automatizados no sustituye una generación real de control cuando se modifica:

- La plantilla PowerPoint.
- La paginación de una sección.
- La colocación de imágenes.
- La tipografía.
- La limpieza final de diapositivas.

En esos casos, genera un informe de prueba y revisa visualmente el PowerPoint resultante.
