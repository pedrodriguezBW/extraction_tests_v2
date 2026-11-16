# Generador de informes PowerPoint

La aplicación genera un informe PowerPoint editable a partir del
`test_metadata.json` de un ensayo. Ese JSON lo produce un agente externo:
la aplicación ya no abre el Excel de inputs ni extrae datos de él.

Flujo principal:

1. Seleccionar la carpeta individual del ensayo mediante Tauri.
2. Inspeccionar la estructura del ensayo y `test_metadata.json`.
3. Revisar las evidencias, las fuentes de datos y la plantilla detectadas.
4. Seleccionar una fuente de datos (SIMPATI, Graphtec o CANoe) y uno de
   sus archivos.
5. Analizar y guardar opcionalmente gráficas SIMPATI o Graphtec.
6. Elegir en **Report images** qué imágenes de `04_Report/_RenderedAssets`
   se incluyen en *Test Results*.
7. Generar el PowerPoint editable dentro de `04_Report`.

## Configuración IEC del ensayo

El panel **Configuración del ensayo** permite elegir Na, Nb, Nc, Ab o Bb
y editar puntos de medida (canal, ubicación, sensor y función: Espécimen,
Aire o Control). Al seleccionar una adquisición SIMPATI se precargan sus
canales térmicos. Los canales nuevos se añaden vacíos; los ya editados se
conservan y los ausentes muestran «no encontrado en los logs». Graphtec no
precarga canales térmicos. También pueden añadirse y borrarse filas manuales.

**Guardar** escribe únicamente `04_Report/_Working/report_inputs.json`
(`schema_version: 1`). Al generar desde la interfaz, lo editado se guarda
automáticamente antes de solicitar el informe; un fallo al guardar impide
generar con datos anteriores. Los scripts de consola consumen la última
configuración guardada. El metadata del agente y el Excel no se modifican.
Si falta `_Working` o el archivo, se empieza vacío. Un JSON corrupto o con
versión desconocida se ignora con aviso y permanece en disco; un guardado
explícito posterior lo sustituye por la configuración actual.

El informe añade Laboratory (`STC`), Test type y Standard como etiquetas con
su valor debajo (sin tabla), el tipo de cámara
HU/OVEN/TS y la tabla de puntos de medida con continuaciones. Los campos
nuevos sin datos aparecen como `—`. La clave opcional `test.standard` del
metadata prevalece sobre la edición del catálogo; su nombre se centraliza
en `standards.STANDARD_METADATA_KEY`. Los nombres de temperatura de los
inputs pasan a **Min temperature (TA)** y **Max temperature (TB)**.

Test Procedure empieza en la primera diapositiva y se amplía hacia abajo.
Test contacts se coloca después; si no queda espacio, pasa a la continuación.
Si el procedimiento supera una página, se reparte entre continuaciones y los
contactos aparecen después de su último fragmento.

En cada gráfica SIMPATI, **Mostrar tolerancias** está desactivado inicialmente
y requiere un tipo de ensayo. Seleccione el canal evaluado (se propone el de
función Control) y, si hace falta, su consigna. La evaluación usa el archivo
completo, aunque el visor reduzca sus muestras o se amplíe una zona: el
recuadro indica **Adquisición completa**. Se sombrean ±2 K tras el asentamiento
de cada meseta y se resaltan las excursiones en rojo. El PNG incluye estado,
TA/TB medidas, t1 y ciclos; el resultado numérico se
guarda en el JSON acompañante. Rampas y estabilización del espécimen no se
evalúan. Sin datos suficientes se muestra `—`, nunca un OK supuesto.

La duración de meseta y los ciclos se calculan desde la consigna, incluso
si faltan medidas de temperatura. Solo se usan mesetas completas y no se
unen ciclos a través de huecos. Un recuento limitado a los tramos observados
se marca **parcial**. Si frío y calor tienen permanencias distintas, t1 se
muestra por separado para TA y TB cuando sus duraciones son comparables.

Los criterios numéricos, las decisiones por fase y cómo reproducir los
ejemplos están en [la nota de implementación IEC](docs/developer-guide/iec-implementation.md).

## Versión del generador

Al iniciar y antes de generar un informe, la aplicación comprueba la versión
contra `generador-informes.json` en la carpeta compartida:

