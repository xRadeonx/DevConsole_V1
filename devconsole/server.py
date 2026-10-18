import http
# devconsole/server.py
import http.server
import ipaddress
import socket
import sys
import threading
import time

from devconsole import local_trust
from devconsole.config import HOST, HOST_IS_LOOPBACK, PORT, BASE_DIR
from devconsole.api.handlers import DevConsoleHandler
from devconsole.services.env_service import env_file_watcher_loop


def _make_server_class(host: str):
    """Return an ``HTTPServer`` subclass with the address family the host needs.

    ``HTTPServer.address_family`` is ``AF_INET``, so binding an IPv6 literal
    such as ``::1`` would raise.  Selecting the family here keeps
    ``SISPER_HOST=::1`` usable instead of crashing at startup.
    """
    bare = host[1:-1] if host.startswith("[") and host.endswith("]") else host
    try:
        version = ipaddress.ip_address(bare).version
    except ValueError:
        version = 4  # a host name such as "localhost"

    class _Server(http.server.ThreadingHTTPServer):
        daemon_threads = True

    if version == 6:
        _Server.address_family = socket.AF_INET6
    return _Server


def _log_bind_notice() -> None:
    print(f"[*] SISPER DevConsole activo en: http://{HOST}:{PORT}")
    print(f"[*] Directorio raíz: {BASE_DIR}")
    if HOST_IS_LOOPBACK:
        print("[*] Modo de escucha: LOOPBACK (solo esta máquina).")
    else:
        print("[!] Modo de escucha: LAN/EXPUESTO "
              f"(SISPER_HOST={HOST}). El orquestador queda accesible desde la red.")
        print("[!] DevConsole puede ejecutar comandos, reescribir .env y operar kubectl. "
              "Habilita este modo solo en redes de confianza.")


def _publish_local_token_if_required() -> None:
    """Publish the ephemeral local-trust token before serving, when enabled."""
    if not local_trust.token_required():
        return
    path = local_trust.publish_token()
    local_trust.register_cleanup()
    if path is None:
        print("[!] SISPER_LOCAL_TOKEN_REQUIRED=1 pero no se pudo publicar el token "
              "de confianza local; las peticiones mutadoras serán rechazadas.")
    else:
        # The path is safe to log; the token value never is.
        print(f"[*] Token de confianza local publicado en: {path} (modo 0600)")


#: Cada cuánto se refrescan en segundo plano los sondeos cacheados.  Debe ser
#: menor que el TTL más corto de las funciones envueltas, para que una petición
#: de la interfaz casi nunca encuentre la caché vencida.
PROBE_REFRESH_SECONDS = 8.0


def _start_probe_refresher() -> None:
    """Mantiene tibia, en un hilo demonio, la caché de sondeos de ``/api/status``.

    ``/api/status`` agrega git, infraestructura y estado por entorno; en frío
    eso cuesta del orden de un segundo, y con sólo un TTL ese coste recaería
    periódicamente sobre la petición de algún usuario.  Refrescarlo en segundo
    plano mueve ese trabajo fuera del camino de la petición: la interfaz lee
    siempre de caché tibia.
    """

    def _run() -> None:
        from devconsole.config import (
            SERVICES_BACKEND,
            SERVICES_FRONTEND,
            get_service_repo_dir,
        )
        from devconsole.services.git_service import get_git_info
        from devconsole.services.infra_service import get_infra_info
        from devconsole.services.env_service import get_all_environments_status

        while True:
            try:
                # Se republica con refresh() antes de que expire la ventana, de
                # modo que ninguna petición de la interfaz encuentre la caché
                # vencida.  get_all_environments_status() recorre los servicios
                # y de paso refresca get_git_info() para cada repositorio.
                get_all_environments_status.refresh()
                get_infra_info.refresh()
                # /api/status consulta get_git_info() directamente por servicio,
                # además de a través del estado de entornos.  Sin republicarlo
                # aquí, sus entradas expiran entre dos pasadas del refrescador y
                # la petición acaba pagando el recálculo completo.
                for s in SERVICES_BACKEND + SERVICES_FRONTEND:
                    get_git_info.refresh(get_service_repo_dir(s["name"]))
            except Exception as exc:  # defensivo: nunca debe tumbar el daemon
                print(f"[!] Refresco de sondeos omitido: {exc}")
            time.sleep(PROBE_REFRESH_SECONDS)

    threading.Thread(target=_run, name="probe-refresher", daemon=True).start()


def main():
    _log_bind_notice()
    _publish_local_token_if_required()

    # Iniciar monitor de archivos .env en segundo plano
    t_env_watcher = threading.Thread(target=env_file_watcher_loop, daemon=True)
    t_env_watcher.start()

    _start_probe_refresher()

    server_class = _make_server_class(HOST)
    try:
        server = server_class((HOST, PORT), DevConsoleHandler)
    except OSError as exc:
        print(f"[!] No se pudo escuchar en {HOST}:{PORT}: {exc}", file=sys.stderr)
        raise
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] DevConsole cerrado.")
    finally:
        server.server_close()
        local_trust.cleanup_token()


if __name__ == "__main__":
    main()
