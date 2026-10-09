# Preparación del entorno de desarrollo

## Repositorio

Trabaja desde la raíz del repositorio `extraction_tests_v2`. Antes de comenzar, comprueba la rama activa y el estado del árbol de trabajo:

```powershell
git branch --show-current
git status
```

## Entorno Python

Se recomienda utilizar un entorno virtual local:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

El archivo `requirements.txt` reúne las dependencias del motor PowerPoint, tratamiento de imágenes y datos, FastAPI y Uvicorn.

:::{warning}
La instalación debe verificarse en un entorno limpio. Si `pip` informa de una dependencia no encontrada, revisa `requirements.txt` antes de modificar versiones o sustituir paquetes.
:::

## Dependencias del frontend

Desde la raíz del repositorio:

```powershell
cd frontend
npm install
```

El frontend utiliza los scripts definidos en `frontend/package.json` para desarrollo, compilación, pruebas y Tauri.

## Iniciar el backend

En una terminal situada en la raíz del repositorio:

```powershell
python -m uvicorn backend.app.main:app --reload
```

La aplicación FastAPI queda disponible de forma local. El endpoint `/health` permite comprobar su estado y versión.

## Iniciar el frontend de escritorio

En otra terminal:

```powershell
cd frontend
npm run tauri dev
```

Tauri ejecuta la aplicación en modo de desarrollo y utiliza el frontend de Vite.

## URL del backend

El frontend utiliza la variable `VITE_API_BASE_URL`. Si no está definida, la configuración actual usa:

```text
http://127.0.0.1:8000
```

## Generar la documentación

Desde la raíz del repositorio:

```powershell
python -m pip install -r docsequirements.txt
python -m sphinx -W --keep-going -b html docs docs\_build\html
```
