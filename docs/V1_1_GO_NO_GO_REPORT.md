# DevConsole V1.1 — Reporte GO / NO-GO (segunda auditoría)

## Alcance

Este reporte sustituye el veredicto optimista inicial y separa cuatro estados distintos:

1. **Core V1.1 conectado:** seguridad, compatibilidad HTTP, roles, runtime y adapters efectivamente usados al arrancar.
2. **Capacidad aditiva:** función nueva disponible y probada, pero el flujo V1 visible sigue coexistiendo.
3. **Migración completa:** flujo histórico reemplazado/extraído sin perder contrato.
4. **Aceptación de host:** evidencia que sólo puede producir el workstation real SISPER/Fedora.

`main` permanece sin modificaciones. Todo continúa concentrado en la PR Draft #2.

## Baseline y evolución del diagnóstico

La primera ejecución reproducible del V1 mostró:

- 524 tests aprobados;
- 54 fallos;
- 48 skipped;
- 1 deselected;
- 321 subtests aprobados.

Tras las fases y la segunda auditoría, el diagnóstico limpio observado pasó a **554 tests aprobados, 50 fallos, 48 skipped, 1 deselected y 326 subtests aprobados**. Los fallos restantes se concentran principalmente en fixtures dependientes del workspace físico, expectativas legacy ya reemplazadas de forma deliberada, layouts Tilix no versionados y pruebas tmux sensibles al host.

El job diagnóstico sigue visible y no bloquea por sí solo el release; cualquier fallo que revele una regresión contractual real se extrae y convierte en test bloqueante V1.1.

## Hallazgos reales de la segunda auditoría y correcciones

La segunda revisión encontró problemas que el primer gate no detectaba:

- **Contrato terminal:** el visor se concatenaba al `message` histórico de `/api/tilix/launch_selected`. Corregido mediante facade verificado: `message` conserva V1 y `viewer` es metadata aditiva.
- **Resultado transaccional:** `/api/environment/switch` podía devolver `success=true` aunque la transacción estuviera abortada o rolled back. Ahora sólo `committed` es éxito y los demás estados responden 409.
- **Rollback Git incompleto:** se restauraba HEAD pero una rama destino podía quedar adelantada. Ahora se restaura la ref previa o se elimina la rama local creada por la transacción.
- **Dependencias V1.1 no garantizadas por el instalador:** ahora se intenta crear un venv aislado e instalar `requirements-v11.txt`; en modo offline se conserva fallback compatible.
- **PIN histórico residual:** `pins.verify()` todavía contenía un fallback incorporado aunque la capa superior lo bloqueara. Fue eliminado completamente.
- **Cancelación de build:** podía quedar esperando stdout sin newline. Ahora se monitoriza fuera del reader, se termina el grupo de procesos y se escala si no sale.
- **Persistencia de builds:** ahora se limita también en memoria y el estado se escribe con permisos restrictivos.

Todas estas correcciones tienen tests dedicados en el gate portable o Playwright.

## Gate bloqueante actual

Se exige:

- Python 3.11 ✅
- Python 3.12 ✅
- `compileall` ✅
- Ruff crítico ✅
- regresión V1 portable ✅
- tests V1.1 + segunda auditoría ✅
- shell syntax ✅
- sintaxis ES Modules ✅
- Playwright Chromium ✅
- Viewer por defecto ✅
- Viewer bloqueado ante mutaciones Developer ✅
- Developer con credencial real ✅
- Developer bloqueado ante operaciones Administrator ✅
- logout → Viewer ✅
- Administrator con credencial real ✅
- aceptación read-only ✅

## Estado funcional por área

