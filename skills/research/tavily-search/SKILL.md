---
category: research
name: tavily
description: AI-optimized web search via Tavily API. Returns concise, relevant results for AI agents.
homepage: https://tavily.com
metadata:
  clawdbot:
    emoji: "🔍"
    requires:
      bins: ["node"]
      env: ["TAVILY_API_KEY"]
    primaryEnv: "TAVILY_API_KEY"
---

# Tavily Search

AI-optimized web search using Tavily API. Designed for AI agents - returns clean, relevant content.

## Search

```bash
node {baseDir}/scripts/search.mjs "query"
node {baseDir}/scripts/search.mjs "query" -n 10
node {baseDir}/scripts/search.mjs "query" --deep
node {baseDir}/scripts/search.mjs "query" --topic news
```

## Options

- `-n <count>`: Number of results (default: 5, max: 20)
- `--deep`: Use advanced search for deeper research (slower, more comprehensive)
- `--topic <topic>`: Search topic - `general` (default) or `news`
- `--days <n>`: For news topic, limit to last n days

## Extract content from URL

```bash
node {baseDir}/scripts/extract.mjs "https://example.com/article"
```

Notes:
- Needs `TAVILY_API_KEY` from https://tavily.com
- Tavily is optimized for AI - returns clean, relevant snippets
- Use `--deep` for complex research questions
- Use `--topic news` for current events

## Pitfalls

### subprocess.run() does not inherit TAVILY_API_KEY from .env

When `search.mjs` is invoked via `subprocess.run()` from a Python script, it does **not** inherit env vars from the Python process's environment — including `TAVILY_API_KEY` even if it is set in `~/.hermes/.env`.

**Symptom**: `Missing TAVILY_API_KEY` printed to stderr, even though the key exists in `.env`.

**Workaround** — read the key from `.env` explicitly before invoking the script:

```python
import os, subprocess

HERMES_ENV = "/Users/twliang/.hermes/.env"

def _get_tavily_key():
    key = os.environ.get("TAVILY_API_KEY", "").strip()
    if key:
        return key
    with open(HERMES_ENV) as f:
        for line in f:
            if line.startswith("TAVILY_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""

env = os.environ.copy()
env["TAVILY_API_KEY"] = _get_tavily_key()
subprocess.run(
    ["node", "/path/to/search.mjs", query, "-n", "3"],
    env=env, capture_output=True, text=True
)
```

The same pattern applies to any skill script invoked from Python subprocesses when the script relies on env vars.
