category: research
---
name: "multi-search-engine"
description: "Multi search engine integration with 17 engines (8 CN + 9 Global). Supports advanced search operators, time filters, site search, privacy engines, and WolframAlpha knowledge queries. No API keys required. Use when: you need a specific engine (Baidu, DuckDuckGo, etc.), advanced operators (!gh, filetype:, site:), or a privacy engine. For quick factual/definitional queries on current topics, prefer the native MCP web search tool (mcp_minimax_web_search) instead — it responds faster without needing to load a skill first."
---

# Multi Search Engine v2.0.1

Integration of 17 search engines for web crawling without API keys.

## When to Use This vs. Native Search Tools

**Use native MCP search (mcp_minimax_web_search) for:**
- Quick factual or definitional queries
- Current events / recent news
- One-off lookups where speed matters
- Any topic where freshness matters (add `tbs=qdr:w` to URL if using this skill)

**Use this skill when:**
- You need a specific domestic engine (Baidu, Sogou, WeChat search)
- Advanced operators: `site:`, `filetype:`, DuckDuckGo bangs (`!gh`, `!so`)
- Privacy-preserving search (DuckDuckGo, Startpage, Brave)
- Cross-engine comparison of results
- WolframAlpha calculations/conversions

## Search Engines

### Domestic (8)
- **Baidu**: `https://www.baidu.com/s?wd={keyword}`
- **Bing CN**: `https://cn.bing.com/search?q={keyword}&ensearch=0`
- **Bing INT**: `https://cn.bing.com/search?q={keyword}&ensearch=1`
- **360**: `https://www.so.com/s?q={keyword}`
- **Sogou**: `https://sogou.com/web?query={keyword}`
- **WeChat**: `https://wx.sogou.com/weixin?type=2&query={keyword}`
- **Toutiao**: `https://so.toutiao.com/search?keyword={keyword}`
- **Jisilu**: `https://www.jisilu.cn/explore/?keyword={keyword}`

### International (9)
- **Google**: `https://www.google.com/search?q={keyword}`
- **Google HK**: `https://www.google.com.hk/search?q={keyword}`
- **DuckDuckGo**: `https://duckduckgo.com/html/?q={keyword}`
- **Yahoo**: `https://search.yahoo.com/search?p={keyword}`
- **Startpage**: `https://www.startpage.com/sp/search?query={keyword}`
- **Brave**: `https://search.brave.com/search?q={keyword}`
- **Ecosia**: `https://www.ecosia.org/search?q={keyword}`
- **Qwant**: `https://www.qwant.com/?q={keyword}`
- **WolframAlpha**: `https://www.wolframalpha.com/input?i={keyword}`

## Quick Examples

```javascript
// Basic search
web_fetch({"url": "https://www.google.com/search?q=python+tutorial"})

// Site-specific
web_fetch({"url": "https://www.google.com/search?q=site:github.com+react"})

// File type
web_fetch({"url": "https://www.google.com/search?q=machine+learning+filetype:pdf"})

// Time filter (past week)
web_fetch({"url": "https://www.google.com/search?q=ai+news&tbs=qdr:w"})

// Privacy search
web_fetch({"url": "https://duckduckgo.com/html/?q=privacy+tools"})

// DuckDuckGo Bangs
web_fetch({"url": "https://duckduckgo.com/html/?q=!gh+tensorflow"})

// Knowledge calculation
web_fetch({"url": "https://www.wolframalpha.com/input?i=100+USD+to+CNY"})
```

## Advanced Operators

| Operator | Example | Description |
|----------|---------|-------------|
| `site:` | `site:github.com python` | Search within site |
| `filetype:` | `filetype:pdf report` | Specific file type |
| `""` | `"machine learning"` | Exact match |
| `-` | `python -snake` | Exclude term |
| `OR` | `cat OR dog` | Either term |

## Time Filters

| Parameter | Description |
|-----------|-------------|
| `tbs=qdr:h` | Past hour |
| `tbs=qdr:d` | Past day |
| `tbs=qdr:w` | Past week |
| `tbs=qdr:m` | Past month |
| `tbs=qdr:y` | Past year |

## Privacy Engines

- **DuckDuckGo**: No tracking
- **Startpage**: Google results + privacy
- **Brave**: Independent index
- **Qwant**: EU GDPR compliant

## Bangs Shortcuts (DuckDuckGo)

| Bang | Destination |
|------|-------------|
| `!g` | Google |
| `!gh` | GitHub |
| `!so` | Stack Overflow |
| `!w` | Wikipedia |
| `!yt` | YouTube |

## WolframAlpha Queries

- Math: `integrate x^2 dx`
- Conversion: `100 USD to CNY`
- Stocks: `AAPL stock`
- Weather: `weather in Beijing`

## Search Freshness — Known Limitation

Web search results are not guaranteed to be recent. If results appear outdated:

1. **Add time filter**: append `&tbs=qdr:w` (past week), `&tbs=qdr:d` (past day), or `&tbs=qdr:m` (past month) to the URL
2. **Use a different engine**: Google and Bing tend to surface fresher content than Baidu for English topics
3. **Use a direct source**: if the topic has a known authoritative source (e.g., official docs, a specific site), navigate directly
4. **Explain to the user**: if no fresh results exist, say so clearly and suggest alternative approaches

Common pattern: Chinese tech topics (Hermes Agent, OpenClaw, etc.) often peak in集中发布期 — content that seems "old" (1-2 months) may actually be the most comprehensive available. When this happens, tell the user why and what alternatives exist.

## Documentation

- `references/advanced-search.md` - Domestic search guide
- `references/international-search.md` - International search guide
- `CHANGELOG.md` - Version history

## License

MIT
