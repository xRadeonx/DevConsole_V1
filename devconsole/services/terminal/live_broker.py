# devconsole/services/terminal/live_broker.py
"""Phase 6R: Real-time LiveConsoleBroker for multi-service monitoring wall.

Provides sub-second live streaming output from all tmux sessions without
creating PTY workers, interactive sessions, or child processes.
Maintains bounded ring buffers (MAX_LINES=1000) and broadcasts incremental
deltas to UI subscribers (via SSE / EventSource).
"""

from __future__ import annotations

import collections
import hashlib
import json
import logging
import os
import queue
import re
import subprocess
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

import devconsole.config as dcfg
from devconsole.services.terminal.tmux_layout import (
    AUX_TYPES,
    SESSION_PREFIX,
    parse_tmux_session_name,
)

logger = logging.getLogger("devconsole.terminal.live_broker")

DEFAULT_MAX_LINES = 1000
MAX_LINE_CHARS = 500
MAX_BATCH_DELTA_LINES = 60
#: Un delta de re-sincronización (`reset`) puede llevar más cola: recortarlo a 60
#: líneas dejaba la consola visible con muy poco historial de golpe.
MAX_RESET_LINES = 200
POLL_INTERVAL_ACTIVE = 0.25  # 4 Hz con suscriptores (antes 8 Hz: 55% de un núcleo)
#: Un `tmux capture-pane` que se cuelgue no debe bloquear el hilo del broker.
CAPTURE_TIMEOUT_SECONDS = 5.0
#: Cuánto se sigue sondeando después de la última lectura de instantánea o
#: catálogo, para cubrir el caso "SSE caído, la interfaz sondea a mano".
CONSUMER_GRACE_SECONDS = 20.0
POLL_INTERVAL_IDLE = 1.0     # 1s when no subscribers

# Error and standby pattern regexes
RE_STANDBY = re.compile(r"(\[MODO STANDBY\]|Opci[oó]n\s*\[r=reintentar\])", re.IGNORECASE)
RE_ERROR = re.compile(
    r"(Traceback\s*\(most recent call last\)|SyntaxError|ModuleNotFoundError|"
    r"ImportError|OperationalError|FATAL|CRITICAL|django\.core\.exceptions)",
    re.IGNORECASE,
)
RE_STARTING = re.compile(r"(Watching for file changes|compiled successfully|Starting development server)", re.IGNORECASE)


@dataclass
class LiveConsoleItem:
    id: str
    service: str
    name: str
    category: str        # 'backend' | 'frontend' | 'worker' | 'consumer' | 'beat' | 'auxiliary'
    service_type: str    # 'backend' | 'frontend' | 'auxiliary'
    port: Optional[int]
    tmux_session: str
    status: str          # 'RUNNING' | 'STARTING' | 'STANDBY' | 'FAILED' | 'STOPPED'
    pid: Optional[int] = None
    uptime_seconds: Optional[int] = None
    environment: str = "develop"
    branch: Optional[str] = None
    ring_buffer: collections.deque = field(default_factory=lambda: collections.deque(maxlen=DEFAULT_MAX_LINES))
    last_line_count: int = 0
    recent_error: Optional[str] = None
    has_new_error: bool = False
    last_seen_ts: float = 0.0
    #: Instante (epoch) en que el buffer creció por última vez, es decir, la
    #: última línea de salida realmente recibida.  `last_seen_ts` no sirve para
    #: esto: se refresca en cada sondeo aunque el servicio esté en reposo.
    last_line_ts: float = 0.0
    #: Última captura completa del panel.  Cuando la ventana de `capture-pane`
    #: se satura el número de líneas deja de crecer aunque el servicio siga
    #: escribiendo; esta copia permite detectar las líneas nuevas por solape.
    last_capture: list = field(default_factory=list)

    def to_dict(self, include_lines: bool = False) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "service": self.service,
            "name": self.name,
            "category": self.category,
            "service_type": self.service_type,
            "port": self.port,
            "tmux_session": self.tmux_session,
            "status": self.status,
            "pid": self.pid,
            "uptime_seconds": self.uptime_seconds,
            "environment": self.environment,
            "branch": self.branch,
            "line_count": len(self.ring_buffer),
            "recent_error": self.recent_error,
            "has_new_error": self.has_new_error,
            "last_seen_ts": self.last_seen_ts,
            "last_line_ts": self.last_line_ts,
        }
        if include_lines:
            data["lines"] = list(self.ring_buffer)
        return data


