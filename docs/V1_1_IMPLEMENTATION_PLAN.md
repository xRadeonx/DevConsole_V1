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
8. El frontend se modulariza por adición y extracción gradual, no por reescritura masiva.
9. Una dependencia nueva no puede convertir una instalación offline existente en inutilizable.
10. `main` no se modifica hasta superar la aceptación final.

## Regla GO / NO-GO

Una fase obtiene **GO** sólo si los tests nuevos aprueban, los gates V1 portables siguen aprobando, los caminos destructivos quedan igual o mejor protegidos y existe fallback cuando se sustituye una pieza crítica.

Se utiliza **GO aditivo** cuando una capacidad nueva está implementada y probada pero el flujo V1 histórico sigue siendo el camino principal. Esto NO equivale a afirmar que la migración visual/operativa de esa función terminó.

Es **NO-GO** si rompe contrato/API, fuerza Internet, obliga React/Electron/Node como runtime del panel, elimina Tilix, reduce controles de ownership/autorización o modifica silenciosamente el workspace activo.

## Estado tras segunda auditoría completa

| Fase | Estado | Evidencia / alcance real |
|---|---|---|
| 0. Baseline QA y trazabilidad | **GO** | CI Python 3.11/3.12, `compileall`, Ruff crítico, shell, Playwright, suite portable y diagnóstico heredado visible. |
| 1. Runtime y procesos | **GO** | `psutil` detrás del inspector con fallback procfs; identidad/ownership conservados. |
| 2. Configuración tipada | **GO aditivo** | Pydantic valida sin reescribir JSON V1; el loader histórico sigue siendo compatible. |
| 3. YAML/Kubernetes seguro | **GO** | `ruamel.yaml` round-trip + adapter V1 con fallback; preflight/diff/apply/rollback V1.1. |
| 4. ProjectDetector | **GO aditivo** | Detector genérico disponible y probado; `config.discover_services()` histórico sigue siendo la fuente principal de la UI V1. |
| 5. Terminal profesional | **GO backend / adopción UI parcial** | tmux ownership/fallback Tilix y addons xterm disponibles; no todas las vistas históricas usan aún esos addons. |
| 6. Frontend modular | **PARCIAL** | Existe capa ES Modules inyectada y probada, pero `dashboard.js` y handlers inline siguen siendo el frontend principal. No se declara modularización completa. |
| 7. Roles de producto | **GO** | Viewer default; Developer/Admin con sesión real; PIN incorporado eliminado; límites probados en navegador. |
| 8. Build/Deploy resiliente | **GO aditivo** | V1.1 tiene worktree, jobs persistentes/cancelables, Podman/Docker y K8s guard; la UI V1 conserva su ruta legacy por compatibilidad. |

## Correcciones de la segunda auditoría

La revisión independiente posterior al primer GO detectó y corrigió problemas que impedían declarar compatibilidad estricta:

- `/api/tilix/launch_selected` ya no altera el `message` histórico al intentar abrir un visor; el resultado del visor es metadata aditiva.
- `/api/environment/switch` sólo responde `success=true` cuando la transacción realmente termina `committed`; abort/rollback responden 409.
- rollback Git restaura también la referencia local de la rama destino o elimina la rama creada durante una transacción fallida.
- el instalador intenta activar `psutil`, Pydantic y `ruamel.yaml` en un venv aislado, con fallback offline.
- se eliminó por completo el PIN histórico incorporado del verificador base.
- cancelación de build ya no depende de recibir una nueva línea por stdout; termina el grupo de procesos y escala a kill si fuera necesario.
- estado persistido de builds queda con permisos restrictivos y límite también en memoria.

Estas correcciones tienen regresiones dedicadas dentro del gate bloqueante.

## Seguridad cerrada

- `SISPER_LOCAL_TOKEN_REQUIRED` se habilita por defecto al arrancar el servidor real; existe opt-out explícito de recuperación.
- Telemetría identificable/actividad/espejo requiere Administrator; la metadata no afirma falsamente ausencia de PII.
- Keycloak verifica TLS por defecto; CA interna configurable y modo inseguro sólo por opt-in explícito.
- Un `index.lock` de Git nunca se borra automáticamente.
- Installer/uninstaller no matan procesos arbitrarios por ocupar un puerto.
- LOCAL/INTRANET modifica `.env` declarativamente; el parche de bitácora queda como acción explícita legacy.

## Decisiones NO-GO deliberadas

No todo candidato debía instalarse:

- **React / Electron:** NO-GO; reescritura innecesaria.
- **Web Awesome:** NO-GO en V1.1; segundo sistema de componentes sin beneficio proporcional todavía.
- **Grid.js:** NO-GO en V1.1; no hay necesidad suficiente.
- **Split.js:** NO-GO; solapa layout existente.
- **CodeMirror 6:** NO-GO mientras el editor siga siendo texto simple.
- **WebGL addon:** NO-GO hasta disponer de artefacto autoalojado/versionado.
- **watchfiles / websockets:** no son dependencias obligatorias mientras watcher/SSE cubran los casos reales.

La evaluación detallada está en `docs/V1_1_FRONTEND_EVALUATION.md`.

## Compatibilidad y recuperación

- `SISPER_V11_HANDLER=0` vuelve al handler HTTP V1 sin revertir commits.
- Dependencias Python V1.1 tienen fallback para operación offline.
- YAML cae a la implementación V1 si `ruamel.yaml` no está disponible.
- tmux se prefiere sólo cuando existe; Tilix continúa seleccionable.
- builds V1.1 usan worktree temporal; rama activa y working tree no se mueven.
- jobs interrumpidos se recuperan como `interrupted`, nunca como éxito ficticio.

## QA y aceptación

El gate bloqueante incluye Python 3.11/3.12, compilación, Ruff crítico, regresión portable, tests de segunda auditoría, shell, sintaxis ES Modules, Playwright real y aceptación read-only.

La suite heredada completa sigue como **diagnóstico no bloqueante** porque contiene fixtures no herméticos ligados al workspace SISPER, layouts Tilix no versionados y tmux dependiente del host. Su fallo no se oculta ni se usa para justificar regresiones nuevas.

## Veredicto de implementación

- **Core de seguridad, compatibilidad y backends V1.1:** GO reproducible.
- **Capacidades nuevas ProjectDetector/build/terminal:** GO aditivo; aún conviven con rutas V1.
- **Modularización completa del frontend visible:** PARCIAL; no debe darse por terminada.
- **Merge a `main`: NO-GO** hasta aceptación del workstation real y hasta decidir si V1.1 cerrará con convivencia progresiva o exigirá migrar visualmente más flujos legacy antes del merge.

La aceptación local continúa siendo:

```bash
./scripts/v11_acceptance.sh
./scripts/v11_acceptance.sh --strict
```

seguida de smoke operacional en workspace y entorno no productivo.
