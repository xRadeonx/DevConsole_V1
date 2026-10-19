# DevConsole V1.1 — Plan evolutivo y criterios GO / NO-GO

## Misión

Evolucionar DevConsole V1 sin perder capacidades funcionales existentes. V1.1 mantiene el enfoque **Python local + HTML/CSS/JavaScript + herramientas nativas del sistema** y moderniza por capas, con compatibilidad y rollback explícitos.

El producto conserva conocimiento SISPER/PROTEO donde aporta valor, pero separa esos datos de mecanismos genéricos: procesos, terminales, Git, YAML, configuración, UI, build y Kubernetes.

## Invariantes

1. Ninguna fase puede quitar una capacidad V1 sin ruta equivalente/fallback.
2. Viewer/QA es el acceso por defecto.
3. Developer y Administrator requieren credencial/sesión real.
4. Tilix continúa disponible; tmux puede ser owner de sesión y xterm visor integrado.
5. Git CLI, kubectl y Podman/Docker siguen siendo fuentes de verdad.
6. Los formatos de configuración V1 continúan aceptados.
7. Una API V1 se conserva o se envuelve mediante compatibilidad; no se rompe silenciosamente.
8. El frontend se modulariza por adición, no por reescritura masiva.
9. Una dependencia nueva no puede convertir una instalación offline existente en inutilizable.
10. `main` no se modifica hasta superar la aceptación final.

## Regla GO / NO-GO

Una fase obtiene **GO** sólo si los tests nuevos aprueban, los gates V1 portables siguen aprobando, los caminos destructivos quedan igual o mejor protegidos y existe fallback cuando se sustituye una pieza crítica.

Es **NO-GO** si rompe contrato/API, fuerza Internet, obliga React/Electron/Node como runtime del panel, elimina Tilix, reduce controles de ownership/autorización o modifica silenciosamente el workspace activo.

## Estado de implementación

| Fase | Estado de implementación | Evidencia / decisión |
|---|---|---|
| 0. Baseline QA y trazabilidad | **GO** | GitHub Actions Python 3.11/3.12, `compileall`, Ruff crítico, shell syntax, suite portable, suite heredada diagnóstica y PR Draft. |
| 1. Runtime y procesos | **GO** | `psutil` detrás de `ProcessInspector`, fallback procfs, fixtures sintéticos preservados, tmux safe runner bloquea `fuser -k`. |
| 2. Configuración tipada | **GO** | Pydantic `extra=allow`, validación de panel/servicios y diagnóstico; JSON V1 no se reescribe. |
| 3. YAML/Kubernetes seguro | **GO** | `ruamel.yaml` round-trip, preview/diff, preflight contexto/namespace, apply confirmado y rollback; V1 `update_yaml_version` usa adapter con fallback. |
| 4. ProjectDetector | **GO** | Detección genérica Django/DRF/Celery/Node/React/package managers/Docker/K8s sin exigir prefijos SISPER. |
| 5. Terminal profesional | **GO** | xterm existente + Fit/Search/Clipboard, tmux preferido cuando existe, Tilix sigue como visor/fallback, wrapper seguro sin kill por puerto. |
| 6. Frontend modular | **GO** | ES Modules paralelos a `dashboard.js`, features de proyectos/operaciones y Playwright real. Dependencias UI sin beneficio concreto quedaron en NO-GO explícito. |
| 7. Roles de producto | **GO** | Viewer default, sesiones Developer/Admin reales, cookies HttpOnly/SameSite, PIN heredado implícito rechazado, matriz de roles backend + Playwright. |
| 8. Build/Deploy resiliente | **GO** | build jobs persistibles/cancelables, Git worktree temporal, Podman/Docker, K8s preflight/diff/apply/rollback. |

## Cambios de seguridad adicionales cerrados

