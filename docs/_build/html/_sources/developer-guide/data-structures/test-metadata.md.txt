# Estructura de `test_metadata.json`

## Finalidad

`test_metadata.json` contiene los datos estructurados que utiliza el motor para completar las secciones técnicas del informe.

El archivo se genera mediante un proceso externo. La aplicación de informes lo lee y valida, pero no abre el Excel de inputs ni regenera el JSON.

## Ubicación

```text
04_Report/test_metadata.json
```

## Estructura de primer nivel

La estructura observada contiene:

```json
{
  "schema_version": "1.0",
  "test": {},
  "people": {},
  "test_facility": {},
  "samples": [],
  "equipment": [],
  "climatic_inputs": {},
  "dut_controller_inputs": {},
  "test_events": []
}
```

## `schema_version`

Identifica la versión de la estructura. La aplicación actual trabaja con metadatos de versión `1.0`.

## `test`

Contiene la identificación general del ensayo:

- `input_date`
- `customer`
- `program_number`
- `program_description`
- `phase`
- `test_name`
- `start_date`
- `end_date`
- `original_path`
- `procedure`

## `people`

Agrupa las personas asociadas al ensayo.

### `requester`

Puede contener:

- `name`
- `email`
- `phone`

### `test_technician`

Contiene la identificación del técnico, mediante `name`.

## `test_facility`

Contiene los recursos principales de la instalación. En el contrato climático actual aparece `climatic_chamber`.

## `samples`

Es una lista de muestras. Cada elemento observado contiene:

- `sample_number`
- `sample_code`
- `sample_description`
- `fixture_code`
- `comments`

Los campos sin información pueden aparecer como `null`.

## `equipment`

Es una lista de equipos. Cada elemento observado contiene:

- `equipment_number`
- `equipment_used`
- `equipment_comments`
- `equipment_code`

## `climatic_inputs`

Contiene la configuración climática:

- `program_name`
- `minimum_temperature_c`
- `maximum_temperature_c`
- `cycle_duration_h`
- `number_of_cycles`
- `total_duration_h`
- `profile_points`

### Puntos del perfil

Cada punto observado contiene:

- `sequence`
- `time_min`
- `duration_min`
- `temperature_c`
- `humidity_percent`
- `actuation`

Los puntos se utilizan para construir tablas y gráficas editables del perfil.

## `dut_controller_inputs`

Contiene la configuración opcional del controlador DUT:

- `profile_required`
- `component`
- `controller_equipment`
- `dataset_filename`
- `voltage_v`
- `expected_current_a`
- `other_comments`
- `controller_codes`
- `profile_points`

Cuando no existe perfil DUT, los valores pueden ser `null` y las listas pueden estar vacías.

## `test_events`

Es una lista cronológica de eventos. Cada elemento observado contiene:

- `sequence`
- `technician`
- `date`
- `comments`
- `source_row`

## Campos que ya no pertenecen al contrato

La versión actual eliminó los objetos heredados `setup`, `source` y `extraction`. Las fotografías de montaje y de estados del ensayo se descubren mediante `evidence.json` y no desde rutas guardadas dentro de `test_metadata.json`.

## Evolución segura

Antes de cambiar esta estructura:

1. Actualiza la versión del esquema si el cambio es incompatible.
2. Modifica la validación Python.
3. Revisa las secciones del PowerPoint que consumen el campo.
4. Revisa modelos y tipos expuestos por el backend y el frontend.
5. Actualiza ejemplos y documentación.
6. Añade o modifica tests.

La documentación describe la estructura observada, pero las reglas exactas de obligatoriedad y tipos deben seguir estando respaldadas por la validación ejecutable del proyecto.
