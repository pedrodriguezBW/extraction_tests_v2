# Generador de PowerPoint

Esta sección documenta cómo el motor transforma los metadatos, las evidencias, las gráficas guardadas y la plantilla configurada en un informe PowerPoint editable.

```{toctree}
:maxdepth: 1

generation-pipeline
template-and-sections
images-and-charts
pagination-and-continuations
cleanup-and-validation
```

## Código relacionado

```text
src/report_generator/
├── generator.py
├── powerpoint/
└── sections/
```

`generator.py` coordina el proceso. `powerpoint/` contiene utilidades comunes de presentación y `sections/` contiene la generación del contenido de cada sección.
