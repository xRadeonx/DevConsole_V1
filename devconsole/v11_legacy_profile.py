"""Local compatibility importer for an existing SISPER DevConsole workspace.

The clean V1 repository intentionally removed installation-specific endpoints and
credentials from version control.  Existing SISPER workstations, however, can
already have the historical DevConsole checkout as the selected workspace.  It
contains the operator's DEVELOP / TEST / MAIN catalog.

This module recovers that *local* catalog in memory without importing or
executing the legacy Python file and without copying credentials into this
repository.  Explicit V1.1 ``panel.json`` configuration always wins.
"""

from __future__ import annotations

import ast
import base64
import json
import re
import sys
from pathlib import Path
from typing import Any

_INSTALLED = False


def _workspace_root() -> Path:
    from devconsole import config

    return Path(config.BASE_DIR)


def _safe_eval(node: ast.AST) -> Any:
    """Evaluate only literals and the legacy base64-decode expression shape.

    No names, imports, attribute access or arbitrary calls are executed.  The
    only supported call is ``base64.b64decode(<literal>).decode('utf-8')`` used
    by the historical configuration to obfuscate (not encrypt) local secrets.
    """
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Dict):
        return {_safe_eval(k): _safe_eval(v) for k, v in zip(node.keys, node.values)}
    if isinstance(node, ast.List):
        return [_safe_eval(v) for v in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_safe_eval(v) for v in node.elts)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _safe_eval(node.operand)
        if not isinstance(value, (int, float)):
            raise ValueError("unsupported unary value")
        return -value if isinstance(node.op, ast.USub) else value

    # Exact historical shape: base64.b64decode("...").decode("utf-8")
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "decode":
        inner = node.func.value
        if (
            isinstance(inner, ast.Call)
            and isinstance(inner.func, ast.Attribute)
            and inner.func.attr == "b64decode"
            and isinstance(inner.func.value, ast.Name)
            and inner.func.value.id == "base64"
            and len(inner.args) == 1
        ):
            encoded = _safe_eval(inner.args[0])
            encoding = _safe_eval(node.args[0]) if node.args else "utf-8"
            if not isinstance(encoded, (str, bytes)) or encoding != "utf-8":
                raise ValueError("unsupported base64 expression")
            return base64.b64decode(encoded).decode("utf-8")

    raise ValueError(f"unsupported legacy expression: {type(node).__name__}")


def _read_legacy_python_catalog(root: Path | None = None) -> dict[str, dict[str, Any]]:
    """Extract selected top-level dictionaries from legacy ``config.py`` safely."""
    root = Path(root) if root is not None else _workspace_root()
    path = root / "devconsole" / "config.py"
    if not path.is_file():
        return {}
    try:
        tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"), filename=str(path))
    except (OSError, SyntaxError):
        return {}

    wanted = {"KEYCLOAK_ENV_CONFIGS", "DATABASE_ENV_CONFIGS"}
    out: dict[str, dict[str, Any]] = {}
    for stmt in tree.body:
        if not isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            continue
        targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
        value_node = stmt.value
        for target in targets:
            if isinstance(target, ast.Name) and target.id in wanted and value_node is not None:
                try:
                    value = _safe_eval(value_node)
                except (ValueError, TypeError, UnicodeDecodeError, base64.binascii.Error):
                    continue
                if isinstance(value, dict):
                    out[target.id] = value
    return out


def _balanced_block(text: str, start: int, open_char: str, close_char: str) -> str | None:
    depth = 0
    quote: str | None = None
    escaped = False
    for index in range(start, len(text)):
        ch = text[index]
        if quote:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == quote:
                quote = None
            continue
        if ch in ("'", '"', "`"):
            quote = ch
            continue
        if ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def _parse_js_value(token: str) -> Any:
    token = token.strip()
    if token == "null":
        return None
    if token == "true":
        return True
    if token == "false":
        return False
    if token.startswith('"'):
        try:
            return json.loads(token)
        except json.JSONDecodeError:
            return token[1:-1]
    return token


def _parse_js_entries(block: str) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for match in re.finditer(r"\{(.*?)\}", block, flags=re.DOTALL):
        body = match.group(1)
        item: dict[str, Any] = {}
        pattern = re.compile(
            r"([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(\"(?:\\.|[^\"\\])*\"|null|true|false)",
            flags=re.DOTALL,
        )
        for field in pattern.finditer(body):
            item[field.group(1)] = _parse_js_value(field.group(2))
        if item.get("id") and item.get("target") is not None:
            entries.append(item)
    return entries


