---
name: daily-finance
category: finance
version: 1.8
description: |
  每日财经动态汇总。每天 18:00 自动执行（cron），汇总：
  1. 大盘指数（腾讯行情 A股/港股/纳指 + 东方财富历史K线算昨日涨跌）
  2. 关注板块ETF（腾讯行情 + 飞书多维表格 tblPBNcI1BiNLg7G）
  3. 基金净值（东方财富历史NAV + 1234567今日估算）
  4. 基金Top5持仓（飞书多维表格 tbl8hhmWssnxpmFg + thsdk/腾讯行情）
  5. 异动股票资讯（同花顺问财 + 快讯 + Tavily search 兜底）

  用户手动触发时说：「每日财经」「财经日报」「今日财经」
---

# 每日财经 Skill（daily-finance）

## 触发方式

- **手动触发**：用户说「每日财经」「财经日报」「今日财经」
- **自动执行**：每天 18:00 via cron（job: 每日财经）

---

## 执行方式

### 自动化模式（cron 调用）

**两步执行**：

**第一步**：使用 `mcp_lark_mcp_bitable_v1_appTableRecord_search` 读取 ETF 列表，写入本地 JSON：

- app_token: `SYgZb5RGHalBU7sctGscDRIpnzg`
- table_id: `tblPBNcI1BiNLg7G`
- 输出文件: `/Users/twliang/.hermes/skills/finance/daily-finance/cache/etf_list.json`
- 返回字段: `所属板块`、`ETF或基金名称`、`ETF或基金代码`
- 格式: JSON 数组，每个元素 `{"sector": "板块", "name": "名称", "code": "代码"}`

**第二步**：运行主脚本：

```bash
python3 /Users/twliang/.hermes/skills/finance/daily-finance/scripts/daily_finance_v2.py
```

脚本会读取上一步生成的 `etf_list.json`，若无该文件则使用硬编码兜底数据。

脚本会：
1. 拉取大盘指数（腾讯行情 A股/港股 + 纳指，thsdk作备用）
2. 拉取关注板块ETF（腾讯行情 + 飞书多维表格 tblPBNcI1BiNLg7G）
3. 查询基金净值（东方财富历史K线 + 1234567今日估算）
4. 查询基金 Top5 持仓（飞书多维表格 tbl8hhmWssnxpmFg + thsdk/腾讯行情）
5. 抓取异动股票资讯（mx-finance-search）
6. 生成飞书文档并推送链接

### 手动模式（对话触发）

**直接用 MCP + MCP，全部我来做，不需要跑脚本**：

1. 用 `mcp_lark_mcp_bitable_v1_appTableRecord_search` 读 ETF 列表：
   - app_token: `SYgZb5RGHalBU7sctGscDRIpnzg`
   - table_id: `tblPBNcI1BiNLg7G`
   - 格式化为 `{"sector": "板块", "name": "名称", "code": "代码"}` 数组

2. 拉取大盘指数：腾讯行情 `https://qt.gtimg.cn/q=sh000001,sz399001,...`（备用：thsdk）

3. 拉取基金净值：东方财富历史NAV接口（`https://api.fund.eastmoney.com/f10/lsjz`）

4. 用 `mcp_lark_mcp_bitable_v1_appTableRecord_search` 读基金持仓：
   - app_token: `SYgZb5RGHalBU7sctGscDRIpnzg`
   - table_id: `tblnShCdlwFweVag`
   - 筛选涨跌幅 >5% 的股票

5. **查异动股新闻（三层兜底，已在 v2 中实现）**：
   - 异动股：筛选涨跌幅 >5% 的持仓股票
   - 第一层：同花顺问财 `ths.wencai_nlp("今日涨停，非ST")` — 匹配股票名称/代码
   - 第二层：同花顺快讯 `ths.news()` — 通用7×24快讯，按股票名关键词过滤
   - 第三层：Tavily search `--topic news` — 实时网络新闻（v2 已接入）
   - Tavily API Key 在 `~/.hermes/.env`，Tavily skill 路径 `~/.hermes/skills/research/tavily-search/`

6. **生成飞书文档并推送**：
   - 用 `mcp_lark_mcp_docx_v1_document_create` 创建文档
   - 立即 `send_message` 推送到用户飞书 DM

---

## 飞书文档发布

**手动模式**：用 `mcp_lark_mcp_docx_v1_document_create` 创建文档，folder_token `K312fSiL0lApa8dLCARczd1jnUO`。
**自动模式（cron）**：也优先用 MCP，同上。

> **用户铁律**：生成飞书文档后必须推送链接，不能只打印输出。

---

## 关注板块

| 板块 | URFI 代码 |
|------|----------|
| 黄金概念 | URFI885530 |
| 共封装光学(CPO) | URFI886033 |
| 智能电网 | URFI885311 |

---

## 目标资产

