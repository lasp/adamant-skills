#!/usr/bin/env python3
"""
Usage report for knowledge-acquisition sessions.

Reads OpenClaw session store and estimates cost for sub-agent sessions.

Usage:
    python3 usage_report.py [--sessions-file PATH] [--format text|json]

Default sessions file: ~/.openclaw/agents/main/sessions/sessions.json
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Approximate per-million-token costs (input+output blended estimate)
# These are rough -- real cost depends on input/output ratio
MODEL_COSTS_PER_MTK = {
    "claude-opus-4-6": 30.0,        # ~$15 in / $75 out, blended ~$30/MTk
    "claude-sonnet-4-20250514": 6.0, # ~$3 in / $15 out, blended ~$6/MTk
    "claude-sonnet-4": 6.0,
    "claude-haiku-3-5": 1.6,        # ~$0.80 in / $4 out, blended ~$1.6/MTk
}

DEFAULT_COST = 10.0  # fallback


def load_sessions(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def estimate_cost(model: str, total_tokens: int) -> float:
    rate = MODEL_COSTS_PER_MTK.get(model, DEFAULT_COST)
    return (total_tokens / 1_000_000) * rate


def report(sessions_file: Path, fmt: str = "text"):
    data = load_sessions(sessions_file)
    rows = []
    total_tokens_all = 0
    total_cost_all = 0.0

    for key, sess in sorted(data.items(), key=lambda x: x[1].get("updatedAt", 0)):
        model = sess.get("model", "unknown")
        total_tokens = sess.get("totalTokens", 0)
        updated = sess.get("updatedAt", 0)
        cost = estimate_cost(model, total_tokens)
        total_tokens_all += total_tokens
        total_cost_all += cost

        ts = datetime.fromtimestamp(updated / 1000).strftime("%H:%M") if updated else "?"
        is_sub = "subagent" in key

        rows.append({
            "key": key,
            "model": model,
            "tokens": total_tokens,
            "cost": cost,
            "time": ts,
            "subagent": is_sub,
        })

    if fmt == "json":
        print(json.dumps({
            "sessions": rows,
            "total_tokens": total_tokens_all,
            "total_cost_estimate": round(total_cost_all, 4),
        }, indent=2))
    else:
        print(f"{'Session':60s} {'Model':30s} {'Tokens':>10s} {'~Cost':>8s} {'Time':>6s}")
        print("-" * 120)
        for r in rows:
            label = r["key"]
            if len(label) > 58:
                label = "..." + label[-55:]
            tag = " [sub]" if r["subagent"] else ""
            print(f"{label:60s} {r['model']:30s} {r['tokens']:>10,d} ${r['cost']:>7.4f} {r['time']:>6s}{tag}")
        print("-" * 120)
        print(f"{'TOTAL':60s} {'':30s} {total_tokens_all:>10,d} ${total_cost_all:>7.4f}")
        subs = [r for r in rows if r["subagent"]]
        if subs:
            sub_tok = sum(r["tokens"] for r in subs)
            sub_cost = sum(r["cost"] for r in subs)
            print(f"{'  sub-agents only':60s} {'':30s} {sub_tok:>10,d} ${sub_cost:>7.4f}")


def main():
    p = argparse.ArgumentParser(description="Knowledge acquisition usage report")
    p.add_argument("--sessions-file", type=Path,
                   default=Path.home() / ".openclaw/agents/main/sessions/sessions.json")
    p.add_argument("--format", choices=["text", "json"], default="text")
    args = p.parse_args()
    report(args.sessions_file, args.format)


if __name__ == "__main__":
    main()