def _read_legacy_infra_targets(root: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    """Extract the historical infrastructure matrix from local dashboard.js.

    The parser understands only the simple literal object used by V1.  It does
    not evaluate JavaScript.
    """
    root = Path(root) if root is not None else _workspace_root()
    path = root / "static" / "js" / "dashboard.js"
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return {}

    marker = re.search(r"\b(?:const|let|var)\s+INFRA_ENDPOINTS\s*=\s*\{", text)
    if not marker:
        return {}
    object_start = text.find("{", marker.start())
    object_block = _balanced_block(text, object_start, "{", "}")
    if not object_block:
        return {}

    result: dict[str, list[dict[str, Any]]] = {}
    for source_name, target_name in (("local", "local"), ("develop", "develop"), ("test", "test"), ("main", "main"), ("prod", "main")):
        match = re.search(rf"\b{re.escape(source_name)}\s*:\s*\[", object_block)
        if not match:
            continue
        start = object_block.find("[", match.start())
        array_block = _balanced_block(object_block, start, "[", "]")
        if not array_block:
            continue
        entries = _parse_js_entries(array_block)
        if entries and target_name not in result:
            result[target_name] = entries
    return result


def _merge_missing(target: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if key not in target or target.get(key) in (None, "", 0):
            target[key] = value


def hydrate_environment_catalog(root: Path | None = None) -> bool:
    """Merge legacy TEST/MAIN/DEVELOP config into current in-memory maps.

    Explicit V1.1 configuration wins field-by-field.  The legacy values are
    never persisted and never printed.
    """
    from devconsole import config

    catalog = _read_legacy_python_catalog(root)
    if not catalog:
        return False

    changed = False
    for attr in ("KEYCLOAK_ENV_CONFIGS", "DATABASE_ENV_CONFIGS"):
        source_map = catalog.get(attr) or {}
        targets: list[dict[str, Any]] = []
        current = getattr(config, attr, None)
        if isinstance(current, dict):
            targets.append(current)
        telemetry = sys.modules.get("devconsole.services.telemetry_service")
        telemetry_map = getattr(telemetry, attr, None) if telemetry else None
        if isinstance(telemetry_map, dict) and telemetry_map is not current:
            targets.append(telemetry_map)

        for source_env, source_values in source_map.items():
            env = "main" if source_env in ("main", "prod") else source_env
            if env not in ("develop", "test", "main") or not isinstance(source_values, dict):
                continue
            for target_map in targets:
                entry = target_map.setdefault(env, {})
                if not isinstance(entry, dict):
                    entry = {}
                    target_map[env] = entry
                before = dict(entry)
                _merge_missing(entry, source_values)
                changed = changed or entry != before
    return changed


def _install_infra_targets_bridge() -> None:
    from devconsole import settings

    original = settings.infra_targets
    if getattr(original, "_v11_legacy_profile", False):
        return

    def infra_targets_with_legacy() -> dict:
        configured = original()
        if configured:
            return configured
        return _read_legacy_infra_targets()

    infra_targets_with_legacy._v11_legacy_profile = True  # type: ignore[attr-defined]
    settings.infra_targets = infra_targets_with_legacy


def _install_base_dir_refresh() -> None:
    from devconsole import config

    original = config.set_base_dir
    if getattr(original, "_v11_legacy_profile", False):
        return

    def set_base_dir_with_legacy(new_path):
        result = original(new_path)
        try:
            ok = bool(result[0])
        except Exception:
            ok = False
        if ok:
            hydrate_environment_catalog()
        return result

    set_base_dir_with_legacy._v11_legacy_profile = True  # type: ignore[attr-defined]
    config.set_base_dir = set_base_dir_with_legacy


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    _install_infra_targets_bridge()
    _install_base_dir_refresh()
    hydrate_environment_catalog()
    _INSTALLED = True


def status() -> dict[str, Any]:
    targets = _read_legacy_infra_targets()
    catalog = _read_legacy_python_catalog()
    return {
        "installed": _INSTALLED,
        "legacy_profile_available": bool(targets or catalog),
        "environments": sorted({"main" if k == "prod" else k for mapping in catalog.values() for k in mapping if k in {"develop", "test", "main", "prod"}}),
        "infra_environments": sorted(targets),
    }
