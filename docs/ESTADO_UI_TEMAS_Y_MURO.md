# Estado: temas globales + muro "Servicios y Consolas"

Documento de traspaso. Última actualización: commits `e870e92` (foco visible de teclado)
y `3a13849` (frescura de tráfico por consola).
Se puede retomar el trabajo leyendo sólo este archivo.

---

## 1. Objetivo de este bloque de trabajo

Dos cosas, en este orden:

1. **Replicar 1:1 el laboratorio** `static/lab_terminales_30.html` en la pestaña
   **Servicios y Consolas**, dejando de ser un demo y pasando a ser funcional con
   la aplicación real.
2. **Unificar el estilo de toda la app** con el lenguaje visual del laboratorio y
   un **selector de temas en Configuración** que se aplique a toda la aplicación.

Restricciones dadas por el usuario:
- Trabajar **directo sobre `main`**, sin perder funcionalidades existentes
  (salvo las que pidió quitar explícitamente).
- La pestaña "Servicios y Consolas" **se reemplaza completa**.
- Sin barra lateral de servicios en el muro.
- No inventar funcionalidad nueva no pedida.

---

## 2. Cómo se ejecuta y se verifica

| Cosa | Valor |
|---|---|
| App | `python3 dashboard.py` → `devconsole/server.py:main()` |
| URL | http://127.0.0.1:9099 |
| Servicio | `systemctl --user status sisper-dashboard.service` |
| Backend de terminales | drop-in con `SISPER_TERMINAL_BACKEND=tmux` |
| Lanzador | `~/.local/share/applications/sisper-devconsole.desktop` |

**Reglas de recarga**
- Cambios en `static/` (HTML/CSS/JS): basta **recargar la página**
  (el server manda `Cache-Control: no-store`).
- Cambios en Python (`devconsole/**`): **reiniciar**:
  ```bash
  systemctl --user restart sisper-dashboard.service
  ```
- La CSP prohíbe CDN externo: nada de `<script src="https://...">`.
  (`handlers.py` ~L138.)

**Verificación automatizada** (Chromium headless + CDP, sin dependencias: Node 22
trae `WebSocket` global):
```bash
cd /home/proteo/Documentos/Develop

node desktop/tools/cdp/sisper-fase3-smoke.mjs           # 8 vistas, logs: []
node desktop/tools/cdp/sisper-fase3-test-modals.mjs    # 22 modales, logs: []
node desktop/tools/cdp/sisper-fase4-freshness.mjs      # indicador de frescura
node desktop/tools/cdp/sisper-fase4-focus.mjs          # foco visible en 13 temas
node desktop/tools/cdp/sisper-fase4-console-liveness.mjs  # las consolas SÍ se repintan
node desktop/tools/cdp/sisper-fase4-capture-focus.mjs  # capturas de evidencia
```
`sisper-fase4-console-liveness.mjs` lanza un **GET inocuo** (solo lectura) a un
backend vivo y comprueba que la línea llega al DOM; es la prueba de regresión
del fallo de congelación de §3.7. Se puede apuntar a otro servicio con
`SISPER_PROBE_SVC` y `SISPER_PROBE_URL`.
`desktop/tools/cdp/lib/cdp.mjs` es el cliente compartido: arranca Chromium, conecta
por WebSocket al target de página y expone `evaluate`, `screenshot`, `logs` y
`contrastRatio`. Los verificadores miden el DOM con `Runtime.evaluate` y
`returnByValue`, y cada uno termina con `exitCode = 1` si algo falla, así que
sirven tal cual en un `&&` de CI. Es la forma más rápida de comprobar sin tocar
datos ni emitir peticiones que muten estado.

> Los verificadores **regeneran las capturas** de `docs/capturas-fase3/` y
> `docs/capturas-fase4/`. Si no quieres ruido en `git status` tras correrlos:
> `git checkout -- docs/capturas-fase3 docs/capturas-fase4`.

> Políticas vigentes: **base de datos solo lectura** (prohibido POST que mute
> estado en microservicios/DB) y **red restringida** a `localhost`,
> `172.23.22.0/24` y `172.30.23.71`. Los botones de servicio del muro se probaron
> **interceptando `fetch`**, nunca ejecutando la acción real.

---

## 3. Estado actual

### 3.1 Sistema de temas (Fase 1 — hecho)

- **13 temas**: `abyss` (por defecto), `catppuccin`, `tokyo`, `dracula`, `nord`,
  `gruvbox`, `onedark`, `solarized`, `monokai`, `rosepine`, `matrix`, `amber`,
  `light` (claro).
- Se eligen en **🎨 Configuración** (pie de la barra lateral) → modal
  `#settingsModal` con `#themePickerGrid`.
- Se aplican **antes del primer pintado** como `data-theme` en `<html>`.
- Persisten en `localStorage['sisper_theme']`.
- API: `window.SisperTheme = { list, current, apply(key), termTheme(), openSettings(), closeSettings() }`;
  emite el evento `sisper:theme-applied`.

Archivos:
- `static/css/themes.css` — escalas (`--radius-*`, `--space-*`, `--fs-*`, `--z-*`,
  `--edge`, `--focus-ring`) + los 13 bloques `[data-theme="KEY"]` + estilos del
  selector. Cada tema define superficies, acento, semánticos, texto, entorno,
  consola, sombras y 5 tokens añadidos en Fase 2:
  `--on-accent`, `--surface-sunken`, `--border-soft`, `--border-strong`,
  `--overlay-scrim`.
- `static/js/theme.js` — lógica del selector y persistencia.

### 3.2 Fase 2: tokenización de toda la app (hecho)

Los colores fijos de `dashboard.css` e `index.html` se reemplazaron por tokens.

| Archivo | hex antes | hex después | rgba antes | rgba después |
|---|---|---|---|---|
| `static/css/dashboard.css` | 282 | **7** | 327 | **66** |
| `static/index.html` | 346 | **99** | 105 | **81** |

- Lo que queda en CSS son `rgba(0,0,0,...)` de sombras y los `#...` dentro de
  `:root` (definiciones de token): correcto.
- Lo que queda en HTML son **colores de marca de tecnologías** (React `#61DAFB`,
  Kubernetes `#326CE5`, Docker `#2496ED`, Python `#FFE873`, Django `#44B78B`,
  Git `#F05032`, Node `#8DD6F9`, Redis `#94C83D`, Nginx `#37814A`, Postgres…) que
  **deben conservarse**.
- Los alfas de acento/estado pasaron a `color-mix(in srgb, var(--accent) N%, transparent)`
  para que cualquier tema herede sus matices.
- Verificado con capturas en `light`, `abyss` y `nord` sobre: Microservicios,
  Servicios y Consolas, Workspace, Kubernetes, Infraestructura, Mapa Operativo,
  Actividad y los modales (Configuración, Layout Studio). **Sin errores JS.**

### 3.3 Pestaña "Servicios y Consolas" (hecho)

Reemplazada completa por el muro del laboratorio, con datos reales (31 servicios).

**Qué muestra**
- Una tarjeta por **todos** los servicios del catálogo (31). Los que no tienen
  salida muestran `(Sin salida capturada todavía)`.
- Anatomía del laboratorio: LED de estado, nombre, puerto, menú `⋯`, salida con
  colores por tipo de línea, y pie con nombre + `LIVE/DETENIDO` + runtime.
- Rejilla de **2 a 8 columnas** (por defecto **6**), densidad, y líneas DOM
  (no xterm) para permitir resaltado de búsqueda y buen rendimiento.

**Barra del muro** (`#consoleWallToolbar`)
`COLUMNAS` · `DENSIDAD` · `LETRA A−/A+` · `ORDEN` (manual/nombre/nombre↓/puerto/tipo) ·
`◎ Enfoque` (con contador) · chips globales `ERROR WARN INFO GET POST PUT DELETE Todo` ·
`Buscar microservicio…` · `Solo errores` · `LÍNEAS` (50/100/200/500) · `Seguir` ·
`↔ Ajustar` · `⧉ Ventana` · `Ⅱ Pausar` · `↺ Reiniciar vista`.

**Por consola** (menú `⋯`): buscar con resaltado + contador + ↑↓, solo errores,
▶ Iniciar · ⏹ Parar · ↻ Reiniciar servicio, ◎ Añadir a Enfoque, ⛶ Maximizar,
⌫ Limpiar salida, A−/A+ y los filtros de línea con su propia selección.

**Modo Enfoque 1/2/3**: capa `#consoleFocusLayer` con plantillas
*automática / columnas / filas / 1 grande + 2*, acople y botón para volver.

**Otras interacciones**
- **Arrastrar la cabecera** de una tarjeta sobre otra para reordenar
  (se guarda como orden manual; el reordenado usa `order` de CSS para **no mover
  nodos con xterm dentro**).
- **La rueda desplaza el muro**; sólo desplaza una consola si antes haces **clic**
  en ella (se resalta). Esto resolvió la queja "el scroll me mueve las consolas".
- `⧉ Ventana` abre `/?tab=consoles&wall=1` (sin barra lateral ni topbar) para un
  segundo monitor, con guarda anti-bucle.
- Todo el estado (columnas, densidad, orden, filtros, fuentes, enfoque, pausa,
  líneas, selección) persiste en `localStorage['sisper_console_workspace']`.

**Qué se quitó a propósito** (pedido por el usuario)
- Barra lateral de servicios del muro (queda **oculta por CSS**, con los nodos en
  el DOM para no romper `renderConsoleSidebarServices`).
- Encabezado del escenario y conmutador de vista: el muro queda fijo en
  **mosaico plano**.
- Botón `⋯ Más` y su menú (vista, organización, Tilix, limpiar, mostrar todas).
- `Tomar control (xterm)` y `Cerrar consola` del menú de cada tarjeta.
  El código de modo control **sigue existiendo pero dormido** (sin entrada en la UI).
- "Copiar última línea" (sesión anterior).

**Backend tocado** (mínimo y aditivo)
- `devconsole/services/terminal/tmux_backend.py`: nueva acción **`stop-single`**
  (detiene **un** servicio; `stop` detenía todos) y su registro en `ACTIONS`.
- `devconsole/api/handlers.py`: rama `stop-single` en `/api/action`.
- Motivo: "Parar servicio" del muro llamaba a `stopSingleService()`, **función
  que no existía** → no hacía nada. Ahora el frontend llama a la acción real y
  **revisa la respuesta del servidor** (antes los fallos eran silenciosos).

### 3.4 Fase 3: Unificación visual de componentes y modales (hecho)

Se unificó el lenguaje visual del resto de las 7 vistas y de los 22 modales para adoptar de forma homogénea la estética técnica de consola del laboratorio:

1. **Microservicios (`#tab-services`)**:
   - Tarjetas `.svc-card` y filas `.svc-list-row` redibujadas con la anatomía del muro: cabecera con LED de estado, nombre en monospace (`var(--font-mono)`), puerto `:XXXX`, chip de estado sutil, métricas (`PID`, `Memoria`) y botones compactos `.btn-card-action` estilizados con tokens de temas.
   - Barra superior "LANZAR TILIX" (`.btn-bar`) y ribbon de KPIs (`.kpi-ribbon`) rediseñados sin gradientes cyber pesados, usando bordes limpios y fondos sutiles.
   - Filtros por categoría y estado (`.filter-card`, `.chip`) alineados al estilo del muro.

2. **Workspace y Kubernetes (`#tab-workspace`, `#tab-k8s`, `#tab-deployments`)**:
   - Tablas `.table-card` con cabeceras `th` y celdas `td` de alta densidad, bordes suaves `var(--card-border)` y tipografía técnica.
   - Badges de estado unificados (`.badge-pill`, `.svc-build-pill`, `.k8s-pod-badge`) y botones de filtro `.k8s-filter-btn.active`.
   - Botones de acción contextuales en tablas integrados con `.btn` unificado.

3. **Infraestructura y Mapa Operativo (`#tab-infra`, `#tab-map`)**:
   - Paneles `.panel-box`, cuadrículas `.control-grid` y tarjetas de variables/contenedores con fondos `var(--card-bg-solid)` y bordes sutiles.
   - Mapa táctico `.map-tactical-panel`, panel de detalle de zonas `.zone-detail-panel` y tabla de repartición `.reparticion-table` con estilo técnico consistente y badges de estado limpios.

