# DevConsole V1.1 — Reporte GO / NO-GO

## Alcance

Este reporte separa tres conceptos que no deben confundirse:

1. **Implementación de fases:** código y compatibilidad introducidos en `refactor/v1.1-foundation`.
2. **Gate reproducible CI:** aquello que GitHub Actions puede demostrar en un runner limpio.
3. **Aceptación de host:** capacidades que dependen del workstation, el workspace SISPER real, tmux/Tilix, Podman/Docker, kubectl, certificados internos y recursos on-premise.

`main` permanece sin modificaciones. La integración está concentrada en la PR Draft #2.

## Baseline heredado

La primera ejecución reproducible de la suite V1, antes de introducir cambios funcionales V1.1, reveló deuda de QA preexistente:

- 524 tests aprobados;
- 54 fallos;
- 48 skipped;
- 1 deselected;
- 321 subtests aprobados.

Los fallos se concentraban en fixtures dependientes del workspace físico, layouts Tilix no versionados, configuración SISPER externa, integración tmux dependiente del host y algunos contratos desactualizados. Dos defectos de producto sí quedaron identificados y corregidos inmediatamente: `fuser -k` en el instalador y `stop-single` ausente del contrato del backend terminal.

La suite heredada completa se conserva visible como job **diagnóstico**. No se maquilla mediante exclusiones masivas ni se reintroducen hardcodes eliminados sólo para satisfacer expectativas antiguas.

## Gate bloqueante V1.1

Para declarar GO de implementación se exige:

- Python 3.11 ✅
- Python 3.12 ✅
- `compileall` ✅
- Ruff crítico ✅
- regresión V1 portable ✅
- tests V1.1 ✅
- shell syntax ✅
- módulos ES syntax ✅
- Playwright Chromium ✅
- Viewer por defecto ✅
- Developer con credencial real ✅
- logout → Viewer ✅
- Administrator con credencial real ✅
- aceptación read-only ✅

El job diagnóstico heredado **no es el gate de release** mientras dependa de recursos externos no versionados. Su función es detectar cambios de patrón y ayudar a convertir progresivamente pruebas no herméticas en fixtures reproducibles.

## Capacidades conservadas

V1.1 no elimina las rutas principales V1:

- selección de workspace;
- descubrimiento de servicios;
- lanzamiento de servicios y auxiliares;
- Tilix;
- tmux;
- terminal integrada xterm;
- Git fetch/pull/push/branching;
- edición `.env`;
- modos LOCAL/INTRANET;
- infraestructura local;
- build/push de imágenes;
- manifiestos Kubernetes;
- deploy/restart/rollout;
- telemetría y espejo para administradores;
- temas y utilidades SISPER existentes.

Las rutas V1 desconocidas por el facade V1.1 delegan al handler heredado. El facade se puede desactivar con `SISPER_V11_HANDLER=0` como recuperación de emergencia.

## Capacidades agregadas

- backend de procesos `psutil` con fallback procfs;
- validación Pydantic compatible;
- YAML round-trip con `ruamel.yaml`;
- ProjectDetector genérico por capacidades;
- Fit/Search/Clipboard para xterm;
- tmux preferido como owner cuando está disponible;
- wrapper tmux que bloquea kill por puerto;
- Developer con sesión real;
- trust token local por defecto;
- TLS Keycloak verificado por defecto;
- build jobs persistibles/cancelables;
- builds en Git worktree temporal;
- engine Podman/Docker;
- K8s preflight/diff/apply/rollback;
- switching Git multi-repo transaccional;
- perfiles LOCAL/INTRANET declarativos y sin patch implícito de source;
- ES Modules paralelos al frontend V1;
- smoke E2E Playwright;
- comando de aceptación local read-only.

## Seguridad: cambios que deliberadamente endurecen comportamiento

Un comportamiento peligroso no se considera una capacidad que deba permanecer habilitada implícitamente:

- un puerto ocupado ya no autoriza `fuser -k`;
- un `index.lock` ya no se borra por antigüedad;
- `sisper2026` ya no concede administración por fallback;
- un cambio LOCAL/INTRANET ya no reescribe `views.py` de forma lateral;
- TLS Keycloak ya no usa `CERT_NONE` por defecto;
- telemetría identificable no se expone a Viewer/Developer.

Cuando existe una necesidad operativa legítima se conserva una ruta explícita: Tilix sigue disponible, el parche de bitácora existe como acción dedicada, TLS inseguro puede habilitarse sólo mediante opt-in de laboratorio y el handler V1 puede restaurarse temporalmente mediante feature flag.

## NO-GO deliberados

No se adoptaron React, Electron, Web Awesome, Grid.js, Split.js, CodeMirror 6 ni WebGL sólo por modernizar. Cada dependencia debe demostrar una capacidad concreta, ser autoalojable y tener fallback. Las razones están documentadas en `V1_1_FRONTEND_EVALUATION.md`.

## Riesgos que sólo puede cerrar el workstation real

GitHub Actions no puede demostrar por sí solo:

- que todos los repositorios reales del workspace sean detectados como antes;
- que los servicios Django/React/Celery concretos arranquen con sus entornos reales;
- que una sesión tmux sobreviva a cerrar/reabrir el visor en el escritorio Fedora;
- que Tilix adjunte correctamente a las sesiones reales;
- que Podman/Docker pueda construir las imágenes institucionales;
- que kubectl apunte al cluster/contexto/namespace esperado;
- que una CA institucional configurada valide Keycloak on-premise;
- que manifests, registries y secretos del entorno privado estén accesibles.

Por ello, **hacer merge sin aceptación local sería un falso GO**.

## Procedimiento final de aceptación

Primero, check read-only:

```bash
git checkout refactor/v1.1-foundation
./scripts/v11_acceptance.sh
```

Para una estación completamente preparada:

```bash
./scripts/v11_acceptance.sh --strict
```

Luego se realiza smoke operacional en entorno no productivo:

1. abrir DevConsole y confirmar Viewer;
2. autenticar Developer;
3. detectar el workspace y comparar el inventario de servicios esperado;
4. levantar un backend Django y un frontend;
5. cerrar/reabrir visor y comprobar que el proceso continúa vivo;
6. abrir visor Tilix;
7. cambiar LOCAL/INTRANET y comprobar que sólo cambió `.env`, no código fuente;
8. ejecutar un build local V1.1 y comprobar que la rama activa/working tree no cambió;
9. ejecutar K8s preflight + preview/diff en namespace no productivo;
10. autenticar Administrator y confirmar que operaciones sensibles están disponibles;
11. logout y confirmar regreso a Viewer.

## Veredicto

### Implementación de fases 0–8

**GO**, sujeto a que el último workflow bloqueante de la rama permanezca verde.

### Merge a `main`

**NO-GO temporal** hasta completar la aceptación de host anterior. Esto no representa una fase incompleta: representa el último control necesario para cumplir la misión de “no perder capacidades” en infraestructura que el runner de GitHub no posee.
