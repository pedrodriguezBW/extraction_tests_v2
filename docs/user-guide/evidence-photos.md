# Fotografías de evidencias

La sección **Evidence photos** aparece dentro de **3. Review project resources** después de inspeccionar el proyecto. Permite elegir qué fotografías de `02_Evidences` se insertan en el informe.

## Dos zonas separadas

Las fotografías se muestran en dos paneles que nunca se mezclan. Cada panel tiene su propio color, su número de sección, su contador y sus propios botones:

| Panel | Evidencias que contiene | Sección del informe | Límite |
|---|---|---|---|
| **2. Test Assembly** (azul verdoso) | Evidencias de tipo `initial` (estado inicial) | `2. Test Assembly` | Hasta **4** fotografías |
| **4. Test Results** (violeta) | Todas las demás evidencias (`incident`, `planned_inspection`, `final`...) | `4. Test Results` | Sin límite |

La zona de una evidencia se decide por su tipo en `evidence.json`; una fotografía pertenece siempre a una sola zona. Cada miniatura muestra además una etiqueta **Assembly** o **Results** con el color de su panel.

Dentro de cada panel las fotografías se agrupan por evidencia, con su secuencia, título, tipo y referencia (por ejemplo `#1 Door seal leak · Incident · 450 cycles`).

## Selección

- **Test Results**: todas las fotografías están marcadas por defecto.
- **Test Assembly**: se marcan por defecto las 4 primeras. Al llegar a 4, las demás casillas se desactivan y aparece el aviso `Test Assembly admits up to 4 photos`. Desmarca una para elegir otra.
- **Select all** / **Clear selection** solo afectan a su panel. En Test Assembly, si hay más de 4 fotografías, el botón se llama **Select first 4**.
- Cada evidencia tiene también **Select** y **Clear** para sus fotografías.
- El contador indica `3 / 4 selected` en Test Assembly y `5 of 7 selected` en Test Results.
- Al volver a inspeccionar el mismo ensayo se conserva la selección; las fotografías nuevas se marcan (en Test Assembly solo si queda hueco) y las que ya no existen desaparecen.
- Las fotografías referenciadas que faltan o que no tienen un formato de imagen admitido se indican en su evidencia y no pueden seleccionarse.

## Inclusión en el PowerPoint

- El orden es siempre el automático: secuencia de la evidencia y orden de sus fotografías.
- **Dos fotografías por diapositiva**, sin deformarlas.
- **Test Assembly**: las fotografías 1 y 2 van en la diapositiva principal (junto al equipamiento); las fotografías 3 y 4, en una diapositiva `2. Test Assembly (cont.)` justo a continuación.
- **Test Results**: cada evidencia ocupa una diapositiva por cada dos fotografías; las siguientes se titulan `<título> (cont.)`. Una evidencia sin fotografías seleccionadas **conserva su diapositiva** con título, referencia y notas.

Junto al botón **Generate PowerPoint** se muestra el reparto antes de generar, por ejemplo:

```text
Test Assembly: 3 photos (2 slides) · Test Results: 7 evidence photos in 5 evidence slides
```