4. **Actividad (`#tab-activity`)**:
   - Consola de diagnóstico y comandos `.cmd-console-box` con fondo `var(--console-bg)`, tipografía monospace y entrada de comandos con borde de enfoque reactivo.
   - Tarjetas de usuarios y auditoría `#activityUsersGrid`, `.activity-user-card` y KPIs `#activityKpiRow` integrados con las variables temáticas.

5. **Modales (22 modales de la aplicación)**:
   - Estructura consistente en los 22 modales: `.modal-header` con borde inferior sutil, `.modal-title` en negrita con icono, `.modal-close` compacto, y `.modal-actions` / `.modal-footer` al ras con fondo `var(--surface-elevated)`.
   - Padding automático de `14px 18px` para modales sin contenedor envolvente mediante `.modal > :not(.modal-header):not(.modal-actions):not(.modal-footer)`, preservando modales de terminal a pantalla completa (`padding: 0`).
   - Formularios, selects, textareas e inputs estandarizados con `background: var(--surface-base)` y `border: 1px solid var(--border-soft)`.

6. **Limpieza y Botones Universales**:
   - Botones consolidados: `button, .btn, .cw-btn` unificados con `var(--surface-elevated)`, borde `var(--card-border)`, hover interactivo suave con `color-mix`, focus visible con `var(--focus-ring)` y estado `:disabled`.
   - Eliminación de gradientes rígidos cyber legados (`.btn-hero`, `.btn-dev`, `.btn-test`, `.btn-main`, `.btn-intranet`, etc.).
   - Eliminación de `!important` innecesarios en `.btn-pull-alert` y `.svc-dropdown-menu`.
   - Eliminación de CSS muerto del modo agrupado antiguo (`.console-grouped-view`, `.console-group-*`).

**Verificación Automatizada**:
- 8 vistas y 22 modales verificados con Chromium headless + CDP sobre Node 22 (`sisper-fase3-smoke.mjs`, `sisper-fase3-test-modals.mjs`).
- Cero errores en consola de JavaScript (`logs: []`).
- Capturas de verificación almacenadas en `docs/capturas-fase3/` cubriendo los temas `abyss` (oscuro por defecto), `light` (claro) y `nord` (azul nórdico).

### 3.5 Fase 4: frescura de tráfico por consola (hecho)

Cada tarjeta del muro muestra en su pie **cuánto hace que recibió su última
línea**, para delatar de un vistazo los microservicios en reposo.

- **Etiqueta**: `hace 15s` → `hace 2m` → `hace 3h` → `hace 2d`, o **`sin tráfico`**
  cuando no hay ninguna línea registrada. Se refresca con el reloj del muro (1/s).
- **Estados visuales** (clases en `.cw-foot-fresh`): `is-fresh` (<60 s, tenue),
  `is-idle` (60–300 s, un punto más marcado), `is-stale` (**≥5 min en `--warn`**,
  la señal de "esto lleva rato parado") y `is-silent` (`sin tráfico`, cursiva tenue).
- **Origen del dato**: `LiveConsoleItem.last_line_ts` en el broker. **No** se usa
  `last_seen_ts`, que se refresca en cada sondeo aunque no haya tráfico y por
  tanto no sirve como señal. La marca viaja en `to_dict()` (sondeo/instantánea) y
  en cada delta SSE, así que al recargar la página se ve "en reposo hace 20m" y no
  un falso "hace 0s".
- **Reloj**: la antigüedad se calcula con el reloj *del servidor*, con el desfase
  calibrado a partir de los `timestamp` de instantánea y sondeo. Así sigue siendo
  correcta aunque la consola se abra desde otra máquina (la calibración se rehace
  en cada sondeo, cada 3 s).
- **Prioridad del pie en rejillas densas**: con 7 u 8 columnas la etiqueta de
  runtime cede su sitio, y a 8 columnas el estado se reduce a su LED. El nombre
  nunca baja de `3.5em` y el pie tiene `overflow: hidden` como red de seguridad.

**Semántica que hay que conocer**: `last_line_ts` sólo se actualiza cuando el
buffer crece de verdad. Al arrancar el broker, la primera captura de tmux de cada
sesión viva cuenta como crecimiento (aún no tiene línea base), así que **justo
después de reiniciar el servicio todos los servicios con sesión aparecen frescos**
y luego divergen. Los que no tienen sesión se quedan en `sin tráfico`.

### 3.6 Fase 4: foco visible de teclado en los 13 temas (hecho)

`--focus-ring` estaba definido como un valor de **box-shadow**
(`0 0 0 2px var(--accent-subtle)`) y se usaba como **color de outline** en
`button:focus-visible`. La declaración completa se descartaba y, en la práctica,
**no había anillo de foco en ningún tema**.

- `--focus-ring` pasa a ser un **color**: el acento del tema, el token con mejor
  contraste garantizado en las 13 paletas.
- Bloque único de `:focus-visible` para botones, `.btn`, `.cw-btn`, enlaces,
  `[role="button"]`, `[tabindex]` e `input`/`select`/`textarea`, **incluidos los
  modales** (sus reglas `outline: none` tenían más especificidad) y el buscador
  del muro (`.cw-search input`).
- Medido con `sisper-fase4-focus.mjs`: 78 muestras (6 objetivos × 13 temas),
  contraste mínimo **3.32:1** (WCAG 1.4.11 pide ≥3:1), `logs: []`.
  El verificador incluye un **control de regresión** que reinyecta el valor
  antiguo del token y comprueba que el anillo desaparece (`outline-style: none`).

### 3.7 Fase 4: vivacidad de las consolas (bug de congelación, corregido)

Síntoma reportado: *"las consolas tienen mucho desfase, no sé si están en vivo
o pegadas"*. **Estaban pegadas**, y no era el stream.

Medido con CDP: el `EventSource` recibía `delta_batch`, el backend crecía
(417 → 423 líneas) y el DOM se quedaba clavado en `renderKey: "200||||false"`.

- **Causa**: `linesForPanel()` recorta siempre a `tailLines` (200), y el
  `renderKey` se construía con `lines[lines.length - 1]`. En una captura de tmux
  la última línea es **una línea vacía**, así que la clave era constante y la
  guarda `if (panel.dataset.renderKey === renderKey && !options.force) return`
  descartaba todos los repintados. Afectaba a toda consola con más de 200 líneas
  y cola en blanco (lo normal). La lógica venía de `e483aa6`, anterior a Fase 4.
- **Arreglo**:
  1. Revisión monotónica por consola (`revMap`) que sube sólo cuando el contenido
     cambia de verdad (delta con líneas, o `last_line_ts` nuevo en el sondeo) y
     entra en el `renderKey`.
  2. Guarda barata **antes** de construir el HTML: el sondeo cada 3 s marcaba
     "sucio" a los 31 paneles y se reconstruían 200 líneas por panel sin que nada
     hubiera cambiado.
  3. Presupuesto de repintado por consola (`WALL_PAINT_MS = 400`, ~2,5 Hz):
     un repintado completo cuesta **57-130 ms** medidos, y pintar a la frecuencia
     del broker (8 Hz) saturaba el hilo principal. Un temporizador garantiza que
     la última línea nunca se pierde.
- **Resultado medido**: latencia extremo a extremo GET → tmux → broker (120 ms) →
  SSE → DOM de **235-527 ms**, el `renderKey` avanza y la suite queda en verde.
- **Pendiente de rendimiento**: el repintado sigue reconstruyendo las 200 líneas.
  La optimización de fondo es **append incremental** (añadir sólo las líneas
  nuevas y recortar las viejas), que bajaría el coste de O(200) a O(nuevas).
  No se hizo aquí por el riesgo sobre búsqueda/filtros/anclaje.

**Segunda causa, en el backend** (la que afecta a servicios con horas de vida):
`capture-pane -S -max_lines` (1000) devuelve una **ventana**, no un contador.
Cuando el historial del panel la supera (`history_size` medido: 1596), el número
de líneas capturadas se queda clavado en ~1050 aunque el servicio siga
escribiendo, así que `curr_count > prev_count` es siempre falso y **el broker
dejaba de emitir deltas para siempre**. Comprobado con un `EventSource` propio en
la página: `{snapshot: 1, deltas: 0}` mientras el servicio seguía registrando
peticiones. Arreglado en `live_broker.py`: cuando el conteo no crece, las líneas
nuevas se detectan **por solape** con la captura anterior (ancla de las últimas
10 líneas, búsqueda acotada a 400 posiciones); si no hay solape se emite un
`reset` para re-sincronizar. Verificado contra un servicio saturado real:
actualiza en 847 ms.

> **Trampa relacionada (heurística de estado)**: el broker marca `FAILED` si ve
> un patrón de error en las últimas 15 líneas capturadas. Una petición con
> `Host` no permitido hace que Django registre un traceback `DisallowedHost`, y
> eso deja el servicio marcado **FAILED durante mucho rato aunque esté sano**
> (hasta que 15 líneas nuevas empujen el traceback fuera de la ventana). Por eso
> las sondas deben ir con `Host: localhost` (404 limpio), no con el `fetch` del
> navegador a `127.0.0.1:<puerto>`.

### 3.8 Fase 4: correcciones del lote reportado por el usuario

Seis fallos reales, todos con causa identificada y verificados con CDP.

| # | Síntoma | Causa | Arreglo |
|---|---|---|---|
| 1 | No se leían los nombres en **Microservicios** | Los 31 nombres comparten el prefijo `ms_sisper_`/`mf_sisper_`; con elipsis el recorte caía siempre en el mismo punto, y envolver el nombre completo (primer intento) agrandaba la tarjeta y no arreglaba la lectura | La cabecera toma el estilo de una consola: **una línea monoespaciada** y el nombre **sin el prefijo común** (se lee `promocion_desempeno`), con el nombre completo en el `title`. Puerto en mono tenue, como `.console-panel-port` (ver §3.9) |
| 2 | «Sin upstream» no se entendía | Jerga de git | Pasa a **«Sin remoto»** con tooltip explícito (tarjeta, lista y tabla del modal) |
| 3 | «Lanzar Consumer (RabbitMQ)» y workers no hacían nada | `classify(servicio, aux_type=…)` caía en el resolutor de procesos, veía el proceso **del propio servicio** ocupando el puerto y devolvía `LEGACY_RUNNING`, que `blocks_launch` considera bloqueante | Sin sesión auxiliar, la clasificación de un auxiliar es `STOPPED`: una consola auxiliar es *adicional* al servicio (verificado: `STOPPED`, `bloquea=False`) |
| 4 | Al iniciar un microservicio no aparecía en el muro | `entrandoAlMuro()` actualizaba la barra lateral pero no repintaba el escenario; y «Iniciar» no llamaba a `fetchStatus()` (sólo reiniciar/parar) | Repinta el escenario al aparecer servicios, refresca el estado de las tarjetas y llama a `fetchStatus()` también al lanzar |
| 5 | «Pausa por scroll» se quedaba pegado | El manejador de `resume-follow` ocultaba la píldora y el botón «ir al final» pero **no el chip**; al reanudar el scroll ya está en el fondo, así que `onPanelScroll` no entra en ninguna rama | Oculta el chip (y restaura el estado del pie) al reanudar; además, los eventos de scroll de un repintado ya no desactivan el seguimiento (guarda de 150 ms) |
| 6 | El indicador parpadeaba entre `hace 0s` y la edad real | `touchPanelTraffic` calibraba el reloj con `last_line_ts`, que **no** es «ahora» (puede ser de hace 23 min), inyectando un desfase distinto en cada sondeo | El reloj sólo se calibra con `timestamp` (instantánea, sondeo o delta). Medido: 0 paneles parpadean y las etiquetas coinciden con el backend |

**Extra del mismo lote (backend)**: el ancla por solape del broker tomaba líneas
vacías del final de la captura de tmux; `''` coincide trivialmente con el final,
así que el solape se encontraba en la última posición y el broker concluía «no
hay nada nuevo» — consolas congeladas con la ventana saturada. Ahora se
descartan las líneas en blanco finales, el ancla es progresiva (10/6/3/1 líneas
y saltos de 0 a 3 desde el final) y un `reset` lleva hasta 200 líneas. Medido en
vivo: `line_count` de `adm_usuario` 66 → 72 → 78 → 84 → 90 con una petición por
segundo, monótono y sin resets.