- `SISPER_LOCAL_TOKEN_REQUIRED` se habilita por defecto al arrancar el servidor real; existe opt-out explícito para recuperación.
- Telemetría identificable/actividad/espejo queda detrás de Administrator; la metadata ya no afirma falsamente que no expone PII.
- Keycloak verifica TLS por defecto. CA interna configurable; TLS inseguro sólo con opt-in explícito de laboratorio.
- Un `index.lock` de Git nunca se borra automáticamente.
- Installer/uninstaller no matan procesos arbitrarios por ocupar un puerto.
- `/api/environment/switch` es transaccional: preflight global y rollback si falla un repositorio.
- `switch_env.sh` conserva su interfaz histórica, pero LOCAL/INTRANET ahora modifican **sólo `.env`** mediante perfiles declarativos. El parche de bitácora se conserva únicamente como acción explícita `bitacora-local/intranet`.

## Decisiones NO-GO deliberadas

No todo candidato debía instalarse. V1.1 rechazó componentes cuando aumentaban complejidad sin una capacidad concreta:

- **React / Electron:** NO-GO; implicarían una reescritura innecesaria.
- **Web Awesome:** NO-GO en V1.1; segundo sistema de componentes sin beneficio proporcional.
- **Grid.js:** NO-GO en V1.1; las tablas actuales no justifican otra dependencia.
- **Split.js:** NO-GO; solapa layout/Dockview existente.
- **CodeMirror 6:** NO-GO mientras el editor siga siendo texto simple.
- **WebGL addon:** NO-GO hasta disponer de artefacto autoalojado/versionado; renderer actual queda como fallback.
- **watchfiles / websockets:** NO-GO como dependencias obligatorias; el watcher actual y SSE cubren los casos actuales. WebSocket se incorporará sólo si una terminal bidireccional real lo requiere.

La evaluación detallada está en `docs/V1_1_FRONTEND_EVALUATION.md`.

## Estrategia de compatibilidad y recuperación

- `SISPER_V11_HANDLER=0` vuelve al handler HTTP V1 sin revertir commits.
- Dependencias Python V1.1 tienen fallback para mantener el arranque offline.
- El adapter YAML cae a la implementación V1 si `ruamel.yaml` no está disponible.
- tmux es preferido sólo cuando está instalado; Tilix sigue disponible y puede seleccionarse explícitamente.
- Los builds V1.1 se hacen en worktree temporal: la rama activa y cambios locales del desarrollador no se mueven.
- Jobs que estaban ejecutándose al caer DevConsole se recuperan como `interrupted`, no como éxito ficticio.

## QA y aceptación

El gate bloqueante incluye:

- Python 3.11 y 3.12;
- `compileall`;
- Ruff de errores semánticos críticos;
- regresión V1 portable + tests V1.1;
- validación de shell;
- sintaxis de módulos ES;
- Playwright con navegador real: carga V1 + V1.1, Viewer, Developer, logout y Administrator;
- `python -m devconsole.acceptance --json` en modo read-only.

La suite heredada completa sigue ejecutándose como **diagnóstico no bloqueante** porque contiene pruebas no herméticas ligadas al workspace SISPER físico, layouts Tilix no versionados y fixtures tmux dependientes del host. No se reintroducen hardcodes ni archivos externos ficticios sólo para volverla verde.

## Gate final de merge

La implementación de fases 0–8 puede obtener GO en CI, pero la PR permanece Draft hasta ejecutar en el workstation real:

```bash
./scripts/v11_acceptance.sh
# opcional, para exigir cero advertencias:
./scripts/v11_acceptance.sh --strict
```

Ese comando es sólo lectura. Después se realiza smoke operacional sobre el workspace real: lanzar/detener/reconectar servicios, visor Tilix, build local en worktree y `kubectl diff` en un namespace no productivo. **No se hace merge automático a `main` sin esa evidencia de host**, porque GitHub Actions no puede demostrar la disponibilidad ni el comportamiento de la infraestructura local del operador.
