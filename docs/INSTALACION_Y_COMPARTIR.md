# Compartir e instalar el SISPER DevConsole

Guía para que **otro usuario** ponga en marcha el panel en su máquina a partir de
este repositorio.  Escrita desde el estado real verificado (16-oct-2026).

---

## 0. Lo primero: qué se comparte (importante)

El panel está **en uso diario en esta máquina** y hay cambios que viven en el
árbol de trabajo.  Comprobado: **14 ficheros están modificados sin commitear** y
son **de ejecución** (`devconsole/config.py`, `devconsole/server.py`,
`devconsole/services/{build,env,git,infra,k8s,telemetry}_service.py`,
`devconsole/services/terminal/{base,live_broker}.py`, …).  Un `git clone` normal
**no los lleva**: el otro usuario recibiría una versión más vieja del panel.

Antes de compartir:

```bash
cd /home/proteo/Documentos/Develop
git status                      # ver qué falta
git add -A && git commit -m "estado funcional del panel"   # o exporta el árbol
git push                        # origin = github.com/xRadeonx/devconsole
```

Alternativa sin publicar nada: `git bundle create devconsole.bundle --all` o un
`tar` del directorio **excluyendo** virtualenvs, `node_modules`, `.git` (111 MB) y
las capturas.

---

## 1. Requisitos en la máquina destino

| Componente | Para qué | Verificado aquí |
|---|---|---|
| **Python 3.11+** | el panel (sólo biblioteca estándar) | `/usr/bin/python3` (3.14.8) |
| **pipenv** | entornos de los microservicios (22 `Pipfile`) | `~/.local/bin/pipenv` |
| **Node + npm** | 10 microfrontends (`package.json`) | `/usr/bin/node` |
| **tmux** | consolas gestionadas (backend activo) | `/usr/bin/tmux` |
| **Tilix** | ventana con las consolas (visor) | `/usr/bin/tilix` |
| **podman** (o docker) | keydb, onlyoffice, keycloak | `/usr/bin/podman` |
| **kubectl** | pestaña Kubernetes y despliegues | `/usr/local/sbin/kubectl` |
| **git** | pestañas Workspace / Git | `/usr/bin/git` |

El panel **no necesita `pip install`**: sólo usa la biblioteca estándar
(`http.server`, `json`, `subprocess`…).  Lo que necesita dependencias son los
**servicios**: cada uno con su `Pipfile` (pipenv) y cada frontend con `npm i`.

Sesión gráfica obligatoria si se quieren ventanas de Tilix: la unidad de systemd
recibe `DISPLAY`, `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR` y
`DBUS_SESSION_BUS_ADDRESS`.

---

## 2. Configuración específica de cada máquina

| Qué | Dónde | Cómo se ajusta |
|---|---|---|
| **Carpeta raíz de proyectos** | `config/settings.json` → `base_dir` | **Desde la propia interfaz**: botón de la carpeta en la barra superior (`openRootFolderModal`).  En esta máquina: `/home/proteo/Documentos/Develop`.  Es el **único** valor con ruta absoluta rastreada en `config/`. |
| **PIN de entrada** | variable `SISPER_ADMIN_PIN` | Cada usuario pone el suyo.  Es el PIN de Administrador **y** de Desarrollador. |
| **Puerto / interfaz** | `SISPER_PORT` (9099) y `SISPER_HOST` (127.0.0.1) | Por defecto **sólo loopback**.  Exponer en LAN exige `SISPER_HOST` explícito a propósito. |
| **Backend de terminal** | `SISPER_TERMINAL_BACKEND=tmux` | Sin esto el panel intenta el lanzador *legacy* de Tilix. |
| **Carpetas de manifiestos K8s** | `config/services.json` → `environments.<env>.k8s_dir` | También se cambia desde el panel (⚙️ Carpeta YAML en Deployments). |
| **`.env` de cada servicio** | `backend/<servicio>/.env` | **No se comparten** (están fuera del repo).  Se crean con `cp .env.example .env`.  El panel los **comprueba antes de lanzar** (🔍 Comprobar) y los diagnostica (🩺 ¿Por qué no arranca?). |
| **kubeconfig** | `~/.kube/config` del usuario | Lo usa `kubectl` tal cual: cada usuario necesita acceso a **su** clúster. |

### Acceso a red

Las funciones de base de datos y clúster usan la conectividad del puesto:
`localhost`, la subred de microservicios `172.23.22.0/24` y el host de BD
`172.30.23.71`.  Sin esa ruta, las pestañas de Kubernetes/BD muestran error (el
resto del panel funciona igual).  **El panel nunca escribe en la base de datos**:
sólo consulta.

---

## 2.b Claves de acceso (PIN) — hasheadas, nunca en claro

Hay **un PIN por rol**: `admin` (Administrador / DevOps) y `dev` (Desarrollador).
Soporte/QA no pide PIN porque es de sólo lectura.

```bash
python3 -m devconsole.pins set --role admin     # lo pide dos veces, sin eco
python3 -m devconsole.pins set --role dev
python3 -m devconsole.pins status               # cómo está configurado cada rol
```

**Cómo se guardan** (`devconsole/pins.py`):

