---
name: 客户新闻追踪
description: 从飞书知识库多维表格读取客户企业列表，查询每家企业的最新新闻/动态，生成飞书文档并回填多维表格。触发词：客户新闻、客户动态、每日客户新闻、客户情报、客户企业追踪
version: "1.0.0"
---

# 客户新闻追踪

从飞书知识库表读取客户列表 → 查询每家企业最新新闻 → 生成飞书文档 → 回填 bitable。

## 资产配置

> **实际值在 `config/config.json`**（脚本运行时读取），SKILL.md 此处仅供参考。

| 资产 | 值 |
|------|-----|
| 客户数据表 App Token | `BO6kb2c7haHY2FsLJCecH1mrnhe`（从 config 读取） |
| 客户数据表 Table ID | `tblDEBAW1NOq61Ch`（从 config 读取） |
| 目标云盘文件夹 | `K312fSiL0lApa8dLCARczd1jnUO` |
| Tavily API Key | 写入 `config/config.json` 的 `tavily.api_key` |

## 执行脚本

**全部逻辑封装在 `scripts/fetch_and_sync.py`，直接运行即可完成全流程：**

> **注意**：必须使用 Python 3.11（系统默认 python3 为 3.9.6，不兼容）。

```bash
/opt/homebrew/bin/python3.11 /Users/twliang/.hermes/skills/workspace/客户新闻追踪/scripts/fetch_and_sync.py
```

**参数说明：**
- 无参数：跑全量 200 家
- `--company=名称`：只处理匹配的企业
- `--limit=N`：最多处理 N 家（配合 `--resume-from` 使用）
- `--resume-from=N`：从第 N 家继续（断点续传）
- `--date=YYYY-MM-DD`：覆盖回填日期（用于补历史）
- `--dry-run`：只查询不创建文档

**示例：**
```bash
# 跑全量
/opt/homebrew/bin/python3.11 /Users/twliang/.hermes/skills/workspace/客户新闻追踪/scripts/fetch_and_sync.py

# 从第 40 家开始跑 10 家
/opt/homebrew/bin/python3.11 /Users/twliang/.hermes/skills/workspace/客户新闻追踪/scripts/fetch_and_sync.py --resume-from=40 --limit=10

# 只查比亚迪
/opt/homebrew/bin/python3.11 /Users/twliang/.hermes/skills/workspace/客户新闻追踪/scripts/fetch_and_sync.py --company=比亚迪
```

脚本内部自动完成：
1. 读取知识库表（lark-cli，--as bot，从 `config/config.json` 读取 app_token 和 table_id）
2. 对每家企业查询新闻（优先东方财富妙想资讯搜索，无结果则调用 Tavily API）
3. 创建飞书文档（lark-cli，--as user，stdin 方式传入 markdown）
4. 回填 bitable（lark-cli，--as bot，写入"企业新闻"URL 和"企业新闻最后更新"日期）

## 已知问题

**Python 版本兼容性**：shebang 为 `#!/opt/homebrew/bin/python3.11`，必须用这个路径运行。脚本使用 `Optional[]` 类型标注，系统 `python3` 为 3.9.6，不支持。

**严禁安装 mx-claw 插件**：该插件与飞书 channel 冲突，会导致飞书消息被渲染为 "[Image]" 占位符、消息完全不回等严重故障。一旦安装只能通过卸载插件解决（`openclaw plugins remove mx-claw` 并重启 gateway）。**任何需要东方财富 API 的场景，直接调用 `~/.hermes/skills/finance/mx-finance-search/scripts/get_data.py` 即可，不依赖 mx-claw 插件。**

**东方财富妙想 API 输出格式**：调用 `get_data.py` 时 stdout 包含非 JSON 前缀行（"默认输出目录"、"Saved: ..."），JSON 从第一个 `{` 字符开始。subprocess 调用时必须用 `stdout.find("{")` 定位起点再截取：
```python
stdout = result.stdout.decode()
json_start = stdout.find("{")
data = json.loads(stdout[json_start:])
```

**lark-cli --markdown 路径解析**：使用 `--markdown -` stdin 方式传入内容，不用绝对路径或 `@relative/path` 写法。

**opencli 输出是 YAML 不是 JSON**：在 Python subprocess 中调用 opencli 命令（如 `opencli 36kr search`），返回的是 YAML 格式（例：`- rank: 1\n  title: ...`），不能用 `json.loads()` 解析，必须用 `yaml.safe_load()`。

## 手动分步执行（当脚本失败时）

当脚本不可用或需要调试时，按以下顺序手动执行：

**Step 1：读取知识库表**
```bash
lark-cli base +record-list --as bot \
  --base-token VNLrbIYoAausDOs5uovcO7fPn0d \
  --table-id tbl2vVHnujNPQczd --limit 200
```
记录每行的 `record_id` 和 `企业名称`。

**Step 2：新闻查询**
- 优先：`opencli 36kr search "{企业名称}"`（输出为 YAML，不是 JSON）
- 兜底：`tavily-search` 或 `cn-web-search`，关键词 `"企业名称" + "新闻"`

**Step 3：写临时 .md 文件**
```bash
echo "{markdown内容}" > /tmp/{safe_name}.md
```

**Step 4：创建飞书文档**
```bash
# 方式1：用 stdin 传入内容（推荐，避免路径解析问题）
cat /tmp/{safe_name}.md | lark-cli docs +create --as user \
  --title "{企业名称} 最新动态" \
  --folder-token K312fSiL0lApa8dLCARczd1jnUO \
  --markdown -

# 方式2：直接用绝对路径
lark-cli docs +create --as user \
  --title "{企业名称} 最新动态" \
  --folder-token K312fSiL0lApa8dLCARczd1jnUO \
  --markdown /tmp/{safe_name}.md
```
从输出中提取 `doc_id`，拼接 `https://www.feishu.cn/docx/{doc_id}`。

**Step 5：回填 bitable**（用脚本时自动完成）

> 脚本内字段 ID：
> - Customer: `fldueSOrU3`
> - 企业新闻: `fldC80mDeb`
> - 企业新闻最后更新: `fldCeGnPG2`

```bash
lark-cli base +record-upsert --as bot \
  --base-token BO6kb2c7haHY2FsLJCecH1mrnhe \
  --table-id tblDEBAW1NOq61Ch \
  --record-id {record_id} \
  --json '{"fldC80mDeb": "https://www.feishu.cn/docx/xxx", "fldCeGnPG2": "2026-05-05"}'
```

## 错误处理

- 单家企业失败 → 跳过，继续下一家，最终汇总报错
- 不因单点失败中断整批任务

## 参考资料

- [lark-cli --markdown stdin 方式](./references/lark-cli-markdown-stdin.md) — 文档创建时路径解析问题及解决方案

## 触发方式

```
客户新闻、客户动态、每日客户新闻、客户情报、客户企业追踪
```