```text
\\vigvsfil1.global.borgwarner.net\vigproductengineering\Documentacion_I+D\R&T\ToolingVersions\generador-informes.json
```

El manifiesto debe ser un JSON UTF-8 con la versión vigente y la ruta UNC
completa del paquete distribuido:

```json
{
  "version": "0.6.0",
  "package": "\\\\vigvsfil1.global.borgwarner.net\\vigproductengineering\\Documentacion_I+D\\R&T\\ToolingVersions\\generador-informes-0.6.0.zip"
}
```

Si la versión instalada no coincide, se muestra un diálogo al arrancar y se
bloquean la generación de informes, el guardado de gráficas y la eliminación
de imágenes hasta actualizar el programa. Las operaciones de inspección y
vista previa siguen disponibles. Si el manifiesto no está disponible o no es
válido, se muestra una advertencia, pero se permite seguir trabajando y
generar informes.

## Estructura del ensayo

La aplicación recibe la carpeta individual de un ensayo:

```text
TEST - 001/
├── 01_Inputs/
├── 02_Evidences/
│   └── <carpeta de evidencia>/
│       ├── evidence.json
│       └── <fotografías>
├── 03_Data/
│   ├── 01_SIMPATI/
│   ├── 02_Graphtec/
│   └── 03_CANoe/
└── 04_Report/
    ├── test_metadata.json
    ├── _RenderedAssets/
    └── _Working/
```

La carpeta seleccionada debe ser la carpeta individual del ensayo, no `04_Report`, una subcarpeta de evidencias ni la raíz del repositorio.

- `04_Report` y un `test_metadata.json` válido son obligatorios para
  generar el informe.
- `01_Inputs`, `02_Evidences` y `03_Data` se comprueban y se informan,
  pero su ausencia solo produce advertencias.
- Las fuentes SIMPATI, Graphtec y CANoe son opcionales. CSV es un formato
  de archivo, no una fuente independiente.
- El PowerPoint final se guarda directamente en `04_Report`. Se monta en
  `04_Report/_Working` y se mueve a `04_Report` cuando está completo.
- `04_Report/_RenderedAssets` es el repositorio genérico de imágenes del
  informe: gráficas SIMPATI y Graphtec guardadas desde la aplicación e
  imágenes PNG, JPG o JPEG copiadas a mano. El usuario marca cuáles se
  incluyen en *Test Results*; la procedencia es solo informativa.

Todas las rutas se definen en `src/report_generator/paths.py`.

### Fuentes de datos

`03_Data` contiene tres orígenes de datos opcionales:

| Fuente | Carpeta |
|---|---|
| SIMPATI | `03_Data/01_SIMPATI` |
| Graphtec | `03_Data/02_Graphtec` |
| CANoe | `03_Data/03_CANoe` |

La inspección devuelve, para cada fuente, si su carpeta existe y el
inventario de sus archivos: `name`, `relative_path` (relativa a la raíz del
ensayo), `extension` y `size`. Solo se listan los archivos situados
directamente en la carpeta de la fuente, ordenados alfabéticamente sin
distinguir mayúsculas. Se excluyen las subcarpetas, los archivos ocultos y
los archivos de bloqueo de Office. La inspección no lee el contenido de los
archivos.

Después de inspeccionar el ensayo, la interfaz muestra los selectores
**Data source** y **File**:

- **File** está deshabilitado si no hay fuente seleccionada, si la carpeta
  de la fuente no existe o si no contiene archivos.
- Cambiar de fuente limpia el archivo seleccionado y el análisis SIMPATI
  anterior. Cambiar de archivo limpia el análisis anterior. Ningún cambio
  de selección abre el editor de análisis automáticamente. La configuración
  del ensayo sí inspecciona los canales del log SIMPATI seleccionado para
  precargar sus puntos de medida.
- **Analyze SIMPATI** solo se habilita con la fuente SIMPATI y la
  adquisición SIMPATI detectada seleccionada.
- **Analyze Graphtec** lee el archivo Graphtec seleccionado. La lectura
  de CANoe se añadirá en un incremento posterior; la interfaz lo indica al
  seleccionarla.

### Graphtec

- Se admite el TXT tabulado de Graphtec (sin cabecera, seis campos por
  línea) con ensayos DCW (tensión y corriente) e IR (tensión y resistencia).
  Existe otro formato Graphtec que todavía no se admite y devuelve un error
  controlado de formato no admitido.