### 3.9 Segunda ronda reportada: auxiliares en el muro y estilo de las tarjetas

**a) Las consolas auxiliares no aparecían en el muro.** El broker *sí* las
conoce: su catálogo traía `ms_sisper_tto_datos_privado_consumer` con
`service_type=auxiliary`, `category=consumer` y estado `RUNNING`. Pero
`entrandoAlMuro()` armaba la lista de tarjetas sólo con
`globalData.backend/frontend` (el catálogo de la configuración), donde una
auxiliar no existe, así que lanzar un RabbitMQ/Celery no se reflejaba nunca.

- `entrandoAlMuro()` une el catálogo del broker (`catalogMap`) con el base y
  **poda** las auxiliares que el broker ya no tiene (evita tarjetas fantasma);
  los servicios del catálogo base nunca se quitan.
- `brokerNames` se refresca con cada instantánea SSE y cada sondeo, y ambos
  llaman a `entrandoAlMuro()`: la tarjeta aparece sin esperar a otra acción.
- Al podar se limpian `focusList` y `maximizedService` si apuntaban a la
  auxiliar desaparecida.

Verificado: el muro pasa de 31 a 32 tarjetas e incluye la auxiliar con LED
`running`, `● LIVE` y su indicador de frescura.

**b) Estilo del nombre en las tarjetas.** El primer intento (envolver el nombre
completo) agrandaba la tarjeta y se leía peor. Ahora la cabecera copia la de una
consola: **una sola línea** monoespaciada (`600 11.5px var(--font-mono)`), el
nombre **sin el prefijo común** y el puerto en mono tenue, como
`.console-panel-port`. El nombre completo sigue en el `title` de la tarjeta y de
la fila de la vista Lista. Evidencia: `docs/capturas-fase4/`.

### 3.10 Tercera ronda: cancelar auxiliares, nombre completo y «Solo activas»

| Punto | Qué pasaba | Qué se hizo |
|---|---|---|
| No se podía **cancelar** un worker/rabbit | La sesión auxiliar se llama `sisper_aux_<servicio>_<tipo>` y sus metadatos apuntan al servicio **base**, pero el muro envía el nombre de la tarjeta (`ms_sisper_x_consumer`). `stop-single` buscaba `sisper_ms_sisper_x_consumer` (inexistente) y respondía «no tiene sesion tmux»; aun acertando, `stop_service` valida contra el nombre recibido y lo habría rechazado | `_find_session_any()` prueba la sesión directa, el nombre de sesión y el par (base, `aux_type`) de los metadatos; `stop-single` de una auxiliar se ejecuta como (base, `aux_type`). Verificado: encuentra la sesión y `validate_metadata` pasa |
| **Nombre de las tarjetas** | El nombre corto no gustó y envolver el completo agrandaba la tarjeta | Vuelve el **nombre completo** en una línea monoespaciada; para que quepa, el chip ACTIVO/APAGADO (que duplicaba el LED) se mueve a la fila media. Medido: 31 tarjetas, **0 recortes**, altura máx. 118 px |
| ¿Todas las consolas o **sólo las activas**? | El muro mostraba los 32 servicios del catálogo, la mayoría detenidos | Conmutador **«Solo activas»** en la barra (junto a «Solo errores»), persistido. Por defecto se sigue mostrando todo (como el laboratorio). El pie pasa a «N de M consolas activas» y, con el filtro puesto, un servicio recién arrancado entra solo. Medido: 32 → 21 visibles (los 21 RUNNING del backend) → 32 |
| «El **panel lateral** ya no existe» | Recordatorio de que se retiró | Confirmado: `console-wall.css:402` oculta `#consoleSidebar`, `#consoleSidebarRail` y sus botones con `display: none !important`. Nada del muro depende de él: la lista de tarjetas sale de `monitoredServices` (unión del catálogo base con el del broker). Además, `renderConsoleSidebarServices()` ya no pinta dentro de nodos ocultos (`offsetParent === null`) |

### 3.11 Cuarta ronda: evaluación completa, arreglos y optimizaciones

Se auditaron las tres capas (backend Python, frontend y hardcodeo/portabilidad) con medición, no con inspección. Lo más relevante:

**Lo que se midió**

| Medición | Valor | Lectura |
|---|---|---|
| CPU del hilo del broker | 369,9 s de usuario = **83 %** de la CPU del proceso | el muro de consolas era el consumidor nº 1 |
| Pasada de captura del broker | 1,39 MB / 9.967 líneas / 66 ms, 3,9 clientes tmux/s | a 8 Hz = ~55 % de un núcleo **sólo en captura** |
| `/api/status` | 0,12 s, 34 KB, cada 3 s | agrega git + puertos + entorno |
| `/api/services/wall` | **914 KB** por sondeo cada 3 s | ~18 MB/min de JSON redundante con el SSE |
| `/api/services/mosaic` (sin args) | 3,31 s | escaneo completo de `/proc` por servicio |
| `/api/activity/feed` | 1,75 s, cada 8 s | consulta a Bitácora |
| Página | 867 KB de JS | 383 KB eran `xterm.js` de un modo sin botón |
| `syncPanelVisibility` | **437 ms** en una pasada | lecturas de layout intercaladas con escrituras |
| Memoria | pico de cgroup 6,3 GB pero `VmHWM` del proceso **65 MB** | el pico es un high-water mark pegajoso del cgroup, no del heap |

**Lo que se arregló**

| Arreglo | Efecto verificado |
|---|---|
| El broker no sondea si no hay suscriptores SSE ni lectura reciente; cadencia 8 → 4 Hz; `timeout` de 5 s en la captura | **0 %** con el muro cerrado; **7,3 %** de un núcleo con el muro abierto |
| `get_env_info()` y `get_live_activity_data()` cacheados (5 s / 12 s) y sondeo del feed a 15 s | 1,75 s → **3 ms** en aciertos; Bitácora de 7,5 a 4 consultas/min |
| `xterm.js` bajo demanda | JS de 867 → **484 KB** (−44 %) |
| Sondeo del muro consciente del SSE (red de seguridad cada 30 s) | **20 → 2** peticiones/min de 914 KB |
| `syncPanelVisibility` en dos fases + soltar DOM fuera de pestaña | desaparece el reflow por panel y el repintado invisible |
| Cerrar SSE, reloj y sondeo al salir del muro | `readyState` cerrado, 0 paneles hidratados fuera de pestaña |
| `renderAllServices` sólo en su pestaña; etiquetas de botón sólo si cambian; `scheduleFrame` cancela su respaldo | 35 ms cada 3 s y ~370 mutaciones de botón por 8 s menos |
| XSS en el buscador de reparticiones + `escapeHtml` triplicado → una sola definición | probado en el navegador: ya no inyecta |
| `inspect_image_labels`: `created` no existía en la rama local (`NameError` tragado) | la imagen local se reporta (`podman-local`) en vez de pagar siempre 3,5 s de registry |
| Despacho HTTP envuelto + cotas del espejo de telemetría + iteración sobre copia | parámetro inválido → **400 con JSON** en vez de conexión cortada |

Suite completa **5/5** en verde tras el bloque, con `logs: []`.

### 3.12 Quinta ronda: pestaña «Sitio» y respuesta sobre xterm

**Pestaña «Sitio»** (sidebar ⚙️, entre Kubernetes y CI/CD & Ops), con selector de entorno y el aviso «Estás modificando: <ENTORNO>». Reúne lo que es configuración **por entorno**:

- **Carpeta de manifiestos (YAML)**: ruta vigente, explorador de carpetas (cada subcarpeta con su número de YAML) y «Usar esta carpeta» para fijarla. El guardado exige sesión y confirmación, escribe `config/services.json` con copia `.bak` y reemplazo atómico.
- **Inventario**: total de manifiestos, desglose por carpeta, esperados por el catálogo vs presentes, lista de los que faltan y los extras detectados. Medido aquí: develop **45** manifiestos, **27/31** esperados (faltan `carrera_correct_comp`, `firmador`, `replicate`, `tto_datos_privado`); test **38**, 26/31; extras `ingress`, `onlyoffice`, `keydb`, `ollama`, `grafana-proxy`, `prometheus-proxy`, `volumes`.
- **Tema estacional**, movido desde Kubernetes: ahora sigue el entorno elegido (antes dependía del selector de namespace de la pestaña de cluster).

Cambio de fondo: `config.k8s_dir_for(env)` lee la carpeta **en vivo** (``k8s_service`` importaba `ENVIRONMENTS` por valor, así que el cambio no surtía efecto hasta reiniciar). Los tres puntos que la usaban dejan además de tener la ruta escrita a mano.

Nuevos endpoints: `GET /api/site/config?env=`, `GET /api/site/browse?path=` y `POST /api/site/k8s_dir` (sólo metadatos: nunca contenido de ficheros; recorridos acotados y sin `node_modules`/`.git`/`__pycache__`).

**xterm: ¿optimiza recursos?** No. El muro no emula un terminal: lee `tmux capture-pane` y **ya convierte ANSI a HTML con color** (`ansiRegex`, `dashboard.js`). Añadir xterm daría más fidelidad (cursor, secuencias), pero costaría **más** recursos (una instancia + parser + bucle de render por consola, hasta 32) frente al render de texto acotado actual (200 líneas por panel, 18 de 32 paneles hidratados, broker en reposo sin público y 4 Hz con público). Y no daría interactividad en el navegador: el modo control exige `window.devconsoleTerminal`, un puente que **sólo inyecta la app de escritorio Electron**; en el navegador no existe. Para terminales interactivas de verdad falta un puente pty en el servidor (SSE/WebSocket + `tmux attach`), y debería ser opcional por consola (por ejemplo, sólo en Enfoque).

### 3.13 Sexta ronda: selección y construcción en Deployments, carpeta YAML y Sitio

**Deployments**

| Ajuste | Causa / solución |
|---|---|
| Al editar la versión YAML se **perdía la selección** | La selección vivía sólo en los checkboxes del DOM y `submitEditYamlVersion()` repinta la tabla al terminar. Ahora un `Set` (`deploySelection`) es la fuente de verdad y `updateDeploySelectedCount()` lo espeja en el DOM tras cada render. Verificado: 2 marcados → repintado → siguen 2, con contador y rótulo del botón. |
| Las imágenes se construían **de una en una** | `run_build_task` recorre los servicios con un `for` en un solo hilo. Ahora la selección lanza **una tarea por servicio** con `MAX_BUILD_PARALELO = 3` en vuelo (cada una con su consola inline; la UI ya seguía varias tareas). Verificado con `fetch` simulado: 6 servicios → 6 tareas, máximo 3 simultáneas (antes: 1 tarea con 6 en serie). |
| Modal de construcción pequeño | `#massiveBuildModal` pasa de 760 a **1180 px** de ancho y 92 vh de alto. |
| Faltaba botón de desplegar **seleccionados** | Los botones pasan a «🚀 Desplegar seleccionados (N)» y «🔄 Rollout seleccionados (N)», con contador vivo y deshabilitados si no hay nada marcado. `deploySelectedManifests()` y `rolloutSelectedDeployments()` leen del `Set` (no del DOM). |

**Sitio y carpeta de manifiestos YAML**

- La pestaña **«Sitio» pasa al grupo CI/CD & Ops** (es administración) y se queda **sólo con el tema estacional**; su selector se rotula «Entorno (tema)» y apunta a Deployments para la carpeta. Así desaparece el enredo de que cambiar de entorno moviera también la selección de carpeta.
- La **carpeta de manifiestos se configura en Deployments** con una tuerca «⚙️ Carpeta YAML», que abre un modal con explorador e inventario. El entorno que rige es el de la propia pestaña (`#deployEnvSelect`), y al guardar se repinta la matriz de versiones.
- **Bug corregido**: una carpeta con los YAML en subcarpetas (por ejemplo `k8s/`, que es justo la que interesa) salía como «no tiene YAML» y el botón quedaba deshabilitado, porque sólo se contaba el nivel superior. Ahora `browse` devuelve también el total recursivo: `k8s/` muestra «0 en este nivel · 143 en total» y se puede elegir. En el camino aparecen las carpetas hermanas con su recuento (`01_deploy_develop 45`, `02_deploy_test 38`, `03_deploy_prod 37`, `ci-cd 1`, `herramientas 22`).

