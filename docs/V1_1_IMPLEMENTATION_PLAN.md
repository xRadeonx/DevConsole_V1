# DevConsole V1.1 — Plan evolutivo y criterios GO / NO-GO

## Misión

Evolucionar DevConsole V1 sin perder ninguna capacidad funcional existente. La versión V1.1 mantiene el enfoque actual —Python local + HTML/CSS/JavaScript + herramientas nativas del sistema— y sustituye progresivamente implementaciones artesanales por componentes maduros cuando exista una ganancia demostrable en seguridad, rendimiento, mantenibilidad o UX.

La versión es específica para el ecosistema SISPER/PROTEO. No se busca eliminar conocimiento del dominio cuando éste aporta valor; sí se busca separar ese conocimiento de los mecanismos genéricos (procesos, terminales, Git, YAML, configuración, UI) para que el código sea mantenible.

## Invariantes de compatibilidad

1. Ninguna fase puede eliminar una capacidad disponible en `main`.
2. Viewer/QA es el nivel de acceso por defecto.
3. Developer y Administrator se desbloquean mediante credencial de producto/sesión; nunca deben concederse implícitamente.
4. Tilix continúa disponible aunque tmux/xterm se conviertan en la experiencia preferida.
5. Git CLI, kubectl y Podman/Docker siguen siendo las fuentes de verdad de sus respectivos dominios.
6. Los formatos de configuración existentes se mantienen compatibles mientras se introduzcan modelos tipados.
7. Las APIs existentes no cambian de contrato sin una capa de compatibilidad y tests de caracterización.
8. Las mejoras de UI se introducen por zonas; no se reescribe todo el frontend de una vez.

## Regla GO / NO-GO

Una fase obtiene **GO** únicamente cuando:

- la suite de regresión anterior sigue aprobando;
- los tests nuevos de la capacidad añadida aprueban;
- no disminuye el número de capacidades expuestas al usuario;
- los caminos destructivos conservan o elevan sus controles de autorización/ownership;
- existe fallback cuando se sustituye una implementación crítica;
- el cambio puede revertirse por commit/fase sin invalidar las fases anteriores.

Una fase es **NO-GO** si ocurre cualquiera de estos casos:

- se rompe un contrato API existente;
- un servicio que antes podía ejecutarse deja de poder hacerlo;
- se requiere Internet para usar DevConsole;
- se fuerza React/Electron/Node como runtime del panel;
- una dependencia nueva se vuelve obligatoria sin instalación/verificación explícita;
- una operación destructiva queda menos protegida;
- el nuevo UI oculta una capacidad sin ofrecer ruta equivalente.

## Fases

### Fase 0 — Baseline QA y trazabilidad

- CI en GitHub Actions para Python 3.11/3.12.
- Ejecutar suite de caracterización existente con historial Git completo.
- `compileall` como gate de sintaxis.
- Introducir configuración de Ruff y pytest sin cambiar runtime.
- Mantener documentado el único golden dependiente de workspace físico hasta convertirlo a fixture portable.

**GO:** CI verde sobre el código V1 antes de refactors funcionales.

### Fase 1 — Runtime y procesos

- Integrar `psutil` detrás de `ProcessInspector`/`ProcessIdentity`, nunca directamente desde handlers.
- Mantener implementación actual como fallback durante la transición.
- Reemplazar progresivamente `pkill`, `fuser` y parsing `/proc` en operaciones administradas.
- Mover sentinels temporales al runtime directory de usuario.

**GO:** mismo o mejor reconocimiento de procesos y cero reducción de protecciones de ownership.

### Fase 2 — Configuración tipada

- Introducir Pydantic para validar `panel`, servicios y configuración de runtime.
- Los JSON existentes siguen siendo aceptados.
- Los errores se convierten en diagnósticos accionables y no en fallos tardíos.

**GO:** fixtures actuales producen la misma configuración efectiva.

### Fase 3 — YAML/Kubernetes seguro

- Introducir `ruamel.yaml` para round-trip de manifiestos.
- Eliminar regex de mutación YAML cuando exista parser estructurado.
- Añadir preview/diff antes de cambios de imagen/deploy.

**GO:** modificar un campo no altera comentarios/estructura no relacionada del manifiesto.

### Fase 4 — Detección de capacidades de proyecto

Crear `ProjectDetector` con detectores independientes para Django, DRF, Celery, React, Node, package managers, Docker y Kubernetes.

Salida objetivo:

```json
{
  "name": "ms_contratos",
  "kind": "backend",
  "frameworks": ["django", "drf"],
  "package_manager": "pipenv",
  "capabilities": ["run", "test", "migrate", "shell", "worker", "git", "build", "deploy"]
}
```

Las heurísticas SISPER actuales permanecen como fallback.

**GO:** todo servicio actualmente descubierto continúa apareciendo y obtiene al menos las capacidades actuales.

### Fase 5 — Terminal profesional

- Mantener xterm.js.
- Incorporar addons Fit/Search/WebLinks/Clipboard y WebGL con fallback al renderer normal.
- Mantener tmux como dueño de sesión y Tilix como visor/terminal externo.
- Introducir WebSocket sólo donde la bidireccionalidad de terminal lo justifique; SSE continúa para streams unidireccionales.

**GO:** abrir/cerrar/reconectar terminal no mata el proceso administrado y Tilix continúa operativo.

### Fase 6 — Frontend modular

- Mantener HTML/CSS/JavaScript.
- Migrar `dashboard.js` progresivamente a ES Modules.
- Introducir componentes Web Awesome de forma local/self-hosted en componentes de bajo riesgo primero.
- Evaluar Grid.js para tablas, Split.js para paneles y CodeMirror 6 para editores.
- Cada migración conserva markup/API anterior hasta superar pruebas visuales y E2E.

**GO:** Playwright valida navegación, roles, acciones principales y ausencia de regresiones funcionales.

### Fase 7 — Roles de producto

- Viewer/QA: default, lectura.
- Developer: desbloqueo mediante clave/credencial de producto; acciones de desarrollo.
- Administrator: clave/credencial superior; infraestructura/despliegue/secretos.
- Hashes/verificadores pueden distribuirse con el producto; nunca claves en claro.
- Sesión autenticada y expiración explícita.

**GO:** matriz de permisos completa en tests backend + Playwright.

### Fase 8 — Build/Deploy resiliente

- Jobs persistibles/cancelables.
- build en worktree temporal para no mover la rama activa del desarrollador.
- abstracción de engine Podman/Docker.
- Kubernetes: contexto/namespace visible, diff previo, confirmación reforzada para producción y estrategia de rollback.

**GO:** build/deploy no modifica silenciosamente el workspace activo y conserva las capacidades actuales.

## Dependencias candidatas

Runtime, introducidas sólo en la fase correspondiente:

- `psutil`
- `pydantic`
- `ruamel.yaml`
- `watchfiles`
- `websockets`

Frontend self-hosted y versionado en el repositorio cuando se adopte:

- Web Awesome
- xterm.js + addons oficiales
- Split.js
- Grid.js
- CodeMirror 6

QA/desarrollo:

- pytest
- Ruff
- Playwright

## Política de implementación

Cada fase se entrega en commits pequeños. No se mezclan una reestructuración masiva de frontend y cambios de runtime en el mismo commit. Antes de avanzar de fase se inspecciona CI y se documenta GO/NO-GO. `main` no se modifica durante la evolución; la integración se realizará mediante PR una vez cumplidos los gates.