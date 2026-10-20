"""Structured YAML utilities for the DevConsole V1.1 migration.

The existing Kubernetes service remains authoritative during this phase.  This
module provides a round-trip implementation backed by ``ruamel.yaml`` so we can
prove equivalence before replacing regex-based reads/writes.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any, Iterable

try:  # Optional until the V1.1 installer is promoted.
    from ruamel.yaml import YAML
except ImportError:  # pragma: no cover
    YAML = None


class YamlDependencyUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class ImageChange:
    old: str
    new: str
    document: int


@dataclass(frozen=True)
class ManifestSummary:
    kind: str = ""
    name: str = ""
    image: str = ""
    version: str = ""
    document: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "name": self.name,
            "image": self.image,
            "version": self.version,
            "document": self.document,
        }


def available() -> bool:
    return YAML is not None


def _yaml():
    if YAML is None:
        raise YamlDependencyUnavailable("ruamel.yaml is not installed")
    parser = YAML(typ="rt")
    parser.preserve_quotes = True
    parser.width = 4096
    return parser


def load_documents(text: str) -> list[Any]:
    parser = _yaml()
    return list(parser.load_all(text))


def dump_documents(documents: Iterable[Any]) -> str:
    parser = _yaml()
    stream = StringIO()
    parser.dump_all(list(documents), stream)
    return stream.getvalue()


def _iter_images(node: Any):
    """Yield mutable mappings and the key for every structured ``image`` field."""
    if isinstance(node, dict):
        for key, value in list(node.items()):
            if str(key) == "image" and isinstance(value, str):
                yield node, key, value
            else:
                yield from _iter_images(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_images(item)


def _retag(image: str, version: str) -> str | None:
    """Retag an already-tagged container image while preserving its registry."""
    value = image.strip()
    if not value or "@" in value:
        return None
    tail = value.rsplit("/", 1)[-1]
    if ":" not in tail:
        return None
    prefix, _old = value.rsplit(":", 1)
    return f"{prefix}:{version}"


def update_image_tags(text: str, new_version: str, *, skip_contains=("nginx",)) -> tuple[str, tuple[ImageChange, ...]]:
    """Update tagged structured ``image`` values and return round-tripped YAML.

    Behaviour intentionally mirrors the legacy updater during shadow mode:
    untagged/digest images are untouched and images containing ``nginx`` are
    skipped.  This function never writes to disk by itself.
    """
    documents = load_documents(text)
    changes: list[ImageChange] = []
    skip = tuple(str(part).lower() for part in skip_contains)

    for doc_index, document in enumerate(documents):
        for mapping, key, old in _iter_images(document):
            if any(part in old.lower() for part in skip):
                continue
            new = _retag(old, new_version)
            if not new or new == old:
                continue
            mapping[key] = new
            changes.append(ImageChange(old=old, new=new, document=doc_index))

    return dump_documents(documents), tuple(changes)


def update_image_tags_file(path: str | Path, new_version: str, *, write: bool = False,
                           skip_contains=("nginx",)) -> tuple[str, tuple[ImageChange, ...]]:
    """Prepare an update for one YAML file; disk write is explicit and optional."""
    target = Path(path)
    original = target.read_text(encoding="utf-8")
    updated, changes = update_image_tags(original, new_version, skip_contains=skip_contains)
    if write and changes:
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(updated, encoding="utf-8")
        tmp.replace(target)
    return updated, changes


def _version_from_image(image: str) -> str:
    if not image or "@" in image:
        return ""
    tail = image.rsplit("/", 1)[-1]
    return tail.rsplit(":", 1)[-1] if ":" in tail else ""


def summarize_manifest(text: str, *, preferred_kinds=("Deployment", "StatefulSet", "DaemonSet", "Job", "CronJob")) -> ManifestSummary:
    """Return kind/name/first image from a parsed multi-document manifest."""
    documents = load_documents(text)
    summaries: list[ManifestSummary] = []
    for index, document in enumerate(documents):
        if not isinstance(document, dict):
            continue
        kind = str(document.get("kind") or "")
        metadata = document.get("metadata") if isinstance(document.get("metadata"), dict) else {}
        name = str(metadata.get("name") or "")
        first_image = next((value for _mapping, _key, value in _iter_images(document)), "")
        summaries.append(ManifestSummary(
            kind=kind,
            name=name,
            image=first_image,
            version=_version_from_image(first_image),
            document=index,
        ))

    for preferred in preferred_kinds:
        for item in summaries:
            if item.kind == preferred:
                return item
    return summaries[0] if summaries else ManifestSummary()


def validate_manifest(text: str) -> tuple[bool, tuple[str, ...]]:
    """Perform safe structural validation without invoking kubectl."""
    try:
        documents = load_documents(text)
    except Exception as exc:
        return False, (f"yaml_parse_error:{type(exc).__name__}:{exc}",)

    errors: list[str] = []
    meaningful = 0
    for index, document in enumerate(documents):
        if document is None:
            continue
        meaningful += 1
        if not isinstance(document, dict):
            errors.append(f"document[{index}]: root must be a mapping")
            continue
        if not document.get("apiVersion"):
            errors.append(f"document[{index}]: missing apiVersion")
        if not document.get("kind"):
            errors.append(f"document[{index}]: missing kind")
        metadata = document.get("metadata")
        if not isinstance(metadata, dict) or not metadata.get("name"):
            errors.append(f"document[{index}]: missing metadata.name")

    if meaningful == 0:
        errors.append("manifest contains no documents")
    return not errors, tuple(errors)
