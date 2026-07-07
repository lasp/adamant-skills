# Streaming and Data Access Mechanics (COSMOS 7.x)

Server-side detail behind the SKILL.md feed table and streaming recipe. File
references are COSMOS source paths (stable across a minor line); verify against
the deployed version when debugging.

## Where values come from

One process per target decommutates packets: the DECOM microservice. It reads
raw buffers from the per-packet `{scope}__TELEMETRY__{{TARGET}}__PACKET` Redis
stream, runs `packet.decom()` (conversions, formats, limits), then publishes:

- the decom hash to the `{scope}__DECOM__{{TARGET}}__PACKET` Redis stream, and
- the Current Value Table entry (Redis hash `{scope}__tlm__TARGET`), latest
  packet only.

The decom hash keys items as `ITEM` (raw), `ITEM__C` (converted, present only
when a conversion or states exist), `ITEM__F` (formatted, units folded in),
`ITEM__L` (limits state). Every downstream consumer -- JSON-RPC, streaming,
TSDB -- serves these stored values; nothing re-runs conversions at read time.

## JSON-RPC (polling) path

`get_tlm_packet` / `get_tlm_values` / `tlm()` read the CVT hash and apply
"downward typing": a CONVERTED request resolves `["ITEM__C", "ITEM"]`, first
key wins, so a missing conversion silently degrades to raw. Latest packet
only -- two packets inside one poll interval means the first is never seen by a
poller. Items return under their plain names (the `__C` suffix is internal).

## Streaming path -- realtime

`StreamingChannel` (ActionCable over `/openc3-api/cable`) with an `add` of item
keys and `start_time: null` attaches a realtime thread that XREADs the DECOM
stream from "now". Per decommutated packet, the server builds one entry:

```
{ "__time": <packet time, integer ns since epoch>,
  "<item_key>": <value from ITEM__C, falling back to ITEM>,
  "__type": "ITEMS" }
```

Entries batch into one websocket broadcast per read cycle (mid-cycle flush at
100 entries realtime / 600 logged). Packets marked `stored` are skipped in
realtime. Errors are transmitted as a non-array `{ "error": "..." }` object.

**Retention:** the DECOM Redis streams are trimmed by the TSDB microservice
(roughly a one-minute keep window, trimmed each minute), so a realtime-only
reader can recover only ~1-2 minutes after a disconnect. Longer gaps require
`start_time` (below). If the TSDB microservice is not deployed, nothing trims
the DECOM streams at all.

## Streaming path -- historical (`start_time`)

An `add` with `start_time` spawns a logged thread. If `start_time` is older
than the oldest Redis entry, values come from the time-series database
(QuestDB); otherwise from the Redis stream at an interpolated offset. Decom
history in 7.x lives only in the TSDB -- there are no decom bucket log files
(raw packet logs in the bucket serve RAW-mode streaming only).

**TSDB storage rules (what is backfillable):**

- The TSDB microservice writes one column per decom-hash key -- including
  `ITEM__C` -- one table per packet.
- Column types follow the item/conversion declaration: STRING/BLOCK map to
  varchar; a conversion's declared `converted_type` types the `__C` column.
- List/dict converted values are stored as JSON **text** in a varchar column.
  On read-back they are returned as that JSON string -- NOT re-parsed -- while
  the live stream delivers the real array/object. Clients must normalize
  (parse string values) to treat backfill and live uniformly.
- ARRAY-typed items (`array_size` set) get no `__C` column via DDL and
  items-mode CONVERTED requests for them are downgraded to RAW.
- A conversion that declares a numeric `converted_type` but returns
  non-numeric data creates a numeric column and the ingest fails per row --
  the history silently lacks those values. Declare `converted_type` to match
  the actual return type.
- Table retention is unbounded unless the plugin sets a decom retain time.

**Transition to realtime:** when the TSDB drain catches up, the thread bridges
onto the Redis stream with a deliberate ~2 s overlap, deduplicating by packet
time, then hands off to the realtime thread once offsets align. The client
sees a seamless stream -- no marker at catch-up. A bounded query (`end_time`
in the past) ends with an explicit empty-array `[]` broadcast; realtime
streams never send `[]`.

**Boundary caveats for clients:**

- Packet-time-equal packets at the TSDB/Redis seam can be dropped by the
  server-side dedup; entries re-delivered across a *client* reconnect are not
  deduplicated for you. Use a value-level unique key client-side.
- `__time` is integer nanoseconds; JS `Number` rounds it (~2^53 precision).
  Safe for display and windowing, unsafe as an exact dedup key.

## Auth details

The websocket URL carries the scope query param; subscriptions carry
`token: localStorage.openc3Token`. The server accepts token placement in
either the connection URL (legacy clients) or the subscription params, so
minor client/server version skew does not break streaming. Every `add` payload
must include `scope` and `token`; a missing scope rejects the subscription.

## Choosing packet mode vs items mode

Item keys (`DECOM__TLM__T__P__ITEM__CONVERTED`) return per-item entries and are
the norm for tools. Packet-mode keys stream whole decom hashes; on TSDB
backfill the `__C` columns are renamed to plain item names and formatted
variants are dropped. Prefer items mode unless the tool genuinely consumes
most of a packet.

## Verifying a tool's feed against ground truth

When validating that a streaming tool shows every packet (no drops) or that a
converted value is what the server actually stored, you need an independent
ground truth -- not the tool reading itself back. Three sources, most to least
reliable in practice:

- **Query the time-series database directly (most reliable).** On COSMOS 7.x the
  decom output is a QuestDB table per packet
  (`{SCOPE}__TLM__{TARGET}__{PACKET}`) with one column per decom-hash key,
  including the converted `ITEM__C` columns. Its HTTP API answers SQL:
  `GET /exp?query=...` (CSV) or `/exec` (JSON) on the tsdb service port (9000),
  authenticated with the QuestDB HTTP user/password (env `QDB_HTTP_USER` /
  `QDB_HTTP_PASSWORD`). Example (from inside a container that can reach the tsdb
  host): select `PACKET_TIMESECONDS` + `"ITEM__C"` over a time window and
  reconcile against the tool's export. Note: **column/table names that are SQL
  keywords must be double-quoted** (`"BUFFER__C"`), and a list/dict converted
  value is stored as **JSON text** in a VARCHAR column (parse it before
  comparing). This bypasses the streaming stack entirely and is the definitive
  record of what decom wrote.
- **`StreamingWebSocketApi.read_all(items=[...], start_time=, end_time=)`** (the
  Python `openc3.script` client, runnable headless inside a container). Convenient
  and language-native, but a *bounded* historical query (with `end_time`) has
  been observed to hang on some deployments at the logged->realtime handoff --
  if a capture stalls, fall back to the direct DB query rather than debugging the
  socket. (venv path: `/openc3/python/.venv/bin/python` on 7.x.)
- **A second, independent consumer** -- e.g. a `subscribe_packets`/`get_packets`
  capture in a procedure reading the DECOM topic. Good for live/near-real-time
  spans; bounded by Redis decom-topic retention (~minutes), so not for history.

Reconciliation tip: match on a **stable per-event identity** (a value that
embeds the source timestamp), not the packet `__time` (ns rounding) and not row
counts alone -- diff the actual event/value set so a discrepancy names the
specific missing item. Account for the tool's own dedup (identical values
collapsed) and any display cap (oldest trimmed) before calling a gap a drop.
