"""Additive UI bootstrap for the V1.1 migration.

The legacy ``index.html`` and ``dashboard.js`` remain untouched.  This adapter
serves the same page and injects a namespaced stylesheet plus one ES-module
bootstrap.  If either V1.1 asset fails, the V1 dashboard still loads because all
existing script/style tags are preserved.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_INSTALLED = False
_ORIGINAL_DO_GET = None


def _asset_version(path: Path) -> str:
    try:
        return str(path.stat().st_mtime_ns)
    except OSError:
        return "0"


def inject_assets(html: str, static_dir: Path) -> str:
    """Inject V1.1 namespaced assets exactly once."""
    if 'data-devconsole-v11="ui-foundation"' in html:
        return html

    css = static_dir / "css" / "v11-foundation.css"
    js = static_dir / "js" / "v11" / "app.js"
    style_tag = (
        '<link data-devconsole-v11="ui-foundation" rel="stylesheet" '
        f'href="/static/css/v11-foundation.css?v={_asset_version(css)}">'
    )
    script_tag = (
        '<script data-devconsole-v11="ui-foundation" type="module" '
        f'src="/static/js/v11/app.js?v={_asset_version(js)}"></script>'
    )

    if "</head>" in html:
        html = html.replace("</head>", f"  {style_tag}\n</head>", 1)
    else:
        html = style_tag + "\n" + html
    if "</body>" in html:
        html = html.replace("</body>", f"  {script_tag}\n</body>", 1)
    else:
        html += "\n" + script_tag
    return html


def render_index(handlers_module) -> tuple[str | None, dict[str, str]]:
    """Render the legacy index with its cache markers plus V1.1 assets."""
    index_file = Path(handlers_module.STATIC_DIR) / "index.html"
    if not index_file.exists():
        return None, {}

    html = index_file.read_text(encoding="utf-8")
    versions = handlers_module._version_estaticos()
    for name, version in versions.items():
        html = html.replace(f'"/static/{name}"', f'"/static/{name}?v={version}"')

    marker = (
        "<script>window.__UI_VERSION="
        + repr(versions.get("js/dashboard.js", "")).replace("'", '"')
        + ";</script>\n  "
    )
    html = html.replace(
        '<script src="/static/js/dashboard.js',
        marker + '<script src="/static/js/dashboard.js',
        1,
    )
    return inject_assets(html, Path(handlers_module.STATIC_DIR)), versions


def install(handler_cls, handlers_module) -> None:
    """Wrap the already authorised GET dispatcher for root-page rendering."""
    global _INSTALLED, _ORIGINAL_DO_GET
    if _INSTALLED:
        return

    _ORIGINAL_DO_GET = handler_cls._do_GET

    def _do_GET_v11_ui(self):
        import urllib.parse

        path = urllib.parse.urlparse(self.path).path
        if path not in ("/", "/index.html"):
            return _ORIGINAL_DO_GET(self)

        html, _versions = render_index(handlers_module)
        if html is None:
            self.send_response(404)
            self.end_headers()
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        if handlers_module.local_trust.token_required():
            self.send_header(
                "Set-Cookie",
                handlers_module.local_trust.build_cookie_header(),
            )
        self._send_security_headers()
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    handler_cls._do_GET = _do_GET_v11_ui
    _INSTALLED = True


def status() -> dict[str, Any]:
    return {
        "installed": _INSTALLED,
        "strategy": "additive-es-module-bootstrap",
        "legacy_index_preserved": True,
    }
