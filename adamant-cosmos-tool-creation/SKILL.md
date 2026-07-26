---
name: adamant-cosmos-tool-creation
description: Create custom COSMOS web UI tools and screen widgets, from a Telemetry Viewer screen up to a full single-spa Vue tool with a backing microservice. Use when a built-in tool and stock screens cannot express a needed display or workflow -- dashboards, log/event viewers, detail panels, terminals -- or when choosing between a screen, a custom widget, a full tool, and a tool+microservice, and wiring its data feed (polling, streaming, or a custom backend).
---

# adamant-cosmos-tool-creation

Extend the COSMOS web UI. COSMOS ships a fixed set of tools and a large
telemetry-screen widget library; when those cannot express what you need, you
add your own -- a screen definition, a custom screen widget (UMD bundle), a full
tool (single-spa Vue app), or a tool paired with a backing microservice. This
skill covers choosing the lightest option that works and building it: plugin.txt
declaration, the vite/single-spa build contract, the data-feed options, and
deployment through the plugin gem.

## When to Use

- A workflow isn't covered by a built-in tool and isn't expressible as a stock
  Telemetry Viewer screen
- Building a dashboard, event/log viewer, detail panel, status page, or a
  terminal/console that bridges an external system
- Deciding among screen / custom widget / full tool / tool+microservice
- Wiring a tool's data feed: JSON-RPC polling, websocket streaming, or a custom
  microservice endpoint

**Prerequisites:** a working plugin gem build (see `adamant-cosmos-integration`),
node + yarn/pnpm for front-end builds, and a running COSMOS to verify against.
COSMOS source is available for crawling at the framework mirror when a detail is
unclear.

## Decision ladder -- pick the lowest rung that works

Each rung up adds a build artifact and a deploy surface. Do not skip to a full
tool when a screen or widget expresses the need.

| Rung | Option | Use when | Cost |
|---|---|---|---|
| 0 | **Reuse a built-in tool** | An existing tool (Telemetry Viewer, Grapher, Packet Viewer, Data Viewer, Command Sender, Data Extractor, Script Runner, ...) already does it | none |
| 1 | **Telemetry Viewer screen** (`screens/*.txt`) | You only display/interact with telemetry and the layout is expressible with stock widgets | text only; no JS build |
| 2 | **Custom WIDGET** (one `.vue` -> UMD) | A screen needs a display element or control the ~55 stock widgets can't produce, but it still lives inside a screen and wants the screen runtime (data binding, limits, layout) for free | one UMD bundle + sourcemap |
| 3 | **Full custom TOOL** (`WINDOW INLINE`) | You need a whole application surface: own route, nav entry, multi-view UX, orchestration across many packets/APIs | full single-spa build |
| 4 | **TOOL + MICROSERVICE** | The tool needs server-side work the browser and existing COSMOS APIs can't do: bridge an external socket/serial/process, hold a long-lived connection, custom endpoint, heavy compute | a persistent process + route |