| Área | Estado | Observación |
|---|---|---|
| Seguridad Viewer/Developer/Admin | **GO** | Aplicada en facade real y probada en navegador. |
| Compatibilidad HTTP V1 | **GO** | Handler legacy permanece como rollback; facade verificado conserva contratos intervenidos. |
| Runtime/procesos | **GO** | psutil con fallback procfs y ownership separado. |
| Configuración tipada | **GO aditivo** | Diagnóstico/validación Pydantic, sin romper loader V1. |
| YAML/K8s | **GO** | round-trip + preflight/diff/apply/rollback y fallback V1. |
| ProjectDetector | **GO aditivo** | Disponible por API; la UI legacy aún usa discovery histórico. |
| tmux/Tilix | **GO backend** | Ownership y fallback existen; Tilix no se elimina. |
| xterm addons | **GO como capacidad** | Disponibles vía módulos V1.1; no todas las vistas V1 los consumen aún. |
| Frontend modular | **PARCIAL** | `app-v11.js` se inyecta y funciona, pero `dashboard.js`/HTML inline siguen dominando la UI. |
| Build seguro/worktree | **GO aditivo** | API V1.1 nueva; la ruta legacy sigue por compatibilidad. |
| Deploy K8s resiliente | **GO aditivo** | API segura nueva; acciones V1 continúan disponibles bajo gate Admin. |

## Capacidades V1 conservadas

Siguen existiendo selección de workspace, descubrimiento histórico, servicios/auxiliares, Tilix, tmux, consola integrada, Git, `.env`, LOCAL/INTRANET, infraestructura local, build/push legacy, manifiestos K8s, deploy/restart/rollout, telemetría Admin, temas y utilidades SISPER.

No se considera “pérdida de capacidad” el retiro de comportamientos inseguros implícitos como matar por puerto, borrar `index.lock`, aceptar un PIN incorporado, desactivar TLS por defecto o parchear código fuente automáticamente al cambiar ambiente.

## Lo que NO está terminado todavía

La segunda auditoría obliga a dejar explícito que **V1.1 no ha completado una migración visual total**:

- `static/index.html` conserva una gran cantidad de handlers inline;
- `static/js/dashboard.js` sigue siendo el entrypoint funcional principal;
- los ES Modules V1.1 son hoy una superficie de extensión, no una extracción completa del monolito;
- ProjectDetector y BuildCoordinator seguro existen por rutas V1.1, pero la UI histórica no ha migrado todos sus workflows hacia ellos;
- los addons xterm están disponibles, pero no todas las experiencias de consola V1 están construidas sobre ellos.

Esto no reduce funciones actuales, pero impide afirmar que la modernización de UX/frontend está “100% terminada”.

## Riesgos que sólo puede cerrar el workstation real

GitHub Actions no puede demostrar:

- inventario exacto de repositorios SISPER reales;
- arranque Django/React/Celery con sus entornos;
- persistencia tmux y attach Tilix en Fedora;
- build de imágenes institucionales con Podman/Docker;
- registry privado;
- context/namespace K8s institucional;
- CA interna Keycloak;
- manifests/secretos privados.

## Procedimiento final de aceptación

```bash
git checkout refactor/v1.1-foundation
./scripts/v11_acceptance.sh
./scripts/v11_acceptance.sh --strict
```

Después, en entorno no productivo:

1. comparar inventario real de servicios;
2. levantar backend, frontend y auxiliar;
3. cerrar/reabrir visor y comprobar continuidad del proceso;
4. abrir Tilix;
5. probar LOCAL/INTRANET y confirmar que no cambia código fuente;
6. ejecutar build V1.1 en worktree y verificar que no cambia la rama activa;
7. comprobar cancelación de build;
8. ejecutar K8s preflight + diff;
9. validar Viewer/Developer/Admin con claves de producto reales;
10. logout y retorno a Viewer.

## Veredicto corregido

### Core de seguridad y compatibilidad V1.1

**GO.**

### Capacidades backend nuevas

**GO aditivo.** Están implementadas y probadas, pero conviven con rutas V1 por diseño de no-regresión.

### Modernización integral de UI/UX y migración de todos los flujos legacy

**PARCIAL / NO-GO para declararla terminada.**

### Merge a `main`

**NO-GO temporal.** Requiere aceptación del host real y una decisión explícita sobre cuánto de la UI legacy debe migrarse antes de considerar V1.1 una modernización completa en lugar de una base segura/evolutiva.