class LiveConsoleBroker:
    """Central daemon streaming incremental tmux output to UI subscribers."""

    def __init__(self, max_lines: int = DEFAULT_MAX_LINES):
        self.max_lines = max_lines
        self._lock = threading.RLock()
        self._items: Dict[str, LiveConsoleItem] = {}
        #: Nombres declarados por el catálogo del proyecto.  Sólo éstos pueden
        #: permanecer en la lista estando detenidos; el resto se poda.
        self._seeded: set = set()
        self._subscribers: Dict[str, queue.Queue] = {}
        #: Última vez que alguien pidió instantánea o catálogo (ver _broker_loop).
        self._last_consumer_ts = 0.0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._init_configured_services()

    def _init_configured_services(self) -> None:
        """Seed known services catalog from devconsole config."""
        try:
            cfg = dcfg.load_config()
        except Exception:
            cfg = {}

        backend_cfgs = cfg.get("backends") or dcfg.SERVICES_BACKEND
        frontend_cfgs = cfg.get("frontends") or dcfg.SERVICES_FRONTEND

        for svc in backend_cfgs:
            name = svc.get("name")
            if not name:
                continue
            item = LiveConsoleItem(
                id=name,
                service=name,
                name=name,
                category="backend",
                service_type="backend",
                port=svc.get("port"),
                tmux_session=f"sisper_{name}",
                status="STOPPED",
            )
            self._items[name] = item
            self._seeded.add(name)

        for svc in frontend_cfgs:
            name = svc.get("name")
            if not name:
                continue
            item = LiveConsoleItem(
                id=name,
                service=name,
                name=name,
                category="frontend",
                service_type="frontend",
                port=svc.get("port"),
                tmux_session=f"sisper_{name}",
                status="STOPPED",
            )
            self._items[name] = item
            self._seeded.add(name)

    def start(self) -> None:
        """Start the background broker polling thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._broker_loop, daemon=True, name="LiveConsoleBrokerThread")
            self._thread.start()
            logger.info("LiveConsoleBroker background thread started.")

    def stop(self) -> None:
        """Stop the background broker polling thread."""
        with self._lock:
            self._running = False

    def subscribe(self, subscriber_queue: queue.Queue) -> str:
        """Register a new subscriber queue to receive live stream events."""
        sub_id = hashlib.sha1(f"{time.time()}_{id(subscriber_queue)}".encode()).hexdigest()[:12]
        with self._lock:
            self._subscribers[sub_id] = subscriber_queue
        # Primer sondeo inmediato: si el bucle estaba en reposo (sin nadie
        # escuchando), la instantánea de bienvenida saldría vacía o en STOPPED.
        try:
            self._poll_once()
        except Exception as exc:
            logger.debug(f"Error in initial LiveConsoleBroker poll: {exc}")
        # Push initial snapshot
        snapshot = self.get_snapshot()
        try:
            subscriber_queue.put_nowait({"type": "snapshot", "data": snapshot})
        except queue.Full:
            pass
        return sub_id

    def unsubscribe(self, sub_id: str) -> None:
        """Unregister a subscriber queue."""
        with self._lock:
            self._subscribers.pop(sub_id, None)

    def get_snapshot(self) -> Dict[str, Any]:
        """Return full catalog and latest lines snapshot."""
        self._last_consumer_ts = time.monotonic()
        with self._lock:
            catalog = [item.to_dict(include_lines=True) for item in self._items.values()]
            return {
                "services": catalog,
                "count": len(catalog),
                "timestamp": time.time(),
            }

    def get_catalog(self) -> List[Dict[str, Any]]:
        """Return catalog metadata without lines (lightweight)."""
        self._last_consumer_ts = time.monotonic()
        with self._lock:
            return [item.to_dict(include_lines=False) for item in self._items.values()]

    def _broker_loop(self) -> None:
        """Main background loop: discovers sessions and polls chained output.

        Sin nadie escuchando NO se sondea: con el muro cerrado esta captura
        costaba, medido, entre medio núcleo y un núcleo entero de forma continua
        (un comando tmux encadenado con 'capture-pane -S -1000' por sesión, 3,9
        clientes tmux/s) para mantener al día un estado que nadie lee.  Se
        considera "alguien escuchando" un suscriptor SSE o una lectura reciente
        de instantánea/catálogo (que es el camino del sondeo de respaldo cuando
        el SSE se cae).  Al llegar el primer suscriptor, `subscribe()` fuerza un
        sondeo para que la instantánea de bienvenida ya traiga el estado real.
        """
        while self._running:
            has_subs = len(self._subscribers) > 0
            reciente = (time.monotonic() - self._last_consumer_ts) < CONSUMER_GRACE_SECONDS
            if not (has_subs or reciente):
                time.sleep(POLL_INTERVAL_IDLE)
                continue

            try:
                self._poll_once()
            except Exception as exc:
                logger.debug(f"Error in LiveConsoleBroker poll: {exc}")

            time.sleep(POLL_INTERVAL_ACTIVE)

    #: Tamaños de ancla que se prueban, de mayor a menor.  Un bloque largo es más
    #: fiable, pero el final del panel puede cambiar solo (una línea reescrita en
    #: el sitio, un re-wrap al redimensionar), así que se va acortando el ancla
    #: antes de rendirse.
    ANCHOR_SIZES = (10, 6, 3, 1)
    #: Cuántas líneas del final se descartan al tomar el ancla.  Con 0 el ancla
    #: incluye la última línea; con 1, 2 o 3 se evita anclar en una cola que se
    #: reescribe sola (barras de progreso, el prompt del shell).  Lo que venga
    #: después del ancla se considera nuevo, así que como mucho se repite alguna
    #: línea: preferible a re-sincronizar y encoger el historial visible.
    ANCHOR_OFFSETS = (0, 1, 2, 3)
    ANCHOR_SEARCH = 400

    @staticmethod
    def _sin_vacias_finales(lines: List[str]) -> List[str]:
        """Copia sin las líneas en blanco del final.

        Una captura de tmux termina en líneas vacías de relleno.  Usarlas como
        ancla era el fallo silencioso: `''` coincide trivialmente con el final de
        la captura nueva, el solape se encuentra en la última posición y el
        broker concluye que no hay nada nuevo — es decir, la consola se queda
        congelada justo cuando la ventana está saturada.
        """
        fin = len(lines)
        while fin and not lines[fin - 1].strip():
            fin -= 1
        return lines[:fin]

    def _new_lines_from_capture(self, item: "LiveConsoleItem",
                                lines: List[str]) -> Optional[List[str]]:
        """Líneas nuevas cuando el conteo no crece (ventana de tmux saturada).

        ``tmux capture-pane -S -max_lines`` devuelve una **ventana**: cuando el
        historial del panel la supera, el número de líneas se queda clavado
        aunque el servicio siga escribiendo.  Comparar conteos deja de detectar
        nada y la consola se congela para siempre.  Aquí se ancla en un bloque
        del final de la captura anterior y se devuelve lo que venga después.

        Devuelve ``None`` si ningún ancla aparece (el panel rotó de verdad más de
        ``ANCHOR_SEARCH`` posiciones): el cliente debe re-sincronizarse.
        """
        prev = item.last_capture
        if not prev or not lines:
            return None
        prev_util = self._sin_vacias_finales(prev)
        lineas_utiles = self._sin_vacias_finales(lines)
        if not prev_util:
            return []
        if not lineas_utiles:
            return None
        for salto in self.ANCHOR_OFFSETS:
            for size in self.ANCHOR_SIZES:
                if size + salto > len(prev_util) or size > len(lineas_utiles):
                    continue
                fin = len(prev_util) - salto
                bloque = prev_util[fin - size:fin]
                if not any(b.strip() for b in bloque):
                    continue      # ancla sólo de líneas vacías: no identifica nada
                inicio = len(lineas_utiles) - size
                for i in range(inicio, max(0, inicio - self.ANCHOR_SEARCH) - 1, -1):
                    if lineas_utiles[i:i + size] == bloque:
                        return lineas_utiles[i + size:]
        return None

    def _poll_once(self) -> None:
        """Execute one chained poll across all managed tmux sessions."""
        active_sessions = self._list_managed_tmux_sessions()
        if not active_sessions:
            # Mark all as stopped if tmux server has no managed sessions
            with self._lock:
                for item in self._items.values():
                    if item.status != "STOPPED":
                        item.status = "STOPPED"
            return

        # Ensure items exist for all active sessions (including dynamic auxiliaries)
        self._reconcile_active_sessions(active_sessions)

        # Build single chained capture command for all active sessions
        cmd = ["tmux"]
        for i, (session_name, _) in enumerate(active_sessions.items()):
            if i > 0:
                cmd.append(";")
            cmd.extend(["display-message", "-p", f"__PANESEP__{session_name}"])
            cmd.append(";")
            cmd.extend(["capture-pane", "-p", "-t", session_name, "-S", f"-{self.max_lines}"])

        try:
            raw = subprocess.check_output(cmd, stderr=subprocess.DEVNULL,
                                          timeout=CAPTURE_TIMEOUT_SECONDS).decode("utf-8", errors="replace")
        except Exception:
            return

        now = time.time()
        deltas_to_emit = []

        parts = raw.split("__PANESEP__")
        with self._lock:
            for p in parts[1:]:
                header_and_body = p.split("\n", 1)
                session_name = header_and_body[0].strip()
                content = header_and_body[1] if len(header_and_body) > 1 else ""

                item_id = active_sessions.get(session_name)
                if not item_id or item_id not in self._items:
                    continue

                item = self._items[item_id]
                item.last_seen_ts = now

                # Split raw lines and sanitize lengths
                lines = [line[:MAX_LINE_CHARS] for line in content.splitlines()]

                # Assess status from buffer content
                tail_sample = "\n".join(lines[-15:]) if len(lines) >= 15 else "\n".join(lines)
                if RE_STANDBY.search(tail_sample):
                    item.status = "STANDBY"
                elif RE_ERROR.search(tail_sample):
                    item.status = "FAILED"
                    item.recent_error = lines[-1] if lines else "Error detected in logs"
                    item.has_new_error = True
                else:
                    item.status = "RUNNING"

                # ¿Creció el contenido?  Con la ventana de captura saturada el
                # número de líneas deja de crecer aunque el servicio escriba
                # (capture-pane devuelve una ventana), así que ese caso se
                # detecta por solape con la captura anterior.  Sin ello, un
                # servicio con más historial que `max_lines` dejaba de emitir
                # deltas para siempre y su consola quedaba congelada.
                prev_count = item.last_line_count
                curr_count = len(lines)

                es_reset = False
                if curr_count < prev_count:
                    # Screen was cleared or respawned
                    es_reset = True
                    delta_lines = lines
                elif curr_count > prev_count:
                    # New lines appended
                    delta_lines = lines[prev_count:curr_count]
                else:
                    delta_lines = self._new_lines_from_capture(item, lines)
                    if delta_lines is None:
                        # El panel rotó más de lo que abarca la búsqueda: se
                        # re-sincroniza el cliente con un reset.
                        es_reset = True
                        delta_lines = lines

                if es_reset:
                    item.ring_buffer.clear()
                    for l in delta_lines:
                        item.ring_buffer.append(l)
                elif delta_lines:
                    # Apply fairness burst limit
                    if len(delta_lines) > MAX_BATCH_DELTA_LINES:
                        delta_lines = delta_lines[-MAX_BATCH_DELTA_LINES:]
                    for l in delta_lines:
                        item.ring_buffer.append(l)

                if es_reset or delta_lines:
                    item.last_line_count = curr_count
                    item.last_line_ts = now
                    payload = {
                        "id": item.id,
                        "service": item.service,
                        "status": item.status,
                        "lines": delta_lines[-(MAX_RESET_LINES if es_reset else MAX_BATCH_DELTA_LINES):] if delta_lines else [],
                        "timestamp": now,
                        "last_line_ts": now,
                    }
                    if es_reset:
                        payload["reset"] = True
                    deltas_to_emit.append(payload)

                item.last_capture = lines

        # Broadcast deltas to subscribers
        if deltas_to_emit and self._subscribers:
            self._broadcast({"type": "delta_batch", "deltas": deltas_to_emit})

    def _broadcast(self, event: Dict[str, Any]) -> None:
        """Send event to all subscriber queues, dropping if queue is congested."""
        dead_subs = []
        with self._lock:
            for sub_id, q in self._subscribers.items():
                try:
                    if q.full():
                        # Backpressure defense: drop oldest item
                        try:
                            q.get_nowait()
                        except queue.Empty:
                            pass
                    q.put_nowait(event)
                except Exception:
                    dead_subs.append(sub_id)

            for sub_id in dead_subs:
                self._subscribers.pop(sub_id, None)

    def _list_managed_tmux_sessions(self) -> Dict[str, str]:
        """Return dict of {tmux_session_name: item_id} for all active managed sessions."""
        try:
            output = subprocess.check_output(
                ["tmux", "list-sessions", "-F", "#{session_name}"],
                stderr=subprocess.DEVNULL,
            ).decode("utf-8", errors="replace")
        except Exception:
            return {}

        sessions = {}
        for line in output.splitlines():
            sname = line.strip()
            if not sname.startswith(SESSION_PREFIX):
                continue

            parsed = parse_tmux_session_name(sname)
            if not parsed or not parsed.get("service"):
                # Check plain service
                svc = sname[len(SESSION_PREFIX):]
                sessions[sname] = svc
            else:
                svc = parsed["service"]
                aux_type = parsed.get("aux_type")
                if aux_type:
                    item_id = f"{svc}_{aux_type}"
                    sessions[sname] = item_id
                else:
                    sessions[sname] = svc
        return sessions

    def _reconcile_active_sessions(self, active_sessions: Dict[str, str]) -> None:
        """Ensure items exist in _items for newly discovered sessions, mark inactive as STOPPED."""
        with self._lock:
            active_item_ids = set(active_sessions.values())

            for sname, item_id in active_sessions.items():
                if item_id not in self._items:
                    # Dynamically create auxiliary or unlisted item
                    parsed = parse_tmux_session_name(sname)
                    aux_type = parsed.get("aux_type") if parsed else None

                    if aux_type == "consumer":
                        cat = "consumer"
                    elif aux_type == "worker":
                        cat = "worker"
                    elif aux_type == "beat":
                        cat = "beat"
                    elif aux_type:
                        cat = "auxiliary"
                    elif item_id.startswith("ms_"):
                        cat = "backend"
                    elif item_id.startswith("mf_"):
                        cat = "frontend"
                    else:
                        cat = "auxiliary"

                    item = LiveConsoleItem(
                        id=item_id,
                        service=parsed.get("service", item_id) if parsed else item_id,
                        name=item_id,
                        category=cat,
                        service_type="auxiliary" if aux_type else ("backend" if cat == "backend" else "frontend"),
                        port=None,
                        tmux_session=sname,
                        status="RUNNING",
                    )
                    self._items[item_id] = item
                else:
                    if self._items[item_id].status == "STOPPED":
                        self._items[item_id].status = "RUNNING"

            # Check stopped items
            for item_id, item in self._items.items():
                if item_id not in active_item_ids and item.status != "STOPPED":
                    item.status = "STOPPED"

            # Podar lo que no es del catálogo ni tiene sesión viva.
            #
            # Marcar STOPPED no basta: cualquier sesión transitoria que el
            # broker alcance a ver —por ejemplo la que crea la prueba de
            # seguridad de terminal para comprobar que se rechaza— quedaba como
            # un servicio fantasma permanente en la interfaz hasta reiniciar el
            # panel.  Los servicios declarados sí se conservan detenidos, que es
            # como la interfaz muestra que existen pero no están corriendo.
            stale = [
                item_id for item_id in self._items
                if item_id not in self._seeded and item_id not in active_item_ids
            ]
            for item_id in stale:
                self._items.pop(item_id, None)


_GLOBAL_BROKER: Optional[LiveConsoleBroker] = None
_BROKER_LOCK = threading.Lock()


def get_live_broker() -> LiveConsoleBroker:
    """Return the global LiveConsoleBroker singleton, starting it if not running."""
    global _GLOBAL_BROKER
    with _BROKER_LOCK:
        if _GLOBAL_BROKER is None:
            _GLOBAL_BROKER = LiveConsoleBroker()
            _GLOBAL_BROKER.start()
        return _GLOBAL_BROKER