Rungs 1-2 reuse the entire Telemetry Viewer runtime; rung 3 re-implements that
surface; rung 4 adds a server process on top. **Multiple tools (and a
microservice) ship fine in one plugin/gem** -- build each tool as its own vite
sub-project and stage the built bundles into the plugin's `tools/` (see
Packaging). The one caveat, per the OpenC3 docs, is combining a custom TOOL and
a custom WIDGET in the same plugin, which can break the build (the widget's UMD
build vs the tool's systemjs build); keep a custom widget in its own plugin.

## Quick Start (full tool, rung 3)

1. Scaffold with the OpenC3 generator (inside the node build container):
   `openc3.sh cli generate tool 'Display Name' <tool_name>` -- emits
   `src/App.vue`, `src/main.js`, `src/router.js`,
   `src/tools/<tool_name>/<tool_name>.vue`, `package.json`, `vite.config.js`.
   (Or copy an existing tool directory and rename the identifier throughout.)
2. Declare it in `plugin.txt`:

```
TOOL <tool_name> "Display Name"
  INLINE_URL main.js
  ICON mdi-chart-line
  CATEGORY "My Tools"
```

3. Build; vite emits the bundle to `tools/<tool_name>/`:

```
yarn install && yarn build
```

4. Ensure the gemspec `s.files` glob covers `tools/**/*`.
5. Build + install the plugin gem (see `adamant-cosmos-integration`). At install
   COSMOS uploads the bundle to the tools bucket; the shell mounts it at
   `/tools/<tool_name>`.

For a custom widget (rung 2): `openc3.sh cli generate widget <Name>Widget`,
`WIDGET NAME` in plugin.txt (separate plugin), build to a UMD bundle -- see
`references/tool-archetypes-and-widgets.md`.

## Tool anatomy

- **Declaration:** `TOOL <folder_name> "<Display Name>"`. A tool is a bundle of
  static assets uploaded to the tools bucket, optionally mounted into the shared
  front-end shell.
- **Modifiers:**

| Modifier | Effect | Default |
|---|---|---|
| `INLINE_URL <file>` | JS entry module SystemJS-imports into the shell (INLINE tools) | `main.js` |
| `URL <path>` | Route/location the tool is served at (or external URL) | `/tools/<folder>` |
| `ICON <name>` | Nav icon; `mdi-*` or `astro:*` | `astro:warning` |
| `WINDOW <mode>` | `INLINE` / `IFRAME` / `SAME` / `NEW` | `INLINE` |
| `CATEGORY <name>` | Group under a nav submenu | none |
| `SHOWN <t/f>` | Appears in nav (hidden tools still deploy + reachable by URL) | `true` |
| `POSITION <n>` | Nav order | auto |
| `DISABLE_ERB [globs]` | Skip ERB templating on matching deployed files | none |
| `IMPORT_MAP_ITEM <k> <v>` | Add an import-map entry for an extra bare specifier | none |

- **WINDOW modes:** `INLINE` mounts the `INLINE_URL` module into the shared
  single-spa shell (shares Vue/Vuetify/router singletons -- what every
  first-party tool uses). `IFRAME` isolates a non-Vue or external app in an
  iframe at `URL`. `SAME`/`NEW` navigate the current/new tab to `URL`.
- **Serving:** no web server in the plugin -- the built bundle is uploaded to the
  tools bucket at install and served through the traefik `/tools/<name>` route;
  everything is static assets plus the COSMOS APIs.
- **Mounting:** the shell loads `main.js` as a single-spa application; the entry
  must export `bootstrap`/`mount`/`unmount` (via `single-spa-vue`) mounting
  `#openc3-tool`.
- **Packaging (multiple tools per gem):** one plugin gem can declare several
  `TOOL`s (and a `MICROSERVICE`). Build each tool as its own vite sub-project
  (its own `package.json`), then copy each built bundle into the plugin's
  `tools/<tool_name>/` before packing the gem; the gemspec globs
  `{targets,lib,tools,microservices}/**/*`. Each tool builds independently, so
  tool-vs-tool build conflicts do not arise. (`tools/` is a build artifact --
  keep it out of version control.)

## Project scaffold essentials (INLINE tool)

- `vite.config.js`:
  - `build.outDir: 'tools/<tool_name>'`, `rollupOptions.input: 'src/main.js'`
  - `output.format: 'systemjs'`, `entryFileNames: '[name].js'` (emits `main.js`)
  - `external: ['single-spa', 'vue', 'pinia', 'vue-router', 'vuetify']` -- shared
    singletons the shell provides via its import map; **never bundle them**.
    (Tools on the older 6.x line list `vuex` instead of `pinia`; match the
    tool-base line you deploy against.)
  - `preserveEntrySignatures: 'strict'` (single-spa needs the exports)
  - `@vitejs/plugin-vue` with `isCustomElement: t => t.startsWith('rux-')`
    (Astro web components)
  - `define: { __BASE_URL__: JSON.stringify('/tools/<tool_name>') }`
- `src/router.js`: wrap routes with `prependBasePath` from
  `@openc3/js-common/utils` so paths resolve under `/tools/<tool_name>`.
- `package.json`: depend on `@openc3/js-common` + `@openc3/vue-common` matching
  the deployed tool-base line. Wire protocols (JSON-RPC, ActionCable) are stable
  across minor version skew.
- **Dev hot-reload:** `localStorage.setItem('devtools', true)` in the browser,
  then point the module at your vite dev server (e.g.
  `http://localhost:2999/tools/<tool_name>/main.js`).

## Choosing a data feed

Tools get telemetry three ways. Pick by access pattern, not habit.

| Need | Mechanism | Semantics |
|---|---|---|
| Latest value, simple readout | JSON-RPC `get_tlm_packet`/`get_tlm_values`/`tlm` (poll) | Current Value Table: latest packet only; polling **misses packets** between polls; same value re-served each poll |
| Every packet, live (logs, events) | Websocket `StreamingChannel`, realtime | Lossless: one delivery per decommutated packet |
| History from before the tool opened | `StreamingChannel` with `start_time` | Served from the time-series database, transitions into realtime |
| External socket/serial/process I/O | Custom MICROSERVICE + raw websocket | Whatever the microservice bridges (rung 4) |

Rules of thumb:

- Poll the CVT only when "latest value" is genuinely the requirement. A tool
  that **accumulates history** from CVT polls will drop bursts and can resurrect
  cleared data (the latest packet re-arrives every poll). Use streaming.
- Do not fetch RAW and convert client-side -- conversions run once, server-side,
  during decommutation; consume their output (the CONVERTED value).
- Client state that must survive reload (accumulating logs) belongs in
  localStorage keyed by scope; pair a persistent "clear" with a watermark so
  cleared data cannot reappear from the stream or a backfill.

The streaming recipe, message shapes, TSDB backfill rules, and the
persist-and-clear-watermark pattern are in
`references/streaming-and-data-access.md`. The tool+microservice transport
(raw websocket, `ROUTE_PREFIX`, auth caveat) is in
`references/tool-archetypes-and-widgets.md`.

## Auth and scope

Tools inherit auth from the shell: `window.openc3Scope` (current scope) and
`localStorage.openc3Token` (session token) are set for you; `OpenC3Api` calls
attach the token automatically, streaming `add` payloads carry it explicitly,
and both require `scope`. A **custom microservice reached over a raw websocket
does not receive or validate this token** -- it is unauthenticated unless you add
validation yourself (see the archetypes reference).

## Common Errors

1. **Tool accumulates from CVT polls; events drop / clear un-clears** -- polling
   `get_tlm_packet` on an interval. Switch to streaming; the CVT is
   latest-value-only and re-served every poll.
2. **Blank page / tool fails to mount** -- a shared framework was bundled instead
   of externalized, `preserveEntrySignatures` is missing, or the entry does not
   export the single-spa lifecycle. Check `vite.config.js` against the scaffold.
3. **Tool missing from nav after install** -- no `TOOL` block in plugin.txt, or
   the built `tools/<name>/` directory not matched by the gemspec `s.files` glob,
   so the bundle never reached the tools bucket.
4. **Custom widget + custom tool in one plugin fails to build** -- split them
   into separate plugins. (Multiple *tools* in one plugin are fine -- only the
   tool+widget combination is the reported problem.)
5. **`perform('add', ...)` does nothing** -- streaming `add` issued before the
   socket connected. Perform it from the `connected` callback (see reference).
6. **Subscription rejected** -- missing/wrong `scope` or stale token in the
   subscription or `add` payload.
7. **Custom microservice endpoint 404 / not reachable** -- `ROUTE_PREFIX` not
   declared, or the tool used an absolute host instead of a relative
   `/<route_prefix>/...` URL under the current origin.
8. **Custom microservice trusts the caller** -- raw-websocket microservices are
   unauthenticated; gate destructive actions and validate tokens yourself.
9. **Animated/WebGL tool degrades after navigating away and back a few times**
   -- the render loop, window-level listeners, and GPU resources were never torn
   down. Single-spa tools remount per navigation; `beforeUnmount` must cancel
   the `requestAnimationFrame` loop, abort window listeners (AbortController),
   dispose scene geometries/materials, and force WebGL context loss. Browsers
   cap live WebGL contexts (~16); one leak per remount kills the tool.
10. **Tool renders wrong or frozen data from an external feed** -- verify the
    feed, not the render: capture the upstream stream directly (in-network,
    from a container) and confirm the values move. A tool faithfully rendering
    a static feed is an upstream problem; changing the tool cannot fix it.
11. **Bundled asset 404s only when deployed (works in dev)** -- vite emitted an
    asset file plus a URL that lacks the tool's base path (e.g. `?inline` on a
    dynamic import silently degrades to an asset URL). Bundle assets as text
    instead: `?raw` for text formats, base64-in-a-text-file + `data:` URI for
    binaries (see the archetypes reference). Inspect the built output for
    root-absolute `/assets/...` URLs before shipping.

