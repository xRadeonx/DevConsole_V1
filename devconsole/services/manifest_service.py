"""Round-trip Kubernetes manifest editing with preview/diff support."""
from __future__ import annotations

import difflib
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    from ruamel.yaml import YAML  # type: ignore
except ImportError:  # pragma: no cover - optional fallback path
    YAML = None  # type: ignore[assignment]


class ManifestDependencyMissing(RuntimeError):
    pass


@dataclass(frozen=True)
class ManifestChange:
    changed: bool
    before: str
    after: str
    diff: str
    images_before: tuple[str, ...] = ()
    images_after: tuple[str, ...] = ()


def _yaml() -> Any:
    if YAML is None:
        raise ManifestDependencyMissing("ruamel.yaml no está instalado")
    yaml = YAML(typ="rt")
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml


def _documents(text: str) -> tuple[Any, list[Any]]:
    yaml = _yaml()
    docs = list(yaml.load_all(text))
    return yaml, docs


def _containers(doc: Any) -> Iterable[dict]:
    if not isinstance(doc, dict):
        return ()
    spec = doc.get("spec") or {}
    template = spec.get("template") or {}
    pod_spec = (template.get("spec") or {}) if isinstance(template, dict) else {}
    containers = pod_spec.get("containers") or []
    if not containers and doc.get("kind") in {"Pod"}:
        containers = spec.get("containers") or []
    return (c for c in containers if isinstance(c, dict))


def _split_image(image: str) -> tuple[str, str | None]:
    if "@sha256:" in image:
        return image, None
    tail = image.rsplit("/", 1)[-1]
    if ":" not in tail:
        return image, None
    base, tag = image.rsplit(":", 1)
    return base, tag


def preview_image_tag_update(
    path: Path | str,
    new_version: str,
    *,
    skip_image_tokens: tuple[str, ...] = ("nginx",),
) -> ManifestChange:
    manifest = Path(path)
    before = manifest.read_text(encoding="utf-8")
    yaml, docs = _documents(before)
    images_before: list[str] = []
    images_after: list[str] = []
    changed = False
    for doc in docs:
        for container in _containers(doc):
            image = str(container.get("image") or "")
            if not image:
                continue
            images_before.append(image)
            if any(token.lower() in image.lower() for token in skip_image_tokens):
                images_after.append(image)
                continue
            base, old_tag = _split_image(image)
            if old_tag is None:
                images_after.append(image)
                continue
            updated = f"{base}:{new_version}"
            images_after.append(updated)
            if updated != image:
                container["image"] = updated
                changed = True

    stream = io.StringIO()
    yaml.dump_all(docs, stream)
    after = stream.getvalue()
    if not changed:
        after = before
    diff = "".join(difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=str(manifest),
        tofile=str(manifest),
    ))
    return ManifestChange(changed, before, after, diff, tuple(images_before), tuple(images_after))


def apply_image_tag_update(
    path: Path | str,
    new_version: str,
    *,
    skip_image_tokens: tuple[str, ...] = ("nginx",),
) -> ManifestChange:
    change = preview_image_tag_update(path, new_version, skip_image_tokens=skip_image_tokens)
    if change.changed:
        manifest = Path(path)
        temporary = manifest.with_suffix(manifest.suffix + ".devconsole.tmp")
        temporary.write_text(change.after, encoding="utf-8")
        temporary.replace(manifest)
    return change
