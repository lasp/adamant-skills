# Tool Archetypes, Custom Widgets, and the Microservice Backend

Concrete patterns behind the decision ladder. File paths are COSMOS 7.x source
locations (stable across a minor line) or the relevant plugin artifact; verify
against the deployed version when a detail matters.

## Archetypes (rung 3 tools)

Four recurring shapes. Pick by data access pattern and display, not by domain.

### A. Append-only log / event stream
A growing list fed by every packet of a high-rate or event packet.
- **Feed:** websocket `StreamingChannel` (lossless) -- NOT CVT polling, which
  drops bursts and re-serves the latest packet.
- **State:** accumulate in a bounded array; persist to localStorage keyed by
  scope so history survives reload; dedup on a value-level key (not the ns
  timestamp, which loses precision in JS `Number`).
- **Clear:** a persisted watermark (newest packet time seen at clear); drop any
  received or backfilled entry at or before it, so a stream/backfill cannot
  resurrect cleared entries. A clear that only empties the array un-clears on
  the next delivery.
- **Backfill:** subscribe with `start_time = last-seen + 1` to fill the gap from
  the time-series database, then continue realtime.
- See `streaming-and-data-access.md` for the exact recipe and message shapes.

### B. Single-packet detail view
Render one structured packet (e.g. an exception/fault packet) as a formatted
panel rather than a table.
- **Feed:** JSON-RPC poll of one packet (`get_tlm_packet(..., 'CONVERTED')`) is
  acceptable here -- the requirement is "show the latest occurrence," which is
  exactly CVT semantics. Poll on a modest interval.
- **Display:** the packet's converted item(s) drive a bespoke layout (nested
  fields, decoded structures, resolved references). The data access is simple;
  the value is in the rendering.
- Contrast with A: same conversion-backed data, opposite access pattern
  (latest-snapshot vs every-packet) and display (panel vs append log).

### C. External-I/O terminal / console (rung 4 -- needs a microservice)
A tool that talks to something COSMOS does not broker: a raw TCP/serial/telnet
endpoint, a subprocess, a device console.
- **Frontend:** a terminal component (e.g. xterm) opening a **raw browser
  `WebSocket`** (not ActionCable) to the backing microservice's route:
  `` `${proto}//${window.location.host}/<route_prefix>/<channel>` `` -- a relative
  URL under the current origin, with the channel selected by a path segment.
- **Backend:** a MICROSERVICE that bridges the external socket to the websocket,
  holds the connection alive independent of any browser tab, and replays a ring
  buffer to newly-attached clients. See the MICROSERVICE section below.

### D. Live 3D/graphics view of an external binary feed (rung 4)
A rendered scene (three.js/WebGL) driven by a binary stream COSMOS does not
broker -- e.g. a simulator's ZMQ/UDP visualization broadcast carrying protobuf
frames. Proven end-to-end; the browser-native render is also what makes the
tool portable (see the portability note below).

- **Bridge (microservice):** subscribe upstream, relay each payload to attached
  clients as **binary websocket frames** (opcode `0x2` -- the text-terminal
  archetype C uses `0x1`). Cache the latest payload and replay it on attach so
  a freshly opened tool renders without waiting for the next upstream message.
  Address the upstream by its **compose service name** (in-network), never a
  host-mapped port -- host mappings collide across concurrent stacks and do not
  exist in CI.
- **Decode in the tool:** vendor the `.proto` beside the tool source, import it
  as raw text (vite `?raw`), and `protobuf.parse(protoText)` at startup
  (protobufjs) -- no codegen step, and schema drift is a source-diff away.
  Distinguish two non-rendering states: *no feed* (backend legitimately absent,
  e.g. CI or a deployment without the upstream) and *frames arriving but not
  decoding* (schema drift) -- a bare `catch { return }` makes drift look like an
  idle feed; count failures and surface a distinct message (throttle the
  console warning).
- **Bundled static assets (meshes):** import the asset as raw text and parse it
  directly (`new OBJLoader().parse(objText)`) instead of fetching a URL -- this
  sidesteps tools-bucket asset-path resolution entirely and works identically
  in dev and deployed. Load heavy assets via dynamic `import()` so they
  code-split into lazy chunks and the scene paints immediately (keep a
  primitive placeholder as the load-failure fallback). Decimate meshes before
  committing (a headless Blender `DECIMATE` pass preserves bounds); raw CAD
  exports are megabytes of repo blob for no visual gain at tool scale.
