# Pruebas y validación

## Pruebas Python

Desde la raíz del repositorio:

```powershell
python -m unittest discover -s tests
```

Estas pruebas validan el motor, los contratos de carpetas, la inspección, el backend y la generación del informe según los casos cubiertos en `tests/`.

## Pruebas del frontend

Desde `frontend/`:

```powershell
npm test
```

El comando ejecuta Vitest. La versión actual incluye pruebas para los servicios HTTP y las reglas de estado del proyecto.

## Compilación del frontend

```powershell
cd frontend
npm run build
```

Este comando ejecuta la comprobación de TypeScript y la compilación de Vite.

## Compilación de la documentación

Desde la raíz:

```powershell
python -m sphinx -W --keep-going -b html docs docs\_build\html
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