## Checklist

1. Lowest rung chosen from the decision ladder (screen/widget before a tool)
2. If a full tool: identifier consistent across `package.json`,
   `vite.config.js` (`outDir`, `__BASE_URL__`), and the `plugin.txt` `TOOL` block
3. Externals + `systemjs` output + `preserveEntrySignatures` in the vite config
4. Data feed chosen from the table (poll only for latest-value; stream for logs)
5. Accumulating tools persist state and implement clear as a watermark
6. Animated/WebGL tools tear everything down in `beforeUnmount` (animation
   loop, window listeners, GPU resources); heavy assets are dynamic-imported
   (code-split) with a load-failure fallback
7. Custom widgets and custom tools are in separate plugins
8. `yarn build` clean; bundle lands at `tools/<name>/` (tool) or
   `tools/widgets/<Name>/` (widget); gemspec globs cover it
9. Plugin installs; tool/widget appears and survives a browser reload with state
   intact

## References

- `references/streaming-and-data-access.md` -- server-side data mechanics:
  streaming message shape, decom topic retention, TSDB storage of converted
  values, logged->realtime handoff, and the JSON-RPC comparison. Read when
  wiring a live/backfilled feed or debugging feed behavior.
- `references/tool-archetypes-and-widgets.md` -- the concrete archetypes
  (append-only log stream, single-packet detail view, external-I/O terminal via
  a backing microservice, live 3D view of an external binary feed), the custom
  WIDGET build + built-in widget catalog, and the MICROSERVICE keyword
  reference. Read when choosing an archetype or building rung 2 / rung 4.

## Related Skills

- `adamant-cosmos-integration` -- plugin gem build/load, plugin.txt basics,
  container internals, JSON-RPC API reference
- `adamant-cosmos-testing` -- scripting API (procedures), suite organization
- `adamant-cosmos-suite-results` -- headless suite runs; object-store naming
  across COSMOS versions
