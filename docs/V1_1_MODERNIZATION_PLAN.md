# DevConsole V1.1 — Plan de modernización

## Misión

Modernizar DevConsole V1 sin perder ninguna capacidad existente. La V1.1 debe conservar el comportamiento funcional actual y sumar mejoras de mantenibilidad, seguridad, rendimiento, detección automática, terminales, QA y UX/UI.

La aplicación continúa siendo una herramienta especializada para el ecosistema SISPER/PROTEO. No se persigue convertirla en un producto genérico a costa de perder automatizaciones propias del entorno.

## Principios no negociables

1. **No feature regression**: ninguna funcionalidad existente se elimina sin reemplazo funcional equivalente o superior.
2. **Cambios reversibles**: cada fase debe poder revertirse de forma aislada.
3. **Backend real, UI delgada**: Git, tmux, kubectl y Podman siguen siendo las fuentes de verdad; DevConsole los orquesta.
4. **Viewer/QA por defecto**: el producto debe poder abrirse en modo de observación sin contraseña. Developer y Admin se desbloquean mediante credencial del producto.
5. **Sin reescritura masiva**: se moderniza por adaptadores y compatibilidad, no mediante un big-bang.
6. **Offline-first**: la aplicación debe funcionar en la red institucional sin depender de CDN ni servicios externos.
7. **Especialización permitida**: integraciones SISPER/PROTEO son válidas, pero deben aislarse del núcleo para evitar que la lógica transversal quede acoplada a nombres/puertos concretos.

## Matriz GO / NO-GO

Una fase obtiene **GO** sólo cuando cumple todos los criterios aplicables:

- suite de regresión relevante en verde;
- arranque de DevConsole sin errores nuevos;
- no disminuye el número de capacidades disponibles;
- no cambia por sorpresa comandos, ramas, puertos o manifiestos;
- existe fallback temporal cuando se reemplaza infraestructura sensible;
- errores nuevos fallan de forma segura y explicable;
- cambios de UI mantienen acceso a las acciones anteriores;
- no se introducen dependencias de Internet en runtime.

Es **NO-GO** si ocurre cualquiera de los siguientes:

- pérdida de una acción actualmente disponible;
- cambio destructivo de Git/entorno/Kubernetes sin confirmación equivalente;
- el nuevo componente no puede ejecutarse offline;
- la librería introduce más complejidad operacional que la que elimina;
- falla la regresión de seguridad, runtime o terminales;
- una migración requiere modificar todos los módulos simultáneamente.

## Fases

### Fase 0 — Baseline y QA

Objetivo: poder medir regresiones antes de modernizar.

- CI de sintaxis y pruebas de runtime/seguridad.
- configuración central de herramientas Python.
- inventario de capacidades existentes.
- pruebas de contrato para endpoints y roles.

**GO:** baseline reproducible y sin cambios funcionales.

### Fase 1 — Runtime y procesos

Objetivo: consolidar ProcessIdentity/Ownership y eliminar progresivamente `pkill`/`fuser -k` peligrosos.

- introducir `psutil` detrás de un adaptador;
- mantener `/proc` como fallback durante la migración;
- no matar procesos cuya identidad/ownership no esté confirmada;
- migrar sentinelas temporales a `XDG_RUNTIME_DIR`.

**GO:** mismo control de servicios con mayor precisión y sin afectar procesos externos.

### Fase 2 — Configuración tipada y YAML

- Pydantic para configuración de DevConsole, manteniendo lectura de formatos existentes;
- `ruamel.yaml` para edición round-trip de manifiestos Kubernetes;
- eliminar regex de YAML sólo después de pruebas de equivalencia;
- validación previa antes de aplicar cambios.

**GO:** todos los archivos actuales siguen siendo aceptados y las escrituras preservan estructura/comentarios relevantes.

### Fase 3 — Detección de proyectos y capacidades

Crear un `ProjectDetector` basado en señales estándar:

- `manage.py`, `pyproject.toml`, `Pipfile`, `requirements.txt`;
- `package.json`, Vite/React/Angular;
- Celery/workers;
- Docker/Containerfile;
- Kubernetes;
- scripts configurados por DevConsole.

La UI consumirá capacidades (`run`, `test`, `worker`, `build`, `deploy`, etc.) en lugar de depender sólo de nombres concretos.

**GO:** servicios SISPER actuales se detectan igual o mejor que en V1.

### Fase 4 — Terminal V2

- mantener tmux como dueño de la sesión;
- xterm.js permanece como emulador;
- habilitar addons Fit, Search, WebLinks y WebGL con fallback;
- estudiar WebSocket para terminal interactiva, manteniendo la vía actual hasta validar equivalencia.

**GO:** start/stop/restart/logs y apertura externa siguen disponibles; menor latencia y mejor navegación de logs.

### Fase 5 — Frontend modular y UX/UI

- mantener HTML + CSS + JavaScript;
- dividir `dashboard.js` en ES Modules por feature;
- introducir componentes Web sólo de forma progresiva;
- evaluar Web Awesome self-hosted para dialog, tooltip, dropdown, tabs y formularios;
- Grid.js para tablas donde aporte valor;
- Split.js para paneles/terminales redimensionables;
- CodeMirror 6 para `.env`, JSON y YAML;
- reducir handlers inline y avanzar CSP hacia enforcement.

**GO:** cada vista conserva sus acciones y mejora accesibilidad/consistencia sin requerir Node en runtime.

### Fase 6 — DevOps seguro

- operaciones Git continúan usando Git CLI como fuente de verdad;
- no borrar `.git/index.lock` automáticamente;
- preflight transaccional para cambios de entorno/branch;
- build sobre worktree cuando corresponda;
- `kubectl diff`, verificación de contexto/namespace y confirmaciones de producción;
- redacción de secretos en logs.

**GO:** igual o mayor capacidad DevOps con menor riesgo operativo.

### Fase 7 — QA UI / E2E

- pytest como runner progresivo (sin obligar a reescribir unittest existente);
- Playwright para Viewer, Developer y Admin;
- smoke tests de inicio, navegación, servicios, Git y terminal;
- pruebas destructivas sólo sobre fixtures/sandboxes.

## Arquitectura objetivo

```text
Browser
  HTML + CSS + ES Modules
  Web Components / Grid / Split / CodeMirror / xterm
                 |
                 v
        Local Python API
                 |
  +--------------+---------------+
  |              |               |
GitService   RuntimeManager   K8s/Build/Config
  |              |               |
 git        ProcessIdentity    kubectl/Podman
                 |
                tmux
```

## Regla de dependencias

Toda nueva dependencia debe clasificarse como:

- **core**: necesaria para el funcionamiento normal;
- **enhancement**: mejora con fallback cuando no está disponible;
- **dev/test**: sólo desarrollo y QA.

Durante las primeras fases, `psutil`, Pydantic, `ruamel.yaml`, `watchfiles` y `websockets` entrarán como **enhancement** hasta que su equivalencia esté validada. Esto evita convertir la modernización en un punto único de falla.

## Definición de terminado V1.1

La misión se considera cumplida cuando:

- Viewer/QA es el nivel predeterminado y Developer/Admin requieren credencial;
- no existe regresión funcional respecto de V1;
- runtime no depende de kills globales para las rutas modernizadas;
- configuración y YAML se validan antes de modificar;
- detección de servicios expone capacidades de forma estructurada;
- terminal integrada dispone de búsqueda, ajuste y aceleración con fallback;
- frontend está modularizado y los componentes principales son consistentes;
- CI y E2E cubren flujos críticos;
- DevConsole sigue pudiendo operar offline y sin Electron/React.