- El nombre del archivo no se interpreta: tipo de ensayo, canal, unidades,
  fases, tiempos y resultado se obtienen solo del contenido.
- El tiempo de cada fase se reinicia en el archivo; la gráfica utiliza
  `elapsed_time_seconds`, el tiempo acumulado de toda la adquisición.
- Los valores limitados como `>50Gohm` se dibujan en el umbral (50000 Mohm)
  con un marcador distinto y una nota; no se presentan como medidas exactas.
- Las gráficas se previsualizan y se guardan en `04_Report/_RenderedAssets`
  como `graphtec_chart_NN.png`, junto con un JSON de metadatos. Una vez
  guardadas aparecen en **Report images** y pueden incluirse en el PowerPoint
  como cualquier otra imagen.

## Imágenes del informe

- `POST /projects/rendered-assets` lista las imágenes compatibles de
  `_RenderedAssets` (PNG, JPG y JPEG, contenido validado, orden estable) con
  su procedencia (`simpati`, `graphtec`, `manual`...). Los archivos no
  compatibles se devuelven como advertencias.
- La interfaz muestra una casilla por imagen (marcadas por defecto),
  **Select all**, **Clear selection**, un contador, **Open image** y
  **Delete**.
- `POST /projects/generate-report` recibe `selected_rendered_assets`, la
  lista ordenada de rutas relativas seleccionadas. El PowerPoint incluye
  exactamente esas imágenes en ese orden; una lista vacía genera el informe
  sin imágenes de resultados. Toda ruta se valida en el servidor y se
  confina a `04_Report/_RenderedAssets`.

### Evidencias

Cada subcarpeta de `02_Evidences` puede contener un archivo
`evidence.json` con los campos `schemaVersion`, `id`, `type`, `title`,
`reference`, `notes`, `sequence`, `folder` y `photos`.

Las evidencias se descubren dinámicamente, se validan y se ordenan por
`sequence`. El nombre de la carpeta no determina el orden ni el tipo de
la evidencia.

La ruta de cada fotografía se resuelve combinando la carpeta que contiene
el descriptor con el valor `savedName` de la fotografía. Durante la
inspección se informa de los descriptores inválidos y de las fotografías
referenciadas que no existen.

Las evidencias válidas generan diapositivas cronológicas en la sección
`Test Results` del PowerPoint. Las diapositivas incluyen el título, la
referencia, las notas y las fotografías definidas en cada descriptor.

Las fotografías se colocan de dos en dos por diapositiva. Cuando una
evidencia tiene más de dos fotografías seleccionadas, el generador crea las
diapositivas de continuación necesarias (`<título> (cont.)`); una evidencia
sin fotografías seleccionadas conserva su diapositiva. Las evidencias de tipo
`initial` proporcionan las fotografías de la sección `Test Assembly` (como
máximo 4: dos en la diapositiva principal y dos en `2. Test Assembly
(cont.)`).

En **Evidence photos** la interfaz muestra dos paneles separados,
**2. Test Assembly** (evidencias `initial`, máximo 4) y **4. Test Results**
(resto de evidencias, sin límite), cada uno con su color, su contador y sus
botones. `POST /projects/generate-report` recibe la selección en
`selected_assembly_photos` y `selected_result_photos`
(`02_Evidences/<carpeta>/<savedName>`); el orden es siempre el automático.

## Uso por consola

- `python generate_report.py`: genera el PowerPoint desde el
  `test_metadata.json` existente.
- `python run_pipeline.py`: mismo flujo, mostrando también el JSON usado.
- `python -m src.report_generator.assets.simpati_extractor`: ventana
  interactiva para guardar gráficas SIMPATI en `04_Report/_RenderedAssets`.

## Organización del código

- `src/report_generator/paths.py`: contrato de carpetas del ensayo.
- `src/report_generator/metadata.py`: lectura y validación de
  `test_metadata.json`.
- `src/report_generator/evidences.py`: descubrimiento y validación de
  evidencias.
- `src/report_generator/data_sources.py`: fuentes de `03_Data` e
  inventario de sus archivos.
- `src/report_generator/graphtec/`: parser del TXT tabulado, tiempo
  acumulado, resolución segura de rutas y gráficas Graphtec.
