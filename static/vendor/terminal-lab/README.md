# Terminal Lab vendor assets

Assets used only by the isolated 30-console prototype. Browser packages were fetched from the npm registry and verified against registry package metadata (integrity/shasum). No source TypeScript is loaded by the browser.

Locally installed bundles:
- `dockview.js` + `dockview.css`: Dockview 8.5.1 UMD + compiled stylesheet.
- `addon-fit.js`: `@xterm/addon-fit` 0.11.0.
- `addon-search.js`: `@xterm/addon-search` 0.16.0.
- Core xterm is existing vendored `static/js/xterm.js` (4.18.0). Both addons document compatibility with xterm v4+.
- `icons/`: selected individual SVGs from Lucide 1.56.0.

Runtime uses local files only (no CDN fetches). Licenses are preserved in the `LICENSE-*` files.
