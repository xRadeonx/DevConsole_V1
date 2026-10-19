# DevConsole V1.1 — Evaluación Frontend

## Decisión

V1.1 mantiene **HTML/CSS/JavaScript + ES Modules**. El objetivo es reducir `dashboard.js` progresivamente sin introducir un bundler ni un framework obligatorio.

La segunda auditoría confirma que esto es actualmente una **estrategia de migración**, no una modularización completa: el HTML histórico y `dashboard.js` continúan siendo el flujo principal y la capa V1.1 se inyecta de forma aditiva.

## Matriz GO / NO-GO

| Tecnología | Decisión V1.1 | Motivo |
|---|---|---|
| ES Modules nativos | **GO como superficie de extensión** | Modularización incremental sin toolchain; aún no reemplaza el monolito. |
| xterm.js existente | **GO** | Ya está autoalojado y sigue disponible donde el producto usa xterm. |
| FitAddon | **GO como capacidad** | Autoalojado y disponible mediante `terminal-enhancements.js`; adopción por vista es progresiva. |
| SearchAddon | **GO como capacidad** | Agrega búsqueda donde se conecta al terminal; no se afirma uso universal. |
| Clipboard API | **GO** | Capacidad nativa con degradación normal. |
| tmux como owner de sesión | **GO backend** | Desacopla la vida del proceso del visor; Tilix sigue disponible. |
| WebGL renderer | **NO-GO por ahora** | Falta artefacto autoalojado/versionado y no se agregará CDN. |
| Web Awesome | **NO-GO por ahora** | Segundo sistema completo de componentes sin beneficio suficiente todavía. |
| Grid.js | **NO-GO por ahora** | Las tablas actuales no justifican otra dependencia. |
| Split.js | **NO-GO** | Solapa layout/Dockview existente. |
| CodeMirror | **NO-GO por ahora** | Se incorporará sólo si la edición estructurada lo justifica. |
| React | **NO-GO** | Reescritura sin beneficio proporcional. |
| Electron | **NO-GO** | Servidor local + navegador cubre el caso con menor peso. |

## Capa introducida

```text
static/js/app-v11.js
├── modules/api-client.js
├── modules/event-bus.js
├── modules/terminal-enhancements.js
├── features/projects.js
└── features/operations.js
```

`DevConsoleV11Handler._serve_index_v11()` inyecta esta capa y `v11.css` sobre el `index.html` V1. La UI V1 continúa cargando `dashboard.js` y conserva numerosos handlers inline. Por ello el estado correcto es **PARCIAL para modularización integral**.

## Próxima condición para declarar frontend modular GO completo

No se declarará completado hasta que un conjunto significativo de funcionalidades visibles haya sido extraído desde `dashboard.js` a módulos con:

1. contrato de API estable;
2. listeners sin nuevos `onclick` inline;
3. tests Playwright de la interacción visible;
4. fallback/compatibilidad mientras dure la transición;
5. reducción medible del monolito, no sólo wrappers paralelos.

## Criterio para agregar una librería

Una dependencia frontend sólo pasa a GO cuando resuelve una capacidad concreta, es autoalojable, tiene degradación controlada, no obliga a reescribir la UI y queda cubierta por QA pertinente.
