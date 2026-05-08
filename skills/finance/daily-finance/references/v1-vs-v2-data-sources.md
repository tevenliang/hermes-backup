# v1 vs v2 数据源架构对比

> 2026-05-06 建立。v2 = `daily_finance_v2.py`，v1 = `daily_finance_new.py`（已废弃）

## 各模块数据源

| 模块 | v1 | v2 |
|------|----|----|
| A股大盘指数 | 腾讯行情 + EM历史K线 | 腾讯行情 + EM历史K线（无变化） |
| 港股大盘指数 | 腾讯行情 + 缓存 | 腾讯行情 + 缓存（无变化） |
| 纳斯达克 | thsdk `market_data_index` | 腾讯 `usNDX`（thsdk批量返回空） |
| A股持仓 | thsdk `market_data_cn` | thsdk `market_data_cn`（无变化） |
| 港股持仓 | thsdk `market_data_hk`（有缺陷） | 腾讯行情（thsdk返回空无兜底） |
| ETF | 腾讯行情 | 腾讯行情（无变化） |
| 基金净值 | EM历史NAV + 1234567 | EM历史NAV + 1234567（无变化） |
| 异动新闻 | 同花顺问财 + 快讯 | + Tavily search（新增第三层） |

## v2 关键修复

1. **港股持仓**：thsdk `market_data_hk` 返回 `success=True/df=空` → 改用腾讯 `qt.gtimg.cn`；德昌代码从 `00579` 修正为 `00179`
2. **纳斯达克**：thsdk 批量指数返回空 → 改用腾讯 `usNDX`
3. **异动新闻**：加 Tavily search `--topic news` 作为第三层兜底

## EM 数据（v1/v2 均保留）

- 指数历史K线（算昨日涨跌幅）
- 基金净值历史NAV

thsdk 无法替代这两块。