| | |
|---|---|
| Algoritmo | **scrypt** con sal aleatoria de 16 bytes por PIN (`n=2^14, r=8, p=1`, 32 bytes derivados) |
| Fichero | `~/.config/sisper-dashboard/secrets.json`, modo **0600**, **fuera del repositorio** |
| En claro | **nunca**: no se escribe, no se registra en el log y no viaja en el repo |
| Comparación | tiempo constante (`hmac.compare_digest`) |
| Fuerza bruta | bloqueo temporal de **30 s** tras **5** fallos seguidos |

Orden de resolución para cada rol: **credencial de systemd** →
**hash (scrypt)** → variable de entorno (`SISPER_ADMIN_PIN` / `SISPER_DEV_PIN`) →
PIN heredado (compatibilidad).  Ojo: en cuanto hay hash, **el PIN por defecto
histórico deja de funcionar** (devuelve 401), que es justo lo que se busca.

### ¿Se pueden «encriptar» para que no las obtengan?

No existe forma de guardar un PIN **reversiblemente cifrado** y seguir
verificándolo en la misma máquina: quien pueda leer el fichero y la clave, lo
descifra.  Lo correcto es **hash** (irreversible) y eso es lo implementado.  Lo
que protege y lo que no:

* ✅ Un repositorio compartido, un volcado de configuración, una captura o un
  log **no revelan el PIN**.
* ✅ Fuerza bruta **en línea** limitada por el bloqueo.
* ⚠️ Quien ya es ese usuario en ese equipo puede intentar adivinarlo en línea o
  sustituir el fichero; a esas alturas controla el equipo igual que controla los
  `.env` y el kubeconfig.

**Opción más fuerte (cifrado real en reposo, atado al equipo):** credenciales de
systemd, que se descifran sólo al arrancar el servicio con la clave del
equipo/TPM — el PIN ni siquiera queda como hash en disco:

```bash
printf '%s' 'TU_PIN_ADMIN' | systemd-creds encrypt --user --name=admin_pin \
    ~/.config/sisper-dashboard/admin_pin.cred -
# en la unidad:  LoadCredentialEncrypted=admin_pin:%h/.config/sisper-dashboard/admin_pin.cred
```

El panel la detecta sola (`$CREDENTIALS_DIRECTORY/admin_pin`) y tiene prioridad
sobre el hash.

### Roles y alcance

| Rol | PIN | Token elevado | Qué puede hacer |
|---|---|---|---|
| **Soporte / QA** | no pide | — | sólo lectura: Kubernetes, Mapa Operativo, Actividad |
| **Desarrollador** | sí (`dev`) | no | lanzar/detener servicios y consolas, Workspace, K8s, Infraestructura |
| **Admin / DevOps** | sí (`admin`) | sí (cookie HttpOnly, 24 h) | todo: despliegues, entornos, Git, mover manifiestos |

## 3. Puesta en marcha

```bash
git clone <repo> ~/devconsole && cd ~/devconsole
python3 dashboard.py          # http://127.0.0.1:9099
```

Primera vez, en el panel:
1. **Carpeta raíz** → apunta a donde estén los repos de servicios.
2. Entra como **Administrador** con tu PIN (`SISPER_ADMIN_PIN`).
3. **🔍 Comprobar** antes de lanzar: dice qué falta (infra, `.env`, entorno de
   pipenv, puertos) con el comando exacto.

### Como servicio de usuario (arranque automático)

Las plantillas están en `deploy/`:

```bash
mkdir -p ~/.config/systemd/user/sisper-dashboard.service.d
sed -e "s|__USUARIO__|$USER|g" -e "s|__RUTA__|$HOME/devconsole|g" \
    deploy/sisper-dashboard.service > ~/.config/systemd/user/sisper-dashboard.service
cp deploy/sisper-dashboard.service.d-override.conf \
   ~/.config/systemd/user/sisper-dashboard.service.d/override.conf
systemctl --user daemon-reload
systemctl --user enable --now sisper-dashboard.service
```

Comprobar: `systemctl --user status sisper-dashboard.service` y abrir
`http://127.0.0.1:9099`.

---

## 4. Qué NO compartir

- `node_modules/` (10 carpetas) y los virtualenvs de pipenv
  (`~/.local/share/virtualenvs/`): se regeneran con `npm i` / `pipenv install`.
- `.env` de los servicios: contienen credenciales.
- `.git` completo si sólo se quiere una copia funcional (111 MB).
- `docs/capturas-*/`: capturas de verificación.

---

## 5. Consumo medido (esta máquina, 64 GB)

Con 28 servicios y 12 frontends en marcha:

| Grupo | Procesos | RAM |
|---|---|---|
| **Panel (servidor Python)** | 1 | **~64 MB** |
| Ventanas/consolas Tilix | 30 | 115 MB |
| `manage.py runserver` | 36 | 2.994 MB |
| **webpack (frontends)** | 12 | **10.696 MB** |
| Firefox | 24 | 7.376 MB |
| VS Code | 33 | 4.724 MB |
| **Total en uso** | — | **38,8 GB de 63,9 GB** (25,2 GB disponibles) |

El panel en sí es marginal (~64 MB y estable): el peso está en los *bundlers* de
los frontends y en las herramientas del puesto.  El `MemoryCurrent` del servicio
systemd (~741 MB) incluye, por cgroup, el servidor tmux y las ventanas de Tilix
que lanza, no sólo el proceso Python.