### 3.14 Séptima ronda: elegir carpeta sin ambigüedad y Sitio con tarjetas

**Selección de la carpeta YAML (Deployments)**

El fallo de fondo era que **navegar y elegir eran la misma acción**: la carpeta que se iba a fijar era siempre la que estabas *mirando*, y como el explorador abría en la raíz del workspace y el conteo era recursivo, un padre cualquiera (`k8s/`, con 143 YAML debajo) parecía válido. Resultado: «escoge la que él quiere».

Ahora el criterio es el que usa el despliegue: `k8s_dir / k8s_file` (`backend/ms_sesion.yaml`), es decir **los manifiestos tienen que estar en ese mismo nivel**. `browse` devuelve, por carpeta y por subcarpeta, cuántos de los manifiestos del catálogo están ahí:

| Carpeta | Aciertos | Veredicto |
|---|---|---|
| `backend/config/k8s` | **0/31** | «ninguno de los 31 manifiestos está en este nivel — el despliegue los busca aquí mismo» → botón deshabilitado |
| `backend/config/k8s/01_deploy_develop` | **27/31** | «27 de 31 manifiestos del catálogo están aquí» → botón habilitado |
| `…/01_deploy_develop/backend` | **0/31** | demasiado profundo |

Además: el modal abre **ya explorando la carpeta vigente** (antes salía vacío y el primer clic apuntaba a la raíz), cada subcarpeta válida trae su botón **«✔ usar ésta»** que la fija sin entrar, y `set_k8s_dir` rechaza en el servidor una carpeta con 0 aciertos del catálogo.

**Interior de la pestaña «Sitio»**

Tenía un desplegable suelto como única herramienta. Ahora son **dos tarjetas** en una rejilla responsiva:

- **Tema estacional del sitio**: el selector «Aplicar a» *dentro* de la tarjeta, el tema vigente en una insignia y los controles (selector de tema + «Aplicar Tema») **visibles**, ya sin `<details>` plegado.
- **Carpeta de manifiestos YAML**: resumen de la carpeta vigente del entorno (`ruta`, `27/31 manifiestos del catálogo · 45 YAML · faltan 4`) y dos atajos: «🔎 Explorar YAML» (abre el explorador sin salir) y «⚙️ Configurar en Deployments», que lleva a la pestaña y abre la tuerca.

### 3.15 Octava ronda: Sitio sólo con el tema e inventario completo de YAML

**Sitio, sólo el tema.** La tarjeta «Carpeta de manifiestos YAML» sale de la pestaña: queda **una sola tarjeta** con el tema estacional (selector «Aplicar a», tema vigente y controles). La carpeta se sigue configurando en Deployments con la tuerca.

**Inventario: no se veían todos los YAML.** El payload de `/api/site/config` **ya traía los 45 ficheros**, pero el inventario sólo pintaba los recuentos, los que faltaban y unos «extras» filtrados por prefijo (`ingress`, `onlyoffice`, …), así que de 45 se veían ~11. Ahora se listan **todos**, agrupados por carpeta y plegables:

```
45 manifiestos en 4 carpeta(s)   27/31 DEL CATÁLOGO   [Filtrar por fichero o servicio...]
Faltan 4 del catálogo: backend/ms_sisper_carrera_correct_comp.yaml, …
▾ . (7)        grafana-proxy.yaml 0.2 KB EXTRA · ingress.yaml 11.5 KB EXTRA · …
▾ backend (20) ms_adm_usuarios.yaml 14.6 KB [MS_SISPER_ADM_USUARIO] · …
▾ frontend (16) · volumes (2)
```

Cada fichero lleva tamaño y etiqueta: **el servicio del catálogo** al que pertenece o **EXTRA** si no lo referencia ninguno. Incluye buscador que filtra sin repintar (conserva foco y scroll). `site_config` expone además `esperados` (servicio ↔ fichero) para poder etiquetarlos.

### 3.16 Novena ronda: explorador de carpetas, búsqueda del muro y orden en Sitio

| Ajuste | Causa | Arreglo |
|---|---|---|
| «Explorar» no dejaba cambiar de carpeta | El botón llamaba a `siteBrowseTo('')`, que resuelve a la **raíz del workspace**: te sacaba de donde estabas y allí no hay ninguna carpeta válida que elegir | «Explorar» abre la carpeta **vigente** (o la que estás mirando) y la raíz pasa a ser un botón aparte «🏠 Raíz» |
| No se reflejaban todos los ficheros | `browse` devolvía **sólo carpetas**, así que al entrar en una carpeta no se veían sus manifiestos; y el inventario tenía un scroll interno (`max-height:320px`) que ocultaba el resto | `browse` devuelve también los ficheros del nivel (nombre y tamaño) y el explorador los lista; el inventario pierde el scroll interno y desplaza el modal, así no queda nada escondido |
| Faltaba «x» para limpiar la búsqueda del muro | No existía | Botón «✕» junto al buscador, visible sólo con texto, que vacía el filtro y repinta (31 paneles tras limpiar) |
| Sitio: anidamiento confuso y títulos repetidos | Caja dentro de caja dentro de caja, con «Tema estacional del sitio» dos veces y los controles dispersos | Una tarjeta con orden numerado: **1 Entorno destino**, **2 Tema actual**, **3 Nuevo tema** (+ Aplicar). Los ids y el comportamiento (tema personalizado) se conservan |

**Regresión detectada y corregida.** Al reescribir el inventario en la ronda anterior, el recorte se llevó por delante `pintarVeredictoCarpeta`, que vivía entre `siteInventoryHtml` y `siteBrowseTo`. El explorador fallaba **en silencio** (la excepción se la tragaba el `try` de `siteBrowseTo` y sólo salía un toast), y por eso el panel aparecía vacío. Restaurada y verificada: el explorador pinta 4.694 bytes, con la carpeta a fijar y los 7 manifiestos de ese nivel. Lección aplicada: tras tocar un bloque, re-verificar **todo** el flujo, no sólo lo que se acaba de añadir.

### 3.17 Décima ronda: Sitio sin sub-tarjeta y árbol completo en el explorador

| Ajuste | Qué se hizo |
|---|---|
| «Tema del sitio» era una caja dentro de otra | La pestaña queda con **una sola tarjeta** «Configuración del Sitio»: cabecera (título, insignia del tema vigente, entorno) y debajo los pasos **1 Entorno destino · 2 Tema actual · 3 Nuevo tema · Aplicar**, sin sub-tarjeta ni título repetido |
| En la lista de selección sólo se veían `ms_*` y `mf_*` | La lista del explorador era **por nivel**: en `backend/` sólo aparecían los `ms_*` y en `frontend/` sólo los `mf_*`, de modo que nunca se veía el conjunto. Ahora el explorador lista **todo el árbol** de la carpeta explorada, agrupado por primera carpeta: `Todos los manifiestos de este árbol (45)` con `. (7)` —extras como `ingress`, `onlyoffice`, `keydb`—, `backend (20)`, `frontend (16)` y `volumes (2)`, cada uno con su ruta relativa y tamaño |

`browse` devuelve ahora `tree` (todo el árbol bajo la carpeta). Coste medido: la carpeta del entorno son 2 ms para 45 ficheros; la raíz del workspace, 2 s para 216 (caso poco frecuente, detrás del botón «🏠 Raíz»).

### 3.18 Undécima ronda: el modal de entorno sí abre Tilix, sin leyenda y con criterio de buildeo

| Ajuste | Hallazgo y arreglo |
|---|---|
| «Abrir Todo en Tilix ▸ Todo en DEVELOP/TEST/MAIN» no abría nada | Los botones del modal (`executeTilixOnly`, `executeAlignAndLaunch`) llamaban a `/api/action` **sin `getAuthHeaders()`** — la petición se rechazaba — y **sin `open_viewer`**, así que aunque pasara no se abría ventana. Ambos corregidos y ahora el resultado se muestra en el aviso. De paso: `/api/env/save` también iba sin credenciales (habría fallado al guardar el `.env`). |
| La leyenda `[sesion:ventana] título 14:26 15-oct-26` en las consolas | Es la **barra de estado de tmux** del cliente. El comando del panel pasa a `tmux set-option -t <sesión> status off ; attach-session -t <sesión>`: se apaga y se adjunta en el mismo comando. No afecta al muro (usa `capture-pane`, que no incluye la barra). |
| «Manifiesto de servicio (no referenciado por el catálogo)» | El catálogo **en vivo** tiene 31 servicios (descubrimiento + `config/services.json`). Un YAML es «de servicio» si su nombre coincide con el de un servicio quitando el token `sisper`: `ms_tto_datos_privado.yaml` ↔ `ms_sisper_tto_datos_privado`. Los que no coinciden con ninguno (`ms_versiones`, `mf_base`, `mf_pizarra`…) son manifiestos de servicios **que no están en el catálogo** (no hay repo ni Dockerfile). |
| ¿De qué depende que sea **buildeable**? | De tener **repo con `Dockerfile`**: la fila lo dice («servicio del catálogo: … (buildeable)» o el motivo) y muestra **🔨 Build** sólo en ese caso (hoy 2 de 18: `ms_sisper_carrera_correct_comp` y `ms_sisper_tto_datos_privado`). Todos, en cambio, se pueden **🚀 Desplegar** (`kubectl apply -f`) y **🔄 Rollout**. |

**Decisiones para las validaciones (puntos 6-7 del bloque anterior):**

- El flujo de trabajo es **pipenv**, no venv genérico: los comandos sugeridos son `pipenv install` / `pipenv install -r requirements.txt` y la comprobación de entorno se hace con `pipenv --venv` + **alineación del intérprete** (los virtualenvs viven en `~/.local/share/virtualenvs` y `scripts/venvs.sh check` ya audita justo el caso que rompió: `bin/python` apuntando a un intérprete sin las dependencias).
- Infra **imprescindible en local**: **keydb** y **onlyoffice**; en modo intranet se añaden **keycloak** y la **BD de bitácora**. El preflight debe exigir ese conjunto según el modo de entorno, no todo.

### 3.19 Duodécima ronda: comprobación previa y diagnóstico (puntos 6 y 7)

Ambas cosas viven en `devconsole/services/preflight_service.py` y son **de sólo lectura**: ninguna ejecuta el arreglo, sólo lo indican.

**Comprobación previa — «¿puedo lanzar?»** (`GET /api/preflight?services=`)

- **Infra según el modo**: en local exige **keydb + onlyoffice**; en intranet añade **keycloak + BD de bitácora** (decidido con el dueño). Modo vigente y host de BD salen de `get_env_info()`.
- **Por servicio**: directorio del repo, **`.env`**, entorno de **pipenv** (`Pipfile`, `Pipfile.lock`, virtualenv en `~/.local/share/virtualenvs` con el criterio de `scripts/venvs.sh`: intérprete real vs `site-packages`), `node_modules` en frontends y **puerto libre o suyo**.
- La interfaz la ejecuta **antes de lanzar** (`launchWithConflictCheck`): si hay bloqueantes muestra el modal con el comando de cada uno y decide el usuario («Lanzar igualmente» / «Cancelar»); si la comprobación falla por red, **no impide** lanzar. Botón suelto **🔍 Comprobar** en la barra de lanzamiento.
- Verificado: con OnlyOffice caído y dos servicios sin `.env`, el lanzamiento de `b1` queda **en 0 llamadas** hasta que el usuario decide.

**Diagnóstico — «¿por qué no arranca?»** (`GET /api/service/diagnose?service=`)