- `src/report_generator/rendered_assets.py`: almacenamiento compartido de
  gráficas en `04_Report/_RenderedAssets`.
- `src/report_generator/media.py`: utilidades neutrales de imágenes.
- `src/report_generator/powerpoint/` y `sections/`: motor de generación.
- `src/report_generator/powerpoint/charts.py`: gráficas climática y DUT
  nativas y editables, creadas con los puntos de perfil del JSON.
- `backend/`: API FastAPI y servicios que conectan con el motor.
- `frontend/`: interfaz React + TypeScript con integración de escritorio
  Tauri.

## API

- `POST /projects/inspect`: estructura, `test_metadata.json`, evidencias,
  fuentes de datos con el inventario de sus archivos, plantilla, errores y
  advertencias.
- `POST /projects/generate-report`: genera el PowerPoint en `04_Report` con
  las imágenes indicadas en `selected_rendered_assets` y las fotografías de
  evidencia de `selected_assembly_photos` y `selected_result_photos`.
- `GET /projects/evidence-photo`: sirve una fotografía declarada por una
  evidencia válida (miniaturas de **Evidence photos**).
- `POST /projects/rendered-assets`, `GET /projects/rendered-asset` y
  `POST /projects/rendered-assets/delete`: inventario, apertura y eliminación
  de las imágenes de `04_Report/_RenderedAssets`.
- `POST /projects/simpati/inspect` y `POST /projects/simpati/save-chart`:
  análisis y guardado de gráficas SIMPATI.
- `POST /projects/graphtec/inspect`, `POST /projects/graphtec/preview-chart`
  y `POST /projects/graphtec/save-chart`: análisis, previsualización y
  guardado de gráficas Graphtec.

## Pruebas

- Python: `python -m unittest discover -s tests`
- Frontend: `cd frontend` y `npm test`

## Instalación en otros PC (paquete de un clic)

**Generar el paquete** (en el PC de desarrollo, con Python, Node.js y Rust):
doble clic en `empaquetar.bat` en la raíz del repositorio. El script
(`packaging/build_package.ps1`):

1. Comprueba que `version.py` y `tauri.conf.json` tienen la misma versión.
2. Descarga el Python embebido de la misma versión que el `.venv` (o usa
   `-PythonEmbedZip <zip>` si el proxy lo impide) e instala dentro las
   dependencias de `requirements.txt`.
3. Copia `backend/`, `src/`, `config.py` y la plantilla configurada.
4. Compila la interfaz en modo release (`npm run tauri -- build --no-bundle`).
5. Verifica el paquete (importaciones y `/health`) y crea en
   `%USERPROFILE%\GeneradorInformes-paquetes`:
   - `GeneradorInformes-<versión>/` y `generador-informes-<versión>.zip`;
   - `generador-informes.json`, el manifiesto de versión.

`empaquetar.bat -Publicar` copia además el ZIP y el manifiesto a la carpeta
compartida `ToolingVersions` (el manifiesto en último lugar).

**Instalar** (cualquier usuario, sin permisos de administrador ni Python,
Node o Rust): descomprimir el ZIP y doble clic en `Instalar.bat`. Se instala
en `%LOCALAPPDATA%\Programs\GeneradorInformes`, crea el acceso directo
*Generador de Informes* en el Escritorio y en el menú Inicio, y abre la
aplicación. Para actualizar se repite con el ZIP nuevo.

El acceso directo (o `Iniciar Generador de Informes.bat`) arranca el backend
oculto en `127.0.0.1:8000`, espera a `/health`, abre la interfaz y detiene el
backend al cerrar la ventana. La plantilla incluida se indica con la variable
`REPORT_TEMPLATE_PATH`. Registros: `%LOCALAPPDATA%\GeneradorInformes\logs`.

## Interfaz de escritorio

El frontend React + TypeScript y la configuración de Tauri están en
`frontend/`.

1. Inicia el backend:

   `python -m uvicorn backend.app.main:app --reload`

2. En otra consola, instala las dependencias del frontend:

   `cd frontend`

   `npm install`

3. Inicia la aplicación de escritorio:

   `npm run tauri dev`

La URL del backend se configura mediante `VITE_API_BASE_URL`. Si no se
especifica, se utiliza `http://127.0.0.1:8000`.
