# Repository Overview

26 skills, ~26K lines for AI-assisted Adamant embedded software development.

## Top-Level Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Claude Code entry point (system prompt): build rules + skill inventory |
| `AGENTS.md` | Vendor-neutral agent instructions ([agents.md](https://agents.md/) convention); counterpart to `CLAUDE.md` |
| `SUBAGENT_CONTRACT.md` | Handoff contract for an orchestrated/headless build subagent (scoped posture: no git, output filtering, quality gates) |

## Skill Inventory by Category

### Core Development
- `adamant-skill-selector` — Entry point, routes to correct skills
- `adamant-component-dev` — YAML models, connectors, LASEL patterns
- `adamant-assembly-dev` — Scheduling, routing, ID assignment
- `adamant-testing` — Test harness, History API, coverage (largest: 2647 lines)
- `adamant-type-system` — YAML types, format codes, Ada hierarchy

### Infrastructure
- `adamant-build-system` — Redo commands, code gen, build paths
- `adamant-debugging` — GDB, post-mortem LCH/stack-trace triage, target pitfalls
- `adamant-project-setup` — Scaffolding, Docker, env/activate
- `adamant-style` — Ada/YAML/Python style rules
- `adamant-tools` — Python utilities: inspector, scaffolder, YAML validator

### Specialized
- `adamant-formal-verification` — SPARK contracts, GNATprove, ghost lemmas
- `adamant-cosmos-integration` — CCSDS pipeline, COSMOS plugin
- `adamant-cosmos-testing` — Integration test scripts
- `adamant-subassemblies` — Splitting assemblies, nesting, wiring
- `adamant-framework-components` — Catalog of 58 built-in components
- `adamant-framework-internals` — Python model internals, code gen debugging
- `adamant-generator-dev` — Custom generators (Ada, YAML types, HTML docs, ground artifacts)
- `adamant-cosmos-suite-results` — COSMOS suite execution (openc3cli / REST API) + result verification
- `adamant-regression-suite` — Black-box Python regression suites via COSMOS cmd/tlm (source-blind)
- `adamant-cosmos-tool-creation` — Custom COSMOS web UI tools (Vue/vite/single-spa), streaming vs polling, TSDB backfill

### Meta/Support
- `adamant-skill-creation` — Building and validating new skills
- `knowledge-acquisition` — Systematic codebase study with sub-agents
- `high-assurance-design` — Design-by-invariant, non-goals, formal verification
- `adamant-skill-campaign` — Cold-start skill-validation campaigns via the Workflow tool
- `adamant-code-review` — Component/test/type/assembly review checklists, design assessment
- `task-planning` — Time-boxing, progress tracking, batch execution for large tasks

## Structure Pattern

Each skill follows: `SKILL.md` (dense patterns) + `references/` (detailed examples) + optional `scripts/` (utilities).

## Validation State

- **Style:** 221/221 directories, 0 failures
- **Coverage:** 89%+ across 100+ components
- **Cold-start:** 0 errors (stress-tested)
- **Subassemblies:** R10 zero cold-start errors

---

# Prompt Caching and Cache Hits

## What Prompt Caching Does

When you send a request to the API, the input tokens are normally billed at full price every time. Prompt caching lets you mark a portion of the request (typically a large, stable system prompt or document) so the API stores it server-side. Subsequent requests that share that prefix hit the cache instead of reprocessing it.

**Cost impact:**
- Cache **miss** (first request): ~25% more expensive than normal input (cache write cost)
- Cache **hit** (subsequent requests): ~90% cheaper than normal input
- Output tokens: unaffected, always billed at full rate

For `claude-opus-5` at $5.00/1M input tokens:

| Event | Effective rate |
|-------|---------------|
| Normal input | $5.00/1M |
| Cache write (5-min TTL) | ~$6.25/1M (one-time) |
| Cache write (1-hour TTL) | ~$10.00/1M (one-time) |
| Cache read | ~$0.50/1M |

## Provider Caching Comparison

The structural principle -- stable content at the front of the prompt, variant content at the end, consistent ordering across calls -- is provider-agnostic and benefits from prefix caching on any provider that implements it. The specific mechanics, however, differ significantly:

| Provider | Caching model | Annotation required | Discount | TTL |
|----------|--------------|---------------------|---------|-----|
| Anthropic (Claude) | Explicit `cache_control` per block | Yes | ~90% on cache reads | 5 min default, 1hr optional (at 2x write cost) |
| OpenAI (GPT-4o+) | Automatic prefix caching | No | ~50% on cached input | 5-10 min inactivity, max 1hr |
| Google (Gemini 2.5+) | Implicit (automatic) or explicit cache objects | No for implicit; Yes for explicit | ~90% (2.5+), ~75% (2.0) | 1hr default, configurable |

> **Sources:** [Anthropic prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) -- [OpenAI prompt caching](https://platform.openai.com/docs/guides/prompt-caching) -- [Google Gemini context caching](https://ai.google.dev/gemini-api/docs/caching)

The skills in this repo are built around Anthropic. All cache mechanics documented here -- `cache_control`, 5-minute TTL, hit/miss reporting via `cache_creation_input_tokens`/`cache_read_input_tokens`, TTL reset on hit -- are Anthropic-specific. The structural optimizations (deterministic read order, stable prefix, variant content last) apply to any provider, but TTL behavior, annotation requirements, and cost models vary.

## Model-Tier Cache Economics

Since cache reads are always priced at 10% of the base input price across all Claude models, the **absolute dollar savings per cache hit scale directly with the model tier**. For a 100k token cached prefix:

| Model | Base input | Cache read | Savings per hit (100k tokens) | Write cost (100k, 5-min TTL) |
|-------|-----------|-----------|-------------------------------|------------------------------|
| Opus 5 | $5.00/1M | $0.50/1M | **$0.45** | $0.625 (recovered after ~2 hits) |
| Sonnet 5 | $3.00/1M | $0.30/1M | $0.27 | $0.375 (recovered after ~2 hits) |
| Haiku 4.5 | $1.00/1M | $0.10/1M | $0.09 | $0.125 (recovered after ~2 hits) |

> **Source:** [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing) -- cache read tokens are 0.1x base input price, cache write tokens are 1.25x base input price (5-min TTL) across all models.

The 90% discount ratio is uniform, but the absolute savings are **5x higher on Opus than Haiku** and **1.67x higher on Opus than Sonnet**. This compounds significantly across multi-step tasks that generate many API calls. Opus is also the model used for the most complex, longest-running tasks -- precisely the tasks that load the most skill content and generate the most API calls per session.

A full component development session (skill selector + component-dev + references + testing + iterative code generation) can produce 10-20 API calls sharing the same large prefix. Each cache hit at Opus pricing returns ~$0.45 per 100k cached tokens, with the initial write cost recovered after roughly 2 hits.

## Where Cache Hits Matter Most

Cache hits only save money when the **same prefix** is reused across multiple requests. High-value scenarios:

- **Multi-turn chat with a large system prompt** -- same system prompt on every turn
- **Document Q&A** -- same 50-page doc, many questions
- **Agentic loops** -- same tool definitions + instructions on every iteration
- **Batch processing** -- shared context across many items

## How This Applies to Skills

**Cache behavior is automatic for Claude Code users.** The structural optimizations in this repo are designed to maximize cache hit rates within a session. No API configuration is required.

### The Three-Tier Prompt Architecture

Skills are loaded in a fixed hierarchy that forms a stable, cacheable prefix:

| Tier | Content | Size | Cache role |
|------|---------|------|-----------|
| 1 | `CLAUDE.md` (system prompt) | ~170 lines | Outermost prefix -- always identical |
| 2 | `adamant-skill-selector/SKILL.md` | ~378 lines | Always loaded first, routes to 1-2 skills |
| 3 | Task-specific `SKILL.md` + `references/` | 250-800 lines | Stable per task type |

Task-variant content (the actual user request, iteration state) appears at the end of the prompt, after all stable skill content. This is the key structural choice that enables caching -- stable content at the front, variant content at the back.

### Deterministic Read Order

The skill selector documents specific read sequences for common task types. For example, a component + tests task always reads:

1. `adamant-skill-selector/SKILL.md`
2. `adamant-component-dev/SKILL.md`
3. `adamant-component-dev/references/pitfalls-and-checklist.md`
4. `adamant-testing/SKILL.md`

Identical read order across sub-agent spawns within a session means the prefix is byte-for-byte identical, which is the requirement for a cache hit. Varying the order -- even with the same files -- breaks the cache.

### Stable vs. Variant Content by Design

Skills are structured to keep the cacheable portion as large as possible:

- **`SKILL.md`** -- imperative procedures, checklists, naming rules, Ada/YAML patterns. Slow-changing. Lives in the stable prefix.
- **`references/`** -- detailed examples, validation history, code artifacts. Loaded only when needed, and only the specific files required.
- **Task request** -- always last. Never in the stable prefix.

This split means the bulk of skill content (~11000 lines across all `SKILL.md` files, plus selected references) can be cached across calls within a session, while only the task-specific question changes between requests.

### What "Within a Session" Means

Cache hits are most reliable for sub-agent calls made seconds apart within the same task run. A single component development session -- selector read, skill read, references read, iterative code generation -- generates multiple API calls that all share the same prefix. Those internal calls benefit most from caching.

Cache hits are less reliable across longer gaps (>5 minutes between requests) due to the default TTL. Returning to a task after a break typically starts with a cache miss on the first call, warming again for subsequent calls in that session.

### Skill Size and Cache Efficiency

The absolute token savings from a cache hit scale directly with the size of the cached prefix -- more tokens in the stable prefix means more tokens served at the ~90% discount on each hit. This has a direct relationship to how skills are sized.

Skills are not all the same size. The SKILL.md target of 250-350 lines is a minimum density floor, not a hard ceiling. The most-used, most complex skills are deliberately larger:

| Skill | Total lines (with refs) | SKILL.md lines | Notes |
|-------|------------------------|----------------|-------|
| `adamant-testing` | ~2647 | ~692 | Largest -- most frequently loaded alongside component dev |
| `adamant-component-dev` | ~2301 | ~718 | Core skill, loaded on almost every task |
| `adamant-formal-verification` | ~2240 | ~553 | SPARK numeric proofs; fixed-point / integer-logic / proof-mechanics refs |
| `adamant-assembly-dev` | ~1455 | ~661 | Second most common task type |
| `adamant-style` | ~1153 | ~490 | Often loaded as a secondary skill |
| `adamant-framework-internals` | ~441 | ~260 | Lightweight -- narrow-use, loaded only for code gen debugging |

**The cache efficiency implication:** a task that loads `adamant-component-dev/SKILL.md` (~719 lines, roughly 9,000-15,000 tokens) plus `adamant-testing/SKILL.md` (~692 lines) creates a stable cacheable prefix of 15,000-25,000 tokens from skill content alone, on top of CLAUDE.md and the selector. Every subsequent API call in that session serves those tokens at ~$0.50/1M instead of $5.00/1M.

A lightweight skill like `adamant-framework-internals` (~260 lines, ~4,000 tokens) cached in isolation saves proportionally less -- though it still benefits when combined with other stable prefix content.

**The key design constraint:** skill size is bounded by context budget, not by cache optimization. A 2,500-line monolithic SKILL.md would cache more tokens per hit but would consume context window that the model needs for the actual task. The `references/` pattern resolves this tension -- detailed examples live outside the core SKILL.md, loaded only when specifically needed, but when loaded they extend the cacheable prefix further for that call.

The result is that the skills most commonly exercised in multi-step tasks (component dev, testing, assembly) are also the largest, producing the best cache economics for the workflows that run the most API calls.

### TTL and Keeping the Cache Warm

The default cache TTL is 5 minutes, **reset on each cache hit** -- not just on the initial write. This means an active session naturally keeps itself warm. As long as API calls are occurring at least every 5 minutes (which is typical during active skill-driven development), the cache stays alive throughout the session. Each hit extends the window for the next one.

The cache cools when work pauses. A 10-minute break between requests lets the TTL expire, and the next call becomes a miss (and a cache write, re-warming for subsequent calls). For practical purposes:

- **Active, continuous work** -- cache stays warm for the duration of the session
- **Short pauses** (compile, review, context switching) -- typically within TTL, no impact
- **Longer breaks** (lunch, end of day, returning to a task) -- cold start, first call re-warms the cache
- **Separate sessions** -- always a cold start; cache does not persist across Claude Code sessions

---

# Cache Efficiency for Regular Users

## What Works for Any User

The same structural conditions apply -- stable system prompt (`CLAUDE.md` loaded at session start), deterministic skill read order, task-variant text at the end of the prompt. Any user who runs multiple requests within a single Claude Code session benefits from intra-session caching. The skill files are large (1-2k lines each), so they're well above the minimum cache threshold.

## Where Caching Is Less Reliable

A tightly-structured automated run has a controlled, repeatable prefix across iterations. Regular users have more variability:

- Different conversation history lengths between requests
- `CLAUDE.md` + skill content is stable, but everything before and between those reads varies by user workflow
- No guarantee of iteration cadence -- a user who pauses for 20 minutes between requests loses the cache at the 5-minute TTL

## Most Reliable Cache Wins for Regular Users

Within a single task session -- reading the skill selector, then one or two deep skills, then iterating on a component or test -- the sub-agent calls within that session will benefit. The skill content gets cached after the first read and serves subsequent calls in the same session cheaply.

Cross-session caching (coming back the next day to continue) -- no benefit. Cache does not persist across sessions.

## Bottom Line

Regular users get the intra-session efficiency. Even without a tightly-structured iteration cadence, the structural optimization (stable prefix, variant text at end) still helps every user by maximizing the cacheable prefix length.
