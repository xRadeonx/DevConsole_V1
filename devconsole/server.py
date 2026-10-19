import http
# devconsole/server.py
import http.server
import ipaddress
import os
import socket
import sys
import threading
import time

from devconsole import local_trust
from devconsole.config import HOST, HOST_IS_LOOPBACK, PORT, BASE_DIR

if os.environ.get("SISPER_V11_HANDLER", "1").strip() == "0":
    from devconsole.api.handlers import DevConsoleHandler
else:
    from devconsole.api.v11_handler import DevConsoleHandler

from devconsole.services.env_service import env_file_watcher_loop


def _make_server_class(host: str):
    bare = host[1:-1] if host.startswith("[") and host.endswith("]") else host
    try:
        version = ipaddress.ip_address(bare).version
    except ValueError:
        version = 4

    class _Server(http.server.ThreadingHTTPServer):
        daemon_threads = True

    if version == 6:
        _Server.address_family = socket.AF_INET6
    return _Server


def _log_bind_notice() -> None:
    print(f"[*] SISPER DevConsole activo en: http://{HOST}:{PORT}")
    print(f"[*] Directorio raíz: {BASE_DIR}")
    print(
        "[*] HTTP handler: "
        + ("V1 legacy (rollback)" if os.environ.get("SISPER_V11_HANDLER", "1").strip() == "0" else "V1.1 compatibility facade")
    )
    if HOST_IS_LOOPBACK:
        print("[*] Modo de escucha: LOOPBACK (solo esta máquina).")
    else:
        print("[!] Modo de escucha: LAN/EXPUESTO "
              f"(SISPER_HOST={HOST}). El orquestador queda accesible desde la red.")
        print("[!] DevConsole puede ejecutar comandos, reescribir .env y operar kubectl. "
              "Habilita este modo solo en redes de confianza.")


def _publish_local_token_if_required() -> None:
    if not local_trust.token_required():
        print("[!] Confianza local deshabilitada explícitamente (SISPER_LOCAL_TOKEN_REQUIRED=0).")
        return
    path = local_trust.publish_token()
    local_trust.register_cleanup()
    if path is None:
        print("[!] SISPER_LOCAL_TOKEN_REQUIRED=1 pero no se pudo publicar el token "
              "de confianza local; las peticiones mutadoras serán rechazadas.")
    else:
        print(f"[*] Token de confianza local publicado en: {path} (modo 0600)")


PROBE_REFRESH_SECONDS = 8.0


def _start_probe_refresher() -> None:
    def _run() -> None:
        from devconsole.config import SERVICES_BACKEND, SERVICES_FRONTEND, get_service_repo_dir
        from devconsole.services.git_service import get_git_info
        from devconsole.services.infra_service import get_infra_info
        from devconsole.services.env_service import get_all_environments_status

        while True:
            try:
                get_all_environments_status.refresh()
                get_infra_info.refresh()
                for s in SERVICES_BACKEND + SERVICES_FRONTEND:
                    get_git_info.refresh(get_service_repo_dir(s["name"]))
            except Exception as exc:
                print(f"[!] Refresco de sondeos omitido: {exc}")
            time.sleep(PROBE_REFRESH_SECONDS)

    threading.Thread(target=_run, name="probe-refresher", daemon=True).start()


def main():
    os.environ.setdefault("SISPER_LOCAL_TOKEN_REQUIRED", "1")

    try:
        from devconsole.services.git_safety import install_checkout_guard
        install_checkout_guard()
    except Exception as exc:
        print(f"[!] No se pudo instalar el guard de Git: {exc}", file=sys.stderr)

    try:
        from devconsole.services.k8s_compat import install_k8s_compatibility_adapters
        install_k8s_compatibility_adapters()
    except Exception as exc:
        print(f"[!] Adapter YAML estructurado omitido; se conserva fallback V1: {exc}", file=sys.stderr)

    # Prefer safe tmux process ownership when the host provides it, but never
    # remove Tilix: it remains the external viewer and the fallback when tmux is
    # unavailable or explicitly selected by the operator.
    try:
        from devconsole.services.terminal.hardening import activate_safe_terminal_runtime
        terminal_policy = activate_safe_terminal_runtime(BASE_DIR)
        print(
            "[*] Terminal runtime: "
            f"{terminal_policy['selected']} "
            f"(safe_wrapper={terminal_policy['safe_wrapper']}, "
            f"tilix_viewer={terminal_policy['tilix_viewer_available']})"
        )
    except Exception as exc:
        print(f"[!] Hardening de terminal omitido; se conserva backend configurado: {exc}", file=sys.stderr)

    _log_bind_notice()
    try:
        from devconsole.startup import print_startup_diagnostics
        print_startup_diagnostics(BASE_DIR)
    except Exception as exc:
        print(f"[!] Diagnóstico V1.1 omitido: {exc}")
    _publish_local_token_if_required()

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