- **Coordinate frames:** convert between the data's frame and the scene's frame
  (e.g. Z-up to Y-up) **once**, with a proper rotation on a single parent group
  (`root.rotation.set(-Math.PI / 2, 0, 0)`), and keep every per-body quantity
  in the data's native frame inside it. Do NOT swap vector/quaternion
  components per-value: a y/z component swap is a reflection (determinant -1)
  that mirrors the scene and breaks chirality in ways that look almost right.
- **Unmount hygiene (any animated/WebGL tool):** single-spa tools remount on
  every navigation, so `beforeUnmount` must (1) `cancelAnimationFrame` the
  render loop -- the closure otherwise pins the whole scene and keeps rendering
  a disposed renderer; (2) remove window-level listeners (register them with
  one `AbortController` signal and abort it); (3) traverse the scene disposing
  geometries/materials, then `renderer.dispose()` +
  `renderer.forceContextLoss()`. Browsers cap live WebGL contexts (~16 in
  Chromium); leaking one per remount breaks the tool after a dozen visits.
- **Dependency caveat:** a Python bridge's native-extension deps (e.g. zmq
  bindings) are NOT auto-installed -- the microservice runs in the operator's
  venv, so the dependency must be provided by the deployment (an install step
  at stack start) or the bridge crash-loops. If the plugin deploys to
  environments without the upstream feed or the dependency, gate the
  microservice behind a plugin `VARIABLE`.
- **Diagnosing a wrong/static render:** the tool renders whatever the feed
  says -- verify the *feed*, not the render. Capture upstream inside the
  network (a short script in a container subscribing directly) and check the
  values change as expected before touching tool code; a static upstream is an
  upstream/simulation problem the tool cannot fix.
- **Portability:** this archetype renders in the browser's own WebGL, so it is
  native-speed on every client OS and needs no GPU passthrough into
  containers -- which containerized native renderers do need and cannot get on
  Docker Desktop (macOS/Windows VMs have no GPU passthrough). Pure-JS deps
  (three, protobufjs) bundle into the tool; the only platform-sensitive piece
  is the bridge dependency above.

## The MICROSERVICE backend (rung 4)

**When:** the tool needs server-side work the browser + existing COSMOS APIs
cannot do -- bridge non-HTTP external I/O (raw TCP, serial, subprocess stdio),
hold a stateful long-lived connection, run a custom endpoint, or do heavy
compute. If the data is already reachable through the OpenC3 REST/streaming API,
build a pure-frontend tool instead (rungs 1-3).

**Declaration** (`plugin.txt`):

```
MICROSERVICE <FolderName> <instance-name>
  CMD <command...>          # process COSMOS launches (python/python3 auto-maps to the venv)
  PORT <n> [TCP|UDP|SCTP]   # port the process listens on; declare so routing knows it
  ROUTE_PREFIX /<prefix>    # traefik reverse-proxies /<prefix>/... to this microservice
  ENV <KEY> <VALUE>         # env vars; ERB <%= variable %> substitutes plugin VARIABLEs
  WORK_DIR <dir>            # optional; working dir for CMD (defaults to the folder)
```

- First positional = folder under `microservices/` holding the code; second =
  instance name (runtime `SCOPE__USER__NAME`). The folder deploys to the config
  bucket at install.
- `ROUTE_PREFIX` is the whole mechanism by which a browser tool reaches a custom
  backend: external `/<prefix>/...` is proxied to the microservice's `PORT`.
- Other modifiers exist (`CONTAINER`, `SECRET`, `TARGET_NAME`, `TOPIC`,
  `OPTION`, `SHARD`/`DB_SHARD`, `STOPPED`); the four above cover a tool backend.

**Transport and auth caveats:**
- Tool-to-microservice is a **raw WebSocket** (or plain HTTP), not ActionCable.
  The tool opens `new WebSocket(url)`; the microservice completes the handshake
  itself (e.g. the Ruby `websocket` gem) -- it is not on Rack/ActionCable and
  does not get the framework's channel plumbing.
- **A raw-websocket microservice is unauthenticated.** The URL carries no token,
  and the microservice receives none automatically -- unlike `OpenC3Api` and
  ActionCable, which attach `localStorage.openc3Token`. Its only protection is
  the traefik route + cluster network. Consequently: gate destructive actions
  client-side (a confirm overlay), and if the endpoint warrants it, validate a
  token you pass explicitly. State this risk plainly for any such tool.
- **Reconnect** splits across ends: give the client a manual/auto retry, and
  make the microservice keep its external connection alive across browser churn
  with a replay buffer, so a reattaching client sees recent history.

