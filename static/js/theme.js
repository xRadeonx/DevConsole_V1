/* =============================================================================
   SISPER DevConsole — Motor de temas
   Aplica un tema a TODA la aplicación cambiando [data-theme] en <html>.
   Los tokens viven en /static/css/themes.css; aquí solo se seleccionan.
   API pública: window.SisperTheme = { list, current, apply, termTheme, openSettings, closeSettings }
   ============================================================================= */
(function () {
  'use strict';

  var STORAGE_KEY = 'sisper_theme';
  var DEFAULT = 'abyss';

  var THEMES = [
      {id:"abyss",label:"Abyss (azul)",mode:'dark'},
      {id:"catppuccin",label:"Catppuccin Mocha",mode:'dark'},
      {id:"tokyo",label:"Tokyo Night",mode:'dark'},
      {id:"dracula",label:"Dracula",mode:'dark'},
      {id:"nord",label:"Nord",mode:'dark'},
      {id:"gruvbox",label:"Gruvbox oscuro",mode:'dark'},
      {id:"onedark",label:"One Dark",mode:'dark'},
      {id:"solarized",label:"Solarized oscuro",mode:'dark'},
      {id:"monokai",label:"Monokai",mode:'dark'},
      {id:"rosepine",label:"Ros\u00e9 Pine",mode:'dark'},
      {id:"matrix",label:"Matrix (verde)",mode:'dark'},
      {id:"amber",label:"\u00c1mbar CRT",mode:'dark'},
      {id:"light",label:"Claro (papel)",mode:'light'}
  ];

  /* Paletas para xterm.js (mismas que el laboratorio de terminales). */
  var TERM = {
      "abyss":{"background": "#080d14", "foreground": "#d9e4ef", "cursor": "#38bdf8", "selectionBackground": "#24516d88", "black": "#101720", "red": "#fb7185", "green": "#34d399", "yellow": "#fbbf24", "blue": "#60a5fa", "magenta": "#c084fc", "cyan": "#22d3ee", "white": "#cbd5e1", "brightBlack": "#64748b", "brightRed": "#fda4af", "brightGreen": "#6ee7b7", "brightYellow": "#fde68a", "brightBlue": "#93c5fd", "brightMagenta": "#d8b4fe", "brightCyan": "#67e8f9", "brightWhite": "#ffffff"},
      "catppuccin":{"background": "#11111b", "foreground": "#cdd6f4", "cursor": "#f5e0dc", "selectionBackground": "#cba6f744", "black": "#45475a", "red": "#f38ba8", "green": "#a6e3a1", "yellow": "#f9e2af", "blue": "#89b4fa", "magenta": "#cba6f7", "cyan": "#94e2d5", "white": "#bac2de", "brightBlack": "#585b70", "brightRed": "#f37799", "brightGreen": "#89d88b", "brightYellow": "#ebd391", "brightBlue": "#74a8fc", "brightMagenta": "#baa0f8", "brightCyan": "#74c7ec", "brightWhite": "#cdd6f4"},
      "tokyo":{"background": "#16161e", "foreground": "#c0caf5", "cursor": "#c0caf5", "selectionBackground": "#33467c88", "black": "#15161e", "red": "#f7768e", "green": "#9ece6a", "yellow": "#e0af68", "blue": "#7aa2f7", "magenta": "#bb9af7", "cyan": "#7dcfff", "white": "#a9b1d6", "brightBlack": "#414868", "brightRed": "#f7768e", "brightGreen": "#9ece6a", "brightYellow": "#e0af68", "brightBlue": "#7aa2f7", "brightMagenta": "#bb9af7", "brightCyan": "#7dcfff", "brightWhite": "#c0caf5"},
      "dracula":{"background": "#21222c", "foreground": "#f8f8f2", "cursor": "#f8f8f2", "selectionBackground": "#44475a99", "black": "#21222c", "red": "#ff5555", "green": "#50fa7b", "yellow": "#f1fa8c", "blue": "#bd93f9", "magenta": "#ff79c6", "cyan": "#8be9fd", "white": "#f8f8f2", "brightBlack": "#6272a4", "brightRed": "#ff6e6e", "brightGreen": "#69ff94", "brightYellow": "#ffffa5", "brightBlue": "#d6acff", "brightMagenta": "#ff92df", "brightCyan": "#a4ffff", "brightWhite": "#ffffff"},
      "nord":{"background": "#2e3440", "foreground": "#d8dee9", "cursor": "#d8dee9", "selectionBackground": "#4c566a99", "black": "#3b4252", "red": "#bf616a", "green": "#a3be8c", "yellow": "#ebcb8b", "blue": "#81a1c1", "magenta": "#b48ead", "cyan": "#88c0d0", "white": "#e5e9f0", "brightBlack": "#4c566a", "brightRed": "#d08770", "brightGreen": "#b9d5a0", "brightYellow": "#f0d8a0", "brightBlue": "#8fbcbb", "brightMagenta": "#c9a7c4", "brightCyan": "#9fd6e0", "brightWhite": "#eceff4"},
      "gruvbox":{"background": "#1d2021", "foreground": "#ebdbb2", "cursor": "#ebdbb2", "selectionBackground": "#504945aa", "black": "#282828", "red": "#fb4934", "green": "#b8bb26", "yellow": "#fabd2f", "blue": "#83a598", "magenta": "#d3869b", "cyan": "#8ec07c", "white": "#ebdbb2", "brightBlack": "#928374", "brightRed": "#fb4934", "brightGreen": "#b8bb26", "brightYellow": "#fabd2f", "brightBlue": "#83a598", "brightMagenta": "#d3869b", "brightCyan": "#8ec07c", "brightWhite": "#fbf1c7"},
      "onedark":{"background": "#21252b", "foreground": "#abb2bf", "cursor": "#528bff", "selectionBackground": "#3e445199", "black": "#282c34", "red": "#e06c75", "green": "#98c379", "yellow": "#e5c07b", "blue": "#61afef", "magenta": "#c678dd", "cyan": "#56b6c2", "white": "#abb2bf", "brightBlack": "#5c6370", "brightRed": "#e06c75", "brightGreen": "#98c379", "brightYellow": "#e5c07b", "brightBlue": "#61afef", "brightMagenta": "#c678dd", "brightCyan": "#56b6c2", "brightWhite": "#ffffff"},
      "solarized":{"background": "#002b36", "foreground": "#93a1a1", "cursor": "#93a1a1", "selectionBackground": "#0f4a5699", "black": "#073642", "red": "#dc322f", "green": "#859900", "yellow": "#b58900", "blue": "#268bd2", "magenta": "#d33682", "cyan": "#2aa198", "white": "#eee8d5", "brightBlack": "#586e75", "brightRed": "#cb4b16", "brightGreen": "#859900", "brightYellow": "#b58900", "brightBlue": "#268bd2", "brightMagenta": "#6c71c4", "brightCyan": "#2aa198", "brightWhite": "#fdf6e3"},
      "monokai":{"background": "#272822", "foreground": "#f8f8f2", "cursor": "#f8f8f0", "selectionBackground": "#49483e99", "black": "#272822", "red": "#f92672", "green": "#a6e22e", "yellow": "#f4bf75", "blue": "#66d9ef", "magenta": "#ae81ff", "cyan": "#a1efe4", "white": "#f8f8f2", "brightBlack": "#75715e", "brightRed": "#f92672", "brightGreen": "#a6e22e", "brightYellow": "#f4bf75", "brightBlue": "#66d9ef", "brightMagenta": "#ae81ff", "brightCyan": "#a1efe4", "brightWhite": "#f9f8f5"},
      "rosepine":{"background": "#191724", "foreground": "#e0def4", "cursor": "#524f67", "selectionBackground": "#403d5299", "black": "#26233a", "red": "#eb6f92", "green": "#31748f", "yellow": "#f6c177", "blue": "#9ccfd8", "magenta": "#c4a7e7", "cyan": "#ebbcba", "white": "#e0def4", "brightBlack": "#6e6a86", "brightRed": "#eb6f92", "brightGreen": "#31748f", "brightYellow": "#f6c177", "brightBlue": "#9ccfd8", "brightMagenta": "#c4a7e7", "brightCyan": "#ebbcba", "brightWhite": "#e0def4"},
      "matrix":{"background": "#020703", "foreground": "#7dfba0", "cursor": "#22c55e", "selectionBackground": "#22c55e33", "black": "#05130a", "red": "#f87171", "green": "#4ade80", "yellow": "#facc15", "blue": "#38bdf8", "magenta": "#c084fc", "cyan": "#2dd4bf", "white": "#bbf7d0", "brightBlack": "#3f7a52", "brightRed": "#fca5a5", "brightGreen": "#86efac", "brightYellow": "#fde68a", "brightBlue": "#7dd3fc", "brightMagenta": "#d8b4fe", "brightCyan": "#5eead4", "brightWhite": "#f0fdf4"},
      "amber":{"background": "#0f0a02", "foreground": "#ffcc66", "cursor": "#f59e0b", "selectionBackground": "#f59e0b33", "black": "#1d1507", "red": "#fb7185", "green": "#a3e635", "yellow": "#fbbf24", "blue": "#7dd3fc", "magenta": "#f0abfc", "cyan": "#5eead4", "white": "#ffe6b0", "brightBlack": "#8a7038", "brightRed": "#fda4af", "brightGreen": "#bef264", "brightYellow": "#fde68a", "brightBlue": "#bae6fd", "brightMagenta": "#f5d0fe", "brightCyan": "#99f6e4", "brightWhite": "#fff7e6"},
      "light":{"background": "#fbfdff", "foreground": "#152238", "cursor": "#0369a1", "selectionBackground": "#0369a133", "black": "#152238", "red": "#be123c", "green": "#15803d", "yellow": "#a16207", "blue": "#1d4ed8", "magenta": "#7e22ce", "cyan": "#0e7490", "white": "#e2e8f0", "brightBlack": "#64748b", "brightRed": "#e11d48", "brightGreen": "#16a34a", "brightYellow": "#ca8a04", "brightBlue": "#2563eb", "brightMagenta": "#9333ea", "brightCyan": "#0891b2", "brightWhite": "#0f172a"}
  };

  /* Colores para la miniatura del selector. */
  var PREVIEW = {
      "abyss":{bg:"#090d14",panel:"#0e1520",stroke:"#243244",accent:"#38bdf8",muted:"#8b9caf",text:"#e5edf7"},
      "catppuccin":{bg:"#11111b",panel:"#181825",stroke:"#45475a",accent:"#cba6f7",muted:"#a6adc8",text:"#cdd6f4"},
      "tokyo":{bg:"#10121c",panel:"#1a1b26",stroke:"#343b58",accent:"#7aa2f7",muted:"#7f8cb0",text:"#c0caf5"},
      "dracula":{bg:"#1b1c26",panel:"#22232e",stroke:"#3d4053",accent:"#bd93f9",muted:"#9aa0b5",text:"#f8f8f2"},
      "nord":{bg:"#242933",panel:"#2e3440",stroke:"#4c566a",accent:"#88c0d0",muted:"#a3adc2",text:"#e5e9f0"},
      "gruvbox":{bg:"#1d2021",panel:"#282828",stroke:"#504945",accent:"#fabd2f",muted:"#a89984",text:"#ebdbb2"},
      "onedark":{bg:"#21252b",panel:"#282c34",stroke:"#3e4451",accent:"#61afef",muted:"#8b93a3",text:"#dcdfe4"},
      "solarized":{bg:"#00212b",panel:"#002b36",stroke:"#0f4a56",accent:"#2aa198",muted:"#93a1a1",text:"#eee8d5"},
      "monokai":{bg:"#1e1f1c",panel:"#272822",stroke:"#4d4e44",accent:"#a6e22e",muted:"#a6a68a",text:"#f8f8f2"},
      "rosepine":{bg:"#16141f",panel:"#1f1d2e",stroke:"#403d52",accent:"#ebbcba",muted:"#9d9ab5",text:"#e0def4"},
      "matrix":{bg:"#040b06",panel:"#07130b",stroke:"#1c4a2c",accent:"#22c55e",muted:"#6fbf85",text:"#c7ffd0"},
      "amber":{bg:"#140f04",panel:"#1d1507",stroke:"#4a3512",accent:"#f59e0b",muted:"#c2a05a",text:"#ffe6b0"},
      "light":{bg:"#eef2f7",panel:"#ffffff",stroke:"#c3cedb",accent:"#0369a1",muted:"#5b6b80",text:"#152238"}
  };

  function byId(id) { for (var i = 0; i < THEMES.length; i++) { if (THEMES[i].id === id) return THEMES[i]; } return null; }

  function current() {
    try {
      var saved = localStorage.getItem(STORAGE_KEY);
      if (byId(saved)) return saved;
    } catch (e) { /* almacenamiento no disponible */ }
    return DEFAULT;
  }

  function apply(id, silent) {
    var theme = byId(id) || byId(DEFAULT);
    document.documentElement.setAttribute('data-theme', theme.id);
    document.documentElement.style.colorScheme = theme.mode === 'light' ? 'light' : 'dark';
    try { localStorage.setItem(STORAGE_KEY, theme.id); } catch (e) { /* ignore */ }
    paintPicker();
    window.dispatchEvent(new CustomEvent('sisper:theme-changed', { detail: { theme: theme.id } }));
    if (!silent) {
      try { window.dispatchEvent(new CustomEvent('sisper:theme-applied', { detail: { label: theme.label } })); } catch (e) {}
    }
  }

  function termTheme() { return TERM[current()] || TERM[DEFAULT]; }

  function paintPicker() {
    var grid = document.getElementById('themePickerGrid');
    if (!grid) return;
    var active = current();
    var html = '';
    for (var i = 0; i < THEMES.length; i++) {
      var t = THEMES[i], p = PREVIEW[t.id] || {};
      html += '<button type="button" class="theme-card' + (t.id === active ? ' is-active' : '') + '"' +
              ' data-theme-id="' + t.id + '" title="Aplicar tema ' + t.label + '"' +
              ' style="background:' + p.panel + ';border-color:' + (t.id === active ? p.accent : p.stroke) + ';">' +
                '<span class="theme-preview" style="background:' + p.bg + ';border-color:' + p.stroke + ';">' +
                  '<span class="tp-head" style="background:' + p.panel + ';"><i style="background:' + p.accent + ';"></i></span>' +
                  '<span class="tp-line" style="background:' + p.muted + ';width:78%;"></span>' +
                  '<span class="tp-line" style="background:' + p.accent + ';width:58%;"></span>' +
                  '<span class="tp-line" style="background:' + p.muted + ';width:68%;"></span>' +
                '</span>' +
                '<span class="theme-name" style="color:' + p.text + ';">' + t.label + '</span>' +
                '<span class="theme-check" style="color:' + p.accent + ';">&#10003;</span>' +
              '</button>';
    }
    grid.innerHTML = html;
    var cards = grid.querySelectorAll('.theme-card');
    for (var j = 0; j < cards.length; j++) {
      cards[j].addEventListener('click', function () { apply(this.getAttribute('data-theme-id')); });
    }
  }

  function openSettings() {
    var m = document.getElementById('settingsModal');
    if (!m) return;
    paintPicker();
    m.style.display = 'flex';
  }

  function closeSettings() {
    var m = document.getElementById('settingsModal');
    if (m) m.style.display = 'none';
  }

  /* Aplicar antes del primer pintado para evitar parpadeo. */
  apply(current(), true);

  /* El muro se puede abrir en otra ventana ("⧉ Ventana"), que comparte
     localStorage pero NO recibe el cambio de tema: al cambiar la apariencia en
     una, la otra se quedaba con el tema anterior.  El evento `storage` lo emite
     el navegador justo en las demás ventanas del mismo origen.  No se usa
     `apply()` para no reescribir localStorage y evitar ping-pong entre ventanas. */
  window.addEventListener('storage', function (ev) {
    if (ev.key !== STORAGE_KEY) return;
    var theme = byId(ev.newValue) || byId(DEFAULT);
    document.documentElement.setAttribute('data-theme', theme.id);
    document.documentElement.style.colorScheme = theme.mode === 'light' ? 'light' : 'dark';
    paintPicker();
    window.dispatchEvent(new CustomEvent('sisper:theme-changed', { detail: { theme: theme.id } }));
  });

  document.addEventListener('DOMContentLoaded', function () {
    paintPicker();
    window.addEventListener('sisper:theme-applied', function (ev) {
      if (typeof window.showToast === 'function') window.showToast('🎨 Tema aplicado: ' + ev.detail.label);
    });
  });

  window.SisperTheme = {
    list: THEMES,
    current: current,
    apply: apply,
    termTheme: termTheme,
    openSettings: openSettings,
    closeSettings: closeSettings
  };
})();
