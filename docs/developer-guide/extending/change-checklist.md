# Lista de comprobación para cambios

Utiliza esta lista antes de cerrar una modificación funcional.

## Código y diseño

- [ ] El cambio está en la capa correcta.
- [ ] No se ha duplicado una utilidad existente.
- [ ] Las rutas y nombres centralizados siguen utilizándose.
- [ ] Los errores se convierten en mensajes controlados.
- [ ] No se exponen datos internos innecesarios.

## Estructuras de datos

- [ ] Se han revisado `test_metadata.json` y `evidence.json` cuando aplica.
- [ ] Se han actualizado validadores y versiones si el cambio es incompatible.
- [ ] Backend y frontend coinciden en nombres y tipos.

## PowerPoint

- [ ] El caso vacío funciona.
- [ ] El caso mínimo funciona.
- [ ] Las continuaciones no pierden ni duplican contenido.
- [ ] No hay solapamientos ni desbordamientos.
- [ ] Las gráficas que deben ser editables siguen siéndolo.
- [ ] `Conclusions` se conserva.
- [ ] La limpieza final mantiene solamente las diapositivas previstas.

## Validación automática

```powershell
python -m unittest discover -s tests
cd frontend
npm test
npm run build
cd ..
python -m sphinx -W --keep-going -b html docs docs/_build/html
```

## Validación manual

- [ ] La aplicación inicia y conecta con el backend.
- [ ] La inspección muestra estados coherentes.
- [ ] Se genera un informe de control.
- [ ] Se revisa visualmente el PowerPoint.
- [ ] La documentación describe el comportamiento final.

## Cierre en Git

```powershell
git status --short
git diff --check
```

Revisa los cambios antes de crear el commit y evita incluir datos reales de ensayos, informes generados o artefactos de compilación.
