# devconsole/services/ttl_cache.py
"""Caché TTL acotada, segura entre hilos y con *single-flight*, para sondeos
costosos e idempotentes.

Motivación
----------
``GET /api/status`` recorre cada servicio descubierto y, por cada uno, lanza
procesos ``git`` (rama, estado, upstream, ahead, behind, log).  Además agrega
``get_all_environments_status()``, que vuelve a recorrer los mismos servicios y
repite esas mismas llamadas.  Con ~30 servicios eso son varios cientos de
subprocesos por petición, y el endpoint queda en el orden de los segundos,
justo en la ruta que la interfaz usa para refrescar el estado.

Este módulo no cambia *qué* se reporta: sólo evita repetir el mismo sondeo
dentro de una ventana corta.  Las funciones decoradas deben ser idempotentes y
depender únicamente de sus argumentos.

*Single-flight*: cuando el valor de una clave expira, sólo el primer hilo lo
recalcula; los demás esperan ese mismo resultado en lugar de lanzar su propia
tanda de subprocesos.  Sin esto, la expiración del TTL produciría una estampida
que bloquea justo a las peticiones que se querían acelerar.

Uso
---
    from devconsole.services.ttl_cache import ttl_cache, invalidate_all

    @ttl_cache(seconds=15)
    def get_git_info(directory: Path) -> dict: ...

Tras una operación que muta el estado observado (pull, checkout, cambio de
raíz, reinicio) conviene llamar a :func:`invalidate_all` para que el próximo
sondeo lea datos frescos en vez de esperar a que expire la ventana.
"""

from __future__ import annotations

import functools
import threading
import time
from typing import Any, Callable

__all__ = ["ttl_cache", "invalidate_all", "stats", "reset_stats"]

_LOCK = threading.RLock()
#: clave -> (instante de expiración monótono, valor)
_STORE: dict[tuple, tuple[float, Any]] = {}
#: clave -> evento que se activa cuando el hilo líder termina de calcularla
_INFLIGHT: dict[tuple, threading.Event] = {}

#: Tope de espera por un cálculo ajeno, para no colgarse si el líder se traba.
_INFLIGHT_WAIT_SECONDS = 60.0

_HITS = 0
_MISSES = 0


def _make_key(name: str, args: tuple, kwargs: dict) -> tuple | None:
    """Clave estable para ``args``/``kwargs``.

    Los argumentos deben ser *hashables* (``Path``, ``str``, ``int`` lo son).
    Un argumento no hashable no debe romper la petición: en ese caso se
    devuelve ``None`` y la función se ejecuta sin cachear.
    """
    try:
        return (name, args, tuple(sorted(kwargs.items())))
    except TypeError:
        return None


def ttl_cache(seconds: float) -> Callable:
    """Decora una función para cachear su resultado durante ``seconds``.

    ``seconds`` debe ser > 0; un valor no positivo desactiva la caché y deja la
    función intacta (útil para tests que necesitan datos siempre frescos).
    """

    def decorator(fn: Callable) -> Callable:
        if seconds <= 0:
            return fn

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            global _HITS, _MISSES

            key = _make_key(fn.__qualname__, args, kwargs)
            if key is None:
                return fn(*args, **kwargs)

            now = time.monotonic()
            with _LOCK:
                entry = _STORE.get(key)
                if entry is not None and entry[0] > now:
                    _HITS += 1
                    return entry[1]

                event = _INFLIGHT.get(key)
                if event is None:
                    event = threading.Event()
                    _INFLIGHT[key] = event
                    is_leader = True
                else:
                    is_leader = False

            if not is_leader:
                # Otro hilo ya está calculando este mismo valor: esperar su
                # resultado en vez de duplicar la tanda de subprocesos.
                event.wait(timeout=_INFLIGHT_WAIT_SECONDS)
                with _LOCK:
                    entry = _STORE.get(key)
                    if entry is not None:
                        _HITS += 1
                        return entry[1]
                # El líder falló o se agotó la espera: calcular sin ser líder,
                # para no dejar a este llamador sin valor.
                _MISSES += 1
                return fn(*args, **kwargs)

            try:
                value = fn(*args, **kwargs)
            except BaseException:
                with _LOCK:
                    _INFLIGHT.pop(key, None)
                event.set()
                raise

            with _LOCK:
                _MISSES += 1
                _STORE[key] = (time.monotonic() + seconds, value)
                _INFLIGHT.pop(key, None)
            # Despertar a los que esperaban DESPUÉS de publicar el valor, para
            # que lo encuentren en la caché al despertar.
            event.set()
            return value

        def cache_clear() -> None:
            """Descarta sólo las entradas de esta función."""
            with _LOCK:
                prefix = fn.__qualname__
                for k in [k for k in _STORE if k and k[0] == prefix]:
                    _STORE.pop(k, None)

        def refresh(*args, **kwargs):
            """Recalcula y publica el valor aunque la entrada siga vigente.

            Lo usa el refrescador en segundo plano: al republicar *antes* de que
            expire la ventana, ninguna petición de la interfaz llega a encontrar
            la caché vencida y por lo tanto ninguna espera un recálculo.
            """
            global _MISSES
            key = _make_key(fn.__qualname__, args, kwargs)
            value = fn(*args, **kwargs)
            if key is not None:
                with _LOCK:
                    _MISSES += 1
                    _STORE[key] = (time.monotonic() + seconds, value)
            return value

        wrapper.cache_clear = cache_clear  # type: ignore[attr-defined]
        wrapper.refresh = refresh  # type: ignore[attr-defined]
        return wrapper

    return decorator


def invalidate_all() -> int:
    """Vacía la caché completa y devuelve cuántas entradas se descartaron.

    Se llama tras cualquier acción que cambie el estado observado, para que la
    interfaz refleje el resultado de inmediato en lugar de mostrar un valor
    obsoleto hasta que expire la ventana.
    """
    with _LOCK:
        removed = len(_STORE)
        _STORE.clear()
        return removed


def stats() -> dict:
    """Métricas de aciertos/fallos, para diagnóstico y pruebas."""
    with _LOCK:
        total = _HITS + _MISSES
        return {
            "entries": len(_STORE),
            "inflight": len(_INFLIGHT),
            "hits": _HITS,
            "misses": _MISSES,
            "hit_ratio": round(_HITS / total, 3) if total else 0.0,
        }


def reset_stats() -> None:
    """Reinicia los contadores (no toca las entradas cacheadas)."""
    global _HITS, _MISSES
    with _LOCK:
        _HITS = 0
        _MISSES = 0