- Estado real en tmux (`classify`), salud del entorno de pipenv y **firmas en la consola**: `ModuleNotFoundError` → `pipenv install`; `Cannot find module`/`webpack: not found` → `npm install`; `ImproperlyConfigured`/`SECRET_KEY` → falta o está incompleto el `.env` (`cp .env.example .env`); `EADDRINUSE` → puerto ocupado; `could not connect`/`OperationalError` → dependencia caída; `Permission denied` → permisos.
- Estado que no arranca (`STOPPED`), sesión con panel muerto (`TMUX_STALE`), proceso fuera de tmux (`LEGACY_RUNNING`) y conflictos (`EXTERNAL_CONFLICT`/`AMBIGUOUS`) se explican aparte.
- En la tarjeta: menú ⋯ → **🩺 ¿Por qué no arranca?**. Probado con `ms_sisper_firmador`: detecta el `.env` ausente, su virtualenv de pipenv y muestra el comando exacto.

### 3.20 Decimotercera ronda: roles por pestaña, icono de Django y medidas del lag

**Roles.** `updateRoleUI` sólo ocultaba *Deployments*; ahora hay una tabla explícita (`ROL_PESTANAS`) y las etiquetas de sección que se quedan sin elementos también se ocultan:

| Rol | Pestañas visibles | Secciones |
|---|---|---|
| **Soporte / QA** (`viewer`) | Kubernetes · Mapa Operativo · Actividad | Monitoreo, Análisis |
| **Desarrollador** (`dev`) | Microservicios · Servicios y consolas · Workspace · Kubernetes · Infraestructura · Mapa Operativo · Actividad | Monitoreo, CI/CD & Ops, Análisis |
| **Admin / DevOps** | todas (añade Sitio y Deployments) | las tres |

Además el rol es una **credencial**: entrar como Desarrollador (o Admin) pide PIN (`verify_pin`); Soporte/QA no lo pide porque es de sólo lectura. Si la pestaña abierta deja de estar permitida, se cae a la primera permitida.

**Icono de Django.** Se dibuja sobre un *chip* con fondo y borde verdes (`rgba(68,183,139,.18)/.35`) y a 17 px en las tarjetas: el monograma ya no se pierde sobre el fondo oscuro.

**Medidas del lag** (pestaña Servicios y consolas, 1920×1080, 31 paneles):

| Medida | Valor |
|---|---|
| Long tasks al entrar al muro | 4 · peor **345 ms** · suma 891 ms |
| Nodos DOM / líneas pintadas | 8.011 / 987 |
| Paneles hidratados | 18 de 31 |
| Heap JS | 3 MB |
| CPU por grupo | Firefox **57 %**; servicios y webpack ~0 % |
| Carga media | 1,52 |

El tirón no está en el backend: está en el **render del muro** (repintado completo por panel en cada delta y una hidratación inicial en bloque). Candidatos medidos, por orden de impacto: (1) **append incremental** en `renderPanelBody` en vez de reemplazar `innerHTML`; (2) **hidratación por trozos** (el paso de 18 paneles es el que produce el tirón de ~345 ms); (3) construir el menú `.cw-menu` de cada panel sólo al abrirlo (~1.300 nodos y 713 botones); (4) bajar el sondeo de `/api/status` (34 KB cada 3 s) cuando la pestaña no está visible.

### 3.21 Decimocuarta ronda: Soporte/QA acotado, scroll de Tilix, ancho del muro y lag

| Ajuste | Qué se hizo |
|---|---|
| **Soporte / QA** veía demasiado | Se ocultan en ese rol la **cinta de KPIs** (`#kpiRibbon`: BE/FE/bajar/subir/sucios/hora), las **insignias de entorno** (`#globalEnvSwitcher`: DEVELOP/TEST/MAIN), el **selector de carpeta raíz** (`#baseDirPathBtn`) y el **Layout Studio de Tilix** del pie. Quedan sus tres pestañas (Kubernetes, Mapa, Actividad). |
| Opciones **básicas del clúster** para Soporte/QA | La detección no necesita configuración extra: el panel usa el mismo `kubectl`/kubeconfig del usuario. Lo que cambia es que las acciones que mutan (`restart`, `rollout`, `deploy`) quedan **deshabilitadas** (39 botones en la pestaña Kubernetes, todos apagados en ese rol); refrescar, cambiar de namespace, ver pods y ver logs siguen disponibles por ser de sólo lectura. |
| El scroll en Tilix escribía `[[A[[A[[A` | Los paneles del visor eran de escritura, así que la rueda (Tilix la traduce a flechas) llegaba al servicio como entrada y la disciplina de línea la repetía. El layout del visor pasa a `readOnly: True`: son consolas para **leer**. |
| Las consolas no usaban el ancho | **Encontrado**: con 6 columnas fijas cada panel medía **273 px** y las líneas largas se partían en dos (35 px de alto frente a 19). Ahora el muro usa **columnas automáticas** (`gridCols: 'auto'`) ajustadas al ancho: **4 columnas × 411 px** con todas las líneas a 19 px. Quien nunca eligió columnas a mano migra del 6 heredado; elegir a mano (`gridColsManual`) desactiva el ajuste. |
| Lag del muro | **Hidratación por trozos** (`HIDRATAR_POR_FRAME = 3` por frame) en vez de 18 paneles de golpe: el peor long task al entrar al muro baja de **345 ms a 150 ms** (medido, misma máquina y mismo muro). Pendiente de la lista: *append incremental* en `renderPanelBody` (el mayor ahorro restante), menú `.cw-menu` perezoso y espaciar `/api/status` con la pestaña oculta. |

### 3.22 Decimoquinta ronda: legibilidad del muro y destino de los lanzamientos

