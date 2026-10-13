# Referencia de Python

Esta referencia se genera con Sphinx Autodoc a partir de las firmas, type hints y docstrings del código Python.

```{toctree}
:maxdepth: 2

report-generator
powerpoint
sections
backend
```

## Criterio de inclusión

Se documentan los módulos que forman la interfaz técnica mantenible del motor y del backend. Los scripts interactivos, archivos de arranque triviales y detalles internos sin docstring no se fuerzan en la referencia.

## Actualización

La referencia se actualiza al compilar Sphinx:

```powershell
python -m sphinx -W --keep-going -b html docs docs/_build/html
```

Autodoc importa los módulos indicados. Por eso, los módulos documentados no deben ejecutar operaciones con efectos secundarios durante la importación.
