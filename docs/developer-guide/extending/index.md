# Guías de ampliación

Estas guías describen los cambios más habituales para ampliar la aplicación sin perder la separación entre interfaz, API, motor de informes y documentación.

```{toctree}
:maxdepth: 1

add-report-section
modify-template
add-api-operation
add-frontend-operation
evolve-data-structures
change-checklist
```

## Regla general

Antes de modificar el código, identifica todas las capas afectadas. Un cambio funcional puede requerir actualizar:

- Estructuras de datos.
- Validación Python.
- Motor de generación.
- Modelos y servicios del backend.
- Tipos y servicios del frontend.
- Pruebas.
- Documentación.

No todos los cambios afectan a todas las capas. Evita añadir elementos que no sean necesarios para el caso concreto.
