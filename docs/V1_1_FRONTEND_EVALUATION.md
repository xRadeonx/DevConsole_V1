# DevConsole V1.1 — Evaluación Frontend

## Decisión

V1.1 mantiene **HTML/CSS/JavaScript + ES Modules** como arquitectura principal. El objetivo es reducir el monolito de `dashboard.js` progresivamente sin introducir un bundler ni un framework obligatorio.

## Matriz GO / NO-GO

| Tecnología | Decisión V1.1 | Motivo |
|---|---|---|
| ES Modules nativos | **GO** | Modularización sin toolchain de runtime y compatible con el HTML actual. |
| xterm.js existente | **GO** | Ya está autoalojado y es una capacidad central. |
| FitAddon | **GO** | Autoalojado; resuelve ajuste responsivo de terminal. |
| SearchAddon | **GO** | Autoalojado; agrega búsqueda sin reemplazar la consola existente. |
| Clipboard API | **GO** | Capacidad nativa del navegador con fallback normal. |
| tmux como owner de sesión | **GO** | Desacopla la vida del proceso de la ventana/visor. Tilix sigue disponible. |
| WebGL renderer | **NO-GO por ahora** | No existe un artefacto WebGL autoalojado versionado. La renderización actual sigue siendo fallback soportado; no se agrega CDN/Internet al runtime. |
| Web Awesome | **NO-GO por ahora** | Agregar un segundo sistema completo de componentes no aporta una capacidad necesaria y aumentaría CSS/JS, migración visual y superficie de regresión. |
| Grid.js | **NO-GO por ahora** | Las tablas actuales no requieren todavía virtualización/ordenamiento complejo que justifique otra dependencia. |
| Split.js | **NO-GO por ahora** | El laboratorio terminal ya dispone de Dockview y layout propio; duplicaría la responsabilidad de paneles. |
| CodeMirror | **NO-GO por ahora** | El editor `.env` sigue siendo texto simple. Se incorporará sólo si se agrega edición estructurada/validación en línea que lo justifique. |
| React | **NO-GO** | Reescritura sin beneficio proporcional; la UI V1 funciona y debe conservarse. |
| Electron | **NO-GO** | El servidor local + navegador ya cubre integración con SO/CLI con menor peso y complejidad. |

## Modularización introducida

V1.1 agrega una capa paralela y no destructiva:

```text
static/js/app-v11.js
├── modules/api-client.js
├── modules/event-bus.js
├── modules/terminal-enhancements.js
├── features/projects.js
└── features/operations.js
```

La capa V1 sigue cargando `dashboard.js`. Las funcionalidades se migrarán hacia módulos únicamente cuando tengan tests de contrato y sin eliminar el entrypoint anterior durante V1.1.

## Criterio para agregar una librería

Una dependencia frontend sólo pasa a GO cuando cumple simultáneamente:

1. resuelve una capacidad concreta que no cubre razonablemente la plataforma actual;
2. puede quedar autoalojada para operación sin Internet;
3. tiene fallback o degradación controlada;
4. no obliga a reescribir la UI existente;
5. queda cubierta por el smoke test Playwright y pruebas de contrato pertinentes.
