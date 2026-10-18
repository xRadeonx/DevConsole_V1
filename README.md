# SISPER DevConsole

Orquestador de entorno local, consolas Tilix, Kubernetes, CI/CD y gestión de variables multi-entorno para microservicios SISPER.

## Prerrequisitos

Linux (Fedora, RHEL, Ubuntu o Debian) con sesión gráfica (GNOME/KDE).

Paquetes base:
```bash
# Fedora / RHEL
sudo dnf install -y python3 tilix git

# Ubuntu / Debian
sudo apt install -y python3 tilix git
```

Opcional según uso:
* `kubectl`: acceso a pods y logs del cluster K8s.
* `podman` o `docker`: contenedores locales (KeyDB, OnlyOffice, Keycloak local).

## Estructura esperada de carpetas

DevConsole espera carpetas `backend/` y `frontend/` en misma raíz:

```text
Develop/
├── dashboard.py
├── devconsole/
├── static/
├── config/
├── backend/                  # Repositorios microservicios Django
│   ├── ms_sisper_sesion/
│   └── ...
└── frontend/                 # Repositorios microfrontends
    ├── mf_sisper_sesion/
    └── ...
```

## Instalación rápida (1 paso)

Ejecutar script instalador en raíz de proyecto:

```bash
bash install_devconsole.sh
```

El script realiza:
1. Verifica dependencias del sistema (`python3`, `git`, `tilix`).
2. Configura e inicia servicio systemd de usuario (`sisper-dashboard.service`).
3. Registra acceso directo en menú de aplicaciones ("SISPER DevConsole").
4. Habilita autoarranque al iniciar sesión gráfica.

## Uso

* **Web UI:** Abrir `http://localhost:9099`
* **Menú del sistema:** Buscar `SISPER DevConsole` en lanzador de aplicaciones.
* **Estado de servicio:**
  ```bash
  systemctl --user status sisper-dashboard.service
  ```
* **Reiniciar servicio:**
  ```bash
  systemctl --user restart sisper-dashboard.service
  ```
* **Ver logs:**
  ```bash
  journalctl --user -u sisper-dashboard.service -f
  ```