**Entry file naming:** `main.js` vs `main.system.js` are both SystemJS output
(single-spa loads via SystemJS); the name only has to match the tool's
`INLINE_URL`. First-party convention is `main.js`.

## Custom WIDGET (rung 2)

A telemetry-screen widget: one Vue component compiled to a UMD bundle, usable
inside any Telemetry Viewer screen with the screen runtime's data binding,
limits, and layout for free -- much lighter than a full tool.

- **Generate:** `openc3.sh cli generate widget <Name>Widget` -> `src/<Name>Widget.vue`.
- **Base class:** `import { Widget } from '@openc3/vue-common/widgets'`;
  `mixins: [Widget]` (or `VWidget`).
- **Naming:** PascalCase `<Name>Widget.vue` maps to the SCREAMING screen keyword:
  `SuperdataWidget.vue` -> `WIDGET SUPERDATA` -> used in a screen as
  `SUPERDATA <TARGET> <PACKET> <ITEM>`.
- **Build (UMD, not systemjs):** `build.lib` with `entry: src/<Name>Widget.vue`,
  `name: '<Name>Widget'`, `formats: ['umd']`,
  `fileName -> '<Name>Widget.umd.min.js'`, `sourcemap: true`,
  `outDir: 'tools/widgets/<Name>Widget'`. Externals `['vue', 'vuetify']`; inline
  CSS into the single JS (only the JS + `.map` deploy). Build one config per
  widget.
- **Deploy:** `WIDGET NAME` reads
  `tools/widgets/<Name>Widget/<Name>Widget.umd.min.js` + `.map` and uploads both
  to the tools bucket; `DISABLE_ERB` is its only modifier.
- **Keep a custom widget in its own plugin, separate from custom tools** -- per
  the OpenC3 docs, combining a custom TOOL and a custom WIDGET in one plugin can
  break the build (the widget's UMD build vs the tool's systemjs build).
  Multiple *tools* in one plugin are fine (the flight plugin ships two, the
  renode plugin ships two tools plus a microservice, each in a single gem); this
  caveat is specific to the tool+widget combination.

## Built-in widget catalog (rung 1 -- use before authoring)

Stock widget types a screen definition uses with zero custom code (from the
framework's `openc3-vue-common/src/widgets/`):

- **Layout:** VERTICAL(BOX), HORIZONTAL(BOX), HORIZONTALLINE, MATRIXBYCOLUMNS,
  TABBOOK, SCROLLWINDOW, ROLLUP, SPACER, TITLE, LABELLED
- **Value:** VALUE, LABEL, LABELVALUE, LABELVALUEDESC, FORMATVALUE, BLOCK,
  TEXTFIELD, TEXTBOX
- **Value + limits:** VALUELIMITSBAR/COLUMN, VALUERANGEBAR,
  LABELVALUELIMITSBAR/COLUMN, LABELVALUERANGEBAR, LIMITSBAR, LIMITSCOLUMN,
  LIMITSCOLOR, RANGEBAR, LED, PROGRESSBAR, LABELPROGRESSBAR
- **Plots:** LINEGRAPH, ARRAYPLOT, SPARKLINE, LABELSPARKLINE, SIGNAL, ARRAY
- **Canvas:** CANVAS(LABEL/IMAGE/LINE/DOT and their VALUE variants)
- **Controls:** BUTTON, CHECKBUTTON, RADIOBUTTON, RADIOGROUP, COMBOBOX, DATE, TIME
- **Media:** IMAGEVIEWER, IFRAME, FILEDISPLAY, FILECHECKSUM

If a stock widget or a composition of them expresses the display, a screen
(rung 1) beats every heavier option.

## Built-in tools (rung 0 -- check before building)

Open-source tools that ship with COSMOS: Admin, Bucket Explorer, Command Sender,
Command and Telemetry Server, Data Extractor, Data Viewer, Handbooks, Limits
Monitor, Packet Viewer, Script Runner, Table Manager, Telemetry Grapher,
Telemetry Viewer. Several tools are Enterprise-only (Autonomic, Calendar,
Command History, Command Queue, Log Explorer, Notebooks, System Health) -- do
not assume they exist on Core. If one already covers the workflow, configure it
instead of building.

## Build environment notes

- Front-end builds run in the OpenC3 node build container; that image lacks the
  `openc3` gem, so gemspec validation during a node-container build fails
  harmlessly.
- Behind a corporate proxy set `NODE_EXTRA_CA_CERTS`; pnpm may need write access
  to `node_modules`.