**Por qué las consolas «no usaban el espacio».**  No era el ancho del panel (el texto llegaba al borde) sino **cómo se partía**: `.console-line` tenía `word-break: break-word`, que equivale a `overflow-wrap: anywhere`, así que el navegador cortaba **dentro de las palabras** («accept ed», «develop ment server», «htt p s://docs.djangoproject.com»).  Ahora es `word-break: normal` + `overflow-wrap: break-word`: sólo se parte un token que no cabe solo.  Verificado con una línea real de 149 caracteres: **0 palabras partidas** (antes se partían varias).

Además el automático de columnas pasa de un mínimo de 340 px a **520 px** por consola: con 1920 de ancho son **3 columnas de 550 px** en vez de 4 de 408 px.  Un log de 149 caracteres ocupa 2 renglones cortando por espacios; con `COLUMNAS = 2` (830 px) caben ~130 caracteres por renglón y con `LETRA = 10 px` entra ~15 % más por fila.

**Destino de los lanzamientos (Tilix o sólo dashboard).**  Botón nuevo en la barra de lanzamiento: **`🖥️ Abrir en: Tilix` / `▦ Abrir en: Dashboard`** (se recuerda en `sisper_launch_destino`).  En modo Dashboard las sesiones tmux se crean igual y se ven en el muro, pero **no se abre ninguna ventana**.  El backend respeta `open_viewer` en `/api/action`, `/api/tilix/launch` y `/api/tilix/launch_selected*` (por defecto `true`, así que el comportamiento anterior no cambia).  Verificado interceptando las peticiones: mismo botón → `open_viewer: true` con Tilix y `open_viewer: false` con Dashboard.

### 3.23 Decimosexta ronda: filas enteras, botón de lanzamiento al dashboard y caché de estáticos

| Ajuste | Causa y arreglo |
|---|---|
| «Las consolas se ven cortadas» | La fila del muro se **estiraba** al alto disponible (`grid-auto-rows: minmax(190px, 1fr)` + `align-content: stretch`), así que el cuerpo quedaba en **14,5 líneas** y la última salía a medias. Ahora cada panel mide un **número entero de líneas**: `--cw-rows` lo fija el JS (cuerpo de ~200 px ⇒ 12 líneas a 11 px) y el CSS calcula el alto (`calc(rows * font-size * line-height + 62px)`); las filas ya no se estiran y el muro se desplaza en vertical. Medido: `filasExactas: 12`, `restoPx: 0`. |
| «El botón de abrir en Dashboard no funciona» | El conmutador **sí** cambiaba el destino (`open_viewer: true/false` verificado con clic real), pero no **lanzaba** nada: parecía muerto. Se añade el botón de acción **▦ Iniciar en Dashboard**, que fija el destino y lanza (seleccionados, o todos si no hay ninguno). El conmutador pasa a llamarse «🖥️/▦ Destino: …» para que se entienda que sólo cambia el modo. |
| Además | `index.html` se sirve con **`?v=<fecha>`** en CSS y JS (`_version_estaticos`): una copia vieja de `dashboard.js` en caché dejaba la interfaz a medias —síntoma exacto de «el botón nuevo no hace nada»—. |
| Verificadores | `frescura` fallaba con el laboratorio escribiendo: con tráfico activo ninguna tarjeta debe parecer inactiva (se omite esa expectativa si ≥80 % están frescas) y un servicio que **repite** la misma línea también rejuvenece la edad, así que «escribió» ahora también cuenta líneas nuevas. |

### 3.24 Decimoséptima ronda: consolas en negro con el pie en «LIVE»

**Síntoma** (captura del 15-oct 17:08): varios paneles con el cuerpo vacío mientras su pie
marcaba «hace 0s • LIVE» y el servicio seguía escribiendo.

**Causa**: la virtualización del muro. `dehydratePanel` **vacía el cuerpo** y `renderPanelBody`
hacía `return` si el panel no estaba hidratado, así que un panel que quedara deshidratado
**estando a la vista** ya no volvía a pintar nada: los datos llegaban (de ahí el pie en
«LIVE») pero el DOM se quedaba vacío.  El disparador es el desplazamiento: al moverse el
muro se recalculan visibilidades y un panel puede quedar deshidratado con rectángulos ya
obsoletos.

**Arreglo** (dos capas):

1. **Autocorrección en el camino de datos**: si llega una línea y el panel no está hidratado
   pero **sí está en pantalla** (`panelEstaEnPantalla`, con el margen de prefetch), se
   rehidrata ahí mismo en vez de descartar el pintado.
2. **Red de seguridad periódica** (2,5 s, sólo con la pestaña del muro activa): una pasada de
   `syncPanelVisibility()` recupera cualquier panel que haya quedado suelto, incluso si su
   servicio lleva un rato sin escribir.

**Verificado** en el panel en marcha reproduciendo el fallo a mano (deshidratar un panel
visible): con una línea nueva vuelve a 200 líneas e `hidratado: 1`, y con la pasada de
visibilidad también.  Suite CDP 5/5 y los cinco ficheros de tests OK.

### 3.25 Decimoctava ronda: selección de texto en el muro y crear/renombrar rama

| Ajuste | Causa y arreglo |
|---|---|
| Al maximizar una consola, la selección de texto se perdía o saltaba al bloque entero | El muro repinta cada panel como máximo cada **400 ms** (`WALL_PAINT_MS`) y el repintado **reemplaza el `innerHTML`** del cuerpo: eso destruye cualquier selección del DOM, y el `scrollToBottom` del seguimiento la remata.  Ahora `renderPanelBody` comprueba si hay **texto seleccionado dentro de ese cuerpo** (`haySeleccionEn`): si lo hay, **no repinta** (deja el búfer acumulando) y reintenta en 500 ms; además no fuerza el desplazamiento al fondo mientras haya selección.  Verificado: selección real en una consola, llega una línea nueva y **la selección sobrevive** (`seleccionSobrevive: true`). |
| Crear y renombrar rama desde la tarjeta | El modal de rama tenía sólo «Cambiar Rama».  Se añaden **➕ Crear** (`git checkout -b <nueva> [<base>]`) y **✏️ Renombrar** (`git branch -m <seleccionada> <nueva>`), con el mismo patrón que el cambio de rama: modal de comando, refresco del estado y consola recargada si el servicio está activo (sólo al crear, porque renombrar no cambia el contenido).  El nombre se valida con `git check-ref-format --branch` (rechaza espacios y caracteres prohibidos) y se comprueba que la rama no exista (o que la vieja sí exista).  Acciones nuevas: `create-branch` y `rename-branch` en `/api/action` (rol Desarrollador, igual que `checkout-branch`).  Verificado en un repo desechable de `/tmp`: crear, duplicada rechazada, renombrar, inexistente rechazada; y en la interfaz los dos envíos correctos. |

### 3.26 Decimonovena ronda: la selección (segundo intento) y quién hace el `git fetch`

| Ajuste | Detalle |
|---|---|
| La selección seguía perdiéndose | **Mi primer arreglo no cubría el camino real**: el delta del SSE repinta con `renderPanelBody(svc, {force: true})`, y la guarda sólo miraba los repintados *no* forzados, así que en la práctica no protegía nada.  Ahora la comprobación de selección se hace **antes de calcular el render y vence también a `force`** (sólo cede si el cuerpo está vacío, para poder pintarlo por primera vez).  Verificado con el camino del SSE: dos `renderPanelBody(svc, {force:true})` con texto seleccionado y **la selección sobrevive**.  Es un cambio de JS: basta **recargar la página** (el `?v=<fecha>` fuerza el JS nuevo); no hace falta reiniciar el servicio. |
| ¿Quién hace el `git fetch`? | **Sólo el botón**: `fetchAllGit()` en la barra de Microservicios → `POST /api/git/fetch_all` → `run_git_fetch_all()`, que recorre los repos del catálogo con `.git` y lanza `git fetch --prune` (timeout 12 s) en un *pool* de 8 hilos; devuelve `total`/`updated` por servicio.  **No hay temporizador**: ningún proceso lo ejecuta solo, así que los contadores «bajar/subir» reflejan el último fetch manual (el resto del estado viene de refs locales). |
| Extra (SEC-10) | `GET /api/git/fetch_all` estaba clasificado como «GET con efecto (red)» y ejecutaba el fetch completo: bastaba abrir la URL.  Ahora responde **405** y remite a POST, que es lo que usa la interfaz. |

### 3.27 Vigésima ronda: consolas «en negro» de servicios sin tráfico

**Aclaración del síntoma**: lo que se veía en negro no era una consola rota, sino una consola
**sin líneas**: un servicio de desarrollo **no escribe si no recibe peticiones**, y además las
capturas de la ronda anterior (autocorrección y red de seguridad) sólo se aplican **al recargar
la página** — la pestaña del usuario seguía con el JS anterior, y por eso la captura mostraba
paneles vacíos con el pie en «LIVE».  Medido en el panel ya recargado: **ningún panel visible
queda vacío sin marcador**.

**Mejora aplicada** (que el vacío sea informativo, no un hueco negro): cuando una consola no
tiene líneas, se pinta un **bloque de estado** (`.console-vacio`) en lugar del texto plano
«(Sin salida capturada todavía)»:

| Situación | Qué muestra |
|---|---|
| Servicio **en marcha** y nunca escribió | 🟢 *En marcha — todavía sin salida* · «Arrancó y aún no ha escrito nada» · sugiere 🩺 si se esperaba actividad |
| Servicio **en marcha** con salida previa | 🟢 *En marcha — sin salida nueva* · «Última línea hace Nm; la captura sigue activa» · explica que un servicio de desarrollo no escribe sin peticiones |
| Servicio **detenido** | ⏹️ *Detenido — sin salida capturada* · indica lanzarlo con ▶ Iniciar / «Iniciar en Dashboard» |

Tres detalles que evitan el «desfase» que se veía antes: el estado sale de `globalData` (estado
real del servicio) y **no** del texto del pie, que se actualiza después; al cambiar el estado
visual se **repinta el marcador** (una consola detenida ya no dice «en marcha»); y la red de
seguridad de 2,5 s repinta cualquier panel visible con el cuerpo vacío, de modo que el bloque
aparece aunque el panel haya perdido su contenido al deshidratarse.

### 3.28 Vigesimoprimera ronda: autodiagnóstico de versión de la interfaz

Cuando algo «sigue igual tras recargar», la causa suele ser que el navegador está ejecutando
una **copia vieja del JS** y no hay forma de saberlo a simple vista.  Ahora se ve solo:

* El HTML se sirve con `window.__UI_VERSION` (la versión del JS que esa página pidió) y
  `/api/status` publica `ui_version` (la que el servidor sirve ahora).  Si no coinciden, la
  interfaz muestra un **aviso ámbar** abajo: «Tu navegador tiene una versión antigua de la
  interfaz (X frente a Y). Recarga con Ctrl+Shift+R».
* `diagnosticoMuro()` (consola del navegador, F12) devuelve el estado real del muro:
  visibilidad, hidratación, líneas, si tiene marcador de estado, el pie y el estado del
  servicio de cada consola, más `versionInterfazCargada`, `versionInterfazServidor`, `coincide`,
  `vigilanciaActiva` y `sseSaludable`.  Sirve para distinguir «copia vieja» de «consola sin
  tráfico» sin adivinar.

Comprobado además que el JS servido coincide byte a byte con el del disco (`md5`), que su GET
lleva `no-store` y que el HTML va con `no-store` y `?v=<fecha>` en CSS/JS.

### 3.29 La causa real de las consolas «negras»: líneas en blanco al final

**Síntoma**: consolas con el cuerpo negro y el pie en «hace Nm • LIVE», con el servicio
escribiendo.  Ni recargar ni mis dos rondas anteriores lo resolvían.

**Causa (medida)**: el final del búfer está lleno de **líneas en blanco** que dejan los
servicios al escribir.  Con la salida anclada al fondo (correcto, es un *tail*), la ventana
visible del cuerpo —unos 11 renglones— queda ocupada por espacios:

| Consola | líneas | en ventana | con texto | vacías al final |
|---|---|---|---|---|
| `ms_sisper_carrera_correct_comp` | 50 | 11 | **0** | **49** |
| `ms_sisper_documentos` | 50 | 11 | **0** | 30 |
| `ms_sisper_bitacora` | 50 | 11 | **0** | 30 |

Es decir: el DOM **sí** tenía líneas (por eso mis comprobaciones anteriores pasaban) pero
ninguna con texto dentro de la ventana visible.  **Lección de verificación**: «tiene líneas»
no basta; hay que mirar «tiene texto en la ventana visible» (`textoEnVentana`).

**Arreglo**: al pintar se recortan **sólo** las líneas en blanco del final (las interiores se
conservan: separan bloques del log).  Si todo el contenido es blanco, la consola cae en su
**bloque de estado** («en marcha — sin salida nueva»), así que nunca queda un hueco negro.

**Verificado**: `negrasProbables: []` y las consolas afectadas muestran su salida real
(`textoEnVentana: 8-9`, `vaciasAlFinal: 0`).  `diagnosticoMuro()` incorpora ahora
`textoEnVentana` y `vaciasAlFinal` por consola, que es exactamente la métrica que faltaba.

### 3.30 Espejo Visual en Vivo: la rama era la correcta, el bloqueo era CORS

**Verificación pedida** — `frontend/mf_sisper_sesion` está en la rama
`feature_telemetria_presencia_en_vivo`, que es la **única** del repositorio con el emisor del
espejo (`apps/main/src/telemetry/LiveTelemetryTracker.jsx`, commit `346d22450`), y el componente
está **montado** (`App.js`: `import LiveTelemetryTracker` + `<LiveTelemetryTracker paused={!isValidLogin}/>`).
El tracker envía a `http://<host>:9099/api/telemetry/mirror_stream` (y el latido a
`/api/telemetry/heartbeat`).  Es decir: **al repositorio no le faltaba nada**.

**Causa real de que no se viera nada**: el panel sólo aceptaba como `Origin` **su propio puerto**
(`allowed_origins()` = `127.0.0.1|localhost|::1:9099` + extras).  El tracker corre en el
frontend (puerto **3000**), así que el navegador rechazaba la petición por CORS:

| Preflight `OPTIONS /api/telemetry/mirror_stream` | Antes | Ahora |
|---|---|---|
| `Origin: http://localhost:3000` | 200 **sin** cabeceras CORS | `Access-Control-Allow-Origin: http://localhost:3000` |
| `Origin: http://localhost:9099` (control) | con cabeceras | con cabeceras |
| `Origin: http://evil.example` / `:4321` / `:9999` | sin cabeceras | **sin cabeceras** (sigue rechazado) |

**Arreglo**: `allowed_origins()` incorpora los orígenes de los **frontends configurados**
(puertos de `config/services.json` en `localhost` y `127.0.0.1`).  No es «cualquier localhost»:
un puerto desconocido sigue sin permiso, que es lo que protege la frontera de confianza.

**Verificado de extremo a extremo**: `POST` desde `Origin: http://localhost:3000` →
`200` + cabecera CORS + `{"status":"ok"}`, y el panel **guarda** el snapshot: `GET
/api/telemetry/mirror_view?user=…` devuelve `dom_html` con `dom_ver: 1`.

**Para que se vea** (después de recargar el frontend): el usuario debe estar **con sesión
iniciada** (el tracker nace `paused`), y el operador debe **activar el espejo** de ese usuario
en el panel (`POST /api/telemetry/mirror_control {enabled:true}`): sólo entonces el panel
responde `mirror_requested: true` y el tracker empieza a mandar el DOM.

#### 3.30.1 El CORS que quedaba: el panel escucha en loopback y el frontend va por IP de LAN

Con el frontend servido desde `172.23.22.38:3000`, el tracker resuelve el panel como
`http://172.23.22.38:9099/...` (lo deriva de `window.location.hostname`), pero el panel escucha
**sólo en `127.0.0.1:9099`** (`SISPER_HOST=127.0.0.1`): la petición **no conecta** y el navegador
lo reporta como «CORS request did not succeed · Status code: (null)» — un fallo de conexión, no
de lista de orígenes.

Dos piezas, y hacían falta las dos:

1. **Orígenes**: `allowed_origins()` amplía los frontends con las **direcciones propias del
   equipo** (`socket.gethostname()` + `socket.getaddrinfo`), no sólo `localhost`.  Verificado:
   `http://172.23.22.38:3000`, `http://fedora:3000`, `http://localhost:3000` → **permitidos**;
   `http://172.23.22.38:4321`, `http://evil.example:3000`, `http://172.23.22.99:3000` →
   **rechazados**.  (El `import socket` faltaba y el `try/except` lo ocultaba: por eso el primer
   intento no surtió efecto.)
2. **Alcance**: mientras el panel siga en loopback, el frontend debe apuntarle a loopback.  El
   tracker ya admite override por runtime (`window.__ENV__.MS_TELEMETRY` /
   `MS_TELEMETRY_STREAM`, y hoy `frontend/mf_sisper_sesion/env.js` está **vacío**), así que basta
   con declararlos apuntando a `http://127.0.0.1:9099/...` — sin recompilar y sin exponer el
   panel a la red.  La alternativa es `SISPER_HOST=172.23.22.38` en la unidad, que sí publica el
   panel en la LAN (decisión del operador).

**Telemetría: cuándo se detiene** (leído del tracker): el **latido va cada 2 s** mientras haya
sesión iniciada y la pestaña viva (`paused={!isValidLogin}`, efecto con `clearInterval`); el
**DOM y el cursor sólo se envían cuando el panel responde `mirror_requested: true`** (espejo
activado por el operador), y se detienen al desactivarlo.  El panel poda usuarios tras 30 s sin
latido y espejos tras 120 s.  Lo que **no** se detiene solo es el latido de presencia: para que
sea opt-in («sólo cuando quiero revisar») hay que condicionarlo en el tracker del frontend.

---

## 4. Mapa de archivos

| Archivo | Rol |
|---|---|
| `static/index.html` (~2300 líneas) | 8 pestañas, 22 modales. Nuevo: links a `themes.css` y `console-wall.css`, `theme.js`, botón 🎨 Configuración, `#settingsModal`, `#consoleWallToolbar`. Sin menú `⋯ Más`. |
| `static/js/dashboard.js` (~9730 líneas) | Toda la lógica. Objeto `consoleWorkspace` con el estado del muro. Funciones nuevas clave: `wallOrder`, `moverConsola`, `applyFocusLayer`, `toggleEnfoque`, `paintFocusButton`, `accionServicioReal`, `anclarSalidaAbajo`, `activarRuedaConsola`, `entrandoAlMuro`, `applyWallPauseUi`, `setWallFont`, `setPanelFont`, `actualizarContadorBusqueda`. Fase 4: `noteServerClock`, `touchPanelTraffic`, `panelIdleSeconds`, `panelFreshness`, `refreshPanelFreshness`, `refreshWallFreshness`, `bumpPanelRevision` y el presupuesto `WALL_PAINT_MS`. |
| `static/css/dashboard.css` (~3559 líneas) | Estilos de la app (tokenizados en Fase 2). |
| `static/css/themes.css` (~550 líneas + selector) | Escalas, 13 temas, selector y **bloque único de `:focus-visible`** de la app. `--focus-ring` es un **color** (el acento), no un box-shadow. |
| `static/js/theme.js` (~150 líneas) | Selector y persistencia de tema. |
| `static/css/console-wall.css` (~500 líneas) | Lenguaje visual del muro (tarjetas, barra, menú flotante, enfoque, pie con el indicador de frescura y sus reglas por rejilla). |
| `static/lab_terminales_30.html` | **Prototipo aprobado**: fuente de verdad del diseño. Cualquier duda de "cómo era en el laboratorio", se mira aquí. |
| `devconsole/services/terminal/tmux_backend.py` | Acción `stop-single`. |
| `devconsole/services/terminal/live_broker.py` | `last_line_ts` por servicio (frescura) y su emisión en `to_dict()` y en los deltas SSE. |
| `devconsole/api/handlers.py` | Ruta `/api/action` para `stop-single`; CSP. |
| `desktop/tools/cdp/lib/cdp.mjs` | Cliente CDP compartido (Chromium headless, `evaluate`, `screenshot`, `contrastRatio`). |
| `desktop/tools/cdp/sisper-fase4-{freshness,focus}.mjs` | Verificadores de Fase 4 (frescura y foco en 13 temas), con `exitCode` 1 al fallar. |
| `desktop/tools/cdp/sisper-fase4-console-liveness.mjs` | Regresión del fallo de congelación: comprueba que una línea nueva llega al DOM. |
| `desktop/tools/cdp/sisper-fase4-capture-focus.mjs` | Capturas de evidencia del foco. |
| `scripts/venvs.sh` | Salud/reparación de los virtualenvs (`check`, `list`, `fix`, `rebuild`); ver §6.3. |
| `docs/capturas-fase4/` | Evidencia de Fase 4: frescura (8 columnas y reposo) y foco (light, amber, solarized, abyss, modal). |

**Datos en vivo**
- SSE `GET /api/services/stream` (eventos `snapshot`, `delta_batch`, ping 3 s).
- Polling `GET /api/services/wall` cada 3 s; `catalog`, `mosaic`, `k8s/logs`.
- Si un servicio no recibe tráfico, **no hay líneas nuevas**: no es un fallo del
  muro (verificado con `line_count` del backend y peticiones locales de prueba).
  Desde Fase 4 el indicador de frescura (§3.5) lo hace evidente sin abrir la
  consola: `hace 12m` en ámbar = el servicio lleva rato sin escribir,
  `sin tráfico` = no tiene sesión o nunca escribió.

---

## 5. Commits de este bloque

| Commit | Contenido |
|---|---|
| `f4aafb7` | Checkpoint del frontend y prototipos antes de unificar estilo |
| `c6668d9` | Sistema de temas global + Configuración con selector |
| `e5179d1` | Muro de Servicios y Consolas con el lenguaje del laboratorio |
| `2673672` | Muro 1:1 con el laboratorio, sin barra lateral |
| `7100ea5` | Nueve ajustes del muro (scroll, buscador de microservicios, ventana, menú, "Seguir", alineación, marcas de Enfoque, anclaje del texto, plantillas) |
| `dfc051d` | Quita menús que no se usan y hace funcionar Parar/Reiniciar |
| `f613866` | **Fase 2**: tokenización de toda la app |
| `0d57c00` | **Fase 3 (U1)**: redibuja microservicios con anatomia del muro, barra tilix, ribbon kpi y filtros |
| `8e29855` | **Fase 3 (U2)**: unifica tablas, badges de estado y acciones en workspace y kubernetes |
| `1e21f96` | **Fase 3 (U3)**: redibuja paneles de infraestructura y mapa operativo con lenguaje de consola |
| `a19684f` | **Fase 3 (U4)**: unifica auditoria de actividad en vivo y consola de diagnostico |
| `a738b14` | **Fase 3 (U5)**: unifica cabecera, cuerpo y pie de los 22 modales con tokens del laboratorio |
| `f7be8c4` | **Fase 3 (U6)**: consolida botones btn y cw-btn con tokens de temas, limpia !important y borra css muerto de modo agrupado |
| `ea6300d` | **Fase 4**: atajos de teclado ergonómicos del muro (`/`, `p`, `Alt+2..8`, `Escape` enriquecido) |
| `e870e92` | **Fase 4**: restaura el foco visible de teclado en los 13 temas (`--focus-ring` era un box-shadow usado como color de outline) |
| `3a13849` | **Fase 4**: indicador de frescura de tráfico por consola (`last_line_ts` en el broker + pie del muro) |
| `25aea83` | **Fase 4**: las consolas se congelaban al superar el recorte de 200 líneas (revisión por consola + guarda barata + presupuesto de repintado) |
| `b6159f6` | **Herramientas**: `scripts/venvs.sh` para detectar/reparar los virtualenvs desalineados y reconstruirlos con intérprete versionado |
| `eafc217` | **Fase 4**: el broker dejaba de emitir deltas cuando la ventana de captura de tmux se saturaba (detección por solape) |
| `4d64cba` | **Verificación**: la frescura no debe exigir formato de segundos al restaurar el reloj |
| `da0fe8c` | **Muro**: el ancla por solape ignoraba las líneas vacías del final (consolas congeladas con la ventana saturada) |
| `c487600` | **Microservicios**: nombres legibles, «Sin remoto» y consumer/worker desbloqueado |
| `768f008` | **Fase 4**: frescura sin parpadeo, pausa por scroll reanudable y muro sincronizado |
| `50970dd` | **Muro**: las consolas auxiliares (RabbitMQ, Celery) ya aparecen como tarjeta |
| `7f1233b` | **Microservicios**: tarjetas con el nombre al estilo de las consolas (una línea, sin prefijo) |
| `0d82f2d` | **Muro**: se puede parar y reiniciar una consola auxiliar (worker/rabbit) |
| `52f6cae` | **Muro**: conmutador «Solo activas» y nombre completo en las tarjetas |
| `02d8f11` | **Verificación**: la frescura tolera el tiempo real y explica por qué falla |
| `2b8f235` | **Rendimiento**: el muro deja de capturar cuando nadie mira (+ cachés de sondeos) |
| `a9105e5` | **Backend**: imagen local nunca se reportaba y errores que cortaban la conexión |
| `0dada6f` | **UI**: xterm bajo demanda, sondeo con SSE, virtualización fuera de pestaña y XSS |
| `c5aa299` | **Terminal**: las consolas auxiliares ya no arrancan el backend otra vez |
| `100f849` | **UI**: Enfoque con varias consolas, pausa por scroll, tema entre ventanas, icono Django |
| `f12bd0c` | **Sitio**: pestaña nueva con carpeta de manifiestos, inventario de YAML y tema por entorno |

---

## 6. Limitaciones y cosas a saber

- **Modo control xterm**: dormido, sin entrada en la UI. Si se quiere volver,
  hay que reponer el botón y probar mejor (abría Tilix y no funcionaba bien).
- **Anclaje del texto**: se hace con un `padding-top` calculado en
  `anclarSalidaAbajo()` al pintar cada consola y al redimensionar. Se intentó con
  `justify-content: flex-end` y **rompía el acceso a las líneas antiguas**; no
  volver a ese camino.
- **Recursión**: `applyFocusLayer()` ↔ `renderConsoleStage()` se llaman entre sí.
  Hay una guarda `consoleWorkspace._applyingFocus`; **no quitarla**.
- **Paneles y xterm**: nunca mover un nodo de panel en el DOM si puede contener
  xterm (pierde el lienzo). Para reordenar se usa `order` de CSS.
- El muro cuenta con verificación automatizada con CDP + capturas en `docs/capturas-fase3/`.
- El repositorio tiene WIP previo en Python/tests/docs **sin tocar** a propósito.
- **Frescura**: `last_line_ts` marca el crecimiento del buffer del broker, no la
  hora de emisión de la línea dentro del servicio. Un tmux cuyo scrollback ya
  estuviera lleno antes de arrancar el panel se marca como "visto" en el primer
  sondeo del broker; a partir de ahí la marca es fiel.
- **Rejillas densas**: a 7-8 columnas el pie oculta la etiqueta de runtime y a 8
  reduce el estado a su LED. Es degradación deliberada para que el nombre y la
  frescura no se recorten; el estado completo sigue en el título del LED de
  cabecera y en el menú `⋯`.
- **Accesibilidad pendiente**: los botones-div del pie de la barra lateral
  (`Configuración`, `Sesiones Tilix`) y la píldora de rol son `<div onclick>`, así
  que **no se alcanzan con Tab**. Convertirlos en `<button>` (o añadir
  `tabindex="0"` + Enter/Espacio) es la continuación natural; no se hizo aquí para
  no arriesgar los bindings existentes.
- **Margen de contraste del foco**: el peor caso medido es 3.32:1 en `light`
  (ítem de la barra lateral). Supera el 3:1 exigido por WCAG 1.4.11, pero si se
  aclara más esa superficie hay que volver a medirlo con `sisper-fase4-focus.mjs`.

### 6.1 Trampa grave: `main` no arranca desde un clon limpio (WIP ajeno)

Comprobado exportando `HEAD` a un directorio limpio (`git archive HEAD`) e
intentando importar el servidor:

```
ImportError: cannot import name 'settings' from 'devconsole'
```

`devconsole/api/handlers.py` (en `HEAD`, sin modificar en el árbol) importa dos
módulos que **no están versionados**:

| Importado por HEAD | Estado |
|---|---|
| `devconsole/settings.py` (handlers.py:45) | **untracked**, ausente de `HEAD` |
| `devconsole/services/ttl_cache.py` (handlers.py:70) | **untracked**, ausente de `HEAD` |

Además `docs/estandarizacion.md` describe `config/panel.example.json`,
`secrets.example.json` y `services.example.json` como versionados, pero los tres
siguen **untracked**; y `.gitignore` ignora `/config/services.json` mientras el
documento dice que se versiona (`config/settings.json`, en cambio, **sí** está en
`HEAD` aunque el documento lo da por no versionado).

Es WIP del bloque de estandarización, no de este bloque de UI: **no se ha tocado**
(regla del usuario). Para dejar `main` reproducible hace falta una decisión
explícita, y entonces habría que añadir esos archivos junto con el resto del WIP
de la misma unidad (`devconsole/config.py`, `server.py`, `services/*.py`,
`tests/devconsole/test_security_boundary.py`, `.gitignore`) para que el árbol
quede coherente. Mientras eso no ocurra, **`main` sólo funciona en esta máquina**,
donde los archivos existen en el directorio de trabajo.

---

### 6.2 Entorno: los virtualenvs del sistema y el "modo entorno" (leer antes de tocar nada)

Tres hechos que, juntos, explican una caída total del muro y conviene tener
presentes:

**1. Los venvs DEBEN estar anclados a un intérprete con versión.** Los de esta
máquina se crearon con el enlace sin versión (`bin/python -> /usr/bin/python`).
El 30-sep el sistema movió ese enlace a **Python 3.14**: los venvs pasaron a
ejecutar 3.14 mientras sus paquetes seguían en `lib/python3.11/site-packages/`,
de modo que `import dotenv` fallaba y cada servicio moría en ~2 s dejando el
lanzador en el prompt `Opción [r=reintentar / s=shell / i=instalar / q=bash]:`.
Herramienta:

```bash
scripts/venvs.sh check     # salud; sale 1 si algo está desalineado
scripts/venvs.sh fix       # repara el enlace (offline, no toca paquetes)
scripts/venvs.sh rebuild ms_sisper_bitacora   # pipenv --python <versionado> (requiere PyPI)
```

**Regla de oro al crear un venv**: `pipenv --python /usr/bin/python3.11 install`.
`pipenv install` a secas coge `/usr/bin/python` y reproduce el problema.

**2. El "MODO DE ENTORNO (.env)" reescribe los `.env` y reinicia los servicios.**
El recuadro de Infraestructura (solo admin) ejecuta `switch_env.sh`, cuya
`apply_mode()` **sustituye en su sitio** las claves que gestiona
(`DATABASE_HOST/USER/NAME/PORT`, `KEYCLOAK_*`). Es **no destructivo**: no borra
el resto del archivo, no crea `.env` inexistentes (`if not path.exists(): return`)
y no deja claves duplicadas. Pero cada escritura sube el `mtime`, y el
`env_file_watcher_loop()` (1,2 s) hace `restart-single` del servicio afectado:
**cualquier cambio de modo de entorno recarga el muro entero**. Por eso, con los
venvs rotos, pulsar el modo entorno tumbó ~20 servicios a la vez (09:04:53).

**3. Dos servicios no están provisionados** en esta instalación: no tienen `.env`
(su única fuente es un `.env.secret` **cifrado con PGP**) y `apply_mode` no puede
crearlo. `ms_sisper_carrera_correct_comp` además tiene el venv vacío y sin
`Pipfile.lock`. Quedan fuera hasta descifrar/provisionar su `.env` e instalar
dependencias.

> `.env` y todo `backend/` están en `.gitignore` (línea 27), así que git **no** es
> red de seguridad para el entorno: el respaldo real es `.env.secret`.

---

### 6.3 Portabilidad: estado real (auditado)

**Hoy NO se puede desplegar en otra máquina desde un clon limpio.** Verificado con `git ls-tree -r HEAD`:

1. `devconsole/settings.py` **no está versionado** y `devconsole/config.py` lo importa ⇒ `ImportError` al arrancar. Es el núcleo de configuración.
2. `devconsole/services/ttl_cache.py` **no está versionado** y lo importan `git_service`, `k8s_service`, `infra_service`, `env_service` y `handlers` ⇒ segundo `ImportError`.
3. `config/panel.example.json`, `config/secrets.example.json`, `config/services.example.json` y `docs/estandarizacion.md` **tampoco están versionados**: el `cp` que documenta el propio traspaso falla en un clon.
4. `config/settings.json` (sí versionado) fija `base_dir` a esta máquina; degrada por un `exists()`, pero es un valor de instalación.
5. Los JSON de sesión versionados llevan 33 rutas absolutas de esta máquina.
6. `switch_env.sh`, `tilix_runner.sh` y `start_tilix.sh` están **congelados byte a byte** por `tests/devconsole/test_runtime_safety.py`: justo donde viven hosts, usuarios, puertos y URLs de Keycloak.
7. `dumps_prod/` (**1,3 GB, 20 dumps de producción**) y `logs/` están sin seguimiento pero **no** ignorados: a un `git add` de subirse.

Pasos para que sea reproducible en otra máquina (sin generalizar los entornos ni los scripts congelados, que no compensa): versionar los puntos 1-3; copiar los `*.example.json` a `config/*.json` y rellenarlos; arreglar o borrar `config/settings.json`; regenerar los JSON de sesión; añadir `dumps_prod/` y `logs/` al `.gitignore`; y rotar las credenciales antes de compartir.

---

## 7. Fases del proyecto

### Fase 1 — Sistema de temas globales (hecho)
13 temas dinámicos en `themes.css`, selector en Configuración y persistencia en `localStorage`.

### Fase 2 — Tokenización de toda la aplicación (hecho)
Reemplazo de colores hexadecimales fijos por variables CSS semánticas en `dashboard.css` e `index.html`.

### Fase 3 — Unificar el lenguaje visual del resto de vistas y modales (hecho)
Rediseño de componentes visuales en las 7 vistas restantes y estandarización completa de los 22 modales, consolidación de botones con `.btn` / `.cw-btn`, eliminación de gradientes rígidos y limpieza de CSS muerto. Verificación sin errores JS en consola.

### Fase 4 — Detalles finos del muro (casi cerrada)
- **Atajos de teclado implementados**:
  - `/`: enfoca y selecciona el buscador de microservicios `#consoleServiceSearch` en el muro.
  - `p` / `P`: conmuta pausa y reanudación global del flujo del muro (`#btnWallPause`).
  - `Alt + 2..8`: cambia instantáneamente la cuadrícula a 2, 3, 4, 5, 6, 7 u 8 columnas.
  - `Escape`: cierra menús flotantes, limpia/desenfoca el buscador, sale de modo Enfoque o restaura consola maximizada.
  - `Ctrl/Cmd + F`: enfoca búsqueda interna de salida.
- **Indicador de frescura por consola**: hecho (§3.5), con verificación determinista
  de la rama de minutos y capturas en `docs/capturas-fase4/`.
- **Foco visible en los 13 temas**: hecho (§3.6), con la corrección de
  `--focus-ring` y contraste medido en los 13 temas.
- **Vivacidad de las consolas**: hecho (§3.7). El muro se congelaba al superar
  200 líneas por consola; ahora la latencia extremo a extremo medida es de
  235-527 ms y hay prueba de regresión (`sisper-fase4-console-liveness.mjs`).
- **Suite CDP**: cliente compartido en `desktop/tools/cdp/lib/` y tres verificadores
  nuevos que devuelven `exitCode` 1 al fallar.
- Pendiente:
  - Confirmar si el "ajuste de letra al maximizar" (+2 px) es lo que se esperaba.
  - Probar `⧉ Ventana` en un segundo monitor real.
  - Convertir en botones reales los `<div onclick>` del pie de la barra lateral
    (hoy inalcanzables con Tab) y revisar `aria-*` de los controles del muro.
  - **Append incremental** en el repintado de consolas (ver §3.7): hoy se
    reconstruyen las 200 líneas en cada actualización, ~57-130 ms por panel.

### Fase 5 — Endurecer (empezada sin pedirse)
- Tests de humo del frontend (CDP) para el muro y el selector de tema: **montados**
  (`desktop/tools/cdp/`, ver §2); Playwright sigue sin ser necesario.
- Revisar el `!important` global y el CSS sin usar.
- **Cerrar la trampa de §6.1**: mientras `HEAD` importe módulos untracked, la suite
  no se puede correr desde un clon limpio.
- Provisionar `.env` (descifrando `.env.secret`) para `ms_sisper_firmador` y
  `ms_sisper_carrera_correct_comp`, y reconstruir el venv de este último (§6.2).

---

## 8. Recetas rápidas

```bash
# estado
systemctl --user is-active sisper-dashboard.service
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:9099/

# tras tocar Python
systemctl --user restart sisper-dashboard.service

# cuánta salida hay por servicio (sin tocar datos)
curl -s http://127.0.0.1:9099/api/services/wall | python3 -c "import json,sys;d=json.load(sys.stdin);items=d if isinstance(d,list) else d.get('services',[]);print(sum(i.get('line_count') or 0 for i in items))"

# git
git log --oneline -8

# suite completa de la interfaz (Chromium headless + CDP)
node desktop/tools/cdp/sisper-fase3-smoke.mjs          # 8 vistas
node desktop/tools/cdp/sisper-fase3-test-modals.mjs    # 22 modales
node desktop/tools/cdp/sisper-fase4-freshness.mjs      # frescura + desbordes del pie
node desktop/tools/cdp/sisper-fase4-focus.mjs          # foco en los 13 temas
node desktop/tools/cdp/sisper-fase4-console-liveness.mjs  # las consolas se repintan

# entorno: ¿los venvs siguen anclados a su versión? (tras actualizar el sistema)
scripts/venvs.sh check        # 1 = hay venvs desalineados
scripts/venvs.sh fix          # reparación offline
scripts/venvs.sh list         # tabla de intérpretes

# ¿está el muro en vivo o no hay tráfico? (line_count no debe cambiar si nada pasa)
curl -s http://127.0.0.1:9099/api/services/wall | python3 -c "import json,sys;d=json.load(sys.stdin);print(sum(i.get('line_count') or 0 for i in d['services']))"

# cuánta antigüedad tiene cada servicio (lo que pinta el indicador)
curl -s http://127.0.0.1:9099/api/services/wall | python3 -c "
import json,sys,time
d=json.load(sys.stdin); now=time.time()
for s in sorted(d['services'], key=lambda x: x.get('last_line_ts') or 0):
    t=s.get('last_line_ts') or 0
    print(s['name'][:30].ljust(30), ('hace %4.0fs' % (now-t)) if t else 'sin tráfico')
"
```

En el navegador (o por CDP):
- Tema: `SisperTheme.apply('light')` / `SisperTheme.apply('abyss')`.
- Muro: `switchTab('consoles')`; estado en
  `JSON.parse(localStorage.sisper_console_workspace)`.
- Si algo del muro no reacciona, comprobar primero que no haya errores de consola:
  los últimos bugs reales fueron una recursión y parches JS no guardados.

---

## 9. Seguridad y optimizaciones pendientes (ordenadas por impacto)

### 9.1 Seguridad: atender antes de compartir la aplicación

1. **Credenciales expuestas en el historial de la sesión.** Durante la auditoría, dos salidas de `grep` sin redactar mostraron valores de `DATABASE_PASSWORD` (`switch_env.sh`) y contraseñas de BD (`clonar_bds_desarrollo.sh`). Deben considerarse **comprometidas** y rotarse. Además, el commit `79d00c2` introdujo un `client_secret` en `devconsole/config.py`: ya no está en `HEAD`, pero sigue en el historial ⇒ rotación obligatoria antes de compartir.
2. **`config/secrets.json` en modo 0644** (sus `*.example.json` están en 0600) guardando las credenciales que `panel.json` resuelve por marcadores. `chmod 600 config/secrets.json`.
3. **PIN de administrador por defecto** en `devconsole/auth.py:31` si falta `SISPER_ADMIN_PIN`; conviene exigir la variable.
4. **Autorización de POST fail-open**: `security.MUTATING_PATHS` declara las rutas que mutan, pero `authorize_post` no la consulta: todo POST no listado cae a rol `DEV`. Además `/api/git/fetch_all` es **GET** y sólo pasa el filtro de confianza (hace `git fetch --prune` sobre 31 repos sin sesión). Decisión pendiente: ¿se aplica la tabla (fail-closed) o queda como documentación?
5. `dumps_prod/` (1,3 GB de producción) sin ignorar.

### 9.2 Optimizaciones pendientes

| Prioridad | Qué | Dónde | Ganancia estimada |
|---|---|---|---|
| Alta | `/proc` completo por servicio (`pids_owning_inodes`); batchear en una sola pasada de fds | `services/runtime/process_inspector.py:267` | `/api/services/mosaic` 3,31 s → decenas de ms |
| Alta | El refresher llama `.refresh()` ignorando los TTL (hasta 416 `git` por pasada) y sondea k8s cada 8 s | `server.py:66,89-105`, `infra_service.py:206` | cientos de subprocesos y 7,5 `kubectl`/min menos |
| Alta | `renderPanelBody` es el hotspot real del muro (162 llamadas / 2,4 s en 20 s): diffing por línea en vez de reescribir el cuerpo | `static/js/dashboard.js` | long task de 935 ms al entrar al muro |
| Media | El menú `.cw-menu` de cada panel se construye siempre, incluso cerrado (1.302 nodos, 713 botones de 31 paneles) | `static/js/dashboard.js` | DOM del muro ~33 % menor |
| Media | `git fetch_all` por GET y sin límite de paralelismo | `handlers.py:503` | riesgo de red y de hilos bloqueados |
| Media | Accesibilidad del muro: 62 clicables sin teclado, 188 botones de icono sin `aria-label`, 23 modales sin `role="dialog"` | `static/js/dashboard.js`, `static/index.html` | uso con teclado y lectores de pantalla |
| Baja | Código muerto confirmado: `isIdleConsoleService`, cuerpo de `renderIdleConsoleStrip`, `renderConsoleTabsStrip`, `renderGroupedConsoleStage`, ~185 líneas de control xterm sin botón, 13 `getElementById` a ids inexistentes | `static/js/dashboard.js` | mantenimiento |
| Baja | `KillMode=process` en la unidad deja `tmux` y procesos huérfanos entre reinicios | unidad `sisper-dashboard.service` | atribución de CPU/memoria entre corridas |
