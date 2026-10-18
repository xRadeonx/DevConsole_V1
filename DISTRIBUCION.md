# Copia limpia para distribuir — SISPER DevConsole

Generada el 16-oct-2026 desde el árbol de trabajo del autor (incluye los cambios
de ejecución que aún no estaban commiteados, que son imprescindibles).

## Qué trae
`dashboard.py` · `devconsole/` · `static/` · `config/` · `scripts/` · `tests/` ·
`deploy/` · `install_devconsole.sh` · `switch_env.sh` · `tilix_runner.sh` ·
`start_tilix.sh` · `README.md` · `docs/` (guía de instalación y traspaso).

## Qué NO trae (a propósito)
- Los proyectos gestionados: `backend/`, `frontend/`, `desktop/` (16 GB + 6,4 GB + 375 MB).
- Historial git (`.git`, 114 MB), `node_modules`, virtualenvs, `dumps_*`, `logs/`,
  capturas de verificación, ficheros personales.
- `config/settings.json` (ruta de la máquina del autor): el panel arranca usando
  **su propio directorio** y la carpeta de trabajo se cambia desde la interfaz.
- Credenciales: las claves de base de datos de `switch_env.sh` quedan como
  `CAMBIAR_ESTA_CLAVE`. **Rellénalas con las tuyas antes de usarlo.**

## Puesta en marcha
1. Requisitos: Python 3.11+, tmux, Tilix, podman/docker, git, kubectl, pipenv, node.
2. `python3 dashboard.py` → http://127.0.0.1:9099
3. En el panel: botón de carpeta → apunta a tu carpeta de proyectos; define tu PIN
   (`SISPER_ADMIN_PIN`) y entra como Administrador.
4. `install_devconsole.sh` deja el servicio de usuario y el lanzador de escritorio.
   Guía detallada en `docs/INSTALACION_Y_COMPARTIR.md`.

## Aviso de seguridad
`switch_env.sh` del repositorio original contenía credenciales de BD en claro y el
remoto es GitHub: **rota esas claves** y sácalas del repositorio (usa variables de
entorno o un fichero fuera del repo). En esta copia están neutralizadas.

## Paso obligatorio antes de arrancar

La copia **no** incluye `config/secrets.json` (contiene credenciales reales del
autor).  Créalo con la plantilla y rellena tus valores:

```bash
cp config/secrets.example.json config/secrets.json
```

El panel avisa en el arranque qué claves faltan (BD de bitácora/contratos/
destinaciones, `onlyoffice_jwt_secret`, `client_secret` de Keycloak).

## Nota sobre `tests/`

Los tests son los del repositorio.  Tres de ellos (`test_api_readonly.py`,
`test_frontend_identity.py` y el fixture `golden_discovery.json`) llevan escrita la
ruta del autor (`/home/proteo/...`), así que en otra máquina fallan hasta
regenerar el fixture; y el conjunto necesita `config/secrets.json`.  Para ejecutar
la app no hacen falta.

## Instalación y desinstalación

- `./install_devconsole.sh` — crea el servicio de usuario y el lanzador.  Elige un
  **puerto libre** desde 9099 (varias cuentas en el mismo PC no chocan) y lo deja
  configurado en la unidad; avisa si el puerto pedido está ocupado.  La unidad usa
  `Restart=on-failure` con `StartLimitBurst=4`: si el panel no arranca, se detiene
  en vez de reiniciarse en bucle (eso provocaba avisos continuos de «Unit recovered»).
  Puerto a mano: `SISPER_PORT=9100 ./install_devconsole.sh`
- `./uninstall_devconsole.sh` — detiene, deshabilita y elimina el servicio, sus
  overrides y el acceso directo.  Con `--purge` borra además esta carpeta y el PIN
  guardado (`~/.config/sisper-dashboard`).  Añade `--yes` para no preguntar.

## El catálogo se puebla con TU carpeta

`config/services.json` viaja **vacío** (a propósito).  Al elegir la carpeta de
proyectos en el panel (botón de carpeta de la barra superior, que guarda la
selección en `config/settings.json`), el panel **descubre** lo que hay en
`<carpeta>/backend` y `<carpeta>/frontend` y arma el catálogo solo:

- backend: directorios `ms_*` o con `manage.py`; el puerto sale del `.env`
  (`PORT=` / `DAPHNE_PORT=`) y, si no está, por convención (8020, 8021…).
- frontend: directorios `mf_*` con `package.json`; puerto por convención (3012, 3013…).

No queda nada de otro entorno: lo que no exista en tu carpeta no aparece.

## Kubernetes también neutro

`config/services.json` viaja **sin** carpetas de manifiestos (`k8s_dir` vacío) y
`config/panel.json` es el de ejemplo (registry y nombre de proyecto genéricos).
Las pestañas de **Deployments** y el explorador de **Sitio** no muestran nada
hasta que se elija la carpeta que contiene los manifiestos por entorno:

- Deployments → **⚙️ Carpeta YAML** → explorador → «✔ usar ésta».
- La carpeta debe tener `.yaml`/`.yml` en su nivel; si el catálogo ya tiene
  servicios, además debe contener alguno de sus manifiestos.

## Puerto y reinstalación (importante)

- El panel usa **siempre 9099** (el mismo para todos); `SISPER_PORT=otro` sólo si
  de verdad hace falta.
- `install_devconsole.sh` **libera el puerto antes de instalar**: para la unidad
  previa del mismo usuario, mata lo que quede escuchando ahí (sólo procesos del
  propio usuario) y espera a que quede libre.  Si lo ocupa otro usuario/proceso,
  aborta y lo muestra: no cambia de puerto por su cuenta.
- `uninstall_devconsole.sh` detiene y deshabilita el servicio, elimina la unidad y
  el lanzador, y **mata lo que siga en el 9099** para dar paso a una instalación
  limpia.
- Las rutas de la unidad van **entre comillas**: la carpeta puede contener
  espacios (`.../21.- Desarrollo Interno/04.- Otros/services/...`) y sin comillas
  systemd partía el comando — el servicio fallaba con `status=2/INVALIDARGUMENT`.

## ¿Está vacía la versión? (sin abrir el panel)

```bash
cd <carpeta-del-panel>
python3 -c "import json;d=json.load(open('config/services.json'));\
print('backends:',len(d['services_backend']),'frontends:',len(d['services_frontend']),\
'k8s_dir:',[e.get('k8s_dir') for e in d['environments'].values()])"
```

Debe imprimir `backends: 0 frontends: 0 k8s_dir: ['', '', '']`.  Y el catálogo se
puebla al elegir la carpeta en la interfaz (o `python3 dashboard.py` a mano para
probarlo sin instalar el servicio).

## Nota técnica de la unidad

`ExecStart` lleva **entrecomillada** la ruta del script (la carpeta puede tener
espacios) y **no** se usa `WorkingDirectory=`: ese ajuste no admite comillas y
systemd rechazaba la unidad («bad unit file setting»).  No hace falta: el panel
localiza sus ficheros por la ruta de `dashboard.py` y `BASE_DIR` sale de
`config/settings.json` (o del propio directorio), así que funciona desde
cualquier directorio de trabajo.
