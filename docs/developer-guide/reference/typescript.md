# Referencia de TypeScript

La referencia automática del frontend se genera mediante TypeDoc.

La referencia incluye:

- Servicios HTTP.
- Reglas derivadas del estado del proyecto.
- Tipos compartidos con el backend.
- Componentes React.
- Componente principal de la aplicación.

```{raw} html
<a href="../../typescript-reference/index.html">
  Abrir la referencia automática de TypeScript
</a>
```


## Generación

Desde la raíz del repositorio:

```powershell
cd frontend
npm run docs:typescript
cd ..
```

La salida se genera en:

```text
docs/_build/html/typescript-reference
```

**Importante:** primero debe generarse la documentación de Sphinx y después la referencia TypeScript. Al limpiar `docs/_build`,también se elimina la salida generada por TypeDoc.