| 资产 | 路径 |
|------|------|
| **主脚本（v2，当前执行版本）** | `/Users/twliang/.hermes/skills/finance/daily-finance/scripts/daily_finance_v2.py` |
| 旧版脚本（已废弃） | `/Users/twliang/.hermes/skills/finance/daily-finance/scripts/daily_finance_new.py` |
| ETF数据源（飞书多维表格） | app_token: SYgZb5RGHalBU7sctGscDRIpnzg, table: tblPBNcI1BiNLg7G |
| 基金持仓数据源（飞书多维表格） | app_token: SYgZb5RGHalBU7sctGscDRIpnzg, table: tbl8hhmWssnxpmFg |

## 注意

- **执行时间**：每天 18:00（工作日）
- **文档存放**：「400 贾维斯」文件夹（folder_token: XwBif5LqOlW1oEdXBoYcx2ADnWe）
- **依赖项**：thsdk（pip install thsdk）、tencent-news skill
- **API Keys 集中管理**：`TENCENT_NEWS_APIKEY`、`TAVILY_API_KEY`、`MATON_API_KEY` 均在 `~/.hermes/.env`，不在 `.zshrc`（已迁移）

## 陷阱（Pitfalls）

### 不要在每次本地修改后自动推送到 GitHub

用户明确说"不需要每次改完都进行git push"。本地修改后除非用户说"上传GitHub"或"备份"，否则不动Git。

### skill 目录迁移后 cron job 路径不自动同步

`daily-finance` 曾从 `workspace/` 迁到 `finance/`，cron job prompt 可能仍含旧路径 `workspace/daily-finance/`。

**每次 skill 目录迁移后执行验证：**
```bash
hermes cron list
# 检查 prompt_preview 中的路径是否为当前实际路径
# 若仍为 workspace/daily-finance/ → 用 hermes cron edit 更新
```

### lark-cli 无法读取 bitable（MCP vs 子进程权限模型）

脚本曾用 `subprocess.run("lark-cli ...")` 读 bitable，报权限错误（Bot 无 bitable 权限）。

**解决方案**：cron job 先用 MCP 读 bitable 写 JSON，脚本只读 JSON。详见 `references/mcp-vs-larkcli-permission.md`。

### A股指数不能用 thsdk market_data_index 批量调用

thsdk `market_data_index(['USHI1A0001'])` 批量传入返回空，但单条 `market_data_index('USHI1A0001')` 有数据。thsdk 批量模式对指数类数据不稳定。

**解决方案**：A 股大盘指数（上证/深证/创业板/科创50）统一用腾讯 `qt.gtimg.cn`：
```
https://qt.gtimg.cn/q=sh000001|sz399001|sz399006|sh000688
```
可一次批量查询多个代码，用 `|` 分隔。恒生/恒生科技/纳指也走腾讯，无需 thsdk 兜底。

### 腾讯行情接口参数格式（已实测验证）

| 品种 | 腾讯代码 | 备注 |
|------|----------|------|
| 上证指数 | `sh000001` | |
| 深证成指 | `sz399001` | |
| 创业板指 | `sz399006` | |
| 科创50 | `sh000688` | |
| 德昌电机控股 | `hk00179` | bitable 存 `00579`（错误，00579是京能清洁能源）|
| 中芯国际 | `hk00981` | |
| 阿里巴巴-W | `hk09988` | |
| 纳指 | `usNDX` | 腾讯行情可用，无需 thsdk |

### thsdk THSCODE 格式（文档错误，实测正确格式）

thsdk 官方文档示例 `USHI000001`（上证指数）和 `USHI000688`（科创50）是**错误的**。

实测正确格式：
| 指数 | THSCODE（实测） | 文档错误格式 |
|------|----------------|-------------|
| 上证指数 | `USHI1A0001` | `USHI000001` |
| 科创50 | `USHI1B0688` | `USHI000688` |
| 深证成指 | `USZI399001` | — |
| 创业板指 | `USZI399006` | — |

注：thsdk `market_data_index` **批量调用**（传入列表）返回空，必须**逐个调用**。A股指数建议直接走腾讯行情，避开此问题。

### 同一文件反复 patch 会导致结构损坏

本 skill 脚本在经历多次 patch 后出现重复函数定义（`get_sector_etfs` 定义两次）和缩进错误。

**经验法则**：对同一文件做超过 3-4 轮 patch 后若再出问题，**重写整个文件**，而非继续 patch。补丁累积会引入重复定义和缩进漂移。

### 德昌电机控股代码勘误

bitable 存储的代码 `00579` 是京能清洁能源，不是德昌电机控股。腾讯正确代码为 `hk00179`。代码映射关系：
```
# stock_code_map（用于修正 bitable 错误代码）
"00579": "hk00179"  # 德昌电机控股
```

### mx-finance-search 路径错误导致新闻静默失败

脚本里引用路径为 `skills/workspace/mx-finance-search`，实际路径为 `skills/finance/mx-finance-search`。skill 不存在时静默跳过，无报错。

**手动模式**：直接用 MCP 调用 `mx-finance-search` skill，不需要在脚本里引用路径。
