# Adaptación IEC: decisiones y validación

## Alcance y punto de partida

Implementadas las fases 1 y 2 del plan del 8D TTT1136. Rama de trabajo:
`feature/iec-report-adaptation`, desde `17a8f3e` de
`feature/data-source-file-selector`; se conservan las correcciones posteriores
al commit `d7349a1` citado en el plan.

No se cambian el agente, el Excel, Final condition ni Conclusions. La
evaluación describe las condiciones de cámara; no certifica conformidad
integral con las normas ni demuestra estabilización del espécimen.

## Fase 1

- `src/report_generator/standards.py` centraliza catálogo, clave opcional
  `test.standard` y reconocimiento de cámara por tokens completos. Añadir
  códigos al catálogo actualiza automáticamente panel e informe.
- `config.LABORATORY_NAME = "STC"`. No se muestra acreditación.
- El metadata es de solo lectura. `test.standard` es opcional y admite texto
  o null. Un texto no vacío prevalece sobre el catálogo.
- `report_inputs.py` valida el JSON independiente con `schema_version: 1`,
  tipo de ensayo y hasta 500 puntos de medida. Los textos de cada celda
  tienen hasta 200 caracteres. Las funciones persistidas son `specimen`,
  `air`, `control` o vacío. El guardado usa archivo temporal y reemplazo
  atómico dentro del mismo directorio.
- API: `POST /projects/report-inputs/load` recibe `test_root` y opcionalmente
  `selected_simpati_files` (rutas relativas). Devuelve `inputs`, `warnings`,
  `test_types` y `channels`. Los canales se obtienen con el parser existente;
  no se consulta Graphtec. Se puede consultar la unión de varios logs aunque
  el selector actual de la interfaz permite abrir uno cada vez.
- `POST /projects/report-inputs/save` recibe `test_root` e `inputs`. La
  interfaz conserva las filas al cambiar la selección, precarga canales
  nuevos y avisa de los ausentes. Las filas eliminadas se vuelven a precargar
  si el canal aparece en una selección posterior.
- Generar desde la interfaz guarda primero la configuración actual. Si
  guardar falla, no se solicita generación. La consola lee lo ya guardado.
- Un archivo ausente o `_Working` borrada equivale a ensayo nuevo. JSON
  corrupto o versión desconocida: aviso, panel vacío, original conservado
  durante la lectura. Un Guardar explícito o el guardado automático posterior
  lo sustituye; la advertencia permite revisar el original antes de ello.
- Laboratory, Test type y Standard se presentan en Test Description con las
  etiquetas grises y los valores debajo del resto de parámetros, sin tabla.
  La cámara aparece una sola vez en la primera diapositiva de Assembly:
  nombre a la izquierda y tipo a su derecha, con la misma tipografía y en la
  misma línea, justo antes de Additional equipment. Caben cuatro equipos en
  esa diapositiva; el resto usa continuaciones. Los
  puntos de medida se presentan en continuaciones propias, estimando alturas
  por contenido y paginando sin reducir fuente.
  Test Procedure empieza en la primera diapositiva y ocupa el espacio hacia
  abajo antes de desplazar Test contacts. Si los contactos no caben tras el
  procedimiento, pasan a una continuación; si el procedimiento ocupa varias
  páginas, se divide y los contactos siguen al último fragmento.

## Verificación del catálogo

Se consultaron las vistas previas oficiales del texto IEC distribuido por
VDE Verlag y la vista previa IEC 60068-2-2:2025:

- [IEC 60068-2-14:2023, edición 7](https://assets.vde-verlag.de/iec-normen/preview-pdf/info_iec60068-2-14%7Bed7.0%7Db.pdf):
  Na, Rapid change of temperature; Nb, Change of temperature with specified
  rate of change; Nc, Rapid change of temperature, two-fluid-bath method.
- [IEC 60068-2-1:2025, edición 7](https://assets.vde-verlag.de/iec-normen/preview-pdf/info_iec60068-2-1%7Bed7.0%7Db.pdf):
  Ab, Cold for non-heat-dissipating specimens.
- [IEC 60068-2-2:2025, edición 6, vista previa IEC](https://cdn.standards.iteh.ai/samples/iec/iec-60068-2-2-2025/a49486573b1e46edad843d80002551b0/iec-60068-2-2-2025.pdf):
  Bb, Dry heat for non-heat-dissipating specimens.

Na no conserva el sufijo de transferencia de ediciones anteriores. Estos
nombres identifican el ensayo; los criterios de evaluación implementados
son las decisiones del plan, no una interpretación completa de las normas.

## Fase 2: algoritmo y límites

`simpati/tolerances.py`, identificador `extreme-plateaus-v2`:

1. Se usan todos los registros del log original. El visor puede reducirlos a
   1200 puntos, pero ni esa reducción ni el zoom deciden el resultado.
2. El canal debe ser una medida térmica. Se propone el punto marcado Control
   si está en el log. La consigna se elige entre los canales reconocidos por
   el parser: misma familia, o la única disponible. Con varias candidatas se
   exige selección explícita. Sin referencia inequívoca no se evalúa.
3. Los valores Fahrenheit se convierten a Celsius para calcular ±2 K; la
   banda se convierte de vuelta a la unidad del canal al dibujarla.
4. Meseta: consigna dentro de ±0,05 K respecto a su primer valor y al menos
   cinco minutos observados. Huecos mayores de tres veces la mediana del
   periodo de adquisición separan segmentos. No se interpola sobre huecos.
5. Se usan solo las mesetas extremas. En Na/Nb/Nc hacen falta ambos extremos
   separados al menos 4 K; Ab usa el frío y Bb el calor. Se descartan las
   mesetas intermedias y las rampas. Este criterio puede no representar
   programas multiseveridad; deben revisarse manualmente.
6. Asentamiento: `max(5, min(15, 0.1 * duración_observada_min))`. Se necesitan
   al menos dos muestras posteriores. La banda comienza tras ese intervalo.
   Desviación estrictamente mayor que 2 K: fuera; exactamente ±2 K: dentro.
   Muestras consecutivas fuera forman un tramo. Se conservan también las
   excursiones de una sola muestra, con marcador rojo.
7. TA medida es el mínimo observado tras el asentamiento en frío; TB medida,
   el máximo en caliente. Son extremos observados, no medias ni consignas.
8. t1 es la mediana de las mesetas delimitadas por cambios dentro del archivo,
   solo si la dispersión entre sus duraciones no supera el 10 % de la mediana.
   La duración observada es última muestra menos primera; su resolución es
   la del muestreo. Mesetas que tocan los extremos del archivo o un hueco no
   cuentan para t1 o ciclos. No se infiere la duración de porciones no grabadas.
   Se calculan también medianas independientes para frío y calor. Si no hay
   una duración global comparable, se muestran las de TA y TB que sí lo sean.
   Estas métricas dependen de la consigna y no exigen una ventana de tolerancia
   con al menos dos medidas posteriores al asentamiento.
9. Ciclos: pares completos de extremos opuestos, empiecen en frío o en calor,
   sin reutilizar mesetas ni cruzar huecos temporales o consignas ausentes.
   Un hueco no anula los pares completos de otros tramos. `cycles_partial`
   señala que el número corresponde solo a lo observado; si no se demuestra
   ningún par y hay partes incompletas se devuelve null, en lugar de cero.
   Ab/Bb muestran `—` porque no se aplica un recuento cíclico.
10. NOK si hay alguna excursión; OK solo con mesetas evaluables y medidas
    completas. Sin mesetas suficientes, o con medidas ausentes, huecos o
    registros rechazados, se evita declarar OK. Las medidas ausentes no anulan
    t1 ni ciclos deducibles de la consigna. Los huecos de consigna limitan las
    métricas a las mesetas completas de cada bloque y producen avisos explícitos.
    ΔTs siempre es null en el JSON. El recuadro no muestra estabilización
    ni referencias a rampas, porque no se evalúan.

El recuadro indica **Adquisición completa**: al guardar una vista ampliada
los dibujos se recortan al zoom y los números siguen describiendo el log
completo. Las bandas son verdes y las excursiones rojas; título, bandas,
recuadro y excursiones forman parte del PNG. El recuadro se diseña con texto
de 10 pt al tamaño de una columna del informe. Apagado conserva exactamente
el SVG anterior, verificado por prueba de igualdad.

`POST /projects/simpati/tolerances` recibe `test_root`, `relative_path`,
`test_type`, `channel` y `reference` opcional. El guardado SIMPATI admite
`tolerances: {test_type, channel, reference}` y recalcula el resultado antes
de persistirlo. El JSON existente añade `tolerances`, con versión del
algoritmo, canales, alcance, estado, severidades, ciclos, mesetas, excursiones
y avisos. No se confía en números enviados por el cliente.

## Ejemplos reproducibles

La plantilla corporativa configurada en `config.py` no está disponible en
este equipo. Los ejemplos usan una plantilla sintética con las dimensiones,
tipografía y helpers existentes. No incluyen datos de ensayos reales ni
sirven como certificado. Debe repetirse la revisión con la plantilla oficial
mediante `REPORT_TEMPLATE_PATH` antes de distribuir el paquete.

```powershell
.\.venv\Scripts\python.exe examples/build_iec_validation.py
node examples/render_iec_charts.mjs <ruta-absoluta-al-paquete-sharp>
.\.venv\Scripts\python.exe examples/build_iec_validation.py --finish
```

El script Node reutiliza el exportador SVG de producción y `esbuild` del
frontend; Sharp es una dependencia opcional solo para renderizar estos
ejemplos. Puede usarse el paquete Sharp del runtime de Codex, sin añadirlo
a las dependencias de producción. Los archivos quedan en
`examples/generated` (ignorado por Git): `IEC_phase1.pptx`, `IEC_phase2.pptx`,
logs sintéticos, configuración, PNG/SVG y JSON acompañantes.

La fase 2 contiene una gráfica OK y otra con una excursión forzada en frío.
Ambas muestran TA -40 °C, TB 85 °C, t1 30 min y dos ciclos completos.
Las pruebas usan también los dos logs reales versionados en
`tests/fixtures/simpati`, sin modificarlos.

## Validación realizada

- Batería Python: `python -m unittest discover -s tests -q` (373 pruebas,
  incluidas las pruebas de formato y paginación; dos omitidas por plataforma).
- Frontend: `npm test` (188 pruebas) y `npm run build`.
- Guardado/recarga, metadata intacto, archivos inválidos, `_Working` borrada,
  cambios de log, cámaras y prioridad de norma.
- OK/NOK sintético, límites inclusivos, asentamiento mínimo/máximo, huecos,
  datos insuficientes, Fahrenheit y consigna ambigua.
- Evaluación por API y persistencia del resultado recalculado junto al PNG.
- Renderizado real con PowerPoint y revisión visual de los dos ejemplos.
- Comprobación completa en Edge sin ventana con backend real: selección
  nativa simulada de la carpeta sintética, precarga, NOK, PNG/JSON y
  generación con una edición sin guardar. Script `examples/verify_iec_ui.mjs`
  (necesita backend en 8000, Vite en 1420 y Playwright opcional).
