# DevConsole V1.1 — Segunda auditoría completa

Fecha: 2026-10-19

## Objetivo

Revisar nuevamente la implementación completa sin asumir que un CI verde equivale a una migración terminada. La auditoría contrastó `refactor/v1.1-foundation` contra `main`, la conexión real de los adapters, compatibilidad HTTP V1, seguridad de roles, transacciones Git, terminales, instalación de dependencias, build/cancelación, K8s, frontend y QA.

## Hallazgos corregidos

1. El resultado del visor alteraba el `message` histórico de `/api/tilix/launch_selected`; ahora es metadata aditiva.
2. `/api/environment/switch` podía responder éxito aunque la transacción estuviera abortada/rolled back; ahora sólo `committed` es éxito.
3. El rollback multi-repo no restauraba una ref destino avanzada por `pull --ff-only`; ahora restaura/elimina refs locales creadas por la transacción.
4. El instalador no activaba por sí mismo las dependencias V1.1; ahora usa venv aislado best-effort con fallback offline y reintentos/timeout acotados.
5. `pins.verify()` conservaba internamente el PIN histórico; fue eliminado.
6. Una cancelación de build podía esperar indefinidamente a que stdout emitiera una línea; ahora la cancelación es independiente del reader y termina el grupo de procesos.
7. La persistencia de jobs de build se endureció con permisos restrictivos y límites en disco/memoria.
8. Playwright ahora verifica límites Viewer→Developer y Developer→Administrator sin ejecutar acciones destructivas.

## Corrección del alcance declarado

La primera evaluación llamó “GO” a todas las fases 0–8. Esta auditoría corrige ese lenguaje:

- seguridad/compatibilidad/runtime: GO;
- ProjectDetector/config tipada/build seguro: GO aditivo;
- terminal backend: GO, adopción visual parcial;
- frontend modular: PARCIAL, porque `dashboard.js` y handlers inline siguen siendo el flujo principal;
- merge a `main`: NO-GO hasta smoke del workstation real.

## Evidencia reproducible

El gate bloqueante contiene tests específicos para:

- contrato V1 del launcher terminal;
- estado HTTP de transacciones de entorno;
- restauración/eliminación de refs Git en rollback;
- rechazo del PIN histórico incorporado;
- cancelación de procesos silenciosos de build;
- fronteras de roles en Chromium real.

La ejecución de CI correspondiente al código re-auditado aprobó los jobs bloqueantes de Python 3.11, Python 3.12, `compileall`, Ruff crítico, regresión portable, aceptación read-only, ES Modules, shell syntax y Playwright. La suite heredada completa permanece como diagnóstico no bloqueante.

La suite heredada no se oculta: si un fallo revela una regresión contractual real, ese caso se extrae y se convierte en test bloqueante V1.1.

## Veredicto

La segunda auditoría mejora materialmente la seguridad y la veracidad del estado del proyecto. No se detectó una pérdida deliberada de capacidad V1. Sin embargo, no se considera terminada la modernización visual ni la migración de todos los workflows legacy hacia las rutas V1.1. La PR debe permanecer Draft hasta aceptación local y decisión de alcance sobre esa migración progresiva.
