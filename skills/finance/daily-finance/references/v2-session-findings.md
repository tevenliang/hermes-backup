# v2 重构关键发现（2026-05-06）

## 数据源总览（v2 确认版）

| 模块 | 主数据源 | 备用/兜底 |
|------|----------|-----------|
| 大盘指数 | 腾讯行情 `qt.gtimg.cn` | EM历史K线（仅算昨日涨跌） |
| 港股持仓 | 腾讯行情 | — |
| A股持仓 | thsdk `market_data_cn` | — |
| ETF | 腾讯行情 | — |
| 基金净值 | EM历史NAV + 1234567估算 | — |
| 异动新闻 | 同花顺问财 → 快讯 → **Tavily** | — |

## v2 关键修复

### 1. 港股持仓：腾讯替代 thsdk
- thsdk `market_data_hk` 对德昌(00179)/中芯国际(00981)返回 `success=True, df=空`
- 条件 `if r.success and not r.df.empty` 为 False，未触发腾讯兜底
- **v2 直接用腾讯行情 `hk00179`/`hk00981`/`hk09988`**，不再走 thsdk

### 2. 纳斯达克：腾讯 usNDX 替代 thsdk
- thsdk `market_data_index` 批量调用返回空，单次调用才能用
- 腾讯接口 `usNDX` 一次批量返回，A 股 + 港股 + 纳指 7 个代码一起查

### 3. 德昌电机控股代码纠错
- bitable 存 `00579`（京能清洁能源，不是德昌）
- 腾讯正确代码 `hk00179`，脚本用 `STOCK_CODE_MAP` 修正

### 4. 三层异动新闻兜底（Tavily 已接入）
```
第一层：ths.wencai_nlp("今日涨停，非ST")  → 异动股列表匹配
第二层：ths.news()                          → 通用快讯关键词匹配
第三层：Tavily search --topic news          → 实时网络新闻（v2 新增）
```
Tavily API Key 在 `~/.hermes/.env`（`TAVILY_API_KEY`），subprocess 调用时需显式注入。

## API Key 迁移记录（2026-05-06）
- `TENCENT_NEWS_APIKEY` — 从 `~/.zshrc` 迁入 `~/.hermes/.env`
- `MATON_API_KEY` — 从 `~/.zshrc` 迁入 `~/.hermes/.env`
- `TAVILY_API_KEY` — 已在 `~/.hermes/.env`
- `.zshrc` 中这两个 key 已注释，不再存储敏感信息
