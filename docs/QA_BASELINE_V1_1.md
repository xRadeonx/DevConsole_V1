# DevConsole V1.1 — Baseline QA

Fecha de baseline: 2026-10-18/19  
Rama: `feature/v1.1-modernization`

## Objetivo

Separar dos conceptos que no deben confundirse durante la modernización:

1. **Regresión V1.1**: un cambio nuevo rompe un contrato que estaba estable.
2. **Deuda legacy**: una prueba existente ya depende de archivos locales, estado del host o contratos que dejaron de corresponder al código actual.

Un GO de V1.1 exige que el gate reproducible permanezca verde. La suite legacy se mantiene visible y se irá saneando; nunca se oculta ni se borra para obtener un resultado artificialmente verde.

## Primera ejecución en GitHub Actions

La primera ejecución completa mostró:

- compilación Python: **OK**;
- suite seleccionada originalmente: **22 fallos + 22 errores + 6 skips** sobre 368 pruebas;
- la gran mayoría de las fallas pertenecen a supuestos del entorno local o fixtures faltantes, no a los cambios V1.1;
- el job de dependencias falló porque `pip install .[modernization]` activó autodiscovery de setuptools sobre una aplicación flat-layout (`static`, `config`, `deploy`, `devconsole`). Las dependencias no eran la causa.

## Deuda legacy identificada

### Fixtures/layouts no versionados

Varias pruebas tmux esperan archivos que no existen en un checkout limpio:

- `backend/backend-terminal-auto.json`
- `backend/backend-terminal-2-auto.json`
- `frontend_terminal_auto.json`
- `sisper_all_single_session_auto.json`

Estas pruebas deberán migrarse a fixtures autocontenidos o generar los layouts durante el test.

### Runtime identity dependiente del host

Escenarios sintéticos de `test_runtime_identity.py` esperan PID/puertos que no se materializan correctamente en el runner Linux limpio. La prueba debe inyectar completamente el inspector/tabla de sockets en vez de depender indirectamente de `/proc` real.

### Tmux real en CI

Parte de `RealTmuxFixtureTest` crea una sesión cuyo comando termina antes de la comprobación y el servidor tmux reporta que la sesión desapareció. Los tests de integración tmux deben usar un proceso fixture de larga duración y aislamiento explícito de socket.

### Mocks desactualizados

`FakeBackend` utilizado por pruebas de endpoints no contiene métodos añadidos al contrato real (`attach_viewers`, `managed_sessions`). Esto indica deuda de tests, no necesariamente fallo del backend productivo.

### Contrato de acciones

La implementación utiliza `stop-single`, pero el vocabulario esperado por una prueba no lo incluye. Debe reconciliarse el contrato de acciones y mantener una única fuente de verdad.

### Installer

`install_devconsole.sh` contiene un `fuser -k` heredado aunque una prueba de seguridad declara que ese script no debe tener primitivas destructivas. La prueba detectó correctamente una inconsistencia real del baseline. Se corregirá en la fase Runtime/Safety y no se normalizará como comportamiento aceptable.

## Gates a partir de V1.1

### Bloqueante

- `compileall`;
- `test_security_boundary` (baseline estable y portable);
- contratos nuevos V1.1;
- pruebas de cada nueva librería/adaptador antes de activar su integración.

### Observacional temporal

- suite unittest completa.

El job observacional usa `continue-on-error: true`, pero permanece ejecutándose en cada push/PR para medir cómo disminuye la deuda. La meta antes de declarar V1.1 terminada es convertir progresivamente los grupos saneados en gates bloqueantes.

## Regla de promoción

Una funcionalidad experimental sólo pasa de adaptador/shadow a ruta principal si:

1. tiene prueba unitaria reproducible;
2. preserva el contrato de entrada/salida V1 o documenta explícitamente una extensión compatible;
3. falla cerrado y permite fallback;
4. el gate bloqueante permanece verde;
5. no incrementa el inventario de fallos legacy atribuibles al cambio.
