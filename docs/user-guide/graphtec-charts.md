# Gráficas Graphtec

El análisis de Graphtec es opcional. El informe PowerPoint puede generarse
aunque no exista ningún archivo Graphtec.

## Formato admitido

En esta versión solo se admite el **TXT tabulado de Graphtec**:

- Sin cabecera.
- Seis campos separados por tabuladores en cada línea: canal, tipo de
  ensayo, estado, tensión, medida y `FASE=tiempo s`.
- Tipos de ensayo **DCW** (medida de corriente en `uA`) e **IR** (medida de
  resistencia en `Mohm` o `Gohm`).
- Estados **TEST** y **PASS**. El resultado final es el estado del último
  registro de resultado (por ejemplo `PASS`).
- Fases **I**, **R**, **T** y **D**. Las letras se muestran tal como aparecen
  en el archivo; la aplicación no les asigna ningún significado.

```text
1	DCW	TEST	2.149kV	002.5 uA	T=000.4s
1	IR	TEST	0.958kV	>50Gohm	D=000.4s
1	IR	PASS	0.999kV	8.794Gohm	D=005.0s
```

Existe al menos otro formato de Graphtec que **todavía no se admite**. Si se
selecciona un archivo con otro formato o con otra extensión, la aplicación
muestra un error de formato no admitido.

## El nombre del archivo no se interpreta

Toda la información técnica (tipo de ensayo, canal, unidades, fases, tiempos
y resultado) se obtiene del contenido. El nombre del archivo solo se utiliza
para mostrarlo y para la trazabilidad. Dos archivos con el mismo contenido y
nombres distintos producen el mismo análisis y la misma gráfica.

## Analizar un archivo

1. Inspecciona el proyecto.
2. En **Data source**, selecciona **Graphtec**.
3. En **File**, selecciona un archivo de `03_Data/02_Graphtec`.
4. Pulsa **Analyze Graphtec**.

Se muestran el archivo, el formato, el tipo de ensayo, el número de
registros, el resultado final, las fases, las series, las unidades, la
duración y las advertencias.

## Tiempo acumulado

En el archivo, el tiempo de cada fase vuelve a empezar al cambiar de fase.
Para representar toda la adquisición en un único eje, la aplicación calcula
`elapsed_time_seconds`: al cambiar de fase suma el último tiempo alcanzado
por la fase anterior. Por ejemplo, si la fase R termina en 4,9 s y la fase T
empieza en 0,2 s, ese registro de T se representa en 5,1 s.

Si el tiempo retrocede dentro de una misma fase, el archivo se rechaza con
un error que indica la línea.

## Configurar la gráfica

- **Series:** Voltage [kV] y Current [uA] (DCW) o Resistance [Mohm] (IR).
  Corriente y resistencia nunca se mezclan.
- **Title:** se propone uno a partir del contenido, por ejemplo
  `Graphtec IR - Channel 1`.
- **Show legend** y **Show phase separators.**
- **Reset view** recupera la configuración inicial y la vista completa.

El eje X es siempre **Elapsed time [s]**. La tensión utiliza el eje
izquierdo y la corriente o la resistencia, el derecho. Con una sola serie
solo se dibuja su eje.

## Valores limitados

Un valor como `>50Gohm` indica que la resistencia es mayor que 50 Gohm, no
que mida exactamente 50 Gohm. La aplicación:

- Conserva el operador `>` en los datos.
- Dibuja el punto en el umbral normalizado (50000 Mohm) con un triángulo
  hueco, sin unirlo a la línea de valores medidos.
- Muestra la nota *Limit marker indicates a value greater than the displayed
  threshold.*

## Explorar la gráfica (zoom)

La gráfica aparece en cuanto se analiza el archivo y funciona igual que la de
SIMPATI. Arrastra sobre el área de la gráfica:

- **En horizontal:** amplía el intervalo de tiempo (eje X) sin cambiar los
  ejes Y.
- **En vertical:** amplía el rango de valores. Los dos ejes Y (tensión y
  corriente o resistencia) se amplían a la vez, en la misma proporción.
- **En diagonal:** amplía ambos ejes.

Los ejes Y muestran el rango completo de la adquisición hasta que los amplías;
ampliar el tiempo nunca los reajusta. Un **doble clic** sobre la gráfica
restablece solo el zoom; **Reset view** restablece también las series y las
opciones.

## Guardar

Pulsa **Save chart**. Se guarda exactamente la vista visible: el mismo
intervalo de tiempo, el mismo rango de cada eje Y, las series, el título, la
leyenda y los separadores de fase. La imagen para el informe se genera con el
formato común de exportación y con todos los registros del archivo.

La gráfica se guarda en `04_Report/_RenderedAssets` con un nombre generado
(`graphtec_chart_01.png`, `graphtec_chart_02.png`, …) que nunca sobrescribe
otra imagen. Junto a ella se guarda un JSON con el archivo de origen, el tipo
de ensayo, las series, el intervalo, los rangos de valores (`value_ranges`) y
las unidades.

Las gráficas guardadas aparecen en **Report images** con la procedencia
`Graphtec`, donde pueden abrirse, eliminarse y marcarse o desmarcarse para el
informe. Una gráfica recién guardada queda seleccionada por defecto y se
inserta en `Test Results` al generar el PowerPoint. Consulta
[Imágenes del informe](report-images.md).
